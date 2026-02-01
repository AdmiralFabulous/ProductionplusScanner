"""
EYESON - Enterprise BodyScan Platform
Core Configuration Module

This module contains all configuration settings for the EYESON platform.
Uses Pydantic Settings for environment variable management.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = "EYESON BodyScan API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database
    database_url: str = Field(default="postgresql+asyncpg://user:pass@localhost/eyeson")
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_pool_size: int = 50
    
    # Security
    secret_key: str = Field(default="change-me-in-production")
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"
    
    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])
    
    # Storage (S3-compatible)
    storage_endpoint: str = Field(default="http://localhost:9000")
    storage_bucket: str = Field(default="eyeson-scans")
    storage_access_key: str = Field(default="minioadmin")
    storage_secret_key: str = Field(default="minioadmin")
    storage_region: str = Field(default="us-east-1")
    storage_secure: bool = Field(default=False)
    
    # Video Processing
    max_video_size_mb: int = 100
    video_chunk_size_mb: int = 10
    video_retention_hours: int = 24
    supported_video_formats: List[str] = Field(default=["video/mp4", "video/webm"])
    
    # Open Source TTS Configuration (Kokoro-82M)
    tts_enabled: bool = True
    tts_model: str = Field(default="onnx-community/Kokoro-82M-ONNX")
    tts_device: str = Field(default="cpu", description="cpu, cuda, or webgpu")
    tts_voice: str = Field(default="af", description="Voice ID: af (American Female), am (American Male), etc.")
    tts_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    tts_cache_enabled: bool = True
    tts_cache_dir: Path = Field(default=Path("./cache/tts"))
    
    # Alternative TTS: Piper (for edge cases)
    tts_fallback_enabled: bool = True
    tts_fallback_model: str = Field(default="en_US-lessac-medium")
    
    # STT Configuration (Deepgram - still needed for accuracy)
    stt_enabled: bool = True
    stt_provider: str = Field(default="deepgram")
    stt_model: str = Field(default="nova-2")
    stt_language: str = Field(default="en")
    
    # ML Service
    ml_service_url: str = Field(default="http://localhost:8001")
    ml_service_timeout: int = 60
    
    # SAM-3D-Body Model
    sam3d_model_path: str = Field(default="./models/sam-3d-body")
    sam3d_device: str = Field(default="cuda")
    
    # Inference Optimization
    inference_batch_size: int = 4
    inference_num_workers: int = 2
    
    # API Rate Limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst: int = 20
    
    # Webhooks
    webhook_timeout_seconds: int = 30
    webhook_max_retries: int = 3
    webhook_retry_delay_seconds: int = 5
    
    # Scanning
    default_scan_duration_seconds: int = 30
    max_scan_duration_seconds: int = 45
    calibration_marker_size_cm: float = 14.0  # A4/Letter marker
    
    # Accuracy Targets
    target_accuracy_p0_cm: float = 1.0
    target_accuracy_p1_cm: float = 2.0
    confidence_threshold: float = 0.75
    
    # Voice Prompts
    voice_prompts_dir: Path = Field(default=Path("./voice_prompts"))
    supported_languages: List[str] = Field(default=["en", "es", "fr", "de", "zh"])
    default_language: str = "en"
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # Monitoring
    metrics_enabled: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = True
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.tts_cache_dir.mkdir(parents=True, exist_ok=True)
        self.voice_prompts_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings


# Export for convenience
settings = get_settings()
