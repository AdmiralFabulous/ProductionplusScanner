#!/usr/bin/env python3
"""
Template Cache Manager

Provides caching for PDS templates to reduce I/O overhead.
Uses Redis when available, falls back to file system gracefully.

Features:
- Template caching with TTL (default 1 hour)
- Cache warming on startup
- Graceful fallback to file system
- Memory-efficient binary storage

Redis Key Structure:
    sds:cache:template:{name}  - Binary template data
    sds:cache:stats            - Cache hit/miss counters

Usage:
    cache = TemplateCache()

    # Get template (from cache or file)
    data = cache.get_template("Basic Tee_2D")

    # Warm cache on startup
    cache.warm_cache(Path("DS-speciale/inputs/pds"))

Author: Claude
Date: 2026-01-31
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateCache:
    """
    Template caching with Redis backend and file system fallback.

    The cache is optional - if Redis is unavailable, templates
    are loaded directly from the file system without error.
    """

    KEY_PREFIX = "sds:cache:template"
    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL (defaults to env var or localhost)
        """
        self._client = None
        self._available = False
        self._stats = {"hits": 0, "misses": 0}

        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._connect(url)

    def _connect(self, url: str):
        """Connect to Redis with graceful handling."""
        try:
            import redis

            self._client = redis.Redis.from_url(
                url,
                decode_responses=False,  # Binary data for templates
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self._client.ping()
            self._available = True
            logger.info("Template cache connected to Redis")
        except Exception as e:
            logger.debug(f"Template cache Redis unavailable ({e}), using file fallback")
            self._client = None
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if Redis cache is available."""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._available = False
            return False

    def _key(self, template_name: str) -> str:
        """Build cache key for template."""
        # Normalize template name
        name = template_name.replace(" ", "_").replace(".PDS", "").replace(".pds", "")
        return f"{self.KEY_PREFIX}:{name}"

    def get(self, template_name: str) -> Optional[bytes]:
        """
        Get template from cache.

        Args:
            template_name: Template name (with or without .PDS extension)

        Returns:
            Template binary data or None if not cached
        """
        if not self.is_available:
            return None

        try:
            key = self._key(template_name)
            data = self._client.get(key)

            if data:
                self._stats["hits"] += 1
                logger.debug(f"Cache hit for template: {template_name}")
                return data
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss for template: {template_name}")
                return None

        except Exception as e:
            logger.debug(f"Cache get error for {template_name}: {e}")
            return None

    def set(self, template_name: str, data: bytes, ttl: int = None):
        """
        Cache template data.

        Args:
            template_name: Template name
            data: Binary template data
            ttl: Time-to-live in seconds (default 1 hour)
        """
        if not self.is_available:
            return

        try:
            key = self._key(template_name)
            ttl = ttl or self.DEFAULT_TTL
            self._client.setex(key, ttl, data)
            logger.debug(f"Cached template: {template_name} (TTL: {ttl}s)")
        except Exception as e:
            logger.debug(f"Cache set error for {template_name}: {e}")

    def invalidate(self, template_name: str):
        """
        Remove template from cache.

        Args:
            template_name: Template to invalidate
        """
        if not self.is_available:
            return

        try:
            key = self._key(template_name)
            self._client.delete(key)
            logger.debug(f"Invalidated cache for: {template_name}")
        except Exception:
            pass

    def get_template(
        self, template_name: str, template_dir: Optional[Path] = None
    ) -> Optional[bytes]:
        """
        Get template from cache or file system.

        This is the main method to use - it handles cache lookup
        and file system fallback automatically.

        Args:
            template_name: Template name
            template_dir: Directory to search for template files

        Returns:
            Template binary data or None if not found
        """
        # Try cache first
        data = self.get(template_name)
        if data:
            return data

        # Load from file system
        if template_dir is None:
            # Default template directory
            template_dir = (
                Path(__file__).parent.parent.parent / "DS-speciale" / "inputs" / "pds"
            )

        data = self._load_from_file(template_name, template_dir)

        if data:
            # Cache for next time
            self.set(template_name, data)

        return data

    def _load_from_file(
        self, template_name: str, template_dir: Path
    ) -> Optional[bytes]:
        """Load template from file system."""
        # Try various filename formats
        candidates = [
            template_name,
            f"{template_name}.PDS",
            f"{template_name}.pds",
            template_name.replace("_", " "),
            f"{template_name.replace('_', ' ')}.PDS",
        ]

        for candidate in candidates:
            file_path = template_dir / candidate
            if file_path.exists():
                try:
                    data = file_path.read_bytes()
                    logger.debug(f"Loaded template from file: {file_path}")
                    return data
                except Exception as e:
                    logger.error(f"Failed to read template {file_path}: {e}")

        logger.warning(f"Template not found: {template_name} in {template_dir}")
        return None

    def warm_cache(self, template_dir: Path, patterns: list = None):
        """
        Pre-load templates into cache.

        Call this on startup to warm the cache with commonly used templates.

        Args:
            template_dir: Directory containing PDS files
            patterns: List of glob patterns (default: ["*.PDS", "*.pds"])
        """
        if not self.is_available:
            logger.info("Cache warming skipped (Redis unavailable)")
            return

        patterns = patterns or ["*.PDS", "*.pds"]
        loaded = 0

        for pattern in patterns:
            for pds_file in template_dir.glob(pattern):
                try:
                    # Check if already cached
                    if self.get(pds_file.stem):
                        continue

                    # Load and cache
                    data = pds_file.read_bytes()
                    self.set(pds_file.stem, data)
                    loaded += 1

                except Exception as e:
                    logger.warning(f"Failed to cache {pds_file}: {e}")

        logger.info(f"Cache warmed with {loaded} templates from {template_dir}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 1),
            "redis_available": self.is_available,
        }

    def clear(self):
        """Clear all cached templates."""
        if not self.is_available:
            return

        try:
            keys = self._client.keys(f"{self.KEY_PREFIX}:*")
            if keys:
                self._client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached templates")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Singleton instance
_cache_instance: Optional[TemplateCache] = None


def get_template_cache() -> TemplateCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TemplateCache()
    return _cache_instance


# Testing
def _test_cache():
    """Test cache operations."""
    import tempfile

    cache = TemplateCache()

    print(f"Redis available: {cache.is_available}")

    # Test set/get
    test_data = b"Test template data"
    cache.set("test_template", test_data, ttl=60)

    retrieved = cache.get("test_template")
    if cache.is_available:
        assert retrieved == test_data, "Cache retrieval failed"
        print("Cache set/get: OK")
    else:
        print("Cache set/get: Skipped (no Redis)")

    # Test file fallback
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test template file
        test_file = tmpdir / "Test_Template.PDS"
        test_file.write_bytes(b"Template file content")

        # Get via get_template (should load from file)
        cache.invalidate("Test_Template")
        data = cache.get_template("Test_Template", tmpdir)
        assert data == b"Template file content", "File fallback failed"
        print("File fallback: OK")

    # Stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")

    print("\nAll cache tests passed!")


if __name__ == "__main__":
    _test_cache()
