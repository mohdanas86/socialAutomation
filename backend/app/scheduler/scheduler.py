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
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from app.utils.logger import get_logger
from app.models.schemas import PostStatus
from app.services.post_service import PostService

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

    Called when user creates a scheduled post.

    Args:
        post_id: MongoDB ObjectId of post
        scheduled_time: When to publish
    """
    try:
        sched = get_scheduler()

        # Use DateTrigger to run once at specific time
        job = sched.add_job(
            publish_post_job,
            trigger=DateTrigger(run_date=scheduled_time),
            id=f"post_{post_id}",  # Unique job ID
            args=[post_id],
            misfire_grace_time=300,  # Allow 5 min grace if server was down
            replace_existing=True,  # If job exists, replace it
        )

        logger.info(f"Scheduled post {post_id} for {scheduled_time}")
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
                # TODO: Implement LinkedIn API call
                result = await publish_to_linkedin(
                    access_token=user["linkedin_access_token"],
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


async def publish_to_linkedin(access_token: str, content: str) -> dict:
    """
    Call LinkedIn API to publish a post.

    TODO: Implement actual LinkedIn API call.

    For now, this is a stub that simulates successful post.
    We'll implement the real API integration next.

    Args:
        access_token: User's LinkedIn OAuth access token
        content: Post content to publish

    Returns:
        Response from LinkedIn API containing post ID

    Raises:
        Exception: If LinkedIn API call fails
    """
    # TODO: Implement real LinkedIn API call
    # For MVP, simulate success
    logger.info(f"Publishing to LinkedIn: {content[:50]}...")

    # Simulated response
    return {"id": "urn:li:share:7001234567890", "status": "posted"}


async def load_existing_scheduled_posts() -> None:
    """
    Load all currently scheduled posts from database on startup.

    When app restarts, all jobs are lost (they're in memory).
    This function reloads jobs from database so they're not missed.

    Called in app.main.py after scheduler and database are initialized.

    FUTURE OPTIMIZATION:
    For production with thousands of posts:
    - Use persistent job store (PostgreSQL, etc.)
    - Jobs survive app restarts
    - Faster startup (don't reload from DB)

    For now, this is sufficient for MVP.
    """
    try:
        logger.info("Loading scheduled posts from database...")

        posts = await PostService.get_posts_to_schedule()

        for post in posts:
            # Re-schedule each post
            await schedule_post(str(post["_id"]), post["scheduled_time"])

        logger.info(f"Loaded {len(posts)} scheduled posts")

    except Exception as e:
        logger.error(f"Error loading scheduled posts: {str(e)}")
        # Don't raise - let app continue even if this fails
