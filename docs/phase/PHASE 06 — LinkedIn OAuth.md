# PHASE 06 — LinkedIn OAuth & Platform Publishing

## Phase Goal
Implement LinkedIn OAuth 2.0 connection flow, token storage/refresh, and actual post publishing to LinkedIn. Users connect their LinkedIn account once and can then publish any generated post directly to LinkedIn from the app.

---

## Features Implemented
- LinkedIn OAuth 2.0 Authorization Code flow
- OAuth callback handling + token exchange
- Access token encrypted storage in MongoDB
- LinkedIn identity fetch (name, profile picture, URN)
- `POST /publish/linkedin` — Publish generated post to LinkedIn
- LinkedIn formatter (ensure spacing, length compliance)
- Disconnect LinkedIn account
- Frontend: Connect LinkedIn button with OAuth popup
- Frontend: Connected account badge
- Platform abstraction layer (extensible to Instagram, GitHub)

---

## Technical Architecture

```
app/
├── api/v1/routes/
│   ├── integrations.py          ← /integrations/linkedin/connect, /callback, /disconnect
│   └── publish.py               ← /publish/:platform
├── services/
│   ├── integration_service.py   ← OAuth flow, token management
│   └── publish_service.py       ← Orchestrates platform publishing
├── services/platforms/
│   ├── __init__.py
│   ├── base_platform.py         ← Abstract Platform class
│   └── linkedin/
│       ├── __init__.py
│       ├── auth.py              ← OAuth token exchange, refresh
│       ├── publish.py           ← LinkedIn share API call
│       └── formatter.py         ← LinkedIn-specific content formatting
├── core/
│   └── encryption.py            ← AES token encryption/decryption
└── repositories/
    └── user_repository.py       ← update_linkedin_integration()
```

---

## LinkedIn OAuth Flow

```
User clicks "Connect LinkedIn"
        ↓
Frontend opens: GET /integrations/linkedin/connect
        ↓
Backend redirects to:
  https://www.linkedin.com/oauth/v2/authorization
  ?client_id=...
  &redirect_uri=https://api.yourdomain.com/api/v1/integrations/linkedin/callback
  &scope=openid%20profile%20w_member_social
  &state=<random_state_token>
  &response_type=code
        ↓
LinkedIn redirects user to: /integrations/linkedin/callback?code=...&state=...
        ↓
Backend:
  1. Verify state token (CSRF check)
  2. Exchange code for access_token
  3. Fetch LinkedIn user profile (URN, name)
  4. Encrypt access_token
  5. Store in users.integrations.linkedin
  6. Redirect to frontend: /dashboard?linkedin=connected
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/integrations/linkedin/connect` | ✅ | Initiate OAuth — redirects to LinkedIn |
| GET | `/api/v1/integrations/linkedin/callback` | ❌ | OAuth callback (LinkedIn redirects here) |
| DELETE | `/api/v1/integrations/linkedin/disconnect` | ✅ | Disconnect LinkedIn |
| GET | `/api/v1/integrations/status` | ✅ | Get integration connection status |
| POST | `/api/v1/publish/linkedin` | ✅ | Publish post to LinkedIn |

---

## Token Encryption (`app/core/encryption.py`)
```python
from cryptography.fernet import Fernet
from app.core.config import settings
import base64

def _get_fernet() -> Fernet:
    # Derive a Fernet key from SECRET_KEY
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32].ljust(32, b'='))
    return Fernet(key)

def encrypt_token(token: str) -> str:
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()
```

---

## Platform Base Class (`app/services/platforms/base_platform.py`)
```python
from abc import ABC, abstractmethod

class BasePlatform(ABC):
    """Abstract base for all social media platforms."""

    @abstractmethod
    async def publish(self, access_token: str, content: str) -> dict:
        """Publish content. Returns dict with platform_post_id."""
        pass

    @abstractmethod
    def format_content(self, content: str) -> str:
        """Platform-specific formatting (spacing, length)."""
        pass

    @abstractmethod
    async def verify_token(self, access_token: str) -> bool:
        """Check if access token is still valid."""
        pass
```

