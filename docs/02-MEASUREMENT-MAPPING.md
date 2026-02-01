# 02 - Measurement Mapping Specification

**Document Version:** 1.0  
**Last Updated:** 2026-02-01  
**Reference:** SUIT_AI_Master_Operations_Manual_v6_7_1.md Section 13 - Database

---

## Table of Contents

1. [Overview](#overview)
2. [Measurement Categories](#measurement-categories)
3. [Complete Mapping Table](#complete-mapping-table)
4. [Confidence Thresholds](#confidence-thresholds)
5. [Size Grading](#size-grading)
6. [Validation Rules](#validation-rules)
7. [Transformation Code](#transformation-code)

---

## Overview

The PRODUCTION-SCANNER system extracts **28 body measurements** from the EYESON 90-second scan and transforms them into Pattern Factory format using standardized measurement codes.

### Key Statistics

| Metric | Value |
|--------|-------|
| Total Measurements | 28 |
| Primary (P0) | 13 |
| Secondary (P1) | 15 |
| Measurement Accuracy | ±0.5-1cm (P0), ±1-2cm (P1) |
| Confidence Threshold (P0) | ≥ 0.90 |
| Confidence Threshold (P1) | ≥ 0.85 |

---

## Measurement Categories

### Primary Measurements (P0)

Critical measurements for pattern generation with ±1cm tolerance:

1. **Chest Girth (Cg)** - Primary circumference measurement
2. **Waist Girth (Wg)** - Narrowest torso point
3. **Hip Girth (Hg)** - Widest hip point
4. **Shoulder Width (Sh)** - Shoulder-to-shoulder across back
5. **Arm Length (Al)** - Shoulder to wrist
6. **Inseam Length (Il)** - Crotch to ankle
7. **Neck Girth (Nc)** - Base of neck circumference
8. **Bicep Girth (Bg)** - Upper arm circumference
9. **Wrist Girth (Wr)** - Wrist circumference
10. **Thigh Girth (Tg)** - Upper thigh circumference
11. **Knee Girth (Kg)** - Knee circumference
12. **Calf Girth (Ca)** - Calf circumference
13. **Back Width (Bw)** - Across back measurement

### Secondary Measurements (P1)

Additional measurements for refined fit with ±2cm tolerance:

14. **Front Waist Length** - Shoulder to waist (front)
15. **Back Waist Length** - Shoulder to waist (back)
16. **Front Shoulder Width** - Shoulder width (front)
17. **Sleeve Inseam** - Armpit to wrist
18. **Crotch Depth** - Waist to crotch
19. **Outseam** - Waist to ankle (side)
20. **Front Hip Depth** - Waist to hip (front)
21. **Back Hip Depth** - Waist to hip (back)
22. **Waist to Knee** - Waist to knee length
23. **Waist to Ankle** - Waist to ankle length
24. **Shoulder Drop** - Shoulder slope measurement
25. **Chest Width** - Chest width (front)
26. **Waist Width** - Waist width (front)
27. **Hip Width** - Hip width (front)
28. **Jacket Length** - Base of neck to hem

---

## Complete Mapping Table

### Primary Measurements (P0 - ±1cm Tolerance)

| # | EYESON Field | PF Code | Description | Min | Max | Unit | Confidence |
|---|--------------|---------|-------------|-----|-----|------|------------|
| 1 | `chest_girth` | **Cg** | Chest circumference at nipple line | 60 | 180 | cm | ≥ 0.90 |
| 2 | `waist_girth` | **Wg** | Waist circumference at narrowest point | 50 | 160 | cm | ≥ 0.90 |
| 3 | `hip_girth` | **Hg** | Hip circumference at widest point | 70 | 160 | cm | ≥ 0.90 |
| 4 | `shoulder_width` | **Sh** | Shoulder-to-shoulder across back | 35 | 60 | cm | ≥ 0.90 |
| 5 | `arm_length` | **Al** | Shoulder point to wrist | 45 | 75 | cm | ≥ 0.90 |
| 6 | `inseam` | **Il** | Crotch to floor along inner leg | 60 | 95 | cm | ≥ 0.90 |
| 7 | `neck_girth` | **Nc** | Base of neck circumference | 30 | 55 | cm | ≥ 0.90 |
| 8 | `bicep_girth` | **Bg** | Upper arm circumference (relaxed) | 20 | 55 | cm | ≥ 0.90 |
| 9 | `wrist_girth` | **Wr** | Wrist circumference | 14 | 25 | cm | ≥ 0.90 |
| 10 | `thigh_girth` | **Tg** | Upper thigh circumference | 40 | 90 | cm | ≥ 0.90 |
| 11 | `knee_girth` | **Kg** | Knee circumference | 28 | 55 | cm | ≥ 0.90 |
| 12 | `calf_girth` | **Ca** | Calf circumference at widest point | 25 | 55 | cm | ≥ 0.90 |
| 13 | `back_width` | **Bw** | Across back at shoulder blades | 30 | 55 | cm | ≥ 0.90 |

### Secondary Measurements (P1 - ±2cm Tolerance)

| # | EYESON Field | PF Code | Description | Min | Max | Unit | Confidence |
|---|--------------|---------|-------------|-----|-----|------|------------|
| 14 | `front_waist_length` | **Fwl** | Shoulder to waist (front) | 35 | 55 | cm | ≥ 0.85 |
| 15 | `back_waist_length` | **Bwl** | Shoulder to waist (back, neck to waist) | 35 | 55 | cm | ≥ 0.85 |
| 16 | `front_shoulder_width` | **Fsw** | Shoulder width (front) | 35 | 60 | cm | ≥ 0.85 |
| 17 | `sleeve_inseam` | **Si** | Armpit to wrist | 35 | 60 | cm | ≥ 0.85 |
| 18 | `crotch_depth` | **Cd** | Waist to crotch (vertical) | 20 | 40 | cm | ≥ 0.85 |
| 19 | `outseam` | **Os** | Waist to ankle (side seam) | 85 | 120 | cm | ≥ 0.85 |
| 20 | `front_hip_depth` | **Fhd** | Waist to hip (front) | 10 | 25 | cm | ≥ 0.85 |
| 21 | `back_hip_depth` | **Bhd** | Waist to hip (back) | 12 | 28 | cm | ≥ 0.85 |
| 22 | `waist_to_knee` | **Wk** | Waist to knee (side) | 50 | 70 | cm | ≥ 0.85 |
| 23 | `waist_to_ankle` | **Wa** | Waist to ankle (side) | 85 | 115 | cm | ≥ 0.85 |
| 24 | `shoulder_drop` | **Sd** | Shoulder slope (front vs back) | 0 | 8 | cm | ≥ 0.85 |
| 25 | `chest_width` | **Cw** | Chest width at nipple line | 25 | 55 | cm | ≥ 0.85 |
| 26 | `waist_width` | **Ww** | Waist width at narrowest | 20 | 50 | cm | ≥ 0.85 |
| 27 | `hip_width` | **Hw** | Hip width at widest | 25 | 60 | cm | ≥ 0.85 |
| 28 | `jacket_length` | **Jl** | Base neck to jacket hem | 60 | 95 | cm | ≥ 0.85 |

---

## Confidence Thresholds

### P0 Measurements (Primary)

| Metric | Requirement |
|--------|-------------|
| Minimum Confidence | 0.90 (90%) |
| Tolerance | ±1cm |
| Action on Low Confidence | Retry scan or manual input |
| Auto-Pass Threshold | 0.95 |

### P1 Measurements (Secondary)

| Metric | Requirement |
|--------|-------------|
| Minimum Confidence | 0.85 (85%) |
| Tolerance | ±2cm |
| Action on Low Confidence | Flag for review |
| Auto-Pass Threshold | 0.90 |

### Overall Session Confidence

```python
def calculate_overall_confidence(measurements: dict) -> float:
    """
    Calculate weighted overall confidence score.
    P0 measurements weighted 2x, P1 weighted 1x.
    """
    p0_confidences = [m.confidence for m in measurements if m.type == 'P0']
    p1_confidences = [m.confidence for m in measurements if m.type == 'P1']
    
    p0_avg = sum(p0_confidences) / len(p0_confidences)
    p1_avg = sum(p1_confidences) / len(p1_confidences)
    
    # Weighted average: P0 = 2x, P1 = 1x
    overall = (p0_avg * 2 + p1_avg) / 3
    return overall
```

---

## Size Grading

### Size Chart (Based on Chest Girth)

| Size | Chest Girth (cm) | Waist Girth (cm) | Hip Girth (cm) |
|------|------------------|------------------|----------------|
| **S** | 86 - 91 | 71 - 76 | 86 - 91 |
| **M** | 96 - 102 | 81 - 86 | 96 - 102 |
| **L** | 107 - 112 | 91 - 97 | 107 - 112 |
| **XL** | 117 - 122 | 102 - 107 | 117 - 122 |
| **2XL** | 127 - 132 | 112 - 117 | 127 - 132 |
| **3XL** | 137 - 142 | 122 - 127 | 137 - 142 |
| **4XL** | 147 - 152 | 132 - 137 | 147 - 152 |
| **5XL** | 157 - 162 | 142 - 147 | 157 - 162 |

### Grading Algorithm

```typescript
// Size grading based on primary measurements
export function calculateSize(measurements: PFMeasurements): string {
  const chestGirth = measurements.Cg?.value || 0;
  
  if (chestGirth < 91) return 'S';
  if (chestGirth < 102) return 'M';
  if (chestGirth < 112) return 'L';
  if (chestGirth < 122) return 'XL';
  if (chestGirth < 132) return '2XL';
  if (chestGirth < 142) return '3XL';
  if (chestGirth < 152) return '4XL';
  return '5XL';
}
```

---

## Validation Rules

### Range Validation

```typescript
const VALIDATION_RULES: Record<string, ValidationRule> = {
  Cg: { min: 60, max: 180, tolerance: 1.0, required: true },
  Wg: { min: 50, max: 160, tolerance: 1.0, required: true },
  Hg: { min: 70, max: 160, tolerance: 1.0, required: true },
  Sh: { min: 35, max: 60, tolerance: 1.0, required: true },
  Al: { min: 45, max: 75, tolerance: 1.0, required: true },
  // ... etc
};
```

### Ratio Validation

Certain measurements must maintain logical ratios:

| Ratio | Valid Range | Example |
|-------|-------------|---------|
| Chest:Waist | 1.1 - 1.4 | 102cm chest → 73-93cm waist |
| Chest:Hip | 0.9 - 1.1 | 102cm chest → 93-112cm hip |
| Arm:Inseam | 0.7 - 0.9 | 65cm arm → 57-81cm inseam |

### Cross-Measurement Validation

```typescript
function validateMeasurementSet(measurements: PFMeasurements): ValidationResult {
  const errors: string[] = [];
  
  // Check chest > waist
  if (measurements.Cg.value <= measurements.Wg.value) {
    errors.push('Chest girth must be greater than waist girth');
  }
  
  // Check hip > waist
  if (measurements.Hg.value <= measurements.Wg.value) {
    errors.push('Hip girth must be greater than waist girth');
  }
  
  // Check arm length > sleeve inseam
  if (measurements.Al.value <= measurements.Si?.value || 0) {
    errors.push('Arm length must be greater than sleeve inseam');
  }
  
  return { valid: errors.length === 0, errors };
}
```

---

## Transformation Code

### TypeScript Implementation

```typescript
// File: eyeson/frontend/src/utils/measurementMapping.ts

// EYESON measurement format (from MediaPipe processing)
interface EyesonMeasurement {
  value: number;        // Raw measurement value
  unit: 'cm' | 'inch';  // Unit of measurement
  confidence: number;   // 0.0 - 1.0 confidence score
  timestamp: string;    // ISO 8601 timestamp
}

interface EyesonMeasurements {
  [key: string]: EyesonMeasurement;
}

// Pattern Factory measurement format
interface PFMeasurement {
  value: number;        // Rounded to 1 decimal place
  unit: 'cm';          // Always cm for PF
  confidence: number;   // Preserved from EYESON
}

interface PFMeasurements {
  [code: string]: PFMeasurement;
}

// Mapping: EYESON field name → Pattern Factory code
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
  front_shoulder_width: 'Fsw',
  sleeve_inseam: 'Si',
  crotch_depth: 'Cd',
  outseam: 'Os',
  front_hip_depth: 'Fhd',
  back_hip_depth: 'Bhd',
  waist_to_knee: 'Wk',
  waist_to_ankle: 'Wa',
  shoulder_drop: 'Sd',
  chest_width: 'Cw',
  waist_width: 'Ww',
  hip_width: 'Hw',
  jacket_length: 'Jl',
};

// Measurement metadata
const MEASUREMENT_META: Record<string, { 
  type: 'P0' | 'P1'; 
  minConfidence: number;
  tolerance: number;
}> = {
  // P0 - Primary (±1cm, 90% confidence)
  Cg: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Wg: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Hg: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Sh: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Al: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Il: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Nc: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Bg: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Wr: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Tg: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Kg: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Ca: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  Bw: { type: 'P0', minConfidence: 0.90, tolerance: 1.0 },
  
  // P1 - Secondary (±2cm, 85% confidence)
  Fwl: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Bwl: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Fsw: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Si: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Cd: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Os: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Fhd: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Bhd: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Wk: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Wa: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Sd: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Cw: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Ww: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Hw: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
  Jl: { type: 'P1', minConfidence: 0.85, tolerance: 2.0 },
};

/**
 * Transform EYESON measurements to Pattern Factory format
 * @param eyeson - Raw measurements from EYESON scan
 * @returns Pattern Factory formatted measurements
 */
export function transformToPatternFactory(
  eyeson: EyesonMeasurements
): PFMeasurements {
  const result: PFMeasurements = {};
  
  for (const [eyesonKey, measurement] of Object.entries(eyeson)) {
    const pfCode = MEASUREMENT_CODES[eyesonKey];
    
    if (!pfCode) {
      console.warn(`Unknown measurement field: ${eyesonKey}`);
      continue;
    }
    
    // Convert to cm if needed (assuming 1 inch = 2.54 cm)
    let valueInCm = measurement.value;
    if (measurement.unit === 'inch') {
      valueInCm = measurement.value * 2.54;
    }
    
    // Round to 1 decimal place
    result[pfCode] = {
      value: parseFloat(valueInCm.toFixed(1)),
      unit: 'cm',
      confidence: parseFloat(measurement.confidence.toFixed(2)),
    };
  }
  
  return result;
}

/**
 * Validate measurement confidence levels
 * @param measurements - Pattern Factory measurements
 * @returns Validation result with failures
 */
export function validateConfidence(
  measurements: PFMeasurements
): { valid: boolean; failures: string[] } {
  const failures: string[] = [];
  
  for (const [code, measurement] of Object.entries(measurements)) {
    const meta = MEASUREMENT_META[code];
    
    if (!meta) {
      failures.push(`Unknown measurement code: ${code}`);
      continue;
    }
    
    if (measurement.confidence < meta.minConfidence) {
      failures.push(
        `${code} (${meta.type}): confidence ${measurement.confidence.toFixed(2)} ` +
        `< required ${meta.minConfidence}`
      );
    }
  }
  
  return { valid: failures.length === 0, failures };
}

/**
 * Calculate overall session confidence score
 * Weighted: P0 = 2x, P1 = 1x
 */
export function calculateOverallConfidence(
  measurements: PFMeasurements
): number {
  let p0Sum = 0, p0Count = 0;
  let p1Sum = 0, p1Count = 0;
  
  for (const [code, measurement] of Object.entries(measurements)) {
    const meta = MEASUREMENT_META[code];
    if (!meta) continue;
    
    if (meta.type === 'P0') {
      p0Sum += measurement.confidence;
      p0Count++;
    } else {
      p1Sum += measurement.confidence;
      p1Count++;
    }
  }
  
  const p0Avg = p0Count > 0 ? p0Sum / p0Count : 0;
  const p1Avg = p1Count > 0 ? p1Sum / p1Count : 0;
  
  // Weighted average: P0 = 2x, P1 = 1x
  return (p0Avg * 2 + p1Avg) / 3;
}
```

---

## Next Steps

1. **Review** [03-ORDER-STATE-MACHINE.md](./03-ORDER-STATE-MACHINE.md) for order lifecycle
2. **Reference** [04-API-REFERENCE.md](./04-API-REFERENCE.md) for measurement submission
3. **Check** [06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md) for validation errors

---

*For questions, refer to the Pattern Factory integration code in `eyeson/frontend/src/utils/measurementMapping.ts`*
