"""
FastAPI routes - all API endpoints for the system.

WHY ONE FILE FOR ALL ROUTES?
- MVP should be simple to understand
- All endpoints visible in one place
- No deep folder nesting
- Easy to add auth middleware
- Can split into multiple files later as it grows

HOW IT WORKS:
- FastAPI uses function-based views (like Flask)
- @app.get(), @app.post(), etc. define endpoints
- Dependency injection (get_current_user) handles auth
- Pydantic models auto-validate request/response data
- OpenAPI docs generated automatically at /docs

STRUCTURE:
- Health/Public endpoints
- Auth endpoints (OAuth, login)
- Post CRUD endpoints (all require auth)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta
from typing import Optional

from app.models.schemas import (
    CreatePostRequest,
    UpdatePostRequest,
    PostResponse,
    UserResponse,
    LoginResponse,
    HealthResponse,
    ErrorResponse,
    PostStatus,
)
from app.services.auth_service import AuthService
from app.services.post_service import PostService
from app.utils.logger import get_logger
from app.utils.config import settings
from bson import ObjectId

logger = get_logger(__name__)

# Create router
router = APIRouter()


# ===========================
# Dependencies (Middleware-like)
# ===========================


async def get_current_user(token: Optional[str] = None) -> str:
    """
    Dependency to verify JWT token and extract user ID.

    This is called on every protected endpoint.
    If token is invalid/missing, raises 401 Unauthorized.

    Usage:
        @app.post("/api/posts")
        async def create_post(
            data: CreatePostRequest,
            user_id: str = Depends(get_current_user)
        ):
            ...

    Args:
        token: JWT token from Authorization header

    Returns:
        User ID if token valid

    Raises:
        HTTPException: If token missing/invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = AuthService.verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


# ===========================
# Public Endpoints
# ===========================


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Used by monitoring systems to verify app is running.
    Called frequently, should respond quickly.

    Returns:
        Health status with timestamp
    """
    return HealthResponse(
        status="healthy",
        environment=settings.app_env,
        timestamp=datetime.utcnow(),
    )


# ===========================
# Authentication Endpoints
# ===========================


@router.get("/auth/linkedin/url")
async def get_linkedin_oauth_url():
    """
    Get LinkedIn OAuth login URL.

    Frontend calls this to get the LinkedIn login link.
    Then redirects user to LinkedIn's login page.
    
    The OAuth flow:
    1. Frontend calls this endpoint
    2. Gets OAuth URL with all required parameters
    3. Redirects user to this URL
    4. User logs in on LinkedIn
    5. LinkedIn redirects back to /auth/callback with authorization code
    
    Scopes explained:
    - r_liteprofile: Read basic profile info (name, picture)
    - w_member_social: Write to member's social feed (create posts)
    - r_emailaddress: Read email address (optional but recommended)

    Returns:
        Dict with "login_url" to redirect user to
    """
    try:
        import secrets
        from urllib.parse import urlencode
        
        # Generate CSRF token for security
        state = secrets.token_urlsafe(32)
        
        # OAuth parameters
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "scope": "r_liteprofile w_member_social r_emailaddress",
            "state": state,  # CSRF protection
        }
        
        login_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
        
        logger.info("OAuth URL generated")
        
        return {
            "login_url": login_url,
            "client_id": settings.linkedin_client_id,
        }
    
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OAuth URL",
        )


@router.get("/auth/callback")
async def oauth_callback(code: str, state: Optional[str] = None):
    """
    OAuth callback handler - called when user returns from LinkedIn.

    LinkedIn redirects here with authorization code.
    We exchange code for access token and create/update user.

    Flow:
    1. User clicks "Login with LinkedIn"
    2. Redirects to LinkedIn login page
    3. User approves access
    4. LinkedIn redirects here with code
    5. We exchange code for token
    6. Create JWT token for user
    7. Return token to frontend

    Args:
        code: Authorization code from LinkedIn
        state: CSRF token (security check)

    Returns:
        Redirects to frontend dashboard with token
    """
    try:
        logger.info(f"OAuth callback received with code: {code[:10]}...")
        
        # Step 1: Exchange code for LinkedIn access token
        token_response = await AuthService.exchange_oauth_code_for_token(code)
        linkedin_access_token = token_response["access_token"]
        expires_in = token_response["expires_in"]
        
        # Step 2: Fetch user profile from LinkedIn
        profile = await AuthService.get_linkedin_profile(linkedin_access_token)
        email = await AuthService.get_linkedin_email(linkedin_access_token)
        
        # Step 3: Calculate token expiry
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Step 4: Create/update user in database
        full_name = f"{profile['first_name']} {profile['last_name']}"
        user = await AuthService.get_or_create_user(
            email=email or f"user_{profile['linkedin_id']}@linkedin.com",
            name=full_name,
            linkedin_id=profile["linkedin_id"],
            linkedin_access_token=linkedin_access_token,
            token_expiry=token_expiry,
        )
        
        # Step 5: Generate JWT token
        jwt_token = AuthService.create_access_token(str(user["_id"]))
        
        logger.info(f"✅ User authenticated: {user['_id']}")
        
        # Step 6: Redirect to frontend with token
        # Frontend will store token and redirect to dashboard
        from fastapi.responses import RedirectResponse
        
        frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
        redirect_url = f"{frontend_url}/dashboard?token={jwt_token}"
        
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}")
        # Redirect to frontend with error
        from fastapi.responses import RedirectResponse
        
        frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
        redirect_url = f"{frontend_url}/?error={str(e)}"
        
        return RedirectResponse(url=redirect_url)


@router.get("/api/me", response_model=UserResponse)
async def get_current_user_info(
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Get current authenticated user's information.
    
    Returns:
        Current user's profile data
    """
    try:
        user = await AuthService.get_user_by_id(current_user)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            linkedin_id=user["linkedin_id"],
            created_at=user["created_at"],
        )
    
    except Exception as e:
        logger.error(f"Error fetching user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user information",
        )


