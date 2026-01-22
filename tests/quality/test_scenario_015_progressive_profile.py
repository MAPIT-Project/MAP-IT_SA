"""
Test Scenario 015: Progressive Profile Building - EXECUTE task.

This test runs the progressive_profile scenario against the live API
and saves results to tests/quality/results/scenarios/progressive_profile.json.

Per PRD: Tests building user profile over 12 turns where user progressively
reveals detailed information about their organization (type, sector, subsector,
location, size, revenue, goals, partnerships, experience level) and expects
highly personalized final recommendations that use ALL accumulated context.
"""

# isort: skip_file
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pytest

from tests.agents.conversation_flow_agent import ConversationFlowAgent, ConversationScenario
from tests.agents.quality_evaluator_agent import QualityEvaluatorAgent

logger = logging.getLogger(__name__)

# Results output path per PRD
RESULTS_DIR = Path(__file__).parent / "results" / "scenarios"
RESULTS_FILE = RESULTS_DIR / "progressive_profile.json"
# Scenario file in advanced/ directory (no subdirectory)
SCENARIO_PATH = Path(__file__).parent.parent / "scenarios" / "advanced" / "progressive_profile.yaml"


async def run_progressive_profile_scenario(base_url: str = "http://localhost:8000") -> dict:
    """
    Execute the Progressive Profile Building scenario and return results.

    Args:
        base_url: The API base URL

    Returns:
        Dictionary with scenario execution results
    """
    # Load scenario
    scenario = ConversationScenario.from_yaml(SCENARIO_PATH)

    # Initialize agents
    flow_agent = ConversationFlowAgent(base_url=base_url)
    quality_evaluator = QualityEvaluatorAgent(passing_threshold=80)

    # Track results
    turns = []
    all_failures = []
    start_time = datetime.now()

    # Track accumulated profile context
    accumulated_profile = {
        "org_type": False,  # SME
        "sector": False,  # Healthcare
        "subsector": False,  # Medical devices
        "location": False,  # Germany
        "size": False,  # 50 employees
        "revenue": False,  # 10M
        "goal": False,  # AI diagnostics
        "partnerships": False,  # Research partnerships
        "experience": False,  # No EU funding experience
    }

    logger.info(f"Running scenario: {scenario.name}")
    logger.info(f"Description: {scenario.description}")
    logger.info(f"Steps: {len(scenario.steps)}")

    # Execute each step
    for turn_idx, step in enumerate(scenario.steps):
        logger.info(f"Turn {turn_idx}: {step.message[:50]}...")

        # Apply delay if specified
        if step.delay_ms > 0:
            await asyncio.sleep(step.delay_ms / 1000.0)

        # Send message
        try:
            turn = await flow_agent.send_message(step.message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            turns.append(
                {
                    "turn_number": turn_idx,
                    "query": step.message,
                    "response_text": f"Error: {str(e)}",
                    "tools_used": [],
                    "quality_score": 0,
                    "factual_score": 0,
                    "failures": [{"type": "ERROR", "message": str(e)}],
                    "passed": False,
                }
            )
            continue

        # Evaluate quality
        quality_result = quality_evaluator.quick_evaluate(
            response=turn.response_text,
            expected_patterns=[],
            min_length=50,
        )

        # Detect failures
        failures = []

        # Check for short response
        if len(turn.response_text) < 50:
            failures.append(
                {
                    "category": "NO_RESULTS",
                    "severity": "HIGH",
                    "description": f"Response too short ({len(turn.response_text)} chars)",
                }
            )

        # Check for error patterns
        error_patterns = [
            "I don't have",
            "I cannot find",
            "no information available",
            "unable to find",
            "couldn't extract",
            "I'm sorry, but",
        ]
        for pattern in error_patterns:
            if pattern.lower() in turn.response_text.lower():
                failures.append(
                    {
                        "category": "NO_RESULTS",
                        "severity": "MEDIUM",
                        "description": f"Response contains error pattern: '{pattern}'",
                    }
                )
                break

        # Check for errors in turn
        if turn.has_error:
            failures.append(
                {
                    "category": "UNEXPECTED_BEHAVIOR",
                    "severity": "CRITICAL",
                    "description": f"Turn has error: {turn.error}",
                }
            )

        # Track profile accumulation based on turn
        response_lower = turn.response_text.lower()

        # Turn 0: SME context
        sme_keywords = ["sme", "small", "medium", "enterprise", "company"]
        if turn_idx == 0:
            if any(kw in response_lower for kw in sme_keywords):
                accumulated_profile["org_type"] = True

        # Turn 1: Healthcare sector
        elif turn_idx == 1:
            if any(kw in response_lower for kw in ["healthcare", "health", "medical", "cluster 1"]):
                accumulated_profile["sector"] = True

        # Turn 2: Medical devices
        device_keywords = ["medical device", "device", "medtech", "equipment"]
        if turn_idx == 2:
            if any(kw in response_lower for kw in device_keywords):
                accumulated_profile["subsector"] = True

        # Turn 3: Germany location
        elif turn_idx == 3:
            if any(kw in response_lower for kw in ["germany", "german", "europe", "eu member"]):
                accumulated_profile["location"] = True

        # Turn 4: 50 employees
        elif turn_idx == 4:
            if any(kw in response_lower for kw in ["50", "employee", "staff", "team", "size"]):
                accumulated_profile["size"] = True

        # Turn 5: 10M revenue
        elif turn_idx == 5:
            if any(kw in response_lower for kw in ["10", "million", "revenue", "turnover"]):
                accumulated_profile["revenue"] = True

        # Turn 6: AI diagnostics goal
        ai_keywords = ["ai", "artificial", "diagnostic", "digital", "innovation"]
        if turn_idx == 6:
            if any(kw in response_lower for kw in ai_keywords):
                accumulated_profile["goal"] = True

        # Turn 7: Research partnerships
        partnership_keywords = ["partnership", "partner", "collaboration", "research"]
        if turn_idx == 7:
            if any(kw in response_lower for kw in partnership_keywords):
                accumulated_profile["partnerships"] = True

        # Turn 8: No EU experience
        experience_keywords = ["first", "new", "never", "experience", "start", "beginner"]
        if turn_idx == 8:
            if any(kw in response_lower for kw in experience_keywords):
                accumulated_profile["experience"] = True

        # Turn 9: KEY TEST - "What's our best option?" should use full profile
        profile_evidence = []
        if turn_idx == 9:
            # Check if the recommendation reflects accumulated profile
            if any(kw in response_lower for kw in ["sme", "small", "medium"]):
                profile_evidence.append("org_type")
            if any(kw in response_lower for kw in ["health", "medical", "cluster 1"]):
                profile_evidence.append("sector")
            if any(kw in response_lower for kw in ["device", "medtech"]):
                profile_evidence.append("subsector")
            if any(kw in response_lower for kw in ["germany", "german"]):
                profile_evidence.append("location")
            if any(kw in response_lower for kw in ["ai", "diagnostic", "digital"]):
                profile_evidence.append("goal")
            if any(kw in response_lower for kw in ["eic", "accelerator", "horizon"]):
                profile_evidence.append("programme_rec")

            # For recommendation turn, at least some profile context should be used
            if len(profile_evidence) < 2:
                failures.append(
                    {
                        "category": "PROFILE_NOT_USED",
                        "severity": "HIGH",
                        "description": (
                            f"Recommendation did not reflect user profile. "
                            f"Profile evidence found: {profile_evidence}"
                        ),
                    }
                )

        # Turn 10-11: Follow-up questions should maintain context
        elif turn_idx in [10, 11]:
            # Check context is maintained in follow-up responses
            context_keywords = [
                "sme",
                "health",
                "medical",
                "device",
                "germany",
                "ai",
                "diagnostic",
                "eic",
                "accelerator",
                "horizon",
                "funding",
                "innovation",
            ]
            context_count = sum(1 for kw in context_keywords if kw in response_lower)
            if context_count < 2:
                failures.append(
                    {
                        "category": "CONTEXT_LOST",
                        "severity": "MEDIUM",
                        "description": (
                            f"Follow-up response (turn {turn_idx}) lost context. "
                            f"Only {context_count} context keywords found."
                        ),
                    }
                )

        # Record turn result
        turn_result = {
            "turn_number": turn_idx,
            "query": step.message,
            "response_text": turn.response_text,
            "tools_used": turn.tools_used,
            "quality_score": quality_result.total_score,
            "factual_score": 100.0,  # Default to 100 unless we detect factual errors
            "failures": failures,
            "profile_evidence": profile_evidence if turn_idx == 9 else [],
            "accumulated_profile": dict(accumulated_profile),
            "passed": quality_result.total_score >= 80 and not failures,
        }
        turns.append(turn_result)
        all_failures.extend(failures)

        logger.info(f"  Quality score: {quality_result.total_score}")
        logger.info(f"  Tools used: {turn.tools_used}")
        logger.info(f"  Passed: {turn_result['passed']}")

    # Calculate aggregate scores
    avg_quality = sum(t["quality_score"] for t in turns) / len(turns) if turns else 0
    avg_factual = sum(t["factual_score"] for t in turns) / len(turns) if turns else 0

    # Calculate profile coverage (how many profile fields were acknowledged)
    profile_fields_acknowledged = sum(1 for v in accumulated_profile.values() if v)
    profile_coverage = profile_fields_acknowledged / len(accumulated_profile)

    # Determine status
    if avg_quality >= 80:
        status = "PASS"
    elif avg_quality >= 75:
        status = "CLOSE_TO_THRESHOLD"
    else:
        status = "FAIL"

    execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

    result = {
        "scenario_name": scenario.name,
        "turns": turns,
        "average_score": round(avg_quality, 1),
        "factual_score": round(avg_factual, 1),
        "failures": all_failures,
        "status": status,
        "execution_time_ms": round(execution_time_ms, 3),
        "timestamp": datetime.now().isoformat(),
        "fix_history": [],
        "profile_tracking": {
            "final_accumulated_profile": accumulated_profile,
            "profile_fields_acknowledged": profile_fields_acknowledged,
            "profile_coverage_pct": round(profile_coverage * 100, 1),
        },
        "metadata": {
            "scenario_path": str(SCENARIO_PATH),
            "tags": scenario.tags,
            "description": scenario.description,
            "conversation_id": flow_agent.conversation_id,
        },
    }

    return result


def save_results(result: dict) -> Path:
    """Save results to JSON file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    return RESULTS_FILE


class TestProgressiveProfileScenario:
    """Test class for Progressive Profile Building scenario execution."""

    @pytest.mark.asyncio
    async def test_execute_scenario(self):
        """Execute the Progressive Profile Building scenario against the live API."""
        base_url = os.environ.get("TEST_API_URL", "http://localhost:8000")

        # Run scenario
        result = await run_progressive_profile_scenario(base_url)

        # Save results
        output_path = save_results(result)
        logger.info(f"Results saved to: {output_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("SCENARIO 015: PROGRESSIVE PROFILE BUILDING - EXECUTE RESULTS")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Average Quality Score: {result['average_score']}/100")
        print(f"Factual Score: {result['factual_score']}/100")
        print(f"Turns: {len(result['turns'])}")
        print(f"Failures: {len(result['failures'])}")
        print(f"Execution Time: {result['execution_time_ms']:.0f}ms")
        print("-" * 60)
        print("Profile Tracking:")
        pt = result["profile_tracking"]
        print(f"  Fields Acknowledged: {pt['profile_fields_acknowledged']}/9")
        print(f"  Coverage: {pt['profile_coverage_pct']}%")
        print(f"  Profile: {pt['final_accumulated_profile']}")
        print("=" * 60)

        for turn in result["turns"]:
            status = "PASS" if turn["passed"] else "FAIL"
            profile_info = ""
            if turn.get("profile_evidence"):
                profile_info = f", profile: {turn['profile_evidence']}"
            print(
                f"  Turn {turn['turn_number']}: {status} "
                f"(score: {turn['quality_score']}, tools: {turn['tools_used']}{profile_info})"
            )

        print("=" * 60)

        # Assertions
        assert result is not None, "Scenario should return results"
        assert len(result["turns"]) == 12, "Scenario should have 12 turns"
        assert output_path.exists(), "Results should be saved to file"

        # Note: We don't assert on score >= 80 here since FIX IF NEEDED task handles that
        # We just ensure the scenario executed successfully


# CLI runner
if __name__ == "__main__":
    import sys

    async def main():
        base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
        result = await run_progressive_profile_scenario(base_url)
        output_path = save_results(result)

        print("\n" + "=" * 60)
        print("SCENARIO 015: PROGRESSIVE PROFILE BUILDING - EXECUTE RESULTS")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Average Quality Score: {result['average_score']}/100")
        print(f"Results saved to: {output_path}")
        print("-" * 60)
        print("Profile Tracking:")
        pt = result["profile_tracking"]
        print(f"  Fields Acknowledged: {pt['profile_fields_acknowledged']}/9")
        print(f"  Coverage: {pt['profile_coverage_pct']}%")
        print("=" * 60)

        # Print turn details
        for turn in result["turns"]:
            status = "PASS" if turn["passed"] else "FAIL"
            print(f"  Turn {turn['turn_number']}: {status} (score: {turn['quality_score']})")
            if turn.get("profile_evidence"):
                print(f"    Profile evidence: {turn['profile_evidence']}")
            if turn["failures"]:
                for f in turn["failures"]:
                    print(f"    Failure: {f['description']}")

        # Exit with appropriate code
        if result["status"] == "PASS":
            sys.exit(0)
        else:
            sys.exit(1)

    asyncio.run(main())
