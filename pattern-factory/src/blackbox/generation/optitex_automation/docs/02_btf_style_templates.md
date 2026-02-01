# BTF-Enabled Style Templates

**Purpose**: Parametric pattern templates that accept body measurements as input and generate custom-fit patterns.

**Technology**: Optitex BTF (Batch Translation Format) scripting within PDS files.

---

## TEMPLATE ARCHITECTURE

Each template contains:
1. Base pattern geometry (size 50/M)
2. Grading rules for standard sizes
3. BTF parametric rules for MTM (Made-to-Measure)
4. Named measurement parameters matching scan output

```
┌─────────────────────────────────────────────┐
│  Style Template (.pds)                      │
├─────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Base Pattern│  │ Grading Rules       │   │
│  │ (size 50)   │  │ S/M/L/XL/XXL        │   │
│  └─────────────┘  └─────────────────────┘   │
│  ┌─────────────────────────────────────────┐│
│  │ BTF Parametric Rules                    ││
│  │ - Measurement parameters                ││
│  │ - Calculation formulas                  ││
│  │ - Point movement rules                  ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

## TEMPLATE 1: SUIT JACKET (suit_jacket_v1.pds)

### Pieces

| Piece Code | Piece Name | Quantity | Material |
|------------|------------|----------|----------|
| JKT-01 | Front Panel Left | 1 | Shell |
| JKT-02 | Front Panel Right | 1 | Shell |
| JKT-03 | Back Panel | 1 | Shell |
| JKT-04 | Side Panel Left | 1 | Shell |
| JKT-05 | Side Panel Right | 1 | Shell |
| JKT-06 | Sleeve Left | 1 | Shell |
| JKT-07 | Sleeve Right | 1 | Shell |
| JKT-08 | Under Sleeve Left | 1 | Shell |
| JKT-09 | Under Sleeve Right | 1 | Shell |
| JKT-10 | Top Collar | 1 | Shell |
| JKT-11 | Under Collar | 1 | Shell |
| JKT-12 | Lapel Facing Left | 1 | Shell |
| JKT-13 | Lapel Facing Right | 1 | Shell |
| JKT-14 | Front Lining Left | 1 | Lining |
| JKT-15 | Front Lining Right | 1 | Lining |
| JKT-16 | Back Lining | 1 | Lining |
| JKT-17 | Sleeve Lining Left | 1 | Lining |
| JKT-18 | Sleeve Lining Right | 1 | Lining |
| JKT-19 | Chest Canvas Left | 1 | Interlining |
| JKT-20 | Chest Canvas Right | 1 | Interlining |
| JKT-21 | Shoulder Pad Left | 1 | Padding |
| JKT-22 | Shoulder Pad Right | 1 | Padding |
| JKT-23 | Pocket Welt Upper | 2 | Shell |
| JKT-24 | Pocket Welt Lower | 2 | Shell |
| JKT-25 | Pocket Bag | 2 | Pocketing |
| JKT-26 | Breast Pocket Welt | 1 | Shell |
| JKT-27 | Inside Pocket | 2 | Pocketing |

### BTF Parameters

```
; =====================================================
; SUIT JACKET BTF PARAMETRIC RULES
; Template: suit_jacket_v1.pds
; Base Size: 50 (European) / 40 (UK) / M
; =====================================================

; ----- INPUT MEASUREMENTS (from body scan) -----
@PARAM CHEST = 100.0           ; Chest circumference (cm)
@PARAM WAIST = 88.0            ; Waist circumference (cm)
@PARAM HIP = 98.0              ; Hip circumference (cm)
@PARAM SHOULDER_WIDTH = 46.0   ; Shoulder point to shoulder point (cm)
@PARAM BACK_LENGTH = 44.0      ; Nape to waist (cm)
@PARAM FRONT_LENGTH = 45.0     ; Shoulder to waist front (cm)
@PARAM JACKET_LENGTH = 76.0    ; Desired jacket length (cm)
@PARAM ARM_LENGTH = 64.0       ; Shoulder to wrist (cm)
@PARAM BICEP = 32.0            ; Bicep circumference (cm)
@PARAM WRIST = 17.0            ; Wrist circumference (cm)
@PARAM NECK = 40.0             ; Neck circumference (cm)
@PARAM ARMHOLE_DEPTH = 22.0    ; Armhole depth (cm)
@PARAM CHEST_DEPTH = 24.0      ; Front to back at chest (cm)
@PARAM SHOULDER_SLOPE = 22.0   ; Shoulder slope angle (degrees)

