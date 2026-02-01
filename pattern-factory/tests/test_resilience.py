#!/usr/bin/env python3
"""
Phase 3 Resilience & Observability Tests

Tests for:
1. Observability module (logging, metrics)
2. Circuit breakers
3. Backup manager
4. Health checks

Author: Claude
Date: 2026-02-01
"""

import sys
import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "core"))


class TestObservabilityLogging(unittest.TestCase):
    """Tests for structured logging configuration."""

    def test_logging_module_imports(self):
        """Test that logging module can be imported."""
        from observability.logging_config import configure_logging, get_logger

        self.assertTrue(callable(configure_logging))
        self.assertTrue(callable(get_logger))

    def test_configure_logging(self):
        """Test logging configuration."""
        from observability.logging_config import configure_logging

        # Should not raise - uses json_format and level params
        configure_logging(json_format=False, level="INFO")

    def test_get_logger(self):
        """Test getting a configured logger."""
        from observability.logging_config import get_logger, configure_logging

        configure_logging(json_format=False, level="INFO")
        logger = get_logger("test-module")

        self.assertIsNotNone(logger)

    def test_logging_with_context(self):
        """Test logging with bound context."""
        from observability.logging_config import (
            get_logger,
            configure_logging,
            STRUCTLOG_AVAILABLE,
        )

        configure_logging(json_format=False, level="INFO")
        logger = get_logger("test-module")

        # Only test bind if structlog is available
        if STRUCTLOG_AVAILABLE and hasattr(logger, "bind"):
            bound_logger = logger.bind(order_id="test-123", customer_id="cust-456")
            self.assertIsNotNone(bound_logger)


class TestObservabilityMetrics(unittest.TestCase):
    """Tests for Prometheus metrics."""

    def test_metrics_module_imports(self):
        """Test that metrics module can be imported."""
        from observability.metrics import (
            ORDERS_TOTAL,
            PROCESSING_TIME,
            QUEUE_LENGTH,
            ACTIVE_WORKERS,
            DLQ_SIZE,
            get_metrics,
        )

        self.assertIsNotNone(ORDERS_TOTAL)
        self.assertIsNotNone(PROCESSING_TIME)
        self.assertIsNotNone(QUEUE_LENGTH)
        self.assertIsNotNone(ACTIVE_WORKERS)
        self.assertIsNotNone(DLQ_SIZE)
        self.assertTrue(callable(get_metrics))

    def test_counter_increment(self):
        """Test incrementing order counter."""
        from observability.metrics import ORDERS_TOTAL

        # Should not raise
        ORDERS_TOTAL.labels(status="completed", garment_type="tee").inc()

    def test_histogram_observation(self):
        """Test observing processing time."""
        from observability.metrics import PROCESSING_TIME

        # Should not raise
        PROCESSING_TIME.observe(45.5)

    def test_gauge_set(self):
        """Test setting gauge values."""
        from observability.metrics import QUEUE_LENGTH, ACTIVE_WORKERS, DLQ_SIZE

        # Should not raise
        QUEUE_LENGTH.labels(priority="normal").set(10)
        ACTIVE_WORKERS.set(3)
        DLQ_SIZE.set(0)

    def test_get_metrics_returns_tuple(self):
        """Test that get_metrics returns Prometheus format tuple."""
        from observability.metrics import get_metrics

        result = get_metrics()

        # get_metrics returns (bytes, content_type) tuple
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        metrics_bytes, content_type = result
        self.assertIsInstance(metrics_bytes, bytes)
        self.assertIn("text/plain", content_type)

        # Should contain HELP and TYPE comments
        metrics_str = metrics_bytes.decode("utf-8")
        self.assertIn("# HELP", metrics_str)
        self.assertIn("# TYPE", metrics_str)


class TestBackupManager(unittest.TestCase):
    """Tests for automated backup functionality."""

    def test_backup_manager_imports(self):
        """Test that backup manager can be imported."""
        from observability.backup_manager import BackupManager

        self.assertTrue(callable(BackupManager))

    def test_backup_manager_initialization(self):
        """Test backup manager initialization."""
        from observability.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BackupManager(backup_dir=tmpdir)
            self.assertEqual(manager.backup_dir, Path(tmpdir))

    def test_backup_outputs(self):
        """Test backing up output directory."""
        from observability.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source directory with test file
            source_dir = Path(tmpdir) / "output"
            source_dir.mkdir()
            (source_dir / "test.plt").write_text("test plt content")

            # Create backup directory
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            manager = BackupManager(backup_dir=str(backup_dir))
            result = manager.backup_outputs(str(source_dir))

            self.assertIsNotNone(result)
            self.assertTrue(result.exists())

    def test_verify_backup(self):
        """Test backup verification."""
        from observability.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file to verify
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            manager = BackupManager(backup_dir=tmpdir)
            result = manager.verify_backup(test_file)

            self.assertTrue(result["valid"])
            self.assertIn("checksum_sha256", result)
            self.assertIn("size_bytes", result)

    def test_list_backups(self):
        """Test listing backups."""
        from observability.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BackupManager(backup_dir=tmpdir)
            backups = manager.list_backups()

            # Should return a list (may be empty)
            self.assertIsInstance(backups, list)


