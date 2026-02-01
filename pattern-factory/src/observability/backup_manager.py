"""
Backup Manager for SameDaySuits Pattern Factory

Provides automated backup functionality for:
- Output files (PLT, metadata, QC reports)
- Configuration files
- Optional Redis data (RDB snapshots)

Usage:
    from observability.backup_manager import BackupManager

    bm = BackupManager("/app/backups")
    backup_path = bm.backup_outputs("/app/output")
    verification = bm.verify_backup(backup_path)
    bm.cleanup_old_backups(keep_days=7)

Author: Claude
Date: 2026-02-01
"""

import hashlib
import shutil
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class BackupManager:
    """
    Manages backups with verification and cleanup.

    Supports:
    - Full directory archiving (tar.gz)
    - Checksum verification (SHA256)
    - Automatic cleanup of old backups
    - Backup inventory listing
    """

    def __init__(self, backup_dir: str = "/app/backups"):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.backup_dir / "backup_manifest.json"

    def backup_outputs(self, output_dir: str = "/app/output") -> Optional[Path]:
        """
        Archive the output directory.

        Args:
            output_dir: Directory containing output files

        Returns:
            Path to backup file or None if failed
        """
        output_path = Path(output_dir)
        if not output_path.exists():
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"outputs_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}.tar.gz"

            # Create archive
            shutil.make_archive(
                str(self.backup_dir / backup_name), "gztar", str(output_path)
            )

            # Update manifest
            self._update_manifest(backup_path, "outputs")

            return backup_path

        except Exception as e:
            print(f"Backup failed: {e}")
            return None

    def backup_config(self, config_files: List[str]) -> Optional[Path]:
        """
        Backup configuration files.

        Args:
            config_files: List of config file paths to backup

        Returns:
            Path to backup file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.backup_dir / f"config_{timestamp}"
            backup_dir.mkdir(exist_ok=True)

            for config_file in config_files:
                src = Path(config_file)
                if src.exists():
                    shutil.copy2(src, backup_dir / src.name)

            # Archive the config directory
            archive_path = shutil.make_archive(
                str(backup_dir), "gztar", str(backup_dir)
            )

            # Clean up temp directory
            shutil.rmtree(backup_dir)

            backup_path = Path(archive_path)
            self._update_manifest(backup_path, "config")

            return backup_path

        except Exception as e:
            print(f"Config backup failed: {e}")
            return None

    def verify_backup(self, file_path: Path) -> Dict[str, Any]:
        """
        Verify backup integrity.

        Args:
            file_path: Path to backup file

        Returns:
            Dict with checksum, size, and validity info
        """
        if not file_path.exists():
            return {"valid": False, "error": "File not found"}

        try:
            # Calculate checksum
            with open(file_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()

            # Get file stats
            stat = file_path.stat()

            return {
                "valid": True,
                "file": str(file_path),
                "checksum_sha256": checksum,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def cleanup_old_backups(self, keep_days: int = 7) -> int:
        """
        Remove backups older than keep_days.

        Args:
            keep_days: Number of days to keep backups

        Returns:
            Number of files removed
        """
        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        removed = 0

        for f in self.backup_dir.iterdir():
            if f.is_file() and f.suffix in (".gz", ".tar", ".zip"):
                if f.stat().st_mtime < cutoff:
                    try:
                        f.unlink()
                        removed += 1
                    except Exception:
                        pass

        # Update manifest
        self._cleanup_manifest()

        return removed

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups with metadata.

        Returns:
            List of backup info dicts, sorted by date (newest first)
        """
        backups = []

        for f in sorted(
            self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            if f.is_file() and f.suffix in (".gz", ".tar", ".zip"):
                stat = f.stat()

                # Determine backup type from filename
                if f.name.startswith("outputs_"):
                    backup_type = "outputs"
                elif f.name.startswith("config_"):
                    backup_type = "config"
                elif f.name.startswith("redis_"):
                    backup_type = "redis"
                else:
                    backup_type = "unknown"

                backups.append(
                    {
                        "name": f.name,
                        "type": backup_type,
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "path": str(f),
                    }
                )

        return backups

    def get_latest_backup(self, backup_type: str = "outputs") -> Optional[Path]:
        """
        Get the most recent backup of a given type.

        Args:
            backup_type: Type of backup (outputs, config, redis)

        Returns:
            Path to most recent backup or None
        """
        backups = [b for b in self.list_backups() if b["type"] == backup_type]
        if backups:
            return Path(backups[0]["path"])
        return None

    def _update_manifest(self, backup_path: Path, backup_type: str) -> None:
        """Update the backup manifest file."""
        try:
            manifest = self._load_manifest()

            verification = self.verify_backup(backup_path)
            manifest["backups"].append(
                {
                    "path": str(backup_path),
                    "type": backup_type,
                    "checksum": verification.get("checksum_sha256"),
                    "size_bytes": verification.get("size_bytes"),
                    "created": datetime.now().isoformat(),
                }
            )

            manifest["last_updated"] = datetime.now().isoformat()

            with open(self.manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

        except Exception:
            pass  # Non-critical

    def _load_manifest(self) -> Dict[str, Any]:
        """Load the backup manifest."""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file) as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "version": "1.0",
            "backups": [],
            "last_updated": None,
        }

    def _cleanup_manifest(self) -> None:
        """Remove entries for deleted backups from manifest."""
        try:
            manifest = self._load_manifest()
            manifest["backups"] = [
                b for b in manifest["backups"] if Path(b["path"]).exists()
            ]
            manifest["last_updated"] = datetime.now().isoformat()

            with open(self.manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

        except Exception:
            pass
