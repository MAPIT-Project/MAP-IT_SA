"""
Main conversation management system that orchestrates all components.
Simplified V3 Architecture - Focused on Agentic AI with ToolAwareAgent.
"""

import asyncio
import json
import logging
import os
import random
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.pool

from ...core.atomic_storage import StorageResult, get_atomic_storage
from ...core.conversation_lock import get_conversation_lock
from ..memory.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Central manager for all conversation operations with V3 SIMPLIFIED ARCHITECTURE.

    V3 uses a single agentic loop (ToolAwareAgent) without intent classification.
    The agent decides what tools to use based on the query and conversation context.
    """

    def __init__(self):
        """Initialize all subsystems"""
        # Set default values for all attributes to prevent AttributeError if initialization fails
        self.memory_service = None
        self.db_pool = None
        self.atomic_storage = None
        self.tool_aware_agent = None
        self._tool_aware_agent_available = False
        self.config = {}

        try:
            # Memory management
            self.memory_service = MemoryService()

            # Database pool
            db_url = os.getenv("DATABASE_URL")
            self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, db_url) if db_url else None

            # Atomic message storage for conversation consistency
            self.atomic_storage = get_atomic_storage(self.db_pool, self.memory_service)
            logger.info("✅ Atomic message storage initialized")

            # Tool-Aware Agent - Single entry point for simplified architecture
            try:
                from ..agents.tool_aware_agent import ToolAwareAgent

                self.tool_aware_agent = ToolAwareAgent(max_iterations=5)
                self._tool_aware_agent_available = True
                logger.info("🛠️ ToolAwareAgent initialized (simplified architecture ready)")
            except Exception as e:
                logger.warning(f"⚠️ ToolAwareAgent unavailable: {e}")
                self.tool_aware_agent = None
                self._tool_aware_agent_available = False

            # Configuration
            self.config = self._load_configuration()

            logger.info("✅ ConversationManager initialized (Simplified Architecture V3)")

        except Exception as e:
            logger.error(f"❌ ConversationManager initialization error: {e}", exc_info=True)

    def _load_configuration(self) -> dict[str, Any]:
        """Load system configuration."""
        return {
            "max_retrieval_chunks": int(os.getenv("MAX_RETRIEVAL_CHUNKS", 4)),
            "max_context_tokens": int(os.getenv("MAX_CONTEXT_TOKENS", 8000)),
            "summarize_every_n_turns": int(os.getenv("SUMMARIZE_EVERY_N_TURNS", 5)),
            "cache_ttl": int(os.getenv("RETRIEVAL_CACHE_TTL", 3600)),
        }

    def _create_error_response(self, error_message: str) -> dict[str, Any]:
        """Create error response."""
        return {
            "response": "I apologize, but I encountered an error processing your request.",
            "error": error_message,
            "success": False,
            "citations": [],
            "confidence": 0.0,
            "grounded": False,
            "processing_time": 0.0,
        }

    async def process_message_v3(
        self, conversation_id: int, user_message: str, user_id: int, streaming: bool = False
    ):
        """
        SIMPLIFIED ARCHITECTURE - Single Agentic Loop

        Routes ALL queries through the ToolAwareAgent. The agent decides:
        - What tools to use (or none)
        - How to handle follow-ups (from conversation context)
        - When to iterate and when to conclude
        """
        start_time = datetime.now()

        if not self._tool_aware_agent_available:
            raise RuntimeError("ToolAwareAgent is not available. V3 architecture requires it.")

        if streaming:
            return self._stream_v3_response_with_lock(
                conversation_id=conversation_id,
                user_message=user_message,
                user_id=user_id,
                start_time=start_time,
            )

        # Non-streaming: acquire lock and process
        async with await get_conversation_lock(conversation_id, timeout=60.0):
            logger.debug(f"🔒 Lock acquired for conversation {conversation_id} (sync)")
            return await self._process_v3_sync(
                conversation_id=conversation_id,
                user_message=user_message,
                user_id=user_id,
                start_time=start_time,
            )

    async def _process_v3_sync(
        self, conversation_id: int, user_message: str, user_id: int, start_time: datetime
    ) -> dict[str, Any]:
        """Non-streaming V3 processing with atomic message storage."""
        logger.info("=" * 60)
        logger.info("🚀 SIMPLIFIED ARCHITECTURE V3 (sync)")
        logger.info(f"   Query: {user_message[:100]}...")
        logger.info("=" * 60)

        try:
            # 1. Get conversation history
            recent_messages = self._get_recent_messages_simple(conversation_id, limit=10)
            conversation_context = self._format_conversation_for_agent(recent_messages)

            # 2. Add user message to memory for context during processing
            self._add_to_memory_only(
                conversation_id=conversation_id, role="user", content=user_message
            )

            # 3. Run the agentic loop
            agent_result = await self.tool_aware_agent.process_query(
                query=user_message,
                context=conversation_context,
                conversation_history=recent_messages,
                conversation_id=conversation_id,
            )

            # 4. Get the answer
            answer = self._extract_answer(agent_result, user_message)

            # 5. Fallback synthesis if needed
            if not answer or len(answer) < 50 or self._is_poor_quality_answer(answer):
                answer = await self._synthesize_agent_response(
                    query=user_message, agent_result=agent_result, context=conversation_context
                )

            # 6. Store BOTH messages atomically
            if answer:
                assistant_metadata = {}
                if agent_result:
                    assistant_metadata = {
                        "ai_provider": "gemini",
                        "ai_version": "V3",
                        "model_used": agent_result.get("model_used", "unknown"),
                        "data_source": "multi_programme",
                        "processing_time": (datetime.now() - start_time).total_seconds(),
                        "projects_found": len(
                            agent_result.get("tool_results", {}).get("projects", [])
                        )
                        if "projects" in agent_result.get("tool_results", {})
                        else 0,
                        "logs_question": user_message,
                        "logs_model_used": agent_result.get("model_used", "unknown"),
                        "logs_phases": json.dumps(
                            {"reasoning_steps": agent_result.get("reasoning_steps", [])}
                        ),
                        "logs_total_processing_time_ms": int(
                            (datetime.now() - start_time).total_seconds() * 1000
                        ),
                        "logs_success": agent_result.get("success", True),
                        "logs_average_relevance_score": str(agent_result.get("confidence", 0.8)),
                    }
                storage_result: StorageResult = await self.atomic_storage.store_message_pair(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_message=user_message,
                    assistant_message=answer,
                    citations=None,
                    assistant_metadata=assistant_metadata,
                )

                if not storage_result.success:
                    logger.error(f"❌ Atomic storage failed: {storage_result.error}")
                    return {
                        "response": answer,
                        "error": f"Message storage failed: {storage_result.error}",
                        "metadata": {
                            "intent_type": "agentic_v3",
                            "architecture": "simplified_v3",
                            "storage_error": storage_result.error,
                        },
                    }

            # 7. Build response
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "response": answer,
                "metadata": {
                    "intent_type": "agentic_v3",
                    "confidence": agent_result.get("confidence", 0.8),
                    "tools_used": agent_result.get("sources_used", []),
                    "iterations": agent_result.get("iterations", 0),
                    "processing_time_ms": processing_time,
                    "architecture": "simplified_v3",
                    "model_used": agent_result.get("model_used", "unknown"),
                },
            }

        except Exception as e:
            logger.error(f"V3 processing error: {e}")
            return self._create_error_response(str(e))

    def _extract_answer(self, agent_result: dict[str, Any], user_message: str) -> str:
        """Extract answer from agent result, applying V3 formatting if appropriate."""
        agent_answer = agent_result.get("answer", "")
        tool_results = agent_result.get("tool_results", {})

        # Markers that indicate the agent already produced a detailed, formatted response
        DETAILED_MARKERS = [
            "## Relevant Funded Projects",
            "## More Funded Projects",
            "## Similar Funded Projects",
            "## Project Search Results",
            "## Projects by ",
            "## Organization Statistics",
            "## Collaboration Network:",
            "| Country | Role |",
            "| Name | Country | Role |",
            "## Funding History Analysis:",
            "## Budget Calculation Results",
            "## Common ",
            "## Comparison",
            "## Cross-Analysis",
            "## Partner",
        ]

        agent_has_detailed_answer = (
            agent_answer
            and len(agent_answer) > 200
            and any(marker in agent_answer for marker in DETAILED_MARKERS)
        )

        if tool_results and not agent_has_detailed_answer:
            try:
                from ..response.v3_response_formatter import get_formatter

                formatter = get_formatter()
                formatted_answer = formatter.format_from_tool_results(tool_results, user_message)
                if formatted_answer:
                    # If the agent provided a substantial natural language answer, merge them
                    if agent_answer and len(agent_answer.strip()) > 30:
                        return f"{agent_answer.strip()}\n\n---\n\n{formatted_answer}"
                    return formatted_answer
            except Exception as e:
                logger.warning(f"V3 formatter failed: {e}")

        return agent_answer

    async def _stream_v3_response_with_lock(
        self, conversation_id: int, user_message: str, user_id: int, start_time: datetime
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Wrapper that acquires conversation lock before streaming response."""
        try:
            async with await get_conversation_lock(conversation_id, timeout=60.0):
                logger.debug(f"🔒 Lock acquired for conversation {conversation_id} (streaming)")
                async for event in self._stream_v3_response(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    user_id=user_id,
                    start_time=start_time,
                ):
                    yield event
        except Exception as e:
            logger.error(f"Error in locked streaming: {e}")
            yield {"type": "error", "error": str(e), "stage": "error"}

    async def _stream_v3_response(
        self, conversation_id: int, user_message: str, user_id: int, start_time: datetime
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream V3 response with real-time events."""
        try:
            yield {"type": "status", "stage": "processing", "message": "Processing..."}

            # 1. Get history and context
            recent_messages = self._get_recent_messages_simple(conversation_id, limit=10)
            conversation_context = self._format_conversation_for_agent(recent_messages)

            # Generate name for first message
            if not recent_messages:
                async for event in self._handle_first_message_naming(conversation_id, user_message):
                    yield event

            yield {
                "type": "status",
                "stage": "context_loaded",
                "message": f"Loaded {len(recent_messages)} messages from history",
            }

            # 2. Add user message to memory
            self._add_to_memory_only(conversation_id, "user", user_message)

            yield {
                "type": "status",
                "stage": "agent_starting",
                "message": "AI agent is analyzing your question...",
            }

            # 3. Run agent with streaming events
            agent_result = None
            async for event in self.tool_aware_agent.process_query_streaming(
                query=user_message,
                context=conversation_context,
                conversation_history=recent_messages,
                conversation_id=conversation_id,
            ):
                if event.get("type") in ["agent_thinking", "tool_call", "tool_result"]:
                    yield event
                elif event.get("type") == "agent_complete":
                    agent_result = event.get("result", {})

            # 4. Extract and synthesize answer
            answer = self._extract_answer(agent_result, user_message) if agent_result else None
            if not answer or len(answer) < 50 or self._is_poor_quality_answer(answer):
                yield {
                    "type": "status",
                    "stage": "synthesizing",
                    "message": "Synthesizing response from search results...",
                }
                answer = await self._synthesize_agent_response(
                    query=user_message, agent_result=agent_result, context=conversation_context
                )

            # 5. Atomic storage
            assistant_metadata = {}
            if agent_result:
                assistant_metadata = {
                    "ai_provider": "gemini",
                    "ai_version": "V3",
                    "model_used": agent_result.get("model_used", "unknown"),
                    "data_source": "multi_programme",
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "projects_found": len(agent_result.get("tool_results", {}).get("projects", []))
                    if "projects" in agent_result.get("tool_results", {})
                    else 0,
                    "logs_question": user_message,
                    "logs_model_used": agent_result.get("model_used", "unknown"),
                    "logs_phases": json.dumps(
                        {"reasoning_steps": agent_result.get("reasoning_steps", [])}
                    ),
                    "logs_total_processing_time_ms": int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    ),
                    "logs_success": agent_result.get("success", True),
                    "logs_average_relevance_score": str(agent_result.get("confidence", 0.8)),
                }
            storage_result = await self.atomic_storage.store_message_pair(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                assistant_message=answer,
                citations=None,
                assistant_metadata=assistant_metadata,
            )

            if not storage_result.success:
                yield {
                    "type": "error",
                    "error": f"Storage failed: {storage_result.error}",
                    "response": answer,
                }

            # 6. Stream tokens
            yield {
                "type": "status",
                "stage": "streaming_response",
                "message": "Generating response...",
            }
            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                yield {"type": "token", "content": answer[i : i + chunk_size]}
                await asyncio.sleep(0.01)

            # 7. Complete event
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            yield {
                "type": "complete",
                "ai_provider": "gemini",
                "ai_version": "V3",
                "model_used": agent_result.get("model_used", "unknown")
                if agent_result
                else "unknown",
                "data_source": "multi_programme",
                "processing_time": processing_time / 1000.0,
                "projects_found": len(agent_result.get("tool_results", {}).get("projects", []))
                if agent_result and "projects" in agent_result.get("tool_results", {})
                else 0,
                "logs": {
                    "question": user_message,
                    "model_used": agent_result.get("model_used", "unknown")
                    if agent_result
                    else "unknown",
                    "phases": {"reasoning_steps": agent_result.get("reasoning_steps", [])}
                    if agent_result
                    else {"reasoning_steps": []},
                    "total_processing_time_ms": int(processing_time),
                    "projects_retrieved": len(
                        agent_result.get("tool_results", {}).get("projects", [])
                    )
                    if agent_result and "projects" in agent_result.get("tool_results", {})
                    else 0,
                    "projects_processed": len(
                        agent_result.get("tool_results", {}).get("projects", [])
                    )
                    if agent_result and "projects" in agent_result.get("tool_results", {})
                    else 0,
                    "success": agent_result.get("success", True) if agent_result else True,
                    "average_relevance_score": agent_result.get("confidence", 0.8)
                    if agent_result
                    else 0.8,
                },
                "metadata": {
                    "architecture": "simplified_v3",
                    "confidence": agent_result.get("confidence", 0.8) if agent_result else 0.5,
                    "tools_used": agent_result.get("sources_used", []) if agent_result else [],
                    "processing_time_ms": processing_time,
                },
            }

        except Exception as e:
            logger.error(f"V3 streaming error: {e}")
            yield {"type": "error", "error": str(e), "stage": "error"}

    async def _handle_first_message_naming(self, conversation_id: int, user_message: str):
        """Generate and update conversation name for the first message."""
        try:
            from .conversation_namer import get_conversation_namer

            namer = get_conversation_namer()
            conversation_name = await namer.generate_name(user_message)
            await self._update_conversation_name(conversation_id, conversation_name)
            yield {
                "type": "conversation_name",
                "name": conversation_name,
                "conversation_id": conversation_id,
            }
        except Exception as e:
            logger.warning(f"Naming failed: {e}")

    def _format_conversation_for_agent(self, messages: list[dict]) -> str:
        """Format conversation history for the agent."""
        if not messages:
            return "No previous conversation."

        lines = []
        for i, msg in enumerate(messages[-6:]):
            role = msg.get("sender", "unknown").upper()
            content = msg.get("text", "")
            max_len = 4000 if (role == "ASSISTANT" and i == len(messages[-6:]) - 1) else 2000
            if len(content) > max_len:
                content = content[:max_len] + "... [truncated]"
            lines.append(f"{role}: {content}")
        return "\n\n".join(lines)

    def _is_poor_quality_answer(self, answer: str) -> bool:
        """Heuristics to detect raw document fragments or poor synthesis."""
        if not answer:
            return True
        poor_patterns = ["Application Form", "Table of Contents", "[Page", "indicative budget"]
        if any(p in answer for p in poor_patterns):
            return True
        if len(answer) > 200 and "**" not in answer and "•" not in answer:
            return True
        return False

    async def _synthesize_agent_response(
        self, query: str, agent_result: dict[str, Any], context: str
    ) -> str:
        """Synthesize a final response using Gemini if direct answer is missing/poor."""
        try:
            import google.generativeai as genai

            tool_info = [
                step["observation"]
                for step in agent_result.get("reasoning_steps", [])
                if step.get("observation")
            ]
            if not tool_info:
                return agent_result.get("answer", "I was unable to find relevant information.")

            prompt = f"Based on these results, answer: {query}\n\nRESULTS:\n{chr(10).join(tool_info[:3])}"
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return agent_result.get("answer", "Error in synthesis.")

    def _add_to_memory_only(self, conversation_id: int, role: str, content: str) -> None:
        """Add message to short-term memory only."""
        from ..memory.short_term_memory import ConversationTurn

        turn = ConversationTurn(
            message_id=random.randint(1000, 9999),
            role=role,
            content=content,
            timestamp=datetime.now(),
        )
        self.memory_service.stm.add_turn(conversation_id, turn)

    def _get_recent_messages_simple(self, conversation_id: int, limit: int = 5) -> list[dict]:
        """Fetch recent messages from database with fallback to memory service."""
        if self.db_pool:
            conn = self.db_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT text, sender FROM message WHERE conversation_id = %s ORDER BY created_at DESC LIMIT %s",
                    (conversation_id, limit),
                )
                return [{"text": r[0], "sender": r[1]} for r in cursor.fetchall()]
            except Exception as e:
                logger.error(f"DB retrieval failed: {e}")
            finally:
                self.db_pool.putconn(conn)
        return []

    async def _update_conversation_name(self, conversation_id: int, name: str) -> bool:
        """Update conversation name in database."""
        if not self.db_pool:
            return False
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE conversation SET name = %s WHERE id = %s", (name, conversation_id)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            self.db_pool.putconn(conn)