---

## LinkedIn Auth (`app/services/platforms/linkedin/auth.py`)
```python
import httpx
import secrets
from datetime import datetime, timezone, timedelta
from app.core.config import settings
from app.utils.logger import logger

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"  # OpenID Connect

# In-memory state store (use Redis in production)
_state_store: dict = {}

def generate_oauth_state(user_id: str) -> str:
    state = secrets.token_urlsafe(32)
    _state_store[state] = {
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    return state

def verify_oauth_state(state: str) -> str | None:
    """Returns user_id if state is valid, else None."""
    entry = _state_store.pop(state, None)
    if not entry:
        return None
    if datetime.now(timezone.utc) > entry["expires_at"]:
        return None
    return entry["user_id"]

def build_auth_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": "openid profile w_member_social"
    }
    from urllib.parse import urlencode
    return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"

async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()  # { access_token, expires_in, ... }

async def fetch_linkedin_profile(access_token: str) -> dict:
    """Fetch user's LinkedIn URN and basic info using OpenID userinfo endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LINKEDIN_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()
        # data contains: sub (LinkedIn URN), name, email, picture
        return {
            "linkedin_id": data.get("sub"),  # urn:li:person:xxx
            "name": data.get("name"),
            "email": data.get("email"),
            "picture": data.get("picture")
        }
```

---

## LinkedIn Publisher (`app/services/platforms/linkedin/publish.py`)
```python
import httpx
from app.utils.logger import logger

LINKEDIN_SHARE_URL = "https://api.linkedin.com/v2/ugcPosts"

class LinkedInPublisher:
    async def publish(self, access_token: str, author_urn: str, content: str) -> dict:
        """
        Post text content to LinkedIn using UGC Post API.
        Returns { platform_post_id }.
        """
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LINKEDIN_SHARE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                }
            )
            
            if response.status_code == 201:
                post_id = response.headers.get("x-restli-id", "")
                logger.info("LinkedIn post published", post_id=post_id)
                return {"platform_post_id": post_id}
            
            logger.error("LinkedIn publish failed", 
                        status=response.status_code, 
                        body=response.text)
            raise Exception(f"LinkedIn API error: {response.status_code} - {response.text}")

    async def verify_token(self, access_token: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
        except Exception:
            return False
```

---

## LinkedIn Formatter (`app/services/platforms/linkedin/formatter.py`)
```python
import re

MAX_POST_LENGTH = 3000  # LinkedIn limit

class LinkedInFormatter:
    def format(self, content: str) -> str:
        # Ensure line breaks are correct (LinkedIn uses \n)
        formatted = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines (max 2 consecutive)
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        # Trim leading/trailing whitespace
        formatted = formatted.strip()
        
        # Truncate if over LinkedIn limit
        if len(formatted) > MAX_POST_LENGTH:
            formatted = formatted[:MAX_POST_LENGTH - 3] + "..."
        
        return formatted
```

---

