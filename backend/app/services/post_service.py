"""
Post service - handles CRUD operations and LinkedIn API integration.

WHY THIS FILE EXISTS:
- Separates business logic from API routes
- Reusable across endpoints
- Easy to test independently
- Can be called from API or scheduler

WHAT IT DOES:
- Create, read, update, delete posts
- Validate post data (length, content, time)
- Call LinkedIn API to publish posts
- Track post status and errors
- Implement retry logic

PATTERN:
Enterprise apps always separate:
- HTTP routes (receive requests, send responses)
- Services (business logic, data validation, external API calls)
- Database (storage operations)

This keeps code organized, testable, and reusable.
"""

from datetime import datetime
from typing import Optional, Dict, List
from bson import ObjectId
from app.utils.logger import get_logger
from app.models.schemas import PostDB, PostStatus, PlatformType
from app.db.mongodb import get_database
import re

logger = get_logger(__name__)


class PostService:
    """Service for managing posts and platform publishing."""

    @staticmethod
    def validate_post_content(content: str) -> None:
        """
        Validate post content before scheduling.
        
        WHY:
        - Prevent invalid posts from being scheduled
        - LinkedIn has length limits
        - Catch errors early before publishing
        - Better user experience with clear error messages
        
        Validates:
        - Content is not empty or just whitespace
        - Content meets minimum length (5 chars)
        - Content doesn't exceed maximum (3000 chars for LinkedIn)
        - Content doesn't appear to be spam
        
        Args:
            content: Post content to validate
            
        Raises:
            ValueError: If content is invalid with descriptive message
        """
        
        # Check 1: Not empty
        if not content or len(content) == 0:
            raise ValueError("Post content cannot be empty")
        
        # Check 2: Not just whitespace
        if not content.strip():
            raise ValueError("Post content cannot be only whitespace")
        
        # Check 3: Minimum length (don't allow very short posts)
        if len(content.strip()) < 5:
            raise ValueError("Post content must be at least 5 characters")
        
        # Check 4: Maximum length (LinkedIn limit)
        if len(content) > 3000:
            raise ValueError("Post content exceeds 3000 character limit for LinkedIn")
        
        # Check 5: Detect spam patterns
        # Pattern 1: All caps (likely spam)
        if len(content) > 50 and len(content.strip()) == len(content.strip().upper()):
            if not any(c.islower() for c in content):
                raise ValueError("Post appears to be spam (all caps text)")
        
        # Pattern 2: Too many URLs (likely spam or promotional)
        url_pattern = r'https?://\S+'
        urls = re.findall(url_pattern, content)
        if len(urls) > 3:
            raise ValueError("Post contains too many URLs (max 3)")
        
        logger.debug(f"Post content validation passed: {len(content)} chars")

    @staticmethod
    async def create_post(
        user_id: str,
        content: str,
        scheduled_time: datetime,
        platform: PlatformType = PlatformType.LINKEDIN,
    ) -> Dict:
        """
        Create a new scheduled post.

        Args:
            user_id: MongoDB ObjectId of user creating post
            content: Post content/caption
            scheduled_time: When to publish
            platform: Which platform (LinkedIn, Instagram, etc.)

        Returns:
            Created post document

        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate content using comprehensive validation
            PostService.validate_post_content(content)

            # Validate scheduled time is in future
            if scheduled_time <= datetime.utcnow():
                raise ValueError("Scheduled time must be in the future")

            db = get_database()
            posts_col = db["posts"]

            # Create post document
            post = PostDB(
                user_id=user_id,
                content=content,
                scheduled_time=scheduled_time,
                platform=platform,
                status=PostStatus.SCHEDULED,
            )

            result = await posts_col.insert_one(post.model_dump())
            created_post = await posts_col.find_one({"_id": result.inserted_id})

            logger.info(f"Created post {result.inserted_id} for user {user_id}")
            return created_post

        except ValueError as e:
            logger.warning(f"Invalid post data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            raise

    @staticmethod
    async def get_post(post_id: str) -> Optional[Dict]:
        """
        Get a single post by ID.

        Args:
            post_id: MongoDB ObjectId as string

        Returns:
            Post document or None
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            post = await posts_col.find_one({"_id": ObjectId(post_id)})
            return post

        except Exception as e:
            logger.error(f"Error fetching post {post_id}: {str(e)}")
            return None

    @staticmethod
    async def list_user_posts(
        user_id: str,
        status: Optional[PostStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Dict:
        """
        List posts for a user with optional filtering.

        Args:
            user_id: MongoDB ObjectId of user
            status: Filter by post status (optional)
            skip: For pagination
            limit: Max posts to return

        Returns:
            Dict with items and total count
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            # Build query
            query = {"user_id": user_id}
            if status:
                query["status"] = status.value

            # Get total count
            total = await posts_col.count_documents(query)

            # Fetch paginated results, sorted by created_at descending
            posts = []
            async for post in posts_col.find(query).sort("created_at", -1).skip(skip).limit(limit):
                posts.append(post)

            return {"items": posts, "total": total}

        except Exception as e:
            logger.error(f"Error listing posts for user {user_id}: {str(e)}")
            raise

    @staticmethod
    async def update_post(
        post_id: str,
        user_id: str,
        content: Optional[str] = None,
        scheduled_time: Optional[datetime] = None,
    ) -> Optional[Dict]:
        """
        Update a post (only if not already posted).

        Args:
            post_id: Post to update
            user_id: User making request (security check)
            content: New content (optional)
            scheduled_time: New time (optional)

        Returns:
            Updated post or None

        Raises:
            ValueError: If post already posted or user doesn't own it
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            # Verify post exists and user owns it
            post = await posts_col.find_one({"_id": ObjectId(post_id), "user_id": user_id})
            if not post:
                raise ValueError("Post not found or you don't have permission")

            # Can't edit posted content
            if post["status"] == PostStatus.POSTED.value:
                raise ValueError("Cannot edit a post that's already been posted")

            # Build update
            updates = {"updated_at": datetime.utcnow()}
            if content:
                updates["content"] = content.strip()
            if scheduled_time:
                updates["scheduled_time"] = scheduled_time

            updated_post = await posts_col.find_one_and_update(
                {"_id": ObjectId(post_id)},
                {"$set": updates},
                return_document=True,
            )

            logger.info(f"Updated post {post_id}")
            return updated_post

        except ValueError as e:
            logger.warning(f"Update validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating post: {str(e)}")
            raise

    @staticmethod
    async def delete_post(post_id: str, user_id: str) -> bool:
        """
        Delete a post (only drafts/scheduled).

        Args:
            post_id: Post to delete
            user_id: User making request

        Returns:
            True if deleted

        Raises:
            ValueError: If can't delete (already posted, wrong user, etc.)
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            # Verify ownership and status
            post = await posts_col.find_one(
                {
                    "_id": ObjectId(post_id),
                    "user_id": user_id,
                    "status": {"$in": ["draft", "scheduled", "failed"]},
                }
            )

            if not post:
                raise ValueError("Post not found, already posted, or you don't have permission")

            result = await posts_col.delete_one({"_id": ObjectId(post_id)})

            if result.deleted_count > 0:
                logger.info(f"Deleted post {post_id}")
                return True
            else:
                raise ValueError("Failed to delete post")

        except ValueError as e:
            logger.warning(f"Delete validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error deleting post: {str(e)}")
            raise

    @staticmethod
    async def get_posts_to_schedule() -> List[Dict]:
        """
        Get all posts that need to be scheduled/posted.

        Called by scheduler to find posts that are due to be published.
        Returns posts where:
        - Status is 'scheduled'
        - scheduled_time <= now
        - Not already being processed

        Returns:
            List of post documents ready to post
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            now = datetime.utcnow()

            # Find posts that should be posted now
            posts = []
            async for post in posts_col.find(
                {
                    "status": PostStatus.SCHEDULED.value,
                    "scheduled_time": {"$lte": now},
                }
            ).sort("scheduled_time", 1):
                posts.append(post)

            return posts

        except Exception as e:
            logger.error(f"Error fetching posts to schedule: {str(e)}")
            raise

    @staticmethod
    async def update_post_status(
        post_id: str,
        status: PostStatus,
        linkedin_post_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict:
        """
        Update post status after posting attempt.

        Called by scheduler after attempting to post to LinkedIn.

        Args:
            post_id: Post to update
            status: New status (posted, failed, etc.)
            linkedin_post_id: LinkedIn's unique ID for this post (if successful)
            error: Error message if failed

        Returns:
            Updated post document
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            updates = {
                "status": status.value,
                "updated_at": datetime.utcnow(),
            }

            if status == PostStatus.POSTED:
                updates["posted_at"] = datetime.utcnow()
                updates["linkedin_post_id"] = linkedin_post_id

            if error:
                updates["last_error"] = error

            updated_post = await posts_col.find_one_and_update(
                {"_id": ObjectId(post_id)},
                {"$set": updates},
                return_document=True,
            )

            logger.info(f"Updated post {post_id} status to {status.value}")
            return updated_post

        except Exception as e:
            logger.error(f"Error updating post status: {str(e)}")
            raise

    @staticmethod
    async def increment_retry_count(post_id: str) -> Dict:
        """
        Increment retry count and update last_error timestamp.

        Called each time we attempt to retry a failed post.

        Args:
            post_id: Post to update

        Returns:
            Updated post document
        """
        try:
            db = get_database()
            posts_col = db["posts"]

            updated_post = await posts_col.find_one_and_update(
                {"_id": ObjectId(post_id)},
                {
                    "$inc": {"retry_count": 1},
                    "$set": {"updated_at": datetime.utcnow()},
                },
                return_document=True,
            )

            logger.info(f"Incremented retry count for post {post_id}")
            return updated_post

        except Exception as e:
            logger.error(f"Error incrementing retry count: {str(e)}")
            raise
