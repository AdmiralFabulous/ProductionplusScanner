#!/usr/bin/env python3
"""
Cutter Operator Dashboard

Web-based GUI for cutter operators to:
- View job queue
- Monitor cutter status
- Trigger reprints
- Track job history

Runs on the laptop next to the Jindex UPC cutter.

Usage:
    python scripts/cutter_dashboard.py --ip 192.168.1.100

    Then open browser to: http://localhost:5000

Author: Claude
Date: 2026-02-01
"""

import os
import sys
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional

# Flask for web interface
try:
    from flask import Flask, render_template_string, jsonify, request, redirect, url_for
except ImportError:
    print("Flask not installed. Run: pip install flask")
    sys.exit(1)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "core"))

try:
    from core.resilient_cutter_queue import (
        ResilientCutterQueue,
        CutterJob,
        JobStatus,
        JobPriority,
    )

    QUEUE_AVAILABLE = True
except ImportError as e:
    QUEUE_AVAILABLE = False
    print(f"Warning: resilient_cutter_queue not found: {e}")


# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)

# Global state
_queue: Optional[ResilientCutterQueue] = None
_cutter_ip: str = "192.168.1.100"
_cutter_port: int = 9100
_last_cutter_status: str = "unknown"
_last_status_check: Optional[datetime] = None


def get_queue() -> Optional[ResilientCutterQueue]:
    global _queue
    if _queue is None and QUEUE_AVAILABLE:
        data_dir = os.environ.get("CUTTER_DATA_DIR", "./cutter_data")
        _queue = ResilientCutterQueue(Path(data_dir))
    return _queue


def check_cutter_status() -> str:
    """Check cutter connection status (cached for 5 seconds)."""
    global _last_cutter_status, _last_status_check

    now = datetime.now()
    if _last_status_check and (now - _last_status_check).seconds < 5:
        return _last_cutter_status

    # Try to connect to cutter
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((_cutter_ip, _cutter_port))
        sock.close()

        if result == 0:
            _last_cutter_status = "connected"
        else:
            _last_cutter_status = "offline"
    except Exception:
        _last_cutter_status = "offline"

    _last_status_check = now
    return _last_cutter_status


