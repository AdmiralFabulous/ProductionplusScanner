#!/usr/bin/env python3
"""
SameDaySuits Web API - REST API and Dashboard

FastAPI-based web API for:
1. Order submission and processing
2. Real-time queue status
3. Job management
4. WebSocket for live updates

Run with:
    uvicorn web_api:app --reload --host 0.0.0.0 --port 8000

Author: Claude
Date: 2026-01-30
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    Header,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import os
import jwt
from datetime import datetime, timedelta

# Import our production modules
from samedaysuits_api import (
    SameDaySuitsAPI,
    Order,
    GarmentType,
    FitType,
    CustomerMeasurements,
    ProductionResult,
)
from cutter_queue import CutterQueue, JobPriority, JobStatus, CutterJob

# Import scalability modules (with graceful fallback)
try:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scalability.queue_manager import (
        OrderQueue,
        JobPriority as QueuePriority,
        JobStatus as QueueStatus,
    )

    SCALABILITY_AVAILABLE = True
except ImportError:
    SCALABILITY_AVAILABLE = False
    OrderQueue = None

# ============================================================================
# Pydantic Models for API
# ============================================================================


class MeasurementsRequest(BaseModel):
    """Customer measurements for order."""

    chest_cm: float = Field(..., gt=50, lt=200, description="Chest circumference in cm")
    waist_cm: float = Field(..., gt=40, lt=200, description="Waist circumference in cm")
    hip_cm: float = Field(..., gt=50, lt=200, description="Hip circumference in cm")
    shoulder_width_cm: Optional[float] = Field(None, description="Shoulder width in cm")
    arm_length_cm: Optional[float] = Field(None, description="Arm length in cm")
    inseam_cm: Optional[float] = Field(None, description="Inseam length in cm")
    source: str = Field("web_api", description="Measurement source")


class OrderRequest(BaseModel):
    """Order submission request."""

    order_id: str = Field(
        ..., min_length=1, max_length=50, description="Unique order ID"
    )
    customer_id: str = Field(
        ..., min_length=1, max_length=50, description="Customer ID"
    )
    garment_type: str = Field(
        ..., description="Garment type: tee, jacket, trousers, cargo"
    )
    fit_type: str = Field("regular", description="Fit type: slim, regular, classic")
    measurements: MeasurementsRequest
    priority: str = Field("normal", description="Priority: rush, high, normal, low")
    quantity: int = Field(1, ge=1, le=100, description="Quantity to produce")
    notes: str = Field("", description="Additional notes")


class OrderResponse(BaseModel):
    """Response for order processing."""

    success: bool
    order_id: str
    message: str
    plt_file: Optional[str] = None
    fabric_length_cm: float = 0.0
    fabric_utilization: float = 0.0
    piece_count: int = 0
    processing_time_ms: float = 0.0
    errors: List[str] = []
    warnings: List[str] = []
    job_id: Optional[str] = None


class QueueStatusResponse(BaseModel):
    """Queue status response."""

    total_jobs: int
    pending_jobs: int
    cutting_jobs: int
    complete_jobs: int
    error_jobs: int
    total_fabric_cm: float
    estimated_time_minutes: float


class JobResponse(BaseModel):
    """Job details response."""

    job_id: str
    order_id: str
    status: str
    priority: str
    fabric_length_cm: float
    piece_count: int
    created_at: str
    queued_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


class TemplateInfo(BaseModel):
    """Template information."""

    garment_type: str
    available: bool
    filename: str


# ============================================================================
# WebSocket Manager for Real-time Updates
# ============================================================================


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Connection might be closed


manager = ConnectionManager()

# ============================================================================
# App Initialization
# ============================================================================

# Initialize API and Queue
api = SameDaySuitsAPI()
queue = CutterQueue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Start queue watcher
    queue.start_watching()
    print("Queue watcher started")
    yield
    # Shutdown: Stop queue watcher
    queue.stop_watching()
    print("Queue watcher stopped")


app = FastAPI(
    title="SameDaySuits Production API",
    description="REST API for automated garment production pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# Secure CORS - update for production
allow_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Authentication
security = HTTPBearer()

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# API Key for service-to-service auth
API_KEY = os.getenv("API_KEY", "sds-api-key-change-in-production")

# Async Processing Configuration
# When enabled, orders are enqueued to Redis and processed by workers
# When disabled (default), orders are processed synchronously (existing behavior)
ASYNC_PROCESSING = os.getenv("ASYNC_PROCESSING", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize async queue (if available and enabled)
async_queue = None
if SCALABILITY_AVAILABLE and ASYNC_PROCESSING:
    try:
        async_queue = OrderQueue(REDIS_URL)
        if async_queue.is_available:
            print(f"Async processing enabled - Redis connected at {REDIS_URL}")
        else:
            print("Async processing requested but Redis unavailable - using sync mode")
            async_queue = None
    except Exception as e:
        print(f"Failed to initialize async queue: {e} - using sync mode")
        async_queue = None


def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Verify API key for service auth"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# Apply authentication to sensitive endpoints
# Example: @app.post("/orders", dependencies=[Depends(verify_token)])

# ============================================================================
# Dashboard HTML
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SameDaySuits - Production Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        h1 { color: #00d4ff; margin-bottom: 30px; font-size: 2.5em; }
        h2 { color: #00d4ff; margin-bottom: 15px; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #16213e; border-radius: 12px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
        .stat-card { text-align: center; }
        .stat-value { font-size: 3em; font-weight: bold; color: #00d4ff; }
        .stat-label { font-size: 0.9em; color: #888; margin-top: 5px; }
        .status-pending { color: #ffc107; }
        .status-cutting { color: #00d4ff; animation: pulse 1s infinite; }
        .status-complete { color: #28a745; }
        .status-error { color: #dc3545; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2a2a4a; }
        th { color: #00d4ff; font-weight: 600; }
        tr:hover { background: #1f2b4a; }
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8em; font-weight: 600; }
        .badge-rush { background: #dc3545; }
        .badge-high { background: #fd7e14; }
        .badge-normal { background: #17a2b8; }
        .badge-low { background: #6c757d; }
        form { display: grid; gap: 15px; }
        label { font-weight: 500; color: #aaa; }
        input, select { width: 100%; padding: 10px; border: 1px solid #2a2a4a; border-radius: 6px; background: #0f0f23; color: #eee; }
        button { padding: 12px 25px; background: #00d4ff; color: #000; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: transform 0.2s; }
        button:hover { transform: scale(1.02); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }
        #log { background: #0f0f23; border-radius: 8px; padding: 15px; max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.85em; }
        .log-entry { margin-bottom: 8px; padding: 5px; border-left: 3px solid #00d4ff; padding-left: 10px; }
        .connected { color: #28a745; }
        .disconnected { color: #dc3545; }
        .refresh-btn { float: right; background: #28a745; padding: 8px 15px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>SameDaySuits Production Dashboard</h1>
        
        <!-- Status Cards -->
        <div class="grid">
            <div class="card stat-card">
                <div class="stat-value" id="pending-count">-</div>
                <div class="stat-label">Pending Jobs</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value status-cutting" id="cutting-count">-</div>
                <div class="stat-label">Currently Cutting</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value status-complete" id="complete-count">-</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="fabric-total">-</div>
                <div class="stat-label">Fabric Queued (cm)</div>
            </div>
        </div>
        
        <!-- Quick Order Form -->
        <div class="card" style="margin-bottom: 30px;">
            <h2>Quick Order</h2>
            <form id="order-form">
                <div class="form-row">
                    <div>
                        <label>Order ID</label>
                        <input type="text" id="order-id" placeholder="ORD-001" required>
                    </div>
                    <div>
                        <label>Customer ID</label>
                        <input type="text" id="customer-id" value="WALK-IN">
                    </div>
                    <div>
                        <label>Garment</label>
                        <select id="garment-type">
                            <option value="tee">Basic Tee</option>
                            <option value="jacket">Light Jacket</option>
                            <option value="trousers">Skinny Trousers</option>
                            <option value="cargo">Skinny Cargo</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div>
                        <label>Chest (cm)</label>
                        <input type="number" id="chest" value="102" min="50" max="200" required>
                    </div>
                    <div>
                        <label>Waist (cm)</label>
                        <input type="number" id="waist" value="88" min="40" max="200" required>
                    </div>
                    <div>
                        <label>Hip (cm)</label>
                        <input type="number" id="hip" value="100" min="50" max="200" required>
                    </div>
                </div>
                <div class="form-row">
                    <div>
                        <label>Priority</label>
                        <select id="priority">
                            <option value="rush">Rush (Same Day)</option>
                            <option value="high">High</option>
                            <option value="normal" selected>Normal</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                    <div>
                        <label>Fit</label>
                        <select id="fit-type">
                            <option value="slim">Slim</option>
                            <option value="regular" selected>Regular</option>
                            <option value="classic">Classic</option>
                        </select>
                    </div>
                    <div style="display: flex; align-items: end;">
                        <button type="submit" style="width: 100%;">Submit Order</button>
                    </div>
                </div>
            </form>
        </div>
        
        <!-- Job Queue -->
        <div class="card" style="margin-bottom: 30px;">
            <h2>Job Queue <button class="refresh-btn" onclick="refreshJobs()">Refresh</button></h2>
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Order</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Fabric</th>
                        <th>Created</th>
                        <th>Files</th>
                    </tr>
                </thead>
                <tbody id="jobs-table">
                    <tr><td colspan="7" style="text-align: center;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <!-- Order Files -->
        <div class="card" style="margin-bottom: 30px;">
            <h2>Order Files</h2>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px;">Order ID</label>
                <input type="text" id="file-order-id" placeholder="Enter order ID" style="width: 300px; display: inline-block;">
                <button onclick="loadOrderFiles()" style="display: inline-block; margin-left: 10px;">Load Files</button>
            </div>
            <div id="order-files-list" style="display: none;">
                <table>
                    <thead>
                        <tr>
                            <th>File Type</th>
                            <th>Status</th>
                            <th>Size</th>
                            <th>Download</th>
                        </tr>
                    </thead>
                    <tbody id="files-table-body">
                    </tbody>
                </table>
                <div id="order-status" style="margin-top: 15px; padding: 10px; background: #0f0f23; border-radius: 6px;">
                    <strong>Order Status:</strong> <span id="order-status-text">-</span>
                </div>
            </div>
        </div>
        
        <!-- Live Log -->
        <div class="card">
            <h2>Live Log <span id="ws-status" class="disconnected">(Disconnected)</span></h2>
            <div id="log"></div>
        </div>
    </div>
    
    <script>
        const API_BASE = window.location.origin;
        let ws = null;
        
        // WebSocket connection
        function connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                document.getElementById('ws-status').textContent = '(Connected)';
                document.getElementById('ws-status').className = 'connected';
                addLog('WebSocket connected');
            };
            
            ws.onclose = () => {
                document.getElementById('ws-status').textContent = '(Disconnected)';
                document.getElementById('ws-status').className = 'disconnected';
                addLog('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addLog(`Event: ${data.event} - ${JSON.stringify(data.data)}`);
                if (data.event === 'status_update') {
                    updateStatus(data.data);
                } else if (data.event === 'job_update') {
                    refreshJobs();
                }
            };
        }
        
        function addLog(message) {
            const log = document.getElementById('log');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            log.insertBefore(entry, log.firstChild);
            if (log.children.length > 50) log.removeChild(log.lastChild);
        }
        
        async function loadOrderFiles() {
            const orderId = document.getElementById('file-order-id').value.trim();
            if (!orderId) {
                addLog('Please enter an order ID');
                return;
            }
            
            try {
                addLog(`Loading files for order: ${orderId}`);
                
                // Get order status
                const statusResponse = await fetch(`${API_BASE}/orders/${orderId}/status`);
                if (!statusResponse.ok) {
                    throw new Error('Order not found');
                }
                const status = await statusResponse.json();
                
                // Get files list
                const filesResponse = await fetch(`${API_BASE}/orders/${orderId}/files`);
                const files = await filesResponse.json();
                
                // Update status
                document.getElementById('order-status-text').textContent = 
                    `${status.status} (${status.stage}) - ${status.progress}%`;
                
                // Build files table
                const tbody = document.getElementById('files-table-body');
                tbody.innerHTML = '';
                
                const fileTypes = [
                    { key: 'plt', label: 'PLT (Cutter)', ext: '.plt' },
                    { key: 'pds', label: 'PDS (Optitex)', ext: '.pds' },
                    { key: 'dxf', label: 'DXF (CAD)', ext: '.dxf' },
                    { key: 'metadata', label: 'Metadata', ext: '_metadata.json' },
                    { key: 'qc_report', label: 'QC Report', ext: '_qc_report.json' },
                ];
                
                fileTypes.forEach(({ key, label, ext }) => {
                    const fileInfo = files.files[key];
                    const row = document.createElement('tr');
                    
                    if (fileInfo && fileInfo.exists) {
                        const sizeKB = (fileInfo.size_bytes / 1024).toFixed(1);
                        const downloadLink = fileInfo.path ? 
                            `<a href="${API_BASE}${fileInfo.path}" download style="color: #00d4ff; text-decoration: none;">Download</a>` :
                            `<span style="color: #666;">View in folder</span>`;
                        
                        row.innerHTML = `
                            <td>${label}</td>
                            <td style="color: #28a745;">✓ Available</td>
                            <td>${sizeKB} KB</td>
                            <td>${downloadLink}</td>
                        `;
                    } else {
                        row.innerHTML = `
                            <td>${label}</td>
                            <td style="color: #ffc107;">⏳ Pending</td>
                            <td>-</td>
                            <td>-</td>
                        `;
                    }
                    
                    tbody.appendChild(row);
                });
                
                // Show individual pieces count
                if (files.files.individual_pieces) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>Individual Pieces</td>
                        <td style="color: #28a745;">✓ ${files.files.individual_pieces.count} files</td>
                        <td>-</td>
                        <td><a href="${API_BASE}${files.files.individual_pieces.folder}" style="color: #00d4ff; text-decoration: none;">View Folder</a></td>
                    `;
                    tbody.appendChild(row);
                }
                
                document.getElementById('order-files-list').style.display = 'block';
                addLog(`Loaded files for ${orderId}`);
                
            } catch (error) {
                addLog(`Error loading order files: ${error}`);
                alert('Order not found or error loading files');
            }
        }
        
        function updateStatus(status) {
            document.getElementById('pending-count').textContent = status.pending_jobs;
            document.getElementById('cutting-count').textContent = status.cutting_jobs;
            document.getElementById('complete-count').textContent = status.complete_jobs;
            document.getElementById('fabric-total').textContent = status.total_fabric_cm.toFixed(0);
        }
        
        async function refreshStatus() {
            try {
                const response = await fetch(`${API_BASE}/queue/status`);
                const status = await response.json();
                updateStatus(status);
            } catch (error) {
                addLog(`Error fetching status: ${error}`);
            }
        }
        
        async function refreshJobs() {
            try {
                const response = await fetch(`${API_BASE}/queue/jobs`);
                const jobs = await response.json();
                
                const tbody = document.getElementById('jobs-table');
                if (jobs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No jobs in queue</td></tr>';
                    return;
                }
                
                tbody.innerHTML = jobs.map(job => `
                    <tr>
                        <td>${job.job_id.substring(0, 20)}...</td>
                        <td><a href="#" onclick="document.getElementById('file-order-id').value='${job.order_id}'; loadOrderFiles(); return false;" style="color: #00d4ff; text-decoration: none;">${job.order_id}</a></td>
                        <td class="status-${job.status}">${job.status.toUpperCase()}</td>
                        <td><span class="badge badge-${job.priority}">${job.priority.toUpperCase()}</span></td>
                        <td>${job.fabric_length_cm.toFixed(1)} cm</td>
                        <td>${new Date(job.created_at).toLocaleTimeString()}</td>
                        <td><button onclick="document.getElementById('file-order-id').value='${job.order_id}'; loadOrderFiles();" style="padding: 4px 8px; font-size: 0.8em;">Files</button></td>
                    </tr>
                `).join('');
            } catch (error) {
                addLog(`Error fetching jobs: ${error}`);
            }
        }
        
        // Order form submission
        document.getElementById('order-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const orderData = {
                order_id: document.getElementById('order-id').value,
                customer_id: document.getElementById('customer-id').value,
                garment_type: document.getElementById('garment-type').value,
                fit_type: document.getElementById('fit-type').value,
                priority: document.getElementById('priority').value,
                measurements: {
                    chest_cm: parseFloat(document.getElementById('chest').value),
                    waist_cm: parseFloat(document.getElementById('waist').value),
                    hip_cm: parseFloat(document.getElementById('hip').value),
                }
            };
            
            try {
                addLog(`Submitting order: ${orderData.order_id}`);
                const response = await fetch(`${API_BASE}/orders`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(orderData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    addLog(`Order ${result.order_id} completed! Fabric: ${result.fabric_length_cm.toFixed(1)}cm`);
                    // Generate new order ID
                    document.getElementById('order-id').value = 'ORD-' + Date.now().toString(36).toUpperCase();
                    refreshJobs();
                    refreshStatus();
                } else {
                    addLog(`Order failed: ${result.errors.join(', ')}`);
                }
            } catch (error) {
                addLog(`Error submitting order: ${error}`);
            }
        });
        
        // Initialize
        document.getElementById('order-id').value = 'ORD-' + Date.now().toString(36).toUpperCase();
        connectWebSocket();
        refreshStatus();
        refreshJobs();
        setInterval(refreshStatus, 10000);
    </script>
</body>
</html>
"""

