"""
EYESON - Enterprise BodyScan Platform API
Main FastAPI Application

A browser-based AI body measurement system with voice guidance.
Uses open source TTS (Kokoro-82M) and SAM-3D-Body for 3D reconstruction.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from src.api import auth, health, measurements, sessions, voice, webhooks
from src.core.config import settings
from src.services.tts_service import tts_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize TTS service (open source Kokoro-82M)
    try:
        await tts_service.initialize()
        logger.info("TTS Service initialized successfully")
    except Exception as e:
        logger.error(f"TTS Service initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EYESON API")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    EYESON BodyScan API - Enterprise-grade body measurement platform.
    
    Features:
    - Browser-based 3D body scanning
    - Open source voice AI guidance (Kokoro TTS)
    - 1cm measurement accuracy with SAM-3D-Body
    - 90-second complete scan experience
    - Enterprise API with OAuth2 authentication
    """,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.is_development else "Please try again later"
        }
    )


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(sessions.router, prefix="/api/v1", tags=["Scan Sessions"])
app.include_router(measurements.router, prefix="/api/v1", tags=["Measurements"])
app.include_router(voice.router, prefix="/api/v1", tags=["Voice AI"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/api/v1/docs" if settings.is_development else None,
        "status": "operational"
    }


@app.get("/api/v1")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "health": "/api/v1/health",
            "sessions": "/api/v1/sessions",
            "measurements": "/api/v1/measurements",
            "voice": "/api/v1/voice",
            "auth": "/api/v1/auth"
        },
        "features": {
            "voice_ai": settings.tts_enabled,
            "open_source_tts": True,
            "languages": settings.supported_languages
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        workers=1 if settings.is_development else settings.workers,
        reload=settings.is_development
    )
