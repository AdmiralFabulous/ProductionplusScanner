# Complete Module Reference

## Table of Contents
1. [Core Modules](#core-modules)
2. [Nesting Algorithms](#nesting-algorithms)
3. [API & Web](#api--web)
4. [Integrations](#integrations)

---

## Core Modules

### 1. samedaysuits_api.py
**Main production API - orchestrates the entire pipeline**

#### Classes

**SameDaySuitsAPI**
```python
class SameDaySuitsAPI:
    """Main API for the Pattern Factory"""
    
    def __init__(self, input_dir: str, output_dir: str, cutter_width_cm: float = 157.48)
    def process_order(order: Order) -> ProductionResult
    def batch_process(orders: List[Order]) -> List[ProductionResult]
    def list_available_templates() -> Dict[str, bool]
    def get_template_path(garment_type: GarmentType) -> Path
```

**Order (Dataclass)**
```python
@dataclass
class Order:
    order_id: str
    customer_id: str
    garment_type: GarmentType
    fit_type: FitType
    measurements: CustomerMeasurements
    quantity: int = 1
    notes: Optional[str] = None
```

**ProductionResult (Dataclass)**
```python
@dataclass
class ProductionResult:
    success: bool
    order_id: str
    plt_file: Optional[Path]
    metadata_file: Optional[Path]
    fabric_length_cm: float
    utilization_percent: float
    processing_time_seconds: float
    errors: List[str]
```

#### Enums

**GarmentType**
- TEE = "tee"
- JACKET = "jacket"
- TROUSERS = "trousers"
- CARGO = "cargo"

**FitType**
- SLIM = "slim"
- REGULAR = "regular"
- CLASSIC = "classic"

#### Usage Example
```python
from samedaysuits_api import SameDaySuitsAPI, Order, GarmentType, FitType, CustomerMeasurements

api = SameDaySuitsAPI("inputs/pds", "out/orders")

order = Order(
    order_id="SDS-20260131-0001-A",
    customer_id="CUST-001",
    garment_type=GarmentType.JACKET,
    fit_type=FitType.REGULAR,
    measurements=CustomerMeasurements(
        chest_cm=102,
        waist_cm=88,
        hip_cm=100
    )
)

result = api.process_order(order)
if result.success:
    print(f"PLT file: {result.plt_file}")
    print(f"Utilization: {result.utilization_percent}%")
```

---

### 2. production_pipeline.py
**End-to-end pipeline: PDS → HPGL/PLT**

#### Functions

**extract_xml_from_pds(pds_path: str) -> str**
- Extracts XML content from PDS file
- Returns: XML string

**extract_svg_geometry(svg_path: str) -> List[Contour]**
- Extracts geometry from SVG
- Returns: List of contours

**nest_contours(contours: List[Contour], fabric_width: float, gap: float) -> NestingResult**
- Nests contours onto fabric
- Returns: NestingResult with positions

**generate_hpgl(nested_contours: List[Contour], output_path: str)**
- Generates HPGL/PLT file
- Output: PLT file ready for cutter

#### Pipeline Flow
```
PDS File → Extract XML → Parse Geometry → Scale → Nest → Generate PLT
```

---

### 3. quality_control.py
**Automated quality control validation**

#### Classes

**QualityControl**
```python
class QualityControl:
    """Validates orders before production"""
    
    def __init__(self)
    def validate_order(order: dict) -> QCReport
    def validate_plt(plt_path: str) -> ValidationResult
    def validate_nesting(nesting_result: dict) -> ValidationResult
```

**QCReport (Dataclass)**
```python
@dataclass
class QCReport:
    order_id: str
    status: str  # PASSED, FAILED, WARNING
    checks: dict
    overall_score: str  # High, Medium, Low
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
```

#### Validation Checks
1. **Piece Count**: Correct number of pieces for garment type
2. **Geometry**: Valid polygons, no self-intersection
3. **Fit**: Measurements within tolerance
4. **Utilization**: Fabric usage above threshold
5. **Small Pieces**: Flag narrow pieces

#### Usage Example
```python
from quality_control import QualityControl

qc = QualityControl()
report = qc.validate_order(order_data)

if report.status == "PASSED":
    print("Order passed QC")
else:
    print(f"Issues: {report.errors}")
```

---

### 4. production_monitor.py
**Real-time monitoring and alerting**

#### Classes

**ProductionMonitor**
```python
class ProductionMonitor:
    """Tracks production metrics and alerts"""
    
    def __init__(self, data_dir: str = "production_data")
    def record_order_processed(success: bool, fabric_cm: float)
    def get_current_metrics() -> dict
    def get_dashboard_data() -> dict
    def check_alerts() -> List[Alert]
    def get_historical_data(days: int) -> dict
```

**Alert (Dataclass)**
```python
@dataclass
class Alert:
    id: str
    severity: str  # critical, error, warning, info
    type: str
    message: str
    timestamp: datetime
    acknowledged: bool
```

#### Alert Thresholds
- Low utilization: < 60%
- High failure rate: > 5%
- Queue backup: > 10 pending
- Slow processing: > 120s

#### Usage Example
```python
from production_monitor import ProductionMonitor, get_monitor

monitor = ProductionMonitor()
monitor.record_order_processed(success=True, fabric_cm=120.5)

metrics = monitor.get_current_metrics()
print(f"Total orders: {metrics['orders']['total']}")

alerts = monitor.check_alerts()
for alert in alerts:
    print(f"ALERT: {alert.message}")
```

---

### 5. cutter_queue.py
**Cutter job queue management**

#### Classes

**CutterQueue**
```python
class CutterQueue:
    """Manages jobs for physical cutter"""
    
    def __init__(self, spool_dir: str)
    def submit_job(order_id: str, plt_file: str, priority: JobPriority, 
                   garment_type: str) -> str
    def get_next_job() -> Optional[CutterJob]
    def update_job_status(job_id: str, status: JobStatus)
    def list_jobs(status: Optional[JobStatus] = None) -> List[CutterJob]
    def get_status() -> QueueStatus
    def cancel_job(job_id: str)
```

**CutterJob (Dataclass)**
```python
@dataclass
class CutterJob:
    job_id: str
    order_id: str
    priority: JobPriority
    status: JobStatus
    plt_file: str
    created_at: datetime
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

#### Enums

**JobPriority**
- URGENT = 1
- HIGH = 2
- NORMAL = 3
- LOW = 4

**JobStatus**
- PENDING
- QUEUED
- PROCESSING
- COMPLETED
- FAILED
- CANCELLED
- PAUSED

---

### 6. pattern_scaler.py
**Pattern scaling to customer measurements**

#### Classes

**PatternScaler**
```python
class PatternScaler:
    """Scales patterns to fit customer measurements"""
    
    def __init__(self, size_chart: Optional[SizeChart] = None)
    def select_base_size(measurements: dict) -> str
    def calculate_scales(measurements: dict, base_size: str) -> dict
    def scale_contours(contours: List[Contour], scale_x: float, scale_y: float) -> List[Contour]
```

#### Size Chart
```
XS: < 86 cm chest
S: 86-94 cm
M: 94-102 cm
L: 102-110 cm
XL: 110-118 cm
2XL: 118-126 cm
3XL: 126-134 cm
4XL: > 134 cm
```

#### Usage Example
```python
from pattern_scaler import PatternScaler

scaler = PatternScaler()
size = scaler.select_base_size({"chest": 102, "waist": 88})
scales = scaler.calculate_scales({"chest": 102}, base_size="L")

print(f"Base size: {size}")
print(f"Scale X: {scales['scale_x']}, Y: {scales['scale_y']}")
```

---

### 7. order_file_manager.py (v6.4.3)
**Order file management and output generation**

#### Classes

**OrderFileManager**
```python
class OrderFileManager:
    """Manages order folders and files"""
    
    def __init__(self, base_dir: str = "DS-speciale/out/orders")
    def generate_order_id(customer_id: Optional[str] = None) -> str
    def create_order_folder(order_id: str, customer_id: Optional[str], 
                           create_subdirs: bool = True) -> Path
    def save_plt(order_id: str, plt_content: str) -> Path
    def save_pds(order_id: str, pds_content: bytes) -> Path
    def save_dxf(order_id: str, dxf_content: str) -> Path
    def save_metadata(order_id: str, metadata: dict) -> Path
    def get_all_files(order_id: str) -> Dict[str, Path]
    def archive_order(order_id: str) -> Path
```

**EnhancedOutputGenerator**
```python
class EnhancedOutputGenerator:
    """Generates all output files with labels"""
    
    def __init__(self, file_manager: OrderFileManager)
    def generate_all_outputs(order_id: str, pieces: List[PieceInfo],
                           nesting_result: dict, metadata: dict) -> Dict[str, Path]
```

**PieceInfo (Dataclass)**
```python
@dataclass
class PieceInfo:
    name: str
    contour: List[Tuple[float, float]]
    bounding_box: Tuple[float, float, float, float]
    notches: Optional[List[Tuple[float, float]]]
    grainline: Optional[dict]
    piece_number: int
    total_pieces: int
```

#### Output Files Generated
1. `{ORDER_ID}.plt` - HPGL with labels
2. `{ORDER_ID}.pds` - Optitex format
3. `{ORDER_ID}.dxf` - CAD format
4. `{ORDER_ID}_metadata.json`
5. `{ORDER_ID}_qc_report.json`
6. `{ORDER_ID}_production.log`
7. `{ORDER_ID}_nesting.json`

---

### 8. order_continuity_validator.py (v6.4.3)
**Order continuity validation**

#### Classes

**OrderContinuityValidator**
```python
class OrderContinuityValidator:
    """Validates order number continuity throughout system"""
    
    def __init__(self, base_dir: str, db_connection=None)
    def validate_full_continuity(order_id: str) -> Tuple[bool, List[str]]
    def generate_continuity_report(order_id: str) -> dict
    def batch_validate(order_ids: List[str]) -> Dict[str, Tuple[bool, List[str]]]
    def fix_continuity_issues(order_id: str, auto_fix: bool = False) -> List[str]
```

#### Validation Checks
1. Database record exists
2. Folder structure correct
3. All required files present
4. File naming conventions
5. PLT contains order labels
6. PDS contains order metadata
7. DXF contains text entities
8. Metadata consistency
9. Piece labels present

#### Usage Example
```python
from order_continuity_validator import OrderContinuityValidator

validator = OrderContinuityValidator("out/orders")
success, errors = validator.validate_full_continuity("SDS-20260131-0001-A")

if success:
    print("All continuity checks passed!")
else:
    print(f"Issues: {errors}")
```

---

### 9. v6_4_3_integration.py
**Complete v6.4.3 pipeline integration**

#### Functions

**process_order_v6_4_3(...)**
```python
def process_order_v6_4_3(
    order_id: str,
    customer_id: str,
    garment_type: str,
    measurements: dict,
    base_dir: str = "DS-speciale/out/orders"
) -> dict
```

#### Classes

**ProductionPipelineV6_4_3**
```python
class ProductionPipelineV6_4_3:
    """Complete production pipeline with v6.4.3 features"""
    
    def __init__(self, base_dir: str)
    def process_order(order_data: dict) -> dict
    def _extract_and_scale_pattern(order_data: dict) -> List[PieceInfo]
    def _nest_pieces(pieces: List[PieceInfo]) -> dict
    def _run_quality_control(order_id: str, pieces: List[PieceInfo], 
                            outputs: dict) -> dict
```

---

## Nesting Algorithms

### master_nesting.py
**Best-of-all nesting selector**

```python
def master_nest(contour_groups: List, fabric_width: float = 157.48, 
                gap: float = 0.5, verbose: bool = False) -> NestingResult
```

Runs multiple algorithms and selects the best result based on utilization.

### hybrid_nesting.py
**True polygon collision nesting**

```python
def hybrid_nest(contours: List, fabric_width: float, gap: float) -> NestingResult
```

Uses actual polygon collision detection for precise nesting.

### turbo_nesting.py
**Shapely-based spatial indexing**

```python
def turbo_nest(contours: List, fabric_width: float, gap: float) -> NestingResult
```

Uses Shapely library for fast spatial operations.

---

## API & Web

### web_api.py
**FastAPI web server**

#### Key Endpoints

**Orders**
- `POST /orders` - Create order
- `GET /orders/{id}` - Get order
- `GET /orders/{id}/plt` - Download PLT
- `GET /orders/{id}/pds` - Download PDS
- `GET /orders/{id}/dxf` - Download DXF
- `GET /orders/{id}/files` - List files
- `GET /orders/{id}/status` - Order status

**Queue**
- `GET /queue/status` - Queue status
- `GET /queue/jobs` - List jobs
- `POST /queue/process-next` - Process next

**Monitoring**
- `GET /api/metrics` - Metrics
- `GET /api/health` - Health check
- `GET /api/alerts` - Alerts

**WebSocket**
- `WS /ws` - Real-time updates

#### Running the Server
```bash
python web_api.py
# or
uvicorn web_api:app --reload --host 0.0.0.0 --port 8000
```

---

## Integrations

### database_integration.py
**Supabase database integration**

```python
class OrderDatabase:
    def __init__(self, mode: str = "local")
    def create_order(order_data: dict) -> str
    def get_order(order_id: str) -> dict
    def update_order_status(order_id: str, status: str)
    def list_orders(status: Optional[str] = None) -> list
    def sync_pending_orders()
```

### theblackbox_integration.py
**TheBlackbox 3D body scanner**

```python
class TheBlackboxIntegration:
    def __init__(self, scans_dir: str)
    def validate_scan(scan_data: dict) -> dict
    def create_order_from_scan(scan_data: dict, garment_type: str) -> dict
    def generate_test_scan(profile: str) -> dict
```

---

## Complete Example

```python
from v6_4_3_integration import process_order_v6_4_3

# Process complete order with all v6.4.3 features
result = process_order_v6_4_3(
    order_id="SDS-20260131-0001-A",
    customer_id="CUST-001",
    garment_type="jacket",
    measurements={
        "chest": 102,
        "waist": 88,
        "hip": 100,
        "shoulder": 46,
        "inseam": 81
    },
    base_dir="DS-speciale/out/orders"
)

if result["success"]:
    print(f"Order processed: {result['order_id']}")
    print(f"Files generated: {len(result['files'])}")
    print(f"Continuity validated: {result['continuity_validated']}")
    
    # Access files
    for file_type, path in result['files'].items():
        print(f"  {file_type}: {path}")
else:
    print(f"Failed: {result['error']}")
```

---

**End of Module Reference**
