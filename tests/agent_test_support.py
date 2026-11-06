"""Isolate orchestration boundaries in preprocessing/context-reset unit tests."""

import os
from unittest.mock import AsyncMock, Mock

import pytest


def isolate_agent_loop(agent):
    """Keep real query preprocessing while replacing model/tool execution."""
    agent.quality_analyzer = None
    agent.analytics = None
    agent._select_model_for_query = Mock()

    async def finish(query, context, plan, event_callback=None):
        decision = await agent._reason_next_step(query, context, plan)
        plan.final_answer = decision["conclusion"]
        plan.confidence = decision["confidence"]
        return 1, {}

    agent._execute_react_loop = AsyncMock(side_effect=finish)


def required_live_conversation_id():
    """Use a provisioned test conversation; V3 has no conversation-create route."""
    value = os.getenv("MAPIT_TEST_CONVERSATION_ID", "")
    if not value.isdecimal() or int(value) <= 0:
        pytest.fail(
            "Live conversation tests require MAPIT_TEST_CONVERSATION_ID to name a "
            "provisioned numeric conversation in a disposable test instance"
        )
    return int(value)
