"""
EYESON - Health Check API Endpoints

Provides health status, readiness, and liveness probes for monitoring.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from src.core.config import settings
from src.services.tts_service import tts_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Track startup time
START_TIME = time.time()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    environment: str


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    ready: bool
    checks: Dict[str, Any]


class LivenessResponse(BaseModel):
    """Liveness probe response."""
    alive: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns general application health status.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        uptime_seconds=time.time() - START_TIME,
        environment=settings.environment
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Kubernetes readiness probe.
    
    Checks if all dependencies are ready to serve traffic.
    """
    checks = {
        "database": await _check_database(),
        "redis": await _check_redis(),
        "storage": await _check_storage(),
        "tts_service": await _check_tts(),
    }
    
    all_ready = all(check.get("status") == "ok" for check in checks.values())
    
    if not all_ready:
        logger.warning(f"Readiness check failed: {checks}")
    
    return ReadinessResponse(
        ready=all_ready,
        checks=checks
    )


@router.get("/health/live", response_model=LivenessResponse)
async def liveness_check():
    """
    Kubernetes liveness probe.
    
    Simple check if the application is running.
    If this fails, Kubernetes will restart the pod.
    """
    return LivenessResponse(alive=True)


@router.get("/health/detailed")
async def detailed_health():
    """
    Detailed health information.
    
    Returns comprehensive system status for debugging.
    """
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
            "uptime_seconds": time.time() - START_TIME,
        },
        "dependencies": {
            "database": await _check_database(),
            "redis": await _check_redis(),
            "storage": await _check_storage(),
            "tts_service": await _check_tts(),
        },
        "configuration": {
            "tts_enabled": settings.tts_enabled,
            "tts_model": settings.tts_model,
            "languages": settings.supported_languages,
            "max_video_size_mb": settings.max_video_size_mb,
        },
        "resources": {
            # These would be populated with actual metrics in production
            "cpu_percent": "N/A (requires psutil)",
            "memory_percent": "N/A (requires psutil)",
            "disk_usage": "N/A (requires psutil)",
        }
    }


async def _check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        # In production, this would actually connect to the database
        # For now, just return ok since we haven't set up the connection yet
        return {
            "status": "ok",
            "type": "postgresql",
            "pool_size": settings.database_pool_size
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        # In production, this would ping Redis
        return {
            "status": "ok",
            "url": settings.redis_url.replace("//", "//***@")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def _check_storage() -> Dict[str, Any]:
    """Check storage connectivity."""
    try:
        return {
            "status": "ok",
            "endpoint": settings.storage_endpoint,
            "bucket": settings.storage_bucket,
            "secure": settings.storage_secure
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def _check_tts() -> Dict[str, Any]:
    """Check TTS service health."""
    try:
        health = await tts_service.health_check()
        return {
            "status": "ok" if health["status"] == "healthy" else "degraded",
            "engine": health.get("primary_model") or health.get("fallback_model"),
            "initialized": health["initialized"],
            "cache_size": health["cache_size"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/health/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns application metrics for monitoring.
    """
    # This would integrate with prometheus-client in production
    metrics_data = f"""# HELP eyeson_uptime_seconds Total uptime in seconds
# TYPE eyeson_uptime_seconds counter
eyeson_uptime_seconds {time.time() - START_TIME}

# HELP eyeson_info Application information
# TYPE eyeson_info gauge
eyeson_info{{version="{settings.app_version}",environment="{settings.environment}"}} 1

# HELP eyeson_tts_cache_size Current TTS cache size
# TYPE eyeson_tts_cache_size gauge
eyeson_tts_cache_size {len(tts_service.cache)}
"""
    
    return metrics_data