; ----- EASE VALUES -----
@PARAM CHEST_EASE = 12.0       ; Total chest ease (cm)
@PARAM WAIST_EASE = 14.0       ; Total waist ease (cm)
@PARAM HIP_EASE = 10.0         ; Total hip ease (cm)
@PARAM SLEEVE_EASE = 8.0       ; Sleeve ease (cm)

; ----- CALCULATED VALUES -----
@CALC HALF_CHEST = (CHEST + CHEST_EASE) / 2
@CALC HALF_WAIST = (WAIST + WAIST_EASE) / 2
@CALC HALF_HIP = (HIP + HIP_EASE) / 2
@CALC HALF_BACK = SHOULDER_WIDTH / 2 - 1.0
@CALC SCYE_DEPTH = ARMHOLE_DEPTH + 2.5
@CALC FRONT_WIDTH = HALF_CHEST * 0.52
@CALC BACK_WIDTH = HALF_CHEST * 0.48
@CALC SIDE_PANEL_WIDTH = HALF_CHEST * 0.15

; ----- PATTERN DIMENSIONS -----
; Front Panel
@CALC FRONT_PANEL_WIDTH = FRONT_WIDTH - SIDE_PANEL_WIDTH
@CALC FRONT_PANEL_LENGTH = JACKET_LENGTH + 2.0
@CALC FRONT_DART_DEPTH = (HALF_CHEST - HALF_WAIST) * 0.3

; Back Panel
@CALC BACK_PANEL_WIDTH = BACK_WIDTH
@CALC BACK_PANEL_LENGTH = JACKET_LENGTH
@CALC BACK_VENT_LENGTH = JACKET_LENGTH * 0.35

; Sleeve
@CALC SLEEVE_LENGTH = ARM_LENGTH - 3.0
@CALC SLEEVE_HEAD_WIDTH = (BICEP + SLEEVE_EASE) * 0.52
@CALC SLEEVE_HEAD_HEIGHT = SCYE_DEPTH * 0.65
@CALC SLEEVE_BOTTOM = WRIST + 4.0

; Collar
@CALC COLLAR_STAND = 3.5
@CALC COLLAR_WIDTH = 5.5
@CALC COLLAR_LENGTH = (NECK / 2) + 2.0

; ----- POINT MOVEMENTS -----
; Format: @MVPNT /PNT=<name> /DX=<delta-x> /DY=<delta-y>

; Front Panel adjustments
@MVPNT /PNT=FP_SHOULDER /DX=(SHOULDER_WIDTH - 46.0) / 2 /DY=0
@MVPNT /PNT=FP_CHEST /DX=(HALF_CHEST - 50.0) /DY=0
@MVPNT /PNT=FP_WAIST /DX=(HALF_WAIST - 44.0) /DY=0
@MVPNT /PNT=FP_HEM /DX=(HALF_HIP - 49.0) /DY=(JACKET_LENGTH - 76.0)

; Back Panel adjustments
@MVPNT /PNT=BP_CENTER_WAIST /DX=0 /DY=(BACK_LENGTH - 44.0)
@MVPNT /PNT=BP_SHOULDER /DX=(SHOULDER_WIDTH - 46.0) / 2 /DY=0
@MVPNT /PNT=BP_HEM /DX=0 /DY=(JACKET_LENGTH - 76.0)

; Armhole adjustments
@MVPNT /PNT=AH_DEPTH /DX=0 /DY=(SCYE_DEPTH - 24.5)
@MVPNT /PNT=AH_WIDTH /DX=(BICEP - 32.0) * 0.3 /DY=0

; Sleeve adjustments
@MVPNT /PNT=SL_HEAD_TOP /DX=0 /DY=(SLEEVE_HEAD_HEIGHT - 16.0)
@MVPNT /PNT=SL_HEAD_WIDTH /DX=(SLEEVE_HEAD_WIDTH - 17.0) /DY=0
@MVPNT /PNT=SL_HEM /DX=(SLEEVE_BOTTOM - 21.0) / 2 /DY=(SLEEVE_LENGTH - 61.0)

