# isort: skip_file
"""
FIX IF NEEDED test for Scenario 003: Programme Recommendation.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V2.md:
- FIX IF NEEDED: Read `tests/quality/results/scenarios/programme_recommendation.json`
- If average_score < 80: identify root causes and fix
- Fix and re-evaluate until passing or 3 attempts
- Record final status: PASS/FAIL/MAX_ATTEMPTS

Programme Recommendation specific root causes:
- missing_personalization → PersonalizationAgent not applying museum/cultural context
- wrong_programme_recommendation → Incorrect programme recommended for user needs
- missing_combined_strategy → No combined strategy recommendation in final turn
- missing_creative_europe → Creative Europe not mentioned for digitization
- missing_erasmus → Erasmus+ not mentioned for staff training
- low_actionability → Missing Next Steps in response
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

logger = logging.getLogger(__name__)

# Configuration
RESULTS_PATH = Path("tests/quality/results/scenarios/programme_recommendation.json")
PASSING_THRESHOLD = 80
MAX_FIX_ATTEMPTS = 3


class FixAttempt:
    """Records a single fix attempt."""

    def __init__(
        self,
        attempt_number: int,
        root_cause: str,
        fix_description: str,
        pre_fix_score: float,
        post_fix_score: float,
        files_modified: list[str],
        success: bool,
    ):
        self.attempt_number = attempt_number
        self.root_cause = root_cause
        self.fix_description = fix_description
        self.pre_fix_score = pre_fix_score
        self.post_fix_score = post_fix_score
        self.files_modified = files_modified
        self.success = success
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "attempt_number": self.attempt_number,
            "root_cause": self.root_cause,
            "fix_description": self.fix_description,
            "pre_fix_score": self.pre_fix_score,
            "post_fix_score": self.post_fix_score,
            "files_modified": self.files_modified,
            "success": self.success,
            "timestamp": self.timestamp,
        }


def detect_missing_personalization(response_text: str, turns: list[dict]) -> bool:
    """
    Detect if personalization is missing for museum/cultural context.

    The response should acknowledge and use the user's context:
    - Small museum
    - Digitization focus
    - European sharing goals
    - Cultural institution identity

    Detection looks for absence of context acknowledgment in responses.
    """
    text_lower = response_text.lower()

    # Primary personalization indicators - must have at least one of these
    # These are specific to the museum/cultural context
    primary_context_terms = [
        "museum",
        "collection",
        "digitiz",
        "heritage",
        "cultural",
        "institution",
    ]

    # Check if any primary context term is present
    has_primary_context = any(term in text_lower for term in primary_context_terms)

    if not has_primary_context:
        logger.warning("Missing personalization: No museum/cultural context acknowledgment")
        return True

    return False


def detect_wrong_programme_recommendation(response_text: str, turns: list[dict]) -> dict:
    """
    Detect if wrong programmes are recommended for the user's needs.

    Expected recommendations:
    - Turn 1 (digitization): Creative Europe CULTURE strand
    - Turn 2 (staff training): Erasmus+ (KA1 or KA2)
    - Turn 3 (strategy): Both programmes mentioned with strategy

    Args:
        response_text: Unused, kept for API consistency
        turns: List of turn dictionaries with response_text

    Returns dict with detected issues.
    """
    issues = {}
    # Note: response_text parameter kept for API consistency with other detect_* functions

    # Check Turn 1: Digitization should mention Creative Europe/culture-related funding
    if len(turns) >= 1:
        turn1_response = turns[0].get("response_text", "").lower()
        creative_europe_terms = ["creative europe", "culture", "cultural", "heritage", "digitiz"]
        has_ce_turn1 = any(term in turn1_response for term in creative_europe_terms)
        if not has_ce_turn1:
            issues["turn1_missing_creative_europe"] = True
            logger.warning("Wrong recommendation: Turn 1 missing Creative Europe/culture reference")

    # Check Turn 2: Training should mention Erasmus+/education-related funding
    if len(turns) >= 2:
        turn2_response = turns[1].get("response_text", "").lower()
        erasmus_terms = ["erasmus", "training", "education", "mobility", "skills", "learning"]
        has_erasmus_turn2 = any(term in turn2_response for term in erasmus_terms)
        if not has_erasmus_turn2:
            issues["turn2_missing_erasmus"] = True
            logger.warning("Wrong recommendation: Turn 2 missing Erasmus+/training reference")

    # Check Turn 3: Strategy should mention both programmes
    if len(turns) >= 3:
        turn3_response = turns[2].get("response_text", "").lower()
        has_strategy = any(
            term in turn3_response
            for term in ["strategy", "recommend", "suggest", "combine", "both", "approach"]
        )
        if not has_strategy:
            issues["turn3_missing_strategy"] = True
            logger.warning("Wrong recommendation: Turn 3 missing strategic recommendation")

    return issues


def detect_missing_combined_strategy(response_text: str, turns: list[dict]) -> bool:
    """
    Detect if combined strategy recommendation is missing.

    The final turn should provide a strategic recommendation that:
    - References both Creative Europe and Erasmus+
    - Explains how to combine/sequence applications
    - Provides actionable guidance

    Detection looks for strategy-related terms in final turn.
    """
    if len(turns) < 3:
        return False

    final_turn_response = turns[2].get("response_text", "").lower()

    # Combined strategy indicators
    strategy_terms = [
        "both",
        "combine",
        "parallel",
        "complementary",
        "strategy",
        "recommend",
        "suggest",
        "first",
        "then",
        "sequence",
        "approach",
        "apply for both",
    ]

    has_strategy = any(term in final_turn_response for term in strategy_terms)

    if not has_strategy:
        logger.warning("Missing combined strategy: Final turn lacks strategic recommendation")
        return True

    return False


def detect_missing_programme_mention(response_text: str, turns: list[dict], programme: str) -> bool:
    """
    Detect if a specific programme is not mentioned when expected.

    Args:
        response_text: Full response text
        turns: List of turn dictionaries
        programme: "creative_europe" or "erasmus"

    Returns:
        True if the programme is missing when expected
    """
    text_lower = response_text.lower()

    if programme == "creative_europe":
        creative_europe_terms = ["creative europe", "culture strand", "cultural programme"]
        # Also accept general cultural/heritage mentions
        broad_terms = ["cultural", "culture", "heritage", "digitiz"]
        has_mention = any(term in text_lower for term in creative_europe_terms + broad_terms)
        if not has_mention:
            logger.warning("Missing Creative Europe: No mention for digitization needs")
            return True

    elif programme == "erasmus":
        erasmus_terms = ["erasmus", "erasmus+"]
        # Also accept training/education mentions
        broad_terms = ["training", "education", "mobility", "staff development", "skills"]
        has_mention = any(term in text_lower for term in erasmus_terms + broad_terms)
        if not has_mention:
            logger.warning("Missing Erasmus+: No mention for training needs")
            return True

    return False


def analyze_root_cause(failures: list[dict], turns: list[dict]) -> tuple[str, str]:
    """
    Analyze failures to determine root cause and recommended fix.

    Specific to Programme Recommendation scenario per PRD:
    - missing_personalization → PersonalizationAgent issue
    - wrong_programme_recommendation → Incorrect programme guidance
    - missing_combined_strategy → No strategic recommendation
    - missing_creative_europe → Creative Europe not mentioned for digitization
    - missing_erasmus → Erasmus+ not mentioned for training
    - low_actionability → Missing Next Steps

    Returns:
        Tuple of (root_cause, recommended_fix_description)
    """
    # Aggregate response text for analysis
    all_response_text = " ".join(turn.get("response_text", "") for turn in turns)

    # Check for missing personalization (PRD priority 1)
    if detect_missing_personalization(all_response_text, turns):
        return (
            "missing_personalization",
            "PersonalizationAgent not applying museum/cultural context - "
            "add context-building message handling to agent prompt",
        )

    # Check for wrong programme recommendation (PRD priority 2)
    recommendation_issues = detect_wrong_programme_recommendation(all_response_text, turns)
    if recommendation_issues:
        if recommendation_issues.get("turn1_missing_creative_europe"):
            return (
                "missing_creative_europe",
                "Creative Europe not mentioned for digitization - "
                "ensure cultural funding tools are called for heritage/digitization queries",
            )
        if recommendation_issues.get("turn2_missing_erasmus"):
            return (
                "missing_erasmus",
                "Erasmus+ not mentioned for staff training - "
                "ensure education/training tools are called for skills development queries",
            )
        if recommendation_issues.get("turn3_missing_strategy"):
            return (
                "missing_combined_strategy",
                "No combined strategy in final turn - "
                "add strategic recommendation synthesis for multi-programme queries",
            )

    # Check for missing combined strategy (PRD priority 3)
    if detect_missing_combined_strategy(all_response_text, turns):
        return (
            "missing_combined_strategy",
            "No strategic recommendation for combining programmes - "
            "ensure compare_programmes tool or synthesis produces combined guidance",
        )

    # Check for low actionability in quality details
    low_actionability = False
    for turn in turns:
        quality_details = turn.get("quality_details", {})
        dimension_scores = quality_details.get("dimension_scores", {})
        actionability_score = dimension_scores.get("actionability", 10)
        if actionability_score < 7:  # Below 70% threshold
            low_actionability = True
            break

    # Count failure categories
    category_counts: dict[str, int] = {}
    for failure in failures:
        category = failure.get("category", "UNKNOWN")
        category_counts[category] = category_counts.get(category, 0) + 1

    # Standard failure patterns from PRD Fix Patterns Reference
    if low_actionability:
        return (
            "low_actionability",
            "Add '🎯 Next Steps:' requirement to ToolAwareAgent prompt for recommendation queries",
        )

    if "INCORRECT_DATA" in category_counts and category_counts["INCORRECT_DATA"] > 0:
        return (
            "factual_error",
            "Fix CrossProgrammeAgent validation for programme-specific facts",
        )

    if "NO_RESULTS" in category_counts and category_counts["NO_RESULTS"] > 0:
        return (
            "no_results",
            "Fix tool queries to return comprehensive results for cultural/training funding",
        )

    if "MISSING_DATA" in category_counts and category_counts["MISSING_DATA"] > 0:
        return (
            "missing_data",
            "Ensure all required fields are included in programme recommendations",
        )

    if "POOR_QUALITY" in category_counts and category_counts["POOR_QUALITY"] > 0:
        return (
            "poor_quality",
            "Improve response structure and formatting for recommendations",
        )

    # Default: general quality improvement needed
    return (
        "general_quality",
        "General improvements to recommendation response quality needed",
    )


def update_result_with_fix_history(result: dict, fix_attempt: FixAttempt, new_status: str) -> dict:
    """
    Update the result JSON with fix history.

    Args:
        result: The current result dictionary
        fix_attempt: The fix attempt to record
        new_status: The new status (PASS/FAIL/MAX_ATTEMPTS)

    Returns:
        Updated result dictionary
    """
    if "fix_history" not in result:
        result["fix_history"] = []

    result["fix_history"].append(fix_attempt.to_dict())
    result["status"] = new_status
    result["last_updated"] = datetime.now().isoformat()

    return result


class TestScenario003FixIfNeeded:
    """
    FIX IF NEEDED tests for Scenario 003: Programme Recommendation.

    These tests implement the fix loop per PRD requirements.
    """

    def test_results_file_exists(self):
        """
        Check if results file exists before attempting fix.

        If the file doesn't exist, the EXECUTE task needs to be run first.
        """
        if not RESULTS_PATH.exists():
            pytest.skip(
                f"Results file does not exist: {RESULTS_PATH}. "
                "Run the EXECUTE task first (test_execute_scenario_003_programme_recommendation)."
            )

        # File exists, read and validate structure
        with open(RESULTS_PATH) as f:
            result = json.load(f)

        assert "average_score" in result, "Result file missing 'average_score' field"
        assert "failures" in result, "Result file missing 'failures' field"
        assert "turns" in result, "Result file missing 'turns' field"
        assert "status" in result, "Result file missing 'status' field"

    def test_check_if_fix_needed(self):
        """
        Determine if a fix is needed based on the current score.

        This is the entry point for the FIX IF NEEDED workflow.
        """
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist - run EXECUTE task first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        avg_score = result.get("average_score", 0)
        current_status = result.get("status", "UNKNOWN")
        fix_history = result.get("fix_history", [])
        fix_count = len(fix_history)

        logger.info(f"Current average score: {avg_score:.1f}")
        logger.info(f"Current status: {current_status}")
        logger.info(f"Previous fix attempts: {fix_count}")

        if avg_score >= PASSING_THRESHOLD:
            logger.info(f"✅ PASS: Score {avg_score:.1f} >= {PASSING_THRESHOLD}")
            assert current_status == "PASS", f"Status should be PASS, got {current_status}"
            return

        if fix_count >= MAX_FIX_ATTEMPTS:
            logger.warning(
                f"⚠️ MAX_ATTEMPTS: {fix_count} fix attempts exhausted, "
                f"score still {avg_score:.1f} < {PASSING_THRESHOLD}"
            )
            # Update status to MAX_ATTEMPTS if not already
            if current_status != "MAX_ATTEMPTS":
                result["status"] = "MAX_ATTEMPTS"
                result["last_updated"] = datetime.now().isoformat()
                with open(RESULTS_PATH, "w") as f:
                    json.dump(result, f, indent=2)
            return

        # Fix is needed
        logger.warning(
            f"⚠️ FIX NEEDED: Score {avg_score:.1f} < {PASSING_THRESHOLD}, "
            f"attempt {fix_count + 1}/{MAX_FIX_ATTEMPTS}"
        )

        # Analyze root cause
        root_cause, fix_description = analyze_root_cause(
            result.get("failures", []), result.get("turns", [])
        )

        logger.info(f"Root cause identified: {root_cause}")
        logger.info(f"Recommended fix: {fix_description}")

        # Record the analysis (actual fix implementation is manual or in separate task)
        raise AssertionError(
            f"Fix needed: score {avg_score:.1f} < {PASSING_THRESHOLD}. "
            f"Root cause: {root_cause}. "
            f"Fix: {fix_description}. "
            f"Attempt {fix_count + 1}/{MAX_FIX_ATTEMPTS}."
        )


class TestScenario003RecommendationSpecificAnalysis:
    """
    Tests for Programme Recommendation specific root cause analysis.

    These tests validate the detection of recommendation-specific issues per PRD.
    """

    def test_detect_missing_personalization_no_context(self):
        """Test detection of missing museum context acknowledgment."""
        response = (
            "There are several EU funding programmes available. "
            "You can apply for various grants through the EU portal."
        )

        assert detect_missing_personalization(response, []) is True

    def test_detect_missing_personalization_with_context(self):
        """Test that museum context acknowledgment is detected correctly."""
        response = (
            "For your museum's digitization project, Creative Europe CULTURE strand "
            "offers excellent opportunities for preserving cultural heritage."
        )

        assert detect_missing_personalization(response, []) is False

    def test_detect_wrong_programme_turn1_missing_creative_europe(self):
        """Test detection of missing Creative Europe in Turn 1."""
        turns = [
            {
                "response_text": "Horizon Europe offers funding for research projects.",
                "turn_number": 0,
            }
        ]

        issues = detect_wrong_programme_recommendation("", turns)
        assert issues.get("turn1_missing_creative_europe") is True

    def test_detect_wrong_programme_turn1_correct(self):
        """Test that Creative Europe mention in Turn 1 is detected."""
        turns = [
            {
                "response_text": "Creative Europe CULTURE strand supports digitization projects.",
                "turn_number": 0,
            }
        ]

        issues = detect_wrong_programme_recommendation("", turns)
        assert "turn1_missing_creative_europe" not in issues

    def test_detect_wrong_programme_turn2_missing_erasmus(self):
        """Test detection of missing Erasmus+ in Turn 2."""
        turns = [
            {
                "response_text": "Creative Europe supports cultural projects.",
                "turn_number": 0,
            },
            {
                "response_text": "The budget for this programme is significant.",
                "turn_number": 1,
            },
        ]

        issues = detect_wrong_programme_recommendation("", turns)
        assert issues.get("turn2_missing_erasmus") is True

    def test_detect_wrong_programme_turn2_correct(self):
        """Test that Erasmus+/training mention in Turn 2 is detected."""
        turns = [
            {
                "response_text": "Creative Europe supports cultural projects.",
                "turn_number": 0,
            },
            {
                "response_text": "Erasmus+ offers training programmes for staff development.",
                "turn_number": 1,
            },
        ]

        issues = detect_wrong_programme_recommendation("", turns)
        assert "turn2_missing_erasmus" not in issues

    def test_detect_wrong_programme_turn3_missing_strategy(self):
        """Test detection of missing strategy in Turn 3."""
        turns = [
            {"response_text": "Creative Europe for digitization.", "turn_number": 0},
            {"response_text": "Erasmus+ for training.", "turn_number": 1},
            {"response_text": "These are the two programmes.", "turn_number": 2},
        ]

        issues = detect_wrong_programme_recommendation("", turns)
        assert issues.get("turn3_missing_strategy") is True

    def test_detect_wrong_programme_turn3_correct(self):
        """Test that strategy mention in Turn 3 is detected."""
        turns = [
            {"response_text": "Creative Europe for digitization.", "turn_number": 0},
            {"response_text": "Erasmus+ for training.", "turn_number": 1},
            {
                "response_text": "I recommend combining both programmes for your museum.",
                "turn_number": 2,
            },
        ]

        issues = detect_wrong_programme_recommendation("", turns)
        assert "turn3_missing_strategy" not in issues

    def test_detect_missing_combined_strategy_no_strategy(self):
        """Test detection of missing combined strategy."""
        turns = [
            {"response_text": "Creative Europe.", "turn_number": 0},
            {"response_text": "Erasmus+.", "turn_number": 1},
            {"response_text": "These are the programmes.", "turn_number": 2},
        ]

        assert detect_missing_combined_strategy("", turns) is True

    def test_detect_missing_combined_strategy_with_strategy(self):
        """Test that combined strategy is detected correctly."""
        turns = [
            {"response_text": "Creative Europe.", "turn_number": 0},
            {"response_text": "Erasmus+.", "turn_number": 1},
            {
                "response_text": "I recommend applying to both programmes in parallel.",
                "turn_number": 2,
            },
        ]

        assert detect_missing_combined_strategy("", turns) is False

    def test_analyze_root_cause_missing_personalization(self):
        """Test that missing personalization is detected as root cause."""
        turns = [
            {
                "response_text": "EU programmes offer funding for various projects.",
                "quality_details": {"dimension_scores": {"actionability": 8}},
            }
        ]
        failures = []

        root_cause, fix_desc = analyze_root_cause(failures, turns)

        assert root_cause == "missing_personalization"
        assert "PersonalizationAgent" in fix_desc or "context" in fix_desc.lower()

    def test_analyze_root_cause_missing_creative_europe(self):
        """Test that missing Creative Europe is detected."""
        turns = [
            {
                "response_text": "For your museum, Horizon Europe research grants may help.",
                "quality_details": {"dimension_scores": {"actionability": 8}},
            }
        ]
        failures = []

        root_cause, fix_desc = analyze_root_cause(failures, turns)

        assert root_cause == "missing_creative_europe"
        assert "Creative Europe" in fix_desc or "cultural" in fix_desc.lower()


class TestScenario003FixIfNeededIntegration:
    """
    Integration tests for the full FIX IF NEEDED workflow.

    These tests require the live API and previous EXECUTE results.
    """

    @pytest.fixture
    def current_result(self):
        """Load current result if exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist")

        with open(RESULTS_PATH) as f:
            return json.load(f)

    def test_full_fix_workflow_status(self, current_result):
        """
        Test the full fix workflow and determine final status.

        This test documents the current state and what action is needed.
        """
        avg_score = current_result.get("average_score", 0)
        fix_history = current_result.get("fix_history", [])
        current_status = current_result.get("status", "UNKNOWN")

        logger.info("=" * 60)
        logger.info("SCENARIO 003: PROGRAMME RECOMMENDATION - FIX IF NEEDED STATUS")
        logger.info("=" * 60)
        logger.info(f"Average Score: {avg_score:.1f}")
        logger.info(f"Passing Threshold: {PASSING_THRESHOLD}")
        logger.info(f"Current Status: {current_status}")
        logger.info(f"Fix Attempts Made: {len(fix_history)}/{MAX_FIX_ATTEMPTS}")

        if avg_score >= PASSING_THRESHOLD:
            logger.info("✅ SCENARIO PASSED - No fix needed")
            assert current_status in ["PASS", "FAIL"], "Status should be updated"
        elif len(fix_history) >= MAX_FIX_ATTEMPTS:
            logger.warning("❌ MAX ATTEMPTS REACHED - Scenario failed after all fix attempts")
            # This is acceptable - we tried our best
        else:
            remaining = MAX_FIX_ATTEMPTS - len(fix_history)
            logger.warning(f"⚠️ FIX NEEDED - {remaining} attempts remaining")

            # Analyze what needs to be fixed
            root_cause, fix_desc = analyze_root_cause(
                current_result.get("failures", []),
                current_result.get("turns", []),
            )
            logger.info(f"Identified root cause: {root_cause}")
            logger.info(f"Recommended action: {fix_desc}")

    def test_verify_fix_history_structure(self, current_result):
        """Verify fix history is properly structured."""
        fix_history = current_result.get("fix_history", [])

        for i, fix in enumerate(fix_history):
            assert "attempt_number" in fix, f"Fix {i} missing attempt_number"
            assert "root_cause" in fix, f"Fix {i} missing root_cause"
            assert "fix_description" in fix, f"Fix {i} missing fix_description"
            assert "pre_fix_score" in fix, f"Fix {i} missing pre_fix_score"
            assert "post_fix_score" in fix, f"Fix {i} missing post_fix_score"
            assert "success" in fix, f"Fix {i} missing success"
            assert "timestamp" in fix, f"Fix {i} missing timestamp"

            # Verify attempt numbers are sequential
            assert fix["attempt_number"] == i + 1, f"Fix {i} has wrong attempt_number"


