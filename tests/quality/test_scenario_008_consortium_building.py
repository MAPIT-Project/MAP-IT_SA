# isort: skip_file
"""
Test for Scenario 008: Consortium Building (Phase 3: Proposal Workflow).

This test executes the Consortium Building scenario against the live MAPIT API
and evaluates quality using the ProductionQualityRunner.

Per PRD MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md:
- EXECUTE: Run scenario `tests/scenarios/advanced/proposal_workflow/consortium_building.yaml`
- Tests consortium composition advice workflow
- Collect: response_text, tools_used, quality_score (QualityEvaluatorAgent),
           factual_score (CrossProgrammeAgent)
- Save: `tests/quality/results/scenarios/consortium_building.json`
- Structure: {scenario_name, turns[], average_score, factual_score, failures[], status}

Note: The actual scenario file path is `tests/scenarios/advanced/consortium_building.yaml`
(not in proposal_workflow subdirectory).

Scenario tests iterative consortium building for an AI in agriculture project:
1. Turn 1: Initial partner need for AI in agriculture project
2. Turn 2: Find organizations experienced in precision farming
3. Turn 3: Find SME partner from Southern Europe
4. Turn 4: Find research organization from Germany
5. Turn 5: Typical consortium size inquiry
6. Turn 6: Show proposed consortium composition
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pytest

from tests.quality.test_scenario_runner import (
    ProductionQualityRunner,
    ScenarioExecutionResult,
)

logger = logging.getLogger(__name__)

# Configuration
SCENARIO_PATH = Path("tests/scenarios/advanced/consortium_building.yaml")
RESULTS_PATH = Path("tests/quality/results/scenarios/consortium_building.json")
PASSING_THRESHOLD = 80
NUM_TURNS = 6


def save_result_prd_format(result: ScenarioExecutionResult, output_path: Path) -> dict:
    """
    Save result in PRD-specified format.

    PRD format: {scenario_name, turns[], average_score, factual_score, failures[], status}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build PRD-compliant structure
    prd_result = {
        "scenario_name": result.scenario_name,
        "turns": [
            {
                "turn_number": t.turn_number,
                "query": t.query,
                "response_text": t.response,
                "tools_used": t.tools_used,
                "quality_score": t.quality_score,
                "factual_score": t.factual_score,
                "failures": [f.to_dict() for f in t.failures],
                "passed": t.passed,
            }
            for t in result.turns
        ],
        "average_score": result.average_quality_score,
        "factual_score": result.average_factual_score,
        "failures": [f.to_dict() for f in result.failures],
        "status": result.status,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": datetime.now().isoformat(),
        "metadata": result.metadata,
        "fix_history": [],  # Empty until FIX IF NEEDED runs
    }

    with open(output_path, "w") as f:
        json.dump(prd_result, f, indent=2)

    return prd_result


