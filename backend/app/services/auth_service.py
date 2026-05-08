"""
Authentication service - handles OAuth2, JWT tokens, and user management.

WHY THIS FILE EXISTS:
- Separates auth logic from API routes
- Reusable across multiple endpoints
- Easy to test independently
- Single place to add new auth methods (email/password, Google, etc.)

WHAT IT DOES:
- LinkedIn OAuth2 flow (authorization code → access token)
- JWT token generation for session management
- User creation and updates
- Token validation and refresh
- Secure password handling (not needed for OAuth, but for future email/password auth)

PRODUCTION PATTERN:
Most web apps have a dedicated auth service:
- It's complex (handles multiple auth methods)
- It's critical (security vulnerability = game over)
- It changes frequently (add new login methods, MFA, etc.)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from app.utils.config import settings
from app.utils.logger import get_logger
from app.models.schemas import UserResponse, UserDB
from app.db.mongodb import get_database
from bson import ObjectId
import aiohttp

logger = get_logger(__name__)


class AuthService:
    """Authentication service for OAuth2, JWT, and user management."""

    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token for a user.

        JWT (JSON Web Token) is a standard way to create tamper-proof tokens.
        When user logs in, we give them a token they send with each request.
        We validate the token (can't be forged) without hitting the database.

        Args:
            user_id: The user's MongoDB ObjectId
            expires_delta: How long token is valid (defaults to 24 hours)

        Returns:
            JWT token string

        Example:
            token = AuthService.create_access_token(user_id="507f1f77bcf86cd799439011")
            # Token is sent to frontend, frontend sends it with each API request
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=settings.jwt_expiration_hours)

        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "sub": user_id,  # sub = subject (the user ID)
            "exp": expire,  # exp = expiration
            "iat": datetime.now(timezone.utc),  # iat = issued at
        }

        # Encode with secret key (only server knows this)
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        logger.debug(f"Created JWT token for user {user_id}")
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """
        Verify JWT token and extract user ID.

        This is called on every API request to check:
        - Token wasn't tampered with (signature valid)
        - Token hasn't expired
        - Token contains a valid user_id

        Args:
            token: JWT token from request header

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id: str = payload.get("sub")

            if user_id is None:
                logger.warning("Token missing user_id (sub)")
                return None

            return user_id

        except JWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None

    @staticmethod
    async def get_or_create_user(
        email: str,
        name: str,
        linkedin_id: str,
        linkedin_access_token: str,
        token_expiry: datetime,
    ) -> Dict:
        """
        Get existing user or create new one after OAuth login.

        When user logs in via LinkedIn:
        1. Check if user exists (by email or linkedin_id)
        2. If exists, update their LinkedIn token (in case it changed)
        3. If new, create user record

        Args:
            email: User's email
            name: User's full name
            linkedin_id: LinkedIn unique ID
            linkedin_access_token: Token to call LinkedIn API on user's behalf
            token_expiry: When token expires

        Returns:
            User document from MongoDB

        Raises:
            Exception: If database operation fails
        """
        try:
            db = get_database()
            users_col = db["users"]

            # Try to find existing user
            existing_user = await users_col.find_one(
                {"$or": [{"email": email}, {"linkedin_id": linkedin_id}]}
            )

            if existing_user:
                # User exists, update their LinkedIn token
                # (tokens expire, so we update on each login)
                updated_user = await users_col.find_one_and_update(
                    {"_id": existing_user["_id"]},
                    {
                        "$set": {
                            "linkedin_access_token": linkedin_access_token,
                            "token_expiry": token_expiry,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                    return_document=True,
                )
                logger.info(f"Updated existing user: {email}")
                return updated_user

            else:
                # Create new user
                new_user = UserDB(
                    email=email,
                    name=name,
                    linkedin_id=linkedin_id,
                    linkedin_access_token=linkedin_access_token,
                    token_expiry=token_expiry,
                )

                result = await users_col.insert_one(new_user.model_dump())
                user_doc = await users_col.find_one({"_id": result.inserted_id})

                logger.info(f"Created new user: {email}")
                return user_doc

        except Exception as e:
            logger.error(f"Error in get_or_create_user: {str(e)}")
            raise

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict]:
        """
        Fetch user by ID.

        Args:
            user_id: MongoDB ObjectId as string

        Returns:
            User document or None if not found
        """
        try:
            db = get_database()
            users_col = db["users"]

            user = await users_col.find_one({"_id": ObjectId(user_id)})
            return user

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None

    @staticmethod
    def convert_user_to_response(user: Dict) -> UserResponse:
        """
        Convert MongoDB user document to response model.

        Why separate function?
        - Response shouldn't include sensitive fields (tokens, passwords)
        - Keeps sensitive data in MongoDB, never returns to frontend
        - Type-safe with Pydantic

        Args:
            user: User document from MongoDB

        Returns:
            UserResponse with non-sensitive fields only
        """
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            linkedin_id=user["linkedin_id"],
            created_at=user["created_at"],
        )

    @staticmethod
    async def exchange_oauth_code_for_token(code: str) -> Dict:
        """
        Exchange LinkedIn OAuth authorization code for access token.
        
        This is Step 2 of the OAuth flow:
        1. User logs in on LinkedIn (browser handles)
        2. LinkedIn redirects with code (browser redirects)
        3. WE exchange code for token (THIS FUNCTION)
        4. User gets JWT token for our app
        
        With OpenID Connect scopes, LinkedIn returns:
        - access_token: For API calls
        - id_token: JWT with user info (name, email, sub)
        
        Args:
            code: Authorization code from LinkedIn
            
        Returns:
            Dict with "access_token", "id_token", and "expires_in"
            
        Raises:
            Exception: If LinkedIn API fails
        """
        try:
            # LinkedIn token endpoint
            url = "https://www.linkedin.com/oauth/v2/accessToken"
            
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.linkedin_redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
            
            # Make async HTTP request to LinkedIn
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        logger.error(f"LinkedIn token error: {error_data}")
                        raise Exception(f"LinkedIn error: {error_data}")
                    
                    token_data = await response.json()
                    
                    logger.info("Successfully exchanged OAuth code for token")
                    logger.debug(f"Token response keys: {token_data.keys()}")
                    
                    return {
                        "access_token": token_data.get("access_token"),
                        "id_token": token_data.get("id_token"),  # OpenID Connect token with user info
                        "expires_in": token_data.get("expires_in"),
                    }
        
        except Exception as e:
            logger.error(f"OAuth token exchange failed: {str(e)}")
            raise

    @staticmethod
    def decode_id_token(id_token: str) -> Dict:
        """
        Decode LinkedIn's OpenID Connect ID token to extract user information.
        
        The id_token is a JWT that contains:
        - sub: LinkedIn user ID
        - given_name: First name
        - family_name: Last name
        - email: Email address
        - picture: Profile picture URL
        
        Args:
            id_token: JWT token from LinkedIn
            
        Returns:
            Dict with user info extracted from token
            
        Raises:
            Exception: If token is invalid
        """
        try:
            from jose import jwt as jose_jwt
            
            # Decode without verification (LinkedIn's token is signed, we trust it)
            # In production, verify signature against LinkedIn's public keys
            payload = jose_jwt.get_unverified_claims(id_token)
            
            logger.info(f"Decoded ID token for LinkedIn user: {payload.get('sub')}")
            
            return {
                "linkedin_id": payload.get("sub"),
                "first_name": payload.get("given_name", "User"),
                "last_name": payload.get("family_name", ""),
                "email": payload.get("email"),
                "picture": payload.get("picture"),
            }
        
        except Exception as e:
            logger.error(f"Failed to decode ID token: {str(e)}")
            raise

    @staticmethod
    async def get_linkedin_profile(access_token: str) -> Dict:
        """
        Fetch user profile information from LinkedIn API.
        
        Returns: id, localizedFirstName, localizedLastName, profilePicture
        
        Args:
            access_token: LinkedIn access token
            
        Returns:
            Dict with "linkedin_id", "first_name", "last_name"
            
        Raises:
            Exception: If LinkedIn API fails
        """
        try:
            url = "https://api.linkedin.com/v2/me"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LinkedIn profile fetch failed: {response.status} - {error_text}")
                        raise Exception(f"LinkedIn profile fetch failed: {response.status}")
                    
                    profile = await response.json()
                    
                    # Handle both v1 and v2 API response formats
                    linkedin_id = profile.get("id") or profile.get("sub")
                    first_name = profile.get("given_name") or profile.get("localizedFirstName", "User")
                    last_name = profile.get("family_name") or profile.get("localizedLastName", "")
                    
                    if not linkedin_id:
                        raise Exception("No LinkedIn ID found in profile response")
                    
                    logger.info(f"Fetched LinkedIn profile for user {linkedin_id}")
                    
                    return {
                        "linkedin_id": linkedin_id,
                        "first_name": first_name,
                        "last_name": last_name,
                    }
        
        except Exception as e:
            logger.error(f"Failed to fetch LinkedIn profile: {str(e)}")
            raise

    @staticmethod
    async def get_linkedin_email(access_token: str) -> str:
        """
        Fetch email address from LinkedIn (requires email permission scope).
        
        With the new LinkedIn OAuth scopes (openid profile email),
        email is returned directly from the /v2/me endpoint.
        This function is kept for backward compatibility and as fallback.
        
        Args:
            access_token: LinkedIn access token
            
        Returns:
            Email address or None if failed
        """
        try:
            # Try the newer endpoint first (v2 with openid/email scopes)
            url = "https://api.linkedin.com/v2/me"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        profile = await response.json()
                        if "email" in profile:
                            logger.info("Fetched LinkedIn email from /v2/me")
                            return profile["email"]
            
            # Fallback to old emailAddress endpoint
            url = "https://api.linkedin.com/v2/emailAddress?q=primary&projection=(elements*(handle~))"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Could not fetch email from LinkedIn: {response.status}")
                        return None
                    
                    email_data = await response.json()
                    if "elements" in email_data and len(email_data["elements"]) > 0:
                        email = email_data["elements"][0]["handle~"]["emailAddress"]
                        logger.info("Fetched LinkedIn email from emailAddress endpoint")
                        return email
                    
                    return None
        
        except Exception as e:
            logger.warning(f"Could not fetch email from LinkedIn: {str(e)}")
            return None

    @staticmethod
    async def check_and_refresh_token_if_needed(user_id: str) -> Optional[str]:
        """
        Check if user's LinkedIn token is about to expire.
        If within 5 minutes of expiry, tokens should be refreshed.
        
        For now, this returns a warning to the client.
        Full implementation requires LinkedIn refresh_token support.
        
        Args:
            user_id: MongoDB user ID
            
        Returns:
            Access token if still valid, None if needs refresh
        """
        try:
            db = get_database()
            users_col = db["users"]
            user = await users_col.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                return None
            
            # Check if token expired (with 5 minute buffer)
            now = datetime.now(timezone.utc)
            buffer = timedelta(minutes=5)
            
            token_expiry = user.get("token_expiry")
            if not token_expiry:
                logger.warning(f"User {user_id} has no token_expiry set")
                return user.get("linkedin_access_token")
            
            # Convert token_expiry to timezone-aware if needed
            if token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            
            if token_expiry - buffer < now:
                # Token expired or expiring soon
                logger.warning(f"Token for user {user_id} is expiring or expired")
                return None
            
            return user.get("linkedin_access_token")
        
        except Exception as e:
            logger.error(f"Error checking token: {str(e)}")
            return user.get("linkedin_access_token") if user else None