## Integration Service (`app/services/integration_service.py`)
```python
from app.services.platforms.linkedin.auth import (
    generate_oauth_state, verify_oauth_state, 
    build_auth_url, exchange_code_for_token, fetch_linkedin_profile
)
from app.core.encryption import encrypt_token, decrypt_token
from app.repositories.user_repository import UserRepository
from app.core.exceptions import AppException
from datetime import datetime, timezone, timedelta

class IntegrationService:
    def __init__(self):
        self.user_repo = UserRepository()

    def get_linkedin_auth_url(self, user_id: str) -> str:
        state = generate_oauth_state(user_id)
        return build_auth_url(state)

    async def handle_linkedin_callback(self, code: str, state: str) -> str:
        """Returns redirect URL for frontend."""
        user_id = verify_oauth_state(state)
        if not user_id:
            raise AppException("INVALID_OAUTH_STATE", "OAuth state invalid or expired.", 400)

        # Exchange code for token
        token_data = await exchange_code_for_token(code)
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 5183999)  # ~60 days default

        # Fetch LinkedIn profile
        profile = await fetch_linkedin_profile(access_token)

        # Encrypt token before storing
        encrypted_token = encrypt_token(access_token)
        
        now = datetime.now(timezone.utc)
        integration_data = {
            "linkedin_id": profile["linkedin_id"],
            "access_token": encrypted_token,
            "token_expires_at": now + timedelta(seconds=expires_in),
            "connected": True,
            "connected_at": now
        }
        
        await self.user_repo.update_linkedin_integration(user_id, integration_data)
        
        # Return frontend redirect URL
        return f"{settings.FRONTEND_URL}/dashboard?linkedin=connected"

    async def disconnect_linkedin(self, user_id: str) -> None:
        await self.user_repo.update_linkedin_integration(user_id, {
            "linkedin_id": None,
            "access_token": None,
            "token_expires_at": None,
            "connected": False,
            "connected_at": None
        })

    async def get_decrypted_linkedin_token(self, user_id: str) -> str:
        user = await self.user_repo.find_by_id(user_id)
        linkedin = user.get("integrations", {}).get("linkedin", {})
        
        if not linkedin.get("connected"):
            raise AppException("LINKEDIN_NOT_CONNECTED", 
                             "Connect your LinkedIn account first.", 400)
        
        # Check token expiry
        expires_at = linkedin.get("token_expires_at")
        if expires_at:
            from dateutil.parser import parse
            if isinstance(expires_at, str):
                expires_at = parse(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= expires_at:
                raise AppException("LINKEDIN_TOKEN_EXPIRED",
                                 "LinkedIn token expired. Please reconnect.", 401)
        
        return decrypt_token(linkedin["access_token"])
```

---

## Publish Service (`app/services/publish_service.py`)
```python
from datetime import datetime, timezone
from bson import ObjectId
from app.services.integration_service import IntegrationService
from app.services.platforms.linkedin.publish import LinkedInPublisher
from app.services.platforms.linkedin.formatter import LinkedInFormatter
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.core.exceptions import AppException
from app.utils.logger import logger

class PublishService:
    def __init__(self):
        self.integration_service = IntegrationService()
        self.linkedin_publisher = LinkedInPublisher()
        self.linkedin_formatter = LinkedInFormatter()
        self.post_repo = PostRepository()
        self.user_repo = UserRepository()

    async def publish_post(self, user_id: str, post_id: str) -> dict:
        # 1. Get post
        post = await self.post_repo.find_by_id(post_id)
        if not post or post["user_id"] != user_id:
            raise AppException("POST_NOT_FOUND", "Post not found.", 404)
        
        if post["status"] == "posted":
            raise AppException("ALREADY_POSTED", "This post has already been published.", 400)

        platform = post.get("platform", "linkedin")

        # 2. Mark as publishing
        await self.post_repo.update_status(post_id, "publishing")

        try:
            if platform == "linkedin":
                result = await self._publish_to_linkedin(user_id, post)
            else:
                raise AppException("UNSUPPORTED_PLATFORM", f"Platform {platform} not supported.", 400)

            # 3. Mark as posted
            await self.post_repo.update_status(post_id, "posted", {
                "posted_at": datetime.now(timezone.utc),
                "platform_post_ids": result
            })
            
            logger.info("Post published", post_id=post_id, platform=platform)
            return {"message": "Post published successfully.", "platform_post_ids": result}

        except AppException:
            await self.post_repo.update_status(post_id, "generated")  # revert
            raise
        except Exception as e:
            await self.post_repo.update_status(post_id, "failed", {
                "error_log": [str(e)]
            })
            raise AppException("PUBLISH_FAILED", f"Failed to publish: {str(e)}", 500)

    async def _publish_to_linkedin(self, user_id: str, post: dict) -> dict:
        # Get decrypted token
        token = await self.integration_service.get_decrypted_linkedin_token(user_id)
        
        # Get LinkedIn URN
        user = await self.user_repo.find_by_id(user_id)
        author_urn = user["integrations"]["linkedin"]["linkedin_id"]
        
        # Format content
        formatted_content = self.linkedin_formatter.format(post["content"])
        
        # Publish
        result = await self.linkedin_publisher.publish(token, author_urn, formatted_content)
        return {"linkedin": result["platform_post_id"]}
```

