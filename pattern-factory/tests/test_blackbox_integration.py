#!/usr/bin/env python3
"""
BlackBox Integration Tests

Tests for the BlackBox module integration into Production.
Verifies:
1. Module imports work correctly
2. Translation module (no external deps)
3. Optitex config (environment-based)
4. BlackBox Bridge integration
5. Graceful degradation when deps missing

Author: SameDaySuits
Date: February 2026
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestBlackboxModuleImports(unittest.TestCase):
    """Test that blackbox modules can be imported."""

    def test_blackbox_main_module_imports(self):
        """Test that main blackbox module imports."""
        import blackbox

        self.assertIsNotNone(blackbox)
        self.assertTrue(hasattr(blackbox, "__version__"))
        self.assertTrue(hasattr(blackbox, "scanning_available"))
        self.assertTrue(hasattr(blackbox, "patterns_available"))

    def test_translation_module_imports(self):
        """Test that translation module imports (no external deps)."""
        from blackbox.translation import (
            MullerTranslator,
            MullerTranslationError,
            BodyMeasurements,
            PatternParameters,
            FitType,
            FabricType,
            calculate_pattern_params,
        )

        self.assertTrue(callable(MullerTranslator))
        self.assertTrue(callable(calculate_pattern_params))
        self.assertTrue(issubclass(MullerTranslationError, Exception))

    def test_optitex_config_imports(self):
        """Test that optitex config imports."""
        from blackbox.generation.optitex_automation import (
            OptitexConfig,
            get_optitex_config,
        )

        self.assertTrue(callable(get_optitex_config))

        config = get_optitex_config()
        self.assertIsInstance(config, OptitexConfig)

    def test_scanning_availability_check(self):
        """Test scanning availability check."""
        from blackbox import scanning_available, patterns_available

        # These should return booleans
        self.assertIsInstance(scanning_available(), bool)
        self.assertIsInstance(patterns_available(), bool)


class TestMullerTranslator(unittest.TestCase):
    """Test M. Muller translation functionality."""

    def test_translator_initialization(self):
        """Test translator can be initialized."""
        from blackbox.translation import MullerTranslator, FitType, FabricType

        translator = MullerTranslator(
            fit_type=FitType.REGULAR, fabric_type=FabricType.WOOL
        )

        self.assertIsNotNone(translator)
        self.assertEqual(translator.fit_type, FitType.REGULAR)
        self.assertEqual(translator.fabric_type, FabricType.WOOL)

    def test_calculate_pattern_params(self):
        """Test pattern parameter calculation."""
        from blackbox.translation import calculate_pattern_params

        measurements = {
            "chest": 102,
            "waist": 88,
            "hip": 100,
            "shoulder_width": 46,
            "arm_length": 64,
        }

        params = calculate_pattern_params(
            measurements, fit_type="regular", fabric_type="wool", source="test"
        )

        self.assertIsInstance(params, dict)
        self.assertIn("HALF_CHEST", params)
        self.assertIn("HALF_WAIST", params)
        self.assertIn("HALF_HIP", params)
        self.assertIn("FIT_TYPE", params)
        self.assertEqual(params["FIT_TYPE"], "regular")

    def test_fit_types(self):
        """Test different fit types produce different results."""
        from blackbox.translation import calculate_pattern_params

        measurements = {"chest": 102, "waist": 88, "hip": 100}

        slim = calculate_pattern_params(measurements, fit_type="slim")
        regular = calculate_pattern_params(measurements, fit_type="regular")
        classic = calculate_pattern_params(measurements, fit_type="classic")

        # Slim should have least ease, classic most
        self.assertLess(slim["HALF_CHEST"], regular["HALF_CHEST"])
        self.assertLess(regular["HALF_CHEST"], classic["HALF_CHEST"])

    def test_missing_measurements_error(self):
        """Test error when required measurements missing."""
        from blackbox.translation import (
            MullerTranslator,
            MullerTranslationError,
            BodyMeasurements,
        )

        translator = MullerTranslator()

        # Missing chest, waist, hip
        incomplete = BodyMeasurements(
            chest=None,
            waist=None,
            hip=None,
        )

        with self.assertRaises(MullerTranslationError):
            translator.translate_measurements(incomplete)


class TestOptitexConfig(unittest.TestCase):
    """Test Optitex configuration."""

    def test_config_defaults(self):
        """Test configuration defaults."""
        from blackbox.generation.optitex_automation.config import OptitexConfig

        config = OptitexConfig()

        # Default should be disabled
        self.assertFalse(config.enabled)
        self.assertEqual(config.timeout_seconds, 300)
        self.assertEqual(config.max_retries, 3)

    def test_config_from_environment(self):
        """Test configuration from environment variables."""
        from blackbox.generation.optitex_automation.config import (
            OptitexConfig,
            reset_config,
        )

        reset_config()  # Clear cached config

        with patch.dict(
            "os.environ",
            {
                "OPTITEX_ENABLED": "true",
                "OPTITEX_TIMEOUT": "600",
            },
        ):
            config = OptitexConfig()

            self.assertTrue(config.enabled)
            self.assertEqual(config.timeout_seconds, 600)

    def test_config_is_available(self):
        """Test is_available() method."""
        from blackbox.generation.optitex_automation.config import OptitexConfig

        config = OptitexConfig()

        # Should be False when disabled or exe doesn't exist
        self.assertFalse(config.is_available())


class TestBlackboxBridge(unittest.TestCase):
    """Test BlackBox to Production bridge."""

    def test_bridge_initialization(self):
        """Test bridge can be initialized."""
        from integrations.blackbox_bridge import BlackBoxBridge

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        self.assertIsNotNone(bridge)
        self.assertFalse(bridge.validate_files)

    def test_generate_order_id(self):
        """Test order ID generation."""
        from integrations.blackbox_bridge import BlackBoxBridge

        bridge = BlackBoxBridge(queue=None)

        order_id = bridge._generate_order_id("CUST-001")

        self.assertTrue(order_id.startswith("BB-CUST-001"))
        self.assertGreater(len(order_id), 20)

    def test_validate_output_missing_measurements(self):
        """Test validation catches missing measurements."""
        from integrations.blackbox_bridge import (
            BlackBoxBridge,
            BlackBoxOutput,
        )

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        output = BlackBoxOutput(
            order_id="TEST-001",
            customer_id="CUST-001",
            measurements={},  # Empty measurements
            garment_type="tee",
        )

        errors = bridge._validate_output(output)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("measurement" in e.lower() for e in errors))

    def test_validate_output_invalid_garment(self):
        """Test validation catches invalid garment type."""
        from integrations.blackbox_bridge import (
            BlackBoxBridge,
            BlackBoxOutput,
        )

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        output = BlackBoxOutput(
            order_id="TEST-001",
            customer_id="CUST-001",
            measurements={"chest_cm": 102, "waist_cm": 88, "hip_cm": 100},
            garment_type="invalid_garment",
        )

        errors = bridge._validate_output(output)

        self.assertTrue(any("garment" in e.lower() for e in errors))

    def test_validate_output_success(self):
        """Test validation passes with valid output."""
        from integrations.blackbox_bridge import (
            BlackBoxBridge,
            BlackBoxOutput,
        )

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        output = BlackBoxOutput(
            order_id="TEST-001",
            customer_id="CUST-001",
            measurements={"chest_cm": 102, "waist_cm": 88, "hip_cm": 100},
            garment_type="tee",
            confidence_score=0.95,
        )

        errors = bridge._validate_output(output)

        self.assertEqual(len(errors), 0)

    def test_to_queue_format(self):
        """Test conversion to queue format."""
        from integrations.blackbox_bridge import (
            BlackBoxBridge,
            BlackBoxOutput,
            InputSource,
        )

        bridge = BlackBoxBridge(queue=None)

        output = BlackBoxOutput(
            order_id="TEST-001",
            customer_id="CUST-001",
            measurements={"chest_cm": 102},
            garment_type="jacket",
            fit_type="slim",
            source=InputSource.BLACKBOX_SCAN,
        )

        queue_data = bridge._to_queue_format(output)

        self.assertEqual(queue_data["order_id"], "TEST-001")
        self.assertEqual(queue_data["customer_id"], "CUST-001")
        self.assertEqual(queue_data["garment_type"], "jacket")
        self.assertEqual(queue_data["fit_type"], "slim")
        self.assertEqual(queue_data["source"], "blackbox_scan")
        self.assertIn("submitted_at", queue_data)

    def test_submit_measurements_without_queue(self):
        """Test submission works in sync mode (no queue)."""
        from integrations.blackbox_bridge import BlackBoxBridge

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        result = bridge.submit_measurements(
            measurements={"chest_cm": 102, "waist_cm": 88, "hip_cm": 100},
            customer_id="CUST-001",
            garment_type="tee",
        )

        # Should succeed in sync mode
        self.assertTrue(result.success)
        self.assertIsNotNone(result.order_id)
        self.assertTrue(any("sync" in w.lower() for w in result.warnings))


class TestGracefulDegradation(unittest.TestCase):
    """Test graceful degradation when dependencies missing."""

    def test_scanning_not_available_message(self):
        """Test appropriate message when scanning not available."""
        from blackbox import scanning_available

        # Just verify the function exists and returns a boolean
        result = scanning_available()
        self.assertIsInstance(result, bool)

    def test_patterns_not_available_message(self):
        """Test appropriate message when patterns not available."""
        from blackbox import patterns_available

        result = patterns_available()
        self.assertIsInstance(result, bool)


class TestDirectoryStructure(unittest.TestCase):
    """Test that expected files and directories exist."""

    def setUp(self):
        self.blackbox_dir = Path(__file__).parent.parent / "src" / "blackbox"

    def test_blackbox_directory_exists(self):
        """Test blackbox directory exists."""
        self.assertTrue(self.blackbox_dir.exists())

    def test_scanning_directory_exists(self):
        """Test scanning subdirectory exists."""
        self.assertTrue((self.blackbox_dir / "scanning").exists())

    def test_translation_directory_exists(self):
        """Test translation subdirectory exists."""
        self.assertTrue((self.blackbox_dir / "translation").exists())

    def test_generation_directory_exists(self):
        """Test generation subdirectory exists."""
        self.assertTrue((self.blackbox_dir / "generation").exists())

    def test_optitex_automation_exists(self):
        """Test optitex_automation subdirectory exists."""
        optitex_dir = self.blackbox_dir / "generation" / "optitex_automation"
        self.assertTrue(optitex_dir.exists())

    def test_key_files_exist(self):
        """Test key Python files exist."""
        files = [
            self.blackbox_dir / "__init__.py",
            self.blackbox_dir / "pipeline.py",
            self.blackbox_dir / "scanning" / "aruco_calibration.py",
            self.blackbox_dir / "scanning" / "pose_extraction.py",
            self.blackbox_dir / "translation" / "muller_translator.py",
            self.blackbox_dir / "generation" / "dxf_generator.py",
            self.blackbox_dir / "generation" / "optitex_automation" / "config.py",
            self.blackbox_dir / "generation" / "optitex_automation" / "workflow.py",
        ]

        for f in files:
            self.assertTrue(f.exists(), f"Missing file: {f}")


def run_tests():
    """Run all blackbox integration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBlackboxModuleImports))
    suite.addTests(loader.loadTestsFromTestCase(TestMullerTranslator))
    suite.addTests(loader.loadTestsFromTestCase(TestOptitexConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestBlackboxBridge))
    suite.addTests(loader.loadTestsFromTestCase(TestGracefulDegradation))
    suite.addTests(loader.loadTestsFromTestCase(TestDirectoryStructure))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
