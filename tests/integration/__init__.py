"""
Integration Tests Package for PRODUCTION-SCANNER.

This package contains integration tests for API endpoints, database
interactions, service communications, and external integrations.

Test Organization:
    - test_api/: API endpoint integration tests
    - test_database/: Database integration tests
    - test_redis/: Redis cache integration tests
    - test_cutter/: Cutter hardware integration tests
    - test_auth/: Authentication integration tests

Guidelines:
    - Test interactions between components
    - Use test database and Redis instances
    - Mock external services only when necessary
    - Medium execution time (< 5s per test)

Reference: Ops Manual v6.8 Section 13 (Testing Infrastructure)
"""

__version__ = "1.0.0"
