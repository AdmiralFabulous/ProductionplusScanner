# EYESON - SameDaySuits Pattern Factory Integration Guide

## Overview

This document describes how EYESON (body scanning frontend) integrates with the **SameDaySuits Pattern Factory** backend (`REVERSE-ENGINEER-PDS\production`).

**References:**
- Backend: `D:\SameDaySuits\_SameDaySuits\PILLARS_SAMEDAYSUITS\XX-EXPERIMENTS\REVERSE-ENGINEER-PDS\production`
- Operations Manual: `D:\SameDaySuits\_SameDaySuits\DOCUMENTATION\SUIT_AI_Master_Operations_Manual_v6_7_1.md`
- Pattern Factory Version: v6.4.3 Production Ready

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EYESON FRONTEND                                 │
│  (React + TypeScript + MediaPipe + Vite)                                     │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Welcome     │→ │   Capture    │→ │  Processing  │→ │   Results    │     │
│  │  (Language)  │  │  (MediaPipe) │  │  (Polling)   │  │  (Download)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                 │                 │                 │              │
│         └─────────────────┴─────────────────┴─────────────────┘              │
│                              │                                               │
│                    JWT Auth + API Calls                                      │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PATTERN FACTORY BACKEND                              │
│  (FastAPI + Supabase + Redis)                                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  API Layer (FastAPI)                                                │    │
│  │  ├── POST /orders          - Submit order with measurements         │    │
│  │  ├── GET  /orders/{id}     - Get order details                      │    │
│  │  ├── GET  /orders/{id}/plt - Download HPGL cutter file              │    │
│  │  ├── GET  /orders/{id}/pds - Download Optitex PDS file              │    │
│  │  └── GET  /orders/{id}/dxf - Download DXF CAD file                  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Black Box Pipeline                                                 │    │
│  │  ├── PDS Template Loading                                           │    │
│  │  ├── Pattern Scaling (from measurements)                            │    │
│  │  ├── Nesting (8 algorithms)                                         │    │
│  │  ├── HPGL Generation                                                │    │
│  │  └── QC Validation (7 checks)                                       │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Database (Supabase)                                                │    │
│  │  └── orders table                                                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Authentication (JWT)

**ref: ops manual Section 2.5 - Security Layer**

EYESON authenticates with Pattern Factory using JWT tokens:

```typescript
// Login flow
const { access_token, refresh_token } = await login(email, password)
localStorage.setItem('access_token', access_token)

// All API calls include Bearer token
Authorization: Bearer <access_token>
```

**Token expiry:** 1 hour (auto-refresh implemented)

### 2. Measurement Data Format

**ref: ops manual Section 13 - Database Schema**

EYESON extracts 28 body measurements using MediaPipe + 3D reconstruction.
These are transformed to Pattern Factory format:

```typescript
// EYESON internal format
{
  chest_girth: { value: 102.5, confidence: 0.95 },
  waist_girth: { value: 88.0, confidence: 0.92 },
  // ... etc
}

// Pattern Factory API format
{
  Cg: { value: 102.5, unit: 'cm', confidence: 0.95 },  // Chest Girth
  Wg: { value: 88.0, unit: 'cm', confidence: 0.92 },   // Waist Girth
  // ... etc (see full mapping below)
}
```

### 3. Order Submission Flow

**ref: ops manual Section 1.2 - Order State Machine**

```
┌─────────────────────────────────────────────────────────────────┐
│  EYESON FLOW               │  PATTERN FACTORY STATE MACHINE     │
├────────────────────────────┼────────────────────────────────────┤
│  1. Customer completes scan│  S02 (PAID) - Precondition         │
│                            │                                    │
│  2. EYESON calls:          │  → S03 (SCAN_RECEIVED)             │
│     POST /orders           │  → Black Box Pipeline triggered    │
│     {measurements: {...}}  │                                    │
│                            │                                    │
│  3. EYESON polls:          │  → S04 (PROCESSING)                │
│     GET /orders/{id}/status│  → Nesting algorithms running      │
│                            │                                    │
│  4. files_available.plt    │  → S05 (PATTERN_READY)             │
│     === true               │                                    │
│                            │                                    │
│  5. EYESON downloads:      │  → S06 (CUTTING)                   │
│     GET /orders/{id}/plt   │  → Physical cutter queue           │
│                            │                                    │
│  6. Pattern cut complete   │  → S07 (PATTERN_CUT)               │
└────────────────────────────┴────────────────────────────────────┘
```

### 4. Measurement Mapping

**EYESON → Pattern Factory:**

