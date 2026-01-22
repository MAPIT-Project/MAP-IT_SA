# isort: skip_file
"""
Unit tests for Failure Detection Module.

Tests each detector class with known good and bad examples to verify
correct categorization of failures.
"""

import pytest
from datetime import datetime

from tests.validators.failure_detector import (
    FailureCategory,
    FailureRecord,
    FailureSeverity,
    IncorrectDataDetector,
    MissingDataDetector,
    NoResultsDetector,
    PoorQualityDetector,
    TurnResult,
    UnexpectedBehaviorDetector,
    detect_all,
    KNOWN_FACTS,
    FUNDING_RATES,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def good_response():
    """A well-formed response with specific details."""
    response_text = """Based on my search, I found **15 funding opportunities** for hydrogen:

## Top Calls

1. **HORIZON-CL5-2025-D3-01** - Clean Hydrogen Partnership
   - Deadline: March 15, 2025
   - Budget: €50 million
   - Funding rate: 100% for RIA

2. **HORIZON-CL5-2025-D3-02** - Green Hydrogen Production
   - Deadline: April 10, 2025
   - Budget: €30 million
   - Funding rate: 70% for IA

### Next Steps
You can apply through the EU Funding & Tenders Portal. The deadline for
HORIZON-CL5-2025-D3-01 is approaching, so I recommend starting soon."""
    return TurnResult(
        query="Find open calls for hydrogen research",
        response=response_text,
        tools_used=["search_funding_calls"],
        tool_results=[
            {
                "tool": "search_funding_calls",
                "result": {
                    "success": True,
                    "calls": [
                        {
                            "call_id": "HORIZON-CL5-2025-D3-01",
                            "title": "Clean Hydrogen",
                            "deadline": "2025-03-15",
                            "budget": 50000000,
                        },
                        {
                            "call_id": "HORIZON-CL5-2025-D3-02",
                            "title": "Green Hydrogen",
                            "deadline": "2025-04-10",
                            "budget": 30000000,
                        },
                    ],
                },
            }
        ],
    )


@pytest.fixture
def empty_response():
    """A short, unhelpful response."""
    return TurnResult(
        query="Find calls for AI",
        response="I couldn't find any results.",
        tools_used=["search_funding_calls"],
        tool_results=[{"tool": "search_funding_calls", "result": {"calls": []}}],
    )


@pytest.fixture
def deflection_response():
    """A response that deflects instead of answering."""
    deflection_text = (
        "For more information about Horizon Europe, you might want to visit "
        "the official EU website. I suggest checking the funding portal for "
        "detailed budget information."
    )
    return TurnResult(
        query="What is the budget for Horizon Europe?",
        response=deflection_text,
        tools_used=[],
        tool_results=[],
    )


@pytest.fixture
def incorrect_data_response():
    """A response with incorrect factual information."""
    return TurnResult(
        query="Tell me about Horizon Europe",
        response="""Horizon Europe is the EU's key funding programme for research and innovation.

- **Budget**: Horizon Europe has a budget of 50 billion EUR for 2020-2025
- **Duration**: Horizon Europe runs from 2020-2025
- **Structure**: Horizon Europe has 5 pillars and 10 clusters
- **RIA funding rate**: RIA: 80%

The programme funds innovative research across Europe.""",
        tools_used=["search_documents"],
        tool_results=[],
    )


@pytest.fixture
def missing_data_response():
    """A response missing required fields in tool results."""
    return TurnResult(
        query="Search for partner organizations",
        response="I found several potential partners for your project in Germany and France.",
        tools_used=["find_experienced_partners"],
        tool_results=[
            {
                "tool": "find_experienced_partners",
                "result": {
                    "partners": [
                        {"name": "TU Munich"},  # Missing: organization_name, country, project_count
                        {"name": "CNRS"},
                    ]
                },
            }
        ],
    )


@pytest.fixture
def wall_of_text_response():
    """A response that is an unstructured wall of text."""
    # Long response without any structure markers (no bullet points, numbers, headers)
    wall_text = (
        "The funding programme is a comprehensive initiative designed to support "
        "various activities across multiple sectors and regions with the aim of "
        "fostering innovation cooperation and development in key priority areas "
        "that have been identified as strategically important for achieving the "
        "broader policy objectives and this programme encompasses a wide range of "
        "eligible activities including research development demonstration deployment "
        "capacity building networking knowledge transfer training education mobility "
        "partnerships institutional strengthening policy development and implementation "
        "support and the programme is open to diverse stakeholders including academic "
        "institutions research organizations enterprises particularly small and medium "
        "sized enterprises public authorities non governmental organizations civil "
        "society organizations and other relevant actors who meet the specific "
        "eligibility criteria defined for each type of action and the programme "
        "operates through different funding mechanisms including grants procurement "
        "prizes and financial instruments with each mechanism having its own rules "
        "and procedures for application evaluation selection and implementation and "
        "successful applicants are expected to demonstrate clear alignment with "
        "programme objectives strong implementation capacity appropriate partnerships "
        "and realistic work plans and budgets."
    )
    return TurnResult(
        query="Explain the funding programme",
        response=wall_text,
        tools_used=[],
        tool_results=[],
    )


@pytest.fixture
def error_response():
    """A response with errors."""
    return TurnResult(
        query="Find projects",
        response="An error occurred while processing your request.",
        tools_used=["search_projects"],
        tool_results=[],
        has_error=True,
        error="Database connection timeout",
        events=[{"type": "error", "message": "Connection timeout"}],
    )


@pytest.fixture
def context_loss_response():
    """A response showing context loss."""
    return TurnResult(
        query="Tell me more about the first one",
        response=(
            "I'm not sure what you're referring to. Could you clarify which one "
            "you mean? I don't have context from our previous conversation."
        ),
        tools_used=[],
        tool_results=[],
    )


# =============================================================================
# Test FailureRecord and TurnResult
# =============================================================================


class TestDataclasses:
    """Tests for FailureRecord and TurnResult dataclasses."""

    def test_failure_record_creation(self):
        """Test creating a FailureRecord."""
        record = FailureRecord(
            category=FailureCategory.NO_RESULTS,
            severity=FailureSeverity.CRITICAL,
            description="Test failure",
            turn_number=0,
            evidence={"key": "value"},
        )
        assert record.category == FailureCategory.NO_RESULTS
        assert record.severity == FailureSeverity.CRITICAL
        assert record.description == "Test failure"
        assert record.turn_number == 0
        assert record.evidence == {"key": "value"}
        assert isinstance(record.timestamp, datetime)

    def test_failure_record_to_dict(self):
        """Test FailureRecord serialization."""
        record = FailureRecord(
            category=FailureCategory.INCORRECT_DATA,
            severity=FailureSeverity.HIGH,
            description="Test",
            turn_number=1,
        )
        d = record.to_dict()
        assert d["category"] == "INCORRECT_DATA"
        assert d["severity"] == "HIGH"
        assert "timestamp" in d

    def test_turn_result_get_events_by_type(self):
        """Test TurnResult event filtering."""
        turn = TurnResult(
            query="test",
            response="test",
            events=[
                {"type": "error", "message": "Error 1"},
                {"type": "info", "message": "Info"},
                {"type": "error", "message": "Error 2"},
            ],
        )
        errors = turn.get_events_by_type("error")
        assert len(errors) == 2
        assert errors[0]["message"] == "Error 1"


# =============================================================================
# Test NoResultsDetector
# =============================================================================


class TestNoResultsDetector:
    """Tests for NoResultsDetector class."""

    def test_good_response_no_failures(self, good_response):
        """Good response should have no failures."""
        detector = NoResultsDetector()
        failures = detector.detect(good_response, turn_number=0)
        assert len(failures) == 0

    def test_short_response_detected(self):
        """Short responses should be flagged."""
        detector = NoResultsDetector(min_response_length=100)
        turn = TurnResult(query="test", response="Short response.")
        failures = detector.detect(turn, turn_number=0)

        assert len(failures) >= 1
        assert any(f.category == FailureCategory.NO_RESULTS for f in failures)
        assert any("too short" in f.description for f in failures)

    def test_no_results_pattern_detected(self, empty_response):
        """No-results patterns should be detected."""
        detector = NoResultsDetector()
        failures = detector.detect(empty_response, turn_number=0)

        assert len(failures) >= 1
        pattern_failures = [f for f in failures if "no-results pattern" in f.description.lower()]
        assert len(pattern_failures) >= 1
        assert pattern_failures[0].severity == FailureSeverity.CRITICAL

    def test_deflection_pattern_detected(self, deflection_response):
        """Deflection patterns should be detected with HIGH severity."""
        detector = NoResultsDetector()
        failures = detector.detect(deflection_response, turn_number=0)

        deflection_failures = [f for f in failures if "deflection" in f.description.lower()]
        assert len(deflection_failures) >= 1
        assert deflection_failures[0].severity == FailureSeverity.HIGH

    def test_empty_tool_results_detected(self):
        """Empty tool results should be detected."""
        detector = NoResultsDetector()
        turn = TurnResult(
            query="test",
            response="Here are the results:" + "x" * 100,
            tools_used=["search_funding_calls"],
            tool_results=[{"tool": "search_funding_calls", "result": {"calls": []}}],
        )
        failures = detector.detect(turn, turn_number=0)

        assert any("empty" in f.description.lower() for f in failures)

    def test_custom_patterns(self):
        """Custom patterns should be used in detection."""
        detector = NoResultsDetector(no_results_patterns=["custom pattern"])
        turn = TurnResult(
            query="test",
            response="This response contains a custom pattern that should be detected." + "x" * 50,
        )
        failures = detector.detect(turn, turn_number=0)

        assert any("custom pattern" in f.description.lower() for f in failures)

    def test_null_result_detected(self):
        """Null tool results should be detected."""
        detector = NoResultsDetector()
        turn = TurnResult(
            query="test",
            response="Processing your request..." + "x" * 100,
            tools_used=["search_projects"],
            tool_results=[{"tool": "search_projects", "result": None}],
        )
        failures = detector.detect(turn, turn_number=0)

        assert any("empty" in f.description.lower() for f in failures)


# =============================================================================
# Test IncorrectDataDetector
# =============================================================================


class TestIncorrectDataDetector:
    """Tests for IncorrectDataDetector class."""

    def test_correct_data_no_failures(self):
        """Correct data should have no failures."""
        detector = IncorrectDataDetector()
        turn = TurnResult(
            query="Tell me about Horizon Europe",
            response="""Horizon Europe has a budget of €95.5 billion for 2021-2027.
            It has 3 pillars and 6 clusters. RIA funding rate is 100%.""",
        )
        failures = detector.detect(turn, turn_number=0)
        assert len(failures) == 0

    def test_incorrect_budget_detected(self, incorrect_data_response):
        """Incorrect budget amounts should be detected."""
        detector = IncorrectDataDetector()
        failures = detector.detect(incorrect_data_response, turn_number=0)

        budget_failures = [f for f in failures if "budget" in f.description.lower()]
        assert len(budget_failures) >= 1
        assert budget_failures[0].severity == FailureSeverity.CRITICAL

    def test_incorrect_funding_rate_detected(self, incorrect_data_response):
        """Incorrect funding rates should be detected."""
        detector = IncorrectDataDetector()
        failures = detector.detect(incorrect_data_response, turn_number=0)

        rate_failures = [f for f in failures if "funding rate" in f.description.lower()]
        assert len(rate_failures) >= 1

    def test_incorrect_pillar_count_detected(self, incorrect_data_response):
        """Incorrect pillar counts should be detected."""
        detector = IncorrectDataDetector()
        failures = detector.detect(incorrect_data_response, turn_number=0)

        pillar_failures = [f for f in failures if "pillar" in f.description.lower()]
        assert len(pillar_failures) >= 1

    def test_incorrect_cluster_count_detected(self, incorrect_data_response):
        """Incorrect cluster counts should be detected."""
        detector = IncorrectDataDetector()
        failures = detector.detect(incorrect_data_response, turn_number=0)

        cluster_failures = [f for f in failures if "cluster" in f.description.lower()]
        assert len(cluster_failures) >= 1

    def test_incorrect_duration_detected(self, incorrect_data_response):
        """Incorrect programme duration should be detected."""
        detector = IncorrectDataDetector()
        failures = detector.detect(incorrect_data_response, turn_number=0)

        duration_failures = [f for f in failures if "duration" in f.description.lower()]
        assert len(duration_failures) >= 1

    def test_validate_facts_dict(self):
        """Test validate_facts_dict method."""
        detector = IncorrectDataDetector()

        # Test with incorrect facts
        incorrect_facts = {
            "budget": 50_000_000_000,  # Wrong - should be 95-96B
            "pillars": 5,  # Wrong - should be 3
        }
        incorrect = detector.validate_facts_dict(incorrect_facts, "horizon_europe")
        assert len(incorrect) == 2

        # Test with correct facts
        correct_facts = {
            "budget": 95_500_000_000,
            "pillars": 3,
            "clusters": 6,
        }
        incorrect = detector.validate_facts_dict(correct_facts, "horizon_europe")
        assert len(incorrect) == 0

    def test_ia_funding_rate_allows_up_to(self):
        """IA funding rate 'up to 70%' should not be flagged."""
        detector = IncorrectDataDetector()
        turn = TurnResult(
            query="What is the IA funding rate?",
            response="Innovation Actions (IA) can receive up to 70% funding rate.",
        )
        failures = detector.detect(turn, turn_number=0)

        # Should not flag 70% or less for IA
        rate_failures = [
            f for f in failures if "IA" in f.description and "funding rate" in f.description
        ]
        assert len(rate_failures) == 0


# =============================================================================
# Test MissingDataDetector
# =============================================================================


class TestMissingDataDetector:
    """Tests for MissingDataDetector class."""

    def test_complete_data_no_failures(self, good_response):
        """Complete data should have no failures."""
        detector = MissingDataDetector()
        failures = detector.detect(good_response, turn_number=0)

        # Filter out non-missing-data failures
        missing_failures = [f for f in failures if f.category == FailureCategory.MISSING_DATA]
        assert len(missing_failures) == 0

    def test_missing_partner_fields_detected(self, missing_data_response):
        """Missing required fields in partner search should be detected."""
        detector = MissingDataDetector()
        failures = detector.detect(missing_data_response, turn_number=0)

        assert len(failures) >= 1
        assert any("missing required fields" in f.description.lower() for f in failures)

    def test_missing_call_fields_detected(self):
        """Missing required fields in call search should be detected."""
        detector = MissingDataDetector()
        turn = TurnResult(
            query="Find calls",
            response="Found calls for your topic." + "x" * 100,
            tools_used=["search_funding_calls"],
            tool_results=[
                {
                    "tool": "search_funding_calls",
                    "result": {
                        "calls": [
                            {"title": "Call 1"},  # Missing call_id, deadline, budget
                        ]
                    },
                }
            ],
        )
        failures = detector.detect(turn, turn_number=0)

        missing_failures = [f for f in failures if "missing" in f.description.lower()]
        assert len(missing_failures) >= 1

    def test_programme_without_details_detected(self):
        """Programme mention without details should be detected with MEDIUM severity."""
        detector = MissingDataDetector()
        turn = TurnResult(
            query="What is Horizon Europe?",
            response=(
                "Horizon Europe is the EU's research funding programme. It supports "
                "innovation across Europe and helps researchers collaborate on important "
                "projects. The programme is managed by the European Commission and has "
                "various funding mechanisms available for different types of organizations."
            ),
        )
        failures = detector.detect(turn, turn_number=0)

        detail_failures = [
            f for f in failures if "without sufficient details" in f.description.lower()
        ]
        assert len(detail_failures) >= 1
        assert detail_failures[0].severity == FailureSeverity.MEDIUM

    def test_check_required_patterns(self):
        """Test check_required_patterns method."""
        detector = MissingDataDetector()

        response = "This response mentions budget and funding but lacks other key information."
        patterns = ["budget", "deadline", "eligibility"]

        failures = detector.check_required_patterns(response, patterns, turn_number=0)

        assert len(failures) == 1
        assert "deadline" in failures[0].evidence["missing_patterns"]
        assert "eligibility" in failures[0].evidence["missing_patterns"]
        assert "budget" not in failures[0].evidence["missing_patterns"]

    def test_nested_fields_checked(self):
        """Nested fields in arrays should be checked."""
        detector = MissingDataDetector()
        turn = TurnResult(
            query="Search projects",
            response="Found projects." + "x" * 100,
            tools_used=["search_projects"],
            tool_results=[
                {
                    "tool": "search_projects",
                    "result": {
                        "projects": [
                            {
                                "project_id": "123",
                                "acronym": "TEST",
                                "budget": 1000000,
                                "coordinator": "Org",
                            },
                        ]
                    },
                }
            ],
        )
        failures = detector.detect(turn, turn_number=0)

        # Should not flag missing fields since they're all present
        missing_failures = [
            f
            for f in failures
            if f.category == FailureCategory.MISSING_DATA
            and "missing required fields" in f.description.lower()
        ]
        assert len(missing_failures) == 0


# =============================================================================
# Test UnexpectedBehaviorDetector
# =============================================================================


class TestUnexpectedBehaviorDetector:
    """Tests for UnexpectedBehaviorDetector class."""

    def test_normal_response_no_failures(self, good_response):
        """Normal response should have no failures."""
        detector = UnexpectedBehaviorDetector()
        failures = detector.detect(good_response, turn_number=0)
        assert len(failures) == 0

    def test_error_detected(self, error_response):
        """Errors should be detected with CRITICAL severity."""
        detector = UnexpectedBehaviorDetector()
        failures = detector.detect(error_response, turn_number=0)

        assert len(failures) >= 1
        error_failures = [f for f in failures if "error" in f.description.lower()]
        assert len(error_failures) >= 1
        assert any(f.severity == FailureSeverity.CRITICAL for f in error_failures)

    def test_sse_error_event_detected(self, error_response):
        """Error events in SSE stream should be detected."""
        detector = UnexpectedBehaviorDetector()
        failures = detector.detect(error_response, turn_number=0)

        sse_failures = [f for f in failures if "SSE" in f.description]
        assert len(sse_failures) >= 1

    def test_quality_degradation_detected(self):
        """Quality score drops should be detected."""
        detector = UnexpectedBehaviorDetector(quality_degradation_threshold=15.0)
        turn = TurnResult(
            query="Follow up question",
            response="Brief response." + "x" * 100,
            quality_score=60.0,
            previous_quality_score=85.0,  # 25 point drop
        )
        failures = detector.detect(turn, turn_number=1)

        degradation_failures = [f for f in failures if "dropped" in f.description.lower()]
        assert len(degradation_failures) >= 1
        assert "25.0" in degradation_failures[0].description

    def test_context_loss_detected(self, context_loss_response):
        """Context loss should be detected."""
        detector = UnexpectedBehaviorDetector()
        failures = detector.detect(context_loss_response, turn_number=1)

        context_failures = [f for f in failures if "context" in f.description.lower()]
        assert len(context_failures) >= 1

    def test_wrong_tool_detected(self):
        """Wrong tool for query type should be detected."""
        detector = UnexpectedBehaviorDetector()
        turn = TurnResult(
            query="Find open calls for my project",
            response="Here is information about your project timeline.",
            tools_used=["generate_timeline"],  # Wrong tool for call search
        )
        failures = detector.detect(turn, turn_number=0)

        wrong_tool_failures = [f for f in failures if "unexpected tools" in f.description.lower()]
        assert len(wrong_tool_failures) >= 1
        assert wrong_tool_failures[0].severity == FailureSeverity.MEDIUM

    def test_no_degradation_within_threshold(self):
        """Small quality drops within threshold should not be flagged."""
        detector = UnexpectedBehaviorDetector(quality_degradation_threshold=15.0)
        turn = TurnResult(
            query="Follow up",
            response="Response text." + "x" * 100,
            quality_score=75.0,
            previous_quality_score=85.0,  # Only 10 point drop
        )
        failures = detector.detect(turn, turn_number=1)

        degradation_failures = [f for f in failures if "dropped" in f.description.lower()]
        assert len(degradation_failures) == 0


# =============================================================================
# Test PoorQualityDetector
# =============================================================================


class TestPoorQualityDetector:
    """Tests for PoorQualityDetector class."""

    def test_good_response_no_failures(self, good_response):
        """Good response should have no poor quality failures."""
        detector = PoorQualityDetector()
        # Simulate a good quality score
        good_response.quality_score = 85.0
        failures = detector.detect(good_response, turn_number=0)

        # Filter to only poor quality failures
        quality_failures = [f for f in failures if f.category == FailureCategory.POOR_QUALITY]
        assert len(quality_failures) == 0

    def test_low_quality_score_detected(self):
        """Low quality score should be detected."""
        detector = PoorQualityDetector(quality_threshold=80.0)
        turn = TurnResult(
            query="Tell me about calls",
            response="Here is some information about funding calls." + "x" * 100,
            quality_score=65.0,
        )
        failures = detector.detect(turn, turn_number=0)

        score_failures = [
            f for f in failures if "quality score below threshold" in f.description.lower()
        ]
        assert len(score_failures) >= 1

    def test_wall_of_text_detected(self, wall_of_text_response):
        """Wall of text should be detected."""
        detector = PoorQualityDetector()
        failures = detector.detect(wall_of_text_response, turn_number=0)

        wall_failures = [f for f in failures if "wall of text" in f.description.lower()]
        assert len(wall_failures) >= 1

    def test_structured_response_not_flagged(self):
        """Structured responses should not be flagged as wall of text."""
        detector = PoorQualityDetector()
        turn = TurnResult(
            query="List information",
            response="""Here is the information:

1. First item with details about the topic
2. Second item with more information
3. Third item explaining additional aspects

## Summary
This section provides a summary of the key points mentioned above.""",
            quality_score=85.0,
        )
        failures = detector.detect(turn, turn_number=0)

        wall_failures = [f for f in failures if "wall of text" in f.description.lower()]
        assert len(wall_failures) == 0

    def test_vague_response_detected(self):
        """Vague responses lacking specifics should be detected."""
        detector = PoorQualityDetector()
        vague_response = (
            "There are various deadlines throughout the year for different programmes "
            "and calls. You should check the specific call you're interested in to find "
            "the exact deadline. The European Commission publishes deadlines regularly "
            "and they can vary depending on the type of action and programme area. "
            "Generally, deadlines are set well in advance to give applicants time to "
            "prepare their proposals."
        )
        turn = TurnResult(
            query="What are the deadlines?",
            response=vague_response,
            quality_score=85.0,
        )
        failures = detector.detect(turn, turn_number=0)

        vague_failures = [f for f in failures if "specificity" in f.description.lower()]
        assert len(vague_failures) >= 1

    def test_response_with_specifics_not_flagged(self, good_response):
        """Response with specific data should not be flagged for vagueness."""
        detector = PoorQualityDetector()
        good_response.quality_score = 85.0
        failures = detector.detect(good_response, turn_number=0)

        vague_failures = [f for f in failures if "specificity" in f.description.lower()]
        assert len(vague_failures) == 0

    def test_non_actionable_response_detected(self):
        """Non-actionable responses should be detected."""
        detector = PoorQualityDetector()
        non_actionable = (
            "Horizon Europe is the European Union's research and innovation programme. "
            "It has been designed to support excellent research and foster innovation "
            "across Europe. The programme builds on the success of previous framework "
            "programmes and incorporates lessons learned from their implementation. "
            "Research organizations and companies across Europe have participated in "
            "these programmes over the years."
        )
        turn = TurnResult(
            query="How do I apply?",
            response=non_actionable,
            quality_score=85.0,
        )
        failures = detector.detect(turn, turn_number=0)

        action_failures = [f for f in failures if "actionable" in f.description.lower()]
        assert len(action_failures) >= 1

    def test_actionable_response_not_flagged(self, good_response):
        """Actionable responses should not be flagged."""
        detector = PoorQualityDetector()
        good_response.quality_score = 85.0
        failures = detector.detect(good_response, turn_number=0)

        action_failures = [f for f in failures if "actionable" in f.description.lower()]
        assert len(action_failures) == 0

    def test_evaluate_dimensions(self):
        """Test evaluate_dimensions method."""
        detector = PoorQualityDetector(
            specificity_threshold=20.0,
            actionability_threshold=7.0,
        )

        # Test with low scores
        failures = detector.evaluate_dimensions(
            response="test",
            specificity_score=15.0,
            actionability_score=5.0,
            turn_number=0,
        )

        assert len(failures) == 2
        assert any("specificity" in f.description.lower() for f in failures)
        assert any("actionability" in f.description.lower() for f in failures)


# =============================================================================
# Test detect_all Function
# =============================================================================


class TestDetectAll:
    """Tests for the detect_all function."""

    def test_detect_all_good_response(self, good_response):
        """Good response should have minimal failures."""
        good_response.quality_score = 85.0
        failures = detect_all(good_response, turn_number=0)

        # Good response should pass most checks
        critical_failures = [f for f in failures if f.severity == FailureSeverity.CRITICAL]
        assert len(critical_failures) == 0

    def test_detect_all_empty_response(self, empty_response):
        """Empty response should have multiple failures."""
        failures = detect_all(empty_response, turn_number=0)

        assert len(failures) >= 2
        # Should detect no-results pattern and short response
        categories = {f.category for f in failures}
        assert FailureCategory.NO_RESULTS in categories

    def test_detect_all_returns_list(self, good_response):
        """detect_all should always return a list."""
        result = detect_all(good_response, turn_number=0)
        assert isinstance(result, list)

    def test_detect_all_with_multiple_issues(self, error_response):
        """Response with multiple issues should detect all."""
        error_response.quality_score = 50.0
        failures = detect_all(error_response, turn_number=0)

        # Should detect: error, low quality, possibly no results (short)
        assert len(failures) >= 2
        categories = {f.category for f in failures}
        assert FailureCategory.UNEXPECTED_BEHAVIOR in categories

    def test_detect_all_turn_number_preserved(self, empty_response):
        """Turn number should be preserved in all failures."""
        failures = detect_all(empty_response, turn_number=5)

        for failure in failures:
            assert failure.turn_number == 5

    def test_detect_all_runs_all_detectors(self, incorrect_data_response):
        """detect_all should run all detector types."""
        incorrect_data_response.quality_score = 50.0  # To trigger poor quality
        failures = detect_all(incorrect_data_response, turn_number=0)

        # Should have failures from multiple detectors
        categories = {f.category for f in failures}
        assert len(categories) >= 2


# =============================================================================
# Test Edge Cases and Integration
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_empty_turn_result(self):
        """Empty TurnResult should be handled gracefully."""
        turn = TurnResult(query="", response="")
        failures = detect_all(turn, turn_number=0)

        # Should detect short response at minimum
        assert len(failures) >= 1
        assert any(f.category == FailureCategory.NO_RESULTS for f in failures)

    def test_unicode_content(self):
        """Unicode content should be handled correctly."""
        turn = TurnResult(
            query="Fördermittel für €10M Projekt",
            response="Das Programm hat ein Budget von €95,5 Milliarden für 2021-2027. "
            "Die Förderquote beträgt 100% für RIA-Projekte." + "x" * 100,
        )
        failures = detect_all(turn, turn_number=0)

        # Should process without error
        assert isinstance(failures, list)

    def test_very_long_response(self):
        """Very long responses should be handled."""
        turn = TurnResult(
            query="Explain everything",
            response="# Detailed Explanation\n\n" + ("This is paragraph. " * 100 + "\n\n") * 10,
            quality_score=85.0,
        )
        failures = detect_all(turn, turn_number=0)

        # Should not crash and should not flag as wall of text (has structure)
        wall_failures = [f for f in failures if "wall of text" in f.description.lower()]
        assert len(wall_failures) == 0

    def test_tool_result_with_metadata_only(self):
        """Tool results with only metadata should be flagged as empty."""
        turn = TurnResult(
            query="Search calls",
            response="Processing your request..." + "x" * 100,
            tools_used=["search_funding_calls"],
            tool_results=[
                {
                    "tool": "search_funding_calls",
                    "result": {
                        "success": True,
                        "metadata": {"query": "test"},
                    },
                }
            ],
        )
        detector = NoResultsDetector()
        failures = detector.detect(turn, turn_number=0)

        assert any("empty" in f.description.lower() for f in failures)

    def test_detector_with_custom_thresholds(self):
        """Detectors should work with custom thresholds."""
        detector = PoorQualityDetector(
            quality_threshold=90.0,
            wall_of_text_threshold=200,
        )
        turn = TurnResult(
            query="test",
            response="A moderately long response without structure " * 10,
            quality_score=85.0,
        )
        failures = detector.detect(turn, turn_number=0)

        # Should flag both quality below 90 and wall of text above 200 chars
        assert len(failures) >= 2


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_known_facts_structure(self):
        """KNOWN_FACTS should have correct structure."""
        assert "horizon_europe" in KNOWN_FACTS
        assert "erasmus_plus" in KNOWN_FACTS
        assert "creative_europe" in KNOWN_FACTS

        # Check Horizon Europe
        he = KNOWN_FACTS["horizon_europe"]
        assert "budget" in he
        assert isinstance(he["budget"], tuple)
        assert len(he["budget"]) == 2
        assert he["pillars"] == 3
        assert he["clusters"] == 6

    def test_funding_rates_values(self):
        """FUNDING_RATES should have correct values."""
        assert FUNDING_RATES["RIA"] == 100
        assert FUNDING_RATES["IA"] == 70
        assert FUNDING_RATES["CSA"] == 100
        assert FUNDING_RATES["ERC"] == 100
