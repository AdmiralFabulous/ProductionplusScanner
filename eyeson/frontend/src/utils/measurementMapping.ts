/**
 * Measurement Mapping: EYESON → SameDaySuits Pattern Factory
 * 
 * INTEGRATION NOTE (ref: SUIT_AI_Master_Operations_Manual_v6_7_1.md):
 * This module transforms EYESON's measurement format into the Pattern Factory's
 * 28-measurement standard format (Section 13 Database Schema).
 * 
 * Pattern Factory uses abbreviated codes:
 * - Cg = Chest Girth
 * - Wg = Waist Girth
 * - etc.
 */

import type { Measurements as PatternFactoryMeasurements } from '../services/patternFactoryApi'

// ============================================================================
// EYESON Internal Measurement Format
// ============================================================================

export interface EyesonMeasurement {
  name: string
  value: number
  unit: string
  confidence: number
  grade: 'P0' | 'P1'
}

// ============================================================================
// MEASUREMENT CODE MAPPING
// ref: ops manual Section 13 - Database Schema
// ============================================================================

const MEASUREMENT_CODE_MAP: Record<string, keyof PatternFactoryMeasurements> = {
  // Primary Measurements (P0 - Critical)
  'chest_girth': 'Cg',
  'waist_girth': 'Wg', 
  'hip_girth': 'Hg',
  'shoulder_width': 'Sh',
  'arm_length': 'Al',
  'back_width': 'Bw',
  'neck_girth': 'Nc',
  'bicep_girth': 'Bi',
  'wrist_girth': 'Wc',
  'inseam': 'Il',
  'thigh_girth': 'Th',
  'knee_girth': 'Kn',
  'calf_girth': 'Ca',
  
  // Additional mappings for variations
  'chest': 'Cg',
  'waist': 'Wg',
  'hip': 'Hg',
  'shoulder': 'Sh',
  'sleeve': 'Al',
  'back': 'Bw',
  'neck': 'Nc',
  'bicep': 'Bi',
  'wrist': 'Wc',
  'inseam_length': 'Il',
  'thigh': 'Th',
  'knee': 'Kn',
  'calf': 'Ca',
}

// Full names for display
const MEASUREMENT_DISPLAY_NAMES: Record<string, string> = {
  'Cg': 'Chest Girth',
  'Wg': 'Waist Girth',
  'Hg': 'Hip Girth',
  'Sh': 'Shoulder Width',
  'Al': 'Arm Length',
  'Bw': 'Back Width',
  'Nc': 'Neck Circumference',
  'Bi': 'Bicep Girth',
  'Wc': 'Wrist Circumference',
  'Il': 'Inseam Length',
  'Th': 'Thigh Girth',
  'Kn': 'Knee Girth',
  'Ca': 'Calf Girth',
}

// ============================================================================
// TRANSFORMATION FUNCTIONS
// ============================================================================

/**
 * Transform EYESON measurements to Pattern Factory format
 * 
 * @param eyesonMeasurements - Measurements from EYESON scan
 * @returns Pattern Factory compatible measurement object
 * 
 * ref: ops manual Section 13 - Measurement JSON Schema
 */
export function transformToPatternFactory(
  eyesonMeasurements: EyesonMeasurement[]
): PatternFactoryMeasurements {
  const result: Partial<PatternFactoryMeasurements> = {}

  for (const measurement of eyesonMeasurements) {
    const code = MEASUREMENT_CODE_MAP[measurement.name.toLowerCase()]
    
    if (code) {
      result[code] = {
        value: measurement.value,
        unit: 'cm',
        confidence: measurement.confidence,
      }
    }
  }

  // Validate all primary measurements are present
  const requiredCodes = ['Cg', 'Wg', 'Hg', 'Sh', 'Al', 'Bw', 'Nc', 'Bi', 'Wc', 'Il', 'Th', 'Kn', 'Ca']
  const missing = requiredCodes.filter(code => !result[code as keyof PatternFactoryMeasurements])
  
  if (missing.length > 0) {
    console.warn('Missing measurements:', missing.map(c => MEASUREMENT_DISPLAY_NAMES[c] || c))
  }

  return result as PatternFactoryMeasurements
}

/**
 * Transform Pattern Factory measurements back to EYESON format
 * For display in Results screen
 */
export function transformToEyeson(
  pfMeasurements: PatternFactoryMeasurements
): EyesonMeasurement[] {
  const result: EyesonMeasurement[] = []

  const codeToNameMap = Object.entries(MEASUREMENT_CODE_MAP).reduce((acc, [name, code]) => {
    acc[code] = name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    return acc
  }, {} as Record<string, string>)

  for (const [code, data] of Object.entries(pfMeasurements)) {
    if (data && typeof data.value === 'number') {
      result.push({
        name: codeToNameMap[code] || code,
        value: data.value,
        unit: data.unit || 'cm',
        confidence: data.confidence || 0.9,
        grade: data.confidence && data.confidence >= 0.9 ? 'P0' : 'P1',
      })
    }
  }

  return result
}

/**
 * Calculate size code from chest girth
 * ref: ops manual Section 13 - Size Grading System
 * 
 * Formula: Selected Size = ROUND((Chest_Girth - 88) / 5) + 1
 */
export function calculateSizeCode(chestGirthCm: number): {
  code: string
  name: string
} {
  const sizeIndex = Math.round((chestGirthCm - 88) / 5) + 1
  
  const sizes: Record<number, { code: string; name: string }> = {
    1: { code: 'S', name: 'Small' },
    2: { code: 'M', name: 'Medium' },
    3: { code: 'L', name: 'Large' },
    4: { code: 'XL', name: 'Extra Large' },
    5: { code: '2XL', name: '2X Large' },
    6: { code: '3XL', name: '3X Large' },
    7: { code: '4XL', name: '4X Large' },
    8: { code: '5XL', name: '5X Large' },
  }

  return sizes[sizeIndex] || { code: 'L', name: 'Large' }
}

/**
 * Validate measurements meet Pattern Factory requirements
 * ref: ops manual Section 2.8 - QC Validation Thresholds
 */
export function validateMeasurements(
  measurements: PatternFactoryMeasurements
): {
  valid: boolean
  errors: string[]
  warnings: string[]
} {
  const errors: string[] = []
  const warnings: string[] = []

  // Check primary measurements exist
  const primaryCodes = ['Cg', 'Wg', 'Hg', 'Sh', 'Al', 'Nc']
  
  for (const code of primaryCodes) {
    const measurement = measurements[code as keyof PatternFactoryMeasurements]
    if (!measurement || !measurement.value) {
      errors.push(`Missing required measurement: ${MEASUREMENT_DISPLAY_NAMES[code] || code}`)
    }
  }

  // Check confidence levels
  for (const [code, data] of Object.entries(measurements)) {
    if (data && data.confidence < 0.75) {
      warnings.push(`Low confidence on ${MEASUREMENT_DISPLAY_NAMES[code] || code}: ${Math.round(data.confidence * 100)}%`)
    }
  }

  // Physical plausibility checks
  const chest = measurements.Cg?.value
  const waist = measurements.Wg?.value
  const hip = measurements.Hg?.value

  if (chest && waist && chest <= waist) {
    warnings.push('Chest measurement should be larger than waist for male garments')
  }

  if (hip && waist && hip <= waist) {
    warnings.push('Hip measurement should be larger than waist')
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  }
}

/**
 * Get display name for measurement code
 */
export function getMeasurementDisplayName(code: string): string {
  return MEASUREMENT_DISPLAY_NAMES[code] || code
}

/**
 * Get measurement code from display name
 */
export function getMeasurementCode(name: string): string | undefined {
  const normalized = name.toLowerCase().replace(/\s+/g, '_')
  return MEASUREMENT_CODE_MAP[normalized]
}

// ============================================================================
// DEFAULT MEASUREMENTS (for testing)
// ============================================================================

export const DEFAULT_MEASUREMENTS: PatternFactoryMeasurements = {
  Cg: { value: 102.5, unit: 'cm', confidence: 0.95 },
  Wg: { value: 88.0, unit: 'cm', confidence: 0.92 },
  Hg: { value: 98.5, unit: 'cm', confidence: 0.94 },
  Sh: { value: 45.2, unit: 'cm', confidence: 0.94 },
  Al: { value: 64.8, unit: 'cm', confidence: 0.88 },
  Bw: { value: 38.5, unit: 'cm', confidence: 0.81 },
  Nc: { value: 39.4, unit: 'cm', confidence: 0.93 },
  Bi: { value: 32.1, unit: 'cm', confidence: 0.85 },
  Wc: { value: 17.8, unit: 'cm', confidence: 0.87 },
  Il: { value: 82.4, unit: 'cm', confidence: 0.86 },
  Th: { value: 58.3, unit: 'cm', confidence: 0.84 },
  Kn: { value: 38.9, unit: 'cm', confidence: 0.83 },
  Ca: { value: 37.2, unit: 'cm', confidence: 0.82 },
}
