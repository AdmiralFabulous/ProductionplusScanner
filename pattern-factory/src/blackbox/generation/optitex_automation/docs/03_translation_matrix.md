# Translation Matrix: Body Measurements to Pattern Parameters

**Purpose**: Convert 80+ body scan measurements into Optitex BTF pattern parameters using M. Muller & Sohn proportional calculations.

---

## OVERVIEW

The Translation Matrix bridges two systems:
1. **Input**: Body measurements from 3D scan (SMPL mesh or manual tape)
2. **Output**: Pattern construction parameters for Optitex BTF rules

```
┌─────────────────┐     ┌────────────────────┐     ┌─────────────────┐
│  Body Scan      │────▶│  Translation       │────▶│  BTF Pattern    │
│  Measurements   │     │  Matrix            │     │  Parameters     │
│  (80+ values)   │     │  (M. Muller rules) │     │  (point moves)  │
└─────────────────┘     └────────────────────┘     └─────────────────┘
```

---

## M. MULLER & SOHN SYSTEM

The Translation Matrix is based on the M. Muller & Sohn proportional system, the industry standard for menswear pattern construction. Key principles:

1. **Primary Measurements** drive all calculations (Chest, Waist, Hip, Height)
2. **Proportional Formulas** derive secondary measurements
3. **Ease Values** are added based on garment type and fit preference
4. **Adjustment Rules** handle deviations from "standard" proportions

---

## PRIMARY MEASUREMENT INPUTS

### Required Measurements (Minimum 15)

| # | Measurement | Code | Source | Priority |
|---|-------------|------|--------|----------|
| 1 | Chest Circumference | `CHEST` | Scan | P0 |
| 2 | Waist Circumference | `WAIST` | Scan | P0 |
| 3 | Hip Circumference | `HIP` | Scan | P0 |
| 4 | Shoulder Width | `SHOULDER_WIDTH` | Scan | P0 |
| 5 | Back Length | `BACK_LENGTH` | Scan | P0 |
| 6 | Arm Length | `ARM_LENGTH` | Scan | P0 |
| 7 | Neck Circumference | `NECK` | Scan | P0 |
| 8 | Bicep Circumference | `BICEP` | Scan | P1 |
| 9 | Wrist Circumference | `WRIST` | Scan | P1 |
| 10 | Inseam | `INSEAM` | Scan | P1 |
| 11 | Thigh Circumference | `THIGH` | Scan | P1 |
| 12 | Height | `HEIGHT` | Scan | P0 |
| 13 | Armhole Depth | `ARMHOLE_DEPTH` | Derived/Scan | P1 |
| 14 | Front Length | `FRONT_LENGTH` | Derived/Scan | P1 |
| 15 | Crotch Depth | `CROTCH_DEPTH` | Derived/Scan | P1 |

### Extended Measurements (Full 80+)

See `standard_params.txt` in BTF templates for complete list.

---

## TRANSLATION FORMULAS

### 1. JACKET CONSTRUCTION

#### Basic Pattern Dimensions