; Collar adjustments
@MVPNT /PNT=COL_LENGTH /DX=(COLLAR_LENGTH - 22.0) /DY=0
@MVPNT /PNT=COL_STAND /DX=0 /DY=(COLLAR_STAND - 3.5)
```

### Grading Table (Standard Sizes)

| Size | Chest | Waist | Hip | Shoulder | Back Length |
|------|-------|-------|-----|----------|-------------|
| 44/S | 92 | 80 | 90 | 43 | 42 |
| 46/S+ | 96 | 84 | 94 | 44 | 43 |
| 48/M- | 100 | 88 | 98 | 45 | 43.5 |
| **50/M** | **104** | **92** | **102** | **46** | **44** |
| 52/L | 108 | 96 | 106 | 47 | 44.5 |
| 54/L+ | 112 | 100 | 110 | 48 | 45 |
| 56/XL | 116 | 104 | 114 | 49 | 45.5 |
| 58/XXL | 120 | 108 | 118 | 50 | 46 |

---

## TEMPLATE 2: TROUSERS (trousers_v1.pds)

### Pieces

| Piece Code | Piece Name | Quantity | Material |
|------------|------------|----------|----------|
| TRS-01 | Front Left | 1 | Shell |
| TRS-02 | Front Right | 1 | Shell |
| TRS-03 | Back Left | 1 | Shell |
| TRS-04 | Back Right | 1 | Shell |
| TRS-05 | Waistband Front | 1 | Shell |
| TRS-06 | Waistband Back | 1 | Shell |
| TRS-07 | Fly Piece | 1 | Shell |
| TRS-08 | Fly Facing | 1 | Shell |
| TRS-09 | Fly Extension | 1 | Shell |
| TRS-10 | Front Pocket Bag | 2 | Pocketing |
| TRS-11 | Front Pocket Facing | 2 | Shell |
| TRS-12 | Back Pocket | 2 | Shell |
| TRS-13 | Back Pocket Welt | 2 | Shell |
| TRS-14 | Belt Loop | 7 | Shell |
| TRS-15 | Waistband Curtain | 1 | Lining |

### BTF Parameters

```
; =====================================================
; TROUSERS BTF PARAMETRIC RULES
; Template: trousers_v1.pds
; Base Size: 50 (European) / 34 (UK Waist)
; =====================================================

; ----- INPUT MEASUREMENTS (from body scan) -----
@PARAM WAIST = 88.0            ; Waist circumference (cm)
@PARAM HIP = 98.0              ; Hip circumference at fullest (cm)
@PARAM SEAT = 102.0            ; Seat circumference (cm)
@PARAM THIGH = 58.0            ; Thigh circumference (cm)
@PARAM KNEE = 40.0             ; Knee circumference (cm)
@PARAM CALF = 38.0             ; Calf circumference (cm)
@PARAM ANKLE = 24.0            ; Ankle circumference (cm)
@PARAM INSEAM = 82.0           ; Crotch to floor (cm)
@PARAM OUTSEAM = 108.0         ; Waist to floor (cm)
@PARAM CROTCH_DEPTH = 26.0     ; Waist to crotch (cm)
@PARAM FRONT_RISE = 27.0       ; Front rise (cm)
@PARAM BACK_RISE = 35.0        ; Back rise (cm)

; ----- STYLE PARAMETERS -----
@PARAM TROUSER_LENGTH = 78.0   ; Desired finished length (cm)
@PARAM HEM_WIDTH = 22.0        ; Hem opening width (cm)
@PARAM KNEE_WIDTH = 24.0       ; Knee width (cm)
@PARAM PLEAT_TYPE = 1          ; 0=flat, 1=single, 2=double
@PARAM PLEAT_DEPTH = 3.0       ; Pleat depth (cm)

; ----- EASE VALUES -----
@PARAM WAIST_EASE = 4.0        ; Waistband ease (cm)
@PARAM HIP_EASE = 6.0          ; Hip ease (cm)
@PARAM THIGH_EASE = 8.0        ; Thigh ease (cm)

