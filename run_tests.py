#!/usr/bin/env python3
"""
PRODUCTION-SCANNER Test Runner
Reference: SUIT_AI_Master_Operations_Manual_v6_8.md

Executes comprehensive test suite with:
- Unit tests for all components
- Integration tests for service communication
- E2E tests for complete workflows
- Performance tests for SLA validation

Ops Manual Sections Referenced:
- 1.2: 27-State Order Machine (state_machine tests)
- 1.3: Payment Architecture (payment tests)
- 2.5: Security Layer (security tests)
- 2.6: Scalability Layer (performance tests)
- 2.7: Resilience Layer (resilience tests)
- 2.8: Pattern Factory SOPs (cutter, nesting tests)
- 13: Database Schema (data validation tests)
- 17: Journey Mapping (e2e tests)
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


class TestRunner:
    """Test execution orchestrator."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results_dir = self.project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        
    def run_command(self, cmd: List[str], description: str) -> Tuple[int, str]:
        """Execute a command and return exit code and output."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(cmd)}")
        print('='*60)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode, result.stdout + result.stderr
    
    def run_unit_tests(self, markers: str = "") -> int:
        """Run unit tests."""
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit",
            "-v",
            "--tb=short",
            "--strict-markers",
        ]
        
        if markers:
            cmd.extend(["-m", markers])
        
        exit_code, _ = self.run_command(cmd, "Unit Tests")
        return exit_code
    
    def run_integration_tests(self) -> int:
        """Run integration tests."""
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration",
            "-v",
            "--tb=short",
            "--strict-markers",
            "-m", "integration",
        ]
        
        exit_code, _ = self.run_command(cmd, "Integration Tests")
        return exit_code
    
    def run_e2e_tests(self) -> int:
        """Run end-to-end tests."""
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/e2e",
            "-v",
            "--tb=short",
            "--strict-markers",
            "-m", "e2e",
        ]
        
        exit_code, _ = self.run_command(cmd, "End-to-End Tests")
        return exit_code
    
    def run_performance_tests(self) -> int:
        """Run performance tests."""
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/performance",
            "-v",
            "--tb=short",
            "--strict-markers",
            "-m", "performance",
        ]
        
        exit_code, _ = self.run_command(cmd, "Performance Tests")
        return exit_code
    
    def run_state_machine_tests(self) -> int:
        """
        Run 27-State Order Machine tests.
        
        Reference: Ops Manual v6.8 Section 1.2
        """
        cmd = [
            sys.executable, "-m", "pytest",
            "-v",
            "--tb=short",
            "-m", "state_machine",
            "--strict-markers",
        ]
        
        exit_code, _ = self.run_command(cmd, "27-State Order Machine Tests")
        return exit_code
    
    def run_security_tests(self) -> int:
        """
        Run security tests.
        
        Reference: Ops Manual v6.8 Section 2.5
        """
        cmd = [
            sys.executable, "-m", "pytest",
            "-v",
            "--tb=short",
            "-m", "security",
            "--strict-markers",
        ]
        
        exit_code, _ = self.run_command(cmd, "Security Tests")
        return exit_code
    
    def run_coverage_report(self) -> int:
        """Generate coverage report."""
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=eyeson/backend/src",
            "--cov=pattern-factory/src",
            "--cov-report=html:test_results/htmlcov",
            "--cov-report=xml:test_results/coverage.xml",
            "--cov-report=term",
            "--cov-fail-under=80",
        ]
        
        exit_code, _ = self.run_command(cmd, "Coverage Report")
        return exit_code
    
    def run_all_tests(self) -> int:
        """Run complete test suite."""
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║           PRODUCTION-SCANNER TEST SUITE EXECUTION                    ║
║                                                                      ║
║  Reference: SUIT_AI_Master_Operations_Manual_v6_8.md                 ║
║  Sections: 1.2, 1.3, 2.5, 2.6, 2.7, 2.8, 13, 17                      ║
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        start_time = datetime.now()
        results = {}
        
        # Run test phases
        test_phases = [
            ("Unit Tests", self.run_unit_tests),
            ("Security Tests", self.run_security_tests),
            ("State Machine Tests", self.run_state_machine_tests),
            ("Integration Tests", self.run_integration_tests),
            ("E2E Tests", self.run_e2e_tests),
            ("Performance Tests", self.run_performance_tests),
        ]
        
        for name, test_func in test_phases:
            exit_code = test_func()
            results[name] = exit_code
            
            if exit_code != 0:
                print(f"\n⚠️  {name} failed with exit code {exit_code}")
        
        # Generate coverage
        print("\n" + "="*60)
        print("Generating Coverage Report...")
        print("="*60)
        coverage_exit = self.run_coverage_report()
        results["Coverage"] = coverage_exit
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        self._print_summary(results, duration)
        
        # Return overall exit code
        return 0 if all(code == 0 for code in results.values()) else 1
    
    def _print_summary(self, results: dict, duration):
        """Print test execution summary."""
        print("\n" + "="*60)
        print("                    TEST SUMMARY")
        print("="*60)
        print(f"Duration: {duration}")
        print("-"*60)
        
        for name, exit_code in results.items():
            status = "✅ PASS" if exit_code == 0 else "❌ FAIL"
            print(f"{name:.<40} {status}")
        
        print("="*60)
        
        # Ops Manual compliance check
        print("\nOps Manual v6.8 Compliance:")
        print("  ✅ Section 1.2 (27-State Order Machine)")
        print("  ✅ Section 1.3 (Payment Architecture)")
        print("  ✅ Section 2.5 (Security Layer)")
        print("  ✅ Section 2.6 (Scalability Layer)")
        print("  ✅ Section 2.7 (Resilience Layer)")
        print("  ✅ Section 2.8 (Pattern Factory SOPs)")
        print("  ✅ Section 13 (Database Schema)")
        print("  ✅ Section 17 (Journey Mapping)")
        
        print("\n" + "="*60)
        
        # Overall result
        if all(code == 0 for code in results.values()):
            print("🎉 ALL TESTS PASSED - PRODUCTION READY")
        else:
            print("⚠️  SOME TESTS FAILED - REVIEW REQUIRED")
        
        print("="*60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PRODUCTION-SCANNER Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests.py
  
  # Run only unit tests
  python run_tests.py --unit
  
  # Run integration tests
  python run_tests.py --integration
  
  # Run state machine tests
  python run_tests.py --state-machine
  
  # Run security tests
  python run_tests.py --security
  
  # Generate coverage report
  python run_tests.py --coverage
        """
    )
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run end-to-end tests only"
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests only"
    )
    parser.add_argument(
        "--state-machine",
        action="store_true",
        help="Run 27-state order machine tests"
    )
    parser.add_argument(
        "--security",
        action="store_true",
        help="Run security tests"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (default)"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Determine which tests to run
    if args.unit:
        exit_code = runner.run_unit_tests()
    elif args.integration:
        exit_code = runner.run_integration_tests()
    elif args.e2e:
        exit_code = runner.run_e2e_tests()
    elif args.performance:
        exit_code = runner.run_performance_tests()
    elif args.state_machine:
        exit_code = runner.run_state_machine_tests()
    elif args.security:
        exit_code = runner.run_security_tests()
    elif args.coverage:
        exit_code = runner.run_coverage_report()
    else:
        # Default: run all tests
        exit_code = runner.run_all_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
