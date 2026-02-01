#!/usr/bin/env python3
"""
Production Monitoring System for SameDaySuits

This module provides comprehensive monitoring for the production pipeline:
1. Real-time metrics collection
2. Historical data tracking
3. Alerting for anomalies
4. Performance analytics
5. Health checks

Author: Claude
Date: 2026-01-31
"""

import json
import time
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from collections import defaultdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProductionMonitor")


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class OrderMetrics:
    """Metrics for a single order."""

    order_id: str
    garment_type: str
    timestamp: str  # ISO format string
    success: bool
    processing_time_seconds: float
    nesting_utilization: float
    fabric_length_cm: float
    piece_count: int
    error_message: str = ""


@dataclass
class Alert:
    """An alert triggered by a condition."""

    id: str
    severity: str
    title: str
    message: str
    timestamp: str
    metric_name: str
    metric_value: float
    threshold: float
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class ProductionStats:
    """Aggregated production statistics."""

    period_start: str
    period_end: str
    orders_total: int = 0
    orders_success: int = 0
    orders_failed: int = 0
    avg_utilization: float = 0.0
    min_utilization: float = 0.0
    max_utilization: float = 0.0
    total_fabric_cm: float = 0.0
    avg_processing_time: float = 0.0


class ProductionMonitor:
    """
    Main production monitoring class.

    Tracks orders, metrics, alerts, and provides dashboard data.
    """

    def __init__(self, data_dir: str = "monitoring_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self._orders: List[OrderMetrics] = []
        self._alerts: List[Alert] = []
        self._gauges: Dict[str, float] = {}
        self._counters: Dict[str, int] = defaultdict(int)

        self._load_historical_data()

    def _load_historical_data(self):
        """Load historical orders from disk."""
        orders_file = self.data_dir / "orders_history.json"
        if orders_file.exists():
            try:
                with open(orders_file) as f:
                    data = json.load(f)
                    self._orders = [OrderMetrics(**item) for item in data]
                logger.info(f"Loaded {len(self._orders)} historical orders")
            except Exception as e:
                logger.error(f"Failed to load history: {e}")

    def _save_historical_data(self):
        """Save orders to disk."""
        orders_file = self.data_dir / "orders_history.json"
        try:
            # Keep last 10K orders
            data = [asdict(o) for o in self._orders[-10000:]]
            with open(orders_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def record_order_processed(
        self,
        order_id: str,
        garment_type: str,
        success: bool,
        processing_time: float,
        utilization: float = 0,
        fabric_length: float = 0,
        piece_count: int = 0,
        error: str = "",
    ):
        """Record that an order was processed."""
        order = OrderMetrics(
            order_id=order_id,
            garment_type=garment_type,
            timestamp=datetime.now().isoformat(),
            success=success,
            processing_time_seconds=processing_time,
            nesting_utilization=utilization,
            fabric_length_cm=fabric_length,
            piece_count=piece_count,
            error_message=error,
        )
        self._orders.append(order)

        # Update counters
        self._counters["orders_total"] += 1
        self._counters[f"orders_{garment_type}"] += 1
        if success:
            self._counters["orders_success"] += 1
        else:
            self._counters["orders_failed"] += 1

        # Save periodically
        if len(self._orders) % 10 == 0:
            self._save_historical_data()

        logger.info(
            f"Order {order_id}: {'OK' if success else 'FAIL'} - {utilization:.1f}%"
        )

    def update_queue_status(self, pending: int, processing: int, completed: int):
        """Update queue status gauges."""
        self._gauges["queue_pending"] = pending
        self._gauges["queue_processing"] = processing
        self._gauges["queue_completed"] = completed

    def get_orders(self, hours: int = 24, garment: str = None) -> List[OrderMetrics]:
        """Get orders from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()

        result = [o for o in self._orders if o.timestamp >= cutoff_str]
        if garment:
            result = [o for o in result if o.garment_type == garment]
        return result

    def get_production_stats(self, hours: int = 24) -> ProductionStats:
        """Get aggregated statistics for the last N hours."""
        orders = self.get_orders(hours)
        now = datetime.now()

        stats = ProductionStats(
            period_start=(now - timedelta(hours=hours)).isoformat(),
            period_end=now.isoformat(),
            orders_total=len(orders),
            orders_success=sum(1 for o in orders if o.success),
            orders_failed=sum(1 for o in orders if not o.success),
        )

        successful = [o for o in orders if o.success]
        if successful:
            utils = [o.nesting_utilization for o in successful]
            stats.avg_utilization = statistics.mean(utils)
            stats.min_utilization = min(utils)
            stats.max_utilization = max(utils)
            stats.total_fabric_cm = sum(o.fabric_length_cm for o in successful)
            stats.avg_processing_time = statistics.mean(
                o.processing_time_seconds for o in successful
            )

        return stats

    def check_alerts(self):
        """Check for alert conditions."""
        orders = self.get_orders(hours=1)

        if len(orders) >= 5:
            successful = [o for o in orders if o.success]
            if successful:
                avg_util = statistics.mean(o.nesting_utilization for o in successful)

                # Low utilization alert
                if avg_util < 70:
                    self._add_alert(
                        "low_utilization",
                        AlertSeverity.WARNING,
                        "Low Utilization",
                        f"Average nesting utilization is {avg_util:.1f}% (below 70%)",
                        "nesting_utilization",
                        avg_util,
                        70,
                    )

            # High failure rate alert
            fail_rate = sum(1 for o in orders if not o.success) / len(orders)
            if fail_rate > 0.1:
                self._add_alert(
                    "high_failure",
                    AlertSeverity.CRITICAL,
                    "High Failure Rate",
                    f"Order failure rate is {fail_rate * 100:.1f}% (above 10%)",
                    "failure_rate",
                    fail_rate,
                    0.1,
                )

        # Queue backup alert
        pending = self._gauges.get("queue_pending", 0)
        if pending > 50:
            self._add_alert(
                "queue_backup",
                AlertSeverity.WARNING,
                "Queue Backup",
                f"{int(pending)} orders pending (above 50)",
                "queue_pending",
                pending,
                50,
            )

    def _add_alert(
        self,
        alert_id: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        metric: str,
        value: float,
        threshold: float,
    ):
        """Add an alert if not already active."""
        # Check if already exists
        for alert in self._alerts:
            if alert.id == alert_id and not alert.resolved:
                return

        alert = Alert(
            id=alert_id,
            severity=severity.value,
            title=title,
            message=message,
            timestamp=datetime.now().isoformat(),
            metric_name=metric,
            metric_value=value,
            threshold=threshold,
        )
        self._alerts.append(alert)
        logger.warning(f"ALERT [{severity.value}]: {title}")

    def get_active_alerts(self) -> List[Alert]:
        """Get unresolved alerts."""
        return [a for a in self._alerts if not a.resolved]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.resolved = True
                return True
        return False

    def health_check(self) -> Dict[str, Any]:
        """Run health checks."""
        checks = {}

        # Check disk space
        try:
            import shutil

            total, used, free = shutil.disk_usage(self.data_dir)
            free_gb = free / (1024**3)
            checks["disk_space"] = {
                "healthy": free_gb > 1,
                "message": f"{free_gb:.1f} GB free",
            }
        except:
            checks["disk_space"] = {"healthy": True, "message": "Check skipped"}

        # Check recent activity
        stats = self.get_production_stats(1)
        if stats.orders_total == 0:
            checks["recent_activity"] = {
                "healthy": True,
                "message": "No orders in last hour",
            }
        elif stats.orders_failed > stats.orders_success:
            checks["recent_activity"] = {
                "healthy": False,
                "message": f"High failure rate: {stats.orders_failed}/{stats.orders_total}",
            }
        else:
            checks["recent_activity"] = {
                "healthy": True,
                "message": f"{stats.orders_total} orders, {stats.orders_success} OK",
            }

        # Overall health
        overall = all(c["healthy"] for c in checks.values())

        return {
            "healthy": overall,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data for a monitoring dashboard."""
        self.check_alerts()

        stats_24h = self.get_production_stats(24)
        stats_1h = self.get_production_stats(1)

        # Utilization distribution
        orders_24h = self.get_orders(24)
        utils = [o.nesting_utilization for o in orders_24h if o.success]

        util_stats = {}
        if utils:
            sorted_utils = sorted(utils)
            util_stats = {
                "count": len(utils),
                "min": min(utils),
                "max": max(utils),
                "avg": statistics.mean(utils),
                "p50": sorted_utils[len(sorted_utils) // 2],
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "health": self.health_check(),
            "alerts": [asdict(a) for a in self.get_active_alerts()],
            "stats_24h": asdict(stats_24h),
            "stats_1h": asdict(stats_1h),
            "queue": {
                "pending": self._gauges.get("queue_pending", 0),
                "processing": self._gauges.get("queue_processing", 0),
                "completed": self._gauges.get("queue_completed", 0),
            },
            "utilization_stats": util_stats,
            "recent_orders": [asdict(o) for o in self._orders[-10:]],
            "counters": dict(self._counters),
        }


# Global instance
_monitor: Optional[ProductionMonitor] = None


def get_monitor() -> ProductionMonitor:
    """Get the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ProductionMonitor()
    return _monitor


def main():
    """Demo the monitoring system."""
    import random

    print("=" * 60)
    print("SameDaySuits Production Monitoring Demo")
    print("=" * 60)

    monitor = get_monitor()

    # Simulate orders
    garments = ["tee", "jacket", "trousers", "cargo"]

    print("\nSimulating 15 orders...")
    for i in range(15):
        success = random.random() > 0.1
        monitor.record_order_processed(
            order_id=f"ORD-{i + 1:04d}",
            garment_type=random.choice(garments),
            success=success,
            processing_time=random.uniform(5, 25),
            utilization=random.uniform(70, 90) if success else 0,
            fabric_length=random.uniform(50, 180) if success else 0,
            piece_count=random.randint(5, 15) if success else 0,
            error="" if success else "Processing error",
        )

    monitor.update_queue_status(pending=5, processing=2, completed=15)

    # Get dashboard data
    print("\n" + "=" * 60)
    print("DASHBOARD")
    print("=" * 60)

    data = monitor.get_dashboard_data()

    health = data["health"]
    print(f"\nSystem Health: {'HEALTHY' if health['healthy'] else 'UNHEALTHY'}")
    for name, check in health["checks"].items():
        status = "OK" if check["healthy"] else "FAIL"
        print(f"  [{status}] {name}: {check['message']}")

    stats = data["stats_24h"]
    print(f"\n24-Hour Statistics:")
    print(
        f"  Orders: {stats['orders_total']} total ({stats['orders_success']} success, {stats['orders_failed']} failed)"
    )
    success_rate = (
        (stats["orders_success"] / stats["orders_total"] * 100)
        if stats["orders_total"] > 0
        else 0
    )
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Avg utilization: {stats['avg_utilization']:.1f}%")
    print(f"  Total fabric: {stats['total_fabric_cm'] / 100:.1f} meters")

    queue = data["queue"]
    print(f"\nQueue Status:")
    print(f"  Pending: {int(queue['pending'])}")
    print(f"  Processing: {int(queue['processing'])}")
    print(f"  Completed: {int(queue['completed'])}")

    alerts = data["alerts"]
    print(f"\nActive Alerts: {len(alerts)}")
    for alert in alerts:
        print(f"  [{alert['severity']}] {alert['title']}: {alert['message']}")

    print(f"\nRecent Orders:")
    for order in data["recent_orders"][-5:]:
        status = "OK" if order["success"] else "FAIL"
        print(
            f"  {order['order_id']}: {order['garment_type']} [{status}] {order['nesting_utilization']:.1f}%"
        )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