---

## Integrations + Publish Routers
```python
# app/api/v1/routes/integrations.py
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from app.services.integration_service import IntegrationService
from app.dependencies.auth import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("/linkedin/connect")
async def linkedin_connect(
    current_user: dict = Depends(get_current_user),
    service: IntegrationService = Depends(IntegrationService)
):
    auth_url = service.get_linkedin_auth_url(current_user["id"])
    return RedirectResponse(url=auth_url)

@router.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    state: str,
    service: IntegrationService = Depends(IntegrationService)
):
    redirect_url = await service.handle_linkedin_callback(code, state)
    return RedirectResponse(url=redirect_url)

@router.delete("/linkedin/disconnect")
async def linkedin_disconnect(
    current_user: dict = Depends(get_current_user),
    service: IntegrationService = Depends(IntegrationService)
):
    await service.disconnect_linkedin(current_user["id"])
    return {"message": "LinkedIn disconnected."}

@router.get("/status")
async def integration_status(current_user: dict = Depends(get_current_user)):
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository()
    user = await user_repo.find_by_id(current_user["id"])
    linkedin = user.get("integrations", {}).get("linkedin", {})
    return {
        "linkedin": {
            "connected": linkedin.get("connected", False),
            "connected_at": linkedin.get("connected_at")
        }
    }

# app/api/v1/routes/publish.py
from fastapi import APIRouter, Depends
from app.services.publish_service import PublishService
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/publish", tags=["Publish"])

@router.post("/{post_id}")
async def publish_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    service: PublishService = Depends(PublishService)
):
    return await service.publish_post(current_user["id"], post_id)
```

---

## Frontend Tasks

### 1. LinkedIn Connect Button (`src/components/integrations/LinkedInConnect.tsx`)
```tsx
'use client';
import { Button } from '@/components/ui/button';
import { Linkedin, CheckCircle } from 'lucide-react';

export default function LinkedInConnect({ connected }: { connected: boolean }) {
  const handleConnect = () => {
    // Redirect to backend OAuth initiation
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/integrations/linkedin/connect`;
  };

  if (connected) {
    return (
      <div className="flex items-center gap-2 text-green-600">
        <CheckCircle className="w-5 h-5" />
        <span className="text-sm font-medium">LinkedIn Connected</span>
      </div>
    );
  }

  return (
    <Button onClick={handleConnect} className="bg-[#0077B5] hover:bg-[#006097]">
      <Linkedin className="w-4 h-4 mr-2" />
      Connect LinkedIn
    </Button>
  );
}
```

### 2. Publish Button in PostOutput
```tsx
// Add to PostOutput.tsx
<Button
  onClick={() => publishPost(post.id)}
  disabled={post.status === 'posted' || publishing}
  className="bg-[#0077B5] hover:bg-[#006097]"
>
  <Linkedin className="w-4 h-4 mr-2" />
  {post.status === 'posted' ? 'Published ✓' : publishing ? 'Publishing...' : 'Post to LinkedIn'}
