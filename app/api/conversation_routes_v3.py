"""
V3 Conversation routes using the simplified agentic architecture.

V3 uses a single agentic loop (ToolAwareAgent) - no intent classification.
The agent decides what tools to use based on the query and conversation context.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services.analytics import get_conversation_analytics_service
from ..services.conversation.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v3/conversation", tags=["conversation-v3"])

# Initialize conversation manager (singleton)
conversation_manager = ConversationManager()

# Initialize analytics service
analytics_service = get_conversation_analytics_service()


class MessageRequest(BaseModel):
    message: str
    include_context: bool = True


class MessageResponse(BaseModel):
    response: str
    metadata: dict[str, Any]


@router.post("/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: int, request: MessageRequest, user_id: int = 1):
    """
    Send a message and stream the response using V3 simplified architecture.

    V3 uses a single agentic loop (no intent classification).
    The agent decides what tools to use based on the query and conversation context.

    Event types emitted:
    - status: Processing stages (processing, context_loaded, agent_starting, streaming_response)
    - conversation_name: Generated name for the conversation (first message only)
    - agent_thinking: Agent's reasoning at each iteration
    - tool_call: When a tool is being called
    - tool_result: When a tool completes
    - token: Streaming response text
    - complete: Final metadata with architecture="simplified_v3"
    - error: If something goes wrong
    """

    async def generate_stream():
        start_time = time.time()
        accumulated_response = []
        tools_used = []
        confidence = None
        final_metadata = {}
        status = "completed"
        error_message = None

        try:
            logger.info(f"[V3] Streaming message for conversation {conversation_id}")

            result = await conversation_manager.process_message_v3(
                conversation_id=conversation_id,
                user_message=request.message,
                user_id=user_id,
                streaming=True,
            )

            # If result is a dict (error case), yield it once
            if isinstance(result, dict):
                status = "error"
                error_message = result.get("error", "Unknown error")
                yield f"data: {json.dumps({'type': 'error', 'error': error_message})}\n\n"

                # Log error analytics
                response_time_ms = int((time.time() - start_time) * 1000)
                try:
                    analytics_service.log_conversation(
                        conversation_id=conversation_id,
                        question=request.message,
                        response=None,
                        tools_used=[],
                        confidence=None,
                        response_time_ms=response_time_ms,
                        metadata=result,
                        user_id=user_id,
                        status=status,
                        error_message=error_message,
                    )
                except Exception as analytics_error:
                    logger.warning(f"Failed to log error analytics: {analytics_error}")
                return

            # Otherwise, it should be an async generator
            async for chunk in result:
                event_type = chunk.get("type", "")

                # Accumulate response tokens
                if event_type == "token":
                    accumulated_response.append(chunk.get("content", ""))

                # Track tool calls
                elif event_type == "tool_call":
                    tool_name = chunk.get("tool", "")
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)

                # Capture final metadata
                elif event_type == "complete":
                    final_metadata = chunk.get("metadata", {})
                    confidence = final_metadata.get("confidence")
                    # Also capture tools from metadata if not tracked
                    if not tools_used and "tools_used" in final_metadata:
                        tools_used = final_metadata["tools_used"]

                # Handle errors during streaming
                elif event_type == "error":
                    status = "error"
                    error_message = chunk.get("error", "Unknown streaming error")

                # Yield the chunk as SSE
                if event_type in [
                    "status",
                    "progress",
                    "conversation_name",
                    "agent_thinking",
                    "tool_call",
                    "tool_result",
                    "token",
                    "complete",
                    "error",
                ]:
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Log analytics after stream completes
            response_time_ms = int((time.time() - start_time) * 1000)
            full_response = "".join(accumulated_response)

            try:
                analytics_service.log_conversation(
                    conversation_id=conversation_id,
                    question=request.message,
                    response=full_response if full_response else None,
                    tools_used=tools_used,
                    confidence=confidence,
                    response_time_ms=response_time_ms,
                    metadata=final_metadata,
                    user_id=user_id,
                    status=status,
                    error_message=error_message,
                )
            except Exception as analytics_error:
                logger.warning(f"Failed to log streaming analytics: {analytics_error}")

        except Exception as e:
            logger.error(f"[V3] Error in streaming: {e}")
            import traceback

            traceback.print_exc()
            status = "error"
            error_message = str(e)
            error_chunk = {"type": "error", "error": str(e), "stage": "error"}
            yield f"data: {json.dumps(error_chunk)}\n\n"

            # Log error analytics
            response_time_ms = int((time.time() - start_time) * 1000)
            try:
                analytics_service.log_conversation(
                    conversation_id=conversation_id,
                    question=request.message,
                    response=None,
                    tools_used=tools_used,
                    confidence=None,
                    response_time_ms=response_time_ms,
                    metadata={"error": str(e)},
                    user_id=user_id,
                    status=status,
                    error_message=error_message,
                )
            except Exception as analytics_error:
                logger.warning(f"Failed to log exception analytics: {analytics_error}")

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: int, request: MessageRequest, user_id: int = 1
) -> MessageResponse:
    """
    Send a message and get a response using V3 simplified architecture (non-streaming).

    V3 uses a single agentic loop - no intent classification, just the agent deciding
    what tools to use based on the query and conversation context.
    """
    start_time = time.time()
    status = "completed"
    error_message = None

    try:
        logger.info(f"[V3] Processing message for conversation {conversation_id}")

        result = await conversation_manager.process_message_v3(
            conversation_id=conversation_id,
            user_message=request.message,
            user_id=user_id,
            streaming=False,
        )

        response_text = result.get("response", "")
        metadata = result.get("metadata", {})

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Extract analytics data from metadata
        tools_used = metadata.get("tools_used", [])
        confidence = metadata.get("confidence", None)

        # Log to analytics (async, non-blocking)
        try:
            await analytics_service.log_conversation_async(
                conversation_id=conversation_id,
                question=request.message,
                response=response_text,
                tools_used=tools_used,
                confidence=confidence,
                response_time_ms=response_time_ms,
                metadata=metadata,
                user_id=user_id,
                status=status,
            )
        except Exception as analytics_error:
            logger.warning(f"Failed to log analytics: {analytics_error}")

        return MessageResponse(response=response_text, metadata=metadata)

    except Exception as e:
        logger.error(f"[V3] Error in send_message: {e}")
        status = "error"
        error_message = str(e)

        # Log error to analytics
        response_time_ms = int((time.time() - start_time) * 1000)
        try:
            await analytics_service.log_conversation_async(
                conversation_id=conversation_id,
                question=request.message,
                response=None,
                tools_used=[],
                confidence=None,
                response_time_ms=response_time_ms,
                metadata={"error": str(e)},
                user_id=user_id,
                status=status,
                error_message=error_message,
            )
        except Exception as analytics_error:
            logger.warning(f"Failed to log error analytics: {analytics_error}")

        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{conversation_id}/context")
async def get_conversation_context(conversation_id: int):
    """
    Get the current conversation context/memory for a conversation.
    """
    try:
        # Get recent messages from memory
        recent_messages = conversation_manager._get_recent_messages_simple(
            conversation_id=conversation_id, limit=10
        )

        return {
            "conversation_id": conversation_id,
            "message_count": len(recent_messages),
            "messages": recent_messages,
            "architecture": "simplified_v3",
        }

    except Exception as e:
        logger.error(f"[V3] Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{conversation_id}/context")
async def clear_conversation_context(conversation_id: int):
    """
    Clear the conversation context/memory for a conversation.
    """
    try:
        success = conversation_manager.clear_conversation(conversation_id)
        return {
            "success": success,
            "message": "Conversation context cleared",
            "conversation_id": conversation_id,
        }
    except Exception as e:
        logger.error(f"[V3] Error clearing context: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def health_check():
    """
    Health check for the V3 conversation system.

    Returns component health status with proper error handling.
    """
    import asyncio

    components = {"redis": False, "database": False, "gemini": False}
    errors = {}

    # Test Redis connection
    try:
        if conversation_manager.memory_service.redis_client:
            components["redis"] = conversation_manager.memory_service.redis_client.ping()
        else:
            errors["redis"] = "Redis client not initialized"
    except Exception as e:
        errors["redis"] = str(e)
        logger.warning(f"Health check - Redis failed: {e}")

    # Test database connection
    try:
        if conversation_manager.memory_service.ltm:
            # Use a non-existent ID to avoid loading real data
            conversation_manager.memory_service.ltm.get_summary(99999)
            components["database"] = True
        else:
            errors["database"] = "Database not initialized"
    except Exception as e:
        errors["database"] = str(e)
        logger.warning(f"Health check - Database failed: {e}")

    # Test Gemini connection with timeout
    try:
        model = None
        if (
            hasattr(conversation_manager, "tool_aware_agent")
            and conversation_manager.tool_aware_agent
            and hasattr(conversation_manager.tool_aware_agent, "llm")
        ):
            model = conversation_manager.tool_aware_agent.llm
        elif (
            hasattr(conversation_manager, "response_generator")
            and conversation_manager.response_generator
            and hasattr(conversation_manager.response_generator, "model")
        ):
            model = conversation_manager.response_generator.model

        if model:
            # Use asyncio timeout for the LLM call
            try:
                test_response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, "ping"),
                    timeout=5.0,  # 5 second timeout for health check
                )
                components["gemini"] = bool(test_response.text)
            except TimeoutError:
                errors["gemini"] = "Timeout waiting for response"
                logger.warning("Health check - Gemini timed out")
        else:
            errors["gemini"] = "Gemini model not initialized"
    except Exception as e:
        errors["gemini"] = str(e)
        logger.warning(f"Health check - Gemini failed: {e}")

    # Determine overall status
    all_ok = all(components.values())
    any_ok = any(components.values())

    if all_ok:
        status = "healthy"
    elif any_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    response = {
        "status": status,
        "architecture": "simplified_v3",
        "components": components,
        "timestamp": datetime.now().isoformat(),
    }

    if errors:
        response["errors"] = errors

    return response


# =============================================================================
# Analytics Endpoints
# =============================================================================


@router.get("/analytics/summary")
async def get_analytics_summary(hours: int = 24):
    """
    Get analytics summary for recent conversations.

    Args:
        hours: Number of hours to look back (default: 24)
    """
    try:
        summary = analytics_service.get_recent_analytics(hours=hours)
        return {"success": True, "period_hours": hours, "data": summary}
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/analytics/low-confidence")
async def get_low_confidence_conversations(threshold: float = 0.4, limit: int = 50):
    """
    Get conversations with low confidence scores for review and improvement.

    Args:
        threshold: Confidence threshold (default: 0.4)
        limit: Maximum number of results (default: 50)
    """
    try:
        conversations = analytics_service.get_low_confidence_conversations(
            threshold=threshold, limit=limit
        )
        return {
            "success": True,
            "threshold": threshold,
            "count": len(conversations),
            "conversations": conversations,
        }
    except Exception as e:
        logger.error(f"Error getting low confidence conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/analytics/search")
async def search_conversation_analytics(
    query: str | None = None,
    conversation_id: int | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Search and filter conversation analytics.

    Args:
        query: Full-text search query
        conversation_id: Filter by conversation ID
        min_confidence: Minimum confidence score
        max_confidence: Maximum confidence score
        limit: Maximum results (default: 100)
        offset: Pagination offset (default: 0)
    """
    try:
        results = analytics_service.search_conversations(
            query=query,
            conversation_id=conversation_id,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            limit=limit,
            offset=offset,
        )
        return {
            "success": True,
            "count": len(results),
            "limit": limit,
            "offset": offset,
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error searching analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/analytics/export")
async def export_conversation_analytics(start_date: str | None = None, end_date: str | None = None):
    """
    Export conversation analytics for analysis.

    Args:
        start_date: Start date (ISO format, e.g., 2026-01-01)
        end_date: End date (ISO format, e.g., 2026-01-31)
    """
    try:
        from datetime import datetime as dt

        start = dt.fromisoformat(start_date) if start_date else None
        end = dt.fromisoformat(end_date) if end_date else None

        results = analytics_service.export_conversations(start_date=start, end_date=end)
        return {
            "success": True,
            "count": len(results),
            "start_date": start_date,
            "end_date": end_date,
            "data": results,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}") from e
    except Exception as e:
        logger.error(f"Error exporting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
