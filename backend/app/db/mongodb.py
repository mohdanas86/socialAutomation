"""Database connection and utilities.

WHY THIS FILE EXISTS:
- Centralized MongoDB connection management
- Connection pooling prevents connection leaks
- Async operations via Motor
- Easy to add caching/middleware later

HOW IT WORKS:
- motor.AsyncIOMotorClient creates async MongoDB connection
- Connection pooled for efficiency (reuse connections)
- get_db() returns database instance
- Collections accessed via db['collection_name']

PRODUCTION TIP:
Connection pooling is critical:
- Each connection uses memory
- Without pooling, would create 1000s of connections
- Motor handles this automatically
- Max pool size defaults to 50 (sufficient for MVP)
"""

import motor.motor_asyncio
from pymongo.errors import ServerSelectionTimeoutError
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global database instance
db_client: motor.motor_asyncio.AsyncIOMotorClient = None
db: motor.motor_asyncio.AsyncIOMotorDatabase = None


async def connect_to_mongo() -> None:
    """
    Connect to MongoDB Atlas on app startup.

    Called in app.main.py before starting FastAPI server.
    """
    global db_client, db

    try:
        logger.info("Connecting to MongoDB...")

        # Create async MongoDB client
        db_client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=50,  # Connection pool size
            minPoolSize=10,  # Minimum connections to maintain
            serverSelectionTimeoutMS=5000,  # Fail fast if server unreachable
        )

        # Get database instance
        db = db_client[settings.mongodb_db_name]

        # Verify connection works
        await db.command("ping")

        logger.info(f"✅ Connected to MongoDB: {settings.mongodb_db_name}")

    except ServerSelectionTimeoutError:
        logger.error("❌ Failed to connect to MongoDB. Check MONGODB_URL in .env")
        raise
    except Exception as e:
        logger.error(f"❌ MongoDB connection error: {str(e)}")
        raise


async def disconnect_from_mongo() -> None:
    """
    Close MongoDB connection on app shutdown.

    Called in app.main.py during shutdown.
    """
    global db_client

    if db_client:
        db_client.close()
        logger.info("Disconnected from MongoDB")


def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """
    Get database instance for use in routes/services.

    Usage in any file:
        from app.db.mongodb import get_database
        db = get_database()
        users = await db['users'].find_one({'email': 'user@example.com'})

    Returns:
        Motor AsyncIOMotorDatabase instance
    """
    if db is None:
        raise RuntimeError("Database not connected. Call connect_to_mongo() first.")
    return db


# Convenience collection getters
async def get_users_collection():
    """Get users collection."""
    return get_database()["users"]


async def get_posts_collection():
    """Get posts collection."""
    return get_database()["posts"]


async def create_indexes() -> None:
    """
    Create database indexes for performance.

    Indexes make queries faster, especially important for:
    - Finding user by email (frequent operation)
    - Querying posts by user_id and scheduled_time (scheduler uses this)
    - Pagination by created_at

    Called once on app startup.
    """
    try:
        db = get_database()

        logger.info("Creating database indexes...")

        # Users collection indexes
        users_col = db["users"]
        await users_col.create_index("email", unique=True)
        await users_col.create_index("linkedin_id", unique=True)

        # Posts collection indexes
        posts_col = db["posts"]
        await posts_col.create_index("user_id")
        await posts_col.create_index([("user_id", 1), ("created_at", -1)])
        await posts_col.create_index("scheduled_time")
        await posts_col.create_index("status")
        await posts_col.create_index([("status", 1), ("scheduled_time", 1)])

        logger.info("✅ Database indexes created successfully")

    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise
