# SameDaySuits Operations Manual

## Version 6.4.2

**Pattern Factory Production System**

---

**Document Information:**
- Version: 6.4.2
- Date: 2026-01-31
- Status: Production
- Classification: Internal Use

**Change History:**
- v6.4.2: Added Database Integration, Queue Management, Pattern Scaling, WebSocket API, System Architecture, Testing Tools, Alert Management
- v6.4.1: Added Nesting Algorithms, Production Monitoring, Quality Control, TheBlackbox Integration
- v6.4: Baseline production release

---

## Table of Contents

### Core Systems
1. [Nesting Algorithms and Optimization](#1-nesting-algorithms-and-optimization)
2. [Production Monitoring System](#2-production-monitoring-system)
3. [Quality Control Automation](#3-quality-control-automation)
4. [TheBlackbox Body Scanner Integration](#4-theblackbox-body-scanner-integration)
5. [Database Integration (Supabase)](#5-database-integration-supabase)
6. [Cutter Queue Management](#6-cutter-queue-management)
7. [Pattern Scaling & Graded Sizes](#7-pattern-scaling--graded-sizes)

### APIs and Interfaces
8. [Updated CLI Commands](#8-updated-cli-commands)
9. [API Endpoints](#9-api-endpoints)
10. [Real-time Systems (WebSocket)](#10-real-time-systems-websocket)

### Architecture and Operations
11. [System Architecture & Data Flow](#11-system-architecture--data-flow)
12. [Testing & Development Tools](#12-testing--development-tools)
13. [Alert Management System](#13-alert-management-system)
14. [Troubleshooting Guides](#14-troubleshooting-guides)

### Reference
- [Appendix A: Complete CLI Reference](#appendix-a-complete-cli-reference)
- [Appendix B: Environment Variables](#appendix-b-environment-variables)
- [Appendix C: File Formats Reference](#appendix-c-file-formats-reference)
- [Appendix D: File Locations](#appendix-d-file-locations)

---

## 1. Nesting Algorithms and Optimization

### 1.1 Overview

The Pattern Factory implements a multi-algorithm nesting system that automatically selects the best layout for fabric utilization. The system achieves **78-88% fabric utilization**, which is excellent for automated garment nesting.

### 1.2 Algorithms Implemented

| Algorithm | Speed | Utilization Range | Best For |
|-----------|-------|-------------------|----------|
| **master_nest** | Medium | 78-88% | Production use (automatic selection) |
| hybrid | Slow | 58-80% | Complex irregular shapes |
| turbo | Medium | 57-77% | Multi-pass optimization |
| guillotine | Fast | 54-83% | Rectangular pieces |
| skyline | Fast | 54-88% | Long pieces |
| shelf | Fastest | 54-60% | Quick previews |

### 1.3 Performance Benchmarks

| Pattern | Pieces | Utilization | Algorithm | Fabric Length |
|---------|--------|-------------|-----------|---------------|
| Basic Tee | 7 | 80.5% | hybrid | 39.7 cm |
| Light Jacket | 15 | 78.1% | guillotine | 56.1 cm |
| Skinny Trousers | 6 | 87.7% | skyline | 180.8 cm |
| Skinny Cargo | 9 | 83.0% | guillotine | 76.4 cm |
| **Average** | - | **82.3%** | - | - |

### 1.4 Why 98% Utilization is Not Achievable

**Theoretical Limitations:**

1. **Piece Shape Irregularity**: Garment pieces are not rectangular. The "bounding box fill ratio" ranges from 65-86%:
   - Skinny Trousers: 65.2% (very curved pieces)
   - Basic Tee: 85.9% (fairly rectangular)
   - Light Jacket: 79.7% (moderately irregular)

2. **Industry Standards**: Professional garment software achieves:
   - 85-92% for irregular pieces
   - 90-95% for rectangular pieces
   - 95-98% only with manual adjustment

3. **Current system achieves 78-88%, which is excellent for fully automated nesting.**

### 1.5 Implementation Details

**Automatic Selection (master_nest):**
```python
from master_nesting import master_nest

result = master_nest(
    contour_groups=contour_groups,
    fabric_width=157.48,  # 62 inches
    gap=0.5,              # 0.5 cm spacing
    verbose=True
)

print(f"Best algorithm: {result.algorithm}")
print(f"Utilization: {result.utilization:.1f}%")
print(f"Fabric length: {result.fabric_length:.1f} cm")
```

**Manual Algorithm Selection:**
```python
# For specific needs, use individual algorithms
from hybrid_nesting import hybrid_nest
from guillotine_nesting import guillotine_nest
from skyline_nesting import skyline_nest
```

### 1.6 Update to Section 2.2.7.1

**NEW:**
```
2.2.7.1 Nesting Optimization
- Implements multi-algorithm nesting with automatic best-selection
- Achieves 78-88% fabric utilization (industry standard: 85-95%)
- Uses master_nest() function which runs multiple algorithms:
  * hybrid: True polygon collision with sliding
  * guillotine: Split free space into rectangles
  * skyline: Track top edge of placements
  * turbo: Shapely-based spatial indexing
- Automatically selects best result based on utilization
- Optimized for 62" (157.48cm) standard fabric width
- Includes quality checks for piece overlap detection

Note: 98% utilization target is unrealistic for automated garment 
nesting without manual optimization or commercial software costing 
$10,000-50,000/year. Current results are excellent for production use.
```

---

## 2. Production Monitoring System

### 2.1 Overview

The Production Monitoring System tracks real-time metrics, monitors system health, and provides alerting for the Pattern Factory pipeline.

### 2.2 Features

**Real-Time Metrics:**
- Orders processed (success/failure rates)
- Fabric consumption (meters used, waste %)
- Queue status (pending, processing, completed)
- Processing times (per stage, total)
- System health (API response time, errors)

**Alert Thresholds:**
- Low utilization (< 60%)
- High failure rate (> 5%)
- Queue backup (> 10 pending orders)
- Slow processing (> 120 seconds)

**Historical Data:**
- Persisted to JSON files in `production_data/`
- Daily summaries automatically generated
- Long-term trend analysis

### 2.3 CLI Commands

```bash
# View system status
sds monitor status

# View current metrics
sds monitor metrics

# View today's summary
sds monitor summary

# View historical data
sds monitor history
```

### 2.4 Web Dashboard

Access at: `http://localhost:8000/monitor`

**Dashboard Sections:**
1. Order Statistics (24h, 7d, 30d views)
2. Fabric Usage (consumption tracking)
3. Queue Status (pending/processing/completed)
4. Processing Times (average by stage)
5. System Health (API status, errors)
6. Alerts (current warnings and issues)

### 2.5 New Section: 2.5 Production Monitoring System

```
2.5 Production Monitoring System

2.5.1 Overview
The Production Monitoring System provides real-time visibility into 
Pattern Factory operations, tracking orders, fabric usage, and system 
health with automated alerting for issues.

2.5.2 Metrics Tracked
- Orders: Total, success rate, failure rate, pending count
- Fabric: Meters consumed, utilization %, waste tracking
- Queue: Pending, processing, completed counts
- Performance: Processing time by stage (scan→nest→cut)
- Health: API response times, error rates, uptime

2.5.3 Alert Configuration
Alert thresholds are configurable in production_monitor.py:
- UTILIZATION_THRESHOLD = 60% (warns if fabric usage drops below)
- FAILURE_THRESHOLD = 5% (alerts if failure rate exceeds)
- QUEUE_THRESHOLD = 10 (warns if >10 orders pending)
- PROCESSING_TIME_THRESHOLD = 120s (alerts if order takes >2 min)

2.5.4 Data Storage
- Real-time metrics: In-memory
- Historical data: production_data/metrics.json
- Daily summaries: production_data/daily_*.json
- Retention: 90 days (configurable)

2.5.5 Integration Points
- Automatically integrated into samedaysuits_api.py
- Tracks every order through complete pipeline
- Exports metrics via /api/metrics endpoint
- Health check via /api/health endpoint

2.5.6 CLI Usage
See Section 5.3 (CLI Reference) for monitor commands.
```

---

## 3. Quality Control Automation

### 3.1 Overview

Quality Control (QC) runs automatically on every order, validating piece count, geometry, fit, and fabric utilization before production.

### 3.2 Validation Checks

**1. Piece Count Validation**
- Verifies number of pieces matches expected range for garment type
- Example: Light Jacket expects 12-20 pieces

**2. Geometry Validation**
- All pieces must be valid polygons
- No self-intersecting edges
- Minimum area thresholds

**3. Fit Validation**
- Compares customer measurements to scaled pattern dimensions
- Calculates measurement mismatches
- Warns on significant deviations (>20%)

**4. Fabric Utilization Check**
- Flags utilization below 60% (potential waste)
- Reports efficiency rating

**5. Small Piece Detection**
- Flags pieces narrower than 2cm (may indicate cutting issues)

### 3.3 QC Report Format

Every order generates a QC report saved as JSON:

```json
{
  "order_id": "SCAN-NORMAL-MAN-001-20260131014945",
  "timestamp": "2026-01-31T01:49:45.123456",
  "status": "PASSED",
  "checks": {
    "piece_count": {"status": "OK", "count": 15, "expected": "12-20"},
    "geometry": {"status": "OK", "invalid_pieces": []},
    "fit_validation": {"status": "WARNING", "mismatches": 3},
    "utilization": {"status": "OK", "percentage": 78.0},
    "small_pieces": {"status": "WARNING", "count": 4}
  },
  "overall_score": "High",
  "errors": [...],
  "warnings": [...],
  "recommendations": [...]
}
```

### 3.4 CLI Commands

```bash
# Validate a specific PLT file
sds qc validate --file path/to/file.plt --garment jacket

# List QC reports
sds qc list

# View QC report for specific order
sds qc report --order <order_id>
```

### 3.5 New Section: 2.6 Quality Control Automation

```
2.6 Quality Control Automation

2.6.1 Overview
Quality Control runs automatically on every production order, validating
the generated patterns meet quality standards before cutting. QC checks
are performed after nesting and before PLT file generation.

2.6.2 Validation Rules

Piece Count Validation:
- Checks actual piece count against expected range
- Expected ranges by garment type:
  * Light Jacket: 12-20 pieces
  * Basic Tee: 5-10 pieces
  * Trousers: 4-8 pieces

Geometry Validation:
- All pieces must be valid, non-self-intersecting polygons
- Minimum area: 1 sq cm
- All points must be numeric and within bounds

Fit Validation:
- Compares customer measurements to pattern dimensions
- Pattern dimensions are half-circumference (front+back = full)
- Warns if measurements deviate >20% from standard
- Notes: Some deviation is normal for custom garments

Fabric Utilization:
- Target: >70% utilization
- Warning: <60% utilization (potential waste)
- Alert: <50% utilization (investigate nesting)

Small Piece Detection:
- Flags pieces <2cm width
- May indicate detail pieces or cutting issues
- Review recommended for flagged pieces

2.6.3 QC Report Structure
Location: DS-speciale/out/orders/<order_id>/<order_id>_qc_report.json

Contains:
- Order identification
- Timestamp
- Overall status (PASSED/FAILED/WARNING)
- Individual check results
- Error details
- Warning explanations
- Recommendations for operators

2.6.4 Manual QC Override
In exceptional cases, QC warnings can be overridden by authorized
personnel. This is logged and requires manager approval.

2.6.5 CLI Reference
See Section 5.3 (CLI Reference) for qc commands.
```

---

## 4. TheBlackbox Body Scanner Integration

### 4.1 Overview

TheBlackbox body scanner integration allows direct processing of 3D scan data into production orders. Scans are validated, measurements extracted, and orders created automatically.

### 4.2 Input Format

**Scan Data JSON Structure:**
```json
{
  "scan_id": "TB-2026-0131-001",
  "timestamp": "2026-01-31T10:30:00Z",
  "scanner_model": "TheBlackbox v2.1",
  "measurements": {
    "chest": 102.0,
    "waist": 88.0,
    "hip": 100.0,
    "shoulder_width": 46.0,
    "neck": 41.0,
    "arm_length": 66.0,
    "inseam": 81.0,
    "torso_length": 71.0
  },
  "quality_score": 0.98,
  "posture": "normal",
  "notes": "Excellent scan quality"
}
```

### 4.3 Quality Levels

| Score | Quality | Action |
|-------|---------|--------|
| >95% | Excellent | Proceed automatically |
| 85-95% | Good | Proceed with note |
| 70-85% | Acceptable | Flag for review |
| <70% | Poor | Reject, request re-scan |

### 4.4 CLI Commands

```bash
# List available scan files
sds scan list

# Validate a scan file
sds scan validate --file path/to/scan.json

# Process scan into production order
sds scan process --file path/to/scan.json --garment jacket --fit regular

# Generate test scan
sds scan generate --profile normal --output path/to/output.json

# Available profiles:
# - normal (athletic/medium build, size Large)
# - fat (heavyset build, size XXL)
# - slim (lean build, size Medium)
# - tall (tall build, size XL)
```

### 4.5 Processing Workflow

```
Scan JSON File
    ↓
Validation (quality check)
    ↓
Measurement Extraction
    ↓
Size Selection (match to template)
    ↓
Pattern Scaling (X/Y factors)
    ↓
Nesting (master_nest)
    ↓
QC Validation
    ↓
PLT Generation
    ↓
Production Order Complete
```

### 4.6 New Section: 2.7 TheBlackbox Body Scanner Integration

```
2.7 TheBlackbox Body Scanner Integration

2.7.1 Overview
The Pattern Factory integrates directly with TheBlackbox 3D body scanner,
allowing seamless conversion of scan data into production-ready patterns.
Scan files contain 28 body measurements that are automatically extracted
and applied to pattern templates.

2.7.2 Scan Input Requirements
File Format: JSON
Required Fields:
- scan_id: Unique identifier
- timestamp: Scan time (ISO 8601)
- measurements: Object with body measurements (cm)
  * chest, waist, hip, shoulder_width, neck
  * arm_length, inseam, torso_length
- quality_score: 0.0-1.0 confidence rating

Optional Fields:
- scanner_model: Hardware version
- posture: normal/forward/back
- notes: Operator observations

2.7.3 Quality Validation
Scan quality determines processing path:

Quality Score | Classification | Processing
--------------|----------------|------------
> 95%         | Excellent      | Fully automated
85-95%        | Good          | Automated with flag
70-85%        | Acceptable    | Automated, review suggested
< 70%         | Poor          | Rejected, requires re-scan

Quality factors:
- Measurement completeness
- Posture detection confidence
- Scan coverage percentage
- Data consistency checks

2.7.4 Measurement Extraction
The system extracts 8 primary measurements:
1. Chest circumference (bust)
2. Waist circumference (narrowest)
3. Hip circumference (fullest)
4. Shoulder width (across back)
5. Neck circumference
6. Arm length (shoulder to wrist)
7. Inseam (crotch to ankle)
8. Torso length (neck to waist)

These map to pattern scaling:
- Width scaling: chest, waist, hip, shoulder
- Length scaling: arm_length, inseam, torso

2.7.5 Size Selection Logic
Based on chest measurement:
- XS: < 86 cm
- S: 86-94 cm
- M: 94-102 cm
- L: 102-110 cm
- XL: 110-118 cm
- 2XL: 118-126 cm
- 3XL: > 126 cm

Base template selected, then fine-tuned with X/Y scaling factors.

2.7.6 Processing Workflow
1. Scan validation (quality check)
2. Measurement extraction
3. Size template selection
4. Scaling calculation (X=width, Y=length)
5. Pattern generation
6. Nesting optimization
7. QC validation
8. PLT file output
9. Order completion

2.7.7 Output Files
Each scan generates:
- <order_id>.plt (HPGL for cutting)
- <order_id>_metadata.json (order details)
- <order_id>_qc_report.json (quality report)

2.7.8 CLI Reference
See Section 5.3 (CLI Reference) for scan commands.

2.7.9 Testing Profiles
For development/testing, use built-in profiles:
- normal: Size Large, athletic build
- fat: Size XXL, heavyset build
- slim: Size Medium, lean build
- tall: Size XL, tall build

Generate with: sds scan generate --profile <type>
```

---

## 5. Database Integration (Supabase)

### 5.1 Overview

The Pattern Factory integrates with Supabase for persistent order storage and synchronization. The system supports both local Supabase instances (via Docker) and cloud-hosted Supabase projects.

### 5.2 Architecture

**Two-Layer Storage:**
1. **Local File System**: Fast, immediate storage during processing
2. **Supabase Database**: Persistent, queryable order history

**Sync Strategy**:
- Orders created locally first (immediate response)
- Background sync to Supabase (async)
- Conflict resolution: Local wins, Supabase is backup

### 5.3 Database Schema

**Core Tables:**

```sql
-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id VARCHAR(100) UNIQUE NOT NULL,
    customer_id VARCHAR(100),
    garment_type VARCHAR(50),
    fit_preference VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    measurements JSONB,
    scaling_factors JSONB,
    fabric_required_cm FLOAT,
    utilization_percent FLOAT,
    plt_file_path VARCHAR(500),
    metadata_path VARCHAR(500),
    qc_report_path VARCHAR(500),
    qc_status VARCHAR(50),
    qc_score VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    default_measurements JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Production Logs table
CREATE TABLE production_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id VARCHAR(100) REFERENCES orders(order_id),
    stage VARCHAR(100),
    status VARCHAR(50),
    details JSONB,
    processing_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### 5.4 Configuration

**Environment Variables:**
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Local Supabase (Docker)
SUPABASE_LOCAL_URL=http://localhost:54321
SUPABASE_LOCAL_KEY=your-local-key
```

### 5.5 Key Classes and Methods

**OrderDatabase Class:**
```python
from database_integration import OrderDatabase

# Initialize
db = OrderDatabase()

# Create order
db.create_order(order_data: dict) -> str

# Get order
db.get_order(order_id: str) -> dict

# Update order status
db.update_order_status(order_id: str, status: str, details: dict)

# List orders
db.list_orders(status: str = None, limit: int = 100) -> list

# Sync local to remote
db.sync_pending_orders()
```

### 5.6 CLI Commands

```bash
# Check database status
sds db status

# Sync local orders to database
sds db sync

# Watch sync operations (real-time)
sds db watch

# Create test order in database
sds db test-order

# Display database schema
sds db schema
```

### 5.7 New Section: 2.8 Database Integration

```
2.8 Database Integration (Supabase)

2.8.1 Overview
The Pattern Factory uses Supabase for persistent order storage, providing
queryable order history, customer management, and production analytics.
Supports both local (Docker) and cloud-hosted instances.

2.8.2 Database Modes

Local Mode (Development):
- Runs via Docker Compose
- URL: http://localhost:54321
- Best for: Development, testing, offline work
- Data persistence: Docker volumes

Cloud Mode (Production):
- Hosted on Supabase Cloud
- Managed infrastructure
- Best for: Production, multi-user access
- Automatic backups included

2.8.3 Connection Configuration
Configuration via environment variables:
- SUPABASE_URL / SUPABASE_LOCAL_URL
- SUPABASE_KEY / SUPABASE_LOCAL_KEY
- SUPABASE_SERVICE_KEY (for admin operations)

2.8.4 Schema Design

Orders Table:
- Primary order storage
- Tracks status, measurements, file paths
- JSONB fields for flexible metadata
- Timestamps for audit trail

Customers Table:
- Customer profile storage
- Default measurements
- Contact information

Production Logs Table:
- Detailed processing logs
- Per-stage timing
- Error tracking
- Supports debugging and optimization

2.8.5 Sync Architecture

Two-Layer Storage:
1. Local filesystem (fast, immediate)
2. Supabase (persistent, queryable)

Sync Strategy:
- Write-through: Local first, async to Supabase
- Conflict resolution: Local wins
- Retry logic: 3 attempts with exponential backoff
- Batch processing: 10 orders per sync cycle

2.8.6 CLI Reference
See Section 8 (CLI Reference) for db commands.

2.8.7 Monitoring
Check sync status via:
- sds db status (CLI)
- /api/metrics endpoint (API)
- Dashboard sync indicator (Web UI)

2.8.8 Troubleshooting

Sync Failures:
- Check network connectivity
- Verify Supabase credentials
- Review sync logs in production_logs table
- Manual retry: sds db sync

Missing Orders:
- Check local directory: DS-speciale/out/orders/
- Verify order_id format
- Check Supabase permissions

2.8.9 Backup Strategy
Local: Filesystem backups
Cloud: Supabase automatic daily backups
Manual: pg_dump for complete database export
```

---

## 6. Cutter Queue Management

### 6.1 Overview

The Cutter Queue manages the flow of orders to physical cutting machines. It provides job prioritization, spool management, and status tracking for production cutting operations.

### 6.2 Queue Architecture

**Components:**
1. **Job Queue**: In-memory priority queue
2. **Spool Directory**: Filesystem-based job storage
3. **Status Tracking**: Job state machine
4. **Priority System**: Urgent/High/Normal/Low priorities

### 6.3 Job Lifecycle

```
PENDING → QUEUED → PROCESSING → COMPLETED
   ↓         ↓          ↓           ↓
Cancel   Pause     Error      Archived
```

**States:**
- `PENDING`: Order submitted, awaiting queue
- `QUEUED`: In queue, waiting for cutter
- `PROCESSING`: Currently being cut
- `COMPLETED`: Successfully cut
- `FAILED`: Error during cutting
- `CANCELLED`: Cancelled before processing
- `PAUSED`: Temporarily paused

### 6.4 Priority System

| Priority | Value | Use Case |
|----------|-------|----------|
| URGENT | 1 | Rush orders, same-day delivery |
| HIGH | 2 | Priority customers |
| NORMAL | 3 | Standard orders (default) |
| LOW | 4 | Bulk orders, non-urgent |

### 6.5 CLI Commands

```bash
# View queue status
sds queue status

# List all jobs
sds queue list

# Watch queue (real-time updates)
sds queue watch

# Process next job in queue
sds queue process

# Cancel specific job
sds queue cancel <job_id>
```

### 6.6 API Endpoints

```
GET /queue/status
  Returns current queue status:
  {
    "pending": 5,
    "processing": 1,
    "completed": 150,
    "failed": 3,
    "paused": false
  }

POST /queue/process-next
  Process next highest priority job
```

### 6.7 New Section: 2.9 Cutter Queue Management

```
2.9 Cutter Queue Management

2.9.1 Overview
The Cutter Queue manages the flow of production orders to physical cutting
machines. Provides job prioritization, status tracking, and operator workflow
management for the cutting stage of production.

2.9.2 Queue Components

Job Queue:
- In-memory priority queue (heapq)
- Prioritizes by: Priority level → Submission time
- Thread-safe for concurrent access

Spool Directory:
- Filesystem-based persistence
- Organized by status: pending/processing/completed/failed
- JSON metadata + PLT file references

Status Tracking:
- State machine: PENDING → QUEUED → PROCESSING → COMPLETED
- Alternative states: FAILED, CANCELLED, PAUSED
- Timestamp tracking for each state transition

2.9.3 Priority System

Four Priority Levels:
1. URGENT (1): Rush orders, same-day requirements
2. HIGH (2): VIP customers, priority shipping
3. NORMAL (3): Standard orders (default)
4. LOW (4): Bulk orders, future delivery

Priority Calculation:
Base priority value + time in queue (aging) - customer tier bonus

2.9.4 Job Lifecycle

Submission:
- Order completes QC validation
- Job automatically created and queued
- Metadata written to spool/pending/
- Notification sent to operators

Processing:
- Operator loads fabric
- Retrieves next job from queue
- PLT file transferred to cutter
- Status updated to PROCESSING

Completion:
- Pieces cut and verified
- Status updated to COMPLETED
- Job moved to spool/completed/
- Order marked complete in database

Failure Handling:
- Errors logged with details
- Job moved to spool/failed/
- Operator can retry or cancel
- Automatic retry for transient errors

2.9.5 Operator Workflow

Daily Operations:
1. Check queue status (sds queue status)
2. Monitor dashboard for new jobs
3. Load appropriate fabric
4. Process next job (sds queue process-next)
5. Verify cut pieces
6. Mark complete and stage for sewing

Priority Overrides:
- Operators can manually prioritize jobs
- Rush orders flagged in dashboard
- Queue can be paused/resumed

2.9.6 CLI Reference
See Section 8 (CLI Reference) for queue commands.

2.9.7 API Reference
See Section 9 (API Reference) for queue endpoints.

2.9.8 Monitoring

Queue Metrics:
- Jobs pending/processing/completed
- Average wait time
- Priority distribution
- Failure rate

Available via:
- sds monitor status (CLI)
- /api/metrics endpoint (API)
- Dashboard queue widget (Web)

2.9.9 Troubleshooting

Job Stuck in Processing:
- Check cutter connectivity
- Verify PLT file exists
- Review cutter logs
- Manually mark failed if cutter error

Queue Backup:
- Check operator capacity
- Verify fabric availability
- Consider adding cutter shifts
- Review priority distribution

Failed Jobs:
- Check error message in job metadata
- Verify PLT file integrity
- Review QC report for issues
- Retry or regenerate order
```

---

## 7. Pattern Scaling & Graded Sizes

### 7.1 Overview

Pattern scaling adjusts base garment templates to fit individual customer measurements. The system supports both proportional scaling and graded size extraction from PDS files.

### 7.2 Size Chart

**Standard Size Ranges (Chest):**

| Size | Chest (cm) | Chest (in) | Scale Base |
|------|------------|------------|------------|
| XS | < 86 | < 34 | XS template |
| S | 86-94 | 34-37 | S template |
| M | 94-102 | 37-40 | M template |
| L | 102-110 | 40-43 | L template |
| XL | 110-118 | 43-46 | XL template |
| 2XL | 118-126 | 46-50 | 2XL template |
| 3XL | 126-134 | 50-53 | 3XL template |
| 4XL | > 134 | > 53 | 4XL template |

### 7.3 Scaling Constraints

**Minimum/Maximum Scales:**
- Width (X): 0.85 to 1.15 (±15%)
- Length (Y): 0.85 to 1.15 (±15%)

### 7.4 CLI Commands

```bash
# Show size chart
sds sizes --template jacket

# Show graded sizes for template
sds sizes --template trousers
```

### 7.5 New Section: 2.10 Pattern Scaling

```
2.10 Pattern Scaling & Graded Sizes

2.10.1 Overview
Pattern scaling adjusts base garment templates to match individual customer
measurements. Uses a two-stage approach: size selection then fine-tuning
with X/Y scaling factors.

2.10.2 Size Selection

Base Template Selection:
Determined primarily by chest measurement:
- XS: < 86 cm
- S: 86-94 cm
- M: 94-102 cm
- L: 102-110 cm
- XL: 110-118 cm
- 2XL: 118-126 cm
- 3XL: 126-134 cm
- 4XL: > 134 cm

Secondary Considerations:
- Waist measurement (for trousers)
- Hip measurement (for bottoms)
- Height estimate (affects length)

2.10.3 Scaling Methodology

Width Scaling (X-axis):
- Based on: chest, waist, hip, shoulder measurements
- Formula: customer_measurement / base_measurement
- Range: 0.85 to 1.15 (clamped)
- Application: Applied to pattern width dimensions

Length Scaling (Y-axis):
- Based on: inseam, arm_length, torso measurements
- Formula: customer_measurement / base_measurement
- Range: 0.85 to 1.15 (clamped)
- Application: Applied to pattern length dimensions

Proportional Pieces:
- Buttons, pockets, details scale uniformly
- Scale factor: minimum of X and Y scales
- Maintains visual proportions

2.10.4 Graded Size Extraction

From PDS Templates:
- Extracts all available sizes from graded patterns
- Maps size names to measurement tables
- Supports: XS, S, M, L, XL, 2XL, 3XL, 4XL
- Fallback to standard chart if extraction fails

Best Size Algorithm:
1. Calculate difference for each measurement
2. Weight by measurement importance (chest = 40%, waist = 30%, etc.)
3. Select size with minimum weighted difference
4. Apply fine scaling to match exactly

2.10.5 Scaling Constraints

Safety Limits:
- Minimum scale: 0.85 (15% reduction)
- Maximum scale: 1.15 (15% increase)
- Rationale: Prevents distortion, maintains proportions

Exceptions:
- Extreme sizes may require next size template
- Operator notification on clamping
- QC validation flags unusual scaling

2.10.6 CLI Reference
See Section 8 (CLI Reference) for sizes command.

2.10.7 API Integration

Automatic Scaling:
- Applied during order processing
- Uses customer measurements from order
- Logs scaling factors in metadata
- Validates with QC system

Manual Override:
- Operators can specify base size
- Custom scaling factors supported
- Requires manager approval for extreme values

2.10.8 Quality Assurance

Fit Validation:
- QC system compares scaled pattern to measurements
- Warns if deviations >20%
- Validates scaling factors in safe range
- Checks for extreme aspect ratios

Measurement Mismatch Handling:
- Normal: Some deviation expected (half vs full circumference)
- Warning: >20% deviation flagged for review
- Error: >30% deviation triggers rejection
```

---

## 8. Updated CLI Commands

### 8.1 New Commands Added

**Monitor Commands:**
```bash
sds monitor status       # Show system status dashboard
sds monitor metrics      # Display current metrics
sds monitor summary      # Show today's summary
sds monitor history      # Show historical data
sds monitor alerts       # View active alerts
sds monitor health       # Health check
```

**QC Commands:**
```bash
sds qc validate          # Validate a PLT file
sds qc list              # List QC reports
sds qc report            # View specific QC report
```

**Scan Commands:**
```bash
sds scan list            # List available scan files
sds scan validate        # Validate a scan file
sds scan process         # Process scan into order
sds scan generate        # Generate test scan profile
```

**Database Commands:**
```bash
sds db status            # Check database status
sds db sync              # Sync to database
sds db watch             # Watch sync operations
sds db test-order        # Create test order
sds db schema            # Show schema
```

**Queue Commands:**
```bash
sds queue status         # View queue status
sds queue list           # List all jobs
sds queue watch          # Watch queue real-time
sds queue process        # Process next job
sds queue cancel         # Cancel job
```

### 8.2 Complete CLI Reference Section

```
8.2 CLI Reference

8.2.1 Order Commands

order [--id ID] [--customer ID] [--garment TYPE] [--fit TYPE]
      [--chest CM] [--waist CM] [--hip CM] [--shoulder CM] [--inseam CM]
  Process single order through pipeline
  Options:
    --id: Order ID (auto-generated if not provided)
    --customer: Customer identifier
    --garment: Garment type (tee, jacket, trousers, cargo)
    --fit: Fit preference (slim, regular, loose)
    --chest, --waist, --hip, --shoulder, --inseam: Measurements in cm

batch <file>
  Process multiple orders from JSON file
  File format: Array of order objects

8.2.2 Queue Commands

queue status
  Display current queue status
  Shows: pending, processing, completed, failed counts

queue list [--status STATUS]
  List all jobs in queue
  --status: Filter by status (pending, processing, completed, failed)

queue watch
  Watch queue in real-time (updates every 5 seconds)
  Press Ctrl+C to exit

queue process [--job-id ID]
  Process next job in queue
  --job-id: Process specific job (operators only)

queue cancel <job-id>
  Cancel pending or paused job

queue pause
  Pause queue (no new jobs processed)

queue resume
  Resume paused queue

8.2.3 Template Commands

templates
  List available garment templates
  Shows: garment type, PDS file, available sizes

sizes --template <type>
  Show graded size information for template
  --template: Garment type (tee, jacket, trousers, cargo)

8.2.4 Database Commands

db status
  Check database connection and sync status
  Shows: connection state, pending syncs, last sync time

db sync
  Manually trigger sync of pending orders to database
  Useful after network interruption

db watch
  Watch sync operations in real-time

db test-order
  Create test order in database
  Useful for validating database connection

db schema
  Display database schema (SQL)

8.2.5 Monitor Commands

monitor status
  Display real-time system status
  Sections: orders, fabric, queue, processing, health, alerts

monitor dashboard
  Open web dashboard in browser
  Launches: http://localhost:8000

monitor metrics [--period PERIOD]
  Display production metrics
  --period: Time period (24h, 7d, 30d, all)

monitor summary [--date DATE]
  Show summary for specific date
  --date: Date in YYYY-MM-DD format (default: today)

monitor history [--days DAYS]
  Show historical trends
  --days: Number of days to show (default: 30)

monitor alerts [--severity SEVERITY]
  View active alerts
  --severity: Filter by severity (critical, error, warning, info)

monitor health
  Run health checks on all systems

8.2.6 QC Commands

qc validate --file PATH [--garment TYPE]
  Validate PLT file for production readiness
  --file: Path to PLT file
  --garment: Garment type for piece count validation

qc list [--date DATE] [--status STATUS]
  List QC reports
  --date: Filter by date
  --status: Filter by status (passed, failed, warning)

qc report --order ORDER_ID
  Display QC report for specific order
  --order: Order ID

8.2.7 Scan Commands

scan list [--directory PATH]
  List available scan files
  --directory: Custom scan directory

scan validate --file PATH
  Validate scan file format and quality
  --file: Path to scan JSON file

scan process --file PATH --garment TYPE [--fit TYPE]
  Process scan into production order
  --file: Path to scan JSON file
  --garment: Garment type
  --fit: Fit preference (default: regular)

scan generate --profile TYPE [--output PATH]
  Generate test scan profile
  --profile: Profile type (normal, fat, slim, tall)
  --output: Output file path

8.2.8 Server Commands

serve [--host HOST] [--port PORT] [--reload]
  Start web API server
  --host: Bind address (default: 0.0.0.0)
  --port: Port number (default: 8000)
  --reload: Enable auto-reload (development only)

8.2.9 Testing Commands

test [--verbose]
  Run pipeline test
  Processes test order and validates output
```

---

## 9. API Endpoints

### 9.1 Production Endpoints

```
GET /api/metrics
  Returns production metrics and statistics
  Authentication: Required (API key)
  Response: JSON with order counts, fabric usage, queue status
  
  Example Response:
  {
    "orders": {
      "total": 150,
      "success_rate": 0.97,
      "failure_rate": 0.03,
      "pending": 3
    },
    "fabric": {
      "consumed_m": 450.5,
      "waste_percentage": 18.0,
      "avg_utilization": 0.82
    },
    "queue": {
      "pending": 3,
      "processing": 1,
      "completed": 146
    },
    "processing": {
      "avg_seconds": 45.2,
      "max_seconds": 120.5,
      "min_seconds": 23.1
    }
  }

GET /api/health
  Returns system health status
  Authentication: None (public endpoint)
  Response: JSON with health indicators
  
  Example Response:
  {
    "status": "healthy",
    "api_response_ms": 23,
    "last_error": null,
    "uptime_seconds": 86400,
    "timestamp": "2026-01-31T01:49:45Z"
  }
```

### 9.2 Updated Order Endpoints

```
GET /api/orders
  Now includes QC information:
  
  Extended Response Fields:
  {
    "orders": [{
      "id": "order-001",
      "status": "completed",
      "qc_status": "passed",
      "qc_score": "High",
      "qc_warnings": 2,
      "qc_errors": 0,
      "fabric_utilization": 0.78,
      "created_at": "...",
      "completed_at": "..."
    }]
  }

GET /api/orders/{order_id}/qc
  Returns QC report for specific order
  Authentication: Required
  Response: Full QC report JSON
```

### 9.3 Queue Endpoints

```
GET /queue/status
  Returns current queue status:
  {
    "pending": 5,
    "processing": 1,
    "completed": 150,
    "failed": 3,
    "paused": false
  }

GET /queue/jobs?status=<status>
  List jobs with optional status filter

GET /queue/jobs/{job_id}
  Get specific job details

POST /queue/jobs/{job_id}/process
  Mark job as processing (cutter started)

POST /queue/jobs/{job_id}/complete
  Mark job as completed

POST /queue/process-next
  Process next highest priority job
```

### 9.4 Alert Endpoints

```
GET /api/alerts
  Returns active alerts:
  {
    "alerts": [
      {
        "id": "ALT-001",
        "severity": "warning",
        "type": "low_utilization",
        "message": "Average utilization below 60%",
        "detected_at": "2026-01-31T10:00:00Z",
        "acknowledged": false,
        "acknowledged_by": null
      }
    ]
  }

POST /api/alerts/{alert_id}/acknowledge
  Acknowledge alert
  Body: {"acknowledged_by": "operator_name"}

POST /api/alerts/{alert_id}/resolve
  Resolve alert
  Body: {"resolution_notes": "Fixed nesting algorithm"}
```

---

## 10. Real-time Systems (WebSocket)

### 10.1 Overview

The Pattern Factory provides real-time updates via WebSocket connections for live dashboard updates, progress tracking, and system notifications.

### 10.2 WebSocket Architecture

**Connection Endpoint:**
```
ws://localhost:8000/ws
wss://production.samedaysuits.com/ws (SSL)
```

### 10.3 Message Types

**Server → Client (Updates):**

```json
// Order Status Update
{
  "type": "order_update",
  "order_id": "ORDER-001",
  "status": "processing",
  "stage": "nesting",
  "progress": 65,
  "timestamp": "2026-01-31T10:30:00Z"
}

// Queue Update
{
  "type": "queue_update",
  "pending": 5,
  "processing": 1,
  "completed": 150,
  "timestamp": "2026-01-31T10:30:00Z"
}

// Alert
{
  "type": "alert",
  "alert_id": "ALT-001",
  "severity": "warning",
  "message": "Low fabric utilization detected",
  "timestamp": "2026-01-31T10:30:00Z"
}
```

**Client → Server (Commands):**

```json
// Subscribe to order
{
  "action": "subscribe",
  "order_id": "ORDER-001"
}

// Acknowledge alert
{
  "action": "ack_alert",
  "alert_id": "ALT-001"
}
```

### 10.4 New Section: 3.4 WebSocket API

```
3.4 WebSocket API

3.4.1 Overview
The WebSocket API provides real-time bidirectional communication for 
live dashboard updates, order progress tracking, and system notifications.

3.4.2 Connection

Endpoint: ws://<host>:8000/ws
Protocol: WebSocket (RFC 6455)
Authentication: Same as REST API (token in query string or header)

3.4.3 Server Messages (Server → Client)

order_update:
- Sent: During order processing stages
- Fields: order_id, status, stage, progress (0-100)
- Frequency: Every 5 seconds during processing

queue_update:
- Sent: When queue status changes
- Fields: pending, processing, completed counts
- Frequency: Every 10 seconds or on change

alert:
- Sent: When alert triggered
- Fields: alert_id, severity, message
- Frequency: Immediate

system_status:
- Sent: Periodic health updates
- Fields: status, active_orders, api_latency_ms
- Frequency: Every 30 seconds

3.4.4 Client Messages (Client → Server)

subscribe:
- Purpose: Subscribe to order updates
- Fields: action="subscribe", order_id

ack_alert:
- Purpose: Acknowledge alert receipt
- Fields: action="ack_alert", alert_id

ping:
- Purpose: Keep connection alive
- Fields: action="ping"
- Response: pong message

3.4.5 Rate Limiting

Connection Limits:
- Max connections: 100 per server
- Max subscriptions: 50 per connection
- Message rate: 10/second per client
```

---

## 11. System Architecture & Data Flow

### 11.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT INTERFACES                        │
├─────────────────────────────────────────────────────────────────┤
│  CLI (sds)        Web Dashboard        REST API        Scanner │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SAME DAY SUITS API                          │
│                   (samedaysuits_api.py)                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PRODUCTION PIPELINE                           │
│               (production_pipeline.py)                          │
├─────────────────────────────────────────────────────────────────┤
│  PDS Load → Extract → Scale → Nest → QC → PLT                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ PATTERN SCALER   │ │ NESTING ENGINE   │ │ QUALITY CONTROL  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CUTTER QUEUE                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATABASE & MONITORING                              │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Data Flow

**Order Processing Flow:**

```
1. ORDER INTAKE
   Input: Customer measurements, garment type, fit preference
   
2. ORDER VALIDATION
   - Validate measurements (range checks)
   - Verify garment type available
   - Create order record
   
3. PATTERN SELECTION
   - Map garment type to PDS template
   - Select base size from measurements
   - Load PDS file
   
4. PATTERN SCALING
   - Calculate X/Y scaling factors
   - Apply to pattern contours
   - Log scaling parameters
   
5. NESTING
   - Run master_nest algorithm
   - Optimize for fabric width (62")
   - Calculate utilization
   
6. QUALITY CONTROL
   - Validate piece count
   - Check geometry integrity
   - Verify fit measurements
   - Generate QC report
   
7. PLT GENERATION
   - Convert nested layout to HPGL
   - Generate .plt file
   
8. CUTTER QUEUE
   - Create cutter job
   - Assign priority
   - Add to spool
   
9. DATABASE SYNC
   - Save order to local files
   - Queue for Supabase sync
```

### 11.3 New Section: 4.0 System Architecture

```
4.0 System Architecture & Data Flow

4.0.1 Overview
The Pattern Factory uses a layered architecture with clear separation of
concerns: client interfaces, business logic, processing pipeline, and
infrastructure services.

4.0.2 Architecture Layers

Layer 1: Client Interfaces
- CLI (sds_cli.py): Command-line operations
- Web Dashboard (web_api.py): Browser-based UI
- REST API (web_api.py): Programmatic access
- Scanner Integration (theblackbox_integration.py): 3D scan input

Layer 2: Business Logic
- SameDaySuitsAPI (samedaysuits_api.py): Core orchestration
- Order management and validation
- Customer measurement handling
- Queue management

Layer 3: Processing Pipeline
- ProductionPipeline (production_pipeline.py): End-to-end processing
- PatternScaler (pattern_scaler.py): Measurement-based scaling
- NestingEngine (master_nesting.py): Fabric optimization
- QualityControl (quality_control.py): Validation

Layer 4: Infrastructure
- Database (database_integration.py): Supabase persistence
- CutterQueue (cutter_queue.py): Physical production queue
- ProductionMonitor (production_monitor.py): Metrics and alerting
- FileSystem: Local storage for orders and artifacts

4.0.3 Storage Strategy

Two-Tier Storage:
1. Local Filesystem: Fast access, immediate response
   - PLT files
   - Order metadata
   - QC reports
   - Temp processing files

2. Supabase Database: Persistent, queryable
   - Order history
   - Customer records
   - Production logs
   - Analytics data

Sync Strategy:
- Write-through: Local first, async to DB
- Conflict resolution: Local wins
- Retry logic: Exponential backoff

4.0.4 Key Files and Locations

Source Code:
- Core: samedaysuits_api.py, production_pipeline.py
- CLI: sds_cli.py
- Web: web_api.py, start_dashboard.py
- Processing: pattern_scaler.py, quality_control.py
- Queue: cutter_queue.py
- Database: database_integration.py
- Monitor: production_monitor.py

Data:
- Templates: DS-speciale/inputs/pds/
- Orders: DS-speciale/out/orders/
- Queue: DS-speciale/out/cutter_spool/
- Scans: scans/
- Monitoring: production_data/
```

---

## 12. Testing & Development Tools

### 12.1 Test Profiles

**Built-in Test Profiles:**

| Profile | Size | Build | Measurements |
|---------|------|-------|--------------|
| normal | Large | Athletic | Chest:102, Waist:88, Hip:100 |
| fat | XXL | Heavyset | Chest:120, Waist:110, Hip:115 |
| slim | Medium | Lean | Chest:94, Waist:76, Hip:92 |
| tall | XL | Tall | Chest:108, Waist:90, Hip:104 |

### 12.2 CLI Commands

```bash
# Generate test scans
sds scan generate --profile normal --output scans/test_normal.json
sds scan generate --profile fat --output scans/test_fat.json
sds scan generate --profile slim --output scans/test_slim.json
sds scan generate --profile tall --output scans/test_tall.json

# Run pipeline test
sds test

# Process test batch
sds batch test_orders.json
```

### 12.3 New Section: 6.0 Testing & Development

```
6.0 Testing & Development Tools

6.0.1 Overview
The Pattern Factory includes comprehensive testing infrastructure for 
validating functionality, benchmarking performance, and ensuring quality.

6.0.2 Test Profiles

Built-in Profiles:
- normal: Size Large, athletic build (Chest:102, Waist:88)
- fat: Size XXL, heavyset build (Chest:120, Waist:110)
- slim: Size Medium, lean build (Chest:94, Waist:76)
- tall: Size XL, tall build (Chest:108, Waist:90)

Generation:
sds scan generate --profile <type> --output <path>

6.0.3 Pipeline Testing

Standard Test:
sds test
- Processes test order through full pipeline
- Validates PLT output
- Reports timing and utilization
- Checks for errors

6.0.4 API Testing

Using curl:
Test endpoints manually with HTTP requests

Using Test Client (test_web_api.py):
Programmatic testing with assertions
- test_health(): Verify API responsive
- test_create_order(): Validate order creation
- test_get_order(): Check order retrieval

6.0.5 Algorithm Testing

Compare Nesting Algorithms:
python master_nesting.py --compare --all
- Runs all algorithms on same pattern
- Compares utilization and speed
- Recommends best algorithm

6.0.6 Performance Testing

Load Testing:
Process multiple orders sequentially
Monitor for degradation
Identify bottlenecks

Benchmarking:
Measure processing times
Track resource usage
Compare algorithm performance
```

---

## 13. Alert Management System

### 13.1 Alert Types

**System Alerts:**
- High failure rate (>5% orders failing)
- Low fabric utilization (<60% average)
- Queue backup (>10 pending jobs)
- Slow processing (>120s per order)
- Database sync failures

**Quality Alerts:**
- QC validation failures
- Pattern geometry errors
- Measurement mismatches (>30%)

**Infrastructure Alerts:**
- Disk space low (<10% free)
- Memory usage high (>80%)
- API response time slow (>500ms)

### 13.2 Severity Levels

| Level | Color | Response Time | Action |
|-------|-------|---------------|--------|
| CRITICAL | Red | Immediate | Page on-call engineer |
| ERROR | Orange | 15 minutes | Notify manager |
| WARNING | Yellow | 1 hour | Log and notify operators |
| INFO | Blue | None | Log only |

### 13.3 CLI Commands

```bash
# View active alerts
sds monitor alerts

# Acknowledge alert
sds monitor ack <alert_id>

# Resolve alert
sds monitor resolve <alert_id>
```

### 13.4 New Section: 2.11 Alert Management

```
2.11 Alert Management System

2.11.1 Overview
The Alert Management System provides automated detection and notification
of operational issues, ensuring rapid response to production problems.

2.11.2 Alert Categories

System Alerts:
- High failure rate (>5% orders failing)
- Low fabric utilization (<60%)
- Queue backup (>10 pending jobs)
- Slow processing (>120s per order)
- Database sync failures
- Infrastructure issues

Quality Alerts:
- QC validation failures
- Pattern geometry errors
- Extreme measurement mismatches (>30%)

2.11.3 Severity Levels

CRITICAL (Red):
- Immediate response required
- Pages on-call engineer
- Examples: System down, data loss risk

ERROR (Orange):
- Response within 15 minutes
- Notifies manager
- Examples: High failure rate, cutter offline

WARNING (Yellow):
- Response within 1 hour
- Notifies operators
- Examples: Low utilization, queue building

INFO (Blue):
- No response required
- Logged for awareness
- Examples: Routine completions

2.11.4 Alert Lifecycle

Detection: Monitoring system identifies issue
Activation: Alert created and notifications sent
Acknowledgment: Operator confirms awareness
Resolution: Issue fixed
Closure: Alert archived
Escalation: Auto-escalate if unacknowledged (30 min)

2.11.5 Response Procedures

Critical Alert Response:
1. Acknowledge immediately
2. Assess severity and impact
3. Notify team if needed
4. Implement fix
5. Verify resolution
6. Document in post-mortem

Warning Alert Response:
1. Review within 1 hour
2. Determine if action needed
3. Implement preventive measures
4. Monitor for recurrence

2.11.6 CLI Reference
See Section 8 (CLI Reference) for alert commands.

2.11.7 API Reference
See Section 9 (API Reference) for alert endpoints.
```

---

## 14. Troubleshooting Guides

### 14.1 Nesting Issues

**Low Utilization (<60%)**
- Check piece shapes: Very irregular pieces reduce max utilization
- Verify fabric width: Ensure 157.48cm (62") is set correctly
- Try manual algorithm: Use `hybrid` for complex shapes
- Review gap settings: Default 0.5cm

**Overlapping Pieces**
- Check contour_group boundaries
- Verify no duplicate pieces
- Review scaling factors (should be ~1.0)
- Use hybrid_nest which has collision detection

### 14.2 QC Failures

**Piece Count Mismatch**
- Verify garment type is correct
- Check PDS file loaded all pieces
- Review contour_group processing

**Geometry Errors**
- Check for self-intersecting polygons
- Verify all coordinates are numeric
- Ensure minimum piece area > 1 sq cm

**Fit Validation Warnings**
- Normal for custom garments (some deviation expected)
- Check measurement units (cm vs inches)
- Verify pattern dimensions are half-circumference

### 14.3 Scan Processing Issues

**Poor Scan Quality (<70%)**
- Request customer re-scan
- Check scanner calibration
- Verify adequate lighting

**Missing Measurements**
- Validate scan JSON structure
- Check all required fields present
- Verify measurement values are numeric

### 14.4 Monitoring Alerts

**Alert: "Low utilization detected"**
- Review nesting algorithm settings
- Check fabric width configuration
- Verify piece shapes are correct

**Alert: "High failure rate"**
- Check error logs
- Verify input data quality
- Review recent code changes

**Alert: "Queue backup"**
- Check processing server load
- Verify no stuck processes
- Scale workers if needed

---

## Appendix A: Complete CLI Reference

### A.1 Command Summary

```bash
# Order Management
sds order [options]              # Process single order
sds batch <file>                 # Process batch from JSON

# Queue Management  
sds queue status                 # View queue status
sds queue list                   # List all jobs
sds queue watch                  # Watch queue real-time
sds queue process                # Process next job

# Templates & Sizes
sds templates                    # List available templates
sds sizes --template <type>      # Show graded size info

# Database
sds db status                    # Check database status
sds db sync                      # Sync to database
sds db watch                     # Watch sync operations
sds db test-order                # Create test order
sds db schema                    # Show schema

# Monitoring
sds monitor status               # System status
sds monitor dashboard            # Open dashboard
sds monitor metrics              # View metrics
sds monitor summary              # Today's summary
sds monitor history              # Historical data
sds monitor alerts               # View alerts
sds monitor health               # Health check

# Quality Control
sds qc validate [options]        # Validate PLT file
sds qc list                      # List QC reports
sds qc report --order <id>       # View QC report

# Scanner Integration
sds scan list                    # List scan files
sds scan validate [options]      # Validate scan
sds scan process [options]       # Process scan
sds scan generate [options]      # Generate test scan

# Server
sds serve [options]              # Start web server

# Testing
sds test                         # Run pipeline test
```

### A.2 Global Options

```bash
--verbose, -v        # Verbose output
--quiet, -q          # Suppress non-error output
--config <path>      # Config file path
--dry-run            # Simulate without executing
--help               # Show help
--version            # Show version
```

---

## Appendix B: Environment Variables

### B.1 Required Variables

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Processing
CUTTER_WIDTH_CM=157.48
NESTING_GAP_CM=0.5
```

### B.2 Optional Variables

```bash
# Paths
TEMPLATE_DIR=DS-speciale/inputs/pds/
OUTPUT_DIR=DS-speciale/out/orders/
SPOOL_DIR=DS-speciale/out/cutter_spool/

# Performance
MAX_WORKERS=4
NESTING_TIMEOUT=300
ENABLE_CACHE=true

# Monitoring
METRICS_RETENTION_DAYS=90
ALERT_EMAIL=ops@samedaysuits.com
ENABLE_PAGERDUTY=false

# Development
DEBUG=false
LOG_LEVEL=INFO
TEST_MODE=false
```

---

## Appendix C: File Formats Reference

### C.1 Order JSON Format

```json
{
  "order_id": "string",
  "customer_id": "string",
  "garment_type": "tee|jacket|trousers|cargo",
  "fit_preference": "slim|regular|loose",
  "customer_measurements": {
    "chest": "float (cm)",
    "waist": "float (cm)",
    "hip": "float (cm)",
    "shoulder": "float (cm)",
    "inseam": "float (cm)"
  },
  "created_at": "ISO 8601 timestamp"
}
```

### C.2 Scan JSON Format

```json
{
  "scan_id": "string",
  "timestamp": "ISO 8601",
  "scanner_model": "string",
  "measurements": {
    "chest": "float",
    "waist": "float",
    "hip": "float",
    "shoulder_width": "float",
    "neck": "float",
    "arm_length": "float",
    "inseam": "float",
    "torso_length": "float"
  },
  "quality_score": "float (0.0-1.0)",
  "posture": "normal|forward|back",
  "notes": "string"
}
```

### C.3 QC Report Format

```json
{
  "order_id": "string",
  "timestamp": "ISO 8601",
  "status": "PASSED|FAILED|WARNING",
  "checks": {
    "piece_count": {"status": "OK|FAIL", "count": "int", "expected": "string"},
    "geometry": {"status": "OK|FAIL", "invalid_pieces": []},
    "fit_validation": {"status": "OK|FAIL", "mismatches": "int"},
    "utilization": {"status": "OK|FAIL", "percentage": "float"},
    "small_pieces": {"status": "OK|FAIL", "count": "int"}
  },
  "overall_score": "High|Medium|Low",
  "errors": [],
  "warnings": [],
  "recommendations": []
}
```

---

## Appendix D: File Locations

### D.1 Source Files

```
Core Production:
- samedaysuits_api.py           # Main production API
- production_pipeline.py        # End-to-end pipeline
- sds_cli.py                    # CLI interface
- web_api.py                    # Web API and dashboard
- start_dashboard.py            # Dashboard launcher

Processing:
- master_nesting.py             # Best-of-all nesting selector
- hybrid_nesting.py             # True polygon collision
- pattern_scaler.py             # Pattern scaling logic
- graded_size_extractor.py      # Size extraction from PDS

Quality & Monitoring:
- quality_control.py            # QC validation engine
- production_monitor.py         # Monitoring & alerting
- cutter_queue.py               # Cutter job queue

Integrations:
- database_integration.py       # Supabase integration
- theblackbox_integration.py    # Body scanner integration
```

### D.2 Data Directories

```
DS-speciale/
├── inputs/
│   └── pds/                    # PDS template files
├── out/
│   ├── orders/                 # Generated order files
│   │   └── <order_id>/
│   │       ├── <order_id>.plt
│   │       ├── <order_id>_metadata.json
│   │       └── <order_id>_qc_report.json
│   └── cutter_spool/           # Cutter queue
│       ├── pending/
│       ├── processing/
│       ├── completed/
│       └── failed/

scans/                          # TheBlackbox scan files
production_data/                # Monitoring data
```

---

**End of Operations Manual v6.4.2**

**Document Version:** 6.4.2  
**Last Updated:** 2026-01-31  
**Total Sections:** 14 + 4 Appendices  
**Status:** Production Ready
