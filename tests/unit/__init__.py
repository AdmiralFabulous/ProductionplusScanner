"""
Unit Tests Package for PRODUCTION-SCANNER.

This package contains unit tests for individual components, modules,
and functions of the PRODUCTION-SCANNER system.

Test Organization:
    - test_models/: Database model tests
    - test_services/: Service layer tests
    - test_utils/: Utility function tests
    - test_validation/: Input validation tests

Guidelines:
    - Each test should test a single unit of functionality
    - Use mocks for external dependencies
    - Fast execution (< 100ms per test)
    - No database or network I/O

Reference: Ops Manual v6.8 Section 13 (Testing Infrastructure)
"""

__version__ = "1.0.0"
