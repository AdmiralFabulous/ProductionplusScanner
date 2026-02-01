"""
Optitex Template Configuration

Maps body measurements to PDS template points and files.
"""

from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TemplateConfig:
    """Configuration for an Optitex template."""

    name: str
    pds_file: Path
    description: str
    garment_type: str
    # Measurement to point mapping
    # Format: {body_measurement: [(point_name, adjustment_type, factor), ...]}
    measurement_mapping: Dict[str, List[Tuple[str, str, float]]]
    # Default fabric width
    default_fabric_width: float = 150.0
    # Nesting algorithm preference
    nesting_algorithm: str = "PRO"  # PRO, TEXTILE, COMPACTION, etc.


# Template configurations
TEMPLATES = {
    "basic_tee": TemplateConfig(
        name="Basic Tee",
        pds_file=Path("templates/Basic Tee_2D.PDS"),
        description="Simple t-shirt template",
        garment_type="top",
        measurement_mapping={
            "chest_girth": [
                ("FP_CHEST", "scale_x", 0.25),  # Front chest width
                ("BP_CHEST", "scale_x", 0.25),  # Back chest width
            ],
            "waist_girth": [
                ("FP_WAIST", "scale_x", 0.25),
                ("BP_WAIST", "scale_x", 0.25),
            ],
            "shoulder_width": [
                ("FP_SHOULDER", "move_x", 0.5),
                ("BP_SHOULDER", "move_x", 0.5),
            ],
            "arm_length": [
                ("SLV_HEM", "move_y", 1.0),
            ],
            "torso_length": [
                ("FP_HEM", "move_y", 0.5),
                ("BP_HEM", "move_y", 0.5),
            ],
        },
        default_fabric_width=150.0,
        nesting_algorithm="PRO",
    ),
    "woven_shirt": TemplateConfig(
        name="Woven Shirt",
        pds_file=Path("templates/Woven SS Shirt_2D.PDS"),
        description="Formal woven shirt",
        garment_type="top",
        measurement_mapping={
            "chest_girth": [
                ("FP_CHEST", "scale_x", 0.25),
                ("BP_CHEST", "scale_x", 0.25),
            ],
            "waist_girth": [
                ("FP_WAIST", "scale_x", 0.25),
                ("BP_WAIST", "scale_x", 0.25),
            ],
            "neck_girth": [
                ("FP_NECK", "scale_x", 0.15),
                ("BP_NECK", "scale_x", 0.15),
            ],
            "shoulder_width": [
                ("FP_SHOULDER", "move_x", 0.5),
                ("BP_SHOULDER", "move_x", 0.5),
            ],
            "arm_length": [
                ("SLV_HEM", "move_y", 1.0),
            ],
            "wrist_girth": [
                ("SLV_CUFF", "scale_x", 0.15),
            ],
        },
        default_fabric_width=150.0,
        nesting_algorithm="PRO",
    ),
    "skinny_trousers": TemplateConfig(
        name="Skinny Trousers",
        pds_file=Path("templates/Skinny Trousers_2D.PDS"),
        description="Fitted trousers",
        garment_type="bottom",
        measurement_mapping={
            "waist_girth": [
                ("FP_WAIST", "scale_x", 0.25),
                ("BP_WAIST", "scale_x", 0.25),
            ],
            "hip_girth": [
                ("FP_HIP", "scale_x", 0.25),
                ("BP_HIP", "scale_x", 0.25),
            ],
            "thigh_girth": [
                ("FP_THIGH", "scale_x", 0.25),
                ("BP_THIGH", "scale_x", 0.25),
            ],
            "knee_girth": [
                ("FP_KNEE", "scale_x", 0.25),
                ("BP_KNEE", "scale_x", 0.25),
            ],
            "inseam": [
                ("LEG_HEM", "move_y", 1.0),
            ],
            "calf_girth": [
                ("FP_CALF", "scale_x", 0.25),
                ("BP_CALF", "scale_x", 0.25),
            ],
        },
        default_fabric_width=150.0,
        nesting_algorithm="PRO",
    ),
}


def get_template(template_name: str) -> TemplateConfig:
    """Get template configuration by name."""
    if template_name not in TEMPLATES:
        raise ValueError(
            f"Unknown template: {template_name}. Available: {list(TEMPLATES.keys())}"
        )
    return TEMPLATES[template_name]


def list_templates() -> List[str]:
    """List all available template names."""
    return list(TEMPLATES.keys())
