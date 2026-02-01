#!/usr/bin/env python3
"""
End-to-End BlackBox Integration Tests

Tests the complete pipeline:
1. BlackBox (scan/measurements → pattern parameters)
2. Bridge (submit to Production queue)
3. Production (template → nesting → HPGL)

This test works even without scanning dependencies by:
- Using mock measurements (simulating scan output)
- Testing the full Production pipeline with real templates

Author: SameDaySuits
Date: February 2026
"""

import sys
import os
import unittest
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "core"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEndToEndPipeline(unittest.TestCase):
    """
    End-to-end tests for the complete BlackBox → Production pipeline.

    Flow:
    1. Simulate BlackBox scan output (measurements)
    2. Translate through M. Muller
    3. Submit via BlackBox Bridge
    4. Process through Production pipeline
    5. Verify HPGL output
    """

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_measurements = {
            "chest_cm": 102.0,
            "waist_cm": 88.0,
            "hip_cm": 100.0,
            "shoulder_width_cm": 46.0,
            "arm_length_cm": 64.0,
            "back_length_cm": 44.0,
            "inseam_cm": 82.0,
            "neck_cm": 40.0,
        }

        cls.customer_id = "E2E-TEST-001"
        cls.output_dir = Path(tempfile.mkdtemp(prefix="e2e_blackbox_"))

    def test_01_muller_translation(self):
        """Test M. Muller translation from measurements."""
        from blackbox.translation.muller_translator import (
            MullerTranslator,
            BodyMeasurements,
            FitType,
        )

        # Create body measurements using the actual API
        body = BodyMeasurements(
            chest=self.test_measurements["chest_cm"],
            waist=self.test_measurements["waist_cm"],
            hip=self.test_measurements["hip_cm"],
            shoulder_width=self.test_measurements["shoulder_width_cm"],
            arm_length=self.test_measurements["arm_length_cm"],
            back_length=self.test_measurements["back_length_cm"],
            source="test",
        )

        # Test all fit types
        for fit_type in [FitType.SLIM, FitType.REGULAR, FitType.CLASSIC]:
            translator = MullerTranslator(fit_type=fit_type)
            params = translator.translate_measurements(body)

            self.assertIsNotNone(params)
            self.assertGreater(params.back_width, 0)
            self.assertGreater(params.front_width, 0)

            # Export to dict (keys are uppercase)
            param_dict = translator.export_to_dict(params)
            self.assertIn("BACK_WIDTH", param_dict)

            logger.info(
                f"Muller translation ({fit_type.value}): back_width={param_dict['BACK_WIDTH']:.1f}cm"
            )

        self.assertTrue(True, "Muller translation successful")

    def test_02_blackbox_bridge_validation(self):
        """Test BlackBox Bridge validates and formats data correctly."""
        from integrations.blackbox_bridge import (
            BlackBoxBridge,
            BlackBoxOutput,
            InputSource,
        )

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        # Create BlackBox output
        output = BlackBoxOutput(
            order_id=f"BB-{self.customer_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            customer_id=self.customer_id,
            measurements=self.test_measurements,
            garment_type="jacket",
            fit_type="slim",
            source=InputSource.MANUAL_MEASUREMENTS,
            confidence_score=0.95,
        )

        # Validate output
        errors = bridge._validate_output(output)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")

        # Convert to queue format
        queue_data = bridge._to_queue_format(output)

        self.assertEqual(queue_data["customer_id"], self.customer_id)
        self.assertEqual(queue_data["garment_type"], "jacket")
        self.assertEqual(queue_data["measurements"]["chest_cm"], 102.0)
        self.assertIn("submitted_at", queue_data)

        logger.info(f"Bridge validation passed for {output.order_id}")

    def test_03_blackbox_bridge_submission_sync(self):
        """Test BlackBox Bridge submits in sync mode (no Redis)."""
        from integrations.blackbox_bridge import BlackBoxBridge

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        result = bridge.submit_measurements(
            measurements=self.test_measurements,
            customer_id=self.customer_id,
            garment_type="jacket",
            fit_type="slim",
        )

        self.assertTrue(result.success)
        self.assertIsNotNone(result.order_id)
        self.assertTrue(result.order_id.startswith("BB-"))

        # Should have sync mode warning
        self.assertTrue(
            any("sync" in w.lower() or "queue" in w.lower() for w in result.warnings),
            f"Expected sync warning, got: {result.warnings}",
        )

        logger.info(f"Sync submission successful: {result.order_id}")

    def test_04_production_pipeline_from_measurements(self):
        """Test Production pipeline processes measurements into HPGL."""
        try:
            from samedaysuits_api import (
                SameDaySuitsAPI,
                Order,
                GarmentType,
                FitType,
                CustomerMeasurements,
            )
        except ImportError as e:
            self.skipTest(f"Production API not available: {e}")

        # Initialize API
        api = SameDaySuitsAPI()

        # Create order with measurements from "BlackBox"
        measurements = CustomerMeasurements(
            chest_cm=self.test_measurements["chest_cm"],
            waist_cm=self.test_measurements["waist_cm"],
            hip_cm=self.test_measurements["hip_cm"],
            shoulder_width_cm=self.test_measurements["shoulder_width_cm"],
            arm_length_cm=self.test_measurements["arm_length_cm"],
            inseam_cm=self.test_measurements["inseam_cm"],
            source="blackbox_scan",
        )

        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-E"

        order = Order(
            order_id=order_id,
            customer_id=self.customer_id,
            garment_type=GarmentType.TEE,  # Use tee for faster processing
            fit_type=FitType.REGULAR,
            measurements=measurements,
            quantity=1,
            notes="End-to-end BlackBox integration test",
        )

        # Process through production pipeline
        result = api.process_order(order)

        self.assertTrue(result.success, f"Pipeline failed: {result.errors}")
        self.assertIsNotNone(result.plt_file)
        self.assertTrue(Path(result.plt_file).exists())
        self.assertGreater(result.fabric_utilization, 0)
        self.assertGreater(result.piece_count, 0)

        logger.info(
            f"Production pipeline complete: "
            f"utilization={result.fabric_utilization:.1f}%, "
            f"pieces={result.piece_count}, "
            f"fabric={result.fabric_length_cm:.1f}cm"
        )

    def test_05_full_pipeline_jacket(self):
        """Test full pipeline with jacket garment type."""
        try:
            from samedaysuits_api import (
                SameDaySuitsAPI,
                Order,
                GarmentType,
                FitType,
                CustomerMeasurements,
            )
        except ImportError as e:
            self.skipTest(f"Production API not available: {e}")

        api = SameDaySuitsAPI()

        measurements = CustomerMeasurements(
            chest_cm=self.test_measurements["chest_cm"],
            waist_cm=self.test_measurements["waist_cm"],
            hip_cm=self.test_measurements["hip_cm"],
            shoulder_width_cm=self.test_measurements["shoulder_width_cm"],
            arm_length_cm=self.test_measurements["arm_length_cm"],
            source="blackbox_scan",
        )

        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0002-E"

        order = Order(
            order_id=order_id,
            customer_id=self.customer_id,
            garment_type=GarmentType.JACKET,
            fit_type=FitType.SLIM,
            measurements=measurements,
            quantity=1,
        )

        result = api.process_order(order)

        self.assertTrue(result.success, f"Jacket pipeline failed: {result.errors}")
        logger.info(f"Jacket processed: {result.fabric_utilization:.1f}% utilization")


