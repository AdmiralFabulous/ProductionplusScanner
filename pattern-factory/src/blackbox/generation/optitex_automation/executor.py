"""
Optitex Batch Script Executor

Executes Optitex batch scripts via subprocess and manages results.

Author: AI Agent
Date: January 2026
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import time

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of batch script execution."""

    success: bool
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    script_path: Path
    timestamp: datetime


class OptitexExecutor:
    """Execute Optitex batch scripts."""

    def __init__(
        self,
        pds_exe: Optional[Path] = None,
        marker_exe: Optional[Path] = None,
        timeout: int = 3600,
    ):
        self.pds_exe = pds_exe or config.pds_exe
        self.marker_exe = marker_exe or config.marker_exe
        self.timeout = timeout

        # Validate installation
        if not self.pds_exe.exists():
            logger.warning(f"PDS.exe not found at {self.pds_exe}")
        if not self.marker_exe.exists():
            logger.warning(f"Marker.exe not found at {self.marker_exe}")

    def run_pds_batch(
        self, script_path: Path, timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute batch script in PDS.

        Args:
            script_path: Path to batch script file
            timeout: Override default timeout (seconds)

        Returns:
            ExecutionResult with success status and output
        """
        return self._execute(
            exe=self.pds_exe, script_path=script_path, timeout=timeout or self.timeout
        )

    def run_marker_batch(
        self, script_path: Path, timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute batch script in Marker.

        Args:
            script_path: Path to batch script file
            timeout: Override default timeout (seconds)

        Returns:
            ExecutionResult with success status and output
        """
        return self._execute(
            exe=self.marker_exe,
            script_path=script_path,
            timeout=timeout or self.timeout,
        )

    def _execute(self, exe: Path, script_path: Path, timeout: int) -> ExecutionResult:
        """Internal execution handler."""

        if not script_path.exists():
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Script not found: {script_path}",
                duration_seconds=0,
                script_path=script_path,
                timestamp=datetime.now(),
            )

        # Command: PDS.exe /BATCH=script.bat
        cmd = [str(exe), f"/BATCH={script_path}"]

        logger.info(f"Executing: {' '.join(cmd)}")
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=script_path.parent,
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            if not success:
                logger.error(f"Batch failed: {result.stderr}")
            else:
                logger.info(f"Batch completed in {duration:.1f}s")

            return ExecutionResult(
                success=success,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                script_path=script_path,
                timestamp=datetime.now(),
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"Batch timed out after {timeout}s")

            return ExecutionResult(
                success=False,
                return_code=-2,
                stdout="",
                stderr=f"Timeout after {timeout} seconds",
                duration_seconds=duration,
                script_path=script_path,
                timestamp=datetime.now(),
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Batch execution error")

            return ExecutionResult(
                success=False,
                return_code=-3,
                stdout="",
                stderr=str(e),
                duration_seconds=duration,
                script_path=script_path,
                timestamp=datetime.now(),
            )

    def run_with_retry(
        self,
        script_path: Path,
        exe_type: str = "pds",
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ) -> ExecutionResult:
        """
        Execute with automatic retry on failure.

        Args:
            script_path: Path to batch script
            exe_type: "pds" or "marker"
            max_retries: Maximum retry attempts
            retry_delay: Seconds between retries

        Returns:
            ExecutionResult from successful attempt or final failure
        """
        runner = self.run_pds_batch if exe_type == "pds" else self.run_marker_batch

        for attempt in range(max_retries):
            result = runner(script_path)

            if result.success:
                return result

            if attempt < max_retries - 1:
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {retry_delay}s"
                )
                time.sleep(retry_delay)

        return result