```python
# =====================================================
# JACKET TRANSLATION MATRIX
# Based on M. Muller & Sohn System
# =====================================================

class JacketTranslation:
    """Convert body measurements to jacket pattern parameters."""
    
    def __init__(self, measurements: dict, fit_type: str = 'regular'):
        self.m = measurements
        self.fit = fit_type
        self.ease = self._get_ease_values()
    
    def _get_ease_values(self) -> dict:
        """Get ease values based on fit type."""
        ease_table = {
            'slim': {
                'chest': 8.0, 'waist': 10.0, 'hip': 6.0,
                'sleeve': 6.0, 'armhole': 2.0
            },
            'regular': {
                'chest': 12.0, 'waist': 14.0, 'hip': 10.0,
                'sleeve': 8.0, 'armhole': 3.0
            },
            'classic': {
                'chest': 16.0, 'waist': 18.0, 'hip': 14.0,
                'sleeve': 10.0, 'armhole': 4.0
            }
        }
        return ease_table.get(self.fit, ease_table['regular'])
    
    # === PRIMARY CALCULATIONS ===
    
    def half_chest(self) -> float:
        """Half chest width including ease."""
        return (self.m['CHEST'] + self.ease['chest']) / 2
    
    def half_waist(self) -> float:
        """Half waist width including ease."""
        return (self.m['WAIST'] + self.ease['waist']) / 2
    
    def half_hip(self) -> float:
        """Half hip width including ease."""
        return (self.m['HIP'] + self.ease['hip']) / 2
    
    def half_back(self) -> float:
        """Half back width (shoulder to center back)."""
        return self.m['SHOULDER_WIDTH'] / 2 - 1.0
    
    def scye_depth(self) -> float:
        """Armhole depth including ease."""
        base = self.m.get('ARMHOLE_DEPTH')
        if base is None:
            # M. Muller formula: CHEST/4 + 2
            base = self.m['CHEST'] / 4 + 2.0
        return base + self.ease['armhole']
    
    # === DERIVED MEASUREMENTS ===
    
    def front_width(self) -> float:
        """Front panel width."""
        return self.half_chest() * 0.52
    
    def back_width(self) -> float:
        """Back panel width."""
        return self.half_chest() * 0.48
    
    def side_panel_width(self) -> float:
        """Side panel width (for 3-piece construction)."""
        return self.half_chest() * 0.15
    
    def front_dart_intake(self) -> float:
        """Front dart depth at waist."""
        chest_waist_diff = self.half_chest() - self.half_waist()
        return chest_waist_diff * 0.3
    
    def back_dart_intake(self) -> float:
        """Back dart depth at waist."""
        chest_waist_diff = self.half_chest() - self.half_waist()
        return chest_waist_diff * 0.2
    
    # === SLEEVE CALCULATIONS ===
    
    def sleeve_length(self) -> float:
        """Sleeve length (shoulder to wrist minus cuff)."""
        return self.m['ARM_LENGTH'] - 3.0
    
    def sleeve_head_width(self) -> float:
        """Sleeve head width at bicep level."""
        bicep_with_ease = self.m['BICEP'] + self.ease['sleeve']
        return bicep_with_ease * 0.52
    
    def sleeve_head_height(self) -> float:
        """Sleeve cap height (M. Muller: scye_depth * 0.65)."""
        return self.scye_depth() * 0.65
    
    def sleeve_bottom_width(self) -> float:
        """Sleeve hem width."""
        return self.m['WRIST'] + 4.0
    
    # === COLLAR CALCULATIONS ===
    
    def collar_length(self) -> float:
        """Collar length (half neck + extension)."""
        return (self.m['NECK'] / 2) + 2.0
    
    def collar_stand_height(self) -> float:
        """Collar stand height (standard: 3.5cm)."""
        return 3.5
    
    def collar_width(self) -> float:
        """Collar leaf width (standard: 5.5cm)."""
        return 5.5
    
    # === POINT MOVEMENT DELTAS ===
    
    def get_point_deltas(self) -> dict:
        """
        Calculate all point movement deltas from base pattern.
        Base pattern is size 50 (European).
        """
        base = {
            'CHEST': 104.0, 'WAIST': 92.0, 'HIP': 102.0,
            'SHOULDER_WIDTH': 46.0, 'BACK_LENGTH': 44.0,
            'ARM_LENGTH': 64.0, 'BICEP': 32.0, 'WRIST': 17.0,
            'NECK': 40.0, 'ARMHOLE_DEPTH': 22.0
        }
        
        return {
            # Front Panel
            'FP_SHOULDER_X': (self.m['SHOULDER_WIDTH'] - base['SHOULDER_WIDTH']) / 2,
            'FP_CHEST_X': self.half_chest() - 52.0,
            'FP_WAIST_X': self.half_waist() - 46.0,
            'FP_HEM_Y': self.m.get('JACKET_LENGTH', 76.0) - 76.0,
            
            # Back Panel
            'BP_SHOULDER_X': (self.m['SHOULDER_WIDTH'] - base['SHOULDER_WIDTH']) / 2,
            'BP_WAIST_Y': self.m['BACK_LENGTH'] - base['BACK_LENGTH'],
            'BP_HEM_Y': self.m.get('JACKET_LENGTH', 76.0) - 76.0,
            
            # Armhole
            'AH_DEPTH_Y': self.scye_depth() - 24.5,
            'AH_WIDTH_X': (self.m['BICEP'] - base['BICEP']) * 0.3,
            
            # Sleeve
            'SL_HEAD_TOP_Y': self.sleeve_head_height() - 16.0,
            'SL_HEAD_WIDTH_X': self.sleeve_head_width() - 17.0,
            'SL_HEM_X': (self.sleeve_bottom_width() - 21.0) / 2,
            'SL_HEM_Y': self.sleeve_length() - 61.0,
            
            # Collar
            'COL_LENGTH_X': self.collar_length() - 22.0,
            'COL_STAND_Y': 0.0,  # Usually fixed
        }
    
    def to_btf_params(self) -> str:
        """Generate BTF parameter file content."""
        deltas = self.get_point_deltas()
        
        lines = [
            "; Generated BTF Parameters",
            f"; Fit Type: {self.fit}",
            "",
            "; Input Measurements",
        ]
        
        for key, value in self.m.items():
            lines.append(f"@PARAM {key} = {value}")
        
        lines.extend([
            "",
            "; Calculated Values",
            f"@CALC HALF_CHEST = {self.half_chest():.1f}",
            f"@CALC HALF_WAIST = {self.half_waist():.1f}",
            f"@CALC HALF_HIP = {self.half_hip():.1f}",
            f"@CALC SCYE_DEPTH = {self.scye_depth():.1f}",
            f"@CALC FRONT_WIDTH = {self.front_width():.1f}",
            f"@CALC BACK_WIDTH = {self.back_width():.1f}",
            f"@CALC SLEEVE_LENGTH = {self.sleeve_length():.1f}",
            f"@CALC SLEEVE_HEAD_HEIGHT = {self.sleeve_head_height():.1f}",
            "",
            "; Point Movements",
        ])
        
        for key, value in deltas.items():
            axis = 'X' if key.endswith('_X') else 'Y'
            point_name = key.rsplit('_', 1)[0]
            lines.append(f"@MVPNT /PNT={point_name} /D{axis}={value:.2f}")
        
        return "\n".join(lines)
```

### 2. TROUSERS CONSTRUCTION

```python
# =====================================================
# TROUSERS TRANSLATION MATRIX
# =====================================================

class TrousersTranslation:
    """Convert body measurements to trouser pattern parameters."""
    
    def __init__(self, measurements: dict, fit_type: str = 'regular'):
        self.m = measurements
        self.fit = fit_type
        self.ease = self._get_ease_values()
    
    def _get_ease_values(self) -> dict:
        ease_table = {
            'slim': {
                'waist': 2.0, 'hip': 4.0, 'thigh': 4.0,
                'knee': 2.0, 'hem': 0.0
            },
            'regular': {
                'waist': 4.0, 'hip': 6.0, 'thigh': 8.0,
                'knee': 4.0, 'hem': 2.0
            },
            'classic': {
                'waist': 6.0, 'hip': 10.0, 'thigh': 12.0,
                'knee': 8.0, 'hem': 4.0
            }
        }
        return ease_table.get(self.fit, ease_table['regular'])
    
    # === PRIMARY CALCULATIONS ===
    
    def half_waist(self) -> float:
        return (self.m['WAIST'] + self.ease['waist']) / 2
    
    def half_hip(self) -> float:
        return (self.m['HIP'] + self.ease['hip']) / 2
    
    def half_thigh(self) -> float:
        return (self.m['THIGH'] + self.ease['thigh']) / 2
    
    # === M. MULLER TROUSER FORMULAS ===
    
    def crotch_extension_front(self) -> float:
        """Front crotch extension (M. Muller: hip/8 - 1.5)."""
        return self.half_hip() * 0.12
    
    def crotch_extension_back(self) -> float:
        """Back crotch extension (M. Muller: hip/4 - 1.0)."""
        return self.half_hip() * 0.24
    
    def front_panel_width(self) -> float:
        """Front panel width at hip (M. Muller: 48% of hip)."""
        return self.half_hip() * 0.48
    
    def back_panel_width(self) -> float:
        """Back panel width at hip (M. Muller: 52% of hip)."""
        return self.half_hip() * 0.52
    
    def crotch_depth(self) -> float:
        """Crotch depth from waist."""
        if 'CROTCH_DEPTH' in self.m:
            return self.m['CROTCH_DEPTH']
        # M. Muller formula: HIP/4 + 1.0
        return self.m['HIP'] / 4 + 1.0
    
    def front_rise(self) -> float:
        """Front rise measurement."""
        if 'FRONT_RISE' in self.m:
            return self.m['FRONT_RISE']
        return self.crotch_depth() + 1.0
    
    def back_rise(self) -> float:
        """Back rise measurement."""
        if 'BACK_RISE' in self.m:
            return self.m['BACK_RISE']
        return self.crotch_depth() + 9.0
    
    def knee_width(self) -> float:
        """Knee width with ease."""
        return self.m.get('KNEE', 40.0) + self.ease['knee']
    
    def hem_width(self) -> float:
        """Hem/ankle width with ease."""
        return self.m.get('ANKLE', 24.0) + self.ease['hem']
    
    def trouser_length(self) -> float:
        """Trouser outseam length."""
        return self.m.get('OUTSEAM', 108.0) - 30.0  # Minus waistband and break
    
    def get_point_deltas(self) -> dict:
        """Calculate point movement deltas from base (size 50)."""
        base = {
            'WAIST': 92.0, 'HIP': 102.0, 'THIGH': 58.0,
            'INSEAM': 82.0, 'CROTCH_DEPTH': 26.0
        }
        
        return {
            # Front Panel
            'TF_WAIST_SIDE_X': self.front_panel_width() - 24.0,
            'TF_HIP_X': self.front_panel_width() - 24.0,
            'TF_HIP_Y': self.crotch_depth() - base['CROTCH_DEPTH'],
            'TF_CROTCH_X': self.crotch_extension_front() - 6.0,
            'TF_KNEE_X': (self.knee_width() / 2) - 12.0,
            'TF_HEM_X': (self.hem_width() / 2) - 11.0,
            'TF_HEM_Y': self.trouser_length() - 78.0,
            
            # Back Panel
            'TB_WAIST_SIDE_X': self.back_panel_width() - 26.0,
            'TB_WAIST_Y': self.back_rise() - 35.0,
            'TB_SEAT_X': self.back_panel_width() - 26.0,
            'TB_CROTCH_X': self.crotch_extension_back() - 12.0,
            'TB_KNEE_X': (self.knee_width() / 2) - 12.0,
            'TB_HEM_X': (self.hem_width() / 2) - 11.0,
            'TB_HEM_Y': self.trouser_length() - 78.0,
            
            # Waistband
            'WB_LENGTH_X': self.half_waist() - 46.0,
        }
```