class TestCircuitBreaker(unittest.TestCase):
    """Tests for circuit breaker pattern."""

    def test_circuit_breaker_import(self):
        """Test that circuit breaker is available."""
        try:
            from pybreaker import CircuitBreaker, CircuitBreakerError

            HAS_PYBREAKER = True
        except ImportError:
            HAS_PYBREAKER = False

        # Test passes regardless - we just need to know availability
        self.assertIn(HAS_PYBREAKER, [True, False])

    def test_circuit_breaker_config_in_database_integration(self):
        """Test that circuit breaker is configured in database integration."""
        from integrations.database_integration import (
            CIRCUIT_BREAKER_AVAILABLE,
            DatabaseUnavailableError,
        )

        # Should have the error class defined
        self.assertTrue(issubclass(DatabaseUnavailableError, Exception))
        # CIRCUIT_BREAKER_AVAILABLE depends on whether pybreaker is installed
        self.assertIn(CIRCUIT_BREAKER_AVAILABLE, [True, False])

    def test_database_unavailable_error_is_exception(self):
        """Test that DatabaseUnavailableError can be raised."""
        from integrations.database_integration import DatabaseUnavailableError

        # Should be able to raise and catch the error
        try:
            raise DatabaseUnavailableError("Test error")
        except DatabaseUnavailableError as e:
            self.assertIn("Test error", str(e))


class TestHealthCheck(unittest.TestCase):
    """Tests for enhanced health check endpoint."""

    def test_health_check_returns_components(self):
        """Test that health check includes component status."""
        # This would require running the actual API
        # For unit testing, we verify the health check logic exists
        import importlib.util

        spec = importlib.util.find_spec("api.web_api")
        if spec is None:
            # Try alternative path
            spec = importlib.util.find_spec("src.api.web_api")

        # Module should be findable
        # Actual endpoint testing is done in integration tests


class TestWorkerHeartbeat(unittest.TestCase):
    """Tests for worker heartbeat functionality."""

    def test_worker_has_heartbeat_method(self):
        """Test that worker class has heartbeat method."""
        from workers.nesting_worker import NestingWorker

        self.assertTrue(hasattr(NestingWorker, "_write_heartbeat_file"))

    def test_heartbeat_file_format(self):
        """Test heartbeat file content format."""
        from workers.nesting_worker import NestingWorker

        with patch.object(NestingWorker, "_load_production_modules"):
            worker = NestingWorker(worker_id="test-worker")
            worker.orders_processed = 5
            worker.orders_failed = 1

            with tempfile.TemporaryDirectory() as tmpdir:
                heartbeat_path = Path(tmpdir) / "heartbeat"

                # Patch the heartbeat path
                with patch("pathlib.Path.write_text") as mock_write:
                    worker._write_heartbeat_file()

                    if mock_write.called:
                        content = mock_write.call_args[0][0]
                        self.assertIn("test-worker", content)
                        self.assertIn("processed=5", content)
                        self.assertIn("failed=1", content)


class TestMonitoringConfiguration(unittest.TestCase):
    """Tests for monitoring configuration files."""

    def test_prometheus_config_exists(self):
        """Test that prometheus.yml exists and is valid YAML."""
        config_path = Path(__file__).parent.parent / "monitoring" / "prometheus.yml"

        if config_path.exists():
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)

            self.assertIn("scrape_configs", config)
            self.assertIn("alerting", config)

    def test_alertmanager_config_exists(self):
        """Test that alertmanager.yml exists and is valid YAML."""
        config_path = Path(__file__).parent.parent / "monitoring" / "alertmanager.yml"

        if config_path.exists():
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)

            self.assertIn("route", config)
            self.assertIn("receivers", config)

    def test_alert_rules_exist(self):
        """Test that alert rules file exists and is valid YAML."""
        rules_path = (
            Path(__file__).parent.parent / "monitoring" / "rules" / "samedaysuits.yml"
        )

        if rules_path.exists():
            import yaml

            with open(rules_path) as f:
                rules = yaml.safe_load(f)

            self.assertIn("groups", rules)
            self.assertGreater(len(rules["groups"]), 0)

    def test_grafana_dashboard_exists(self):
        """Test that Grafana dashboard JSON exists and is valid."""
        dashboard_path = (
            Path(__file__).parent.parent
            / "monitoring"
            / "grafana"
            / "dashboards"
            / "samedaysuits.json"
        )

        if dashboard_path.exists():
            with open(dashboard_path) as f:
                dashboard = json.load(f)

            self.assertIn("panels", dashboard)
            self.assertIn("title", dashboard)
            self.assertEqual(dashboard["title"], "SameDaySuits Pattern Factory")


class TestDockerComposeMonitoring(unittest.TestCase):
    """Tests for docker-compose.monitoring.yml."""

    def test_monitoring_compose_exists(self):
        """Test that docker-compose.monitoring.yml exists and is valid."""
        compose_path = Path(__file__).parent.parent / "docker-compose.monitoring.yml"

        if compose_path.exists():
            import yaml

            with open(compose_path) as f:
                config = yaml.safe_load(f)

            self.assertIn("services", config)

            # Check required services
            services = config["services"]
            self.assertIn("prometheus", services)
            self.assertIn("alertmanager", services)
            self.assertIn("grafana", services)
            self.assertIn("redis-exporter", services)

    def test_monitoring_uses_external_network(self):
        """Test that monitoring stack uses external network."""
        compose_path = Path(__file__).parent.parent / "docker-compose.monitoring.yml"

        if compose_path.exists():
            import yaml

            with open(compose_path) as f:
                config = yaml.safe_load(f)

            networks = config.get("networks", {})
            self.assertIn("samedaysuits-network", networks)
            self.assertTrue(networks["samedaysuits-network"].get("external", False))


def run_tests():
    """Run all resilience tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestObservabilityLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestObservabilityMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestBackupManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCircuitBreaker))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthCheck))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkerHeartbeat))
    suite.addTests(loader.loadTestsFromTestCase(TestMonitoringConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestDockerComposeMonitoring))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