; ----- CALCULATED VALUES -----
@CALC HALF_WAIST = (WAIST + WAIST_EASE) / 2
@CALC HALF_HIP = (HIP + HIP_EASE) / 2
@CALC HALF_THIGH = (THIGH + THIGH_EASE) / 2
@CALC CROTCH_EXTENSION_FRONT = HALF_HIP * 0.12
@CALC CROTCH_EXTENSION_BACK = HALF_HIP * 0.24
@CALC FRONT_WIDTH = HALF_HIP * 0.48
@CALC BACK_WIDTH = HALF_HIP * 0.52

; ----- POINT MOVEMENTS -----
; Front Panel
@MVPNT /PNT=TF_WAIST_CENTER /DX=0 /DY=0
@MVPNT /PNT=TF_WAIST_SIDE /DX=(FRONT_WIDTH - 24.0) /DY=0
@MVPNT /PNT=TF_HIP /DX=(FRONT_WIDTH - 24.0) /DY=(CROTCH_DEPTH - 26.0)
@MVPNT /PNT=TF_CROTCH /DX=(CROTCH_EXTENSION_FRONT - 6.0) /DY=(CROTCH_DEPTH - 26.0)
@MVPNT /PNT=TF_KNEE /DX=(KNEE_WIDTH/2 - 12.0) /DY=(INSEAM - TROUSER_LENGTH + 45.0)
@MVPNT /PNT=TF_HEM /DX=(HEM_WIDTH/2 - 11.0) /DY=(OUTSEAM - TROUSER_LENGTH)

; Back Panel
@MVPNT /PNT=TB_WAIST_CENTER /DX=0 /DY=(BACK_RISE - 35.0)
@MVPNT /PNT=TB_WAIST_SIDE /DX=(BACK_WIDTH - 26.0) /DY=0
@MVPNT /PNT=TB_SEAT /DX=(BACK_WIDTH - 26.0) /DY=(CROTCH_DEPTH - 26.0)
@MVPNT /PNT=TB_CROTCH /DX=(CROTCH_EXTENSION_BACK - 12.0) /DY=(CROTCH_DEPTH - 26.0)
@MVPNT /PNT=TB_KNEE /DX=(KNEE_WIDTH/2 - 12.0) /DY=(INSEAM - TROUSER_LENGTH + 45.0)
@MVPNT /PNT=TB_HEM /DX=(HEM_WIDTH/2 - 11.0) /DY=(OUTSEAM - TROUSER_LENGTH)

; Waistband
@MVPNT /PNT=WB_LENGTH /DX=(HALF_WAIST - 44.0) /DY=0
```

---

## TEMPLATE 3: DRESS SHIRT (shirt_v1.pds)

### Pieces

| Piece Code | Piece Name | Quantity | Material |
|------------|------------|----------|----------|
| SHT-01 | Front Left | 1 | Shell |
| SHT-02 | Front Right | 1 | Shell |
| SHT-03 | Back | 1 | Shell |
| SHT-04 | Yoke | 1 | Shell |
| SHT-05 | Sleeve Left | 1 | Shell |
| SHT-06 | Sleeve Right | 1 | Shell |
| SHT-07 | Collar Band | 1 | Shell |
| SHT-08 | Collar | 1 | Shell |
| SHT-09 | Cuff Left | 1 | Shell |
| SHT-10 | Cuff Right | 1 | Shell |
| SHT-11 | Placket | 1 | Shell |
| SHT-12 | Sleeve Placket Left | 1 | Shell |
| SHT-13 | Sleeve Placket Right | 1 | Shell |
| SHT-14 | Collar Interlining | 1 | Interlining |
| SHT-15 | Cuff Interlining | 2 | Interlining |

### BTF Parameters

```
; =====================================================
; DRESS SHIRT BTF PARAMETRIC RULES
; Template: shirt_v1.pds
; Base Size: 40 (Collar) / M
; =====================================================

; ----- INPUT MEASUREMENTS (from body scan) -----
@PARAM NECK = 40.0             ; Neck circumference (cm)
@PARAM CHEST = 100.0           ; Chest circumference (cm)
@PARAM WAIST = 88.0            ; Waist circumference (cm)
@PARAM HIP = 98.0              ; Hip circumference (cm)
@PARAM SHOULDER_WIDTH = 46.0   ; Shoulder to shoulder (cm)
@PARAM ARM_LENGTH = 64.0       ; Shoulder to wrist (cm)
@PARAM BICEP = 32.0            ; Bicep circumference (cm)
@PARAM WRIST = 17.0            ; Wrist circumference (cm)
@PARAM BACK_LENGTH = 44.0      ; Nape to waist (cm)
@PARAM SHIRT_LENGTH = 80.0     ; Desired shirt length (cm)
@PARAM YOKE_DEPTH = 8.0        ; Yoke depth (cm)

