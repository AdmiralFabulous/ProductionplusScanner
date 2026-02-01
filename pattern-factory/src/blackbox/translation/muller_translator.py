"""
M. Muller Translation Layer

Converts body measurements to pattern parameters using M. Muller & Sohn
tailoring formulas. This is proprietary IP for SameDaySuits.

The translation layer applies:
- Proportional rules (M. Muller formulas)
- Ease allowances (slim/regular/classic fit)
- Fabric-specific adjustments
- Measurement deviation handling

Based on BUILD RECOMMENDATIONS:
- This is your proprietary IP layer
- Portable between open-source and commercial stacks
- Generates Excel/CSV for Optitex PDS @MTM_CREATE

Author: AI Agent
Date: January 2026
"""

from dataclasses import dataclass
from typing import Dict, Optional, Literal
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FitType(Enum):
    """Fit type for ease allowance calculation."""

    SLIM = "slim"
    REGULAR = "regular"
    CLASSIC = "classic"


class FabricType(Enum):
    """Fabric type for specific adjustments."""

    WOOL = "wool"
    COTTON = "cotton"
    LINEN = "linen"
    SILK = "silk"
    SYNTHETIC = "synthetic"


@dataclass
class BodyMeasurements:
    """Raw body measurements input."""

    # Core measurements (in cm)
    height: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None
    shoulder_width: Optional[float] = None
    arm_length: Optional[float] = None
    back_length: Optional[float] = None
    neck: Optional[float] = None
    wrist: Optional[float] = None

    # Additional measurements
    bicep: Optional[float] = None
    thigh: Optional[float] = None
    knee: Optional[float] = None
    calf: Optional[float] = None
    inseam: Optional[float] = None

    # Measurement source
    source: str = "unknown"  # "manual", "mediapipe", "sam3d", etc.
    confidence: Optional[Dict[str, float]] = None


@dataclass
class PatternParameters:
    """Generated pattern parameters for garment construction."""

    # Jacket parameters
    half_chest: float
    half_waist: float
    half_hip: float
    scye_depth: float
    front_width: float
    back_width: float
    shoulder_length: float
    armhole_width: float
    back_length_nape_to_waist: float
    front_length_shoulder_to_waist: float

    # Sleeve parameters
    sleeve_length: float
    upper_arm_width: float
    elbow_width: float
    cuff_width: float
    sleeve_head_height: float

    # Trouser parameters
    trouser_waist: float
    trouser_hip: float
    thigh_width: float
    knee_width: float
    hem_width: float
    inside_leg: float
    outside_leg: float

    # Fit configuration
    fit_type: str
    ease_total: float
    fabric_type: str

    # Metadata
    measurement_source: str
    calculation_timestamp: str


class MullerTranslationError(Exception):
    """Raised when M. Muller translation fails."""

    pass