| EYESON Field | Pattern Factory | Description | Type |
|--------------|-----------------|-------------|------|
| `chest_girth` | `Cg` | Chest Girth | Girth |
| `waist_girth` | `Wg` | Waist Girth | Girth |
| `hip_girth` | `Hg` | Hip Girth | Girth |
| `shoulder_width` | `Sh` | Shoulder Width | Linear |
| `arm_length` | `Al` | Arm Length | Linear |
| `back_width` | `Bw` | Back Width | Linear |
| `neck_girth` | `Nc` | Neck Circumference | Girth |
| `bicep_girth` | `Bi` | Bicep Girth | Girth |
| `wrist_girth` | `Wc` | Wrist Circumference | Girth |
| `inseam` | `Il` | Inseam Length | Linear |
| `thigh_girth` | `Th` | Thigh Girth | Girth |
| `knee_girth` | `Kn` | Knee Girth | Girth |
| `calf_girth` | `Ca` | Calf Girth | Girth |

**Complete in:** `src/utils/measurementMapping.ts`

### 5. API Endpoints Used

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/auth/login` | POST | Get JWT tokens | No |
| `/orders` | POST | Submit order | Yes |
| `/orders/{id}` | GET | Get order details | Yes |
| `/orders/{id}/status` | GET | Check status | Yes |
| `/orders/{id}/plt` | GET | Download cutter file | Yes |
| `/orders/{id}/pds` | GET | Download PDS file | Yes |
| `/orders/{id}/dxf` | GET | Download DXF file | Yes |
| `/api/health` | GET | Health check | No |

### 6. File Formats

**ref: ops manual Section 6 - DXF Output Specification**

| Format | Extension | Purpose | Tool |
|--------|-----------|---------|------|
| HPGL | `.plt` | Cutter file | Plotter (Tool 1) |
| PDS | `.pds` | Optitex pattern | Editing |
| DXF | `.dxf` | CAD exchange | CAD software |

**Note:** DXF uses specific layer mapping (ref: ops manual "Holy Grail" spec):
- Layer 1 (Clockwise): Knife cuts
- Layer 14 (CCW): Pen marks
- Layer 13: Drill holes

---

## Configuration

### Environment Variables

Create `.env.local` in frontend directory:

```bash
# Pattern Factory API URL
VITE_PATTERN_FACTORY_URL=http://localhost:8000

# Supabase (if using direct DB access)
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-anon-key

# Default settings
VITE_DEFAULT_GARMENT_TYPE=jacket
VITE_DEFAULT_FIT_TYPE=regular
```

### CORS Configuration

Pattern Factory must allow CORS from EYESON origin:

```python
# backend/src/api/web_api.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # EYESON dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Error Handling

**ref: ops manual Section 7 - Error Handling Standards**

| Error Code | Meaning | Frontend Action |
|------------|---------|-----------------|
| `401` | JWT expired | Auto-refresh token |
| `403` | Insufficient permissions | Show login prompt |
| `422` | Invalid measurements | Show validation errors |
| `500` | Server error | Retry with backoff |
| `SCAN_QUALITY_LOW` | Poor scan quality | Prompt for re-scan |
| `MEASUREMENT_INVALID` | Failed validation | Show manual entry |

---

## Build Notes

### Prerequisites

1. **Pattern Factory Backend Running**
   ```bash
   cd REVERSE-ENGINEER-PDS\production
   docker-compose up -d
   # or
   python src/api/web_api.py
   ```

2. **EYESON Frontend**
   ```bash
   cd eyeson-production\frontend
   npm install
   npm run dev
   ```

### Integration Testing

```bash
# 1. Health check
curl http://localhost:8000/api/health

# 2. Test order submission
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d @test_order.json

# 3. Check status
curl http://localhost:8000/api/v1/orders/{order_id}/status \
  -H "Authorization: Bearer <token>"
```

### Production Deployment

1. **Set production API URL:**
   ```bash
   VITE_PATTERN_FACTORY_URL=https://api.samedaysuits.io
   ```

2. **Enable TLS 1.3** (ref: ops manual Section 2.5)

3. **Configure rate limiting** (100 req/min per IP)

---

## References

| Document | Path | Relevant Sections |
|----------|------|-------------------|
| Operations Manual | `DOCUMENTATION\SUIT_AI_Master_Operations_Manual_v6_7_1.md` | 1.2, 2.5, 2.8, 6, 13 |
| System Architecture | `REVERSE-ENGINEER-PDS\production\docs\SYSTEM_ARCHITECTURE.md` | Full document |
| API Specification | `REVERSE-ENGINEER-PDS\production\src\api\web_api.py` | FastAPI routes |
| Database Schema | `REVERSE-ENGINEER-PDS\production\docs\DATABASE_SCHEMA.md` | Orders table |

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-02-01 | Initial integration spec | EYESON Team |
| 2026-02-01 | Added measurement mapping | EYESON Team |