; ----- FIT PARAMETERS -----
@PARAM FIT_TYPE = 1            ; 0=slim, 1=regular, 2=classic
@PARAM COLLAR_STYLE = 1        ; 0=spread, 1=semi-spread, 2=button-down
@PARAM CUFF_STYLE = 1          ; 0=barrel, 1=french

; ----- EASE VALUES (varies by fit type) -----
@CALC CHEST_EASE = FIT_TYPE == 0 ? 10.0 : (FIT_TYPE == 1 ? 14.0 : 18.0)
@CALC WAIST_EASE = FIT_TYPE == 0 ? 8.0 : (FIT_TYPE == 1 ? 12.0 : 18.0)
@CALC SLEEVE_EASE = FIT_TYPE == 0 ? 6.0 : (FIT_TYPE == 1 ? 8.0 : 10.0)

; ----- CALCULATED VALUES -----
@CALC HALF_CHEST = (CHEST + CHEST_EASE) / 2
@CALC HALF_WAIST = (WAIST + WAIST_EASE) / 2
@CALC COLLAR_SIZE = NECK + 1.5
@CALC CUFF_SIZE = WRIST + 3.0
@CALC SLEEVE_FULL_LENGTH = ARM_LENGTH + 2.5

; ----- POINT MOVEMENTS -----
; Body adjustments
@MVPNT /PNT=SH_SHOULDER /DX=(SHOULDER_WIDTH - 46.0) / 2 /DY=0
@MVPNT /PNT=SH_CHEST /DX=(HALF_CHEST - 57.0) /DY=0
@MVPNT /PNT=SH_WAIST /DX=(HALF_WAIST - 50.0) /DY=(BACK_LENGTH - 44.0)
@MVPNT /PNT=SH_HEM /DX=0 /DY=(SHIRT_LENGTH - 80.0)

; Sleeve adjustments
@MVPNT /PNT=SL_CAP /DX=0 /DY=(BICEP + SLEEVE_EASE - 40.0) * 0.15
@MVPNT /PNT=SL_WIDTH /DX=(BICEP + SLEEVE_EASE - 40.0) / 2 /DY=0
@MVPNT /PNT=SL_CUFF /DX=(CUFF_SIZE - 20.0) / 2 /DY=(SLEEVE_FULL_LENGTH - 66.5)

; Collar adjustments
@MVPNT /PNT=COL_BAND_LENGTH /DX=(COLLAR_SIZE - 41.5) / 2 /DY=0
@MVPNT /PNT=COL_LEAF_LENGTH /DX=(COLLAR_SIZE - 41.5) / 2 /DY=0

; Cuff adjustments
@MVPNT /PNT=CUFF_LENGTH /DX=(CUFF_SIZE - 20.0) /DY=0
```

---

## TEMPLATE 4: WAISTCOAT (waistcoat_v1.pds)

### Pieces

| Piece Code | Piece Name | Quantity | Material |
|------------|------------|----------|----------|
| WST-01 | Front Left | 1 | Shell |
| WST-02 | Front Right | 1 | Shell |
| WST-03 | Back Left | 1 | Lining |
| WST-04 | Back Right | 1 | Lining |
| WST-05 | Front Lining Left | 1 | Lining |
| WST-06 | Front Lining Right | 1 | Lining |
| WST-07 | Front Facing Left | 1 | Shell |
| WST-08 | Front Facing Right | 1 | Shell |
| WST-09 | Welt Pocket Upper | 2 | Shell |
| WST-10 | Welt Pocket Lower | 2 | Shell |
| WST-11 | Pocket Bag | 2 | Pocketing |
| WST-12 | Back Belt | 1 | Lining |
| WST-13 | Back Belt Buckle Tab | 1 | Lining |
| WST-14 | Front Interlining Left | 1 | Interlining |
| WST-15 | Front Interlining Right | 1 | Interlining |

### BTF Parameters

```
; =====================================================
; WAISTCOAT BTF PARAMETRIC RULES
; Template: waistcoat_v1.pds
; Base Size: 50 (European)
; =====================================================

