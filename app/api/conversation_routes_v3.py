"""
V3 Conversation routes using the simplified agentic architecture.

V3 uses a single agentic loop (ToolAwareAgent) - no intent classification.
The agent decides what tools to use based on the query and conversation context.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime

from ..services.conversation.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v3/conversation", tags=["conversation-v3"])

# Initialize conversation manager (singleton)
conversation_manager = ConversationManager()


class MessageRequest(BaseModel):
    message: str
    include_context: bool = True


class MessageResponse(BaseModel):
    response: str
    metadata: Dict[str, Any]


@router.post("/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: int,
    request: MessageRequest,
    user_id: int = 1
):
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
        try:
            logger.info(f"[V3] Streaming message for conversation {conversation_id}")

            result = await conversation_manager.process_message_v3(
                conversation_id=conversation_id,
                user_message=request.message,
                user_id=user_id,
                streaming=True
            )

            # If result is a dict (error case), yield it once
            if isinstance(result, dict):
                yield f"data: {json.dumps({'type': 'error', 'error': result.get('error', 'Unknown error')})}\n\n"
                return

            # Otherwise, it should be an async generator
            async for chunk in result:
                # Format as SSE - include ALL V3 event types
                event_type = chunk.get('type', '')
                if event_type in ['status', 'progress', 'conversation_name', 'agent_thinking', 'tool_call', 'tool_result', 'token', 'complete', 'error']:
                    yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"[V3] Error in streaming: {e}")
            import traceback
            traceback.print_exc()
            error_chunk = {'type': 'error', 'error': str(e), 'stage': 'error'}
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: int,
    request: MessageRequest,
    user_id: int = 1
) -> MessageResponse:
    """
    Send a message and get a response using V3 simplified architecture (non-streaming).

    V3 uses a single agentic loop - no intent classification, just the agent deciding
    what tools to use based on the query and conversation context.
    """
    try:
        logger.info(f"[V3] Processing message for conversation {conversation_id}")

        result = await conversation_manager.process_message_v3(
            conversation_id=conversation_id,
            user_message=request.message,
            user_id=user_id,
            streaming=False
        )

        return MessageResponse(
            response=result.get('response', ''),
            metadata=result.get('metadata', {})
        )

    except Exception as e:
        logger.error(f"[V3] Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/context")
async def get_conversation_context(conversation_id: int):
    """
    Get the current conversation context/memory for a conversation.
    """
    try:
        # Get recent messages from memory
        recent_messages = conversation_manager._get_recent_messages_simple(
            conversation_id=conversation_id,
            limit=10
        )

        return {
            'conversation_id': conversation_id,
            'message_count': len(recent_messages),
            'messages': recent_messages,
            'architecture': 'simplified_v3'
        }

    except Exception as e:
        logger.error(f"[V3] Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            "conversation_id": conversation_id
        }
    except Exception as e:
        logger.error(f"[V3] Error clearing context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for the V3 conversation system.

    Returns component health status with proper error handling.
    """
    import asyncio

    components = {
        'redis': False,
        'database': False,
        'gemini': False
    }
    errors = {}

    # Test Redis connection
    try:
        if conversation_manager.memory_service.redis_client:
            components['redis'] = conversation_manager.memory_service.redis_client.ping()
        else:
            errors['redis'] = 'Redis client not initialized'
    except Exception as e:
        errors['redis'] = str(e)
        logger.warning(f"Health check - Redis failed: {e}")

    # Test database connection
    try:
        if conversation_manager.memory_service.ltm:
            # Use a non-existent ID to avoid loading real data
            conversation_manager.memory_service.ltm.get_summary(99999)
            components['database'] = True
        else:
            errors['database'] = 'Database not initialized'
    except Exception as e:
        errors['database'] = str(e)
        logger.warning(f"Health check - Database failed: {e}")

    # Test Gemini connection with timeout
    try:
        if hasattr(conversation_manager, 'response_generator') and conversation_manager.response_generator.model:
            # Use asyncio timeout for the LLM call
            try:
                test_response = await asyncio.wait_for(
                    asyncio.to_thread(
                        conversation_manager.response_generator.model.generate_content,
                        "ping"
                    ),
                    timeout=5.0  # 5 second timeout for health check
                )
                components['gemini'] = bool(test_response.text)
            except asyncio.TimeoutError:
                errors['gemini'] = 'Timeout waiting for response'
                logger.warning("Health check - Gemini timed out")
        else:
            errors['gemini'] = 'Gemini model not initialized'
    except Exception as e:
        errors['gemini'] = str(e)
        logger.warning(f"Health check - Gemini failed: {e}")

    # Determine overall status
    all_ok = all(components.values())
    any_ok = any(components.values())

    if all_ok:
        status = 'healthy'
    elif any_ok:
        status = 'degraded'
    else:
        status = 'unhealthy'

    response = {
        'status': status,
        'architecture': 'simplified_v3',
        'components': components,
        'timestamp': datetime.now().isoformat()
    }

    if errors:
        response['errors'] = errors

    return response