# ============================================================================
# API Routes
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the production dashboard."""
    return DASHBOARD_HTML


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================================================
# Templates Routes
# ============================================================================


@app.get("/templates", response_model=List[TemplateInfo])
async def list_templates():
    """List available garment templates."""
    templates = api.list_available_templates()

    # Map garment type to filename
    filename_map = {
        "tee": "Basic Tee_2D.PDS",
        "jacket": "Light  Jacket_2D.PDS",
        "trousers": "Skinny Trousers_2D.PDS",
        "cargo": "Skinny Cargo_2D.PDS",
    }

    return [
        TemplateInfo(
            garment_type=garment,
            available=available,
            filename=filename_map.get(garment, "unknown"),
        )
        for garment, available in templates.items()
    ]


# ============================================================================
# Orders Routes
# ============================================================================


@app.post("/orders", response_model=OrderResponse)
async def create_order(order_request: OrderRequest, background_tasks: BackgroundTasks):
    """
    Submit a new order for production.

    Processing modes:
    - ASYNC (ASYNC_PROCESSING=true): Enqueues order to Redis for worker processing (~50ms)
    - SYNC (ASYNC_PROCESSING=false, default): Processes synchronously (~45s)

    The order will be processed through the pipeline:
    1. Pattern extracted from template
    2. Scaled to customer measurements
    3. Nested for 62" fabric
    4. HPGL/PLT file generated
    5. Added to cutter queue
    """
    try:
        # Validate garment type
        try:
            garment_type = GarmentType(order_request.garment_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid garment type: {order_request.garment_type}. "
                f"Valid types: tee, jacket, trousers, cargo",
            )

        # Validate fit type
        try:
            fit_type = FitType(order_request.fit_type)
        except ValueError:
            fit_type = FitType.REGULAR

        # =====================================================================
        # ASYNC PROCESSING PATH
        # =====================================================================
        if async_queue and async_queue.is_available:
            # Enqueue order for worker processing
            priority_map = {
                "rush": QueuePriority.RUSH,
                "high": QueuePriority.HIGH,
                "normal": QueuePriority.NORMAL,
                "low": QueuePriority.LOW,
            }
            priority = priority_map.get(order_request.priority, QueuePriority.NORMAL)

            order_data = {
                "order_id": order_request.order_id,
                "customer_id": order_request.customer_id,
                "garment_type": order_request.garment_type,
                "fit_type": order_request.fit_type,
                "measurements": {
                    "chest_cm": order_request.measurements.chest_cm,
                    "waist_cm": order_request.measurements.waist_cm,
                    "hip_cm": order_request.measurements.hip_cm,
                    "shoulder_width_cm": order_request.measurements.shoulder_width_cm,
                    "arm_length_cm": order_request.measurements.arm_length_cm,
                    "inseam_cm": order_request.measurements.inseam_cm,
                    "source": order_request.measurements.source,
                },
                "priority": order_request.priority,
                "quantity": order_request.quantity,
                "notes": order_request.notes,
            }

            try:
                job_id = async_queue.enqueue(
                    order_request.order_id,
                    order_data,
                    priority,
                )

                return OrderResponse(
                    success=True,
                    order_id=order_request.order_id,
                    message="Order queued for processing",
                    job_id=job_id,
                    processing_time_ms=0,  # Not processed yet
                )
            except Exception as enqueue_error:
                # Failed to enqueue - fall through to sync processing
                print(f"Failed to enqueue order, falling back to sync: {enqueue_error}")

        # =====================================================================
        # SYNC PROCESSING PATH (default or fallback)
        # =====================================================================
        # Create Order object
        order = Order(
            order_id=order_request.order_id,
            customer_id=order_request.customer_id,
            garment_type=garment_type,
            fit_type=fit_type,
            measurements=CustomerMeasurements(
                chest_cm=order_request.measurements.chest_cm,
                waist_cm=order_request.measurements.waist_cm,
                hip_cm=order_request.measurements.hip_cm,
                shoulder_width_cm=order_request.measurements.shoulder_width_cm,
                arm_length_cm=order_request.measurements.arm_length_cm,
                inseam_cm=order_request.measurements.inseam_cm,
                source=order_request.measurements.source,
            ),
            quantity=order_request.quantity,
            notes=order_request.notes,
        )

        # Process order synchronously
        result: ProductionResult = api.process_order(order)

        # Add to cutter queue if successful
        job_id = None
        if result.success and result.plt_file:
            priority_map = {
                "rush": JobPriority.RUSH,
                "high": JobPriority.HIGH,
                "normal": JobPriority.NORMAL,
                "low": JobPriority.LOW,
            }
            priority = priority_map.get(order_request.priority, JobPriority.NORMAL)

            # Load metadata for queue
            metadata = None
            if result.metadata_file and result.metadata_file.exists():
                with open(result.metadata_file) as f:
                    metadata = json.load(f)

            job = queue.add_job(
                order_request.order_id,
                result.plt_file,
                priority=priority,
                metadata=metadata,
            )
            job_id = job.job_id

            # Broadcast update
            background_tasks.add_task(broadcast_status_update)

        return OrderResponse(
            success=result.success,
            order_id=result.order_id,
            message="Order processed successfully"
            if result.success
            else "Order processing failed",
            plt_file=str(result.plt_file) if result.plt_file else None,
            fabric_length_cm=result.fabric_length_cm,
            fabric_utilization=result.fabric_utilization,
            piece_count=result.piece_count,
            processing_time_ms=result.processing_time_ms,
            errors=result.errors,
            warnings=result.warnings,
            job_id=job_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        return OrderResponse(
            success=False,
            order_id=order_request.order_id,
            message=f"Error: {str(e)}",
            errors=[str(e)],
        )


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details and status."""
    # Check if order directory exists
    order_dir = api.output_dir / order_id

    if not order_dir.exists():
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")

    # Load metadata
    metadata_file = order_dir / f"{order_id}_metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            return json.load(f)

    return {"order_id": order_id, "status": "processing"}


