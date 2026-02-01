# SameDaySuits Pattern Factory - System Architecture

**Version:** 1.0  
**Date:** 2026-02-01  
**Status:** Production  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Order Processing Flow](#2-order-processing-flow)
3. [Nesting Algorithm Selection](#3-nesting-algorithm-selection)
4. [Cutter Queue Flow](#4-cutter-queue-flow)
5. [Recovery & Resilience](#5-recovery--resilience)
6. [File Output Structure](#6-file-output-structure)
7. [API Request Flow](#7-api-request-flow)
8. [Deployment Architecture](#8-deployment-architecture)
9. [BlackBox Scanning Pipeline](#9-blackbox-scanning-pipeline)
10. [Component Reference](#10-component-reference)

---

## 1. System Overview

The SameDaySuits Pattern Factory is an automated garment manufacturing system that transforms customer measurements into cutter-ready PLT files for a Jindex UPC inkjet cutter.

### High-Level Architecture

```mermaid
flowchart TB
    subgraph Inputs["INPUT SOURCES"]
        API["Web API<br/>POST /orders<br/>:8000"]
        CLI["CLI Tool<br/>sds command"]
        DB[("Supabase<br/>Database")]
        BB["BlackBox<br/>Body Scanner"]
    end
    
    subgraph Processing["PROCESSING LAYER"]
        RQ[("Redis Queue<br/>Order Queue")]
        NW["Nesting Workers<br/>(Scalable)"]
        PP["Production Pipeline<br/>v6.4.3"]
        QC["Quality Control<br/>7 Checks"]
    end
    
    subgraph Output["OUTPUT LAYER"]
        FS[("File System<br/>PLT/PDS/DXF")]
        CQ["Cutter Queue<br/>WAL + SQLite"]
        DASH["Operator Dashboard<br/>:5000"]
    end
    
    subgraph Cutter["PHYSICAL LAYER"]
        JC["Jindex UPC<br/>Inkjet Cutter<br/>TCP:9100"]
        FAB["Cut Fabric<br/>62 inch width"]
    end
    
    API --> RQ
    CLI --> PP
    DB -.->|Polling| RQ
    BB --> RQ
    
    RQ --> NW
    NW --> PP
    PP --> QC
    QC --> FS
    QC --> CQ
    
    CQ --> DASH
    CQ --> JC
    JC --> FAB
    
    style Inputs fill:#e1f5fe
    style Processing fill:#fff3e0
    style Output fill:#e8f5e9
    style Cutter fill:#fce4ec
```

### Component Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web API | FastAPI | REST endpoints for order submission |
| CLI | Python argparse | Command-line order processing |
| Redis Queue | Redis | Async order queue with priority |
| Nesting Workers | Python multiprocessing | Scalable order processors |
| Production Pipeline | Python | PDS → PLT conversion |
| Quality Control | Python | Automated validation (7 checks) |
| Cutter Queue | SQLite + WAL | Crash-safe job queue |
| Operator Dashboard | Flask | Web UI for cutter operators |
| Jindex Cutter | TCP Socket | Physical fabric cutter |

---

## 2. Order Processing Flow

Complete flow from order input to cut fabric.

### Processing Pipeline

```mermaid
flowchart LR
    A["Order<br/>Input"] --> B{"Validate<br/>Measurements"}
    B -->|Valid| C["Load PDS<br/>Template"]
    B -->|Invalid| X["Reject<br/>Order"]
    C --> D["Extract<br/>Geometry"]
    D --> E["Scale<br/>Pattern"]
    E --> F["Nest<br/>Pieces"]
    F --> G{"QC<br/>Check"}
    G -->|Pass| H["Generate<br/>Files"]
    G -->|Fail| I["Alert<br/>Operator"]
    H --> J["Queue for<br/>Cutter"]
    J --> K["Cut<br/>Fabric"]
    K --> L["Complete"]
    
    style A fill:#bbdefb
    style L fill:#c8e6c9
    style X fill:#ffcdd2
    style I fill:#fff9c4
```

### Processing Stages Detail

```mermaid
flowchart TB
    subgraph Stage1["1. VALIDATION"]
        V1["Check order ID format<br/>SDS-YYYYMMDD-NNNN-R"]
        V2["Validate measurements<br/>chest, waist, hip"]
        V3["Check garment type<br/>tee, jacket, trousers"]
        V1 --> V2 --> V3
    end
    
    subgraph Stage2["2. TEMPLATE LOADING"]
        T1["Select PDS template<br/>by garment type"]
        T2["Extract embedded XML"]
        T3["Parse SVG geometry"]
        T4["Get piece dimensions"]
        T1 --> T2 --> T3 --> T4
    end
    
    subgraph Stage3["3. PATTERN SCALING"]
        S1["Calculate scale factors<br/>from measurements"]
        S2["Apply to each piece"]
        S3["Preserve proportions"]
        S4["Verify tolerance ±2mm"]
        S1 --> S2 --> S3 --> S4
    end
    
    subgraph Stage4["4. NESTING"]
        N1["Run all algorithms"]
        N2["Compare utilization"]
        N3["Select best result"]
        N4["Verify 62 inch width"]
        N1 --> N2 --> N3 --> N4
    end
    
    subgraph Stage5["5. OUTPUT"]
        O1["Generate PLT<br/>with labels"]
        O2["Generate PDS<br/>Optitex format"]
        O3["Generate DXF<br/>CAD format"]
        O4["Write metadata<br/>JSON files"]
        O1 --> O2 --> O3 --> O4
    end
    
    Stage1 --> Stage2 --> Stage3 --> Stage4 --> Stage5
```

### Order Status States

```mermaid
stateDiagram-v2
    [*] --> submitted: Order received
    submitted --> validating: Start processing
    validating --> rejected: Invalid data
    validating --> selecting_template: Valid
    selecting_template --> scaling: Template loaded
    scaling --> nesting: Scaled
    nesting --> qc_check: Nested
    qc_check --> queued: QC passed
    qc_check --> failed: QC failed
    queued --> cutting: Cutter ready
    cutting --> completed: Success
    cutting --> failed: Cutter error
    completed --> [*]
    failed --> [*]
    rejected --> [*]
```

---

## 3. Nesting Algorithm Selection

The `master_nest()` function runs all algorithms and selects the best result.

### Algorithm Competition

```mermaid
flowchart TB
    START["Scaled Pieces<br/>Input"] --> MASTER["master_nest()<br/>Best-of-All Selector"]
    
    MASTER --> ALG1["Bottom-Left Fill<br/>nesting_engine.py"]
    MASTER --> ALG2["Guillotine Split<br/>improved_nesting.py"]
    MASTER --> ALG3["Skyline Tracking<br/>improved_nesting.py"]
    MASTER --> ALG4["Hybrid Polygon<br/>hybrid_nesting.py"]
    MASTER --> ALG5["Turbo Shapely<br/>turbo_nesting.py"]
    
    ALG1 --> R1["Result 1<br/>~72% util"]
    ALG2 --> R2["Result 2<br/>~78% util"]
    ALG3 --> R3["Result 3<br/>~80% util"]
    ALG4 --> R4["Result 4<br/>~78% util"]
    ALG5 --> R5["Result 5<br/>~76% util"]
    
    R1 --> COMPARE["Compare<br/>Utilization"]
    R2 --> COMPARE
    R3 --> COMPARE
    R4 --> COMPARE
    R5 --> COMPARE
    
    COMPARE --> BEST{"Select<br/>Highest"}
    BEST --> OUTPUT["Best Nested Layout<br/>78-88% utilization"]
    
    style MASTER fill:#fff3e0
    style OUTPUT fill:#c8e6c9
```

### Algorithm Characteristics

| Algorithm | Technique | Best For | Typical Utilization |
|-----------|-----------|----------|---------------------|
| Bottom-Left Fill | Shelf packing | Simple shapes | 70-75% |
| Guillotine | Rectangle splitting | Rectangular pieces | 75-80% |
| Skyline | Height tracking | Varied heights | 78-85% |
| Hybrid | Polygon collision | Complex shapes | 76-82% |
| Turbo | Shapely spatial index | Large batches | 74-80% |

### Nesting Constraints

```mermaid
flowchart LR
    subgraph Constraints["CONSTRAINTS"]
        C1["Fabric Width<br/>62 inches<br/>(157.48 cm)"]
        C2["No Overlap<br/>Collision detection"]
        C3["Rotation<br/>0°, 90°, 180°, 270°"]
        C4["Margin<br/>5mm between pieces"]
    end
    
    subgraph Goals["GOALS"]
        G1["Maximize<br/>Utilization"]
        G2["Minimize<br/>Fabric Length"]
        G3["Optimize<br/>Cut Path"]
    end
    
    Constraints --> Goals
```

---

## 4. Cutter Queue Flow

Resilient queue with crash recovery via Write-Ahead Log (WAL).

### Queue Architecture

```mermaid
flowchart LR
    subgraph Input["JOB INPUT"]
        ADD["add_job()"]
    end
    
    subgraph Queue["RESILIENT CUTTER QUEUE"]
        WAL[("WAL File<br/>cutter_queue.wal")]
        MEM["In-Memory<br/>Priority Queue"]
        ARCH[("SQLite Archive<br/>job_archive.db")]
        FILES[("PLT Files<br/>archive/files/")]
    end
    
    subgraph Worker["CUTTER WORKER"]
        GET["get_next_job()"]
        TCP["TCP Send<br/>:9100"]
        MARK["mark_complete()<br/>mark_failed()"]
    end
    
    ADD --> WAL
    WAL --> MEM
    ADD --> ARCH
    ADD --> FILES
    
    MEM --> GET
    GET --> TCP
    TCP --> MARK
    MARK --> ARCH
    
    style WAL fill:#ffecb3
    style ARCH fill:#e1f5fe
```

### Priority Ordering

```mermaid
flowchart TB
    subgraph Priority["PRIORITY LEVELS"]
        P1["RUSH<br/>Priority 1"]
        P2["HIGH<br/>Priority 2"]
        P3["NORMAL<br/>Priority 3"]
        P4["LOW<br/>Priority 4"]
        P5["REPRINT<br/>Priority 3*"]
    end
    
    subgraph Queue["QUEUE ORDER"]
        Q1["First: RUSH jobs"]
        Q2["Then: HIGH jobs"]
        Q3["Then: NORMAL + REPRINT"]
        Q4["Last: LOW jobs"]
    end
    
    P1 --> Q1
    P2 --> Q2
    P3 --> Q3
    P5 --> Q3
    P4 --> Q4
    
    note["*Reprints use NORMAL<br/>priority by default"]
```

### Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING: Job created
    PENDING --> QUEUED: Added to queue
    QUEUED --> CUTTING: Worker picks up
    CUTTING --> COMPLETE: Success
    CUTTING --> ERROR: Failed
    ERROR --> QUEUED: Retry (max 3)
    ERROR --> [*]: Max retries exceeded
    COMPLETE --> [*]: Archived
    
    QUEUED --> CANCELLED: Operator cancel
    CANCELLED --> [*]: Removed
```

---

## 5. Recovery & Resilience

System recovers automatically from crashes using WAL replay.

### Crash Recovery Flow

```mermaid
flowchart TB
    CRASH["System Crash<br/>Power failure"] --> RESTART["System Restart"]
    RESTART --> INIT["Initialize Queue"]
    INIT --> REPLAY["Replay WAL<br/>cutter_queue.wal"]
    
    REPLAY --> CHECK{"For each entry"}
    CHECK --> JC["JOB_CREATED<br/>Restore job"]
    CHECK --> JQ["JOB_QUEUED<br/>Add to queue"]
    CHECK --> JS["JOB_STARTED<br/>Re-queue + retry++"]
    CHECK --> JCOMP["JOB_COMPLETED<br/>Skip (done)"]
    CHECK --> JF["JOB_FAILED<br/>Mark failed"]
    
    JC --> MERGE["Merge State"]
    JQ --> MERGE
    JS --> MERGE
    JCOMP --> MERGE
    JF --> MERGE
    
    MERGE --> READY["Queue Ready<br/>Resume processing"]
    
    style CRASH fill:#ffcdd2
    style READY fill:#c8e6c9
```

### Retry Logic

```mermaid
flowchart LR
    FAIL["Job Failed"] --> CHECK{"retry_count<br/>< max_retries?"}
    CHECK -->|Yes| INCR["retry_count++"]
    INCR --> BACKOFF["Exponential<br/>Backoff"]
    BACKOFF --> REQUEUE["Re-queue"]
    REQUEUE --> PROCESS["Process Again"]
    
    CHECK -->|No| DLQ["Dead Letter<br/>Mark ERROR"]
    DLQ --> ALERT["Alert<br/>Operator"]
    
    style FAIL fill:#ffcdd2
    style ALERT fill:#fff9c4
```

### Circuit Breaker Pattern

```mermaid
flowchart LR
    subgraph States["CIRCUIT STATES"]
        CLOSED["CLOSED<br/>Normal operation"]
        OPEN["OPEN<br/>Failing fast"]
        HALF["HALF-OPEN<br/>Testing"]
    end
    
    CLOSED -->|"failures > threshold"| OPEN
    OPEN -->|"timeout elapsed"| HALF
    HALF -->|"success"| CLOSED
    HALF -->|"failure"| OPEN
    
    style CLOSED fill:#c8e6c9
    style OPEN fill:#ffcdd2
    style HALF fill:#fff9c4
```

---

## 6. File Output Structure

Every order generates a complete set of files in a standardized folder structure.

### Folder Hierarchy

```mermaid
flowchart TB
    ROOT["orders/"] --> ORDER["SDS-20260201-0001-A/"]
    
    ORDER --> PLT["SDS-20260201-0001-A.plt<br/>Cutter file"]
    ORDER --> PDS["SDS-20260201-0001-A.pds<br/>Optitex pattern"]
    ORDER --> DXF["SDS-20260201-0001-A.dxf<br/>CAD format"]
    ORDER --> META["SDS-20260201-0001-A_metadata.json"]
    ORDER --> QCR["SDS-20260201-0001-A_qc_report.json"]
    ORDER --> LOG["SDS-20260201-0001-A_production.log"]
    ORDER --> NEST["SDS-20260201-0001-A_nesting.json"]
    
    ORDER --> PIECES["pieces/"]
    ORDER --> PREV["previews/"]
    ORDER --> HIST["history/"]
    
    PIECES --> P1["..._piece_01_front.pds"]
    PIECES --> P2["..._piece_02_back.pds"]
    
    PREV --> PR1["nesting_layout.png"]
    PREV --> PR2["piece_details.pdf"]
    
    HIST --> H1["rev_A/"]
    HIST --> H2["rev_B/"]
    
    style PLT fill:#bbdefb
    style PDS fill:#c8e6c9
    style DXF fill:#fff9c4
```

### File Types

| File | Format | Purpose | Required |
|------|--------|---------|----------|
| `.plt` | HPGL | Cutter instructions with labels | YES |
| `.pds` | Optitex PDS | Editable pattern file | YES |
| `.dxf` | AutoCAD DXF | CAD exchange format | YES |
| `_metadata.json` | JSON | Order parameters | YES |
| `_qc_report.json` | JSON | Quality validation | YES |
| `_production.log` | Text | Processing timeline | YES |
| `_nesting.json` | JSON | Nesting statistics | YES |

### Order ID Format

```
SDS-YYYYMMDD-NNNN-R

SDS        = SameDaySuits prefix (constant)
YYYYMMDD   = Order date (e.g., 20260201)
NNNN       = Sequential number (0001-9999)
R          = Revision letter (A, B, C...)

Example: SDS-20260201-0042-A
         SDS-20260201-0042-B (revision)
```

---

## 7. API Request Flow

Sequence diagram showing API interaction.

### Async Order Processing

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Web API
    participant V as Validator
    participant Q as Redis Queue
    participant W as Nesting Worker
    participant F as File System
    participant CQ as Cutter Queue
    participant D as Dashboard
    
    C->>A: POST /orders {measurements}
    A->>V: Validate order
    V-->>A: Valid
    A->>Q: Enqueue (priority)
    A-->>C: 202 {order_id, status: queued}
    
    Note over Q,W: Async Processing
    
    Q->>W: Dequeue order
    W->>W: Load template
    W->>W: Scale pattern
    W->>W: Nest pieces
    W->>W: QC validation
    W->>F: Write PLT/PDS/DXF
    W->>CQ: Add cutter job
    W->>Q: Mark complete
    
    Note over C,A: Status Check
    
    C->>A: GET /orders/{id}/status
    A-->>C: 200 {status: complete, files: [...]}
    
    C->>A: GET /orders/{id}/plt
    A->>F: Read file
    A-->>C: 200 [PLT binary]
    
    Note over CQ,D: Operator View
    
    D->>CQ: Get queue status
    CQ-->>D: {depth: 5, cutting: 1}
```

### API Endpoints Summary

```mermaid
flowchart LR
    subgraph Orders["ORDER ENDPOINTS"]
        O1["POST /orders<br/>Submit order"]
        O2["GET /orders/{id}<br/>Get details"]
        O3["GET /orders/{id}/status<br/>Get status"]
        O4["GET /orders/{id}/plt<br/>Download PLT"]
        O5["GET /orders/{id}/pds<br/>Download PDS"]
        O6["GET /orders/{id}/dxf<br/>Download DXF"]
    end
    
    subgraph Queue["QUEUE ENDPOINTS"]
        Q1["GET /queue/status<br/>Queue stats"]
        Q2["GET /queue/jobs<br/>List jobs"]
        Q3["POST /queue/reprint<br/>Reprint job"]
    end
    
    subgraph System["SYSTEM ENDPOINTS"]
        S1["GET /health<br/>Health check"]
        S2["GET /metrics<br/>Prometheus"]
        S3["WS /ws<br/>WebSocket"]
    end
```

---

## 8. Deployment Architecture

Production deployment with Docker.

### Container Architecture

```mermaid
flowchart TB
    subgraph External["EXTERNAL"]
        USERS["Users /<br/>Operators"]
        CUTTER["Jindex Cutter<br/>192.168.1.100:9100"]
    end
    
    subgraph LoadBalancer["LOAD BALANCER"]
        NGINX["Nginx<br/>:443 HTTPS<br/>:80 HTTP"]
    end
    
    subgraph Application["APPLICATION CONTAINERS"]
        API1["api-1<br/>FastAPI"]
        API2["api-2<br/>FastAPI"]
        W1["worker-1<br/>Nesting"]
        W2["worker-2<br/>Nesting"]
        W3["worker-3<br/>Nesting"]
        CW["cutter-worker<br/>TCP sender"]
        DASH["dashboard<br/>Flask :5000"]
    end
    
    subgraph Data["DATA LAYER"]
        REDIS[("Redis<br/>:6379")]
        SUPA[("Supabase<br/>PostgreSQL")]
        VOL[("Volume<br/>/data/orders")]
        SQLITE[("SQLite<br/>cutter_queue")]
    end
    
    subgraph Monitoring["MONITORING"]
        PROM["Prometheus<br/>:9090"]
        GRAF["Grafana<br/>:3000"]
    end
    
    USERS --> NGINX
    NGINX --> API1
    NGINX --> API2
    NGINX --> DASH
    
    API1 --> REDIS
    API2 --> REDIS
    W1 --> REDIS
    W2 --> REDIS
    W3 --> REDIS
    
    W1 --> VOL
    W2 --> VOL
    W3 --> VOL
    
    CW --> SQLITE
    CW --> CUTTER
    
    API1 --> SUPA
    
    API1 -.-> PROM
    W1 -.-> PROM
    PROM --> GRAF
    
    style NGINX fill:#fff3e0
    style REDIS fill:#ffcdd2
    style SUPA fill:#e1f5fe
```

### Docker Compose Services

```yaml
# docker-compose.yml structure
services:
  nginx:        # Load balancer, SSL termination
  api:          # FastAPI (scale: 2)
  worker:       # Nesting workers (scale: 3)
  cutter:       # Cutter worker (scale: 1)
  dashboard:    # Operator UI
  redis:        # Queue backend
  prometheus:   # Metrics collection
  grafana:      # Dashboards
```

### Scaling Strategy

```mermaid
flowchart LR
    subgraph Scale["HORIZONTAL SCALING"]
        S1["API Instances<br/>Scale for traffic"]
        S2["Nesting Workers<br/>Scale for throughput"]
        S3["Cutter Worker<br/>Single instance*"]
    end
    
    S1 --> N1["2-4 instances<br/>Behind load balancer"]
    S2 --> N2["3-10 instances<br/>Parallel processing"]
    S3 --> N3["1 instance<br/>*One cutter"]
    
    note["*Only one cutter worker<br/>per physical cutter"]
```

---

## 9. BlackBox Scanning Pipeline

Body scanning to pattern generation flow.

### Scan to Pattern Flow

```mermaid
flowchart TB
    subgraph Capture["1. IMAGE CAPTURE"]
        CAM["Camera<br/>Capture"]
        IMG["Body Image<br/>+ ArUco Markers"]
    end
    
    subgraph Calibration["2. CALIBRATION"]
        ARUCO["ArUco Detection<br/>aruco_calibration.py"]
        SCALE["Calculate Scale<br/>pixels → cm"]
    end
    
    subgraph Pose["3. POSE EXTRACTION"]
        MP["MediaPipe<br/>pose_extraction.py"]
        LAND["33 Landmarks<br/>Body points"]
    end
    
    subgraph Measure["4. MEASUREMENTS"]
        CALC["Calculate<br/>Dimensions"]
        MEAS["Measurements<br/>chest, waist, hip..."]
    end
    
    subgraph Pattern["5. PATTERN GENERATION"]
        MULLER["M. Muller System<br/>muller_translator.py"]
        DXF["DXF Generator<br/>dxf_generator.py"]
    end
    
    subgraph Output["6. PRODUCTION"]
        QUEUE["Order Queue"]
        PROD["Production<br/>Pipeline"]
    end
    
    CAM --> IMG
    IMG --> ARUCO
    ARUCO --> SCALE
    IMG --> MP
    SCALE --> MP
    MP --> LAND
    LAND --> CALC
    CALC --> MEAS
    MEAS --> MULLER
    MULLER --> DXF
    DXF --> QUEUE
    QUEUE --> PROD
    
    style Capture fill:#e1f5fe
    style Pattern fill:#c8e6c9
```

### BlackBox Components

| Component | File | Purpose |
|-----------|------|---------|
| ArUco Calibration | `aruco_calibration.py` | Scale detection from markers |
| Pose Extraction | `pose_extraction.py` | MediaPipe landmark detection |
| Muller Translator | `muller_translator.py` | M. Muller pattern system |
| DXF Generator | `dxf_generator.py` | Pattern file generation |
| BlackBox Bridge | `blackbox_bridge.py` | Integration with order queue |

---

## 10. Component Reference

### Directory Structure

```
production/
├── src/
│   ├── core/                    # Core pipeline modules
│   │   ├── samedaysuits_api.py  # Main API
│   │   ├── production_pipeline.py
│   │   ├── resilient_cutter_queue.py
│   │   ├── quality_control.py
│   │   └── ...
│   ├── nesting/                 # Nesting algorithms
│   │   ├── master_nesting.py    # Best-of-all selector
│   │   ├── improved_nesting.py  # Guillotine, skyline
│   │   ├── hybrid_nesting.py    # Polygon collision
│   │   └── turbo_nesting.py     # Shapely-based
│   ├── api/                     # Web API
│   │   └── web_api.py           # FastAPI endpoints
│   ├── workers/                 # Background workers
│   │   ├── nesting_worker.py    # Order processor
│   │   └── jindex_cutter.py     # Cutter interface
│   ├── blackbox/                # Body scanning
│   │   ├── pipeline.py
│   │   └── scanning/
│   ├── scalability/             # Queue & cache
│   ├── security/                # Auth & encryption
│   └── observability/           # Logging & metrics
├── scripts/                     # CLI tools
│   ├── cutter_cli.py
│   └── cutter_dashboard.py
├── tests/                       # Test suites
├── docs/                        # Documentation
├── samples/                     # Sample data
└── config/                      # Configuration
```

### Key Configuration

```bash
# Environment Variables
JWT_SECRET=your-secret-key
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-anon-key
JINDEX_IP=192.168.1.100
JINDEX_PORT=9100
CUTTER_DATA_DIR=./cutter_data
ASYNC_PROCESSING=false
```

### Port Reference

| Service | Port | Protocol |
|---------|------|----------|
| Web API | 8000 | HTTP |
| Dashboard | 5000 | HTTP |
| Redis | 6379 | TCP |
| Supabase | 54321 | HTTP |
| Jindex Cutter | 9100 | TCP |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |
| Nginx HTTPS | 443 | HTTPS |

---

## Appendix: Quick Reference Diagrams

### A. Complete Data Flow (Simplified)

```mermaid
flowchart LR
    ORDER["Order"] --> VALIDATE["Validate"]
    VALIDATE --> TEMPLATE["Load Template"]
    TEMPLATE --> SCALE["Scale"]
    SCALE --> NEST["Nest"]
    NEST --> QC["QC"]
    QC --> FILES["Generate Files"]
    FILES --> QUEUE["Cutter Queue"]
    QUEUE --> CUT["Cut Fabric"]
```

### B. Error Handling Flow

```mermaid
flowchart TB
    ERROR["Error Occurs"] --> TYPE{"Error Type"}
    
    TYPE -->|Validation| REJECT["Reject Order<br/>Return 400"]
    TYPE -->|Processing| RETRY["Retry with<br/>Backoff"]
    TYPE -->|Cutter| REQUEUE["Re-queue<br/>Job"]
    TYPE -->|System| ALERT["Alert<br/>Operator"]
    
    RETRY --> MAX{"Max<br/>Retries?"}
    MAX -->|No| PROCESS["Retry"]
    MAX -->|Yes| DLQ["Dead Letter<br/>Queue"]
    
    REQUEUE --> MAX
```

### C. Monitoring Flow

```mermaid
flowchart LR
    subgraph Apps["APPLICATIONS"]
        A1["API"]
        A2["Workers"]
        A3["Cutter"]
    end
    
    subgraph Metrics["METRICS"]
        PROM["Prometheus<br/>Scrape"]
        STORE[("Time Series<br/>Storage")]
    end
    
    subgraph Viz["VISUALIZATION"]
        GRAF["Grafana<br/>Dashboards"]
        ALERT["Alert<br/>Manager"]
    end
    
    A1 --> PROM
    A2 --> PROM
    A3 --> PROM
    PROM --> STORE
    STORE --> GRAF
    STORE --> ALERT
```

---

**Document End**

*Generated: 2026-02-01*  
*System Version: 6.4.3*  
*Architecture Version: 1.0*
