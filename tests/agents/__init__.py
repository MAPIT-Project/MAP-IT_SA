"""
Test sub-agents for automated conversation flow testing.

This module provides three specialized agents for comprehensive
conversation testing:

1. ConversationFlowAgent - Simulates multi-turn conversations
2. ContextValidatorAgent - Validates state consistency
3. QualityEvaluatorAgent - Scores response quality

Usage:
    from tests.agents import (
        ConversationFlowAgent,
        ContextValidatorAgent,
        QualityEvaluatorAgent,
    )

    async def test_conversation():
        agent = ConversationFlowAgent(base_url="http://localhost:8000")
        turn = await agent.send_message("Find hydrogen funding calls")
        assert turn.response_text
"""

from tests.agents.context_validator_agent import ContextValidatorAgent
from tests.agents.conversation_flow_agent import ConversationFlowAgent
from tests.agents.quality_evaluator_agent import QualityEvaluatorAgent

__all__ = [
    "ConversationFlowAgent",
    "ContextValidatorAgent",
    "QualityEvaluatorAgent",
]