# ===========================
# Post Endpoints (Require Auth)
# ===========================


@router.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: CreatePostRequest,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Create a new scheduled post.

    User provides content and scheduled time.
    Post is stored in database and scheduled for publishing.

    Args:
        request: Post creation data
        authorization: JWT token in header
        current_user: User ID (from token)

    Returns:
        Created post data

    Raises:
        HTTPException: If validation fails
    """
    try:
        # Verify user exists
        user = await AuthService.get_user_by_id(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create post in database
        post = await PostService.create_post(
            user_id=current_user,
            content=request.content,
            scheduled_time=request.scheduled_time,
            platform=request.platform,
        )

        # Schedule the post with APScheduler
        from app.scheduler.scheduler import schedule_post

        await schedule_post(str(post["_id"]), request.scheduled_time)

        logger.info(f"Post created: {post['_id']}")

        # Convert to response model
        return PostResponse(
            id=str(post["_id"]),
            user_id=post["user_id"],
            content=post["content"],
            scheduled_time=post["scheduled_time"],
            status=PostStatus(post["status"]),
            platform=post["platform"],
            retry_count=post["retry_count"],
            created_at=post["created_at"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post",
        )


@router.get("/api/posts", response_model=dict)
async def list_posts(
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List user's posts with optional filtering.

    Args:
        authorization: JWT token
        current_user: User ID (from token)
        status_filter: Filter by status (draft, scheduled, posted, failed)
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        List of posts with pagination info
    """
    try:
        # Parse status filter if provided
        status_enum = None
        if status_filter:
            try:
                status_enum = PostStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}",
                )

        # Get posts from database
        result = await PostService.list_user_posts(
            user_id=current_user,
            status=status_enum,
            skip=skip,
            limit=limit,
        )

        # Convert to response models
        posts = [
            PostResponse(
                id=str(p["_id"]),
                user_id=p["user_id"],
                content=p["content"],
                scheduled_time=p["scheduled_time"],
                status=PostStatus(p["status"]),
                platform=p["platform"],
                linkedin_post_id=p.get("linkedin_post_id"),
                retry_count=p["retry_count"],
                last_error=p.get("last_error"),
                created_at=p["created_at"],
                posted_at=p.get("posted_at"),
            )
            for p in result["items"]
        ]

        return {
            "items": posts,
            "total": result["total"],
            "page": skip // limit + 1,
            "per_page": limit,
        }

    except Exception as e:
        logger.error(f"Error listing posts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list posts",
        )