# ============================================================================
# HTML TEMPLATE
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cutter Dashboard - SameDaySuits</title>
    <meta http-equiv="refresh" content="10">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #333;
        }
        
        .header h1 {
            font-size: 24px;
            color: #fff;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-connected { background: rgba(46, 204, 113, 0.2); }
        .status-connected .status-dot { background: #2ecc71; }
        
        .status-offline { background: rgba(231, 76, 60, 0.2); }
        .status-offline .status-dot { background: #e74c3c; }
        
        .status-busy { background: rgba(241, 196, 15, 0.2); }
        .status-busy .status-dot { background: #f1c40f; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .stat-card p {
            color: #888;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-queued h3 { color: #3498db; }
        .stat-cutting h3 { color: #f39c12; }
        .stat-complete h3 { color: #2ecc71; }
        .stat-failed h3 { color: #e74c3c; }
        
        .section {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .section h2 {
            font-size: 18px;
            color: #fff;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: #3498db;
            color: #fff;
        }
        
        .btn-primary:hover {
            background: #2980b9;
        }
        
        .btn-danger {
            background: #e74c3c;
            color: #fff;
        }
        
        .btn-success {
            background: #2ecc71;
            color: #fff;
        }
        
        .btn-small {
            padding: 4px 10px;
            font-size: 12px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #2a2a4a;
        }
        
        th {
            color: #888;
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .badge-queued { background: rgba(52, 152, 219, 0.2); color: #3498db; }
        .badge-cutting { background: rgba(243, 156, 18, 0.2); color: #f39c12; }
        .badge-complete { background: rgba(46, 204, 113, 0.2); color: #2ecc71; }
        .badge-error { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
        .badge-rush { background: rgba(155, 89, 182, 0.2); color: #9b59b6; }
        .badge-high { background: rgba(230, 126, 34, 0.2); color: #e67e22; }
        
        .time-ago {
            color: #666;
            font-size: 12px;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .search-box input {
            flex: 1;
            padding: 10px 15px;
            border: 1px solid #333;
            border-radius: 6px;
            background: #1a1a2e;
            color: #fff;
            font-size: 14px;
        }
        
        .search-box input:focus {
            outline: none;
            border-color: #3498db;
        }
        
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 100;
            align-items: center;
            justify-content: center;
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal {
            background: #16213e;
            border-radius: 12px;
            padding: 25px;
            width: 400px;
            max-width: 90%;
        }
        
        .modal h3 {
            margin-bottom: 15px;
        }
        
        .modal textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 6px;
            background: #1a1a2e;
            color: #fff;
            resize: vertical;
            min-height: 80px;
            margin-bottom: 15px;
        }
        
        .modal-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        
        .refresh-indicator {
            font-size: 12px;
            color: #666;
        }
        
        .cutter-info {
            font-size: 12px;
            color: #666;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Cutter Dashboard</h1>
        <div class="status-bar">
            <span class="cutter-info">{{ cutter_ip }}:{{ cutter_port }}</span>
            <span class="refresh-indicator">Auto-refresh: 10s</span>
            <div class="status-indicator status-{{ cutter_status_class }}">
                <span class="status-dot"></span>
                <span>Cutter: {{ cutter_status }}</span>
            </div>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card stat-queued">
            <h3>{{ stats.queued }}</h3>
            <p>In Queue</p>
        </div>
        <div class="stat-card stat-cutting">
            <h3>{{ stats.cutting }}</h3>
            <p>Cutting</p>
        </div>
        <div class="stat-card stat-complete">
            <h3>{{ stats.completed_today }}</h3>
            <p>Completed</p>
        </div>
        <div class="stat-card stat-failed">
            <h3>{{ stats.failed }}</h3>
            <p>Failed</p>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">
            <h2>Job Queue</h2>
            <a href="/refresh" class="btn btn-primary btn-small">Refresh</a>
        </div>
        
        {% if queue_jobs %}
        <table>
            <thead>
                <tr>
                    <th>Order</th>
                    <th>Job ID</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Pieces</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for job in queue_jobs %}
                <tr>
                    <td><strong>{{ job.order_id }}</strong></td>
                    <td style="font-family: monospace; font-size: 11px;">{{ job.job_id[:25] }}...</td>
                    <td>
                        {% if job.priority == 'RUSH' %}
                        <span class="badge badge-rush">RUSH</span>
                        {% elif job.priority == 'HIGH' %}
                        <span class="badge badge-high">HIGH</span>
                        {% else %}
                        {{ job.priority }}
                        {% endif %}
                    </td>
                    <td>
                        <span class="badge badge-{{ job.status|lower }}">{{ job.status }}</span>
                    </td>
                    <td>{{ job.piece_count }}</td>
                    <td class="time-ago">{{ job.created_ago }}</td>
                    <td>
                        {% if job.status == 'QUEUED' %}
                        <a href="/cancel/{{ job.job_id }}" class="btn btn-danger btn-small" onclick="return confirm('Cancel this job?')">Cancel</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state">
            <p>No jobs in queue - all caught up!</p>
        </div>
        {% endif %}
    </div>
    
    <div class="section">
        <div class="section-header">
            <h2>Recent Jobs</h2>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search by order ID..." onkeyup="filterJobs()">
        </div>
        
        {% if recent_jobs %}
        <table id="recentJobsTable">
            <thead>
                <tr>
                    <th>Order</th>
                    <th>Status</th>
                    <th>Completed</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for job in recent_jobs %}
                <tr data-order="{{ job.order_id|lower }}">
                    <td>
                        <strong>{{ job.order_id }}</strong>
                        {% if job.is_reprint %}<span class="badge" style="background: rgba(155, 89, 182, 0.2); color: #9b59b6; margin-left: 5px;">REPRINT</span>{% endif %}
                    </td>
                    <td>
                        <span class="badge badge-{{ job.status|lower }}">{{ job.status }}</span>
                    </td>
                    <td class="time-ago">{{ job.completed_ago }}</td>
                    <td>
                        {% if job.status == 'COMPLETE' %}
                        <button class="btn btn-success btn-small" onclick="showReprintModal('{{ job.job_id }}', '{{ job.order_id }}')">
                            Reprint
                        </button>
                        {% elif job.status == 'ERROR' %}
                        <a href="/retry/{{ job.job_id }}" class="btn btn-primary btn-small">Retry</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state">
            <p>No recent jobs</p>
        </div>
        {% endif %}
    </div>
    
    <!-- Reprint Modal -->
    <div class="modal-overlay" id="reprintModal">
        <div class="modal">
            <h3>Reprint Job</h3>
            <form action="/reprint" method="POST">
                <input type="hidden" name="job_id" id="reprintJobId">
                <p style="margin-bottom: 10px;">Order: <strong id="reprintOrderId"></strong></p>
                <textarea name="reason" placeholder="Reason for reprint (e.g., damaged piece, quality issue)..." required></textarea>
                <div class="modal-actions">
                    <button type="button" class="btn" onclick="hideReprintModal()" style="background: #333;">Cancel</button>
                    <button type="submit" class="btn btn-success">Confirm Reprint</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        function showReprintModal(jobId, orderId) {
            document.getElementById('reprintJobId').value = jobId;
            document.getElementById('reprintOrderId').textContent = orderId;
            document.getElementById('reprintModal').classList.add('active');
        }
        
        function hideReprintModal() {
            document.getElementById('reprintModal').classList.remove('active');
        }
        
        function filterJobs() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#recentJobsTable tbody tr');
            
            rows.forEach(row => {
                const order = row.dataset.order;
                row.style.display = order.includes(search) ? '' : 'none';
            });
        }
        
        // Close modal on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') hideReprintModal();
        });
        
        // Close modal on overlay click
        document.getElementById('reprintModal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) hideReprintModal();
        });
    </script>
</body>
</html>
"""


# ============================================================================
# ROUTES
# ============================================================================


def time_ago(dt_str: str) -> str:
    """Convert datetime string to 'X minutes ago' format."""
    if not dt_str:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except Exception:
        return dt_str[:16] if len(dt_str) > 16 else dt_str


@app.route("/")
def dashboard():
    """Main dashboard page."""
    queue = get_queue()
    cutter_status = check_cutter_status()

    # Get stats
    stats = {
        "queued": 0,
        "cutting": 0,
        "completed_today": 0,
        "failed": 0,
    }

    queue_jobs = []
    recent_jobs = []

    if queue:
        try:
            # Get queue status
            status = queue.get_status()
            stats["queued"] = status.get("queue_depth", 0)
            stats["cutting"] = status.get("cutting_count", 0)

            # Get queued jobs
            for job in queue.list_queue():
                queue_jobs.append(
                    {
                        "job_id": job.job_id,
                        "order_id": job.order_id,
                        "priority": job.priority.name
                        if hasattr(job.priority, "name")
                        else str(job.priority),
                        "status": job.status.name
                        if hasattr(job.status, "name")
                        else str(job.status),
                        "piece_count": job.piece_count,
                        "created_ago": time_ago(job.created_at),
                    }
                )

            # Get recent completed/failed jobs
            for job in queue.get_recent_jobs(limit=20):
                status_name = (
                    job.status.name if hasattr(job.status, "name") else str(job.status)
                )

                if status_name == "COMPLETE":
                    stats["completed_today"] += 1
                elif status_name == "ERROR":
                    stats["failed"] += 1

                recent_jobs.append(
                    {
                        "job_id": job.job_id,
                        "order_id": job.order_id,
                        "status": status_name,
                        "is_reprint": job.is_reprint,
                        "completed_ago": time_ago(job.completed_at or job.created_at),
                    }
                )

        except Exception as e:
            print(f"Error getting queue data: {e}")
            import traceback

            traceback.print_exc()

    # Determine cutter status class
    status_class_map = {
        "connected": "connected",
        "busy": "busy",
        "offline": "offline",
        "unknown": "offline",
    }

    return render_template_string(
        DASHBOARD_HTML,
        stats=stats,
        queue_jobs=queue_jobs,
        recent_jobs=recent_jobs,
        cutter_status=cutter_status.title(),
        cutter_status_class=status_class_map.get(cutter_status.lower(), "offline"),
        cutter_ip=_cutter_ip,
        cutter_port=_cutter_port,
    )


@app.route("/refresh")
def refresh():
    """Force refresh and redirect to dashboard."""
    return redirect(url_for("dashboard"))


@app.route("/reprint", methods=["POST"])
def reprint():
    """Handle reprint request."""
    job_id = request.form.get("job_id")
    reason = request.form.get("reason", "Operator request")

    queue = get_queue()
    if queue and job_id:
        try:
            new_job = queue.reprint_job(job_id, reason=reason, requested_by="operator")
            if new_job:
                print(f"Reprint queued: {new_job.job_id} (original: {job_id})")
        except Exception as e:
            print(f"Reprint failed: {e}")

    return redirect(url_for("dashboard"))


@app.route("/retry/<job_id>")
def retry(job_id: str):
    """Retry a failed job."""
    queue = get_queue()
    if queue:
        try:
            result = queue.retry_job(job_id)
            if result:
                print(f"Retry queued: {job_id}")
            else:
                print(f"Retry failed for: {job_id}")
        except Exception as e:
            print(f"Retry error: {e}")

    return redirect(url_for("dashboard"))


@app.route("/cancel/<job_id>")
def cancel(job_id: str):
    """Cancel a queued job."""
    queue = get_queue()
    if queue:
        try:
            result = queue.cancel_job(job_id)
            if result:
                print(f"Job cancelled: {job_id}")
            else:
                print(f"Cancel failed for: {job_id}")
        except Exception as e:
            print(f"Cancel error: {e}")

    return redirect(url_for("dashboard"))


@app.route("/api/status")
def api_status():
    """JSON API for status (for external integrations)."""
    queue = get_queue()
    cutter_status = check_cutter_status()

    data = {
        "cutter_status": cutter_status,
        "cutter_ip": _cutter_ip,
        "cutter_port": _cutter_port,
        "queue_depth": 0,
        "cutting_count": 0,
    }

    if queue:
        try:
            status = queue.get_status()
            data.update(status)
        except Exception:
            pass

    return jsonify(data)


# ============================================================================
# MAIN
# ============================================================================


def main():
    global _cutter_ip, _cutter_port

    import argparse

    parser = argparse.ArgumentParser(description="Cutter Operator Dashboard")
    parser.add_argument(
        "--ip", default="192.168.1.100", help="Jindex cutter IP address"
    )
    parser.add_argument("--port", type=int, default=9100, help="Jindex cutter port")
    parser.add_argument(
        "--data-dir", default="./cutter_data", help="Queue data directory"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Dashboard host")
    parser.add_argument("--web-port", type=int, default=5000, help="Dashboard web port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Set global cutter config
    _cutter_ip = args.ip
    _cutter_port = args.port

    # Set environment variables for Flask app
    os.environ["CUTTER_IP"] = args.ip
    os.environ["CUTTER_PORT"] = str(args.port)
    os.environ["CUTTER_DATA_DIR"] = args.data_dir

    print(f"""
+==============================================================+
|           CUTTER OPERATOR DASHBOARD                          |
+==============================================================+
|  Jindex Cutter: {args.ip}:{args.port:<24}         |
|  Data Directory: {args.data_dir:<40}|
|                                                              |
|  Dashboard URL: http://localhost:{args.web_port:<24} |
|                                                              |
|  Press Ctrl+C to stop                                        |
+==============================================================+
""")

    app.run(host=args.host, port=args.web_port, debug=args.debug)


if __name__ == "__main__":
    main()