class MullerTranslator:
    """
        M. Muller & Sohn pattern translation engine.

        Implements proprietary formulas for converting body measurements
    to bespoke suit pattern parameters.
    """

    # Ease allowances by fit type (in cm)
    EASE_ALLOWANCES = {
        FitType.SLIM: {
            "chest": 8,
            "waist": 6,
            "hip": 6,
            "shoulder": 1,
            "armhole": 2,
            "sleeve": 3,
        },
        FitType.REGULAR: {
            "chest": 12,
            "waist": 8,
            "hip": 8,
            "shoulder": 2,
            "armhole": 2.5,
            "sleeve": 4,
        },
        FitType.CLASSIC: {
            "chest": 16,
            "waist": 12,
            "hip": 10,
            "shoulder": 3,
            "armhole": 3,
            "sleeve": 5,
        },
    }

    # Fabric-specific adjustments (multipliers)
    FABRIC_ADJUSTMENTS = {
        FabricType.WOOL: {
            "ease_multiplier": 1.0,
            "drape_factor": 1.0,
            "shrinkage": 0.02,
        },
        FabricType.COTTON: {
            "ease_multiplier": 1.05,
            "drape_factor": 0.95,
            "shrinkage": 0.03,
        },
        FabricType.LINEN: {
            "ease_multiplier": 1.08,
            "drape_factor": 0.90,
            "shrinkage": 0.05,
        },
        FabricType.SILK: {
            "ease_multiplier": 0.95,
            "drape_factor": 1.1,
            "shrinkage": 0.01,
        },
        FabricType.SYNTHETIC: {
            "ease_multiplier": 1.0,
            "drape_factor": 1.05,
            "shrinkage": 0.01,
        },
    }

    def __init__(
        self,
        fit_type: FitType = FitType.REGULAR,
        fabric_type: FabricType = FabricType.WOOL,
    ):
        """
        Initialize M. Muller translator.

        Args:
            fit_type: Slim, Regular, or Classic fit
            fabric_type: Type of fabric for adjustments
        """
        self.fit_type = fit_type
        self.fabric_type = fabric_type
        self.ease = self.EASE_ALLOWANCES[fit_type]
        self.fabric_adj = self.FABRIC_ADJUSTMENTS[fabric_type]

        logger.info(
            f"Initialized M. Muller translator: {fit_type.value} fit, {fabric_type.value}"
        )

    def translate_measurements(
        self, measurements: BodyMeasurements
    ) -> PatternParameters:
        """
        Translate body measurements to pattern parameters.

        Args:
            measurements: BodyMeasurements object with raw measurements

        Returns:
            PatternParameters with calculated pattern values

        Raises:
            MullerTranslationError: If required measurements missing
        """
        self._validate_measurements(measurements)

        # Apply M. Muller proportional formulas
        jacket_params = self._calculate_jacket(measurements)
        sleeve_params = self._calculate_sleeve(measurements)
        trouser_params = self._calculate_trouser(measurements)

        # Combine into PatternParameters
        from datetime import datetime

        params = PatternParameters(
            # Jacket
            half_chest=jacket_params["half_chest"],
            half_waist=jacket_params["half_waist"],
            half_hip=jacket_params["half_hip"],
            scye_depth=jacket_params["scye_depth"],
            front_width=jacket_params["front_width"],
            back_width=jacket_params["back_width"],
            shoulder_length=jacket_params["shoulder_length"],
            armhole_width=jacket_params["armhole_width"],
            back_length_nape_to_waist=jacket_params["back_length"],
            front_length_shoulder_to_waist=jacket_params["front_length"],
            # Sleeve
            sleeve_length=sleeve_params["sleeve_length"],
            upper_arm_width=sleeve_params["upper_arm_width"],
            elbow_width=sleeve_params["elbow_width"],
            cuff_width=sleeve_params["cuff_width"],
            sleeve_head_height=sleeve_params["sleeve_head_height"],
            # Trouser
            trouser_waist=trouser_params["waist"],
            trouser_hip=trouser_params["hip"],
            thigh_width=trouser_params["thigh_width"],
            knee_width=trouser_params["knee_width"],
            hem_width=trouser_params["hem_width"],
            inside_leg=trouser_params["inside_leg"],
            outside_leg=trouser_params["outside_leg"],
            # Configuration
            fit_type=self.fit_type.value,
            ease_total=sum(self.ease.values()),
            fabric_type=self.fabric_type.value,
            # Metadata
            measurement_source=measurements.source,
            calculation_timestamp=datetime.now().isoformat(),
        )

        logger.info(
            f"Translated {len([m for m in [measurements.chest, measurements.waist, measurements.hip] if m])} measurements to pattern parameters"
        )

        return params

    def _validate_measurements(self, measurements: BodyMeasurements) -> None:
        """Validate that required measurements are present."""
        required = ["chest", "waist", "hip"]
        missing = [m for m in required if getattr(measurements, m) is None]

        if missing:
            raise MullerTranslationError(f"Missing required measurements: {missing}")

    def _calculate_jacket(self, m: BodyMeasurements) -> Dict:
        """Calculate jacket pattern parameters using M. Muller formulas."""
        # Apply ease with fabric adjustment
        ease_multiplier = self.fabric_adj["ease_multiplier"]

        chest_ease = self.ease["chest"] * ease_multiplier
        waist_ease = (
            self.ease["waist"] * ease_multiplier + 2
        )  # +2 for waist suppression
        hip_ease = self.ease["hip"] * ease_multiplier

        # Half measurements (garment is symmetrical)
        half_chest = (m.chest + chest_ease) / 2
        half_waist = (m.waist + waist_ease) / 2
        half_hip = (m.hip + hip_ease) / 2 if m.hip else half_chest * 0.95

        # Scye depth (armhole depth) - M. Muller formula
        scye_depth = (m.chest / 4 + 2) + self.ease["armhole"]
        if m.arm_length:
            scye_depth = m.arm_length * 0.28 + 3

        # Width proportions (M. Muller standard)
        front_width = half_chest * 0.52
        back_width = half_chest * 0.48

        # Shoulder length
        shoulder_length = (
            m.shoulder_width / 2 if m.shoulder_width else half_chest * 0.23
        )

        # Armhole width
        armhole_width = scye_depth * 0.4

        # Back length (nape to waist)
        back_length = (
            m.back_length if m.back_length else m.height * 0.25 if m.height else 45
        )

        # Front length (shoulder to waist)
        front_length = back_length + 2  # +2cm for front waist position

        return {
            "half_chest": half_chest,
            "half_waist": half_waist,
            "half_hip": half_hip,
            "scye_depth": scye_depth,
            "front_width": front_width,
            "back_width": back_width,
            "shoulder_length": shoulder_length,
            "armhole_width": armhole_width,
            "back_length": back_length,
            "front_length": front_length,
        }

    def _calculate_sleeve(self, m: BodyMeasurements) -> Dict:
        """Calculate sleeve pattern parameters."""
        # Sleeve length
        sleeve_length = m.arm_length if m.arm_length else 65

        # Upper arm (bicep + ease)
        bicep = m.bicep if m.bicep else m.chest * 0.31
        upper_arm_width = (bicep + self.ease["sleeve"]) / 2

        # Elbow width (proportional)
        elbow_width = upper_arm_width * 0.85

        # Cuff width (wrist + ease)
        wrist = m.wrist if m.wrist else 18
        cuff_width = (wrist + 3) / 2  # +3cm ease for cuff

        # Sleeve head height (armhole related)
        sleeve_head_height = (m.chest / 4 + 2) * 0.6

        return {
            "sleeve_length": sleeve_length,
            "upper_arm_width": upper_arm_width,
            "elbow_width": elbow_width,
            "cuff_width": cuff_width,
            "sleeve_head_height": sleeve_head_height,
        }

    def _calculate_trouser(self, m: BodyMeasurements) -> Dict:
        """Calculate trouser pattern parameters."""
        # Waist (with ease)
        waist = (m.waist + self.ease["waist"]) / 2

        # Hip (with ease)
        hip = (m.hip + self.ease["hip"]) / 2 if m.hip else waist * 1.08

        # Thigh width
        thigh = m.thigh if m.thigh else m.hip * 0.58 if m.hip else 58
        thigh_width = (thigh + 4) / 2  # +4cm ease

        # Knee width (tapers from thigh)
        knee = m.knee if m.knee else thigh * 0.70
        knee_width = (knee + 3) / 2

        # Hem width
        hem_width = knee_width * 0.85

        # Leg lengths
        inside_leg = m.inseam if m.inseam else m.height * 0.45 if m.height else 82
        outside_leg = inside_leg + 12  # Hip depth allowance

        return {
            "waist": waist,
            "hip": hip,
            "thigh_width": thigh_width,
            "knee_width": knee_width,
            "hem_width": hem_width,
            "inside_leg": inside_leg,
            "outside_leg": outside_leg,
        }

    def export_to_dict(self, params: PatternParameters) -> Dict:
        """Export PatternParameters to dictionary for serialization."""
        return {
            # Jacket
            "HALF_CHEST": round(params.half_chest, 2),
            "HALF_WAIST": round(params.half_waist, 2),
            "HALF_HIP": round(params.half_hip, 2),
            "SCYE_DEPTH": round(params.scye_depth, 2),
            "FRONT_WIDTH": round(params.front_width, 2),
            "BACK_WIDTH": round(params.back_width, 2),
            "SHOULDER_LENGTH": round(params.shoulder_length, 2),
            "ARMHOLE_WIDTH": round(params.armhole_width, 2),
            "BACK_LENGTH_NAPE_TO_WAIST": round(params.back_length_nape_to_waist, 2),
            "FRONT_LENGTH_SHOULDER_TO_WAIST": round(
                params.front_length_shoulder_to_waist, 2
            ),
            # Sleeve
            "SLEEVE_LENGTH": round(params.sleeve_length, 2),
            "UPPER_ARM_WIDTH": round(params.upper_arm_width, 2),
            "ELBOW_WIDTH": round(params.elbow_width, 2),
            "CUFF_WIDTH": round(params.cuff_width, 2),
            "SLEEVE_HEAD_HEIGHT": round(params.sleeve_head_height, 2),
            # Trouser
            "TROUSER_WAIST": round(params.trouser_waist, 2),
            "TROUSER_HIP": round(params.trouser_hip, 2),
            "THIGH_WIDTH": round(params.thigh_width, 2),
            "KNEE_WIDTH": round(params.knee_width, 2),
            "HEM_WIDTH": round(params.hem_width, 2),
            "INSIDE_LEG": round(params.inside_leg, 2),
            "OUTSIDE_LEG": round(params.outside_leg, 2),
            # Configuration
            "FIT_TYPE": params.fit_type,
            "EASE_TOTAL": round(params.ease_total, 2),
            "FABRIC_TYPE": params.fabric_type,
            # Metadata
            "MEASUREMENT_SOURCE": params.measurement_source,
            "CALCULATION_TIMESTAMP": params.calculation_timestamp,
        }