class TestBlackBoxPipelineWithMocks(unittest.TestCase):
    """
    Test BlackBox pipeline with mocked scanning step.

    This simulates what happens when a scan completes:
    1. Mock scan output (landmarks/measurements)
    2. Real Muller translation
    3. Bridge submission
    4. Production processing
    """

    def test_simulated_scan_to_production(self):
        """Simulate complete flow from scan to cutting file."""
        from blackbox.translation.muller_translator import (
            MullerTranslator,
            BodyMeasurements,
            FitType,
            FabricType,
        )
        from integrations.blackbox_bridge import BlackBoxBridge, BridgeResult

        # Step 1: Simulate scan output (what ArUco + MediaPipe would produce)
        simulated_scan_output = {
            "landmarks": [
                {"name": "left_shoulder", "x": 200, "y": 150, "visibility": 0.99},
                {"name": "right_shoulder", "x": 350, "y": 150, "visibility": 0.99},
                {"name": "left_hip", "x": 220, "y": 400, "visibility": 0.98},
                {"name": "right_hip", "x": 330, "y": 400, "visibility": 0.98},
            ],
            "scale_cm_per_pixel": 0.15,  # From ArUco marker
            "measurements": {
                "shoulder_width_cm": 46.0,
                "torso_length_cm": 65.0,
                "arm_span_cm": 180.0,
            },
            "confidence": 0.95,
        }

        # Step 2: Calculate body measurements (normally from PoseExtractor)
        body_measurements = BodyMeasurements(
            chest=102.0,  # Estimated from landmarks
            waist=88.0,
            hip=100.0,
            shoulder_width=simulated_scan_output["measurements"]["shoulder_width_cm"],
            arm_length=64.0,
            back_length=44.0,
            source="simulated_scan",
        )

        # Step 3: M. Muller translation
        translator = MullerTranslator(
            fit_type=FitType.REGULAR,
            fabric_type=FabricType.WOOL,
        )
        pattern_params = translator.translate_measurements(body_measurements)
        pattern_dict = translator.export_to_dict(pattern_params)

        self.assertIn("BACK_WIDTH", pattern_dict)
        self.assertIn("FRONT_WIDTH", pattern_dict)

        # Step 4: Submit to Production via Bridge
        bridge = BlackBoxBridge(queue=None, validate_files=False)

        result = bridge.submit_measurements(
            measurements={
                "chest_cm": body_measurements.chest,
                "waist_cm": body_measurements.waist,
                "hip_cm": body_measurements.hip,
                "shoulder_width_cm": body_measurements.shoulder_width,
                "arm_length_cm": body_measurements.arm_length,
            },
            customer_id="SCAN-SIM-001",
            garment_type="jacket",
            fit_type="regular",
        )

        self.assertTrue(result.success)
        logger.info(
            f"Simulated scan → Production flow complete. "
            f"Order: {result.order_id}, "
            f"Pattern back_width: {pattern_dict['BACK_WIDTH']:.1f}cm"
        )


