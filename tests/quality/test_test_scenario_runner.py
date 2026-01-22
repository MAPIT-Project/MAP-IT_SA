# isort: skip_file
"""
Unit tests for test_scenario_runner module.

Tests that the module correctly exports all required classes and constants
from tests.test_production_quality_validation and tests.validators.failure_detector.

Per MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md Task 001:
- Verify ProductionQualityRunner class is available
- Verify ScenarioExecutionResult dataclass is available
- Verify TurnResult dataclass is available
- Verify pattern detection for failure categories works
"""


# =============================================================================
# Test Module Imports
# =============================================================================


class TestModuleImports:
    """Tests that all required exports are available from the module."""

    def test_import_production_quality_runner(self):
        """Test that ProductionQualityRunner can be imported."""
        from tests.quality.test_scenario_runner import ProductionQualityRunner

        assert ProductionQualityRunner is not None
        assert hasattr(ProductionQualityRunner, "run_scenario")
        assert hasattr(ProductionQualityRunner, "evaluate_turn")
        assert hasattr(ProductionQualityRunner, "generate_report")

    def test_import_scenario_execution_result(self):
        """Test that ScenarioExecutionResult can be imported."""
        from tests.quality.test_scenario_runner import ScenarioExecutionResult

        assert ScenarioExecutionResult is not None
        # Verify it's a dataclass with expected fields
        result = ScenarioExecutionResult(scenario_name="Test")
        assert result.scenario_name == "Test"
        assert hasattr(result, "turns")
        assert hasattr(result, "failures")
        assert hasattr(result, "to_dict")

    def test_import_turn_result(self):
        """Test that TurnResult can be imported."""
        from tests.quality.test_scenario_runner import TurnResult

        assert TurnResult is not None
        # Verify it's a dataclass with expected fields
        result = TurnResult(
            query="Test query",
            response="Test response",
            quality_score=85.0,
            factual_score=90.0,
            turn_number=0,
        )
        assert result.query == "Test query"
        assert result.quality_score == 85.0
        assert hasattr(result, "to_dict")

    def test_import_failure_record(self):
        """Test that FailureRecord can be imported."""
        from tests.quality.test_scenario_runner import (
            FailureCategory,
            FailureRecord,
            FailureSeverity,
        )

        assert FailureRecord is not None
        # Verify it's a dataclass with expected fields
        record = FailureRecord(
            category=FailureCategory.NO_RESULTS,
            severity=FailureSeverity.CRITICAL,
            description="Test failure",
            turn_number=0,
        )
        assert record.category == FailureCategory.NO_RESULTS
        assert record.severity == FailureSeverity.CRITICAL
        assert hasattr(record, "to_dict")

    def test_import_failure_enums(self):
        """Test that FailureCategory and FailureSeverity enums are available."""
        from tests.quality.test_scenario_runner import FailureCategory, FailureSeverity

        # Verify all expected categories exist
        assert FailureCategory.NO_RESULTS == "NO_RESULTS"
        assert FailureCategory.INCORRECT_DATA == "INCORRECT_DATA"
        assert FailureCategory.MISSING_DATA == "MISSING_DATA"
        assert FailureCategory.UNEXPECTED_BEHAVIOR == "UNEXPECTED_BEHAVIOR"
        assert FailureCategory.POOR_QUALITY == "POOR_QUALITY"

        # Verify severity levels
        assert FailureSeverity.CRITICAL == "CRITICAL"
        assert FailureSeverity.HIGH == "HIGH"
        assert FailureSeverity.MEDIUM == "MEDIUM"

    def test_import_pattern_constants(self):
        """Test that pattern constants are available."""
        from tests.quality.test_scenario_runner import (
            NO_RESULTS_PATTERNS,
            DEFLECTION_PATTERNS,
            REQUIRED_FIELDS,
            KNOWN_FACTS,
        )

        # Verify patterns are lists with content
        assert isinstance(NO_RESULTS_PATTERNS, list)
        assert len(NO_RESULTS_PATTERNS) > 0
        assert "I don't have" in NO_RESULTS_PATTERNS

        assert isinstance(DEFLECTION_PATTERNS, list)
        assert len(DEFLECTION_PATTERNS) > 0
        assert "you might want to" in DEFLECTION_PATTERNS

        # Verify required fields dict
        assert isinstance(REQUIRED_FIELDS, dict)
        assert "call_search" in REQUIRED_FIELDS
        assert "project_search" in REQUIRED_FIELDS

        # Verify known facts dict
        assert isinstance(KNOWN_FACTS, dict)
        assert "horizon_europe" in KNOWN_FACTS
        assert "erasmus_plus" in KNOWN_FACTS
        assert "creative_europe" in KNOWN_FACTS


class TestFailureDetectorImports:
    """Tests that failure detector exports are available."""

    def test_import_detect_all(self):
        """Test that detect_all function is available."""
        from tests.quality.test_scenario_runner import detect_all

        assert detect_all is not None
        assert callable(detect_all)

    def test_import_detector_classes(self):
        """Test that all detector classes are available."""
        from tests.quality.test_scenario_runner import (
            NoResultsDetector,
            IncorrectDataDetector,
            MissingDataDetector,
            UnexpectedBehaviorDetector,
            PoorQualityDetector,
            BaseDetector,
        )

        # Verify all classes can be instantiated
        no_results = NoResultsDetector()
        assert no_results is not None
        assert hasattr(no_results, "detect")

        incorrect_data = IncorrectDataDetector()
        assert incorrect_data is not None

        missing_data = MissingDataDetector()
        assert missing_data is not None

        unexpected = UnexpectedBehaviorDetector()
        assert unexpected is not None

        poor_quality = PoorQualityDetector()
        assert poor_quality is not None

        # Verify BaseDetector is abstract
        assert BaseDetector is not None

    def test_import_helper_function(self):
        """Test that helper function is available."""
        from tests.quality.test_scenario_runner import create_turn_result_from_conversation_turn

        assert create_turn_result_from_conversation_turn is not None
        assert callable(create_turn_result_from_conversation_turn)


# =============================================================================
# Test Basic Functionality Through Re-exported Classes
# =============================================================================


class TestProductionQualityRunnerBasics:
    """Tests that ProductionQualityRunner works through re-export."""

    def test_runner_initialization(self):
        """Test that runner can be initialized with default parameters."""
        from tests.quality.test_scenario_runner import ProductionQualityRunner

        runner = ProductionQualityRunner()
        assert runner.base_url == "http://localhost:8000"
        assert runner.passing_threshold == 80
        assert runner.factual_threshold == 0.9

    def test_runner_custom_parameters(self):
        """Test that runner accepts custom parameters."""
        from tests.quality.test_scenario_runner import ProductionQualityRunner

        runner = ProductionQualityRunner(
            base_url="http://custom:9000",
            passing_threshold=85,
            factual_threshold=0.95,
        )
        assert runner.base_url == "http://custom:9000"
        assert runner.passing_threshold == 85
        assert runner.factual_threshold == 0.95

    def test_runner_has_agents(self):
        """Test that runner initializes all required agents."""
        from tests.quality.test_scenario_runner import ProductionQualityRunner

        runner = ProductionQualityRunner()
        assert hasattr(runner, "quality_evaluator")
        assert hasattr(runner, "cross_programme_agent")
        assert hasattr(runner, "goal_tracking_agent")
        assert hasattr(runner, "personalization_agent")
        assert hasattr(runner, "context_validator")


class TestScenarioExecutionResultBasics:
    """Tests that ScenarioExecutionResult works through re-export."""

    def test_result_default_values(self):
        """Test that result has correct default values."""
        from tests.quality.test_scenario_runner import ScenarioExecutionResult

        result = ScenarioExecutionResult(scenario_name="Test")
        assert result.scenario_name == "Test"
        assert result.turns == []
        assert result.failures == []
        assert result.scores == {}
        assert result.execution_time_ms == 0.0

    def test_result_average_quality_score(self):
        """Test average quality score calculation."""
        from tests.quality.test_scenario_runner import ScenarioExecutionResult, TurnResult

        result = ScenarioExecutionResult(
            scenario_name="Test",
            turns=[
                TurnResult(
                    query="Q1", response="R1", quality_score=80, factual_score=90, turn_number=0
                ),
                TurnResult(
                    query="Q2", response="R2", quality_score=90, factual_score=95, turn_number=1
                ),
            ],
        )
        assert result.average_quality_score == 85.0

    def test_result_passed_property(self):
        """Test passed property logic."""
        from tests.quality.test_scenario_runner import (
            ScenarioExecutionResult,
            TurnResult,
            FailureRecord,
            FailureCategory,
            FailureSeverity,
        )

        # Passing result (score >= 80, no critical failures)
        passing_result = ScenarioExecutionResult(
            scenario_name="Test",
            turns=[
                TurnResult(
                    query="Q1", response="R1", quality_score=85, factual_score=90, turn_number=0
                ),
            ],
        )
        assert passing_result.passed is True
        assert passing_result.status == "PASS"

        # Failing result (critical failure)
        failing_result = ScenarioExecutionResult(
            scenario_name="Test",
            turns=[
                TurnResult(
                    query="Q1", response="R1", quality_score=85, factual_score=90, turn_number=0
                ),
            ],
            failures=[
                FailureRecord(
                    category=FailureCategory.NO_RESULTS,
                    severity=FailureSeverity.CRITICAL,
                    description="Critical failure",
                    turn_number=0,
                )
            ],
        )
        assert failing_result.passed is False
        assert failing_result.status == "FAIL"

    def test_result_serialization(self):
        """Test to_dict serialization."""
        from tests.quality.test_scenario_runner import ScenarioExecutionResult, TurnResult

        result = ScenarioExecutionResult(
            scenario_name="Test Scenario",
            turns=[
                TurnResult(
                    query="Q1", response="R1", quality_score=85, factual_score=90, turn_number=0
                ),
            ],
        )
        data = result.to_dict()

        assert data["scenario_name"] == "Test Scenario"
        assert data["status"] == "PASS"
        assert data["average_quality_score"] == 85.0
        assert len(data["turns"]) == 1
        assert "timestamp" in data


class TestTurnResultBasics:
    """Tests that TurnResult works through re-export."""

    def test_turn_result_passed_property(self):
        """Test passed property logic."""
        from tests.quality.test_scenario_runner import (
            TurnResult,
            FailureRecord,
            FailureCategory,
            FailureSeverity,
        )

        # Passing turn (score >= 80, no critical failures)
        passing_turn = TurnResult(
            query="Q1",
            response="R1",
            quality_score=85,
            factual_score=90,
            turn_number=0,
        )
        assert passing_turn.passed is True

        # Failing turn (critical failure)
        failing_turn = TurnResult(
            query="Q1",
            response="R1",
            quality_score=85,
            factual_score=90,
            turn_number=0,
            failures=[
                FailureRecord(
                    category=FailureCategory.NO_RESULTS,
                    severity=FailureSeverity.CRITICAL,
                    description="Critical failure",
                    turn_number=0,
                )
            ],
        )
        assert failing_turn.passed is False

        # Failing turn (low score)
        low_score_turn = TurnResult(
            query="Q1",
            response="R1",
            quality_score=70,  # Below 80
            factual_score=90,
            turn_number=0,
        )
        assert low_score_turn.passed is False


class TestFailureDetectionBasics:
    """Tests that failure detection works through re-export."""

    def test_detect_all_function(self):
        """Test detect_all finds failures."""
        from tests.quality.test_scenario_runner import (
            detect_all,
            FailureDetectorTurnResult,
            FailureCategory,
        )

        # Create a turn with no-results pattern
        turn = FailureDetectorTurnResult(
            query="Find calls",
            response="I couldn't find any results.",
            tools_used=["search_funding_calls"],
            tool_results=[{"tool": "search_funding_calls", "result": {"calls": []}}],
        )

        failures = detect_all(turn, turn_number=0)
        assert len(failures) > 0
        # Should detect short response and/or no-results pattern
        categories = [f.category for f in failures]
        assert FailureCategory.NO_RESULTS in categories

    def test_no_results_detector(self):
        """Test NoResultsDetector through re-export."""
        from tests.quality.test_scenario_runner import (
            NoResultsDetector,
            FailureDetectorTurnResult,
        )

        detector = NoResultsDetector()
        turn = FailureDetectorTurnResult(
            query="Find calls",
            response="I don't have any information about that.",
        )

        failures = detector.detect(turn, turn_number=0)
        assert len(failures) > 0

    def test_good_response_passes(self):
        """Test that a good response doesn't trigger failures."""
        from tests.quality.test_scenario_runner import (
            NoResultsDetector,
            FailureDetectorTurnResult,
        )

        detector = NoResultsDetector()
        good_response = """Based on my search, I found **15 funding opportunities** for hydrogen:

## Top Calls

1. **HORIZON-CL5-2025-D3-01** - Clean Hydrogen Partnership
   - Deadline: March 15, 2025
   - Budget: €50 million

### Next Steps
You can apply through the EU Funding & Tenders Portal."""

        turn = FailureDetectorTurnResult(
            query="Find calls for hydrogen",
            response=good_response,
            tools_used=["search_funding_calls"],
            tool_results=[
                {
                    "tool": "search_funding_calls",
                    "result": {
                        "calls": [{"call_id": "HORIZON-CL5-2025-D3-01", "title": "Clean Hydrogen"}]
                    },
                }
            ],
        )

        failures = detector.detect(turn, turn_number=0)
        # Should not have no-results or short response failures
        assert len(failures) == 0


# =============================================================================
# Test __all__ Export List
# =============================================================================


class TestAllExports:
    """Tests that __all__ contains all expected exports."""

    def test_all_exports_defined(self):
        """Test that __all__ is defined and contains expected items."""
        from tests.quality import test_scenario_runner

        assert hasattr(test_scenario_runner, "__all__")
        all_exports = test_scenario_runner.__all__

        # Check main classes
        assert "ProductionQualityRunner" in all_exports
        assert "ScenarioExecutionResult" in all_exports
        assert "TurnResult" in all_exports
        assert "FailureRecord" in all_exports

        # Check enums
        assert "FailureCategory" in all_exports
        assert "FailureSeverity" in all_exports

        # Check pattern constants
        assert "NO_RESULTS_PATTERNS" in all_exports
        assert "DEFLECTION_PATTERNS" in all_exports
        assert "REQUIRED_FIELDS" in all_exports
        assert "KNOWN_FACTS" in all_exports

        # Check detector classes
        assert "detect_all" in all_exports
        assert "NoResultsDetector" in all_exports
        assert "IncorrectDataDetector" in all_exports
        assert "MissingDataDetector" in all_exports

    def test_all_exports_importable(self):
        """Test that all items in __all__ can be imported."""
        from tests.quality import test_scenario_runner

        for name in test_scenario_runner.__all__:
            obj = getattr(test_scenario_runner, name, None)
            assert obj is not None, f"Export '{name}' not found in module"
