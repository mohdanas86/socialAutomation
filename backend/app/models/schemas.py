"""
Pydantic models for request/response validation and database schemas.

WHY THIS FILE EXISTS:
- Defines clear API contracts (what data flows in/out)
- Automatic validation (Pydantic checks types, required fields, etc.)
- Single source of truth for data shapes
- Generates OpenAPI documentation automatically
- Separates concerns: what we accept vs what we store

HOW IT WORKS:
- Request models: Used in FastAPI endpoints
- Response models: What API returns to client
- Database models: Match MongoDB collections
- Pydantic validates automatically on instantiation
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime (always serializes with +00:00)."""
    return datetime.now(timezone.utc)


# ===========================
# Enums (Fixed choices)
# ===========================


class PostStatus(str, Enum):
    """Possible post statuses."""

    DRAFT = "draft"  # Not scheduled yet
    SCHEDULED = "scheduled"  # Waiting to be posted
    POSTED = "posted"  # Successfully posted
    FAILED = "failed"  # Failed after retries
    CANCELLED = "cancelled"  # User cancelled


class PlatformType(str, Enum):
    """Supported social platforms."""

    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FACEBOOK = "facebook"


# ===========================
# Request Models (API Input)
# ===========================


class CreatePostRequest(BaseModel):
    """Request body for creating a new post."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        description="Post content/caption",
    )
    scheduled_time: datetime = Field(
        ...,
        description="When to post (ISO format)",
    )
    platform: PlatformType = Field(
        default=PlatformType.LINKEDIN,
        description="Which platform to post to",
    )

    @validator("content")
    def content_not_empty(cls, v: str) -> str:
        """Ensure content isn't just whitespace."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Excited to share my latest project!",
                "scheduled_time": "2026-05-09T10:00:00",
                "platform": "linkedin",
            }
        }


class UpdatePostRequest(BaseModel):
    """Request body for updating a post."""

    content: Optional[str] = Field(None, min_length=1, max_length=3000)
    scheduled_time: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Updated post content",
                "scheduled_time": "2026-05-09T11:00:00",
            }
        }


class LoginRequest(BaseModel):
    """OAuth login request."""

    code: str = Field(..., description="OAuth authorization code from LinkedIn")


class ScheduleOptions(BaseModel):
    preferredTime: str
    gapHours: int
    startDate: str


class AIOptions(BaseModel):
    includeHook: bool
    includeCTA: bool
    includeHashtags: bool
    includeEmojis: bool
    humanLike: bool
    conciseWriting: bool


class Constraints(BaseModel):
    minChars: int
    maxChars: int


class GeneratePostRequest(BaseModel):
    """Request body for generating posts using AI."""

    topic: str
    niche: str
    postCount: int
    targetAudience: str
    tones: List[str]
    contentGoal: str
    postStyle: str
    schedule: ScheduleOptions
    aiOptions: AIOptions
    constraints: Constraints
    keywords: List[str]
    customInstructions: str
    generatedAt: str


# ===========================
# Response Models (API Output)
# ===========================


class UserResponse(BaseModel):
    """User data returned to client (no sensitive fields)."""

    id: str = Field(..., alias="_id")
    email: str
    name: str
    linkedin_id: str
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class PostResponse(BaseModel):
    """Post data returned to client."""

    id: str = Field(..., alias="_id")
    user_id: str
    content: str
    scheduled_time: datetime
    status: PostStatus
    platform: PlatformType
    linkedin_post_id: Optional[str] = None
    retry_count: int
    last_error: Optional[str] = None
    created_at: datetime
    posted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "content": "Great post!",
                "scheduled_time": "2026-05-09T10:00:00",
                "status": "scheduled",
                "platform": "linkedin",
                "linkedin_post_id": None,
                "retry_count": 0,
                "last_error": None,
                "created_at": "2026-05-08T10:00:00",
                "posted_at": None,
            }
        }


class LoginResponse(BaseModel):
    """Response from OAuth login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    environment: str
    timestamp: datetime


# ===========================
# Database Models (MongoDB)
# ===========================
# These match our MongoDB collection structure


class UserDB(BaseModel):
    """User document in MongoDB."""

    email: str
    name: str
    linkedin_id: str
    linkedin_member_id: Optional[str] = None
    linkedin_access_token: str  # Encrypted in production
    token_expiry: datetime
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Config:
        from_attributes = True


class PostDB(BaseModel):
    """Post document in MongoDB."""

    user_id: str  # ObjectId as string
    content: str
    scheduled_time: datetime
    status: PostStatus = PostStatus.DRAFT
    platform: PlatformType = PlatformType.LINKEDIN
    linkedin_post_id: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    posted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===========================
# Utility Models
# ===========================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int


class ListResponse(BaseModel):
    """Standard list response with pagination info."""

    items: List[dict]
    total: int
    page: int
    per_page: int