### 3. SHIRT CONSTRUCTION

```python
# =====================================================
# SHIRT TRANSLATION MATRIX
# =====================================================

class ShirtTranslation:
    """Convert body measurements to shirt pattern parameters."""
    
    def __init__(self, measurements: dict, fit_type: str = 'regular'):
        self.m = measurements
        self.fit = fit_type
        self.ease = self._get_ease_values()
    
    def _get_ease_values(self) -> dict:
        ease_table = {
            'slim': {
                'chest': 10.0, 'waist': 8.0, 'hip': 8.0,
                'sleeve': 6.0, 'cuff': 2.0
            },
            'regular': {
                'chest': 14.0, 'waist': 12.0, 'hip': 12.0,
                'sleeve': 8.0, 'cuff': 3.0
            },
            'classic': {
                'chest': 18.0, 'waist': 18.0, 'hip': 18.0,
                'sleeve': 10.0, 'cuff': 4.0
            }
        }
        return ease_table.get(self.fit, ease_table['regular'])
    
    # === PRIMARY CALCULATIONS ===
    
    def half_chest(self) -> float:
        return (self.m['CHEST'] + self.ease['chest']) / 2
    
    def half_waist(self) -> float:
        return (self.m['WAIST'] + self.ease['waist']) / 2
    
    def collar_size(self) -> float:
        """Collar size (neck + ease)."""
        return self.m['NECK'] + 1.5
    
    def cuff_size(self) -> float:
        """Cuff circumference."""
        return self.m['WRIST'] + self.ease['cuff']
    
    def yoke_depth(self) -> float:
        """Yoke depth from nape."""
        return self.m.get('YOKE_DEPTH', 8.0)
    
    def sleeve_length(self) -> float:
        """Full sleeve length including cuff."""
        return self.m['ARM_LENGTH'] + 2.5
    
    def sleeve_cap_height(self) -> float:
        """Sleeve cap height (lower than jacket)."""
        bicep_with_ease = self.m['BICEP'] + self.ease['sleeve']
        return bicep_with_ease * 0.15
    
    def get_point_deltas(self) -> dict:
        """Calculate point movement deltas from base (size 40 collar)."""
        base = {
            'CHEST': 104.0, 'WAIST': 92.0, 'SHOULDER_WIDTH': 46.0,
            'BACK_LENGTH': 44.0, 'ARM_LENGTH': 64.0, 'BICEP': 32.0,
            'WRIST': 17.0, 'NECK': 40.0
        }
        
        return {
            # Body
            'SH_SHOULDER_X': (self.m['SHOULDER_WIDTH'] - base['SHOULDER_WIDTH']) / 2,
            'SH_CHEST_X': self.half_chest() - 57.0,
            'SH_WAIST_X': self.half_waist() - 50.0,
            'SH_WAIST_Y': self.m['BACK_LENGTH'] - base['BACK_LENGTH'],
            'SH_HEM_Y': self.m.get('SHIRT_LENGTH', 80.0) - 80.0,
            
            # Sleeve
            'SL_CAP_Y': self.sleeve_cap_height() - 6.0,
            'SL_WIDTH_X': (self.m['BICEP'] + self.ease['sleeve'] - 40.0) / 2,
            'SL_CUFF_X': (self.cuff_size() - 20.0) / 2,
            'SL_CUFF_Y': self.sleeve_length() - 66.5,
            
            # Collar
            'COL_BAND_LENGTH_X': (self.collar_size() - 41.5) / 2,
            'COL_LEAF_LENGTH_X': (self.collar_size() - 41.5) / 2,
            
            # Cuff
            'CUFF_LENGTH_X': self.cuff_size() - 20.0,
        }
```