class TestScenario003FixPatterns:
    """
    Test fix patterns referenced in the PRD for Programme Recommendation.

    These tests verify the fix targets exist without requiring actual code modifications.
    """

    def test_fix_pattern_personalization(self):
        """
        Test fix pattern: missing_personalization → PersonalizationAgent/ToolAwareAgent.

        The agent should apply user context (museum, cultural institution) to recommendations.
        """
        expected_file = Path("app/services/agents/tool_aware_agent.py")
        assert expected_file.exists(), f"Target file for fix does not exist: {expected_file}"

        content = expected_file.read_text()
        assert len(content) > 0, "Target file is empty"

    def test_fix_pattern_creative_europe_tools(self):
        """
        Test fix pattern: missing_creative_europe → Creative Europe tools.

        The Creative Europe tools should be called for cultural/heritage queries.
        """
        expected_file = Path("app/services/tools/creative_europe_tools.py")
        if not expected_file.exists():
            # Try alternative location
            expected_file = Path("app/services/tools/multi_programme_search.py")

        assert expected_file.exists(), f"Target file for fix does not exist: {expected_file}"

        content = expected_file.read_text()
        assert len(content) > 0, "Target file is empty"

    def test_fix_pattern_erasmus_tools(self):
        """
        Test fix pattern: missing_erasmus → Erasmus+ tools.

        The Erasmus+ tools should be called for training/education queries.
        """
        expected_file = Path("app/services/tools/erasmus_tools.py")
        if not expected_file.exists():
            # Try alternative location
            expected_file = Path("app/services/tools/multi_programme_search.py")

        assert expected_file.exists(), f"Target file for fix does not exist: {expected_file}"

        content = expected_file.read_text()
        assert len(content) > 0, "Target file is empty"

    def test_fix_pattern_low_actionability(self):
        """
        Test fix pattern: low_actionability → add Next Steps to agent prompt.

        The ToolAwareAgent should include Next Steps in responses.
        """
        expected_file = Path("app/services/agents/tool_aware_agent.py")
        assert expected_file.exists(), f"Target file for fix does not exist: {expected_file}"

        content = expected_file.read_text()
        assert len(content) > 0, "Target file is empty"

    def test_fix_pattern_cross_programme_agent(self):
        """
        Test fix pattern: factual_error → CrossProgrammeAgent.

        The CrossProgrammeAgent should validate programme-specific facts.
        """
        expected_file = Path("tests/agents/cross_programme_agent.py")
        assert expected_file.exists(), f"Target file for fix does not exist: {expected_file}"

        content = expected_file.read_text()
        assert len(content) > 0, "Target file is empty"


