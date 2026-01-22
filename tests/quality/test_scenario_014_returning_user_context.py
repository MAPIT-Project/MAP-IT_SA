"""
Test Scenario 014: Returning User Context - EXECUTE task.

This test runs the returning_user_context scenario against the live API
and saves results to tests/quality/results/scenarios/returning_user_context.json.

Per PRD: Tests recalling context from earlier in conversation - a researcher
working on hydrogen storage establishes context early, provides organization
details, then later references the hydrogen topic expecting the system to recall
without asking for clarification.
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
RESULTS_FILE = RESULTS_DIR / "returning_user_context.json"
# Scenario file in advanced/ directory
SCENARIO_PATH = (
    Path(__file__).parent.parent / "scenarios" / "advanced" / "returning_user_context.yaml"
)


async def run_returning_user_context_scenario(base_url: str = "http://localhost:8000") -> dict:
    """
    Execute the Returning User Context scenario and return results.

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
        if len(turn.response_text) < 100:
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
        ]
        for pattern in error_patterns:
            if pattern.lower() in turn.response_text.lower():
                failures.append(
                    {
                        "category": "NO_RESULTS",
                        "severity": "HIGH",
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

        # Check for context recall in final turn (Turn 3)
        # The key test: When user says "I mentioned earlier I work on hydrogen",
        # system should recall the context and provide hydrogen-related calls
        context_evidence = []
        if turn_idx == 3:  # Final turn - check context recall
            # Keywords that show hydrogen context was recalled
            hydrogen_context_keywords = [
                "hydrogen",
                "storage",
                "energy",
                "clean",
                "fuel",
                "renewable",
                "cluster 5",
                "cl5",
            ]
            # Keywords that show organization context was recalled
            org_context_keywords = [
                "germany",
                "institute",
                "research",
                "horizon",
            ]

            response_lower = turn.response_text.lower()
            for keyword in hydrogen_context_keywords:
                if keyword in response_lower:
                    context_evidence.append(f"hydrogen:{keyword}")
            for keyword in org_context_keywords:
                if keyword in response_lower:
                    context_evidence.append(f"org:{keyword}")

            # For returning user context, we specifically need hydrogen context recall
            hydrogen_recalled = any(kw in response_lower for kw in hydrogen_context_keywords)
            if not hydrogen_recalled:
                failures.append(
                    {
                        "category": "CONTEXT_NOT_RECALLED",
                        "severity": "HIGH",
                        "description": (
                            "System did not recall hydrogen context when user referenced it. "
                            f"Found: {context_evidence}"
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
            "context_evidence": context_evidence if turn_idx == 3 else [],
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


class TestReturningUserContextScenario:
    """Test class for Returning User Context scenario execution."""

    @pytest.mark.asyncio
    async def test_execute_scenario(self):
        """Execute the Returning User Context scenario against the live API."""
        base_url = os.environ.get("TEST_API_URL", "http://localhost:8000")

        # Run scenario
        result = await run_returning_user_context_scenario(base_url)

        # Save results
        output_path = save_results(result)
        logger.info(f"Results saved to: {output_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("SCENARIO 014: RETURNING USER CONTEXT - EXECUTE RESULTS")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Average Quality Score: {result['average_score']}/100")
        print(f"Factual Score: {result['factual_score']}/100")
        print(f"Turns: {len(result['turns'])}")
        print(f"Failures: {len(result['failures'])}")
        print(f"Execution Time: {result['execution_time_ms']:.0f}ms")
        print("=" * 60)

        for turn in result["turns"]:
            status = "PASS" if turn["passed"] else "FAIL"
            context_info = ""
            if turn.get("context_evidence"):
                context_info = f", context: {turn['context_evidence']}"
            print(
                f"  Turn {turn['turn_number']}: {status} "
                f"(score: {turn['quality_score']}, tools: {turn['tools_used']}{context_info})"
            )

        print("=" * 60)

        # Assertions
        assert result is not None, "Scenario should return results"
        assert len(result["turns"]) == 4, "Scenario should have 4 turns"
        assert output_path.exists(), "Results should be saved to file"

        # Note: We don't assert on score >= 80 here since FIX IF NEEDED task handles that
        # We just ensure the scenario executed successfully


# CLI runner
if __name__ == "__main__":
    import sys

    async def main():
        base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
        result = await run_returning_user_context_scenario(base_url)
        output_path = save_results(result)

        print("\n" + "=" * 60)
        print("SCENARIO 014: RETURNING USER CONTEXT - EXECUTE RESULTS")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Average Quality Score: {result['average_score']}/100")
        print(f"Results saved to: {output_path}")
        print("=" * 60)

        # Print turn details
        for turn in result["turns"]:
            status = "PASS" if turn["passed"] else "FAIL"
            print(f"  Turn {turn['turn_number']}: {status} (score: {turn['quality_score']})")
            if turn.get("context_evidence"):
                print(f"    Context evidence: {turn['context_evidence']}")
            if turn["failures"]:
                for f in turn["failures"]:
                    print(f"    Failure: {f['description']}")

        # Exit with appropriate code
        if result["status"] == "PASS":
            sys.exit(0)
        else:
            sys.exit(1)

    asyncio.run(main())
