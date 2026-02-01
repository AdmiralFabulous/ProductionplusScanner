"""
Locust Load Test Configuration

Usage:
    # Run with web UI
    locust -f locustfile.py --host=http://localhost:8000
    
    # Run headless
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 10m --headless

Reference: Ops Manual v6.8 - Section 2.6 (Scalability Layer)
"""

import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Sample measurement data
SAMPLE_MEASUREMENTS = {
    "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
    "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
    "Hg": {"value": 98.7, "unit": "cm", "confidence": 0.94},
    "Sh": {"value": 46.2, "unit": "cm", "confidence": 0.93},
    "Al": {"value": 64.8, "unit": "cm", "confidence": 0.90},
    "Bw": {"value": 38.5, "unit": "cm", "confidence": 0.91},
    "Nc": {"value": 39.4, "unit": "cm", "confidence": 0.94},
}


class PatternFactoryUser(HttpUser):
    """
    Simulates a Pattern Factory API user.
    
    User behaviors:
    - Create orders (high frequency)
    - Check order status (very high frequency)
    - Download pattern files (medium frequency)
    - View queue status (medium frequency)
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when a user starts."""
        self.client.headers["Authorization"] = "Bearer test_token"
        self.created_orders = []
    
    def on_stop(self):
        """Called when a user stops."""
        pass
    
    @task(10)
    def check_health(self):
        """Check API health - very frequent."""
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="/api/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def create_order(self):
        """Create a new order - frequent."""
        order_data = {
            "customer_id": f"locust_user_{self.user_id}_{int(time.time() * 1000)}",
            "garment_type": random.choice(["jacket", "trousers", "tee", "cargo"]),
            "fit_type": random.choice(["slim", "regular", "classic"]),
            "priority": random.choice(["rush", "high", "normal", "low"]),
            "measurements": SAMPLE_MEASUREMENTS
        }
        
        with self.client.post(
            "/api/v1/orders",
            json=order_data,
            catch_response=True,
            name="/api/v1/orders [POST]"
        ) as response:
            if response.status_code == 201:
                order_id = response.json().get("order_id")
                if order_id:
                    self.created_orders.append(order_id)
                    # Keep only recent orders
                    if len(self.created_orders) > 10:
                        self.created_orders.pop(0)
                response.success()
            else:
                response.failure(f"Create order failed: {response.status_code}")
    
    @task(8)
    def check_order_status(self):
        """Check order status - very frequent."""
        if not self.created_orders:
            return
        
        order_id = random.choice(self.created_orders)
        
        with self.client.get(
            f"/api/v1/orders/{order_id}/status",
            catch_response=True,
            name="/api/v1/orders/{id}/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Order might not exist, remove from list
                self.created_orders.remove(order_id)
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")
    
    @task(3)
    def get_queue_status(self):
        """Check queue status - medium frequency."""
        with self.client.get(
            "/api/v1/queue/status",
            catch_response=True,
            name="/api/v1/queue/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Queue status failed: {response.status_code}")
    
    @task(2)
    def list_orders(self):
        """List orders with filters - medium frequency."""
        params = {
            "limit": random.randint(10, 100),
            "status": random.choice(["", "processing", "pattern_ready", "cutting"])
        }
        
        with self.client.get(
            "/api/v1/orders",
            params=params,
            catch_response=True,
            name="/api/v1/orders [GET]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List orders failed: {response.status_code}")
    
    @task(1)
    def download_pattern_file(self):
        """Download pattern file - low frequency (expensive)."""
        if not self.created_orders:
            return
        
        order_id = random.choice(self.created_orders)
        file_type = random.choice(["plt", "pds", "dxf"])
        
        with self.client.get(
            f"/api/v1/orders/{order_id}/{file_type}",
            catch_response=True,
            name=f"/api/v1/orders/{{id}}/{file_type}",
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # File not ready yet
                response.success()
            elif response.status_code == 409:
                # File not ready
                response.success()
            else:
                response.failure(f"Download failed: {response.status_code}")


class EYESONUser(HttpUser):
    """
    Simulates an EYESON mobile app user.
    
    User behaviors:
    - Create scan sessions
    - Get voice prompts
    - Submit scan data
    """
    
    wait_time = between(5, 15)  # Longer wait for mobile users
    host = "http://localhost:8001"  # EYESON API
    
    def on_start(self):
        """Called when a user starts."""
        self.client.headers["Content-Type"] = "application/json"
        self.session_id = None
    
    @task(5)
    def create_scan_session(self):
        """Create a scan session."""
        session_data = {
            "user_id": f"eyeson_user_{self.user_id}",
            "scan_mode": random.choice(["video", "dual_image"]),
            "language": random.choice(["en", "es", "fr"]),
            "device_info": {
                "platform": random.choice(["ios", "android"]),
                "camera": "back",
                "resolution": "1920x1080"
            }
        }
        
        with self.client.post(
            "/api/v1/sessions",
            json=session_data,
            catch_response=True,
            name="/api/v1/sessions [POST]"
        ) as response:
            if response.status_code == 201:
                self.session_id = response.json().get("session_id")
                response.success()
            else:
                response.failure(f"Create session failed: {response.status_code}")
    
    @task(3)
    def get_voice_prompts(self):
        """Get voice prompts for scan."""
        language = random.choice(["en", "es", "fr"])
        
        with self.client.get(
            f"/api/v1/voice/prompts/{language}",
            catch_response=True,
            name="/api/v1/voice/prompts/{lang}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get prompts failed: {response.status_code}")
    
    @task(2)
    def check_voice_health(self):
        """Check TTS service health."""
        with self.client.get(
            "/api/v1/voice/health",
            catch_response=True,
            name="/api/v1/voice/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Voice health check failed: {response.status_code}")
    
    @task(1)
    def get_session_status(self):
        """Get session status."""
        if not self.session_id:
            return
        
        with self.client.get(
            f"/api/v1/sessions/{self.session_id}",
            catch_response=True,
            name="/api/v1/sessions/{id}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get session failed: {response.status_code}")


class TailorPlatformUser(HttpUser):
    """
    Simulates a Tailor Platform user.
    
    User behaviors:
    - View job board
    - Claim orders
    - Update order status
    """
    
    wait_time = between(10, 30)  # Tailors work slower
    host = "http://localhost:8002"  # Tailor Platform API
    
    def on_start(self):
        """Called when a user starts."""
        self.client.headers["Authorization"] = "Bearer tailor_token"
        self.tailor_id = f"tailor_{self.user_id}"
        self.claimed_orders = []
    
    @task(5)
    def view_job_board(self):
        """View available jobs."""
        with self.client.get(
            "/api/v1/job-board",
            catch_response=True,
            name="/api/v1/job-board"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Job board failed: {response.status_code}")
    
    @task(2)
    def claim_order(self):
        """Claim an order."""
        # First get job board
        response = self.client.get("/api/v1/job-board")
        if response.status_code != 200:
            return
        
        orders = response.json().get("orders", [])
        if not orders:
            return
        
        # Try to claim first available order
        order_id = orders[0]["order_id"]
        
        with self.client.post(
            f"/api/v1/orders/{order_id}/claim",
            json={"tailor_id": self.tailor_id},
            catch_response=True,
            name="/api/v1/orders/{id}/claim"
        ) as response:
            if response.status_code == 200:
                self.claimed_orders.append(order_id)
                response.success()
            elif response.status_code == 409:
                # Already claimed
                response.success()
            else:
                response.failure(f"Claim failed: {response.status_code}")
    
    @task(3)
    def update_order_status(self):
        """Update order production status."""
        if not self.claimed_orders:
            return
        
        order_id = random.choice(self.claimed_orders)
        
        with self.client.post(
            f"/api/v1/orders/{order_id}/status",
            json={
                "tailor_id": self.tailor_id,
                "status": random.choice(["sewing", "assembly", "finishing"]),
                "progress_percent": random.randint(0, 100)
            },
            catch_response=True,
            name="/api/v1/orders/{id}/status [POST]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status update failed: {response.status_code}")


# Event handlers for test metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # Log requests over 1 second
        print(f"⚠️  Slow request: {name} took {response_time:.0f}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "=" * 60)
    print("🚀 Load Test Started")
    print("=" * 60)
    print(f"Target Host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count}")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "=" * 60)
    print("🏁 Load Test Completed")
    print("=" * 60)
    
    # Print statistics
    stats = environment.runner.stats
    
    print("\n📊 Request Statistics:")
    print(f"{'Request':<40} {'Count':>10} {'Avg (ms)':>12} {'p95 (ms)':>12}")
    print("-" * 80)
    
    for key in sorted(stats.entries.keys()):
        entry = stats.entries[key]
        print(f"{entry.method} {entry.name:<35} {entry.num_requests:>10} "
              f"{entry.avg_response_time:>12.0f} {entry.get_response_time_percentile(0.95):>12.0f}")
    
    print("=" * 60 + "\n")


# Load Test Scenarios
LOAD_TEST_SCENARIOS = {
    "normal_load": {
        "description": "Normal production load",
        "users": 10,
        "spawn_rate": 1,
        "duration": "10m",
        "target_throughput": 100  # orders/hour
    },
    "peak_load": {
        "description": "Peak hours load",
        "users": 50,
        "spawn_rate": 5,
        "duration": "5m",
        "target_throughput": 200
    },
    "stress_test": {
        "description": "Stress test - maximum capacity",
        "users": 100,
        "spawn_rate": 10,
        "duration": "3m",
        "target_throughput": 300
    },
    "spike_test": {
        "description": "Sudden traffic spike",
        "users": 200,
        "spawn_rate": 50,
        "duration": "2m",
        "target_throughput": 400
    }
}


# Custom commands
def run_load_test(scenario_name: str, host: str = "http://localhost:8000"):
    """
    Run a load test scenario programmatically.
    
    Usage:
        from locustfile import run_load_test
        run_load_test("normal_load")
    """
    import subprocess
    
    if scenario_name not in LOAD_TEST_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    scenario = LOAD_TEST_SCENARIOS[scenario_name]
    
    cmd = [
        "locust",
        "-f", __file__,
        "--host", host,
        "--users", str(scenario["users"]),
        "--spawn-rate", str(scenario["spawn_rate"]),
        "--run-time", scenario["duration"],
        "--headless"
    ]
    
    print(f"Running {scenario_name} load test...")
    print(f"Command: {' '.join(cmd)}")
    
    subprocess.run(cmd)


if __name__ == "__main__":
    # Allow running directly for testing
    print("Locust load test file.")
    print("Run with: locust -f locustfile.py --host=http://localhost:8000")
    print("\nAvailable scenarios:")
    for name, config in LOAD_TEST_SCENARIOS.items():
        print(f"  - {name}: {config['description']}")
        print(f"    Users: {config['users']}, Duration: {config['duration']}")
