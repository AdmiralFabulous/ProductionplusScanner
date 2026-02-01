# SameDaySuits Pattern Factory - Production System

**Version:** 6.4.3  
**Status:** Production Ready  
**Date:** 2026-01-31

---

## Overview

The SameDaySuits Pattern Factory is a complete automated garment production system that converts 3D body scans into production-ready pattern files for CNC fabric cutters.

## Production Directory Structure

```
production/
├── src/                          # All source code
│   ├── core/                     # Core production modules
│   ├── nesting/                  # Nesting algorithms
│   ├── api/                      # Web API and dashboard
│   └── integrations/             # External integrations
├── docs/                         # Documentation
├── tests/                        # Test scripts
├── config/                       # Configuration files
└── samples/                      # Sample data

```

---

## Quick Start

### 1. Install Dependencies

```bash
cd production
pip install -r requirements.txt
```

### 2. Configure System

Edit `config/system.yaml` to set your paths and settings.

### 3. Run Tests

```bash
python -m pytest tests/ -v
```

### 4. Start Production Server

```bash
cd src/api
python web_api.py
```

### 5. Access Dashboard

Open browser: http://localhost:8000/dashboard

---

## Core Features

### 1. Multi-Algorithm Nesting
- 8 different nesting algorithms
- Automatic best-selection
- 78-88% fabric utilization

### 2. Quality Control
- Automated validation on every order
- 7 validation checks
- Detailed QC reports

### 3. TheBlackbox Integration
- 3D body scan processing
- Automatic measurement extraction
- Scan quality validation

### 4. Order File Management (v6.4.3)
- Standardized folder structure
- 7 required output files
- Order number on every piece

### 5. Continuity Validation
- 9 automated checks
- Complete order traceability
- Detailed validation reports

---

## File Reference

### Core Modules (src/core/)

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `samedaysuits_api.py` | Main production API | SameDaySuitsAPI, Order, ProductionResult |
| `production_pipeline.py` | End-to-end pipeline | process_order(), extract_pds(), generate_hpgl() |
| `quality_control.py` | QC validation | QualityControl, QCReport |
| `production_monitor.py` | Monitoring & alerts | ProductionMonitor, Alert |
| `cutter_queue.py` | Cutter queue management | CutterQueue, CutterJob |
| `pattern_scaler.py` | Pattern scaling | PatternScaler, calculate_scales() |
| `database_integration.py` | Supabase integration | OrderDatabase, OrderSyncService |
| `theblackbox_integration.py` | Body scanner | TheBlackboxIntegration, ScanData |
| `order_file_manager.py` | v6.4.3 file management | OrderFileManager, EnhancedOutputGenerator |
| `order_continuity_validator.py` | Continuity validation | OrderContinuityValidator |
| `v6_4_3_integration.py` | Complete pipeline | process_order_v6_4_3() |

### Nesting Algorithms (src/nesting/)

| File | Algorithm | Description |
|------|-----------|-------------|
| `master_nesting.py` | master_nest | Best-of-all selector (78-88% utilization) |
| `hybrid_nesting.py` | hybrid_nest | True polygon collision |
| `turbo_nesting.py` | turbo_nest | Shapely-based spatial indexing |
| `guillotine_nesting.py` | guillotine_nest | Rectangle splitting |
| `skyline_nesting.py` | skyline_nest | Top-edge tracking |
| `shelf_nesting.py` | shelf_nest | Bottom-left fill |
| `improved_nesting.py` | improved_nest | Enhanced guillotine+skyline |
| `nesting_engine.py` | basic_nest | Basic nesting engine |

### API & Web (src/api/)

| File | Purpose |
|------|---------|
| `web_api.py` | FastAPI web server with dashboard |
| `start_dashboard.py` | Convenience script to start server |

### Test Scripts (tests/)

| File | Tests |
|------|-------|
| `test_v6_4_3_end_to_end.py` | v6.4.3 complete workflow (30+ tests) |
| `test_master_complete.py` | Master test suite (all systems) |
| `test_normal_man.py` | Normal man profile test |
| `test_web_api.py` | API endpoint tests |

---

## CLI Commands

### Order Management
```bash
sds order --garment jacket --chest 102 --waist 88
sds batch orders.json
```

### Queue Management
```bash
sds queue status
sds queue process
sds queue list
```

### Monitoring
```bash
sds monitor status
sds monitor metrics
sds monitor alerts
```

### Quality Control
```bash
sds qc validate --file order.plt
sds qc list
```

### Scan Processing
```bash
sds scan process --file scan.json --garment jacket
sds scan validate --file scan.json
```

### Database
```bash
sds db status
sds db sync
```

---

## Order Output Files

Every order generates these files:

```
{ORDER_ID}/
├── {ORDER_ID}.plt          # HPGL cutter file (with labels)
├── {ORDER_ID}.pds          # Optitex editable pattern
├── {ORDER_ID}.dxf          # CAD exchange format
├── {ORDER_ID}_metadata.json    # Order details
├── {ORDER_ID}_qc_report.json   # QC validation
├── {ORDER_ID}_production.log   # Processing log
├── {ORDER_ID}_nesting.json     # Nesting statistics
├── pieces/                 # Individual piece files
├── previews/              # Visual previews
└── history/               # Revision history
```

---

## API Endpoints

### Orders
- `POST /orders` - Submit new order
- `GET /orders/{id}` - Get order details
- `GET /orders/{id}/plt` - Download PLT file
- `GET /orders/{id}/pds` - Download PDS file
- `GET /orders/{id}/dxf` - Download DXF file
- `GET /orders/{id}/files` - List all files
- `GET /orders/{id}/status` - Get order status

### Queue
- `GET /queue/status` - Queue status
- `POST /queue/process-next` - Process next job

### Monitoring
- `GET /api/metrics` - Production metrics
- `GET /api/health` - Health check
- `GET /api/alerts` - Active alerts

### WebSocket
- `WS /ws` - Real-time updates

---

## Configuration

### Environment Variables
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
CUTTER_WIDTH_CM=157.48
NESTING_GAP_CM=0.5
```

### System Configuration (config/system.yaml)
```yaml
paths:
  templates: "DS-speciale/inputs/pds/"
  output: "DS-speciale/out/orders/"
  spool: "DS-speciale/out/cutter_spool/"

processing:
  fabric_width: 157.48  # cm (62 inches)
  nesting_gap: 0.5      # cm
  min_utilization: 60.0 # %

monitoring:
  alert_thresholds:
    utilization_low: 60
    failure_rate_high: 5
    queue_backup: 10
```

---

## Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test
```bash
python tests/test_v6_4_3_end_to_end.py
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

---

## Troubleshooting

### Issue: Low nesting utilization
- Check fabric width setting (should be 157.48cm)
- Try manual algorithm selection
- Verify piece shapes

### Issue: Missing output files
- Check folder permissions
- Verify disk space
- Review production logs

### Issue: Database sync failed
- Check network connectivity
- Verify Supabase credentials
- Run `sds db sync` manually

### Issue: WebSocket disconnected
- Check server status
- Verify network connection
- Refresh dashboard

---

## Documentation

See `docs/` directory for complete documentation:
- `OPERATIONS_MANUAL_v6.4.2.md` - System documentation
- `OPERATIONS_MANUAL_v6.4.3.md` - Output standards
- `NESTING_ANALYSIS.md` - Nesting performance analysis
- `V6_4_3_TEST_SUMMARY.md` - Test results

---

## Support

For issues or questions:
- Check documentation in `docs/`
- Review test scripts in `tests/`
- Check logs in `logs/`

---

**System Version:** 6.4.3  
**Last Updated:** 2026-01-31  
**Status:** Production Ready
