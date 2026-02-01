"""
Prometheus Metrics for SameDaySuits Pattern Factory

Exposes metrics at /metrics endpoint for Prometheus scraping.

Metrics:
- sds_orders_total: Counter of orders by status and garment type
- sds_order_processing_seconds: Histogram of processing times
- sds_nesting_utilization_percent: Histogram of fabric utilization
- sds_queue_length: Gauge of queue depth by priority
- sds_active_workers: Gauge of active worker count
- sds_dlq_size: Gauge of dead letter queue size
- sds_circuit_breaker_state: Gauge of circuit breaker states

Author: Claude
Date: 2026-02-01
"""

from typing import Optional, Tuple

# Try to import prometheus_client, provide stubs if not available
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Info,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Stub classes for when prometheus_client is not installed
    class StubMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            pass

        def dec(self, amount=1):
            pass

        def set(self, value):
            pass

        def observe(self, value):
            pass

        def info(self, val):
            pass

    Counter = Histogram = Gauge = Info = StubMetric
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest():
        return b"# prometheus_client not installed\n"


# =============================================================================
# Counters (monotonically increasing)
# =============================================================================

ORDERS_TOTAL = Counter(
    "sds_orders_total", "Total orders processed", ["status", "garment_type"]
)

FAILURES_TOTAL = Counter(
    "sds_failures_total",
    "Total failures by type",
    ["type"],  # db_error, queue_error, processing_error, validation_error
)

# =============================================================================
# Histograms (distributions)
# =============================================================================

PROCESSING_TIME = Histogram(
    "sds_order_processing_seconds",
    "Order processing time in seconds",
    buckets=[10, 30, 60, 90, 120, 180, 300, 600],
)

NESTING_UTILIZATION = Histogram(
    "sds_nesting_utilization_percent",
    "Fabric utilization percentage",
    buckets=[50, 60, 70, 75, 80, 85, 90, 95, 100],
)

FABRIC_LENGTH = Histogram(
    "sds_fabric_length_cm",
    "Fabric length per order in cm",
    buckets=[25, 50, 75, 100, 150, 200, 300],
)

# =============================================================================
# Gauges (current values)
# =============================================================================

QUEUE_LENGTH = Gauge(
    "sds_queue_length",
    "Current orders in queue",
    ["priority"],  # rush, high, normal, low
)

ACTIVE_WORKERS = Gauge("sds_active_workers", "Number of active worker processes")

DLQ_SIZE = Gauge("sds_dlq_size", "Dead letter queue size")

CIRCUIT_BREAKER_STATE = Gauge(
    "sds_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["service"],  # database, redis
)

# =============================================================================
# Info (static metadata)
# =============================================================================

BUILD_INFO = Info("sds_build", "Build information")
if PROMETHEUS_AVAILABLE:
    BUILD_INFO.info({"version": "6.4.3", "phase": "3", "component": "pattern-factory"})


# =============================================================================
# Helper Functions
# =============================================================================


def get_metrics() -> Tuple[bytes, str]:
    """
    Return Prometheus metrics in text format.

    Returns:
        Tuple of (content bytes, content type string)
    """
    return generate_latest(), CONTENT_TYPE_LATEST


def update_queue_metrics(queue) -> None:
    """
    Update queue-related metrics from OrderQueue instance.

    Args:
        queue: OrderQueue instance (from scalability module)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    if queue and hasattr(queue, "is_available") and queue.is_available:
        try:
            stats = queue.get_stats()

            # Update queue length gauges
            # Note: Current queue doesn't track by priority, using total for 'normal'
            QUEUE_LENGTH.labels(priority="rush").set(0)
            QUEUE_LENGTH.labels(priority="high").set(0)
            QUEUE_LENGTH.labels(priority="normal").set(getattr(stats, "queued", 0))
            QUEUE_LENGTH.labels(priority="low").set(0)

            # Update DLQ size
            DLQ_SIZE.set(getattr(stats, "dlq", 0))

            # Update active workers
            workers = queue.get_active_workers()
            ACTIVE_WORKERS.set(len(workers) if workers else 0)

        except Exception:
            pass  # Metrics update failure shouldn't crash the app


def record_order_complete(
    garment_type: str, processing_time_sec: float, utilization: float, fabric_cm: float
) -> None:
    """
    Record metrics for a successfully completed order.

    Args:
        garment_type: Type of garment (tee, jacket, etc.)
        processing_time_sec: Processing time in seconds
        utilization: Fabric utilization percentage (0-100)
        fabric_cm: Fabric length in centimeters
    """
    if not PROMETHEUS_AVAILABLE:
        return

    ORDERS_TOTAL.labels(status="success", garment_type=garment_type).inc()
    PROCESSING_TIME.observe(processing_time_sec)
    NESTING_UTILIZATION.observe(utilization)
    FABRIC_LENGTH.observe(fabric_cm)


def record_order_failed(garment_type: str, failure_type: str) -> None:
    """
    Record metrics for a failed order.

    Args:
        garment_type: Type of garment (tee, jacket, etc.)
        failure_type: Type of failure (db_error, queue_error, processing_error, validation_error)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    ORDERS_TOTAL.labels(status="failed", garment_type=garment_type).inc()
    FAILURES_TOTAL.labels(type=failure_type).inc()


def set_circuit_breaker_state(service: str, state: str) -> None:
    """
    Update circuit breaker state metric.

    Args:
        service: Service name (database, redis)
        state: Circuit state (closed, open, half-open)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    state_map = {"closed": 0, "open": 1, "half-open": 2}
    CIRCUIT_BREAKER_STATE.labels(service=service).set(state_map.get(state, 0))