class TestBlackBoxOptitexIntegration(unittest.TestCase):
    """Test Optitex automation components (without requiring Optitex installed)."""

    def test_btf_generation(self):
        """Test BTF parameter file generation."""
        from blackbox.generation.optitex_automation.btf_generator import BTFGenerator
        import tempfile

        measurements = {
            "chest_cm": 102.0,
            "waist_cm": 88.0,
            "hip_cm": 100.0,
            "shoulder_width_cm": 46.0,
        }

        # BTFGenerator requires an output directory
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = BTFGenerator(output_dir=Path(tmpdir))

            # Generate all formats using available template
            result = generator.generate_all_formats(
                measurements=measurements,
                template_name="basic_tee",  # Use available template
                order_id="TEST-001",
            )

            self.assertIsNotNone(result)
            # Format C commands should exist
            self.assertIsNotNone(result.format_c_commands)

            logger.info(
                f"BTF generation test passed - {len(result.format_c_commands)} commands generated"
            )

    def test_optitex_config(self):
        """Test Optitex configuration loading."""
        from blackbox.generation.optitex_automation.config import OptitexConfig

        config = OptitexConfig()

        # Should have defaults
        self.assertFalse(config.enabled)  # Disabled by default
        self.assertIsNotNone(config.pds_exe)  # Has default path

        # is_available should return False without Optitex installed
        self.assertFalse(config.is_available())

        logger.info(
            f"Optitex config: enabled={config.enabled}, available={config.is_available()}"
        )

    def test_batch_script_generation(self):
        """Test batch script generation for Optitex."""
        from blackbox.generation.optitex_automation.batch_generator import (
            BatchGenerator,
        )
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = BatchGenerator(output_dir=Path(tmpdir))

            # Generate a pattern from measurements script
            script_path = generator.generate_pattern_from_measurements(
                measurements={"chest": 102.0, "waist": 88.0},
                style_template=Path("template.pds"),
                output_path=Path(tmpdir) / "output.pds",
                order_id="TEST-002",
            )

            self.assertIsNotNone(script_path)
            self.assertTrue(script_path.exists())

            # Read and verify content
            content = script_path.read_text()
            self.assertIn("template.pds", content)

            logger.info("Batch script generation test passed")


