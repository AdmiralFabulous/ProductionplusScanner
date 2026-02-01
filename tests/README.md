# PRODUCTION-SCANNER Test Suite

Comprehensive test suite for the SameDaySuits PRODUCTION-SCANNER system.

## Reference

- **Ops Manual v6.8**: Section 13 (Testing Infrastructure)
- **Ops Manual v6.8**: Section 17 (Journey Mapping)
- **Ops Manual v6.8**: Section 2.6 (Scalability Layer)

## Test Structure

```
tests/
├── README.md                  # This file
├── conftest.py               # Shared fixtures and configuration
├── pytest.ini               # Pytest configuration
├── requirements-test.txt    # Test dependencies
├── e2e/                     # End-to-End Tests
│   ├── __init__.py
│   ├── test_customer_journey.py   # Complete customer journey
│   ├── test_tailor_journey.py     # Tailor platform journey
│   └── test_qc_journey.py         # QC inspector journey
├── integration/             # Integration Tests
├── performance/             # Performance Tests
│   ├── __init__.py
│   ├── locustfile.py       # Locust load testing
│   ├── test_api_performance.py    # API response times
│   └── test_load_patterns.py      # Load and throughput tests
└── unit/                    # Unit Tests
```

## Quick Start

### Install Dependencies

```bash
cd tests
pip install -r requirements-test.txt

# For Locust load testing
pip install locust
```

### Run Tests

```bash
# Run all tests
cd tests
pytest

# Run E2E tests only
pytest -m e2e

# Run performance tests
pytest -m performance

# Run specific test file
pytest e2e/test_customer_journey.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=../src --cov-report=html
```

### Run Load Tests with Locust

```bash
# Web UI mode
cd tests/performance
locust -f locustfile.py --host=http://localhost:8000

# Headless mode
locust -f locustfile.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 10 --run-time 10m --headless

# Specific scenario
locust -f locustfile.py --host=http://localhost:8000 \
       --users 50 --spawn-rate 5 --run-time 5m --headless \
       --html=report.html
```

## E2E Tests

### Customer Journey (`test_customer_journey.py`)

Tests the complete customer journey from opening EYESON to downloading patterns:

1. **Welcome Screen**: EYESON loads, voice prompts available
2. **Camera Permissions**: Session initialization (< 500ms)
3. **Voice Guidance**: Kokoro TTS synthesis (< 2s)
4. **90-Second Scan**: Complete scan cycle
5. **Review Measurements**: 28 measurements, P0 confidence ≥ 0.85
6. **Submit to Pattern Factory**: Order creation, S02→S03 transition
7. **Poll for Pattern**: Pattern generation (< 3 min p99)
8. **Download Files**: PLT, PDS, DXF (< 5s each)

**Run:**
```bash
pytest e2e/test_customer_journey.py -v
```

### Tailor Journey (`test_tailor_journey.py`)

Tests the tailor platform workflow:

1. **Pattern on Job Board**: S08 (STAGING) orders visible
2. **Claim Order**: S08→S09 transition (< 500ms)
3. **Pattern Dispatched**: S10 (STAGING2)
4. **Pattern in Transit**: S11 (SEWING)
5. **Pattern Received**: S12 (ASSEMBLY)
6. **Production Started**: S13 (FINISHING)
7. **Ready for QC**: S14 (READY_FOR_PICKUP)

**SLA Targets:**
- S08 (Staging): < 30 min
- S09 (QA): < 15 min
- S10 (Staging2): < 1 hour
- S11 (Sewing): < 4 hours
- S12 (Assembly): < 2 hours
- S13 (Finishing): < 1 hour

**Run:**
```bash
pytest e2e/test_tailor_journey.py -v
```

### QC Journey (`test_qc_journey.py`)

Tests the QC inspector workflow:

1. **Garment Received**: S14a (QC_RECEIVED)
2. **Inspection**: S15 (QC_INSPECTION) - < 15 min SLA
3. **QC Pass**: S16 (QC_PASSED) → labeling → packing
4. **QC Fail**: S17 (QC_FAILED) → dispute process

**Scenarios:**
- Complete inspection with pass/fail
- Multiple defects documentation
- Partial inspection save/resume
- Inspection reassignment

**Run:**
```bash
pytest e2e/test_qc_journey.py -v
```

## Performance Tests

### API Performance (`test_api_performance.py`)

Tests API response times and performance:

| Metric | Target | Test |
|--------|--------|------|
| API Response (p95) | < 100ms | `test_endpoint_response_time_p95` |
| API Response (p99) | < 200ms | `test_order_creation_response_time_distribution` |
| Pattern Generation (p99) | < 3 min | `test_pattern_generation_time_p99` |
| File Download | < 5s | `test_plt_download_time` |
| Concurrent Users | 100 | `test_concurrent_order_creation` |

**Run:**
```bash
pytest performance/test_api_performance.py -v
```

### Load Patterns (`test_load_patterns.py`)

Tests system under various load patterns:

| Test | Target | Description |
|------|--------|-------------|
| Sustained Throughput | 100 orders/hour | `test_sustained_order_throughput` |
| Burst Load | 50 orders/30s | `test_burst_load_handling` |
| Ramp-up | Gradual increase | `test_ramp_up_pattern` |
| Cutter Queue | 60 patterns/hour | `test_cutter_queue_throughput` |
| DB Query (p95) | < 50ms | `test_order_lookup_query_performance` |
| Cache Hit Rate | > 90% | `test_cache_hit_rate` |

**Run:**
```bash
pytest performance/test_load_patterns.py -v
```

## Performance Baselines

Based on Ops Manual v6.8 Section 2.6:

```python
PERFORMANCE_TARGETS = {
    # API
    "api_response_p95_ms": 100,
    "api_response_p99_ms": 200,
    
    # Pattern Generation
    "pattern_generation_p99_s": 180,  # 3 minutes
    
    # File Downloads
    "file_download_max_s": 5,
    
    # Throughput
    "orders_per_hour": 100,
    "cutter_patterns_per_hour": 60,
    "garments_qc_per_hour": 60,
    
    # Database
    "db_query_p95_ms": 50,
    
    # Cache
    "redis_cache_hit_rate": 0.90,
    
    # Concurrent Users
    "concurrent_users_supported": 100,
}
```

## Test Markers

| Marker | Description | Usage |
|--------|-------------|-------|
| `e2e` | End-to-end tests | `pytest -m e2e` |
| `performance` | Performance tests | `pytest -m performance` |
| `slow` | Slow running tests | `pytest -m slow` |
| `benchmark` | Benchmark tests | `pytest -m benchmark` |
| `unit` | Unit tests | `pytest -m unit` |
| `integration` | Integration tests | `pytest -m integration` |

## State Machine Test Coverage

Tests cover all 27 states from the Order State Machine:

```
S01 ORDER_CREATED → S02 RECEIVED → S03 SCAN_RECEIVED
                                        ↓
S04 PROCESSING → S04a VALIDATION → S05 PATTERN_READY
                                        ↓
S06 CUTTING → S06a QUEUE_WAIT → S07 PATTERN_CUT
                                        ↓
S08 STAGING → S09 QA → S10 STAGING2 → S11 SEWING
                                        ↓
S12 ASSEMBLY → S13 FINISHING → S14 READY_FOR_PICKUP
                                        ↓
                    ┌───────────────────┼───────────────────┐
                    ↓                   ↓                   ↓
                S15 PICKED_UP      S16 SHIPPING        S18 ALTERATIONS
                    ↓                   ↓                   ↓
                [TERMINAL]       S17 DELIVERED       S19 COMPLETED
                                        [TERMINAL]          [TERMINAL]
                    
S14 → S20 CANCELLED → S21 REFUND_PROCESSING → S22 CLOSED [TERMINAL]
```

## CI/CD Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run E2E Tests
  run: |
    cd tests
    pytest e2e/ -v --tb=short
    
- name: Run Performance Tests
  run: |
    cd tests
    pytest performance/ -v --tb=short -m "not slow"
    
- name: Run Load Tests
  run: |
    cd tests/performance
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 10 --spawn-rate 1 --run-time 2m --headless
```

## Troubleshooting

### Test Timeouts

If tests timeout, increase timeout in pytest.ini or run specific tests:

```bash
pytest e2e/test_customer_journey.py::TestCustomerJourney::test_step_1_welcome_screen -v
```

### Connection Refused

Ensure services are running:

```bash
# Pattern Factory
cd pattern-factory && python -m src.api.web_api

# EYESON Backend
cd eyeson/backend && python -m src.main
```

### Locust Not Found

Install locust:

```bash
pip install locust
```

## Contributing

When adding new tests:

1. Follow the existing naming convention: `test_<feature>_<scenario>.py`
2. Add appropriate markers: `@pytest.mark.e2e`, `@pytest.mark.performance`
3. Include docstrings referencing Ops Manual sections
4. Update this README with new test documentation
5. Run full test suite before committing

## License

Internal Use Only - SameDaySuits
