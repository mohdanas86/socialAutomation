"""
FastAPI application initialization and startup/shutdown logic.

WHY THIS FILE EXISTS:
- Single entry point for the entire backend
- Handles app lifecycle (startup, shutdown)
- Configures CORS, middleware, error handlers
- Imports and registers all routes
- Demonstrates clean app architecture

HOW IT WORKS:
1. Create FastAPI app instance
2. Register routes
3. Setup event handlers (startup/shutdown)
4. When server starts, runs all startup handlers
5. When server stops, runs all shutdown handlers

LIFECYCLE:
┌─────────────────────────────────────┐
│ uvicorn starts FastAPI server       │
├─────────────────────────────────────┤
│ on_startup() event handler:         │
│  - Validate environment variables   │
│  - Connect to MongoDB               │
│  - Initialize APScheduler           │
│  - Load existing scheduled posts    │
├─────────────────────────────────────┤
│ Server running, handling requests   │
│ /health, /auth/*, /api/*            │
├─────────────────────────────────────┤
│ on_shutdown() event handler:        │
│  - Shutdown scheduler gracefully    │
│  - Disconnect from MongoDB          │
├─────────────────────────────────────┤
│ Server stopped                      │
└─────────────────────────────────────┘

PRODUCTION PATTERN:
All web apps follow this pattern:
- Initialize dependencies
- Configure error handling
- Setup middleware
- Start long-running services
- Graceful shutdown
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

from app.utils.config import settings, validate_settings
from app.utils.logger import get_logger, setup_logging
from app.db.mongodb import connect_to_mongo, disconnect_from_mongo, create_indexes
from app.scheduler.scheduler import init_scheduler, shutdown_scheduler, load_existing_scheduled_posts
from app.api import routes

logger = get_logger(__name__)


# ===========================
# Startup/Shutdown Handlers
# ===========================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup (before yield) and shutdown (after yield) logic.

    With this pattern:
    - Code before yield runs on startup
    - yield lets the app run
    - Code after yield runs on shutdown
    - Guaranteed to run even if app crashes
    """
    # ===== STARTUP =====
    try:
        logger.info("=" * 60)
        logger.info("Starting Social Media Automation System...")
        logger.info("=" * 60)

        # Validate all required environment variables are set
        validate_settings()
        logger.info("✅ Environment variables validated")

        # Connect to MongoDB
        await connect_to_mongo()

        # Create indexes for performance
        await create_indexes()

        # Initialize APScheduler for background jobs
        await init_scheduler()

        # Load existing scheduled posts from database
        # (so they don't get missed if app restarts)
        await load_existing_scheduled_posts()

        logger.info("=" * 60)
        logger.info("✅ System startup complete!")
        logger.info(f"Server running in {settings.app_env} mode")
        logger.info("=" * 60)

    except Exception as e:
        logger.critical(f"❌ Startup failed: {str(e)}")
        raise

    # ===== APP RUNS HERE =====
    yield

    # ===== SHUTDOWN =====
    try:
        logger.info("=" * 60)
        logger.info("Shutting down system gracefully...")
        logger.info("=" * 60)

        # Shutdown scheduler
        await shutdown_scheduler()

        # Disconnect from MongoDB
        await disconnect_from_mongo()

        logger.info("✅ System shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# ===========================
# Create FastAPI Application
# ===========================


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title=settings.app_name,
        description="Social media automation platform for scheduling and posting",
        version="0.1.0",
        openapi_url="/docs/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ===========================
    # CORS Middleware
    # ===========================
    # Allow frontend to call backend API
    # CORS = Cross-Origin Resource Sharing
    # Without this, browser blocks requests from different origins
    #
    # WHY NEEDED:
    # Frontend on localhost:3000 calling backend on localhost:8000
    # These are "different origins" by browser security rules
    # We need to explicitly allow it

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # Which origins can access
        allow_credentials=True,  # Allow cookies/auth headers
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )

    # ===========================
    # Global Error Handlers
    # ===========================

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions with consistent format."""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else None,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )

    # ===========================
    # Include Routers
    # ===========================
    # Import all routes and register them
    app.include_router(routes.router)

    return app


# Create app instance
app = create_app()


# ===========================
# Main Entry Point
# ===========================
# To run the server:
#   python -m uvicorn app.main:app --reload
#
# This starts Uvicorn (ASGI server) which:
# - Loads app from app.main.py
# - Watches for file changes (--reload)
# - Serves on http://localhost:8000
# - Auto-generates OpenAPI docs at /docs

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