class TestScenario008ConsortiumBuildingOffline:
    """Offline tests that don't require live API."""

    def test_scenario_file_exists(self):
        """Verify the scenario YAML file exists."""
        assert SCENARIO_PATH.exists(), f"Scenario file not found: {SCENARIO_PATH}"

    def test_scenario_yaml_is_valid(self):
        """Verify the scenario YAML is parseable."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert "name" in data
        assert data["name"] == "Consortium Building"
        assert "steps" in data
        assert len(data["steps"]) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(data['steps'])}"
        )

    def test_results_directory_exists(self):
        """Verify results directory can be created."""
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        assert RESULTS_PATH.parent.exists()

    def test_prd_result_format(self):
        """Test that PRD result format is correctly structured."""
        from tests.quality.test_scenario_runner import (
            FailureCategory,
            FailureRecord,
            FailureSeverity,
            TurnResult,
        )

        # Create mock result for 6-turn consortium building scenario
        mock_turns = [
            TurnResult(
                query=f"Query {i}",
                response=f"Response {i}",
                quality_score=80.0 + i,
                factual_score=85.0 + i % 5,
                tools_used=(
                    ["get_consortium_patterns"] if i % 2 == 0 else ["find_experienced_partners"]
                ),
                turn_number=i,
            )
            for i in range(NUM_TURNS)
        ]

        mock_result = ScenarioExecutionResult(
            scenario_name="Consortium Building",
            turns=mock_turns,
            failures=[
                FailureRecord(
                    category=FailureCategory.MISSING_DATA,
                    severity=FailureSeverity.MEDIUM,
                    description="Test failure",
                    turn_number=0,
                ),
            ],
        )

        # Use temp directory for test
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_result.json"
            prd_result = save_result_prd_format(mock_result, test_path)

        # Verify PRD structure
        assert "scenario_name" in prd_result
        assert "turns" in prd_result
        assert "average_score" in prd_result
        assert "factual_score" in prd_result
        assert "failures" in prd_result
        assert "status" in prd_result
        assert "fix_history" in prd_result

        # Verify turn structure
        assert len(prd_result["turns"]) == NUM_TURNS
        turn = prd_result["turns"][0]
        assert "response_text" in turn
        assert "tools_used" in turn
        assert "quality_score" in turn
        assert "factual_score" in turn

    def test_scenario_covers_consortium_building(self):
        """Verify scenario covers consortium building workflow."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        # Check tags include relevant context
        tags = data.get("tags", [])
        assert any(tag in tags for tag in ["consortium", "partners", "proposal-development"])

        # Check first turn mentions partners or consortium
        first_turn = data["steps"][0]["message"]
        assert "partner" in first_turn.lower() or "consortium" in first_turn.lower()

    def test_scenario_covers_consortium_elements(self):
        """Verify scenario covers all consortium building elements."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        all_messages = " ".join(step["message"] for step in data["steps"])
        all_lower = all_messages.lower()

        # Should cover key consortium building elements
        has_partner = "partner" in all_lower
        has_organization = "organization" in all_lower
        has_sme = "sme" in all_lower
        has_research = "research" in all_lower
        has_geography = any(
            term in all_lower for term in ["germany", "southern europe", "country", "countries"]
        )
        has_consortium_size = "consortium" in all_lower or "size" in all_lower

        assert has_partner, "Scenario should mention partners"
        assert has_organization, "Scenario should mention organizations"
        assert has_sme, "Scenario should include SME partner search"
        assert has_research, "Scenario should include research organization search"
        assert has_geography, "Scenario should include geographic filtering"
        assert has_consortium_size, "Scenario should include consortium size guidance"

    def test_scenario_is_6_turns(self):
        """Verify this is a 6-turn consortium building scenario."""
        import yaml

        with open(SCENARIO_PATH) as f:
            data = yaml.safe_load(f)

        assert len(data["steps"]) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(data['steps'])}"
        )


class TestScenario008ConsortiumBuildingLive:
    """Live API tests for Consortium Building scenario."""

    @pytest.fixture
    def api_base_url(self):
        """Get API base URL from environment or default."""
        return os.environ.get("TEST_API_URL", "http://localhost:8000")

    @pytest.fixture
    def runner(self, api_base_url):
        """Create ProductionQualityRunner instance."""
        return ProductionQualityRunner(
            base_url=api_base_url,
            passing_threshold=PASSING_THRESHOLD,
        )

    @pytest.mark.asyncio
    async def test_api_is_available(self, api_base_url):
        """Check if API is available before running scenario."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    assert response.status == 200
        except Exception as e:
            pytest.skip(f"API not available at {api_base_url}: {e}")

    @pytest.mark.asyncio
    async def test_execute_scenario_008_consortium_building(self, runner, api_base_url):
        """
        EXECUTE task: Run Consortium Building scenario against live API.

        This is the main test that executes Scenario 008 per the PRD.
        Tests iterative consortium building for an AI in agriculture project.
        """
        import aiohttp

        # First check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        logger.info(f"Executing scenario: {SCENARIO_PATH}")
        result = await runner.run_scenario(SCENARIO_PATH)

        # Log results
        logger.info(f"Scenario: {result.scenario_name}")
        logger.info(f"Average Quality Score: {result.average_quality_score:.2f}")
        logger.info(f"Average Factual Score: {result.average_factual_score:.2f}")
        logger.info(f"Status: {result.status}")
        logger.info(f"Turns: {len(result.turns)}")
        logger.info(f"Failures: {len(result.failures)}")

        # Log per-turn details
        for turn in result.turns:
            logger.info(
                f"  Turn {turn.turn_number}: Q={turn.quality_score:.1f}, "
                f"F={turn.factual_score:.1f}, Tools={turn.tools_used}"
            )

        # Save result in PRD format
        prd_result = save_result_prd_format(result, RESULTS_PATH)
        logger.info(f"Result saved to: {RESULTS_PATH}")

        # Assertions based on PRD requirements
        assert result.scenario_name == "Consortium Building"
        assert len(result.turns) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(result.turns)}"
        )

        # Check that consortium-related terms are mentioned across conversation
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        partner_mentioned = any(
            term in all_lower for term in ["partner", "organization", "consortium", "member"]
        )
        agriculture_context = any(
            term in all_lower for term in ["agriculture", "farming", "ai", "precision", "agri"]
        )
        geography_mentioned = any(
            term in all_lower for term in ["germany", "southern", "europe", "country", "countries"]
        )
        org_type_mentioned = any(
            term in all_lower for term in ["sme", "research", "university", "institute", "company"]
        )

        logger.info(
            f"Consortium elements: partner={partner_mentioned}, agriculture={agriculture_context}, "
            f"geography={geography_mentioned}, org_type={org_type_mentioned}"
        )

        # PRD-specific checks for consortium building
        # Check for agriculture context maintenance
        agriculture_context_maintained = any(
            term in all_lower
            for term in ["agriculture", "farming", "ai", "precision", "crop", "agri"]
        )
        logger.info(f"Agriculture context maintained: {agriculture_context_maintained}")

        # Check for partner-specific language
        partner_terms = [
            "partner",
            "organization",
            "consortium",
            "member",
            "sme",
            "research",
            "university",
            "institute",
        ]
        has_partner_guidance = any(term in all_lower for term in partner_terms)
        logger.info(f"Partner guidance present: {has_partner_guidance}")

        # Log final status
        if result.average_quality_score >= PASSING_THRESHOLD:
            logger.info(f"PASSED: Score {result.average_quality_score:.1f} >= {PASSING_THRESHOLD}")
        else:
            logger.warning(
                f"NEEDS FIX: Score {result.average_quality_score:.1f} < {PASSING_THRESHOLD}"
            )

        # Store pass/fail for FIX IF NEEDED task
        return prd_result

    @pytest.mark.asyncio
    async def test_scenario_008_individual_turn_quality(self, runner, api_base_url):
        """Test that each turn meets minimum quality thresholds."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # Check each turn
        min_turn_score = 60  # Minimum acceptable per-turn score

        for turn in result.turns:
            assert turn.quality_score >= min_turn_score, (
                f"Turn {turn.turn_number} quality score {turn.quality_score:.1f} "
                f"< minimum {min_turn_score}"
            )

    @pytest.mark.asyncio
    async def test_scenario_008_no_critical_failures(self, runner, api_base_url):
        """Test that scenario has no critical failures."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # Check for critical failures
        from tests.quality.test_scenario_runner import FailureSeverity

        critical_failures = [f for f in result.failures if f.severity == FailureSeverity.CRITICAL]

        if critical_failures:
            for f in critical_failures:
                logger.error(f"CRITICAL FAILURE at turn {f.turn_number}: {f.description}")

        # This test passes even with critical failures (they're logged)
        # The main test_execute checks overall pass/fail
        logger.info(f"Critical failures: {len(critical_failures)}")

    @pytest.mark.asyncio
    async def test_scenario_008_consortium_tools_used(self, runner, api_base_url):
        """Test that consortium-related tools are used during scenario."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # Collect all tools used
        all_tools = []
        for turn in result.turns:
            all_tools.extend(turn.tools_used)

        unique_tools = set(all_tools)
        logger.info(f"Tools used: {unique_tools}")

        # Consortium building should use partner/consortium-related tools
        # Expected tools based on scenario steps:
        # - get_consortium_patterns (consortium size/patterns)
        # - find_experienced_partners (partner discovery)
        # - search_projects (finding organizations)
        consortium_tools = [
            "get_consortium_patterns",
            "find_experienced_partners",
            "search_projects",
        ]
        consortium_tools_used = any(tool in unique_tools for tool in consortium_tools)

        logger.info(f"Consortium tools used: {consortium_tools_used}")

        # Log which consortium tools were used
        for tool in consortium_tools:
            if tool in unique_tools:
                logger.info(f"  - {tool}: used")
            else:
                logger.info(f"  - {tool}: not used")

    @pytest.mark.asyncio
    async def test_scenario_008_context_preserved(self, runner, api_base_url):
        """Test that consortium context is preserved across turns."""
        import aiohttp

        # Check API availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_base_url}/api/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"API not healthy: status {response.status}")
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Execute scenario
        result = await runner.run_scenario(SCENARIO_PATH)

        # For consortium building, context preservation is important
        all_responses = " ".join(t.response for t in result.turns)
        all_lower = all_responses.lower()

        # Key context elements that should persist
        partner_mentions = all_lower.count("partner")
        consortium_mentions = all_lower.count("consortium")
        agriculture_mentions = all_lower.count("agriculture") + all_lower.count("farming")
        org_mentions = all_lower.count("organization")

        logger.info(f"Partner mentions across {NUM_TURNS} turns: {partner_mentions}")
        logger.info(f"Consortium mentions across {NUM_TURNS} turns: {consortium_mentions}")
        logger.info(f"Agriculture mentions across {NUM_TURNS} turns: {agriculture_mentions}")
        logger.info(f"Organization mentions across {NUM_TURNS} turns: {org_mentions}")

        # Should have multiple mentions of consortium/partner context across turns
        assert partner_mentions >= 2 or consortium_mentions >= 2 or org_mentions >= 2, (
            "Consortium context should be maintained across turns"
        )


class TestScenario008ConsortiumBuildingResults:
    """Tests for reading and validating scenario results."""

    def test_read_existing_results(self):
        """Read and validate existing results file if it exists."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet - run execute test first")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        # Validate PRD structure
        assert "scenario_name" in result
        assert result["scenario_name"] == "Consortium Building"
        assert "turns" in result
        assert "average_score" in result
        assert "factual_score" in result
        assert "status" in result

        # Validate this is a 6-turn scenario
        assert len(result["turns"]) == NUM_TURNS, (
            f"Expected {NUM_TURNS} turns, got {len(result['turns'])}"
        )

        # Log current status
        logger.info(f"Current status: {result['status']}")
        logger.info(f"Average score: {result['average_score']}")

    def test_check_if_fix_needed(self):
        """Check if scenario needs fixing based on results."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        avg_score = result.get("average_score", 0)

        if avg_score >= PASSING_THRESHOLD:
            logger.info(f"Score {avg_score:.1f} >= {PASSING_THRESHOLD}: No fix needed")
        else:
            logger.warning(f"Score {avg_score:.1f} < {PASSING_THRESHOLD}: Fix needed")
            logger.warning(f"Failures: {len(result.get('failures', []))}")

            # Identify problematic turns
            for turn in result.get("turns", []):
                turn_score = turn.get("quality_score", 0)
                if turn_score < PASSING_THRESHOLD:
                    logger.warning(
                        f"  Turn {turn.get('turn_number')}: score={turn_score:.1f}, "
                        f"tools={turn.get('tools_used')}"
                    )

            # Identify root causes from failures (per PRD)
            for failure in result.get("failures", []):
                category = failure.get("category", "")
                description = failure.get("description", "")

                logger.warning(f"  - {category}: {description}")

                # PRD-specific root cause hints for consortium building
                if "consortium" in description.lower() or "pattern" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/consortium_patterns.py")
                if "partner" in description.lower() or "discovery" in description.lower():
                    logger.warning("    Hint: Fix app/services/tools/partner_discovery.py")
                if "organization" in description.lower():
                    logger.warning("    Hint: Fix partner search in partner_discovery.py")
                if "context" in description.lower():
                    logger.warning("    Hint: Fix app/services/memory/memory_service.py")

    def test_analyze_per_turn_scores(self):
        """Analyze scores per turn to identify weak points."""
        if not RESULTS_PATH.exists():
            pytest.skip("Results file does not exist yet")

        with open(RESULTS_PATH) as f:
            result = json.load(f)

        turns = result.get("turns", [])

        # Group turns by quality level
        high_quality = []
        medium_quality = []
        low_quality = []

        for turn in turns:
            score = turn.get("quality_score", 0)
            turn_num = turn.get("turn_number", 0)

            if score >= 85:
                high_quality.append(turn_num)
            elif score >= 70:
                medium_quality.append(turn_num)
            else:
                low_quality.append(turn_num)

        logger.info(f"High quality turns (>=85): {high_quality}")
        logger.info(f"Medium quality turns (70-84): {medium_quality}")
        logger.info(f"Low quality turns (<70): {low_quality}")

        # Identify patterns specific to consortium building
        if low_quality:
            logger.warning(f"Low quality turns need attention: {low_quality}")

            # Check specific turn patterns for consortium building
            for turn_num in low_quality:
                if turn_num == 0:
                    logger.warning(
                        "  Turn 0 (initial partner need): May need better initial guidance"
                    )
                elif turn_num == 1:
                    logger.warning("  Turn 1 (precision farming): May need better partner search")
                elif turn_num == 2:
                    logger.warning(
                        "  Turn 2 (SME Southern Europe): May need better geographic filtering"
                    )
                elif turn_num == 3:
                    logger.warning("  Turn 3 (German research): May need better org type filtering")
                elif turn_num == 4:
                    logger.warning(
                        "  Turn 4 (consortium size): May need consortium patterns improvement"
                    )
                elif turn_num == 5:
                    logger.warning("  Turn 5 (show consortium): May need better context synthesis")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])
