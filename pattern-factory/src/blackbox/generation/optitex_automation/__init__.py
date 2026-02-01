"""
Optitex Automation Module

Complete automation for pattern generation using Optitex PDS.

Features:
- BTF parameter generation (3 formats)
- Batch script generation
- Optitex PDS.exe execution
- Result parsing and validation

Requires:
- Windows OS
- Optitex PDS installed
- OPTITEX_ENABLED=true in environment

Usage:
    from blackbox.generation.optitex_automation import (
        OptitexAutomationWorkflow,
        automate_pattern_generation,
        get_optitex_config,
    )

    # Check if available
    config = get_optitex_config()
    if config.is_available():
        result = automate_pattern_generation(
            measurements={'chest_girth': 102, 'waist_girth': 88},
            template_name='basic_tee',
            order_id='ORD-001'
        )
"""

import logging

logger = logging.getLogger(__name__)

# Config is always available
from blackbox.generation.optitex_automation.config import (
    OptitexConfig,
    get_optitex_config,
    reset_config,
)

__all__ = [
    "OptitexConfig",
    "get_optitex_config",
    "reset_config",
]

# Try to import workflow components (may fail on non-Windows or without deps)
try:
    from blackbox.generation.optitex_automation.workflow import (
        OptitexAutomationWorkflow,
        AutomationResult,
        automate_pattern_generation,
    )

    __all__.extend(
        [
            "OptitexAutomationWorkflow",
            "AutomationResult",
            "automate_pattern_generation",
        ]
    )
except ImportError as e:
    logger.debug(f"Optitex workflow not available: {e}")

try:
    from blackbox.generation.optitex_automation.btf_generator import (
        generate_btf_parameters,
        BTFResult,
    )

    __all__.extend(
        [
            "generate_btf_parameters",
            "BTFResult",
        ]
    )
except ImportError as e:
    logger.debug(f"BTF generator not available: {e}")

try:
    from blackbox.generation.optitex_automation.executor import (
        OptitexExecutor,
        ExecutionResult,
    )

    __all__.extend(
        [
            "OptitexExecutor",
            "ExecutionResult",
        ]
    )
except ImportError as e:
    logger.debug(f"Optitex executor not available: {e}")

try:
    from blackbox.generation.optitex_automation.template_config import (
        get_template,
        list_templates,
        TemplateConfig,
    )

    __all__.extend(
        [
            "get_template",
            "list_templates",
            "TemplateConfig",
        ]
    )
except ImportError as e:
    logger.debug(f"Template config not available: {e}")

try:
    from blackbox.generation.optitex_automation.result_parser import (
        ResultParser,
        NestingMetrics,
    )

    __all__.extend(
        [
            "ResultParser",
            "NestingMetrics",
        ]
    )
except ImportError as e:
    logger.debug(f"Result parser not available: {e}")
