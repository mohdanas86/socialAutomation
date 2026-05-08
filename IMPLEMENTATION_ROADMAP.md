# Social Media Automation Platform - Complete Implementation Roadmap

**Status**: MVP Built (Auth + Posting + Dashboard)
**Current Phase**: Stabilization and Testing
**Date Created**: May 8, 2026

---

## Table of Contents
1. [Overview](#overview)
2. [Phase 1: LinkedIn OAuth Implementation](#phase-1-linkedin-oauth-implementation)
3. [Phase 2: LinkedIn API Integration](#phase-2-linkedin-api-integration)
4. [Phase 3: Frontend Dashboard](#phase-3-frontend-dashboard)
5. [Phase 4: Testing & Validation](#phase-4-testing--validation)
6. [Phase 5: Deployment & Production Features](#phase-5-deployment--production-features)

---

## Overview

This document outlines **every step** needed to build a fully functional social media automation system. Each step includes:
- **WHY**: Purpose and business value
- **HOW**: Technical implementation details
- **MANUAL TESTING**: How to verify it works

**Estimated Timeline**: 4-6 weeks for MVP completion

---

---

# Phase 1: LinkedIn OAuth Implementation

## Step 1.1: Implement OAuth Token Exchange

### WHY
- LinkedIn OAuth is the gateway to user authentication
- Without this, users can't login and authorize the system
- Token exchange creates a secure connection to LinkedIn API
- This is the first critical user-facing feature

### HOW

**1. Implement in `auth_service.py`:**

```python
import aiohttp
from typing import Dict

@staticmethod
async def exchange_oauth_code_for_token(code: str) -> Dict:
    """
    Exchange LinkedIn OAuth code for access token.
**Use the current `publish_to_linkedin` in `app/scheduler/scheduler.py`:**

```python
async def publish_to_linkedin(
  access_token: str,
  linkedin_member_id: str,
  content: str,
) -> dict:
  url = "https://api.linkedin.com/v2/ugcPosts"

  headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0",
  }

  author_urn = (
    linkedin_member_id
    if linkedin_member_id.startswith("urn:li:")
    else f"urn:li:person:{linkedin_member_id}"
  )

  payload = {
    "author": author_urn,
    "lifecycleState": "PUBLISHED",
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareCommentary": {"text": content},
        "shareMediaCategory": "NONE",
      }
    },
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
  }
```

**In `publish_post_job`, use `linkedin_member_id` or `linkedin_id` fallback:**

```python
member_id = user.get("linkedin_member_id") or user.get("linkedin_id")
result = await publish_to_linkedin(
  access_token=user["linkedin_access_token"],
  linkedin_member_id=member_id,
  content=post["content"],
)
```
    """
    Get LinkedIn OAuth login URL for frontend.
    
    Frontend redirects user to this URL.
    User logs in on LinkedIn.
    LinkedIn redirects back to /auth/callback with code.
    """
    from urllib.parse import urlencode
    
    try:
        # OAuth parameters
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "scope": "openid profile email w_member_social",
            # scope breakdown:
            # openid/profile/email = OpenID Connect user identity
            # w_member_social = Write to member social feed (POST)
            "state": secrets.token_urlsafe(32),  # CSRF protection
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
```

### MANUAL TESTING

**Test 1: Generate OAuth URL**
```bash
curl http://localhost:8000/auth/linkedin/url

# Expected Response
{
  "login_url": "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&...",
  "client_id": "YOUR_CLIENT_ID"
}
```

**Test 2: Verify URL has required parameters**
```bash
# Copy URL and paste in browser
# Should redirect to LinkedIn login page
# OR if already logged in, ask for permission
# Then redirect back to http://localhost:8000/auth/callback?code=XXXX
```

---

## Step 1.3: Add Refresh Token Handler (Optional but Recommended)

### WHY
- LinkedIn access tokens expire
- Without refresh, users can't post after token expires
- Refresh tokens allow seamless experience without re-login

### HOW

**Add to `auth_service.py`:**

```python
@staticmethod
async def refresh_linkedin_token(refresh_token: str) -> Dict:
    """
    Refresh expired LinkedIn access token.
    
    LinkedIn tokens expire. This function gets a new one without user re-login.
    """
    try:
        url = "https://www.linkedin.com/oauth/v2/accessToken"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as response:
                if response.status != 200:
                    raise Exception("Token refresh failed")
                
                token_data = await response.json()
                
                return {
                    "access_token": token_data["access_token"],
                    "expires_in": token_data["expires_in"],
                }
    
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise


@staticmethod
async def check_and_refresh_token(user_id: str) -> Optional[str]:
    """
    Check if user's LinkedIn token expired.
    If expired, refresh it automatically.
    """
    try:
        db = get_database()
        users_col = db["users"]
        user = await users_col.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return None
        
        # Check if token expired (with 5 minute buffer)
        now = datetime.utcnow()
        buffer = timedelta(minutes=5)
        
        if user["token_expiry"] - buffer < now:
            # Token expired, refresh it
            logger.info(f"Token expired for user {user_id}, refreshing...")
            
            # This assumes LinkedIn gave us a refresh_token (requires special setup)
            # For MVP, users need to re-login
            # Later: implement refresh_token support
            return None
        
        return user["linkedin_access_token"]
    
    except Exception as e:
        logger.error(f"Error checking token: {str(e)}")
        return None
```

### MANUAL TESTING

**Test 1: Check Token Expiry Logic**
```bash
# In MongoDB, manually set a past expiry time
db.users.updateOne(
  {email: "your@email.com"},
  {$set: {token_expiry: ISODate("2020-01-01")}}
)

# Try to post, system should request re-login
```

---

# Phase 2: LinkedIn API Integration

## Step 2.1: Implement LinkedIn Post Publishing

### WHY
- This is the core feature: actually posting to LinkedIn
- Users schedule posts → scheduler publishes at time → this code runs
- Handles API calls, errors, and LinkedIn response parsing

### HOW

**Create new file `app/services/linkedin_service.py`:**

```python
"""
LinkedIn API service - handles all LinkedIn API interactions.

WHY THIS FILE EXISTS:
- Separates LinkedIn-specific logic from general post logic
- Easy to test LinkedIn calls independently
- Can add other social platforms later (different service file)
- Handles LinkedIn errors, rate limits, etc.
"""

import aiohttp
from typing import Dict, Optional
from app.utils.logger import get_logger
from app.utils.config import settings

logger = get_logger(__name__)


class LinkedInService:
    """Service for LinkedIn API interactions."""

    @staticmethod
    async def publish_post(
        access_token: str,
        content: str,
        user_linkedin_id: str,
    ) -> Dict:
        """
        Publish a post to LinkedIn.

        WHY:
        - Core feature: actually posts to LinkedIn
        - Handles authentication, formatting, error handling
        - Returns LinkedIn's post ID for tracking

        HOW:
        - LinkedIn API endpoint: POST /rest/posts
        - Authentication: Bearer token
        - Content: Formatted as LinkedIn-specific JSON

        Args:
            access_token: User's LinkedIn access token
            content: Post content/text
            user_linkedin_id: LinkedIn user ID

        Returns:
            {"id": "urn:li:share:12345..."}

        Raises:
            Exception: If LinkedIn API fails
        """
        try:
            url = "https://api.linkedin.com/v2/posts"

            # LinkedIn requires specific JSON format
            payload = {
                "author": f"urn:li:person:{user_linkedin_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.share": {
                        "shareCommentary": {
                            "text": content,
                        },
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.visibility.visibility": "PUBLIC",
                },
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            logger.info(f"Publishing post to LinkedIn (user: {user_linkedin_id})")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers=headers
                ) as response:

                    # Check response status
                    if response.status == 201:  # Created
                        response_data = await response.json()
                        post_id = response_data.get("id")

                        logger.info(f"✅ Post published successfully: {post_id}")

                        return {
                            "id": post_id,
                            "status": "published",
                        }

                    elif response.status == 401:
                        raise Exception("Unauthorized - access token may be expired")

                    elif response.status == 403:
                        raise Exception("Forbidden - user may not have posting permission")

                    elif response.status == 400:
                        error_data = await response.json()
                        raise Exception(f"Bad request: {error_data}")

                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"LinkedIn API error {response.status}: {error_text}"
                        )

        except Exception as e:
            logger.error(f"Failed to publish post: {str(e)}")
            raise

    @staticmethod
    async def delete_post(
        post_id: str,
        access_token: str,
    ) -> bool:
        """
        Delete a post from LinkedIn.

        WHY:
        - Users may want to delete posts
        - Admin may need to remove inappropriate content

        Args:
            post_id: LinkedIn post ID (urn:li:share:...)
            access_token: User's access token

        Returns:
            True if deleted successfully
        """
        try:
            url = f"https://api.linkedin.com/v2/posts/{post_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as response:

                    if response.status == 204:  # No Content (success)
                        logger.info(f"Post deleted: {post_id}")
                        return True

                    elif response.status == 401:
                        raise Exception("Unauthorized")

                    else:
                        raise Exception(f"Delete failed: {response.status}")

        except Exception as e:
            logger.error(f"Failed to delete post: {str(e)}")
            raise

    @staticmethod
    async def get_post_stats(
        post_id: str,
        access_token: str,
    ) -> Dict:
        """
        Get post statistics (likes, comments, shares).

        WHY:
        - Analytics: show users how their posts perform
        - Track engagement

        Args:
            post_id: LinkedIn post ID
            access_token: User's access token

        Returns:
            {
                "likes": 10,
                "comments": 3,
                "reposts": 1,
                "engagement": 14
            }
        """
        try:
            # LinkedIn API endpoint for analytics
            url = f"https://api.linkedin.com/v2/posts/{post_id}"

            params = {
                "projection": "(totalShareStatistics)",
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=headers
                ) as response:

                    if response.status == 200:
                        data = await response.json()

                        stats = data.get("totalShareStatistics", {})

                        return {
                            "likes": stats.get("likeCount", 0),
                            "comments": stats.get("commentCount", 0),
                            "reposts": stats.get("shareCount", 0),
                            "engagement": sum(
                                [
                                    stats.get("likeCount", 0),
                                    stats.get("commentCount", 0),
                                    stats.get("shareCount", 0),
                                ]
                            ),
                        }

                    else:
                        logger.warning(f"Could not fetch stats: {response.status}")
                        return {
                            "likes": 0,
                            "comments": 0,
                            "reposts": 0,
                            "engagement": 0,
                        }

        except Exception as e:
            logger.error(f"Error fetching post stats: {str(e)}")
            return {
                "likes": 0,
                "comments": 0,
                "reposts": 0,
                "engagement": 0,
            }
```

**Update `app/scheduler/scheduler.py` to use LinkedIn service:**

```python
# Add import at top
from app.services.linkedin_service import LinkedInService

# Update publish_to_linkedin function

async def publish_to_linkedin(access_token: str, content: str, user_linkedin_id: str) -> dict:
    """
    Call LinkedIn API to publish a post.
    
    Now uses real LinkedIn API instead of simulation.
    """
    try:
        result = await LinkedInService.publish_post(
            access_token=access_token,
            content=content,
            user_linkedin_id=user_linkedin_id,
        )
        return result
    
    except Exception as e:
        logger.error(f"LinkedIn publishing failed: {str(e)}")
        raise
```

**Update `app/scheduler/scheduler.py` publish_post_job to get user's LinkedIn ID:**

```python
async def publish_post_job(post_id: str) -> None:
    """
    Job executed when post is due to be published.
    """
    try:
        logger.info(f"Starting publish job for post {post_id}")

        # Fetch post from database
        post = await PostService.get_post(post_id)
        if not post:
            logger.error(f"Post {post_id} not found")
            return

        # Get user's LinkedIn credentials
        from app.db.mongodb import get_database
        from bson import ObjectId

        db = get_database()
        user = await db["users"].find_one({"_id": ObjectId(post["user_id"])})
        if not user:
            logger.error(f"User {post['user_id']} not found")
            await PostService.update_post_status(
                post_id, PostStatus.FAILED, error="User not found"
            )
            return

        # Try to publish with retry logic
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Call LinkedIn API to publish
                result = await LinkedInService.publish_post(
                    access_token=user["linkedin_access_token"],
                    content=post["content"],
                    user_linkedin_id=user["linkedin_id"],
                )

                # Success! Update post status
                await PostService.update_post_status(
                    post_id,
                    PostStatus.POSTED,
                    linkedin_post_id=result.get("id"),
                )

                logger.info(f"✅ Successfully posted {post_id}")
                return

            except Exception as e:
                retry_count += 1
                await PostService.increment_retry_count(post_id)

                if retry_count >= max_retries:
                    logger.error(
                        f"❌ Failed to post {post_id} after {max_retries} retries: {str(e)}"
                    )
                    await PostService.update_post_status(
                        post_id, PostStatus.FAILED, error=str(e)
                    )
                    return
                else:
                    wait_time = 5 ** retry_count
                    logger.warning(
                        f"Post {post_id} failed (attempt {retry_count}/{max_retries}). "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)

    except Exception as e:
        logger.error(f"Unexpected error in publish_post_job: {str(e)}")
        await PostService.update_post_status(
            post_id, PostStatus.FAILED, error=f"Unexpected error: {str(e)}"
        )
```

### MANUAL TESTING

**Test 1: Create a Scheduled Post**
```bash
# Get your JWT token from OAuth login
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Create post scheduled for 1 minute from now
curl -X POST http://localhost:8000/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Testing automated posting! 🚀",
    "scheduled_time": "2026-05-08T15:01:00Z",
    "platform": "linkedin"
  }'

# Expected Response (201 Created)
{
  "id": "507f1f77bcf86cd799439011",
  "user_id": "507f1f77bcf86cd799439012",
  "content": "Testing automated posting! 🚀",
  "scheduled_time": "2026-05-08T15:01:00",
  "status": "scheduled",
  "platform": "linkedin",
  "linkedin_post_id": null,
  "retry_count": 0,
  "created_at": "2026-05-08T15:00:00"
}
```

**Test 2: List Your Posts**
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/posts

# Expected Response
{
  "items": [
    {
      "id": "507f1f77bcf86cd799439011",
      "status": "scheduled",
      "content": "Testing automated posting! 🚀",
      ...
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

**Test 3: Wait for Auto-Publishing**
```bash
# Watch server logs
tail -f backend/logs/app_*.log

# Should see at scheduled time:
# INFO: Starting publish job for post 507f1f77bcf86cd799439011
# INFO: Publishing post to LinkedIn...
# INFO: ✅ Successfully posted 507f1f77bcf86cd799439011

# Check MongoDB
db.posts.findOne({_id: ObjectId("507f1f77bcf86cd799439011")})

# Should show:
# status: "posted"
# linkedin_post_id: "urn:li:share:1234567890"
# posted_at: ISODate("2026-05-08T15:01:00")
```

**Test 4: View Post on LinkedIn**
```bash
# If real LinkedIn token used:
# 1. Login to LinkedIn
# 2. Go to your profile
# 3. Should see the auto-posted post
# 4. Check post URL matches linkedin_post_id
```

**Test 5: Test Retry Logic (Simulate Failure)**
```bash
# Edit user token to invalid value to force failure
db.users.updateOne(
  {_id: ObjectId("507f1f77bcf86cd799439012")},
  {$set: {linkedin_access_token: "invalid_token"}}
)

# Create new post
# Should see retry attempts in logs:
# WARN: Post ... failed (attempt 1/3). Retrying in 5s...
# WARN: Post ... failed (attempt 2/3). Retrying in 25s...
# WARN: Post ... failed (attempt 3/3). Retrying in 125s...
# ERROR: Failed to post after 3 retries

# Check MongoDB - status should be "failed"
db.posts.findOne({...})  # status: "failed"
```

---

## Step 2.2: Add Post Content Validation

### WHY
- Prevent invalid posts from being scheduled
- LinkedIn has length limits
- Catch errors early before publishing

### HOW

**Update `app/services/post_service.py`:**

```python
@staticmethod
def validate_post_content(content: str) -> None:
    """
    Validate post content before scheduling.
    
    WHY:
    - Prevent invalid posts
    - LinkedIn has length limits
    - Catch errors early
    
    Raises:
        ValueError: If content is invalid
    """
    
    # Check length
    if len(content) == 0:
        raise ValueError("Post content cannot be empty")
    
    if len(content) > 3000:
        raise ValueError("Post content exceeds 3000 character limit")
    
    # Check not just whitespace
    if not content.strip():
        raise ValueError("Post content cannot be only whitespace")
    
    # Check for suspicious patterns
    if len(content) < 5:
        raise ValueError("Post content too short (minimum 5 characters)")
    
    # Check for spam-like patterns
    spam_patterns = [
        r"^[A-Z\s]{100,}$",  # All caps, likely spam
        r"(http|https):\/\/.*?\/.*?\/.*?\/.*?\s",  # Too many URLs
    ]
    
    for pattern in spam_patterns:
        if re.match(pattern, content):
            raise ValueError("Post content appears to be spam")

# Call this in create_post
async def create_post(...):
    # Validate content
    PostService.validate_post_content(content)
    
    # ... rest of function
```

### MANUAL TESTING

**Test 1: Empty Content**
```bash
curl -X POST http://localhost:8000/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "",
    "scheduled_time": "2026-05-09T10:00:00"
  }'

# Expected Response (400 Bad Request)
{
  "error": "Post content cannot be empty",
  "status_code": 400
}
```

**Test 2: Too Long Content**
```bash
# Create content over 3000 characters
LONG_CONTENT=$(python -c "print('a' * 3001)")

curl -X POST http://localhost:8000/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$LONG_CONTENT\", \"scheduled_time\": \"2026-05-09T10:00:00\"}"

# Expected Response (400 Bad Request)
{
  "error": "Post content exceeds 3000 character limit",
  "status_code": 400
}
```

**Test 3: Valid Content**
```bash
curl -X POST http://localhost:8000/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Just the right amount of content! 🎉",
    "scheduled_time": "2026-05-09T10:00:00"
  }'

# Expected Response (201 Created)
# Post should be created successfully
```

---

## Step 2.3: Handle LinkedIn API Rate Limiting

### WHY
- LinkedIn has rate limits (e.g., 10 posts/day for some users)
- Without handling, system could get blocked
- Need to detect and inform user

### HOW

**Update `linkedin_service.py`:**

```python
@staticmethod
async def publish_post(
    access_token: str,
    content: str,
    user_linkedin_id: str,
) -> Dict:
    """
    Publish to LinkedIn with rate limit handling.
    """
    try:
        # ... existing code ...
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers
            ) as response:
                
                # Check for rate limiting
                if response.status == 429:  # Too Many Requests
                    retry_after = response.headers.get("Retry-After", "60")
                    logger.warning(
                        f"LinkedIn rate limit hit. Retry after {retry_after}s"
                    )
                    raise Exception(
                        f"Rate limited by LinkedIn. Try again in {retry_after} seconds."
                    )
                
                # ... rest of existing code ...
    
    except Exception as e:
        logger.error(f"Failed to publish post: {str(e)}")
        raise
```

### MANUAL TESTING

**Test 1: Check Rate Limit Response**
```bash
# If you hit LinkedIn rate limit, check logs
tail -f backend/logs/app_*.log

# Should see:
# WARN: LinkedIn rate limit hit. Retry after 60s

# Check MongoDB - post status should be "failed" after retries
db.posts.findOne({...}).last_error
# "Rate limited by LinkedIn. Try again in 60 seconds."
```

---

# Phase 3: Frontend Dashboard

## Step 3.1: Setup Next.js Project

### WHY
- Dashboard is user interface
- Users need to see their posts
- Need login, create post, view posts features

### HOW

**Current Next.js project (already created):**

```bash
# In parent directory
cd front
npm install axios zustand js-cookie

# Structure
front/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # Landing page
│   ├── login/
│   │   └── page.tsx          # Login page
│   ├── dashboard/
│   │   ├── page.tsx          # Main dashboard
│   │   ├── posts/
│   │   │   └── page.tsx      # Posts list
│   │   └── create/
│   │       └── page.tsx      # Create post form
│   └── api/
│       └── auth/
│           └── callback/
│               └── route.ts  # OAuth callback handler
│
├── components/
│   ├── Navbar.tsx
│   ├── PostCard.tsx
│   ├── CreatePostForm.tsx
│   └── LoadingSpinner.tsx
│
├── lib/
│   ├── api.ts                # API client
│   ├── auth.ts               # Auth utilities
│   └── store.ts              # Zustand store
│
└── .env.local
```

### MANUAL TESTING

**Test 1: Next.js Dev Server**
```bash
npm run dev

# Expected: Server starts on http://localhost:3000
# Should see blank page (will add content)
```

---

## Step 3.2: Implement Login Flow

### WHY
- Users need to login before creating posts
- Redirect to LinkedIn OAuth
- Receive JWT token and store

### HOW

**Create `front/lib/api.ts`:**

```typescript
import axios from 'axios'
import Cookie from 'js-cookie'
import { useAuthStore } from './store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Add JWT token to requests
api.interceptors.request.use((config) => {
  const token = Cookie.get('token') || useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authAPI = {
  getLoginUrl: () => api.get('/auth/linkedin/url'),
}

export const postAPI = {
  create: (data: any) => api.post('/api/posts', data),
  list: (params?: any) => api.get('/api/posts', { params }),
  get: (id: string) => api.get(`/api/posts/${id}`),
  delete: (id: string) => api.delete(`/api/posts/${id}`),
}

export const userAPI = {
  getMe: () => api.get('/api/me'),
}
```

**Create `front/app/login/page.tsx`:**

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleLogin = async () => {
      try {
        // Get LinkedIn OAuth URL from backend
        const response = await authAPI.getLoginUrl();
        const { login_url } = response.data;

        // Redirect to LinkedIn
        window.location.href = login_url;
      } catch (err: any) {
        setError(err.message || 'Failed to initiate login');
        setLoading(false);
      }
    };

    handleLogin();
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Login Error</h1>
          <p className="mt-2 text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Redirecting to LinkedIn...</h1>
        <p className="mt-2 text-gray-600">Please wait...</p>
      </div>
    </div>
  );
}
```

**OAuth callback (current flow):**

- Backend `/auth/callback` exchanges code and redirects to
  `/dashboard?token=JWT`.
- `front/components/Providers.tsx` reads `token` from the URL, stores it in
  cookies, and fetches `/api/me` before rendering.

### MANUAL TESTING

**Test 1: Login Flow**
```bash
# Start frontend
cd front
npm run dev

# Go to http://localhost:3000/login
# Should redirect to LinkedIn login
# After login, should redirect back to dashboard
```

**Test 2: Token Storage**
```bash
# Open browser DevTools (F12)
# Go to Application → Cookies
# Should see token with value from backend

# Verify token is valid
# Go to http://localhost:8000/docs
# Paste token in Authorize field
# Should be able to call protected endpoints
```

---

## Step 3.3: Build Dashboard UI

### WHY
- Central place to manage posts
- Show list of scheduled/posted posts
- Form to create new posts

### HOW

**Create `front/components/PostCard.tsx`:**

```typescript
'use client';

import { useState } from 'react';
import { PostAPI } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

interface PostCardProps {
  post: any;
  onDelete: () => void;
}

export default function PostCard({ post, onDelete }: PostCardProps) {
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!confirm('Are you sure?')) return;

    setLoading(true);
    try {
      await postAPI.delete(post.id);
      onDelete();
    } catch (error) {
      console.error('Failed to delete post:', error);
      alert('Failed to delete post');
    } finally {
      setLoading(false);
    }
  };

  const statusColors: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800',
    posted: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    draft: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="border rounded-lg p-4 mb-4 bg-white shadow">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <p className="text-gray-700 mb-2">{post.content}</p>

          <div className="flex gap-2 items-center">
            <span
              className={`px-2 py-1 rounded text-sm font-semibold ${
                statusColors[post.status] || 'bg-gray-100'
              }`}
            >
              {post.status}
            </span>

            {post.status === 'scheduled' && (
              <span className="text-sm text-gray-600">
                Scheduled for{' '}
                {formatDistanceToNow(new Date(post.scheduled_time), {
                  addSuffix: true,
                })}
              </span>
            )}

            {post.status === 'posted' && (
              <span className="text-sm text-gray-600">
                Posted{' '}
                {formatDistanceToNow(new Date(post.posted_at), {
                  addSuffix: true,
                })}
              </span>
            )}

            {post.status === 'failed' && (
              <span className="text-sm text-red-600">{post.last_error}</span>
            )}
          </div>
        </div>

        {post.status !== 'posted' && (
          <button
            onClick={handleDelete}
            disabled={loading}
            className="ml-4 px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 disabled:opacity-50"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
```

**Create `front/components/CreatePostForm.tsx`:**

```typescript
'use client';

import { useState } from 'react';
import { postAPI } from '@/lib/api';

interface CreatePostFormProps {
  onSuccess: () => void;
}

export default function CreatePostForm({ onSuccess }: CreatePostFormProps) {
  const [content, setContent] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await postAPI.create({
        content,
        scheduled_time: new Date(scheduledTime).toISOString(),
        platform: 'linkedin',
      });

      setContent('');
      setScheduledTime('');
      onSuccess();
      alert('Post scheduled successfully!');
    } catch (err: any) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white border rounded-lg p-6 mb-6 shadow"
    >
      <h2 className="text-xl font-bold mb-4">Create New Post</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-gray-700 font-semibold mb-2">
          Content
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="What's on your mind?"
          className="w-full border rounded px-3 py-2 h-24 focus:outline-none focus:border-blue-500"
          required
        />
        <p className="text-gray-600 text-sm mt-1">
          {content.length}/3000 characters
        </p>
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 font-semibold mb-2">
          Schedule For (Optional)
        </label>
        <input
          type="datetime-local"
          value={scheduledTime}
          onChange={(e) => setScheduledTime(e.target.value)}
          className="w-full border rounded px-3 py-2 focus:outline-none focus:border-blue-500"
        />
        <p className="text-gray-600 text-sm mt-1">
          Leave empty to post immediately
        </p>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white font-semibold py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Posting...' : 'Schedule Post'}
      </button>
    </form>
  );
}
```

**Create `front/app/dashboard/page.tsx`:**

Current dashboard uses `useAuthStore` + `usePostStore` and relies on
`front/components/Providers.tsx` to initialize auth from the `token` query
parameter and cookies before rendering.

### MANUAL TESTING

**Test 1: Dashboard Loads**
```bash
# After OAuth callback
# Should see dashboard with welcome message
# Should see "Your Posts" section
```

**Test 2: Create Post Form**
```bash
# Fill in content
# Set scheduled time (tomorrow at 10 AM)
# Click "Schedule Post"
# Should see post appear in list with "scheduled" status
```

**Test 3: View Posts**
```bash
# Posts should display with:
# - Content
# - Status badge (scheduled/posted/failed)
# - Delete button (for non-posted posts)
```

---

# Phase 4: Testing & Validation

## Step 4.1: Manual End-to-End Testing

### WHY
- Verify entire system works together
- Catch integration bugs
- Build confidence before deployment

### HOW & MANUAL TESTING

**Test Scenario: Complete Post Scheduling Flow**

```bash
# Step 1: Start backend
cd backend
python -m uvicorn app.main:app --reload

# Expected: Server starts on http://localhost:8000

# Step 2: Start frontend
cd front
npm run dev

# Expected: Frontend on http://localhost:3000

# Step 3: Login
# Go to http://localhost:3000
# Click "Login with LinkedIn"
# Authorize app
# Redirected back to dashboard

# Step 4: Create Post
# Enter content: "Testing social automation platform!"
# Schedule for 2 minutes from now
# Click "Schedule Post"

# Verify in UI:
# Post appears in list
# Status shows "scheduled"
# Time shows "scheduled for X minutes from now"

# Step 5: Wait for Auto-Publish
# Watch server logs
# tail -f backend/logs/app_*.log

# Should see:
# INFO: Starting publish job for post [id]
# INFO: Publishing post to LinkedIn...
# INFO: ✅ Successfully posted [id]

# Step 6: Verify in Dashboard
# Refresh page (or wait for auto-refresh)
# Post status should change from "scheduled" to "posted"
# Posted time shown

# Step 7: Verify on LinkedIn
# Login to LinkedIn
# Go to profile
# Should see the new post!
# Posted content should match exactly
```

**Test Scenario: Handle Failure and Retry**

```bash
# Step 1: Create post with fake LinkedIn token
# Edit MongoDB:
db.users.updateOne(
  {email: "your@email.com"},
  {$set: {linkedin_access_token: "fake_token_12345"}}
)

# Step 2: Create and schedule post

# Step 3: Watch logs as it fails and retries
# tail -f backend/logs/app_*.log

# Should see:
# WARN: Post ... failed (attempt 1/3). Retrying in 5s...
# WARN: Post ... failed (attempt 2/3). Retrying in 25s...
# WARN: Post ... failed (attempt 3/3). Retrying in 125s...
# ERROR: ❌ Failed to post after 3 retries

# Step 4: Check MongoDB
db.posts.findOne({_id: ObjectId("...")})

# Should show:
# status: "failed"
# last_error: "LinkedIn API error 401: Unauthorized"
# retry_count: 3

# Step 5: Fix token and retry manually
# For now: need to implement manual retry button (Phase 5 feature)
```

**Test Scenario: Update and Delete Posts**

```bash
# Test updating scheduled post
TOKEN="eyJ..."

# Update content before scheduled time
curl -X PUT http://localhost:8000/api/posts/[POST_ID] \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated content!"}'

# Expected: Post content updated in DB and UI

# Test deleting scheduled post
curl -X DELETE http://localhost:8000/api/posts/[POST_ID] \
  -H "Authorization: Bearer $TOKEN"

# Expected: Post removed from DB and UI

# Try deleting posted post (should fail)
# Status should be "posted"
# Expected: 400 Bad Request - "Cannot delete a post that's already been posted"
```

## Step 4.2: Automated Testing

### WHY
- Manual testing doesn't scale
- Automated tests catch regressions
- Continuous validation

### HOW

**Create `backend/tests/test_auth.py`:**

```python
import pytest
from app.services.auth_service import AuthService
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_create_access_token():
    """Test JWT token creation."""
    user_id = "507f1f77bcf86cd799439011"
    token = AuthService.create_access_token(user_id)
    
    # Token should be a string
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Token should be verifiable
    verified_id = AuthService.verify_token(token)
    assert verified_id == user_id


@pytest.mark.asyncio
async def test_verify_expired_token():
    """Test that expired tokens are rejected."""
    user_id = "507f1f77bcf86cd799439011"
    
    # Create token that expires immediately
    token = AuthService.create_access_token(
        user_id,
        expires_delta=timedelta(seconds=-1)
    )
    
    # Should return None (invalid)
    verified_id = AuthService.verify_token(token)
    assert verified_id is None


@pytest.mark.asyncio
async def test_invalid_token():
    """Test that invalid tokens are rejected."""
    invalid_token = "not.a.valid.token"
    
    verified_id = AuthService.verify_token(invalid_token)
    assert verified_id is None
```

**Run tests:**

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run tests
pytest backend/tests/

# Output should show all tests passing
```

### MANUAL TESTING

**Test 1: Run All Tests**
```bash
cd backend
pytest tests/ -v

# Expected:
# test_auth.py::test_create_access_token PASSED
# test_auth.py::test_verify_expired_token PASSED
# test_auth.py::test_invalid_token PASSED

# All tests should pass
```

---

# Phase 5: Deployment & Production Features

## Step 5.1: Docker Containerization

### WHY
- Reproducible environments
- Easy deployment anywhere
- Consistent across machines

### HOW

**Dockerfile already created, build it:**

```bash
# From backend directory
docker build -t social-automation:latest .

# Run container
docker run -p 8000:8000 \
  -e MONGODB_URL="mongodb+srv://..." \
  -e LINKEDIN_CLIENT_ID="..." \
  -e LINKEDIN_CLIENT_SECRET="..." \
  -e JWT_SECRET_KEY="..." \
  social-automation:latest

# Expected: Server runs on http://localhost:8000
```

### MANUAL TESTING

**Test 1: Build Docker Image**
```bash
docker build -t social-automation:latest .

# Should complete without errors
# Shows "Successfully tagged social-automation:latest"
```

**Test 2: Run Container**
```bash
docker run -p 8000:8000 \
  -e MONGODB_URL="..." \
  social-automation:latest

# Expected: Server starts
# Verify: http://localhost:8000/health
```

---

## Step 5.2: Add Manual Retry Feature

### WHY
- Failed posts can be retried manually
- Users shouldn't wait for automatic retry schedule
- Improves user experience

### HOW

**Add endpoint to `routes.py`:**

```python
@router.post("/api/posts/{post_id}/retry")
async def retry_failed_post(
    post_id: str,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Manually retry a failed post.
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
                detail="Not authorized",
            )
        
        # Only retry failed posts
        if post["status"] != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed posts can be retried",
            )
        
        # Reset status to scheduled
        await PostService.update_post_status(post_id, PostStatus.SCHEDULED)
        
        # Re-schedule the job
        from app.scheduler.scheduler import schedule_post
        await schedule_post(post_id, post["scheduled_time"])
        
        logger.info(f"Post {post_id} retried by user {current_user}")
        
        return {"message": "Post queued for retry"}
    
    except Exception as e:
        logger.error(f"Error retrying post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry post",
        )
```

### MANUAL TESTING

**Test 1: Retry Failed Post**
```bash
# Create a post that will fail (use invalid token)
# Wait for it to reach "failed" status

TOKEN="eyJ..."
POST_ID="507f1f77bcf86cd799439011"

# Retry the post
curl -X POST http://localhost:8000/api/posts/$POST_ID/retry \
  -H "Authorization: Bearer $TOKEN"

# Expected Response
{
  "message": "Post queued for retry"
}

# In dashboard, post status should change back to "scheduled"
```

**Test 2: Try Retry on Non-Failed Post**
```bash
# Try to retry a "posted" post
curl -X POST http://localhost:8000/api/posts/[POSTED_POST_ID]/retry \
  -H "Authorization: Bearer $TOKEN"

# Expected Response (400)
{
  "error": "Only failed posts can be retried",
  "status_code": 400
}
```

---

## Step 5.3: Add Analytics Endpoint

### WHY
- Show users post performance
- LinkedIn engagement metrics
- Track system effectiveness

### HOW

**Add endpoint to `routes.py`:**

```python
@router.get("/api/posts/{post_id}/stats")
async def get_post_stats(
    post_id: str,
    authorization: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Get post performance statistics from LinkedIn.
    """
    try:
        post = await PostService.get_post(post_id)
        
        if not post or post["status"] != "posted":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or not yet posted",
            )
        
        if post["user_id"] != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )
        
        # Get user credentials
        db = get_database()
        user = await db["users"].find_one({"_id": ObjectId(current_user)})
        
        # Fetch stats from LinkedIn
        from app.services.linkedin_service import LinkedInService
        
        stats = await LinkedInService.get_post_stats(
            post_id=post["linkedin_post_id"],
            access_token=user["linkedin_access_token"],
        )
        
        return {
            "post_id": post_id,
            "likes": stats["likes"],
            "comments": stats["comments"],
            "reposts": stats["reposts"],
            "engagement": stats["engagement"],
        }
    
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post statistics",
        )
```

### MANUAL TESTING

**Test 1: Get Post Stats**
```bash
TOKEN="eyJ..."
POST_ID="507f1f77bcf86cd799439011"  # Must be a posted post

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/posts/$POST_ID/stats

# Expected Response
{
  "post_id": "507f1f77bcf86cd799439011",
  "likes": 5,
  "comments": 2,
  "reposts": 1,
  "engagement": 8
}
```

---

## Step 5.4: Deploy to Production

### WHY
- Make system accessible online
- Test real-world scenarios
- Go live!

### HOW

**Deploy to Railway (Recommended for beginners):**

```bash
# 1. Create Railway account at https://railway.app

# 2. Install Railway CLI
npm i -g @railway/cli

# 3. Login to Railway
railway login

# 4. Create new project
railway init

# 5. Add MongoDB Atlas connection
# In Railway dashboard:
# - Add MongoDB service
# - Connect to Atlas (provide connection string)

# 6. Deploy backend
railway up

# 7. Set environment variables in Railway dashboard:
MONGODB_URL=mongodb+srv://...
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
JWT_SECRET_KEY=...

# 8. Update front .env with production API URL
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app

# 9. Deploy frontend (Vercel recommended)
# Push to GitHub
# Connect to Vercel
# Auto-deploys on push
```

### MANUAL TESTING

**Test 1: Production Health Check**
```bash
curl https://your-railway-url.railway.app/health

# Expected Response
{
  "status": "healthy",
  "environment": "production",
  "timestamp": "2026-05-08T..."
}
```

**Test 2: End-to-End Production Test**
```bash
# Go to frontend URL (Vercel)
# Login with LinkedIn
# Create and schedule post
# Wait for auto-publish
# Verify on LinkedIn

# Everything should work as in local environment
```

---

# Summary Table

| Phase | Step | Task                     | Estimated Time   | Status     |
| ----- | ---- | ------------------------ | ---------------- | ---------- |
| 1     | 1.1  | OAuth Token Exchange     | 2-3 hours        | ⏳ Ready    |
| 1     | 1.2  | OAuth URL Generation     | 30 min           | ⏳ Ready    |
| 1     | 1.3  | Refresh Token Handler    | 1 hour           | ⏳ Optional |
| 2     | 2.1  | LinkedIn Post Publishing | 3 hours          | ⏳ Ready    |
| 2     | 2.2  | Post Content Validation  | 1 hour           | ⏳ Ready    |
| 2     | 2.3  | Rate Limit Handling      | 1 hour           | ⏳ Ready    |
| 3     | 3.1  | Next.js Setup            | 30 min           | ⏳ Ready    |
| 3     | 3.2  | Login Flow               | 2 hours          | ⏳ Ready    |
| 3     | 3.3  | Dashboard UI             | 4 hours          | ⏳ Ready    |
| 4     | 4.1  | Manual E2E Testing       | 2 hours          | ⏳ Ready    |
| 4     | 4.2  | Automated Testing        | 2 hours          | ⏳ Ready    |
| 5     | 5.1  | Docker Containerization  | 1 hour           | ⏳ Ready    |
| 5     | 5.2  | Manual Retry Feature     | 1 hour           | ⏳ Ready    |
| 5     | 5.3  | Analytics Endpoint       | 1 hour           | ⏳ Ready    |
| 5     | 5.4  | Production Deployment    | 2 hours          | ⏳ Ready    |
|       |      | **TOTAL**                | **~28-30 hours** |            |

---

# Implementation Priority

## Must-Have (MVP)
1. Step 1.1 - OAuth Token Exchange
2. Step 2.1 - LinkedIn Post Publishing
3. Step 3.1-3.3 - Frontend Dashboard
4. Step 4.1 - Manual E2E Testing

## Should-Have (Phase 1.5)
5. Step 2.2 - Post Validation
6. Step 5.1 - Docker
7. Step 5.4 - Deployment

## Nice-to-Have (Phase 2)
8. Step 1.3 - Refresh Token
9. Step 2.3 - Rate Limiting
10. Step 4.2 - Automated Testing
11. Step 5.2 - Manual Retry
12. Step 5.3 - Analytics

---

# Next Steps

1. **Start with Phase 1, Step 1.1** - Implement OAuth token exchange
2. Follow the HOW section precisely
3. Test manually after each step
4. Move to next step only when current step passes all manual tests
5. Document any issues or blockers

Good luck! You now have a complete roadmap! 🚀