class TestWorkerBlackBoxIntegration(unittest.TestCase):
    """Test that nesting worker can handle BlackBox orders."""

    def test_worker_handles_blackbox_source(self):
        """Test worker correctly processes orders with blackbox source."""
        from workers.nesting_worker import NestingWorker

        # Create order data as it would come from BlackBox Bridge
        blackbox_order = {
            "order_id": "BB-E2E-001-20260201",
            "customer_id": "E2E-TEST",
            "garment_type": "tee",
            "fit_type": "regular",
            "source": "blackbox_scan",
            "measurements": {
                "chest_cm": 102.0,
                "waist_cm": 88.0,
                "hip_cm": 100.0,
                "shoulder_width_cm": 46.0,
                "arm_length_cm": 64.0,
                "source": "blackbox_scan",
            },
            "confidence_score": 0.95,
            "blackbox_processing_time_ms": 1250.0,
        }

        # Create worker
        worker = NestingWorker(worker_id="test-worker")

        # Test order object creation
        order = worker._create_order_object(blackbox_order)

        self.assertEqual(order.order_id, "BB-E2E-001-20260201")
        self.assertEqual(order.customer_id, "E2E-TEST")
        self.assertEqual(order.measurements.chest_cm, 102.0)
        self.assertEqual(order.measurements.source, "blackbox_scan")

        logger.info("Worker handles BlackBox order format correctly")


class TestDataFlow(unittest.TestCase):
    """Test data flows correctly through the entire system."""

    def test_measurement_preservation(self):
        """Verify measurements are preserved through the pipeline."""
        from integrations.blackbox_bridge import BlackBoxBridge

        original_measurements = {
            "chest_cm": 102.5,
            "waist_cm": 88.3,
            "hip_cm": 100.7,
        }

        bridge = BlackBoxBridge(queue=None, validate_files=False)

        # Format for queue
        from integrations.blackbox_bridge import BlackBoxOutput, InputSource

        output = BlackBoxOutput(
            order_id="TEST-001",
            customer_id="CUST-001",
            measurements=original_measurements,
            garment_type="tee",
            source=InputSource.BLACKBOX_SCAN,
        )

        queue_data = bridge._to_queue_format(output)

        # Verify measurements are preserved exactly
        self.assertEqual(
            queue_data["measurements"]["chest_cm"],
            original_measurements["chest_cm"],
        )
        self.assertEqual(
            queue_data["measurements"]["waist_cm"],
            original_measurements["waist_cm"],
        )
        self.assertEqual(
            queue_data["measurements"]["hip_cm"],
            original_measurements["hip_cm"],
        )

        logger.info("Measurement preservation verified")


def run_tests():
    """Run all end-to-end tests with summary."""
    print("=" * 70)
    print("END-TO-END BLACKBOX INTEGRATION TESTS")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes in order
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestBlackBoxPipelineWithMocks))
    suite.addTests(loader.loadTestsFromTestCase(TestBlackBoxOptitexIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkerBlackBoxIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFlow))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    success_rate = (
        (result.testsRun - len(result.failures) - len(result.errors))
        / result.testsRun
        * 100
        if result.testsRun > 0
        else 0
    )
    print(f"Success rate: {success_rate:.1f}%")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