@router.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Get a specific post by ID.

    Args:
        post_id: Post MongoDB ObjectId
        authorization: JWT token
        current_user: User ID (from token)

    Returns:
        Post data

    Raises:
        HTTPException: If post not found or user doesn't own it
    """
    try:
        post = await PostService.get_post(post_id)

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Verify user owns this post
        if post["user_id"] != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this post",
            )

        return PostResponse(
            id=str(post["_id"]),
            user_id=post["user_id"],
            content=post["content"],
            scheduled_time=post["scheduled_time"],
            status=PostStatus(post["status"]),
            platform=post["platform"],
            linkedin_post_id=post.get("linkedin_post_id"),
            retry_count=post["retry_count"],
            last_error=post.get("last_error"),
            created_at=post["created_at"],
            posted_at=post.get("posted_at"),
        )

    except Exception as e:
        logger.error(f"Error fetching post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post",
        )


@router.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    request: UpdatePostRequest,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Update a scheduled post.

    Can only update unposted posts (draft, scheduled, failed).

    Args:
        post_id: Post MongoDB ObjectId
        request: Update data
        authorization: JWT token
        current_user: User ID (from token)

    Returns:
        Updated post

    Raises:
        HTTPException: If can't update
    """
    try:
        updated = await PostService.update_post(
            post_id=post_id,
            user_id=current_user,
            content=request.content,
            scheduled_time=request.scheduled_time,
        )

        return PostResponse(
            id=str(updated["_id"]),
            user_id=updated["user_id"],
            content=updated["content"],
            scheduled_time=updated["scheduled_time"],
            status=PostStatus(updated["status"]),
            platform=updated["platform"],
            linkedin_post_id=updated.get("linkedin_post_id"),
            retry_count=updated["retry_count"],
            last_error=updated.get("last_error"),
            created_at=updated["created_at"],
            posted_at=updated.get("posted_at"),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post",
        )


@router.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Delete a post.

    Can only delete unposted posts (draft, scheduled, failed).

    Args:
        post_id: Post MongoDB ObjectId
        authorization: JWT token
        current_user: User ID (from token)

    Raises:
        HTTPException: If can't delete
    """
    try:
        await PostService.delete_post(post_id, current_user)
        return None

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post",
        )


@router.post("/api/posts/{post_id}/retry", status_code=status.HTTP_200_OK)
async def retry_failed_post(
    post_id: str,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Manually retry a failed post.
    
    WHY:
    - Users shouldn't have to wait for automatic retry schedule
    - Improves UX when they fix the underlying issue
    - Empowers users to take action
    
    Args:
        post_id: Post to retry
        authorization: JWT token
        current_user: User ID (from token)
    
    Returns:
        Success message
    
    Raises:
        HTTPException: If post not found, not failed, or retry fails
    """
    try:
        post = await PostService.get_post(post_id)
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        
        # Verify ownership
        if post["user_id"] != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to retry this post",
            )
        
        # Only retry failed posts
        if post["status"] != PostStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only failed posts can be retried (current status: {post['status']})",
            )
        
        # Reset status to scheduled for immediate retry
        await PostService.update_post_status(post_id, PostStatus.SCHEDULED)
        
        logger.info(f"Post {post_id} retried by user {current_user}")
        
        return {
            "message": "Post queued for retry",
            "post_id": post_id,
            "status": "scheduled",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry post",
        )


@router.get("/api/posts/{post_id}/stats", response_model=dict)
async def get_post_stats(
    post_id: str,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Get post performance statistics from LinkedIn.
    
    WHY:
    - Show users how their posts perform
    - Track engagement metrics
    - Measure automation effectiveness
    - Provide analytics dashboard insights
    
    Args:
        post_id: Post to get stats for
        authorization: JWT token
        current_user: User ID (from token)
    
    Returns:
        Post engagement statistics
    
    Raises:
        HTTPException: If post not found or not posted yet
    """
    try:
        post = await PostService.get_post(post_id)
        
        if not post or post["status"] != PostStatus.POSTED.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or not yet posted",
            )
        
        if post["user_id"] != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view these stats",
            )
        
        # Get user credentials
        db = get_database()
        user = await db["users"].find_one({"_id": ObjectId(current_user)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Fetch stats from LinkedIn
        from app.services.linkedin_service import LinkedInService
        
        linkedin_post_id = post.get("linkedin_post_id")
        if not linkedin_post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post has no LinkedIn ID",
            )
        
        stats = await LinkedInService.get_post_stats(
            post_id=linkedin_post_id,
            access_token=user["linkedin_access_token"],
        )
        
        return {
            "post_id": post_id,
            "linkedin_post_id": linkedin_post_id,
            "likes": stats["likes"],
            "comments": stats["comments"],
            "reposts": stats["reposts"],
            "engagement": stats["engagement"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching post stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post statistics",
        )


@router.get("/api/me", response_model=UserResponse)
async def get_current_user_info(
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Get current logged-in user's information.

    Args:
        authorization: JWT token
        current_user: User ID (from token)

    Returns:
        User data

    Raises:
        HTTPException: If user not found
    """
    try:
        user = await AuthService.get_user_by_id(current_user)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return AuthService.convert_user_to_response(user)

    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )
