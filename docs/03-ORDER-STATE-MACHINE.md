# 03 - Order State Machine

**Document Version:** 1.0  
**Last Updated:** 2026-02-01  
**Reference:** SUIT_AI_Master_Operations_Manual_v6_7_1.md Section 1.2

---

## Table of Contents

1. [Overview](#overview)
2. [State Machine Diagram](#state-machine-diagram)
3. [State Descriptions](#state-descriptions)
4. [EYESON Integration Points](#eyeson-integration-points)
5. [State Transitions](#state-transitions)
6. [Error States & Recovery](#error-states--recovery)
7. [SLA Requirements](#sla-requirements)
8. [Event Log Format](#event-log-format)

---

## Overview

The **27-State Order Machine** governs the complete lifecycle of a bespoke garment order within the SameDaySuits Pattern Factory system. This state machine ensures traceability, quality control, and SLA compliance from order creation through final delivery.

### Key Statistics

| Metric | Value |
|--------|-------|
| Total States | 27 (S01-S22 + 5 substates) |
| Primary States | 22 |
| Substates | 5 (S04a, S05a, S06a, S09a, S10a) |
| Terminal States | 5 (S07, S15, S17, S19, S22) |
| EYESON Trigger States | 2 (S02→S03, S04→S05) |

---

## State Machine Diagram

### ASCII State Flow

```
                                    ┌─────────────────────────────────────┐
                                    │         ORDER LIFECYCLE             │
                                    └─────────────────────────────────────┘

S01 ORDER_CREATED
        │
        │ POST /orders
        ▼
S02 RECEIVED ─────────────────────┐
        │                         │
        │ EYESON POST /orders     │ Manual entry
        ▼                         │
S03 SCAN_RECEIVED                 │
        │                         │
        │ Measurements valid      │
        ▼                         │
S04 PROCESSING ◄─────┐            │
   │  │  │  │        │            │
   │  │  │  │        │ Retry      │
   │  │  │  │        │            │
   ▼  ▼  ▼  ▼        │            │
S04a VALIDATION      │            │
   │                 │            │
   │ Valid           │            │
   ▼                 │            │
S05 PATTERN_READY ◄──┘            │
   │                              │
   │ Auto-submit                  │ Manual submit
   ▼                              │
S06 CUTTING ◄─────┐               │
   │              │               │
   │              │ Queue retry   │
   ▼              │               │
S06a QUEUE_WAIT   │               │
   │              │               │
   │ Cutter ready │               │
   ▼              │               │
S07 PATTERN_CUT ──┘               │
   │                              │
   │ Fabric ready                 │
   ▼                              │
S08 STAGING                       │
   │                              │
   │ QA check                     │
   ▼                              │
S09 QA ◄─────┐                    │
   │         │                    │
   │ Pass    │ Fail               │
   ▼         │                    │
S10 STAGING2─┘                    │
   │                              │
   │ Sewing starts                │
   ▼                              │
S11 SEWING ◄────┐                 │
   │            │                 │
   │ Complete   │ Repair needed   │
   ▼            │                 │
S12 ASSEMBLY    │                 │
   │            │                 │
   │ Complete   │                 │
   ▼            │                 │
S13 FINISHING ◄─┘                 │
   │                              │
   │ Pressed                      │
   ▼                              │
S14 READY_FOR_PICKUP              │
   │                              │
   │ ╔═══════════════════════╗    │
   │ ║   FULFILLMENT PATHS   ║    │
   │ ╚═══════════════════════╝    │
   │                              │
   ├──────► S15 PICKED_UP ────────┤◄────── Customer pickup
   │                              │
   ├──────► S16 SHIPPING ────────┐│
   │         │                   ││
   │         ▼                   ││
   │       S17 DELIVERED ◄───────┘│◄────── Delivery complete
   │                              │
   ├──────► S18 ALTERATIONS ◄────┤
   │         │                   │
   │         ▼                   │
   │       S19 COMPLETED ◄───────┤◄────── Alterations done
   │                              │
   └──────► S20 CANCELLED ───────┤
            │                    │
            ▼                    │
          S21 REFUND_PROCESSING ─┤
            │                    │
            ▼                    │
          S22 CLOSED ◄───────────┘◄────── Refund issued
```

### Mermaid Diagram

```mermaid
stateDiagram-v2
    [*] --> S01: Order Created
    S01 --> S02: POST /orders
    
    S02 --> S03: EYESON Scan
    S02 --> S04: Manual Entry
    
    S03 --> S04: Measurements Valid
    
    S04 --> S04a: Validate
    S04a --> S04: Validation Failed
    S04a --> S05: Validation Pass
    
    S05 --> S06: Auto Submit
    S05 --> S06: Manual Submit
    
    S06 --> S06a: Queue Wait
    S06a --> S06: Retry
    S06a --> S07: Cutter Ready
    
    S07 --> S08: Fabric Ready
    S08 --> S09: QA Check
    
    S09 --> S10: QA Pass
    S09 --> S11: QA Fail (Repair)
    
    S10 --> S11: Sewing Start
    S11 --> S12: Assembly
    S12 --> S13: Finishing
    S13 --> S14: Pressed
    
    S14 --> S15: Customer Pickup
    S14 --> S16: Ship Order
    S14 --> S18: Needs Alterations
    
    S16 --> S17: Delivered
    S18 --> S19: Alterations Done
    
    S14 --> S20: Cancel Order
    S20 --> S21: Process Refund
    S21 --> S22: Refund Issued
    
    S15 --> [*]
    S17 --> [*]
    S19 --> [*]
    S22 --> [*]
```

---

## State Descriptions

### S01 - ORDER_CREATED
**Description:** Initial state when order is first created in system.

| Attribute | Value |
|-----------|-------|
| Entry Action | Generate order ID (SDS-YYYYMMDD-NNNN-R) |
| Exit Action | Log creation timestamp |
| Timeout | None |
| SLA | N/A |

### S02 - RECEIVED
**Description:** Order received by Pattern Factory, awaiting scan data.

| Attribute | Value |
|-----------|-------|
| Entry Action | Validate order structure |
| Exit Action | Assign to processing queue |
| Timeout | 24 hours (auto-cancel if no scan) |
| SLA | N/A |

### S03 - SCAN_RECEIVED
**Description:** EYESON scan submitted with 28 measurements.

| Attribute | Value |
|-----------|-------|
| Entry Action | Validate measurement confidence ≥ 0.85 |
| Exit Action | Store scan metadata |
| Timeout | None |
| SLA | N/A |
| EYESON Trigger | ✅ POST /orders from EYESON |

### S04 - PROCESSING
**Description:** Black Box pipeline processing measurements into patterns.

| Attribute | Value |
|-----------|-------|
| Entry Action | Start Black Box pipeline |
| Exit Action | Generate pattern files |
| Timeout | 5 minutes |
| SLA | < 3 minutes |

### S04a - VALIDATION (Substate)
**Description:** Measurement validation and grading check.

| Attribute | Value |
|-----------|-------|
| Entry Action | Run measurement validation rules |
| Exit Action | Flag issues or approve |
| Timeout | 30 seconds |
| SLA | < 10 seconds |

### S05 - PATTERN_READY
**Description:** Pattern files generated, ready for nesting.

| Attribute | Value |
|-----------|-------|
| Entry Action | Select nesting algorithm |
| Exit Action | Create HPGL output |
| Timeout | None |
| SLA | N/A |
| EYESON Trigger | ✅ Polling returns files_available=true |

### S06 - CUTTING
**Description:** Pattern submitted to cutter queue.

| Attribute | Value |
|-----------|-------|
| Entry Action | Add to resilient queue |
| Exit Action | Send to cutter TCP socket |
| Timeout | 30 minutes |
| SLA | < 15 minutes |

### S06a - QUEUE_WAIT (Substate)
**Description:** Waiting for cutter availability.

| Attribute | Value |
|-----------|-------|
| Entry Action | Check queue position |
| Exit Action | Connect to cutter |
| Timeout | None |
| SLA | < 10 minutes |

### S07 - PATTERN_CUT
**Description:** Fabric successfully cut. **TERMINAL STATE** for cutting phase.

| Attribute | Value |
|-----------|-------|
| Entry Action | Log cut completion |
| Exit Action | Notify staging team |
| Timeout | N/A |
| SLA | N/A |

### S08 - STAGING
**Description:** Cut pieces staged for assembly.

| Attribute | Value |
|-----------|-------|
| Entry Action | Organize pieces by garment |
| Exit Action | Schedule QA |
| Timeout | 2 hours |
| SLA | < 30 minutes |

### S09 - QA
**Description:** Quality assurance inspection.

| Attribute | Value |
|-----------|-------|
| Entry Action | Run QA checklist |
| Exit Action | Pass/fail determination |
| Timeout | 30 minutes |
| SLA | < 15 minutes |

### S10 - STAGING2
**Description:** QA passed, ready for sewing.

| Attribute | Value |
|-----------|-------|
| Entry Action | Assign to tailor |
| Exit Action | Start sewing tracking |
| Timeout | 4 hours |
| SLA | < 1 hour |

### S11 - SEWING
**Description:** Active sewing and construction.

| Attribute | Value |
|-----------|-------|
| Entry Action | Load work order |
| Exit Action | Complete assembly |
| Timeout | 8 hours |
| SLA | < 4 hours |

### S12 - ASSEMBLY
**Description:** Final assembly and detail work.

| Attribute | Value |
|-----------|-------|
| Entry Action | Attach hardware, buttons |
| Exit Action | Move to finishing |
| Timeout | 4 hours |
| SLA | < 2 hours |

### S13 - FINISHING
**Description:** Pressing, steaming, final touches.

| Attribute | Value |
|-----------|-------|
| Entry Action | Steam press garment |
| Exit Action | Final inspection |
| Timeout | 2 hours |
| SLA | < 1 hour |

### S14 - READY_FOR_PICKUP
**Description:** Garment complete, awaiting fulfillment.

| Attribute | Value |
|-----------|-------|
| Entry Action | Package garment |
| Exit Action | Hand to customer/ship |
| Timeout | 48 hours |
| SLA | < 24 hours |

### S15 - PICKED_UP
**Description:** Customer collected garment. **TERMINAL STATE**.

### S16 - SHIPPING
**Description:** In transit to customer.

| Attribute | Value |
|-----------|-------|
| Entry Action | Generate shipping label |
| Exit Action | Update tracking |
| Timeout | 7 days |
| SLA | Per carrier SLA |

### S17 - DELIVERED
**Description:** Delivered to customer. **TERMINAL STATE**.

### S18 - ALTERATIONS
**Description:** Customer requested modifications.

| Attribute | Value |
|-----------|-------|
| Entry Action | Document alteration request |
| Exit Action | Schedule rework |
| Timeout | 14 days |
| SLA | < 7 days |

### S19 - COMPLETED
**Description:** Alterations complete. **TERMINAL STATE**.

### S20 - CANCELLED
**Description:** Order cancelled by customer or system.

### S21 - REFUND_PROCESSING
**Description:** Refund being processed.

### S22 - CLOSED
**Description:** Order closed, refund issued. **TERMINAL STATE**.

---

## EYESON Integration Points

### Trigger 1: S02 → S03 (Order Submission)

When EYESON submits a scan, it triggers the transition from RECEIVED to SCAN_RECEIVED.

```typescript
// EYESON Frontend: patternFactoryApi.ts
async createOrder(measurements: PFMeasurements, config: GarmentConfig) {
  const orderData = {
    order_id: this.generateOrderId(),  // SDS-YYYYMMDD-NNNN-R
    customer_id: config.customerId,
    garment_type: config.garmentType,   // jacket, trousers, etc.
    fit_type: config.fitType,           // slim, regular, classic
    measurements: measurements,         // { Cg: {value, unit, confidence}, ... }
    priority: "normal"
  };
  
  // POST triggers S02 → S03
  const response = await this.post('/orders', orderData);
  return response.order_id;  // Returns new order ID
}
```

**API Request:**
```http
POST /orders HTTP/1.1
Host: pattern-factory:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "order_id": "SDS-20260201-0001-A",
  "customer_id": "cust_12345",
  "garment_type": "jacket",
  "fit_type": "regular",
  "measurements": {
    "Cg": { "value": 102.5, "unit": "cm", "confidence": 0.95 },
    "Wg": { "value": 88.0, "unit": "cm", "confidence": 0.92 },
    "Hg": { "value": 98.5, "unit": "cm", "confidence": 0.94 }
  }
}
```

### Trigger 2: S04 → S05 (Pattern Ready Polling)

EYESON polls the order status until files are available.

```typescript
// EYESON Frontend: patternFactoryApi.ts
async pollUntilReady(orderId: string, timeoutMs = 120000) {
  const interval = 2000;  // 2 seconds
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeoutMs) {
    const status = await this.getOrderStatus(orderId);
    
    // Check if pattern is ready (S05)
    if (status.state === 'S05' && status.files_available?.plt) {
      return status;
    }
    
    await this.delay(interval);
  }
  
  throw new Error('Timeout waiting for pattern generation');
}
```

**API Request:**
```http
GET /orders/SDS-20260201-0001-A/status HTTP/1.1
Host: pattern-factory:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (S05 - PATTERN_READY):**
```json
{
  "order_id": "SDS-20260201-0001-A",
  "state": "S05",
  "state_name": "PATTERN_READY",
  "files_available": {
    "plt": true,
    "pds": true,
    "dxf": true
  },
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-01T10:02:30Z",
  "processing_time_seconds": 150
}
```

---

## State Transitions

### Transition Matrix

| From | To | Trigger | Timeout | Auto-Retry |
|------|-----|---------|---------|------------|
| S01 | S02 | POST /orders | - | No |
| S02 | S03 | EYESON Scan | 24h | No |
| S02 | S04 | Manual Entry | - | No |
| S03 | S04 | Validation Pass | - | No |
| S04 | S04a | Start Validation | 5m | Yes (3x) |
| S04a | S05 | Validation OK | 30s | No |
| S04a | S04 | Validation Fail | - | Yes |
| S05 | S06 | Submit to Queue | - | No |
| S06 | S06a | Queue Full | 30m | Yes |
| S06a | S06 | Retry | - | Yes (exponential) |
| S06a | S07 | Cutter Ready | 10m | No |
| S06 | S07 | Direct Cut | - | No |
| S07 | S08 | Fabric Ready | - | No |
| S08 | S09 | QA Scheduled | 2h | No |
| S09 | S10 | QA Pass | 30m | No |
| S09 | S11 | QA Fail | - | No |
| S10 | S11 | Start Sewing | 4h | No |
| S11 | S12 | Assembly | 8h | No |
| S12 | S13 | Finishing | 4h | No |
| S13 | S14 | Pressed | 2h | No |
| S14 | S15 | Pickup | 48h | No |
| S14 | S16 | Ship | - | No |
| S14 | S18 | Alterations | - | No |
| S16 | S17 | Delivered | 7d | No |
| S18 | S19 | Complete | 14d | No |
| S14 | S20 | Cancel | - | No |
| S20 | S21 | Refund | - | No |
| S21 | S22 | Closed | - | No |

---

## Error States & Recovery

### Validation Errors (S04a)

| Error Code | Description | Recovery Action |
|------------|-------------|-----------------|
| E4001 | Low confidence measurement | Request rescan |
| E4002 | Out of range value | Manual correction |
| E4003 | Missing required measurement | Request rescan |
| E4004 | Invalid garment type | Reject order |
| E4005 | Ratio validation failed | Flag for review |

### Processing Errors (S04)

| Error Code | Description | Recovery Action |
|------------|-------------|-----------------|
| E5001 | Black Box timeout | Retry with timeout 2x |
| E5002 | Nesting failure | Try alternative algorithm |
| E5003 | HPGL generation failed | Retry with debug logging |

### Cutter Errors (S06)

| Error Code | Description | Recovery Action |
|------------|-------------|-----------------|
| E6001 | Cutter offline | Queue and retry |
| E6002 | TCP connection failed | Retry exponential backoff |
| E6003 | HPGL parse error | Regenerate PLT file |

### Recovery Procedures

```python
# Pseudo-code for state recovery
def recover_from_error(order_id: str, error_code: str):
    error_config = ERROR_HANDLING[error_code]
    
    if error_config.retryable:
        for attempt in range(error_config.max_retries):
            try:
                transition_state(order_id, error_config.recovery_state)
                return RecoveryResult.SUCCESS
            except Exception as e:
                wait(exponential_backoff(attempt))
    
    if error_config.manual_intervention:
        flag_for_manual_review(order_id)
        notify_ops_team(order_id, error_code)
        return RecoveryResult.MANUAL_REVIEW
    
    return RecoveryResult.FAILED
```

---

## SLA Requirements

### Timing Requirements by State

| State | Max Duration | Target Duration | Alert Threshold |
|-------|--------------|-----------------|-----------------|
| S04 (Processing) | 5 min | 3 min | 4 min |
| S04a (Validation) | 30 sec | 10 sec | 20 sec |
| S06 (Cutting) | 30 min | 15 min | 20 min |
| S06a (Queue Wait) | ∞ | 10 min | 15 min |
| S08 (Staging) | 2 hours | 30 min | 1 hour |
| S09 (QA) | 30 min | 15 min | 20 min |
| S10 (Staging2) | 4 hours | 1 hour | 2 hours |
| S11 (Sewing) | 8 hours | 4 hours | 6 hours |
| S12 (Assembly) | 4 hours | 2 hours | 3 hours |
| S13 (Finishing) | 2 hours | 1 hour | 1.5 hours |
| S14 (Ready) | 48 hours | 24 hours | 36 hours |

### EYESON-Specific SLAs

| Metric | Target | Maximum |
|--------|--------|---------|
| Scan to Order Submission | < 2 min | 5 min |
| Order Submission to S03 | < 1 sec | 5 sec |
| S03 to S05 (Pattern Ready) | < 3 min | 5 min |
| File Download | < 5 sec | 30 sec |
| Total Scan-to-Files | < 5 min | 10 min |

---

## Event Log Format

### Event Log Schema

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440000",
  "order_id": "SDS-20260201-0001-A",
  "timestamp": "2026-02-01T10:00:00.000Z",
  "event_type": "STATE_CHANGE",
  "from_state": "S02",
  "to_state": "S03",
  "trigger": "EYESON_SCAN_RECEIVED",
  "metadata": {
    "customer_id": "cust_12345",
    "garment_type": "jacket",
    "measurement_count": 28,
    "confidence_avg": 0.93,
    "source_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  },
  "processing_time_ms": 1500
}
```

### Event Types

| Event Type | Description | Fields |
|------------|-------------|--------|
| `STATE_CHANGE` | Order transitioned states | from_state, to_state, trigger |
| `MEASUREMENT_RECEIVED` | EYESON scan submitted | measurement_count, confidence |
| `FILE_GENERATED` | Pattern file created | file_type, file_size, checksum |
| `CUTTER_SUBMITTED` | Order sent to cutter | cutter_id, queue_position |
| `CUTTER_COMPLETE` | Fabric cut successfully | cut_duration, piece_count |
| `ERROR_OCCURRED` | Processing error | error_code, error_message, retry_count |
| `MANUAL_INTERVENTION` | Ops team action | action_type, operator_id |

---

## Next Steps

1. **Reference** [04-API-REFERENCE.md](./04-API-REFERENCE.md) for endpoint details
2. **Review** [05-SECURITY-AUTH.md](./05-SECURITY-AUTH.md) for authentication flows
3. **Check** [06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md) for error handling

---

*For detailed API implementation, see `pattern-factory/src/api/web_api.py` and `eyeson/frontend/src/services/patternFactoryApi.ts`*