</Button>
```

---

## Security Considerations
- LinkedIn `access_token` MUST be AES-encrypted before storage — never plain text
- OAuth `state` token prevents CSRF — verified before token exchange
- State token expires in 10 minutes — enforced in `verify_oauth_state`
- `LINKEDIN_CLIENT_SECRET` must be server-side only — never exposed to frontend
- Token decrypted only in memory during publish — never returned in API responses
- Check token expiry before every publish attempt

---

## Environment Variables

```env
# Add to backend .env
LINKEDIN_CLIENT_ID=86xxx...
LINKEDIN_CLIENT_SECRET=xxxxx...
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/integrations/linkedin/callback
FRONTEND_URL=http://localhost:3000

# For token encryption (use same SECRET_KEY from Phase 02)
# SECRET_KEY must be exactly 32 chars
```

---

## Third-Party Services Required
| Service | Setup |
|---------|-------|
| LinkedIn Developer App | developer.linkedin.com → Create App → Request `w_member_social` scope |
| `cryptography` Python package | `pip install cryptography` |
| `python-dateutil` | `pip install python-dateutil` |

### LinkedIn App Setup:
1. Go to `developer.linkedin.com`
2. Create application
3. Add OAuth 2.0 redirect URL: `http://localhost:8000/api/v1/integrations/linkedin/callback`
4. Request products: `Sign In with LinkedIn using OpenID Connect` + `Share on LinkedIn`
5. Copy Client ID and Client Secret to `.env`

---

## Implementation Steps (Exact Order)

1. Create LinkedIn Developer App and get Client ID/Secret
2. Add all env vars to `.env` and `config.py`
3. `pip install cryptography python-dateutil`
4. Create `app/core/encryption.py` and test encrypt/decrypt roundtrip
5. Create `app/services/platforms/base_platform.py`
6. Create `app/services/platforms/linkedin/auth.py`
7. Create `app/services/platforms/linkedin/publish.py`
8. Create `app/services/platforms/linkedin/formatter.py`
9. Create `app/services/integration_service.py`
10. Create `app/services/publish_service.py`
11. Create `app/api/v1/routes/integrations.py`
12. Create `app/api/v1/routes/publish.py`
13. Register both routers in `api_router`
14. Test OAuth flow: open `localhost:8000/api/v1/integrations/linkedin/connect` → redirects to LinkedIn
15. Complete OAuth → verify token saved (encrypted) in MongoDB
16. Test `POST /publish/:post_id` → verify post appears on LinkedIn
17. Create `LinkedInConnect` component on frontend
18. Test full flow: Connect → Generate → Publish from browser
19. Commit: `git commit -m "Phase 06: LinkedIn OAuth & publishing"`

---

## Edge Cases
- LinkedIn token expires (~60 days) → user must reconnect; `check expiry` before publish
- LinkedIn API returns 429 (rate limit) → mark post as `failed`, log error
- OAuth state expired (user took > 10 min) → redirect to `/dashboard?error=oauth_timeout`
- User disconnects LinkedIn while posts are scheduled → scheduler must check token validity before publishing
- LinkedIn scope `w_member_social` not approved yet → returns 403; display clear error to user

---

## Deliverables / Checklist

- [ ] LinkedIn Developer App created with correct redirect URI
- [ ] `encrypt_token` / `decrypt_token` work (roundtrip tested)
- [ ] OAuth flow redirects correctly to LinkedIn
- [ ] Callback stores encrypted token in MongoDB
- [ ] `GET /integrations/status` returns `connected: true` after OAuth
- [ ] `POST /publish/:post_id` successfully posts to LinkedIn
- [ ] Published post appears on LinkedIn timeline
- [ ] Token expiry check prevents stale-token publish
- [ ] Frontend `LinkedInConnect` button initiates OAuth
- [ ] Publish button in PostOutput works
- [ ] Disconnect clears integration data
- [ ] LinkedIn token NEVER returned in any API response

---

## Definition of Completion
A user can connect LinkedIn via OAuth, generate a post, and click "Post to LinkedIn" to see it appear on their LinkedIn feed. The access token is encrypted in MongoDB. Expiry is checked before publishing. Disconnecting clears the integration.