"""
APScheduler configuration and job management.

WHY THIS FILE EXISTS:
- Centralizes job scheduling logic
- Single place to manage all background jobs
- Easy to add new job types (analytics, cleanup, etc.)
- Can be tested independently

WHAT IT DOES:
- Initialize APScheduler
- Define jobs (functions to run on schedule)
- Handle job lifecycle (add, remove, update)
- Implement retry logic with exponential backoff

HOW APSCHEDULER WORKS:
- In-memory job store (lives in Python process memory)
- When job triggers, it calls your function
- You can add/remove jobs dynamically
- Great for MVP on single machine

PRODUCTION SCALING:
As your system grows:
- More jobs → Use job queue (Redis + Celery)
- Multiple machines → Distributed scheduler
- Complex workflows → Apache Airflow

For now, APScheduler is perfect.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from app.utils.logger import get_logger
from app.models.schemas import PostStatus
from app.services.post_service import PostService
from app.services.auth_service import AuthService

logger = get_logger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Get the scheduler instance.

    Usage:
        scheduler = get_scheduler()
        job = scheduler.add_job(...)
    """
    if scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return scheduler


async def init_scheduler() -> AsyncIOScheduler:
    """
    Initialize APScheduler for background job management.

    Called in app.main.py when app starts.

    Returns:
        Configured AsyncIOScheduler instance
    """
    global scheduler

    try:
        logger.info("Initializing scheduler...")

        # Create scheduler with memory job store
        # MemoryJobStore = jobs stored in RAM (lost on restart, fine for MVP)
        # In production, use PersistentJobStore to survive restarts
        scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone="UTC",
        )

        # Start the scheduler
        scheduler.start()

        logger.info("✅ Scheduler initialized successfully")
        return scheduler

    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}")
        raise


async def shutdown_scheduler() -> None:
    """
    Gracefully shutdown scheduler on app shutdown.

    Called in app.main.py during shutdown.
    """
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete")


async def schedule_post(post_id: str, scheduled_time: datetime) -> None:
    """
    Register a post to be published at scheduled time.

    Called when user creates a scheduled post or during startup reload.

    Args:
        post_id: MongoDB ObjectId of post
        scheduled_time: When to publish (should be UTC datetime)
    """
    try:
        sched = get_scheduler()
        
        # Ensure scheduled_time is timezone-aware (UTC)
        if scheduled_time.tzinfo is None:
            logger.warning(f"Post {post_id} has naive datetime, treating as UTC")
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)

        # Use DateTrigger to run once at specific time
        job = sched.add_job(
            publish_post_job,
            trigger=DateTrigger(run_date=scheduled_time),
            id=f"post_{post_id}",  # Unique job ID
            args=[post_id],
            misfire_grace_time=300,  # Allow 5 min grace if server was down
            replace_existing=True,  # If job exists, replace it
        )

        logger.info(f"✅ Scheduled post {post_id} for {scheduled_time} (UTC)")
        return job

    except Exception as e:
        logger.error(f"❌ Error scheduling post {post_id}: {str(e)}")
        raise
        return job

    except Exception as e:
        logger.error(f"Error scheduling post {post_id}: {str(e)}")
        raise


async def unschedule_post(post_id: str) -> None:
    """
    Remove scheduled post from job queue.

    Called when user deletes a scheduled post.

    Args:
        post_id: MongoDB ObjectId of post
    """
    try:
        sched = get_scheduler()
        job_id = f"post_{post_id}"

        if sched.get_job(job_id):
            sched.remove_job(job_id)
            logger.info(f"Unscheduled post {post_id}")
        else:
            logger.warning(f"Job not found: {job_id}")

    except Exception as e:
        logger.error(f"Error unscheduling post {post_id}: {str(e)}")
        raise


