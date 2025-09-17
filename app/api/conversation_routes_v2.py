"""
Updated conversation routes using the new architecture.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, AsyncGenerator
import json
import asyncio
import logging
from datetime import datetime

from ..services.conversation.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/conversation", tags=["conversation-v2"])

# Initialize conversation manager (singleton)
conversation_manager = ConversationManager()

class MessageRequest(BaseModel):
    message: str
    include_context: bool = True
    memory_strategy: str = "full"  # full, summary, minimal
    retrieval_config: Optional[Dict[str, Any]] = None
    tools_enabled: Optional[list] = None

class MessageResponse(BaseModel):
    response: str
    memory_used: Dict[str, Any]
    retrieval_stats: Dict[str, Any]
    tools_executed: list
    processing_time_ms: float
    confidence: float
    grounded: bool
    citations: list

@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: int,
    request: MessageRequest,
    user_id: int = 1  # Would come from auth in production
) -> MessageResponse:
    """
    Send a message and get a response using the new architecture.
    """
    try:
        logger.info(f"Processing message for conversation {conversation_id}")
        
        # Process message
        result = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message=request.message,
            user_id=user_id,
            streaming=False
        )
        
        # Format response
        tools_executed = result.get('tools_executed', False)
        if isinstance(tools_executed, bool):
            tools_executed = []
        
        return MessageResponse(
            response=result['response'],
            memory_used=result.get('memory_stats', {}),
            retrieval_stats=result.get('retrieval_stats', {}),
            tools_executed=tools_executed,
            processing_time_ms=result.get('processing_time', 0) * 1000,
            confidence=result.get('confidence', 0.0),
            grounded=result.get('grounded', False),
            citations=result.get('citations', [])
        )
        
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: int,
    request: MessageRequest,
    user_id: int = 1
):
    """
    Send a message and stream the response.
    """
    async def generate_stream():
        try:
            logger.info(f"Streaming message for conversation {conversation_id}")
            
            # Check if we should return an async generator or regular response
            result = await conversation_manager.process_message(
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
                # Format as SSE
                if chunk.get('type') == 'token':
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk.get('type') == 'complete':
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk.get('type') == 'error':
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            error_chunk = {'type': 'error', 'error': str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/{conversation_id}/memory")
async def get_conversation_memory(conversation_id: int):
    """
    Get memory statistics for a conversation.
    """
    try:
        stats = conversation_manager.get_conversation_stats(conversation_id)
        
        return {
            'conversation_id': conversation_id,
            'memory_stats': stats.get('memory', {}),
            'retrieval_stats': stats.get('retrieval', {}),
            'configuration': stats.get('config', {})
        }
        
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{conversation_id}/memory")
async def clear_conversation_memory(conversation_id: int):
    """
    Clear memory for a conversation.
    """
    try:
        success = conversation_manager.clear_conversation(conversation_id)
        return {"success": success, "message": "Memory cleared"}
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}/context")
async def get_conversation_context(conversation_id: int):
    """
    Get the current context for a conversation.
    """
    try:
        # Get context from memory service
        context = conversation_manager.memory_service.get_context_for_query(
            conversation_id=conversation_id,
            query="[Context Request]"
        )
        
        # Get detailed memory info
        memory_stats = conversation_manager.memory_service.get_memory_stats(conversation_id)
        
        return {
            'conversation_id': conversation_id,
            'context_preview': context[:500] + "..." if len(context) > 500 else context,
            'memory_stats': memory_stats,
            'context_length': len(context),
            'estimated_tokens': len(context) // 4
        }
        
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/test")
async def test_conversation_flow(conversation_id: int):
    """
    Test endpoint to verify the conversation system is working.
    """
    try:
        # Test with a simple question
        test_message = "What is Horizon Europe?"
        
        result = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message=test_message,
            user_id=1,
            streaming=False
        )
        
        return {
            'test_message': test_message,
            'response_received': bool(result.get('response')),
            'processing_time': result.get('processing_time', 0),
            'memory_working': bool(result.get('memory_stats')),
            'retrieval_working': bool(result.get('retrieval_stats')),
            'full_result': result
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check for the new system
@router.get("/health")
async def health_check():
    """
    Health check for the conversation system.
    """
    try:
        # Test Redis connection
        redis_ok = conversation_manager.memory_service.redis_client.ping()
        
        # Test database connection
        db_ok = True
        try:
            summary = conversation_manager.memory_service.ltm.get_summary(99999)
            db_ok = True
        except:
            db_ok = False
        
        # Test Gemini connection
        gemini_ok = True
        try:
            test_response = conversation_manager.response_generator.model.generate_content("Test")
            gemini_ok = bool(test_response.text)
        except:
            gemini_ok = False
        
        return {
            'status': 'healthy' if all([redis_ok, db_ok, gemini_ok]) else 'degraded',
            'components': {
                'redis': redis_ok,
                'database': db_ok,
                'gemini': gemini_ok
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }