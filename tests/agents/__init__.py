"""
Test sub-agents for automated conversation flow testing.

This module provides specialized agents for comprehensive
conversation testing:

1. ConversationFlowAgent - Simulates multi-turn conversations
2. ContextValidatorAgent - Validates state consistency
3. QualityEvaluatorAgent - Scores response quality
4. GoalTrackingAgent - Tracks user goal progress across turns
5. PersonalizationAgent - Validates context learning and personalization

Usage:
    from tests.agents import (
        ConversationFlowAgent,
        ContextValidatorAgent,
        QualityEvaluatorAgent,
        GoalTrackingAgent,
        PersonalizationAgent,
    )

    async def test_conversation():
        agent = ConversationFlowAgent(base_url="http://localhost:8000")
        turn = await agent.send_message("Find hydrogen funding calls")
        assert turn.response_text

    async def test_goal_tracking():
        tracker = GoalTrackingAgent()
        tracker.set_goal("Find funding for hydrogen research")
        progress = await tracker.evaluate_progress(query, response)
        assert progress.score >= 0.5

    async def test_personalization():
        agent = PersonalizationAgent()
        agent.add_turn("I'm from a German university", "For German universities...")
        result = await agent.validate_personalization(response)
        assert result.passed
"""

from tests.agents.context_validator_agent import ContextValidatorAgent
from tests.agents.conversation_flow_agent import ConversationFlowAgent
from tests.agents.goal_tracking_agent import GoalTrackingAgent
from tests.agents.personalization_agent import PersonalizationAgent
from tests.agents.quality_evaluator_agent import QualityEvaluatorAgent

__all__ = [
    "ConversationFlowAgent",
    "ContextValidatorAgent",
    "GoalTrackingAgent",
    "PersonalizationAgent",
    "QualityEvaluatorAgent",
]