; ----- INPUT MEASUREMENTS (from body scan) -----
@PARAM CHEST = 100.0           ; Chest circumference (cm)
@PARAM WAIST = 88.0            ; Waist circumference (cm)
@PARAM HIP = 98.0              ; Hip circumference (cm)
@PARAM SHOULDER_WIDTH = 46.0   ; Shoulder to shoulder (cm)
@PARAM FRONT_LENGTH = 45.0     ; Shoulder to waist front (cm)
@PARAM BACK_LENGTH = 44.0      ; Nape to waist (cm)
@PARAM WAISTCOAT_LENGTH = 58.0 ; Desired waistcoat length (cm)
@PARAM ARMHOLE_DEPTH = 22.0    ; Armhole depth (cm)
@PARAM NECK = 40.0             ; Neck circumference (cm)

; ----- STYLE PARAMETERS -----
@PARAM BUTTON_COUNT = 6        ; Number of buttons
@PARAM LAPEL_STYLE = 0         ; 0=notch, 1=shawl, 2=none
@PARAM POINT_STYLE = 1         ; 0=straight, 1=pointed

; ----- EASE VALUES -----
@PARAM CHEST_EASE = 6.0        ; Less ease than jacket
@PARAM WAIST_EASE = 4.0        ; Fitted at waist

; ----- CALCULATED VALUES -----
@CALC HALF_CHEST = (CHEST + CHEST_EASE) / 2
@CALC HALF_WAIST = (WAIST + WAIST_EASE) / 2
@CALC FRONT_OPENING = NECK / 6 + 2.0
@CALC POINT_DROP = WAISTCOAT_LENGTH - FRONT_LENGTH + 8.0

; ----- POINT MOVEMENTS -----
; Front Panel
@MVPNT /PNT=WF_SHOULDER /DX=(SHOULDER_WIDTH - 46.0) / 2 - 2.0 /DY=0
@MVPNT /PNT=WF_CHEST /DX=(HALF_CHEST - 53.0) /DY=0
@MVPNT /PNT=WF_WAIST /DX=(HALF_WAIST - 46.0) /DY=(FRONT_LENGTH - 45.0)
@MVPNT /PNT=WF_POINT /DX=0 /DY=(WAISTCOAT_LENGTH - 58.0)
@MVPNT /PNT=WF_ARMHOLE /DX=(HALF_CHEST - 53.0) * 0.3 /DY=(ARMHOLE_DEPTH - 22.0)

; Back Panel
@MVPNT /PNT=WB_SHOULDER /DX=(SHOULDER_WIDTH - 46.0) / 2 - 2.0 /DY=0
@MVPNT /PNT=WB_WAIST /DX=0 /DY=(BACK_LENGTH - 44.0)
@MVPNT /PNT=WB_HEM /DX=0 /DY=(WAISTCOAT_LENGTH - 58.0) - 5.0

; Armhole
@MVPNT /PNT=AH_FRONT /DX=(ARMHOLE_DEPTH - 22.0) * 0.2 /DY=(ARMHOLE_DEPTH - 22.0)
@MVPNT /PNT=AH_BACK /DX=(ARMHOLE_DEPTH - 22.0) * 0.15 /DY=(ARMHOLE_DEPTH - 22.0)

; Neckline
@MVPNT /PNT=NECK_FRONT /DX=(FRONT_OPENING - 8.7) /DY=0
@MVPNT /PNT=NECK_BACK /DX=(NECK - 40.0) / 6 /DY=0
```

---

## MEASUREMENT PARAMETER REFERENCE

### Complete List (80+ Measurements)

All templates use a standardized measurement parameter naming convention:

```
; =====================================================
; STANDARD MEASUREMENT PARAMETERS
; Used across all garment templates
; All values in centimeters (cm)
; =====================================================

