# INTEGRATION ARCHITECTURE

**EYESON Scanner ↔ Pattern Factory Integration Specification**

**Document Version:** 1.0  
**Last Updated:** 2026-02-01  
**Reference:** SUIT_AI_Master_Operations_Manual_v6_7_1.md Sections 1.2, 2.5, 2.8, 13

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Context](#system-context)
3. [Data Flow Architecture](#data-flow-architecture)
4. [API Contract Specification](#api-contract-specification)
5. [Measurement Transformation](#measurement-transformation)
6. [State Machine Integration](#state-machine-integration)
7. [Security Architecture](#security-architecture)
8. [Error Handling Matrix](#error-handling-matrix)
9. [Performance Requirements](#performance-requirements)
10. [Sequence Diagrams](#sequence-diagrams)

---

## Executive Summary

This document provides comprehensive technical specification for the integration between **EYESON** (browser-based body scanning) and **Pattern Factory** (automated pattern generation). The integration enables a complete **scan-to-cutter** workflow in under 5 minutes.

### Key Integration Metrics

| Metric | Value | SLA |
|--------|-------|-----|
| End-to-End Time | < 5 minutes | 99th percentile |
| Measurement Accuracy (P0) | ±0.5-1cm | 95% pass rate |
| Measurement Accuracy (P1) | ±1-2cm | 90% pass rate |
| API Response Time | < 100ms | p95 |
| Pattern Generation | < 3 minutes | 99th percentile |
| Cutter Queue Time | < 10 minutes | Average |

---

## System Context

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION CONTEXT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐              ┌──────────────┐              ┌───────────┐ │
│   │   EXTERNAL   │              │   EYESON     │              │  PATTERN  │ │
│   │   SYSTEMS    │              │   SCANNER    │              │  FACTORY  │ │
│   └──────┬───────┘              └──────┬───────┘              └─────┬─────┘ │
│          │                             │                            │       │
│          │                             │ ◄─── INTEGRATION LAYER ───►│       │
│          │                             │                            │       │
│   ┌──────┴───────┐              ┌──────┴───────┐              ┌─────┴─────┐ │
│   │              │              │              │              │           │ │
│   │ • Stripe     │              │ • MediaPipe  │              │ • Nesting │ │
│   │ • SendGrid   │              │ • Kokoro TTS │              │ • HPGL    │ │
│   │ • Cloudflare │              │ • React 18   │              │ • Queue   │ │
│   │              │              │              │              │           │ │
│   └──────────────┘              └──────────────┘              └───────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Integration Boundaries

| Boundary | EYESON Responsibility | Pattern Factory Responsibility |
|----------|----------------------|--------------------------------|
| **Data** | 28 measurements, scan metadata | Order state, pattern files |
| **Auth** | Token storage, refresh logic | Token issuance, validation |
| **State** | Poll for completion | State transitions, persistence |
| **Files** | Download PLT/PDS/DXF | Generate, store, serve files |

---

## Data Flow Architecture

### Complete Data Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ CUSTOMER│───▶│ EYESON  │───▶│   PF    │───▶│NESTING  │───▶│  HPGL   │───▶│ CUTTER  │
│ BROWSER │    │ BACKEND │    │   API   │    │ ENGINE  │    │  GEN    │    │ QUEUE   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │              │              │
     │ 90s Video    │ 33 Landmarks │ 28 Measures  │ 8 Algorithms │ PLT File     │ TCP 9100
     │ Capture      │ Extract      │ Validate     │ Optimize     │ Generate     │ Send
     │              │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼              ▼
  Timeline:    0-90s          90-95s         95-120s       120-180s       180-300s
```

### Data Flow by Stage

| Stage | Duration | System | Action | Output |
|-------|----------|--------|--------|--------|
| 1. Video Capture | 90s | EYESON Frontend | MediaPipe pose detection | 33 landmarks/frame |
| 2. Measurement Extraction | 5s | EYESON Backend | Calculate 28 measurements | Measurement set |
| 3. Order Submission | 1s | EYESON Backend | POST /orders | Order ID |
| 4. State Transition | <1s | Pattern Factory | S02→S03 | Acknowledgment |
| 5. Validation | 10s | Pattern Factory | S03→S04a→S04 | Validated order |
| 6. Black Box Pipeline | 90s | Pattern Factory | Generate patterns | PDS files |
| 7. Nesting | 60s | Pattern Factory | Optimize layout | Nesting result |
| 8. HPGL Generation | 5s | Pattern Factory | Create PLT | Cutter file |
| 9. State Update | <1s | Pattern Factory | S04→S05 | Files available |
| 10. File Download | 5s | EYESON Frontend | GET /plt, /pds, /dxf | Local files |

---

## API Contract Specification

### 1. Order Submission

**Endpoint:** `POST /orders`  
**Source:** EYESON Backend → Pattern Factory  
**Trigger:** Customer completes scan

#### Request Schema

```typescript
interface CreateOrderRequest {
  order_id: string;           // Format: SDS-YYYYMMDD-NNNN-R
  customer_id: string;        // EYESON session ID or customer ID
  garment_type: 'jacket' | 'trousers' | 'shirt' | 'waistcoat' | 'suit';
  fit_type: 'slim' | 'regular' | 'classic';
  measurements: {
    // Primary (P0) - All required
    Cg: MeasurementValue;     // Chest Girth
    Wg: MeasurementValue;     // Waist Girth
    Hg: MeasurementValue;     // Hip Girth
    Sh: MeasurementValue;     // Shoulder Width
    Al: MeasurementValue;     // Arm Length
    Il: MeasurementValue;     // Inseam
    Nc: MeasurementValue;     // Neck Girth
    Bg: MeasurementValue;     // Bicep Girth
    Wr: MeasurementValue;     // Wrist Girth
    Tg: MeasurementValue;     // Thigh Girth
    Kg: MeasurementValue;     // Knee Girth
    Ca: MeasurementValue;     // Calf Girth
    Bw: MeasurementValue;     // Back Width
    
    // Secondary (P1) - Optional but recommended
    Fwl?: MeasurementValue;   // Front Waist Length
    Bwl?: MeasurementValue;   // Back Waist Length
    // ... 13 more secondary
  };
  scan_metadata?: {
    device_type: 'photogrammetry' | 'lidar' | 'video';
    vertex_count: number;
    capture_duration_seconds: number;
    confidence_avg: number;
  };
  priority?: 'normal' | 'high' | 'rush';
}

interface MeasurementValue {
  value: number;              // Rounded to 1 decimal
  unit: 'cm';                // Always cm
  confidence: number;        // 0.0 - 1.0
}
```

#### Example Request

```json
{
  "order_id": "SDS-20260201-0042-A",
  "customer_id": "eyeson_session_550e8400",
  "garment_type": "jacket",
  "fit_type": "regular",
  "measurements": {
    "Cg": { "value": 102.5, "unit": "cm", "confidence": 0.95 },
    "Wg": { "value": 88.0, "unit": "cm", "confidence": 0.92 },
    "Hg": { "value": 98.5, "unit": "cm", "confidence": 0.94 },
    "Sh": { "value": 46.0, "unit": "cm", "confidence": 0.91 },
    "Al": { "value": 64.5, "unit": "cm", "confidence": 0.93 },
    "Il": { "value": 82.0, "unit": "cm", "confidence": 0.90 },
    "Nc": { "value": 41.0, "unit": "cm", "confidence": 0.94 },
    "Bg": { "value": 34.0, "unit": "cm", "confidence": 0.88 },
    "Wr": { "value": 17.5, "unit": "cm", "confidence": 0.95 },
    "Tg": { "value": 58.0, "unit": "cm", "confidence": 0.87 },
    "Kg": { "value": 40.0, "unit": "cm", "confidence": 0.89 },
    "Ca": { "value": 38.0, "unit": "cm", "confidence": 0.88 },
    "Bw": { "value": 38.5, "unit": "cm", "confidence": 0.90 }
  },
  "scan_metadata": {
    "device_type": "photogrammetry",
    "vertex_count": 6890,
    "capture_duration_seconds": 90,
    "confidence_avg": 0.91
  },
  "priority": "normal"
}
```

#### Response Schema

```typescript
interface CreateOrderResponse {
  order_id: string;
  state: 'S02' | 'S03' | 'S04';
  state_name: string;
  created_at: string;         // ISO 8601
  estimated_completion: string; // ISO 8601
  queue_position?: number;
}
```

#### Example Response (200 OK)

```json
{
  "order_id": "SDS-20260201-0042-A",
  "state": "S03",
  "state_name": "SCAN_RECEIVED",
  "created_at": "2026-02-01T14:30:00Z",
  "estimated_completion": "2026-02-01T14:33:00Z",
  "queue_position": 3
}
```

#### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | E4001 | Invalid measurement value |
| 400 | E4002 | Missing required measurement |
| 400 | E4003 | Invalid garment type |
| 401 | E4011 | Invalid or expired token |
| 403 | E4031 | Insufficient permissions |
| 409 | E4091 | Order ID already exists |
| 422 | E4221 | Measurement validation failed |
| 429 | E4291 | Rate limit exceeded |
| 500 | E5001 | Internal server error |

---

### 2. Status Polling

**Endpoint:** `GET /orders/{order_id}/status`  
**Source:** EYESON Frontend → Pattern Factory  
**Trigger:** Every 2 seconds until completion

#### Request

```http
GET /orders/SDS-20260201-0042-A/status HTTP/1.1
Host: pattern-factory:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json
```

#### Response Schema

```typescript
interface OrderStatusResponse {
  order_id: string;
  state: string;              // S01-S22
  state_name: string;
  state_description: string;
  files_available: {
    plt: boolean;            // HPGL cutter file
    pds: boolean;            // Optitex PDS file
    dxf: boolean;            // DXF CAD file
  };
  progress_percent: number;   // 0-100
  queue_position?: number;    // If in queue
  processing_time_seconds?: number;
  estimated_completion?: string;
  created_at: string;
  updated_at: string;
  error?: {
    code: string;
    message: string;
    retryable: boolean;
  };
}
```

#### Example Responses

**S04 - PROCESSING:**
```json
{
  "order_id": "SDS-20260201-0042-A",
  "state": "S04",
  "state_name": "PROCESSING",
  "state_description": "Generating pattern from measurements",
  "files_available": { "plt": false, "pds": false, "dxf": false },
  "progress_percent": 45,
  "processing_time_seconds": 75,
  "estimated_completion": "2026-02-01T14:32:45Z",
  "created_at": "2026-02-01T14:30:00Z",
  "updated_at": "2026-02-01T14:31:15Z"
}
```

**S05 - PATTERN_READY:**
```json
{
  "order_id": "SDS-20260201-0042-A",
  "state": "S05",
  "state_name": "PATTERN_READY",
  "state_description": "Pattern generated and ready for download",
  "files_available": { "plt": true, "pds": true, "dxf": true },
  "progress_percent": 100,
  "processing_time_seconds": 142,
  "created_at": "2026-02-01T14:30:00Z",
  "updated_at": "2026-02-01T14:32:22Z"
}
```

---

### 3. File Downloads

**Endpoints:**
- `GET /orders/{order_id}/plt` - HPGL cutter file
- `GET /orders/{order_id}/pds` - Optitex PDS file
- `GET /orders/{order_id}/dxf` - DXF CAD file

#### Request

```http
GET /orders/SDS-20260201-0042-A/plt HTTP/1.1
Host: pattern-factory:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response

**Success (200 OK):**
```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="SDS-20260201-0042-A.plt"
Content-Length: 15234

[Binary HPGL data]
```

**Error (404 Not Ready):**
```json
{
  "error": "E4041",
  "message": "PLT file not yet generated",
  "state": "S04",
  "retry_after": 30
}
```

---

## Measurement Transformation

### Transformation Flow

```
EYESON Raw Measurements          Pattern Factory Format
─────────────────────           ─────────────────────
chest_girth: 102.5 cm     ───▶   Cg: {value: 102.5, unit: 'cm', confidence: 0.95}
waist_girth: 88.0 cm      ───▶   Wg: {value: 88.0, unit: 'cm', confidence: 0.92}
hip_girth: 98.5 cm        ───▶   Hg: {value: 98.5, unit: 'cm', confidence: 0.94}
shoulder_width: 46.0 cm   ───▶   Sh: {value: 46.0, unit: 'cm', confidence: 0.91}
...                              ...
```

### TypeScript Implementation

```typescript
// eyeson/frontend/src/utils/measurementMapping.ts

const MEASUREMENT_CODES: Record<string, string> = {
  // Primary (P0)
  chest_girth: 'Cg',
  waist_girth: 'Wg',
  hip_girth: 'Hg',
  shoulder_width: 'Sh',
  arm_length: 'Al',
  inseam: 'Il',
  neck_girth: 'Nc',
  bicep_girth: 'Bg',
  wrist_girth: 'Wr',
  thigh_girth: 'Tg',
  knee_girth: 'Kg',
  calf_girth: 'Ca',
  back_width: 'Bw',
  
  // Secondary (P1)
  front_waist_length: 'Fwl',
  back_waist_length: 'Bwl',
  // ... etc
};

export function transformToPatternFactory(
  eyeson: EyesonMeasurements
): PFMeasurements {
  const result: PFMeasurements = {};
  
  for (const [key, measurement] of Object.entries(eyeson)) {
    const code = MEASUREMENT_CODES[key];
    if (!code) continue;
    
    result[code] = {
      value: parseFloat(measurement.value.toFixed(1)),
      unit: 'cm',
      confidence: parseFloat(measurement.confidence.toFixed(2))
    };
  }
  
  return result;
}
```

---

## State Machine Integration

### EYESON Integration Points

```mermaid
sequenceDiagram
    participant E as EYESON Frontend
    participant B as EYESON Backend
    participant P as Pattern Factory
    participant Q as Cutter Queue
    participant C as Jindex Cutter

    E->>E: 90s Video Capture
    E->>E: MediaPipe: 33 landmarks
    E->>B: Upload video
    B->>B: Extract 28 measurements
    B->>B: Transform to PF format
    B->>P: POST /orders
    activate P
    P->>P: S02 → S03 (SCAN_RECEIVED)
    P-->>B: 201 Created + order_id
    deactivate P
    
    B-->>E: Order submitted
    
    loop Poll every 2 seconds
        E->>P: GET /orders/{id}/status
        P-->>E: S04 (PROCESSING)
    end
    
    P->>P: S04 → S04a (VALIDATION)
    P->>P: S04a → S04 (PROCESSING)
    P->>P: Black Box pipeline
    P->>P: Nesting algorithm
    P->>P: S04 → S05 (PATTERN_READY)
    
    E->>P: GET /orders/{id}/status
    P-->>E: S05 + files_available=true
    
    E->>P: GET /orders/{id}/plt
    P-->>E: HPGL file
    
    E->>P: GET /orders/{id}/pds
    P-->>E: PDS file
    
    P->>Q: Auto-submit to queue
    Q->>C: TCP socket (port 9100)
    C-->>Q: Cut complete
    Q->>P: S05 → S06 (CUTTING)
    P->>P: S06 → S07 (PATTERN_CUT)
```

### State Transitions

| Transition | Trigger | EYESON Action |
|------------|---------|---------------|
| S02 → S03 | POST /orders | Submit measurements |
| S03 → S04 | Validation pass | Continue polling |
| S04 → S05 | Pattern ready | Stop polling, enable downloads |
| S05 → S06 | Auto-submit | N/A |
| S06 → S07 | Cutter complete | N/A |

---

## Security Architecture

### Authentication Flow

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   EYESON     │         │  PATTERN FACTORY │         │   REDIS      │
│   FRONTEND   │         │     BACKEND      │         │   CACHE      │
└──────┬───────┘         └────────┬─────────┘         └──────┬───────┘
       │                          │                          │
       │ POST /auth/login         │                          │
       │ {email, password}        │                          │
       │─────────────────────────▶│                          │
       │                          │                          │
       │                          │ Verify credentials       │
       │                          │ (bcrypt check)           │
       │                          │                          │
       │                          │ Generate JWT             │
       │                          │ {access, refresh, exp}   │
       │                          │                          │
       │ 200 OK                   │                          │
       │ {access_token, ...}      │                          │
       │◀─────────────────────────│                          │
       │                          │                          │
       │ Store in memory          │                          │
       │ (sessionStorage)         │                          │
       │                          │                          │
       │ Subsequent requests:     │                          │
       │ Authorization: Bearer    │                          │
       │ {access_token}           │                          │
       │─────────────────────────▶│                          │
       │                          │                          │
       │                          │ Validate JWT             │
       │                          │ Check signature + exp    │
       │                          │                          │
       │                          │ Check Redis (not revoked)│
       │                          │─────────────────────────▶│
       │                          │◀─────────────────────────│
       │                          │                          │
       │ 200 OK + Data            │                          │
       │◀─────────────────────────│                          │
```

### Security Controls

| Control | Implementation | Reference |
|---------|---------------|-----------|
| JWT Expiry | 1 hour | Ops Manual 2.5 |
| Token Refresh | 5 min before expiry | Best Practice |
| CORS | Whitelist origins | Ops Manual 2.5 |
| Rate Limit | 100 req/min | Ops Manual 2.5 |
| TLS | 1.3 only | Ops Manual 2.5 |
| Secrets | Environment variables | 12-Factor |

---

## Error Handling Matrix

### Error Categories

| Category | EYESON Handling | Pattern Factory Handling |
|----------|-----------------|-------------------------|
| **Auth Errors** | Redirect to login, clear tokens | Return 401, log attempt |
| **Validation Errors** | Show inline errors, allow retry | Return 422 with details |
| **Timeout Errors** | Show "still processing" | Return 202, continue async |
| **Cutter Errors** | Show queue status | Queue and retry |
| **Network Errors** | Exponential backoff | Log and alert |

### Specific Error Handling

```typescript
// EYESON Frontend error handling
class APIError extends Error {
  constructor(
    public code: string,
    message: string,
    public retryable: boolean,
    public status: number
  ) {
    super(message);
  }
}

async function handleAPIError(error: APIError): Promise<void> {
  switch (error.code) {
    case 'E4011': // Token expired
      await refreshToken();
      break;
      
    case 'E4001': // Invalid measurement
      showInlineError(error.message);
      break;
      
    case 'E5001': // Server error
      if (error.retryable) {
        await retryWithBackoff();
      } else {
        showErrorModal(error.message);
      }
      break;
      
    case 'E4291': // Rate limit
      await sleep(parseInt(error.retryAfter) * 1000);
      break;
      
    default:
      logError(error);
      showGenericError();
  }
}
```

---

## Performance Requirements

### Timing Requirements

| Operation | Target | Maximum | Measurement |
|-----------|--------|---------|-------------|
| JWT Validation | < 10ms | 50ms | API Gateway |
| Order Creation | < 100ms | 500ms | EYESON → PF |
| Status Poll | < 50ms | 200ms | Frontend → PF |
| File Download | < 5s | 30s | PF → Frontend |
| Pattern Generation | < 3min | 5min | S03 → S05 |
| Total Scan-to-Files | < 5min | 10min | End-to-end |

### Resource Requirements

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| EYESON Frontend | Client | 100MB | N/A |
| EYESON Backend | 0.5 cores | 512MB | 1GB |
| Pattern Factory | 2 cores | 4GB | 10GB |
| Nesting Worker | 4 cores | 8GB | 5GB |
| Redis | 0.5 cores | 1GB | 5GB |
| PostgreSQL | 1 core | 2GB | 50GB |

---

## Sequence Diagrams

### 1. Complete Scan-to-Cutter Flow

```mermaid
sequenceDiagram
    autonumber
    actor C as Customer
    participant F as EYESON Frontend
    participant B as EYESON Backend
    participant TTS as Kokoro TTS
    participant P as Pattern Factory
    participant BB as Black Box
    participant N as Nesting Engine
    participant Q as Cutter Queue
    participant J as Jindex Cutter

    C->>F: Open browser
    F->>F: Load MediaPipe
    
    F->>TTS: GET /voice/prompts/en
    TTS-->>F: Voice prompts
    
    C->>F: Click "Start Scan"
    F->>TTS: POST /voice/synthesize<br/>"Please stand in frame"
    TTS-->>F: Audio stream
    F->>C: Play voice guidance
    
    C->>F: Position body
    F->>F: MediaPipe detect pose
    F->>C: Show skeleton overlay
    
    F->>TTS: POST /voice/synthesize<br/>"Rotate slowly"
    TTS-->>F: Audio
    
    C->>F: Rotate 360°
    F->>F: Record 90s video
    
    F->>B: POST /sessions/{id}/upload
    B->>B: Extract 33 landmarks
    B->>B: Calculate 28 measurements
    B-->>F: Session complete
    
    F->>B: GET /measurements/{id}
    B-->>F: 28 measurements
    
    F->>F: Show results screen
    C->>F: Submit to Pattern Factory
    
    F->>B: Submit order
    B->>B: transformToPatternFactory()
    B->>P: POST /orders
    P->>P: S02 → S03
    P-->>B: 201 Created
    B-->>F: Order submitted
    
    F->>C: Show "Processing..."
    
    loop Poll every 2s
        F->>P: GET /orders/{id}/status
        P-->>F: S04 (PROCESSING)
    end
    
    P->>BB: Generate pattern
    BB-->>P: PDS file
    
    P->>N: Run nesting
    N-->>P: Optimized layout
    
    P->>P: Generate HPGL
    P->>P: S04 → S05
    
    F->>P: GET /orders/{id}/status
    P-->>F: S05 (PATTERN_READY)<br/>files_available=true
    
    F->>C: Show "Download Ready"
    
    C->>F: Download files
    F->>P: GET /orders/{id}/plt
    P-->>F: HPGL file
    F->>P: GET /orders/{id}/pds
    P-->>F: PDS file
    F->>C: Save files locally
    
    P->>Q: Auto-submit to cutter
    Q->>J: Send via TCP:9100
    J->>J: Cut fabric
    J-->>Q: Complete
    Q->>P: Update status
    P->>P: S05 → S06 → S07
```

### 2. Error Recovery Flow

```mermaid
sequenceDiagram
    participant F as EYESON Frontend
    participant B as EYESON Backend
    participant P as Pattern Factory
    participant Q as Cutter Queue

    F->>B: POST /orders
    B->>P: POST /orders
    
    alt Network Error
        P--xB: Connection timeout
        B->>B: Retry (3x, exponential)
        B->>P: POST /orders
        P-->>B: 201 Created
    end
    
    B-->>F: Order created
    
    loop Poll
        F->>P: GET /status
        
        alt Token Expired
            P-->>F: 401 Unauthorized
            F->>P: POST /auth/refresh
            P-->>F: New access_token
            F->>P: GET /status (retry)
        end
        
        P-->>F: S04 (PROCESSING)
    end
    
    P->>P: Generate pattern
    
    alt Generation Failed
        P->>P: Log error
        P->>P: Retry with algorithm B
        P->>P: Success
    end
    
    P->>Q: Submit to cutter
    
    alt Cutter Offline
        Q->>Q: Queue job
        Q->>Q: Retry every 30s
        Q->>P: Cutter connected
        Q->>P: Send job
    end
    
    P-->>F: S07 (PATTERN_CUT)
```

---

## Appendix: Configuration

### Environment Variables

```bash
# EYESON Configuration
EYESON_API_PORT=8001
EYESON_API_HOST=0.0.0.0
EYESON_SECRET_KEY=your-secret-key

# TTS Configuration
TTS_MODEL=kokoro-82m
TTS_FALLBACK=piper
TTS_CACHE_DIR=/app/cache/tts

# Pattern Factory Configuration
PATTERN_FACTORY_URL=http://localhost:8000
PATTERN_FACTORY_API_KEY=your-api-key

# Cutter Configuration
CUTTER_IP=192.168.1.100
CUTTER_PORT=9100
CUTTER_AUTO_SUBMIT=true

# Shared Infrastructure
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/samedaysuits
```

---

*For questions or issues, refer to [06-TROUBLESHOOTING.md](./docs/06-TROUBLESHOOTING.md)*