# ============================================================================
# Async Processing Status Routes (for ASYNC_PROCESSING=true mode)
# ============================================================================


@app.get("/orders/{order_id}/processing-status")
async def get_processing_status(order_id: str):
    """
    Get processing status for an async-enqueued order.

    Returns:
        - status: queued, processing, complete, failed, dlq
        - position: Queue position (if queued)
        - result: Processing result (if complete)
        - error: Error message (if failed)
    """
    # Check async queue first
    if async_queue and async_queue.is_available:
        status = async_queue.get_status(order_id)

        if status:
            response = {
                "order_id": order_id,
                "status": status.value,
                "async_processing": True,
            }

            if status == QueueStatus.QUEUED:
                position = async_queue.get_position(order_id)
                response["queue_position"] = position

            elif status == QueueStatus.COMPLETE:
                result = async_queue.get_result(order_id)
                response["result"] = result

            elif status in (QueueStatus.FAILED, QueueStatus.DLQ):
                response["error"] = async_queue.get_error(order_id)
                response["attempts"] = async_queue.get_attempts(order_id)

            return response

    # Fall back to checking file system (for sync-processed orders)
    order_dir = api.output_dir / order_id
    if order_dir.exists():
        metadata_file = order_dir / f"{order_id}_metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
            return {
                "order_id": order_id,
                "status": "complete",
                "async_processing": False,
                "result": metadata,
            }
        return {
            "order_id": order_id,
            "status": "processing",
            "async_processing": False,
        }

    raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")


