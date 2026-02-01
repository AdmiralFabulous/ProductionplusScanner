"""
BlackBox Translation Module

M. Muller & Sohn pattern translation layer.
Converts body measurements to pattern parameters using proprietary formulas.

No external dependencies required - this is pure Python.
"""

from blackbox.translation.muller_translator import (
    MullerTranslator,
    MullerTranslationError,
    BodyMeasurements,
    PatternParameters,
    FitType,
    FabricType,
    calculate_pattern_params,
)

__all__ = [
    "MullerTranslator",
    "MullerTranslationError",
    "BodyMeasurements",
    "PatternParameters",
    "FitType",
    "FabricType",
    "calculate_pattern_params",
]