; === PRIMARY CIRCUMFERENCES ===
@PARAM NECK = 40.0                  ; Neck base circumference
@PARAM CHEST = 100.0                ; Chest at fullest point
@PARAM WAIST = 88.0                 ; Natural waist
@PARAM HIP = 98.0                   ; Hip at fullest point
@PARAM SEAT = 102.0                 ; Seat circumference
@PARAM BICEP = 32.0                 ; Upper arm at fullest
@PARAM ELBOW = 28.0                 ; Elbow circumference
@PARAM WRIST = 17.0                 ; Wrist circumference
@PARAM THIGH = 58.0                 ; Upper thigh at fullest
@PARAM KNEE = 40.0                  ; Knee circumference
@PARAM CALF = 38.0                  ; Calf at fullest
@PARAM ANKLE = 24.0                 ; Ankle circumference

; === VERTICAL MEASUREMENTS ===
@PARAM BACK_LENGTH = 44.0           ; Nape to waist
@PARAM FRONT_LENGTH = 45.0          ; Shoulder to waist front
@PARAM HALF_BACK_LENGTH = 40.0      ; Nape to shoulder blade
@PARAM SHOULDER_SLOPE = 22.0        ; Shoulder slope (degrees)
@PARAM ARM_LENGTH = 64.0            ; Shoulder point to wrist
@PARAM UPPER_ARM = 35.0             ; Shoulder to elbow
@PARAM FOREARM = 29.0               ; Elbow to wrist
@PARAM INSEAM = 82.0                ; Crotch to floor
@PARAM OUTSEAM = 108.0              ; Waist side to floor
@PARAM CROTCH_DEPTH = 26.0          ; Waist to crotch
@PARAM FRONT_RISE = 27.0            ; Front crotch length
@PARAM BACK_RISE = 35.0             ; Back crotch length

; === HORIZONTAL MEASUREMENTS ===
@PARAM SHOULDER_WIDTH = 46.0        ; Shoulder point to point
@PARAM BACK_WIDTH = 38.0            ; Across back armhole to armhole
@PARAM CHEST_WIDTH = 36.0           ; Across chest armhole to armhole
@PARAM WAIST_FRONT_ARC = 44.0       ; Front waist arc
@PARAM WAIST_BACK_ARC = 44.0        ; Back waist arc
@PARAM HIP_FRONT_ARC = 49.0         ; Front hip arc
@PARAM HIP_BACK_ARC = 49.0          ; Back hip arc

; === DEPTHS ===
@PARAM ARMHOLE_DEPTH = 22.0         ; Scye depth
@PARAM CHEST_DEPTH = 24.0           ; Front to back at chest
@PARAM WAIST_DEPTH = 22.0           ; Front to back at waist
@PARAM HIP_DEPTH = 24.0             ; Front to back at hip

; === COLLAR/NECK ===
@PARAM NECK_WIDTH = 14.0            ; Neck base width
@PARAM NECK_DEPTH_FRONT = 10.0      ; Front neck drop
@PARAM NECK_DEPTH_BACK = 2.5        ; Back neck drop

; === SPECIAL POINTS ===
@PARAM SHOULDER_POINT_HEIGHT = 145.0 ; Floor to shoulder point
@PARAM BUST_POINT_HEIGHT = 120.0    ; Floor to bust point
@PARAM WAIST_HEIGHT = 105.0         ; Floor to waist
@PARAM HIP_HEIGHT = 85.0            ; Floor to hip
@PARAM KNEE_HEIGHT = 48.0           ; Floor to knee
@PARAM CROTCH_HEIGHT = 78.0         ; Floor to crotch
```

---

## FILE STRUCTURE

```
optitex_templates/
├── styles/
│   ├── suit_jacket_v1.pds
│   ├── trousers_v1.pds
│   ├── shirt_v1.pds
│   └── waistcoat_v1.pds
├── btf_rules/
│   ├── jacket_btf.txt
│   ├── trousers_btf.txt
│   ├── shirt_btf.txt
│   └── waistcoat_btf.txt
├── grading/
│   ├── jacket_grade_rules.rul
│   ├── trousers_grade_rules.rul
│   ├── shirt_grade_rules.rul
│   └── waistcoat_grade_rules.rul
├── measurements/
│   └── standard_params.txt
└── batch/
    ├── generate_jacket.bat
    ├── generate_trousers.bat
    ├── generate_shirt.bat
    └── generate_waistcoat.bat
```