async def publish_post_job(post_id: str) -> None:
    """
    Job executed when post is due to be published.

    This is the CORE job that publishes posts to LinkedIn.
    Handles retries with exponential backoff.

    Args:
        post_id: MongoDB ObjectId of post to publish
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
                member_id = user.get("linkedin_member_id") or user.get("linkedin_id")

                result = await publish_to_linkedin(
                    access_token=user["linkedin_access_token"],
                    linkedin_member_id=member_id,
                    content=post["content"],
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
                    # Max retries exceeded, mark as failed
                    logger.error(
                        f"❌ Failed to post {post_id} after {max_retries} retries: {str(e)}"
                    )
                    await PostService.update_post_status(
                        post_id, PostStatus.FAILED, error=str(e)
                    )
                    return
                else:
                    # Exponential backoff: 5s, 25s, 125s
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


async def publish_to_linkedin(
    access_token: str,
    linkedin_member_id: Optional[str],
    content: str,
) -> dict:
    """
    Call LinkedIn API to publish a post.

    Uses LinkedIn's /v2/ugcPosts endpoint with w_member_social scope.
    
    IMPORTANT: The author must be in format urn:li:person:<id>
    LinkedIn rejects "urn:li:person:me" format.

    Args:
        access_token: User's LinkedIn OAuth access token
        linkedin_member_id: User's LinkedIn member ID (string or urn format)
        content: Post content to publish

    Returns:
        Response from LinkedIn API containing post ID

    Raises:
        Exception: If LinkedIn API call fails
    """
    import aiohttp

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    if not linkedin_member_id:
        raise Exception("Missing LinkedIn member ID for author URN")

    # Convert to proper author URN format if needed
    if linkedin_member_id.startswith("urn:li:"):
        author_urn = linkedin_member_id
    else:
        author_urn = f"urn:li:person:{linkedin_member_id}"

    # Standard UGC Posts payload with correct author format
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

    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Posting to LinkedIn: {content[:50]}...")
            
            async with session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 201:
                    # Success - LinkedIn returns 201 Created with post ID in header
                    post_id = response.headers.get("X-LinkedIn-Id", "")
                    logger.info(f"✅ Successfully posted to LinkedIn. Post ID: {post_id}")
                    return {
                        "id": post_id,
                        "status": "posted"
                    }
                elif response.status == 401:
                    logger.error(f"❌ LinkedIn auth failed (401): Token may be expired")
                    raise Exception("LinkedIn authentication failed - token may be expired or invalid")
                elif response.status == 403:
                    logger.error(f"❌ LinkedIn permission denied (403)")
                    # Log full error for debugging
                    logger.error(f"Full error response: {response_text}")
                    
                    # Check common issues
                    if "w_member_social" in response_text or "scope" in response_text.lower():
                        raise Exception("❌ w_member_social scope not approved by LinkedIn. Check your app settings at https://www.linkedin.com/developers/apps")
                    elif "Unpermitted fields" in response_text:
                        logger.error("LinkedIn rejected the request format. This may indicate:")
                        logger.error("1. w_member_social scope is not fully approved")
                        logger.error("2. Your app hasn't been approved for member posts")
                        logger.error("3. API format may need updating for current LinkedIn version")
                        raise Exception("LinkedIn API format incompatibility - check app approval status")
                    else:
                        raise Exception(f"Permission denied: {response_text[:200]}")
                elif response.status == 422:
                    logger.error(f"❌ Validation error (422): {response_text}")
                    raise Exception(f"Invalid request format: {response_text[:200]}")
                else:
                    logger.error(f"❌ LinkedIn API error ({response.status})")
                    logger.error(f"Response: {response_text[:500]}")
                    raise Exception(f"LinkedIn API error: {response.status}")

    except aiohttp.ClientError as e:
        logger.error(f"❌ Network error posting to LinkedIn: {str(e)}")
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        # Re-raise with additional context
        logger.error(f"❌ Post to LinkedIn failed: {str(e)}")
        raise


async def load_existing_scheduled_posts() -> None:
    """
    Load all currently scheduled posts from database on startup.

    When app restarts, all jobs in memory are lost (MemoryJobStore).
    This function reloads ALL scheduled posts from database so they're not missed.

    CRITICAL: Must load ALL scheduled posts (past and future), not just ones due now.
    If we only load past posts, future posts won't be scheduled!

    Called in app.main.py after scheduler and database are initialized.

    FUTURE OPTIMIZATION:
    For production with thousands of posts:
    - Use persistent job store (PostgreSQL, etc.)
    - Jobs survive app restarts
    - Faster startup (don't reload from DB)

    For now, this is sufficient for MVP.
    """
    try:
        logger.info("Loading all scheduled posts from database...")

        # Load ALL scheduled posts (past and future)
        posts = await PostService.get_all_scheduled_posts()

        for post in posts:
            # Re-schedule each post
            await schedule_post(str(post["_id"]), post["scheduled_time"])

        logger.info(f"✅ Loaded and scheduled {len(posts)} posts")

    except Exception as e:
        logger.error(f"Error loading scheduled posts: {str(e)}")
        # Don't raise - let app continue even if this fails
