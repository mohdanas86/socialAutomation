"""
LinkedIn API service - handles all LinkedIn API interactions.

WHY THIS FILE EXISTS:
- Separates LinkedIn-specific logic from general post logic
- Easy to test LinkedIn calls independently
- Can add other social platforms later (different service file)
- Handles LinkedIn errors, rate limits, etc.

WHAT IT DOES:
- Publishes posts to LinkedIn
- Deletes posts from LinkedIn
- Fetches post statistics (engagement)
- Handles LinkedIn API errors and rate limiting
"""

import aiohttp
import json
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
            user_linkedin_id: LinkedIn user ID (from OAuth)

        Returns:
            {"id": "urn:li:share:12345..."}

        Raises:
            Exception: If LinkedIn API fails
        """
        try:
            url = "https://api.linkedin.com/v2/posts"

            # LinkedIn requires specific JSON format for posting
            # "author" identifies who's posting (the user)
            # "specificContent" contains the actual post content
            # "visibility" controls who can see it (PUBLIC = everyone)
            
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
                    if response.status == 201:  # Created - success!
                        response_data = await response.json()
                        post_id = response_data.get("id")

                        logger.info(f"✅ Post published successfully: {post_id}")

                        return {
                            "id": post_id,
                            "status": "published",
                        }

                    elif response.status == 401:
                        # Unauthorized - token may be expired
                        raise Exception("Unauthorized - access token may be expired or invalid")

                    elif response.status == 403:
                        # Forbidden - user may not have posting permission
                        raise Exception("Forbidden - user may not have posting permission")

                    elif response.status == 400:
                        # Bad request - something wrong with our request
                        error_data = await response.json()
                        raise Exception(f"Bad request: {error_data}")

                    elif response.status == 429:
                        # Rate limited - too many requests
                        retry_after = response.headers.get("Retry-After", "60")
                        raise Exception(
                            f"Rate limited by LinkedIn. Try again in {retry_after} seconds."
                        )

                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"LinkedIn API error {response.status}: {error_text}"
                        )

        except aiohttp.ClientError as e:
            # Network error
            logger.error(f"Network error publishing post: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
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

        Raises:
            Exception: If deletion fails
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
                        logger.info(f"✅ Post deleted: {post_id}")
                        return True

                    elif response.status == 401:
                        raise Exception("Unauthorized")

                    elif response.status == 404:
                        raise Exception(f"Post not found: {post_id}")

                    else:
                        error_text = await response.text()
                        raise Exception(f"Delete failed: {response.status} - {error_text}")

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
        - Measure automation effectiveness

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
