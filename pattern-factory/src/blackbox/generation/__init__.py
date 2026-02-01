"""
BlackBox Generation Module

Pattern generation and output:
- DXF/HPGL file generation (requires ezdxf)
- Optitex automation (requires Windows + Optitex)
"""

import logging

logger = logging.getLogger(__name__)

__all__ = []

# DXF generation (requires ezdxf)
try:
    from blackbox.generation.dxf_generator import (
        DXFGenerator,
        generate_suit_patterns,
    )

    __all__.extend(
        [
            "DXFGenerator",
            "generate_suit_patterns",
        ]
    )
except ImportError as e:
    logger.debug(f"DXF generation not available: {e}")

# Optitex automation (requires Windows + Optitex)
try:
    from blackbox.generation.optitex_automation import (
        OptitexAutomationWorkflow,
        automate_pattern_generation,
        get_optitex_config,
    )

    __all__.extend(
        [
            "OptitexAutomationWorkflow",
            "automate_pattern_generation",
            "get_optitex_config",
        ]
    )
except ImportError as e:
    logger.debug(f"Optitex automation not available: {e}")
