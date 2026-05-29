from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agents.tool_aware_agent import ToolAwareAgent
from app.services.conversation.conversation_manager import ConversationManager


class TestExtractAnswerShort:
    def test_extract_answer_under_30_chars_discarded(self):
        """Test that agent answers <= 30 characters are discarded in favor of formatted tool results."""
        # Mock ConversationManager
        manager = ConversationManager.__new__(ConversationManager)

        agent_result = {
            "answer": "Here are calls:",  # 15 chars
            "tool_results": {
                "search_funding_calls": {
                    "success": True,
                    "calls": [{"title": "Test Call", "call_id": "ID1", "status": "open"}],
                }
            },
        }

        # Call _extract_answer
        result = manager._extract_answer(agent_result, "Find calls")

        # The short answer should be discarded, showing only formatted tool results
        assert "Here are calls" not in result
        assert "Test Call" in result

    def test_extract_answer_over_30_chars_preserved(self):
        """Test that agent answers > 30 characters are preserved and prepended to formatted tool results."""
        # Mock ConversationManager
        manager = ConversationManager.__new__(ConversationManager)

        agent_result = {
            "answer": "I found some open calls on Digital Europe that match your criteria:",  # 67 chars
            "tool_results": {
                "search_funding_calls": {
                    "success": True,
                    "calls": [{"title": "Test Call", "call_id": "ID1", "status": "open"}],
                }
            },
        }

        result = manager._extract_answer(agent_result, "Find calls")

        # The answer should be preserved and prepended
        assert "I found some open calls on Digital Europe" in result
        assert "Test Call" in result
        assert "---" in result


class TestAsyncContextualIntro:
    @pytest.mark.asyncio
    async def test_generate_contextual_intro_all_types(self):
        """Test that _generate_contextual_intro supports all result keys and uses async correctly."""
        # Mock ToolAwareAgent
        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.llm_flash = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Here is the generated intro sentence."
        agent.llm_flash.generate_content.return_method = mock_response

        # We need to mock generate_content to return our mock_response
        agent.llm_flash.generate_content = MagicMock(return_value=mock_response)

        tool_results = {
            "search_projects": {"success": True, "projects": [{"title": "Test Project"}]},
            "search_funding_calls": {"success": True, "calls": [{"title": "Test Call"}]},
        }

        intro = await agent._generate_contextual_intro("Find calls and projects", tool_results)

        # Verify that generate_content was called with a prompt containing query and result counts
        assert agent.llm_flash.generate_content.called
        prompt_arg = agent.llm_flash.generate_content.call_args[0][0]
        assert "Find calls and projects" in prompt_arg
        assert "1 matching projects found" in prompt_arg
        assert "1 funding opportunities found" in prompt_arg
        assert intro == "Here is the generated intro sentence."


class TestFirstMessageNaming:
    @pytest.mark.asyncio
    async def test_handle_first_message_naming_yields_correctly(self):
        """Test that _handle_first_message_naming yields conversation name event correctly."""
        # Mock ConversationManager
        manager = ConversationManager.__new__(ConversationManager)

        # Mock dependencies
        manager._update_conversation_name = AsyncMock()

        # Patch conversation namer
        mock_namer = MagicMock()
        mock_namer.generate_name = AsyncMock(return_value="Quantum Computing Project")

        with patch(
            "app.services.conversation.conversation_namer.get_conversation_namer",
            return_value=mock_namer,
        ):
            events = []
            async for event in manager._handle_first_message_naming(
                12345, "What is quantum computing?"
            ):
                events.append(event)

            assert len(events) == 1
            assert events[0]["type"] == "conversation_name"
            assert events[0]["name"] == "Quantum Computing Project"
            assert events[0]["conversation_id"] == 12345
            assert mock_namer.generate_name.called
            assert manager._update_conversation_name.called