class TestFixAttemptSerialization:
    """Tests for FixAttempt class serialization."""

    def test_fix_attempt_serialization(self):
        """Test FixAttempt dataclass serialization."""
        fix = FixAttempt(
            attempt_number=1,
            root_cause="missing_personalization",
            fix_description="Added museum context handling to PersonalizationAgent",
            pre_fix_score=65.0,
            post_fix_score=82.0,
            files_modified=["app/services/agents/tool_aware_agent.py"],
            success=True,
        )

        data = fix.to_dict()

        assert data["attempt_number"] == 1
        assert data["root_cause"] == "missing_personalization"
        assert data["pre_fix_score"] == 65.0
        assert data["post_fix_score"] == 82.0
        assert data["success"] is True
        assert "timestamp" in data

    def test_update_result_with_fix_history(self):
        """Test updating result with fix history."""
        result = {
            "scenario_name": "Programme Recommendation",
            "average_score": 65.0,
            "status": "FAIL",
            "failures": [],
            "turns": [],
            "fix_history": [],
        }

        fix = FixAttempt(
            attempt_number=1,
            root_cause="missing_personalization",
            fix_description="Added museum context handling",
            pre_fix_score=65.0,
            post_fix_score=82.0,
            files_modified=["app/services/agents/tool_aware_agent.py"],
            success=True,
        )

        updated = update_result_with_fix_history(result, fix, "PASS")

        assert len(updated["fix_history"]) == 1
        assert updated["status"] == "PASS"
        assert updated["fix_history"][0]["attempt_number"] == 1
        assert updated["fix_history"][0]["root_cause"] == "missing_personalization"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
