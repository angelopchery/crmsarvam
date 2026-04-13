"""
Main FastAPI application for CRMSarvam.

A production-grade CRM + ERP hybrid system with AI-powered transcription.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, init_db
from app.routers import auth, users, clients, events, intelligence
from app.services.user_service import UserService
from app.schemas.user import UserCreate

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting CRMSarvam application...")
    logger.info(f"Application: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Ensure upload directory exists
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory: {upload_dir.absolute()}")

    # Note: Database initialization is handled by Alembic migrations
    # In production, run: alembic upgrade head
    logger.info("Database migrations should have been run during container startup")

    # Create default admin user if no users exist
    # This is wrapped in try/except in case tables don't exist yet
    async for db in get_db():
        try:
            # First check if users table exists by trying to query it
            result = await db.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'users'"))
            table_exists = result.scalar_one_or_none()

            if table_exists:
                user_service = UserService(db)
                user_count = await user_service.count_users()
                if user_count == 0:
                    logger.info("No users found. Creating default admin user...")
                    try:
                        default_admin = UserCreate(
                            username="admin",
                            password="admin123",
                            role="admin"
                        )
                        await user_service.create_user(default_admin)
                        logger.info("Default admin user created: username='admin', password='admin123'")
                        logger.warning("Please change the default admin password after first login!")
                    except Exception as e:
                        logger.error(f"Failed to create default admin user: {e}")
            else:
                logger.warning("Users table does not exist. Skipping default admin creation.")
                logger.warning("Please ensure database migrations have been run: alembic upgrade head")
        except ProgrammingError as e:
            logger.warning(f"Database table check failed (migrations may not have run yet): {e}")
            logger.warning("Default admin user creation will be skipped.")
        except Exception as e:
            logger.error(f"Unexpected error during startup user check: {e}")
        finally:
            await db.close()
        break

    yield

    # Shutdown
    logger.info("Shutting down CRMSarvam application...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="CRM + ERP hybrid system with AI-powered transcription and task intelligence",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
upload_dir = Path(settings.UPLOAD_DIR)
if upload_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(clients.poc_router)
app.include_router(events.router)
app.include_router(intelligence.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "database": "configured (check connection)",
        "transcription": "configured (check Sarvam AI API key)",
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled exception: {exc}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