### 4. WAISTCOAT CONSTRUCTION

```python
# =====================================================
# WAISTCOAT TRANSLATION MATRIX
# =====================================================

class WaistcoatTranslation:
    """Convert body measurements to waistcoat pattern parameters."""
    
    def __init__(self, measurements: dict, fit_type: str = 'regular'):
        self.m = measurements
        self.fit = fit_type
        self.ease = self._get_ease_values()
    
    def _get_ease_values(self) -> dict:
        # Waistcoat is always more fitted than jacket
        ease_table = {
            'slim': {'chest': 4.0, 'waist': 2.0},
            'regular': {'chest': 6.0, 'waist': 4.0},
            'classic': {'chest': 8.0, 'waist': 6.0}
        }
        return ease_table.get(self.fit, ease_table['regular'])
    
    def half_chest(self) -> float:
        return (self.m['CHEST'] + self.ease['chest']) / 2
    
    def half_waist(self) -> float:
        return (self.m['WAIST'] + self.ease['waist']) / 2
    
    def front_opening(self) -> float:
        """Front neckline opening."""
        return self.m['NECK'] / 6 + 2.0
    
    def waistcoat_length(self) -> float:
        """Total waistcoat length."""
        return self.m.get('WAISTCOAT_LENGTH', 58.0)
    
    def get_point_deltas(self) -> dict:
        base = {
            'CHEST': 104.0, 'WAIST': 92.0, 'SHOULDER_WIDTH': 46.0,
            'FRONT_LENGTH': 45.0, 'BACK_LENGTH': 44.0, 'ARMHOLE_DEPTH': 22.0
        }
        
        return {
            # Front
            'WF_SHOULDER_X': (self.m['SHOULDER_WIDTH'] - base['SHOULDER_WIDTH']) / 2 - 2.0,
            'WF_CHEST_X': self.half_chest() - 55.0,
            'WF_WAIST_X': self.half_waist() - 48.0,
            'WF_WAIST_Y': self.m.get('FRONT_LENGTH', 45.0) - base['FRONT_LENGTH'],
            'WF_POINT_Y': self.waistcoat_length() - 58.0,
            
            # Back
            'WB_SHOULDER_X': (self.m['SHOULDER_WIDTH'] - base['SHOULDER_WIDTH']) / 2 - 2.0,
            'WB_WAIST_Y': self.m['BACK_LENGTH'] - base['BACK_LENGTH'],
            'WB_HEM_Y': (self.waistcoat_length() - 58.0) - 5.0,
            
            # Armhole
            'AH_DEPTH_Y': self.m.get('ARMHOLE_DEPTH', 22.0) - base['ARMHOLE_DEPTH'],
            
            # Neckline
            'NECK_FRONT_X': self.front_opening() - 8.7,
        }
```