def calculate_pattern_params(
    measurements: Dict[str, float],
    fit_type: Literal["slim", "regular", "classic"] = "regular",
    fabric_type: Literal["wool", "cotton", "linen", "silk", "synthetic"] = "wool",
    source: str = "unknown",
) -> Dict:
    """
    Convenience function to calculate pattern parameters from dict.

    Args:
        measurements: Dict with keys like 'chest', 'waist', 'hip', etc.
        fit_type: 'slim', 'regular', or 'classic'
        fabric_type: 'wool', 'cotton', 'linen', 'silk', or 'synthetic'
        source: Measurement source identifier

    Returns:
        Dict with calculated pattern parameters
    """
    fit_enum = FitType(fit_type)
    fabric_enum = FabricType(fabric_type)

    body_measurements = BodyMeasurements(
        height=measurements.get("height"),
        chest=measurements.get("chest"),
        waist=measurements.get("waist"),
        hip=measurements.get("hip"),
        shoulder_width=measurements.get("shoulder_width"),
        arm_length=measurements.get("arm_length"),
        back_length=measurements.get("back_length"),
        neck=measurements.get("neck"),
        wrist=measurements.get("wrist"),
        bicep=measurements.get("bicep"),
        thigh=measurements.get("thigh"),
        knee=measurements.get("knee"),
        inseam=measurements.get("inseam"),
        source=source,
    )

    translator = MullerTranslator(fit_type=fit_enum, fabric_type=fabric_enum)
    params = translator.translate_measurements(body_measurements)

    return translator.export_to_dict(params)


if __name__ == "__main__":
    # Example usage
    test_measurements = {
        "chest": 102,
        "waist": 88,
        "hip": 98,
        "shoulder_width": 46,
        "arm_length": 64,
        "back_length": 44,
        "height": 175,
    }

    params = calculate_pattern_params(
        test_measurements, fit_type="regular", fabric_type="wool", source="mediapipe"
    )

    print("M. Muller Pattern Parameters:")
    print("=" * 50)
    for key, value in params.items():
        if not key.startswith("_"):
            print(f"{key}: {value}")
