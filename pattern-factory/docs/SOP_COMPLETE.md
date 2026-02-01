# SameDaySuits Pattern Factory
# Standard Operating Procedures (SOP)

**Version:** 1.0  
**Date:** 2026-02-01  
**Location:** Amritsar, India  
**Status:** Production  

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-01 | Claude | Initial release |

---

## Table of Contents

### Part 1: Factory Operators Guide
- [1.1 System Overview](#11-system-overview)
- [1.2 Daily Startup Checklist](#12-daily-startup-checklist)
- [1.3 Processing Orders](#13-processing-orders)
- [1.4 Using the Cutter Dashboard](#14-using-the-cutter-dashboard)
- [1.5 Handling Reprints](#15-handling-reprints)
- [1.6 Troubleshooting Common Issues](#16-troubleshooting-common-issues)
- [1.7 End of Day Procedures](#17-end-of-day-procedures)

### Part 2: Developer/DevOps Guide
- [2.1 System Architecture](#21-system-architecture)
- [2.2 Environment Setup](#22-environment-setup)
- [2.3 Starting Services](#23-starting-services)
- [2.4 API Reference](#24-api-reference)
- [2.5 Monitoring & Alerts](#25-monitoring--alerts)
- [2.6 Database Management](#26-database-management)
- [2.7 Scaling Workers](#27-scaling-workers)
- [2.8 Backup & Recovery](#28-backup--recovery)
- [2.9 Deployment Checklist](#29-deployment-checklist)

### Appendices
- [A. Quick Reference Cards](#appendix-a-quick-reference-cards)
- [B. Error Codes & Solutions](#appendix-b-error-codes--solutions)
- [C. Contact Information](#appendix-c-contact-information)
- [D. Glossary](#appendix-d-glossary)

---

# PART 1: FACTORY OPERATORS GUIDE

## 1.1 System Overview

### What Does This System Do?

The SameDaySuits Pattern Factory automatically:

1. **Receives** customer measurements (chest, waist, hip, etc.)
2. **Selects** the right pattern template (tee, jacket, trousers)
3. **Scales** the pattern to fit the customer
4. **Nests** all pieces to minimize fabric waste
5. **Sends** instructions to the Jindex cutter
6. **Cuts** the fabric automatically

### System Components (What You'll See)

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR WORKSTATION                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [Laptop]  ──────────────────────►  [Jindex Cutter]        │
│      │                                    │                  │
│      │ Dashboard                          │ Cuts             │
│      │ http://localhost:5000              │ Fabric           │
│      │                                    ▼                  │
│      │                              [Cut Pieces]             │
│      │                                                       │
└─────────────────────────────────────────────────────────────┘
```

### Key Terms

| Term | Meaning |
|------|---------|
| **Order** | A customer's request for a garment |
| **Order ID** | Unique code like `SDS-20260201-0001-A` |
| **PLT File** | Instructions file for the cutter |
| **Queue** | List of jobs waiting to be cut |
| **Reprint** | Cutting an order again (if damaged) |
| **Dashboard** | The web page to monitor cutting |

---

## 1.2 Daily Startup Checklist

### Before Starting Work

Complete this checklist every morning:

```
□ Step 1: Turn on the Jindex cutter
□ Step 2: Turn on the laptop
□ Step 3: Start the dashboard (see below)
□ Step 4: Check cutter connection (green light)
□ Step 5: Load fabric on cutter
□ Step 6: Verify queue status
□ Step 7: Ready to process orders
```

### Starting the Dashboard

1. **Open Command Prompt** (Press `Win + R`, type `cmd`, press Enter)

2. **Navigate to the production folder:**
   ```
   cd D:\SameDaySuits\production
   ```

3. **Start the dashboard:**
   ```
   python scripts/cutter_dashboard.py --ip 192.168.1.100
   ```

4. **Open browser** to: `http://localhost:5000`

### What You Should See

The dashboard shows:

```
┌─────────────────────────────────────────────────────────────┐
│  CUTTER DASHBOARD                    Cutter: Connected ●    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐           │
│   │   3    │  │   1    │  │  12    │  │   0    │           │
│   │In Queue│  │Cutting │  │ Today  │  │Failed  │           │
│   └────────┘  └────────┘  └────────┘  └────────┘           │
│                                                              │
│  JOB QUEUE                                                   │
│  ─────────────────────────────────────────────────────────  │
│  Order          Priority    Status      Actions              │
│  ORD-0042       RUSH       CUTTING     -                     │
│  ORD-0041       HIGH       QUEUED      [Cancel]              │
│  ORD-0040       NORMAL     QUEUED      [Cancel]              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Verifying Cutter Connection

| Status | Indicator | Meaning | Action |
|--------|-----------|---------|--------|
| Connected | Green ● | Cutter is ready | Start working |
| Offline | Red ● | No connection | Check cables |
| Busy | Yellow ● | Currently cutting | Wait |

---

## 1.3 Processing Orders

### How Orders Arrive

Orders come from:
1. **Web API** - Online orders
2. **Database** - Synced orders
3. **Body Scanner** - BlackBox scans

You don't need to enter orders manually. The system handles this automatically.

### Monitoring Order Progress

Watch the dashboard for order status:

| Status | Meaning |
|--------|---------|
| QUEUED | Waiting to be cut |
| CUTTING | Currently being cut |
| COMPLETE | Finished successfully |
| FAILED | Something went wrong |

### Priority Levels

Orders are processed in this order:

| Priority | Badge Color | When Used |
|----------|-------------|-----------|
| RUSH | Purple | Urgent orders (same-day) |
| HIGH | Orange | Priority customers |
| NORMAL | Gray | Standard orders |
| LOW | Gray | Can wait |

**RUSH orders always cut first!**

### What To Do When Cutting

1. **Watch the cutter** - Make sure it's cutting correctly
2. **Check the fabric** - Ensure no wrinkles or issues
3. **Remove cut pieces** - Carefully lift each piece
4. **Verify labels** - Each piece has the order number printed
5. **Sort by order** - Keep pieces together

### Verifying Cut Pieces

Each piece should have printed:
```
SDS-20260201-0001-A    ← Order number
FRONT_PANEL            ← Piece name
001/015                ← Piece 1 of 15
```

**If a label is missing or wrong, request a reprint!**

---

## 1.4 Using the Cutter Dashboard

### Dashboard Sections

#### 1. Status Bar (Top)
- Shows cutter connection status
- Auto-refreshes every 10 seconds

#### 2. Statistics Cards
- **In Queue**: Jobs waiting
- **Cutting**: Currently cutting
- **Today**: Completed today
- **Failed**: Jobs that failed

#### 3. Job Queue Table
- Shows all pending and cutting jobs
- Click **Cancel** to remove a queued job

#### 4. Recent Jobs
- Shows completed and failed jobs
- Click **Reprint** to cut again
- Click **Retry** to retry failed jobs

### Searching for Orders

1. Use the **search box** under "Recent Jobs"
2. Type the order ID (or part of it)
3. Results filter automatically

### Understanding Job Information

```
Job ID: JOB-ORD-20260201-0001-A-1738412345678
        └───┬───┘ └────┬────┘ └─┬─┘ └────┬────┘
            │         │        │       │
         Prefix   Order ID  Revision  Timestamp
```

---

## 1.5 Handling Reprints

### When To Reprint

Request a reprint when:
- Fabric was damaged during cutting
- Cutter made an error
- Quality issue on cut pieces
- Customer needs duplicate

### How To Reprint

1. **Find the job** in "Recent Jobs"
2. **Click the green "Reprint" button**
3. **Enter a reason** (required)
   - Example: "Fabric defect on front panel"
4. **Click "Confirm Reprint"**

The reprint job will be added to the queue.

### Reprint Priority

By default, reprints use **NORMAL** priority and mix with regular work.

### Tracking Reprints

Reprints show a special badge: `[REPRINT]`

```
Order              Status     Actions
ORD-0038 [REPRINT] QUEUED    [Cancel]
```

---

## 1.6 Troubleshooting Common Issues

### Issue: Cutter Shows "Offline" (Red Light)

**Cause:** Network or connection problem

**Solution:**
1. Check the network cable is connected
2. Verify cutter IP address: `192.168.1.100`
3. Restart the cutter
4. Restart the dashboard

### Issue: Job Stuck in "CUTTING"

**Cause:** Cutter stopped or error occurred

**Solution:**
1. Check the physical cutter
2. Look for error messages on cutter display
3. If needed, cancel the job and retry
4. Check fabric is loaded correctly

### Issue: PLT File Not Found

**Cause:** File was deleted or not generated

**Solution:**
1. Check the order processed correctly
2. Look in: `cutter_data/archive/files/`
3. If missing, the order needs reprocessing
4. Contact supervisor

### Issue: Quality Check Failed

**Cause:** Pattern did not pass validation

**Solution:**
1. Check the QC report in dashboard
2. Look for specific error message
3. Common issues:
   - Pieces overlap
   - Exceeds fabric width
   - Missing pieces

### Issue: Dashboard Won't Start

**Cause:** Flask not installed or port in use

**Solution:**
1. Install Flask: `pip install flask`
2. Check port 5000 is free
3. Try different port: `--web-port 5001`

### Issue: Wrong Order Cut

**Cause:** Pieces mixed up or wrong job selected

**Solution:**
1. Stop cutting immediately
2. Verify piece labels match order
3. Sort pieces correctly
4. Report the error

---

## 1.7 End of Day Procedures

### Shutdown Checklist

```
□ Step 1: Check queue is empty (or note remaining jobs)
□ Step 2: Stop the dashboard (Ctrl+C in command prompt)
□ Step 3: Clean the cutter
□ Step 4: Remove and store unused fabric
□ Step 5: Turn off the cutter
□ Step 6: Turn off the laptop
□ Step 7: Complete handover notes
```

### Handover Notes

If jobs remain in queue, note:
- Number of pending jobs
- Any RUSH orders for tomorrow
- Any issues encountered today

### Weekly Maintenance

Every Friday:
1. Clean cutter thoroughly
2. Check blade condition
3. Verify backup completed
4. Clear old log files if needed

---

# PART 2: DEVELOPER/DEVOPS GUIDE

## 2.1 System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Web API  │  │   CLI    │  │ Supabase │  │ BlackBox │        │
│  │  :8000   │  │          │  │ Database │  │ Scanner  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │                │
│       └─────────────┴──────┬──────┴─────────────┘                │
│                            ▼                                     │
├─────────────────────────────────────────────────────────────────┤
│                       PROCESSING LAYER                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Redis Queue  │───►│Nesting Worker│───►│  Production  │       │
│  │              │    │  (Scalable)  │    │   Pipeline   │       │
│  └──────────────┘    └──────────────┘    └──────┬───────┘       │
│                                                  │                │
│                            ┌─────────────────────┘                │
│                            ▼                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │    Files     │◄───│   Quality    │───►│   Cutter     │       │
│  │  PLT/PDS/DXF │    │   Control    │    │    Queue     │       │
│  └──────────────┘    └──────────────┘    └──────┬───────┘       │
│                                                  │                │
├─────────────────────────────────────────────────────────────────┤
│                        OUTPUT LAYER                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Dashboard   │◄───│Cutter Worker │───►│ Jindex UPC   │       │
│  │    :5000     │    │  TCP:9100    │    │   Cutter     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

| Component | Technology | Location | Purpose |
|-----------|------------|----------|---------|
| Web API | FastAPI | `src/api/web_api.py` | REST endpoints |
| Redis Queue | Redis | External | Order queue |
| Nesting Worker | Python | `src/workers/nesting_worker.py` | Process orders |
| Production Pipeline | Python | `src/core/` | Core logic |
| Cutter Queue | SQLite+WAL | `src/core/resilient_cutter_queue.py` | Job queue |
| Cutter Worker | Python | `src/workers/jindex_cutter.py` | TCP interface |
| Dashboard | Flask | `scripts/cutter_dashboard.py` | Operator UI |

### Data Flow

```
Order Input
    │
    ▼
Validate Measurements ──► Reject (if invalid)
    │
    ▼
Load PDS Template
    │
    ▼
Scale Pattern (customer measurements)
    │
    ▼
Nest Pieces (62" fabric width)
    │
    ▼
Quality Control ──► Alert (if fail)
    │
    ▼
Generate Files (PLT, PDS, DXF, JSON)
    │
    ▼
Add to Cutter Queue
    │
    ▼
Cutter Worker ──► TCP:9100 ──► Jindex Cutter
    │
    ▼
Cut Fabric
```

---

## 2.2 Environment Setup

### Prerequisites

- Python 3.10+
- Redis Server
- Git

### Installation Steps

```bash
# 1. Clone repository
cd D:\SameDaySuits
git clone <repo-url> production

# 2. Create virtual environment
cd production
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Flask for dashboard
pip install flask

# 5. Copy environment file
copy .env.example .env  # Windows
cp .env.example .env    # Linux

# 6. Edit .env with your settings
notepad .env
```

### Environment Variables

```bash
# .env file
# ==========

# Security
JWT_SECRET=your-secret-key-min-32-characters
ENCRYPTION_KEY=your-encryption-key
API_KEY=your-api-key
AUTH_ENABLED=true

# Database
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-anon-key

# Queue
REDIS_URL=redis://localhost:6379/0
ASYNC_PROCESSING=false

# Cutter
JINDEX_IP=192.168.1.100
JINDEX_PORT=9100
CUTTER_DATA_DIR=./cutter_data

# Monitoring
LOG_LEVEL=INFO
GRAFANA_ADMIN_PASSWORD=changeme
```

### Directory Structure

```
production/
├── src/
│   ├── core/               # Core modules
│   ├── nesting/            # Nesting algorithms
│   ├── api/                # Web API
│   ├── workers/            # Background workers
│   ├── blackbox/           # Body scanning
│   ├── scalability/        # Queue/cache
│   ├── security/           # Auth
│   └── observability/      # Logging/metrics
├── scripts/                # CLI tools
├── tests/                  # Test suites
├── docs/                   # Documentation
├── samples/                # Sample data
├── config/                 # Configuration
└── cutter_data/           # Queue data (created at runtime)
```

---

## 2.3 Starting Services

### Development Mode

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start API
cd production
python -m uvicorn src.api.web_api:app --reload --port 8000

# Terminal 3: Start Nesting Worker
python -m src.workers.nesting_worker

# Terminal 4: Start Cutter Worker
JINDEX_IP=192.168.1.100 python -m src.workers.jindex_cutter

# Terminal 5: Start Dashboard
python scripts/cutter_dashboard.py --ip 192.168.1.100
```

### Production Mode (Docker)

```bash
# Start all services
docker-compose up -d

# Scale workers
docker-compose up -d --scale nesting-worker=3

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Service Health Checks

```bash
# API health
curl http://localhost:8000/health

# Dashboard
curl http://localhost:5000/api/status

# Redis
redis-cli ping

# Cutter connection
python scripts/cutter_cli.py test-cutter --ip 192.168.1.100
```

---

## 2.4 API Reference

### Order Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders` | Submit new order |
| GET | `/orders/{id}` | Get order details |
| GET | `/orders/{id}/status` | Get order status |
| GET | `/orders/{id}/plt` | Download PLT file |
| GET | `/orders/{id}/pds` | Download PDS file |
| GET | `/orders/{id}/dxf` | Download DXF file |
| GET | `/orders/{id}/files` | List all files |

### Queue Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/queue/status` | Get queue statistics |
| GET | `/queue/jobs` | List all jobs |
| POST | `/queue/reprint` | Request reprint |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| WS | `/ws` | WebSocket updates |

### Example: Submit Order

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-001",
    "garment_type": "tee",
    "fit_type": "regular",
    "measurements": {
      "chest": 102,
      "waist": 88,
      "hip": 100
    },
    "priority": "normal"
  }'
```

### Response

```json
{
  "order_id": "SDS-20260201-0001-A",
  "status": "queued",
  "message": "Order submitted successfully"
}
```

---

## 2.5 Monitoring & Alerts

### Prometheus Metrics

Metrics available at: `http://localhost:8000/metrics`

| Metric | Type | Description |
|--------|------|-------------|
| `orders_total` | Counter | Total orders processed |
| `orders_processing_seconds` | Histogram | Processing time |
| `queue_depth` | Gauge | Current queue size |
| `cutter_jobs_total` | Counter | Jobs sent to cutter |
| `nesting_utilization` | Histogram | Fabric utilization |

### Grafana Dashboards

1. **Production Overview**
   - Orders per hour
   - Processing time trends
   - Error rates

2. **Queue Status**
   - Queue depth over time
   - Worker status
   - Job completion rate

3. **Cutter Status**
   - Connection status
   - Jobs cut per day
   - Reprint rate

### Alert Configuration

```yaml
# alerts.yml
groups:
  - name: production
    rules:
      - alert: QueueBacklog
        expr: queue_depth > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Queue backlog detected"
          
      - alert: CutterOffline
        expr: cutter_connected == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Cutter connection lost"
```

### Log Files

| Log | Location | Contents |
|-----|----------|----------|
| API | `logs/api.log` | API requests |
| Worker | `logs/worker.log` | Processing logs |
| Cutter | `logs/cutter.log` | Cutter operations |
| Production | Per order folder | Order-specific logs |

---

## 2.6 Database Management

### Supabase Schema

```sql
-- Orders table
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    garment_type TEXT NOT NULL,
    measurements JSONB NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- QC Reports table
CREATE TABLE qc_reports (
    id SERIAL PRIMARY KEY,
    order_id TEXT REFERENCES orders(id),
    passed BOOLEAN NOT NULL,
    checks JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cutter Jobs table
CREATE TABLE cutter_jobs (
    id TEXT PRIMARY KEY,
    order_id TEXT REFERENCES orders(id),
    status TEXT DEFAULT 'queued',
    priority INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Backup Procedures

```bash
# Daily backup (automated)
pg_dump $SUPABASE_URL > backup_$(date +%Y%m%d).sql

# Manual backup
python -c "from src.observability.backup_manager import backup_now; backup_now()"
```

### Data Retention

| Data | Retention | Action |
|------|-----------|--------|
| Orders | Forever | Archive after 90 days |
| QC Reports | 1 year | Archive then delete |
| Logs | 30 days | Rotate and compress |
| PLT Files | Forever | Keep in archive |

---

## 2.7 Scaling Workers

### Horizontal Scaling

```bash
# Scale nesting workers
docker-compose up -d --scale nesting-worker=5

# Or manually start multiple workers
WORKER_ID=worker-1 python -m src.workers.nesting_worker &
WORKER_ID=worker-2 python -m src.workers.nesting_worker &
WORKER_ID=worker-3 python -m src.workers.nesting_worker &
```

### Scaling Guidelines

| Orders/Hour | Recommended Workers |
|-------------|---------------------|
| < 10 | 1 worker |
| 10-50 | 2-3 workers |
| 50-100 | 4-5 workers |
| > 100 | 5+ workers |

### Cutter Worker Note

**Only run ONE cutter worker per physical cutter.**

The cutter can only process one job at a time.

---

## 2.8 Backup & Recovery

### Automatic Backup

Backups run daily at 2:00 AM:
- Database (Supabase)
- Cutter queue (SQLite)
- Configuration files

### Manual Backup

```bash
# Backup everything
python scripts/backup.py --full

# Backup database only
python scripts/backup.py --database

# Backup cutter queue only
python scripts/backup.py --cutter-queue
```

### Recovery Procedures

#### Scenario 1: Cutter Queue Crash

The WAL (Write-Ahead Log) automatically recovers:

```bash
# Just restart the service
python -m src.workers.jindex_cutter

# Queue will replay WAL and restore state
```

#### Scenario 2: Database Corruption

```bash
# Restore from backup
psql $SUPABASE_URL < backup_20260201.sql
```

#### Scenario 3: Complete System Failure

1. Restore database from backup
2. Restore cutter_data folder from backup
3. Start all services
4. Verify queue recovered correctly
5. Resume processing

---

## 2.9 Deployment Checklist

### Pre-Deployment

```
□ All tests passing
□ Environment variables configured
□ Database migrations applied
□ Redis running
□ Cutter network accessible
□ Backup completed
□ Team notified
```

### Deployment Steps

```bash
# 1. Pull latest code
git pull origin master

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python scripts/migrate.py

# 4. Restart services
docker-compose down
docker-compose up -d

# 5. Verify health
curl http://localhost:8000/health
```

### Post-Deployment

```
□ Health check passing
□ Dashboard accessible
□ Cutter connection green
□ Process test order
□ Monitor for 30 minutes
□ Document any issues
```

### Rollback Procedure

```bash
# If issues occur:
git checkout <previous-commit>
docker-compose down
docker-compose up -d
```

---

# APPENDICES

## Appendix A: Quick Reference Cards

### Operator Quick Start

```
1. Power on cutter
2. Start dashboard:
   python scripts/cutter_dashboard.py --ip 192.168.1.100
3. Open browser: http://localhost:5000
4. Verify green connection light
5. Start processing orders
```

### CLI Commands

```bash
# Queue status
python scripts/cutter_cli.py status

# List jobs
python scripts/cutter_cli.py list

# Reprint job
python scripts/cutter_cli.py reprint-job --job-id JOB-xxx

# Search orders
python scripts/cutter_cli.py search --order-id ORD-001

# Test cutter
python scripts/cutter_cli.py test-cutter --ip 192.168.1.100
```

### Important URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5000 |
| API | http://localhost:8000 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

---

## Appendix B: Error Codes & Solutions

| Error | Meaning | Solution |
|-------|---------|----------|
| `E001` | Invalid measurements | Check values are in valid range |
| `E002` | Template not found | Verify garment type is correct |
| `E003` | Nesting failed | Check piece dimensions |
| `E004` | QC validation failed | Review QC report details |
| `E005` | Cutter connection lost | Check network and cables |
| `E006` | Job timeout | Retry or check cutter |
| `E007` | File not found | Reprocess the order |
| `E008` | Max retries exceeded | Manual intervention needed |

---

## Appendix C: Contact Information

### Support Contacts

| Role | Name | Contact |
|------|------|---------|
| System Admin | TBD | admin@samedaysuits.com |
| Supervisor | TBD | supervisor@samedaysuits.com |
| Technical Lead | TBD | tech@samedaysuits.com |

### Escalation Path

1. **Level 1**: Operator (self-troubleshoot)
2. **Level 2**: Supervisor (dashboard issues)
3. **Level 3**: Technical Lead (system issues)
4. **Level 4**: External Support (hardware issues)

---

## Appendix D: Glossary

| Term | Definition |
|------|------------|
| **API** | Application Programming Interface - how systems communicate |
| **DXF** | Drawing Exchange Format - CAD file format |
| **HPGL** | Hewlett-Packard Graphics Language - cutter commands |
| **Nesting** | Arranging pattern pieces to minimize fabric waste |
| **PDS** | Optitex Pattern Design File format |
| **PLT** | Plot file containing HPGL commands for cutter |
| **Queue** | List of jobs waiting to be processed |
| **Redis** | In-memory database used for job queue |
| **Reprint** | Cutting an order again |
| **SDS** | SameDaySuits (company prefix) |
| **TCP** | Transmission Control Protocol - network communication |
| **Utilization** | Percentage of fabric used (vs. waste) |
| **WAL** | Write-Ahead Log - crash recovery mechanism |

---

**End of Document**

*For questions about this SOP, contact the Technical Lead.*

*Last updated: 2026-02-01*