---

## UNIFIED TRANSLATION ENGINE

```python
# =====================================================
# UNIFIED TRANSLATION ENGINE
# =====================================================

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class GarmentType(Enum):
    JACKET = 'jacket'
    TROUSERS = 'trousers'
    SHIRT = 'shirt'
    WAISTCOAT = 'waistcoat'

class FitType(Enum):
    SLIM = 'slim'
    REGULAR = 'regular'
    CLASSIC = 'classic'

@dataclass
class TranslationResult:
    """Result of translation matrix calculation."""
    garment_type: GarmentType
    fit_type: FitType
    input_measurements: Dict[str, float]
    calculated_values: Dict[str, float]
    point_deltas: Dict[str, float]
    btf_content: str
    excel_content: str  # For @MTM_CREATE command

class TranslationMatrix:
    """
    Unified translation matrix for all garment types.
    Converts body measurements to pattern parameters.
    """
    
    TRANSLATORS = {
        GarmentType.JACKET: JacketTranslation,
        GarmentType.TROUSERS: TrousersTranslation,
        GarmentType.SHIRT: ShirtTranslation,
        GarmentType.WAISTCOAT: WaistcoatTranslation,
    }
    
    @classmethod
    def translate(
        cls,
        measurements: Dict[str, float],
        garment_type: GarmentType,
        fit_type: FitType = FitType.REGULAR
    ) -> TranslationResult:
        """
        Translate body measurements to pattern parameters.
        
        Args:
            measurements: Dict of body measurements (cm)
            garment_type: Type of garment to generate
            fit_type: Desired fit (slim/regular/classic)
        
        Returns:
            TranslationResult with all calculated values
        """
        translator_class = cls.TRANSLATORS[garment_type]
        translator = translator_class(measurements, fit_type.value)
        
        # Get point deltas
        deltas = translator.get_point_deltas()
        
        # Generate BTF content
        btf_content = translator.to_btf_params()
        
        # Generate Excel content for MTM_CREATE
        excel_content = cls._generate_mtm_excel(measurements, garment_type)
        
        return TranslationResult(
            garment_type=garment_type,
            fit_type=fit_type,
            input_measurements=measurements,
            calculated_values=cls._extract_calculated(translator),
            point_deltas=deltas,
            btf_content=btf_content,
            excel_content=excel_content
        )
    
    @staticmethod
    def _extract_calculated(translator) -> Dict[str, float]:
        """Extract calculated values from translator."""
        calculated = {}
        for method_name in dir(translator):
            if not method_name.startswith('_') and method_name not in ['m', 'fit', 'ease']:
                method = getattr(translator, method_name)
                if callable(method) and method_name != 'get_point_deltas' and method_name != 'to_btf_params':
                    try:
                        calculated[method_name] = method()
                    except:
                        pass
        return calculated
    
    @staticmethod
    def _generate_mtm_excel(measurements: Dict[str, float], garment_type: GarmentType) -> str:
        """
        Generate CSV content for Optitex @MTM_CREATE command.
        
        Format: First column is "Measure", subsequent columns are size names.
        """
        lines = ["Measure,CUSTOM"]
        
        # Map measurement names to Optitex internal names
        name_mapping = {
            'CHEST': 'Chest',
            'WAIST': 'Waist',
            'HIP': 'Hip',
            'SHOULDER_WIDTH': 'Shoulder',
            'BACK_LENGTH': 'Back Length',
            'ARM_LENGTH': 'Arm Length',
            'NECK': 'Neck',
            'BICEP': 'Bicep',
            'WRIST': 'Wrist',
            'INSEAM': 'Inseam',
            'THIGH': 'Thigh',
            'KNEE': 'Knee',
            'CALF': 'Calf',
            'ANKLE': 'Ankle',
            'FRONT_LENGTH': 'Front Length',
            'ARMHOLE_DEPTH': 'Armhole',
            'CROTCH_DEPTH': 'Crotch Depth',
        }
        
        for key, value in measurements.items():
            optitex_name = name_mapping.get(key, key)
            lines.append(f"{optitex_name},{value}")
        
        return "\n".join(lines)
```

---

## VALIDATION RULES

### Sanity Checks