# ============================================================================
# Dead Letter Queue (DLQ) Admin Routes
# ============================================================================


@app.get("/admin/dlq")
async def get_dlq():
    """
    Get all orders in the dead-letter queue.

    These are orders that failed after 3 retry attempts.
    Requires admin role (when auth enabled).
    """
    if not async_queue or not async_queue.is_available:
        return {"dlq": [], "message": "Async processing not enabled"}

    orders = async_queue.get_dlq_orders()
    return {
        "dlq": orders,
        "count": len(orders),
    }


@app.post("/admin/dlq/{order_id}/retry")
async def retry_dlq_order(order_id: str, priority: Optional[str] = None):
    """
    Retry a failed order from the dead-letter queue.

    Args:
        order_id: Order to retry
        priority: Optional new priority (rush, high, normal, low)
    """
    if not async_queue or not async_queue.is_available:
        raise HTTPException(status_code=503, detail="Async processing not enabled")

    # Validate priority if provided
    queue_priority = None
    if priority:
        try:
            queue_priority = QueuePriority[priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {priority}. Valid: rush, high, normal, low",
            )

    try:
        async_queue.requeue_from_dlq(order_id, queue_priority)
        return {
            "success": True,
            "message": f"Order {order_id} requeued from DLQ",
            "priority": priority or "original",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry order: {e}")


@app.get("/admin/queue-stats")
async def get_queue_stats():
    """
    Get async queue statistics.

    Returns counts for each queue state and active workers.
    """
    if not async_queue or not async_queue.is_available:
        return {
            "enabled": False,
            "message": "Async processing not enabled",
        }

    stats = async_queue.get_stats()
    workers = async_queue.get_active_workers()

    return {
        "enabled": True,
        "stats": stats.to_dict(),
        "active_workers": workers,
        "worker_count": len(workers),
    }


# ============================================================================
# Queue Routes
# ============================================================================


@app.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get current queue status."""
    status = queue.get_status()
    return QueueStatusResponse(
        total_jobs=status.total_jobs,
        pending_jobs=status.pending_jobs,
        cutting_jobs=status.cutting_jobs,
        complete_jobs=status.complete_jobs,
        error_jobs=status.error_jobs,
        total_fabric_cm=status.total_fabric_cm,
        estimated_time_minutes=status.estimated_time_minutes,
    )


@app.get("/queue/jobs", response_model=List[JobResponse])
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """List jobs in the queue."""
    status_filter = JobStatus(status) if status else None
    jobs = queue.list_jobs(status_filter)[:limit]

    return [
        JobResponse(
            job_id=job.job_id,
            order_id=job.order_id,
            status=job.status.value,
            priority=job.priority.name.lower(),
            fabric_length_cm=job.fabric_length_cm,
            piece_count=job.piece_count,
            created_at=job.created_at,
            queued_at=job.queued_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
        for job in jobs
    ]


@app.get("/queue/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get details for a specific job."""
    if job_id not in queue.jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    job = queue.jobs[job_id]
    return JobResponse(
        job_id=job.job_id,
        order_id=job.order_id,
        status=job.status.value,
        priority=job.priority.name.lower(),
        fabric_length_cm=job.fabric_length_cm,
        piece_count=job.piece_count,
        created_at=job.created_at,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@app.post("/queue/jobs/{job_id}/process")
async def process_job(job_id: str, background_tasks: BackgroundTasks):
    """Manually trigger processing of a specific job."""
    if job_id not in queue.jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    job = queue.jobs[job_id]

    # Copy to spool
    spool_file = queue.copy_to_spool(job_id)
    if spool_file:
        queue.mark_cutting(job_id)
        background_tasks.add_task(broadcast_status_update)
        return {
            "message": f"Job {job_id} sent to cutter",
            "spool_file": str(spool_file),
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to copy to spool")


@app.post("/queue/process-next")
async def process_next_job(background_tasks: BackgroundTasks):
    """Process the next job in the queue."""
    job = queue.get_next_job()

    if not job:
        return {"message": "No jobs in queue"}

    spool_file = queue.copy_to_spool(job.job_id)
    if spool_file:
        queue.mark_cutting(job.job_id)
        background_tasks.add_task(broadcast_status_update)
        return {
            "message": f"Job {job.job_id} sent to cutter",
            "job_id": job.job_id,
            "spool_file": str(spool_file),
        }
    else:
        queue.mark_error(job.job_id, "Failed to copy to spool")
        raise HTTPException(status_code=500, detail="Failed to copy to spool")


@app.post("/queue/jobs/{job_id}/complete")
async def mark_job_complete(job_id: str, background_tasks: BackgroundTasks):
    """Mark a job as complete (called when cutter finishes)."""
    if job_id not in queue.jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    queue.mark_complete(job_id)
    background_tasks.add_task(broadcast_status_update)
    return {"message": f"Job {job_id} marked complete"}


# ============================================================================
# File Download Routes
# ============================================================================


@app.get("/orders/{order_id}/plt")
async def download_plt(order_id: str):
    """Download the PLT file for an order."""
    plt_file = api.output_dir / order_id / f"{order_id}.plt"

    if not plt_file.exists():
        raise HTTPException(
            status_code=404, detail=f"PLT file not found for order: {order_id}"
        )

    return FileResponse(
        plt_file,
        media_type="application/octet-stream",
        filename=f"{order_id}.plt",
    )


@app.get("/orders/{order_id}/pds")
async def download_pds(order_id: str):
    """Download the PDS (Optitex) file for an order."""
    pds_file = api.output_dir / order_id / f"{order_id}.pds"

    if not pds_file.exists():
        raise HTTPException(
            status_code=404, detail=f"PDS file not found for order: {order_id}"
        )

    return FileResponse(
        pds_file,
        media_type="application/octet-stream",
        filename=f"{order_id}.pds",
    )


@app.get("/orders/{order_id}/dxf")
async def download_dxf(order_id: str):
    """Download the DXF (CAD) file for an order."""
    dxf_file = api.output_dir / order_id / f"{order_id}.dxf"

    if not dxf_file.exists():
        raise HTTPException(
            status_code=404, detail=f"DXF file not found for order: {order_id}"
        )

    return FileResponse(
        dxf_file,
        media_type="application/octet-stream",
        filename=f"{order_id}.dxf",
    )


@app.get("/orders/{order_id}/files")
async def list_order_files(order_id: str):
    """List all files available for an order."""
    order_folder = api.output_dir / order_id

    if not order_folder.exists():
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")

    files = {"order_id": order_id, "folder_path": str(order_folder), "files": {}}

    # Main files
    main_files = {
        "plt": order_folder / f"{order_id}.plt",
        "pds": order_folder / f"{order_id}.pds",
        "dxf": order_folder / f"{order_id}.dxf",
        "metadata": order_folder / f"{order_id}_metadata.json",
        "qc_report": order_folder / f"{order_id}_qc_report.json",
        "production_log": order_folder / f"{order_id}_production.log",
        "nesting_report": order_folder / f"{order_id}_nesting.json",
    }

    for file_type, file_path in main_files.items():
        files["files"][file_type] = {
            "exists": file_path.exists(),
            "path": f"/orders/{order_id}/{file_type}"
            if file_type in ["plt", "pds", "dxf"]
            else None,
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "filename": file_path.name if file_path.exists() else None,
        }

    # Individual piece files
    pieces_folder = order_folder / "pieces"
    if pieces_folder.exists():
        piece_files = list(pieces_folder.glob(f"{order_id}_piece_*.pds"))
        files["files"]["individual_pieces"] = {
            "count": len(piece_files),
            "folder": f"/orders/{order_id}/pieces",
        }

    return files


@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: str):
    """Get detailed order status including file availability."""
    order_folder = api.output_dir / order_id

    if not order_folder.exists():
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")

    # Check which files are available
    files_available = {
        "plt": (order_folder / f"{order_id}.plt").exists(),
        "pds": (order_folder / f"{order_id}.pds").exists(),
        "dxf": (order_folder / f"{order_id}.dxf").exists(),
        "metadata": (order_folder / f"{order_id}_metadata.json").exists(),
        "qc_report": (order_folder / f"{order_id}_qc_report.json").exists(),
    }

    # Try to load metadata
    metadata = {}
    metadata_file = order_folder / f"{order_id}_metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
        except:
            pass

    status = {
        "order_id": order_id,
        "status": metadata.get("status", "unknown"),
        "stage": metadata.get("stage", "unknown"),
        "progress": metadata.get("progress", 0),
        "customer_id": metadata.get("customer_id"),
        "garment_type": metadata.get("garment_type"),
        "files_available": files_available,
        "download_links": {
            "plt": f"/orders/{order_id}/plt" if files_available["plt"] else None,
            "pds": f"/orders/{order_id}/pds" if files_available["pds"] else None,
            "dxf": f"/orders/{order_id}/dxf" if files_available["dxf"] else None,
            "files_list": f"/orders/{order_id}/files",
        },
        "folder_path": str(order_folder),
        "created_at": metadata.get("created_at"),
        "completed_at": metadata.get("completed_at"),
    }

    return status


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        # Send initial status
        status = queue.get_status()
        await websocket.send_json(
            {
                "event": "status_update",
                "data": {
                    "total_jobs": status.total_jobs,
                    "pending_jobs": status.pending_jobs,
                    "cutting_jobs": status.cutting_jobs,
                    "complete_jobs": status.complete_jobs,
                    "error_jobs": status.error_jobs,
                    "total_fabric_cm": status.total_fabric_cm,
                    "estimated_time_minutes": status.estimated_time_minutes,
                },
            }
        )

        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            # Handle client messages if needed

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_status_update():
    """Broadcast current status to all WebSocket clients."""
    status = queue.get_status()
    await manager.broadcast(
        {
            "event": "status_update",
            "data": {
                "total_jobs": status.total_jobs,
                "pending_jobs": status.pending_jobs,
                "cutting_jobs": status.cutting_jobs,
                "complete_jobs": status.complete_jobs,
                "error_jobs": status.error_jobs,
                "total_fabric_cm": status.total_fabric_cm,
                "estimated_time_minutes": status.estimated_time_minutes,
            },
        }
    )


# ============================================================================
# Monitoring Routes
# ============================================================================

# Import monitoring
try:
    from production_monitor import get_monitor

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


@app.get("/api/metrics")
async def get_metrics():
    """Get production metrics dashboard data."""
    if not MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Monitoring system not available")

    monitor = get_monitor()
    return monitor.get_dashboard_data()


@app.get("/api/health/detailed")
async def detailed_health_check():
    """Get detailed system health status with monitoring."""
    if not MONITORING_AVAILABLE:
        return {"healthy": True, "message": "Monitoring not available", "checks": {}}

    monitor = get_monitor()
    return monitor.health_check()


@app.get("/api/alerts")
async def get_alerts():
    """Get active alerts."""
    if not MONITORING_AVAILABLE:
        return {"alerts": []}

    monitor = get_monitor()
    alerts = monitor.get_active_alerts()
    return {
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp,
                "acknowledged": a.acknowledged,
            }
            for a in alerts
        ]
    }


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    if not MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Monitoring system not available")

    monitor = get_monitor()
    if monitor.acknowledge_alert(alert_id):
        return {"success": True, "message": f"Alert {alert_id} acknowledged"}
    else:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert."""
    if not MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Monitoring system not available")

    monitor = get_monitor()
    if monitor.resolve_alert(alert_id):
        return {"success": True, "message": f"Alert {alert_id} resolved"}
    else:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("SameDaySuits Production API")
    print("=" * 60)
    print(f"Dashboard: http://localhost:8000")
    print(f"API Docs:  http://localhost:8000/docs")
    print(f"OpenAPI:   http://localhost:8000/openapi.json")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
