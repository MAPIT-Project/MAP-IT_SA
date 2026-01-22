# isort: skip_file
"""
Test Scenario Runner Module.

This module provides the ProductionQualityRunner class and supporting dataclasses
for executing and evaluating MAPIT conversation scenarios against the live API.

This module exports from tests.test_production_quality_validation to provide
the PRD-specified import path: `tests.quality.test_scenario_runner`

Per MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md Task 001:
- ProductionQualityRunner class
- ScenarioExecutionResult dataclass
- TurnResult dataclass
- Pattern detection for failure categories

Usage:
    from tests.quality.test_scenario_runner import ProductionQualityRunner

    runner = ProductionQualityRunner(base_url="http://localhost:8000")
    result = await runner.run_scenario("tests/scenarios/advanced/programme_discovery.yaml")
    print(f"Score: {result.average_quality_score}")
"""

# Re-export all public classes and constants from the main implementation
from tests.test_production_quality_validation import (
    # Main runner class
    ProductionQualityRunner,
    # Dataclasses
    ScenarioExecutionResult,
    TurnResult,
    FailureRecord,
    # Enums
    FailureCategory,
    FailureSeverity,
    # Pattern constants for failure detection
    NO_RESULTS_PATTERNS,
    DEFLECTION_PATTERNS,
    REQUIRED_FIELDS,
    KNOWN_FACTS,
)

# Also export from failure_detector module for comprehensive failure detection
from tests.validators.failure_detector import (
    # Main detection function
    detect_all,
    # Detector classes
    NoResultsDetector,
    IncorrectDataDetector,
    MissingDataDetector,
    UnexpectedBehaviorDetector,
    PoorQualityDetector,
    # Base class for custom detectors
    BaseDetector,
    # Dataclasses
    TurnResult as FailureDetectorTurnResult,
    FailureRecord as FailureDetectorRecord,
    # Helper function
    create_turn_result_from_conversation_turn,
)

__all__ = [
    # Main runner
    "ProductionQualityRunner",
    # Dataclasses from production quality validation
    "ScenarioExecutionResult",
    "TurnResult",
    "FailureRecord",
    # Enums
    "FailureCategory",
    "FailureSeverity",
    # Pattern constants
    "NO_RESULTS_PATTERNS",
    "DEFLECTION_PATTERNS",
    "REQUIRED_FIELDS",
    "KNOWN_FACTS",
    # Failure detector exports
    "detect_all",
    "NoResultsDetector",
    "IncorrectDataDetector",
    "MissingDataDetector",
    "UnexpectedBehaviorDetector",
    "PoorQualityDetector",
    "BaseDetector",
    "FailureDetectorTurnResult",
    "FailureDetectorRecord",
    "create_turn_result_from_conversation_turn",
]