```python
class MeasurementValidator:
    """Validate measurements before translation."""
    
    # Anatomical constraints (min, max in cm)
    CONSTRAINTS = {
        'CHEST': (80, 160),
        'WAIST': (60, 150),
        'HIP': (80, 160),
        'SHOULDER_WIDTH': (36, 60),
        'BACK_LENGTH': (38, 54),
        'ARM_LENGTH': (52, 76),
        'NECK': (32, 52),
        'BICEP': (24, 50),
        'WRIST': (14, 24),
        'INSEAM': (68, 100),
        'THIGH': (42, 80),
    }
    
    # Proportional rules
    PROPORTIONS = {
        'WAIST_TO_CHEST': (0.75, 1.0),      # Waist should be 75-100% of chest
        'HIP_TO_CHEST': (0.85, 1.15),       # Hip should be 85-115% of chest
        'BICEP_TO_CHEST': (0.28, 0.40),     # Bicep should be 28-40% of chest
    }
    
    @classmethod
    def validate(cls, measurements: Dict[str, float]) -> tuple[bool, list[str]]:
        """
        Validate measurements.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check absolute constraints
        for key, (min_val, max_val) in cls.CONSTRAINTS.items():
            if key in measurements:
                value = measurements[key]
                if value < min_val or value > max_val:
                    errors.append(
                        f"{key}: {value}cm is outside valid range ({min_val}-{max_val}cm)"
                    )
        
        # Check proportions
        if 'CHEST' in measurements:
            chest = measurements['CHEST']
            
            if 'WAIST' in measurements:
                ratio = measurements['WAIST'] / chest
                min_r, max_r = cls.PROPORTIONS['WAIST_TO_CHEST']
                if ratio < min_r or ratio > max_r:
                    errors.append(
                        f"Waist/Chest ratio {ratio:.2f} outside expected range ({min_r}-{max_r})"
                    )
            
            if 'HIP' in measurements:
                ratio = measurements['HIP'] / chest
                min_r, max_r = cls.PROPORTIONS['HIP_TO_CHEST']
                if ratio < min_r or ratio > max_r:
                    errors.append(
                        f"Hip/Chest ratio {ratio:.2f} outside expected range ({min_r}-{max_r})"
                    )
        
        return (len(errors) == 0, errors)
```

---

## OUTPUT FORMAT

### BTF Parameter File

```
; suit_jacket_params_ORD123.txt
; Generated: 2026-01-29
; Order: ORD-2026-0001

@PARAM CHEST = 102.5
@PARAM WAIST = 88.0
@PARAM HIP = 98.5
@PARAM SHOULDER_WIDTH = 46.0
; ... all measurements ...

@CALC HALF_CHEST = 57.3
@CALC HALF_WAIST = 51.0
; ... all calculated values ...

@MVPNT /PNT=FP_SHOULDER /DX=0.00 /DY=0.00
@MVPNT /PNT=FP_CHEST /DX=5.30 /DY=0.00
; ... all point movements ...
```

### Excel File (for @MTM_CREATE)

| Measure | CUSTOM |
|---------|--------|
| Chest | 102.5 |
| Waist | 88.0 |
| Hip | 98.5 |
| Shoulder | 46.0 |
| Back Length | 44.0 |
| ... | ... |

---

## USAGE

```python
# Example: Generate jacket pattern from scan measurements

measurements = {
    'CHEST': 102.5,
    'WAIST': 88.0,
    'HIP': 98.5,
    'SHOULDER_WIDTH': 46.0,
    'BACK_LENGTH': 44.0,
    'ARM_LENGTH': 64.5,
    'NECK': 40.0,
    'BICEP': 32.0,
    'WRIST': 17.5,
    'ARMHOLE_DEPTH': 22.0,
    'HEIGHT': 178.0,
}

# Validate
is_valid, errors = MeasurementValidator.validate(measurements)
if not is_valid:
    print("Validation errors:", errors)

# Translate
result = TranslationMatrix.translate(
    measurements=measurements,
    garment_type=GarmentType.JACKET,
    fit_type=FitType.REGULAR
)

# Output BTF file
with open('jacket_params.txt', 'w') as f:
    f.write(result.btf_content)

# Output Excel for MTM_CREATE
with open('measures.csv', 'w') as f:
    f.write(result.excel_content)
```
