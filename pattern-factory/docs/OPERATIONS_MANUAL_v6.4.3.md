# SameDaySuits Operations Manual

## Version 6.4.3

**Pattern Factory Production System - Output Standards & Order Tracking**

---

**Document Information:**
- Version: 6.4.3
- Date: 2026-01-31
- Status: Production
- Classification: Internal Use

**Change History:**
- v6.4.3: Added output file standards (PDS, DXF), folder nomenclature, order tracking dashboard, piece labeling requirements
- v6.4.2: Added Database, Queue, Pattern Scaling, WebSocket, Architecture, Testing, Alerts
- v6.4.1: Added Nesting, Monitoring, QC, TheBlackbox Integration

---

## Table of Contents (v6.4.3)

15. [Output File Standards](#15-output-file-standards)
16. [Folder Structure & Nomenclature](#16-folder-structure--nomenclature)
17. [Order Tracking Dashboard](#17-order-tracking-dashboard)
18. [Pattern Piece Labeling](#18-pattern-piece-labeling)
19. [Order Number Continuity](#19-order-number-continuity)

---

## 15. Output File Standards

### 15.1 Required Output Files

Every production order MUST generate the following files:

| File Type | Extension | Purpose | Required |
|-----------|-----------|---------|----------|
| HPGL/PLT | `.plt` | Cutter instruction file | YES |
| PDS (Optitex) | `.pds` | Editable pattern file | YES |
| DXF | `.dxf` | CAD exchange format | YES |
| Metadata | `_metadata.json` | Order details & parameters | YES |
| QC Report | `_qc_report.json` | Quality validation results | YES |
| Production Log | `_production.log` | Processing timeline | YES |
| Nesting Report | `_nesting.json` | Nesting statistics | YES |

### 15.2 PDS (Optitex) Output

**Purpose**: Generate editable PDS files for pattern modifications and future adjustments.

**File Location**: 
```
DS-speciale/out/orders/{ORDER_ID}/{ORDER_ID}.pds
```

**Implementation**:
```python
from production_pipeline import generate_pds_output

# Generate PDS from scaled contours
pds_path = generate_pds_output(
    order_id=order_id,
    scaled_contours=scaled_contours,
    output_dir=output_dir,
    include_notches=True,
    include_grainline=True,
    include_piece_names=True
)
```

**PDS Content Requirements**:
- All pattern pieces with original curves (not faceted)
- Notch marks for alignment
- Grain line indicators
- Piece names and identifiers
- Order number in file metadata
- Scaling factors recorded
- Original graded size information preserved

### 15.3 DXF Output

**Purpose**: Standard CAD exchange format for compatibility with other systems.

**File Location**:
```
DS-speciale/out/orders/{ORDER_ID}/{ORDER_ID}.dxf
```

**Implementation**:
```python
from production_pipeline import generate_dxf_output

# Generate DXF for CAD import
dxf_path = generate_dxf_output(
    order_id=order_id,
    nested_contours=nested_contours,
    output_dir=output_dir,
    units='mm',
    layer_pieces='PATTERN_PIECES',
    layer_notches='NOTCHES',
    layer_text='LABELS'
)
```

**DXF Content Requirements**:
- POLYLINE entities for piece boundaries
- LAYER organization:
  - `PATTERN_PIECES`: Main piece outlines
  - `NOTCHES`: Alignment notches
  - `LABELS`: Text annotations (order number, piece names)
  - `GRAINLINE`: Grain direction lines
  - `CUT_LINES`: Cut paths for nested layout
- Text entities with order number and piece info
- Coordinate system: mm units
- Proper scaling applied

### 15.4 Enhanced PLT Output

**Updated Requirements**:
- Include piece numbering (xxx/xxx format)
- Include order number labels
- Include piece names
- Include grain direction arrows

**Implementation**:
```python
from production_pipeline import generate_enhanced_hpgl

# Generate enhanced PLT with labels
plt_path = generate_enhanced_hpgl(
    order_id=order_id,
    nested_contours=nested_contours,
    piece_names=piece_names,
    output_dir=output_dir,
    include_labels=True,
    label_font_size=8,  # mm
    label_position='center'  # or 'corner'
)
```

**PLT Label Commands**:
```
; Piece with labels
SP1;                    ; Select pen 1
PU1000,1000;            ; Move to piece position
PD1000,2000;            ; Draw piece outline
...
PU1500,1500;            ; Move to label position
LB12345-001^;           ; Order number label
PU1600,1600;            ; Move to piece counter
LB001/015^;             ; Piece 1 of 15
PU1700,1700;            ; Move to piece name
LBFRONT_PANEL^;         ; Piece name
SP0;                    ; Deselect pen
```

### 15.5 New Section: 2.12 Output File Standards

```
2.12 Output File Standards

2.12.1 Overview
Every production order must generate a complete set of output files
including editable formats (PDS, DXF) and production formats (PLT).
This ensures compatibility with various systems and preserves order
information for future reference.

2.12.2 Required Outputs

For each order, the following files MUST be created:

1. {ORDER_ID}.plt
   - HPGL format for cutter
   - Nested pieces ready for cutting
   - Includes piece labels and order numbers
   
2. {ORDER_ID}.pds
   - Optitex PDS format
   - Editable pattern with curves preserved
   - Includes notches, grain lines, piece names
   
3. {ORDER_ID}.dxf
   - CAD exchange format
   - Layer-organized geometry
   - Includes all annotations
   
4. {ORDER_ID}_metadata.json
   - Order parameters and measurements
   - Processing settings
   - File paths reference
   
5. {ORDER_ID}_qc_report.json
   - Quality control results
   - Validation checks
   - Error and warning details
   
6. {ORDER_ID}_production.log
   - Processing timeline
   - Stage durations
   - Error logs
   
7. {ORDER_ID}_nesting.json
   - Nesting statistics
   - Piece positions
   - Utilization data

2.12.3 File Retention Policy

Local Storage: Retain indefinitely
- PLT files: Production artifacts (keep forever)
- PDS files: Pattern masters (keep forever)
- DXF files: CAD backups (keep forever)
- Metadata: Order records (keep forever)

Database Sync: 90 days active, then archive
- Production logs: Archive after 90 days
- QC reports: Keep active for 1 year
- Sync records: Clean after 30 days

2.12.4 File Naming Convention

Format: {ORDER_ID}.{ext}
Example: SDS-20260131-001-A.plt

Where:
- SDS: SameDaySuits prefix
- 20260131: Date (YYYYMMDD)
- 001: Sequential order number
- A: Revision (A, B, C...)
- .plt: File extension

2.12.5 Quality Standards

All output files must pass validation:
- PLT: Cutter simulation test
- PDS: Opens in Optitex without errors
- DXF: Imports to CAD software successfully
- JSON: Valid JSON schema

2.12.6 Output Verification

Automated checks after generation:
1. File exists and size > 0
2. File format is valid
3. Order number present in file
4. All pieces included
5. Metadata matches actual content
```

---

## 16. Folder Structure & Nomenclature

### 16.1 Standardized Folder Hierarchy

```
DS-speciale/out/orders/
├── {ORDER_ID}/                           # Individual order folder
│   ├── {ORDER_ID}.plt                    # HPGL cutter file
│   ├── {ORDER_ID}.pds                    # Optitex pattern file
│   ├── {ORDER_ID}.dxf                    # CAD exchange file
│   ├── {ORDER_ID}_metadata.json          # Order metadata
│   ├── {ORDER_ID}_qc_report.json         # QC validation
│   ├── {ORDER_ID}_production.log         # Processing log
│   ├── {ORDER_ID}_nesting.json           # Nesting data
│   ├── pieces/                           # Individual piece exports
│   │   ├── {ORDER_ID}_piece_01_front.pds
│   │   ├── {ORDER_ID}_piece_02_back.pds
│   │   └── ...
│   ├── previews/                         # Visual previews
│   │   ├── nesting_layout.png
│   │   └── piece_details.pdf
│   └── history/                          # Revision history
│       ├── rev_A/                        # Original version
│       ├── rev_B/                        # Modified version
│       └── ...
```

### 16.2 Order Number Format

**Standard Format**: `SDS-YYYYMMDD-NNNN-R`

**Components**:
- `SDS`: SameDaySuits prefix
- `YYYYMMDD`: Order date
- `NNNN`: Sequential number (0001-9999)
- `R`: Revision letter (A, B, C...)

**Examples**:
- `SDS-20260131-0001-A`: First order on Jan 31, 2026
- `SDS-20260131-0002-A`: Second order same day
- `SDS-20260131-0001-B`: Revised version of first order

### 16.3 Implementation

```python
from production_pipeline import OrderFileManager

# Initialize file manager
file_mgr = OrderFileManager(base_dir="DS-speciale/out/orders")

# Create order folder structure
order_folder = file_mgr.create_order_folder(
    order_id="SDS-20260131-0001-A",
    customer_id="CUST-001",
    create_subdirs=True
)

# Returns path: DS-speciale/out/orders/SDS-20260131-0001-A/
# Creates subdirectories:
#   - pieces/
#   - previews/
#   - history/rev_A/

# Save output files
file_mgr.save_plt(plt_data)
file_mgr.save_pds(pds_data)
file_mgr.save_dxf(dxf_data)
file_mgr.save_metadata(metadata)

# Files are automatically named with order_id prefix
```

### 16.4 New Section: 2.13 Folder Structure & Nomenclature

```
2.13 Folder Structure & Nomenclature

2.13.1 Overview
Standardized folder hierarchy and naming conventions ensure order
continuity, easy retrieval, and proper file organization. Every order
must follow this structure exactly.

2.13.2 Order Number Format

Standard: SDS-YYYYMMDD-NNNN-R

Components:
- SDS: SameDaySuits prefix (constant)
- YYYYMMDD: Order creation date
- NNNN: Sequential order number (4 digits)
- R: Revision letter (A-Z)

Examples:
- SDS-20260131-0001-A: First order of Jan 31, 2026
- SDS-20260131-0150-A: 150th order of Jan 31, 2026
- SDS-20260131-0001-B: First revision of order 0001

2.13.3 Folder Hierarchy

DS-speciale/out/orders/{ORDER_ID}/
├── {ORDER_ID}.plt              # Cutter file
├── {ORDER_ID}.pds              # Optitex file
├── {ORDER_ID}.dxf              # CAD file
├── {ORDER_ID}_metadata.json    # Order data
├── {ORDER_ID}_qc_report.json   # QC results
├── {ORDER_ID}_production.log   # Processing log
├── {ORDER_ID}_nesting.json     # Nesting stats
├── pieces/                     # Individual pieces
│   ├── {ORDER_ID}_piece_01.pds
│   ├── {ORDER_ID}_piece_02.pds
│   └── ...
├── previews/                   # Visual outputs
│   ├── nesting_layout.png
│   └── piece_details.pdf
└── history/                    # Revisions
    ├── rev_A/
    ├── rev_B/
    └── ...

2.13.4 Naming Rules

Order ID Rules:
- Must be unique across all time
- Sequential numbering within each day
- Revision letters increment for changes
- Case sensitive: always uppercase

File Naming:
- Always start with order ID
- Use underscores for separation
- Include descriptive suffixes
- Use lowercase for extensions

Examples:
✓ SDS-20260131-0001-A.plt
✓ SDS-20260131-0001-A_metadata.json
✓ SDS-20260131-0001-A_piece_01_front.pds
✗ sds-20260131-1-A.plt (lowercase, missing leading zeros)
✗ SDS_20260131_0001_A.plt (underscores instead of hyphens)

2.13.5 Subdirectory Purposes

pieces/: 
- Individual piece exports
- One file per piece
- Multiple formats (.pds, .dxf)

previews/:
- PNG nesting visualization
- PDF piece details
- Thumbnail images

history/:
- Previous revisions
- Backup before modifications
- Archive after completion

2.13.6 Retention & Archival

Active Orders: Keep in orders/
Completed Orders: Move to orders/archive/ after 30 days
Revision History: Keep 1 year, then archive
Backup: Daily sync to cloud storage

2.13.7 Implementation

File Manager Class:
- Automatically creates folder structure
- Enforces naming conventions
- Handles revisions
- Manages archival

See production_pipeline.py: OrderFileManager
```

---

## 17. Order Tracking Dashboard

### 17.1 Dashboard Overview

Real-time dashboard showing all orders from submission through completion with order number continuity maintained throughout.

### 17.2 Dashboard Sections

**1. Active Orders Panel**
```
┌─────────────────────────────────────────────────────────────┐
│ ACTIVE ORDERS (12)                                          │
├──────────────┬──────────┬──────────┬──────────┬─────────────┤
│ Order ID     │ Customer │ Status   │ Stage    │ Progress    │
├──────────────┼──────────┼──────────┼──────────┼─────────────┤
│ SDS-202...1-A│ CUST-001 │ Processing│ Nesting │ ████████░░ │
│ SDS-202...2-A│ CUST-002 │ Queued   │ -        │ ⏳ Pending  │
│ SDS-202...3-A│ CUST-003 │ Cutting  │ Cutter   │ 🔪 Active   │
└──────────────┴──────────┴──────────┴──────────┴─────────────┘
```

**2. Order Detail View**
Click any order ID to see:
- Complete order information
- Current processing stage
- All output files with links
- Processing timeline
- QC status
- Cutter queue position

**3. File Access Panel**
Direct links to all files:
```
Order: SDS-20260131-0001-A

📁 View Folder
📄 Download PLT
📄 Download PDS
📄 Download DXF
📄 View Metadata
📄 View QC Report
```

### 17.3 Implementation

**Dashboard UI** (`web_api.py`):
```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/dashboard", response_class=HTMLResponse)
async def production_dashboard():
    """Main production dashboard"""
    orders = await get_all_orders_with_status()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pattern Factory Dashboard</title>
        <style>
            .order-row { cursor: pointer; }
            .order-row:hover { background: #f0f0f0; }
            .status-pending { color: orange; }
            .status-processing { color: blue; }
            .status-completed { color: green; }
        </style>
    </head>
    <body>
        <h1>Production Dashboard</h1>
        <table>
            <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Stage</th>
                <th>Files</th>
            </tr>
    """
    
    for order in orders:
        html += f"""
            <tr class="order-row" onclick="viewOrder('{order['id']}'}">
                <td>{order['id']}</td>
                <td>{order['customer']}</td>
                <td class="status-{order['status']}">{order['status']}</td>
                <td>{order['stage']}</td>
                <td>
                    <a href="/orders/{order['id']}/plt">PLT</a> |
                    <a href="/orders/{order['id']}/pds">PDS</a> |
                    <a href="/orders/{order['id']}/dxf">DXF</a>
                </td>
            </tr>
        """
    
    html += "</table></body></html>"
    return html

@app.get("/orders/{order_id}/status")
async def order_status(order_id: str):
    """Get detailed order status"""
    return {
        "order_id": order_id,
        "status": "processing",
        "stage": "nesting",
        "progress": 75,
        "files": {
            "plt": f"/orders/{order_id}.plt",
            "pds": f"/orders/{order_id}.pds",
            "dxf": f"/orders/{order_id}.dxf",
            "metadata": f"/orders/{order_id}_metadata.json"
        },
        "folder": f"DS-speciale/out/orders/{order_id}/"
    }
```

### 17.4 WebSocket Real-time Updates

```javascript
// Dashboard JavaScript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'order_update') {
        updateOrderRow(data.order_id, {
            status: data.status,
            stage: data.stage,
            progress: data.progress
        });
    }
};

function updateOrderRow(orderId, data) {
    const row = document.querySelector(`[data-order-id="${orderId}"]`);
    if (row) {
        row.querySelector('.status').textContent = data.status;
        row.querySelector('.stage').textContent = data.stage;
        row.querySelector('.progress').style.width = data.progress + '%';
    }
}
```

### 17.5 New Section: 3.5 Order Tracking Dashboard

```
3.5 Order Tracking Dashboard

3.5.1 Overview
The Order Tracking Dashboard provides real-time visibility into all orders
from initial submission through final completion. Maintains order number
continuity throughout the entire process and provides direct access to all
associated files.

3.5.2 Dashboard Layout

Main Panels:
1. Active Orders Table
   - All orders in progress
   - Current status and stage
   - Progress indicators
   - Quick file access links

2. Order Detail View
   - Comprehensive order information
   - Processing timeline
   - File list with download links
   - QC results
   - Cutter queue position

3. Completed Orders
   - Recently finished orders
   - Archive access
   - Search and filter

4. System Status
   - Queue length
   - Processing rate
   - Error counts
   - Alert notifications

3.5.3 Order Status Tracking

Status Values:
- submitted: Order received
- validating: Checking measurements
- selecting_template: Choosing base pattern
- scaling: Applying customer measurements
- nesting: Optimizing layout
- qc_check: Quality validation
- queued: Waiting for cutter
- cutting: Being cut
- completed: Finished
- failed: Error occurred

Stage Progress:
Each status includes progress percentage (0-100%)
Visual progress bars show completion
Color coding indicates status type

3.5.4 File Access

Every order row includes direct links to:
- PLT file (cutter file)
- PDS file (Optitex editable)
- DXF file (CAD format)
- Metadata JSON
- QC Report
- Production folder

Clicking order ID opens detail view with:
- Full file list
- File sizes and timestamps
- Download buttons
- Preview images

3.5.5 Real-time Updates

WebSocket Connection:
- Live status updates
- Progress changes
- File availability
- Alert notifications

Update Frequency:
- Status changes: Immediate
- Progress: Every 5 seconds during processing
- File availability: As generated
- System metrics: Every 30 seconds

3.5.6 Search & Filter

Search Options:
- Order ID
- Customer ID
- Date range
- Status
- Garment type

Filter Controls:
- Show/hide completed
- Status filters
- Date range picker
- Customer search

3.5.7 Mobile Access

Responsive Design:
- Mobile-optimized layout
- Touch-friendly controls
- Essential features only
- Quick status checks

3.5.8 API Endpoints

GET /dashboard
  Returns HTML dashboard page
  Authentication: Required

GET /api/orders?status=&date=&customer=
  List orders with filters
  Returns: Array of order summaries

GET /api/orders/{order_id}/status
  Detailed order status
  Returns: Complete order info + file list

GET /api/orders/{order_id}/files
  List all files for order
  Returns: File paths and metadata

WebSocket /ws
  Real-time updates
  Subscribe to order changes

3.5.9 Implementation

See web_api.py:
- Dashboard route
- Order status endpoints
- WebSocket handlers
- File serving routes
```

---

## 18. Pattern Piece Labeling

### 18.1 Labeling Requirements

Every pattern piece MUST have:
1. Order number printed on piece
2. Piece name/identifier
3. Piece number/total count (xxx/xxx format)
4. Grain direction arrow
5. Notch marks (for alignment)

### 18.2 Label Format

**Standard Label**:
```
┌─────────────────────────┐
│  SDS-20260131-0001-A    │  ← Order Number
│  FRONT_PANEL            │  ← Piece Name
│  001/015                │  ← Piece 1 of 15
│  ↗                      │  ← Grain Arrow
└─────────────────────────┘
```

**Position**: Center of piece or designated label area
**Font Size**: 8mm minimum for cutter readability
**Contrast**: High contrast for visibility on fabric

### 18.3 PLT Label Implementation

```python
from production_pipeline import add_labels_to_plt

def generate_labeled_plt(order_id, pieces, output_path):
    """Generate PLT with piece labels"""
    
    with open(output_path, 'w') as plt:
        plt.write("IN;\n")  # Initialize
        
        for idx, piece in enumerate(pieces, 1):
            # Draw piece outline
            plt.write(f"SP1;\n")  # Select pen 1
            
            for point in piece.contour:
                plt.write(f"PD{point.x},{point.y};\n")
            
            # Calculate label position (center of bounding box)
            center_x = (piece.bbox.min_x + piece.bbox.max_x) / 2
            center_y = (piece.bbox.min_y + piece.bbox.max_y) / 2
            
            # Add order number label
            plt.write(f"PU{center_x},{center_y + 40};\n")
            plt.write(f"LB{order_id}^;\n")
            
            # Add piece name
            plt.write(f"PU{center_x},{center_y + 20};\n")
            plt.write(f"LB{piece.name}^;\n")
            
            # Add piece counter (xxx/xxx format)
            total_pieces = len(pieces)
            plt.write(f"PU{center_x},{center_y};\n")
            plt.write(f"LB{idx:03d}/{total_pieces:03d}^;\n")
            
            # Add grain line arrow
            if piece.has_grainline:
                arrow_x = center_x + 60
                arrow_y = center_y - 20
                plt.write(f"PU{arrow_x},{arrow_y};\n")
                plt.write(f"PD{arrow_x + 20},{arrow_y + 10};\n")  # Arrow shaft
                plt.write(f"PD{arrow_x},{arrow_y + 20};\n")      # Arrow head
            
            plt.write("PU;\n")
        
        plt.write("SP0;\n")  # Deselect pen
        plt.write("IN;\n")  # Finalize
```

### 18.4 PDS Label Implementation

```python
from production_pipeline import add_labels_to_pds

def generate_labeled_pds(order_id, pieces, output_path):
    """Generate PDS with piece labels"""
    
    pds = PDSFile()
    
    for idx, piece in enumerate(pieces, 1):
        # Add piece geometry
        pds.add_piece(
            name=piece.name,
            contour=piece.contour,
            notches=piece.notches
        )
        
        # Add text label
        center = piece.bounding_box.center
        
        # Order number
        pds.add_text(
            text=order_id,
            position=(center.x, center.y + 40),
            font_size=8,
            layer="LABELS"
        )
        
        # Piece name
        pds.add_text(
            text=piece.name,
            position=(center.x, center.y + 20),
            font_size=6,
            layer="LABELS"
        )
        
        # Piece counter
        pds.add_text(
            text=f"{idx:03d}/{len(pieces):03d}",
            position=(center.x, center.y),
            font_size=8,
            font_weight="bold",
            layer="LABELS"
        )
        
        # Grain line
        if piece.grainline:
            pds.add_grainline(
                start=piece.grainline.start,
                end=piece.grainline.end,
                arrow=True,
                layer="GRAINLINE"
            )
    
    pds.save(output_path)
```

### 18.5 DXF Label Implementation

```python
import ezdxf

def generate_labeled_dxf(order_id, pieces, output_path):
    """Generate DXF with piece labels"""
    
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Create layers
    doc.layers.add("PATTERN_PIECES")
    doc.layers.add("LABELS")
    doc.layers.add("GRAINLINE")
    
    for idx, piece in enumerate(pieces, 1):
        # Draw piece outline
        points = [(p.x, p.y) for p in piece.contour]
        msp.add_lwpolyline(
            points,
            close=True,
            dxfattribs={'layer': 'PATTERN_PIECES'}
        )
        
        # Calculate center
        bbox = piece.bounding_box
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        # Add order number
        msp.add_text(
            order_id,
            dxfattribs={
                'insert': (center_x, center_y + 40),
                'height': 8,
                'layer': 'LABELS'
            }
        )
        
        # Add piece name
        msp.add_text(
            piece.name,
            dxfattribs={
                'insert': (center_x, center_y + 20),
                'height': 6,
                'layer': 'LABELS'
            }
        )
        
        # Add piece counter
        msp.add_text(
            f"{idx:03d}/{len(pieces):03d}",
            dxfattribs={
                'insert': (center_x, center_y),
                'height': 8,
                'layer': 'LABELS',
                'style': 'BOLD'
            }
        )
    
    doc.saveas(output_path)
```

### 18.6 New Section: 2.14 Pattern Piece Labeling

```
2.14 Pattern Piece Labeling

2.14.1 Overview
Every pattern piece must be clearly labeled with order identification,
piece identification, and count information. This ensures proper tracking
during cutting and assembly, and prevents mix-ups between orders.

2.14.2 Required Labels

Each piece must include:
1. Order Number (top line)
   - Full order ID: SDS-YYYYMMDD-NNNN-R
   - Font size: 8mm minimum
   
2. Piece Name (middle line)
   - Descriptive name: FRONT_PANEL, BACK_PANEL, SLEEVE_LEFT
   - Font size: 6mm
   
3. Piece Counter (bottom line)
   - Format: XXX/XXX (piece number / total pieces)
   - Example: 001/015, 002/015, etc.
   - Font size: 8mm, bold
   
4. Grain Direction (optional line)
   - Arrow indicating grain line
   - Positioned near counter

2.14.3 Label Format

Standard Layout:
┌─────────────────────────┐
│  SDS-20260131-0001-A    │  ← Order Number (8mm)
│  FRONT_PANEL            │  ← Piece Name (6mm)
│  001/015                │  ← Counter (8mm bold)
│  ↗                      │  ← Grain Arrow
└─────────────────────────┘

Positioning:
- Center of piece bounding box
- Minimum 10mm from edges
- Avoid overlapping seams or notches
- Ensure visibility on fabric color

2.14.4 Font Specifications

HPGL/PLT:
- Use standard HPGL font commands
- LB (Label) command for text
- Font size in mm units

PDS:
- Optitex text entities
- Vector fonts for scaling
- Embedded in file

DXF:
- TEXT entities
- Height attribute in drawing units
- Layer: LABELS

2.14.5 Implementation

See production_pipeline.py:
- generate_labeled_plt()
- generate_labeled_pds()
- generate_labeled_dxf()

All functions:
- Calculate piece center
- Position labels appropriately
- Ensure readability
- Verify text within piece bounds

2.14.6 Quality Control

QC checks for labels:
- All pieces have labels
- Order number matches order ID
- Counter sequential (001 to N)
- Text within piece boundaries
- Readable size (>= 8mm)

Failure Modes:
- Missing labels: REJECT
- Wrong order number: REJECT
- Illegible text: WARNING
- Outside piece bounds: WARNING

2.14.7 Cutting Considerations

Label Placement:
- Labels cut with pattern piece
- Positioned in waste areas when possible
- Avoid functional areas of garment
- Consider fabric print/pattern

Cutter Settings:
- Text cut at lower speed for precision
- Pen 2 for labels (if supported)
- Verify cutter can handle text

2.14.8 Assembly Tracking

Piece counters help assembly:
- Verify all pieces present
- Correct assembly order
- Quality check completeness
- Inventory management

Operators use labels to:
- Sort pieces by order
- Identify pieces quickly
- Verify completeness
- Track progress
```

---

## 19. Order Number Continuity

### 19.1 Continuity Requirements

The order number must be maintained throughout the entire lifecycle:

1. **Order Submission**: Assigned at creation
2. **Database**: Stored as primary key
3. **Folder Name**: Folder named with order ID
4. **File Names**: All files prefixed with order ID
5. **Output Files**: Order ID embedded in PLT/PDS/DXF
6. **Piece Labels**: Order ID printed on every piece
7. **Cutter Queue**: Job tagged with order ID
8. **Physical Pieces**: Order ID on cut fabric pieces

### 19.2 Continuity Chain

```
Customer Order
    ↓
Order Number: SDS-20260131-0001-A (Assigned)
    ↓
Database Record (order_id field)
    ↓
Folder: DS-speciale/out/orders/SDS-20260131-0001-A/
    ↓
Files: SDS-20260131-0001-A.plt
       SDS-20260131-0001-A.pds
       SDS-20260131-0001-A.dxf
    ↓
PLT Content: Labels with order number
    ↓
Cut Pieces: Physical pieces with order number printed
    ↓
Assembly: Operator matches pieces by order number
```

### 19.3 Validation Checks

**Automated Continuity Checks**:
```python
from production_pipeline import validate_order_continuity

def check_order_continuity(order_id):
    """Verify order number continuity throughout system"""
    
    checks = {
        'database': check_database_record(order_id),
        'folder': check_folder_exists(order_id),
        'files': check_all_files_present(order_id),
        'plt_labels': check_plt_contains_order_id(order_id),
        'pds_labels': check_pds_contains_order_id(order_id),
        'dxf_labels': check_dxf_contains_order_id(order_id)
    }
    
    all_passed = all(checks.values())
    
    if not all_passed:
        failed = [k for k, v in checks.items() if not v]
        raise ContinuityError(f"Order {order_id} continuity failed: {failed}")
    
    return True
```

### 19.4 New Section: 2.15 Order Number Continuity

```
2.15 Order Number Continuity

2.15.1 Overview
Order number continuity ensures the order ID is consistently maintained
throughout the entire production lifecycle, from initial submission to
final assembly. This prevents mix-ups and enables complete traceability.

2.15.2 Continuity Requirements

The order number (SDS-YYYYMMDD-NNNN-R) must appear in:

1. Order Submission
   - Assigned at order creation
   - Included in order metadata
   - Sent to customer confirmation

2. Database Record
   - Primary key in orders table
   - Referenced in production_logs
   - Linked to customer record

3. File System
   - Folder name: {ORDER_ID}/
   - All files prefixed: {ORDER_ID}.*
   - Subfolders maintain reference

4. Output Files
   - PLT: Embedded in labels
   - PDS: In file metadata
   - DXF: In layer attributes
   - JSON: In order_id field

5. Pattern Pieces
   - Printed on every piece
   - Visible after cutting
   - Survives handling

6. Cutter Queue
   - Job tagged with order ID
   - Operator sees order ID
   - Completion logged by order ID

7. Physical Garment
   - Temporary labels on pieces
   - Final care label (optional)
   - Packaging slip reference

2.15.3 Continuity Validation

Automated Checks:
At each stage, verify order ID consistency:

Database → Files:
- Check folder name matches database
- Verify all files use correct prefix

Files → Content:
- Parse PLT for order ID labels
- Check PDS metadata
- Verify DXF text entities

Content → Physical:
- Spot check cut pieces
- Verify labels printed correctly
- Confirm readability

2.15.4 Continuity Failures

Failure Scenarios:
- Wrong order ID in file: REJECT file
- Missing order ID on piece: REPRINT
- Mismatched IDs: HALT production
- Illegible labels: RECUT

Recovery Procedures:
1. Stop all processing
2. Identify affected orders
3. Verify physical pieces
4. Regenerate if necessary
5. Update tracking
6. Resume production

2.15.5 Implementation

Continuity Checker:
See production_pipeline.py: validate_order_continuity()

Checks performed:
- Database record exists
- Folder structure correct
- All files present and named correctly
- File content contains order ID
- Labels properly formatted

Integration Points:
- Run before marking order complete
- Part of QC validation
- Logged in production log
- Alert on failure

2.15.6 Audit Trail

Complete traceability:
- Every operation logged with order ID
- Timestamp for each stage
- Operator identification
- File checksums
- Physical location tracking

Audit Report:
Can reconstruct entire order history:
- When submitted
- Who processed
- What files generated
- When cut
- Where assembled
- When shipped

2.15.7 Best Practices

Operators must:
- Verify order ID at each handoff
- Report mismatches immediately
- Never mix pieces from different orders
- Check labels before cutting
- Confirm order ID on packaging

System enforces:
- Automatic validation
- Hard stops on mismatch
- Complete audit logging
- Immutable order records
```

---

## Appendix E: Implementation Checklist

### E.1 Output File Generation

- [ ] Update `production_pipeline.py` to generate PDS files
- [ ] Update `production_pipeline.py` to generate DXF files
- [ ] Enhance PLT generation with labels
- [ ] Add file validation functions
- [ ] Test all output formats

### E.2 Folder Structure

- [ ] Implement `OrderFileManager` class
- [ ] Create folder structure on order creation
- [ ] Enforce naming conventions
- [ ] Add revision handling
- [ ] Implement archival system

### E.3 Dashboard Updates

- [ ] Add file download links
- [ ] Show file generation status
- [ ] Add folder path display
- [ ] Implement file preview
- [ ] Add search by order ID

### E.4 Piece Labeling

- [ ] Update PLT generator with label functions
- [ ] Update PDS generator with text entities
- [ ] Update DXF generator with TEXT entities
- [ ] Add label positioning logic
- [ ] Test label readability

### E.5 Continuity Validation

- [ ] Implement continuity checker
- [ ] Add to QC validation
- [ ] Create audit logging
- [ ] Add failure alerts
- [ ] Test end-to-end continuity

---

**End of Operations Manual v6.4.3**

**Document Version:** 6.4.3  
**Last Updated:** 2026-01-31  
**New Sections:** 15-19 + Appendix E  
**Status:** Production Requirements
