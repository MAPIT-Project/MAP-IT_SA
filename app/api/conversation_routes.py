from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator
import os
import time
import json
import asyncio
from app.services.rag_service import CordisRAG
from app.services.conversation_context_service import ConversationContextService, ConversationContext
from dataclasses import asdict

router = APIRouter(prefix="/api/conversation", tags=["conversation"])

# Initialize services
rag_service = CordisRAG(use_local_db=False, ai_provider="gemini")
context_service = ConversationContextService(os.getenv("DATABASE_URL"))

class MessageRequest(BaseModel):
    message: str
    include_context: bool = True

class MessageResponse(BaseModel):
    response: str
    context_used: bool
    resolved_question: Optional[str]
    follow_up_suggestions: List[str]
    projects_discussed: List[dict]
    processing_time: float

@router.post("/{conversation_id}/message", response_model=MessageResponse)
async def send_contextual_message(
    conversation_id: int,
    request: MessageRequest
):
    """Send a message with conversation context"""
    
    start_time = time.time()
    
    try:
        # Load conversation context
        if request.include_context:
            context = context_service.load_context(conversation_id)
        else:
            # Create minimal context for non-contextual queries
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=0,
                messages=[],
                discussed_projects=[],
                mentioned_organizations=[],
                topics_of_interest=[],
                last_search_results=[],
                last_query_type='UNKNOWN',
                follow_up_expected=False
            )
        
        # Process with RAG service
        response = rag_service.get_ai_response_with_context(
            question=request.message,
            conversation_context=context
        )
        
        # Save message to database (implement this based on your schema)
        # save_message(conversation_id, request.message, response['answer'])
        
        # Update context with new information
        context_service.update_context(
            conversation_id,
            {'text': request.message, 'sender': 'user'},
            response
        )
        
        processing_time = time.time() - start_time
        
        return MessageResponse(
            response=response['answer'],
            context_used=response.get('context_used', False),
            resolved_question=response.get('resolved_question'),
            follow_up_suggestions=response.get('follow_up_suggestions', []),
            projects_discussed=response.get('discussed_projects', []),
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}/context")
async def get_conversation_context(conversation_id: int):
    """Get the current context for a conversation"""
    
    try:
        context = context_service.load_context(conversation_id)
        return {
            'conversation_id': conversation_id,
            'message_count': len(context.messages),
            'projects_discussed': [asdict(p) for p in context.discussed_projects],
            'topics': context.topics_of_interest,
            'last_query_type': context.last_query_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/reset-context")
async def reset_conversation_context(conversation_id: int):
    """Reset the context for a conversation"""
    
    # Clear from cache
    if conversation_id in context_service.context_cache:
        del context_service.context_cache[conversation_id]
    
    return {"message": "Context reset successfully"}

@router.get("/{conversation_id}/suggestions")
async def get_follow_up_suggestions(conversation_id: int):
    """Get follow-up suggestions for a conversation"""
    
    try:
        context = context_service.load_context(conversation_id)
        suggestions = context_service.generate_follow_up_suggestions(context, {})
        return {
            'suggestions': suggestions,
            'has_context': len(context.discussed_projects) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/message/stream")
async def send_contextual_message_stream(
    conversation_id: int,
    request: MessageRequest
):
    """Send a message with conversation context and stream the response"""
    
    async def generate_stream():
        try:
            # Load conversation context
            if request.include_context:
                context = context_service.load_context(conversation_id)
            else:
                # Create minimal context for non-contextual queries
                context = ConversationContext(
                    conversation_id=conversation_id,
                    user_id=0,
                    messages=[],
                    discussed_projects=[],
                    mentioned_organizations=[],
                    topics_of_interest=[],
                    last_search_results=[],
                    last_query_type='UNKNOWN',
                    follow_up_expected=False
                )
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'stage': 'context_loaded', 'message': 'Conversation context loaded'})}\n\n"
            
            # Resolve references
            from app.services.conversation_context_service import ConversationContextService
            context_service_local = ConversationContextService(os.getenv("DATABASE_URL"))
            resolved_question = context_service_local.resolve_references(request.message, context)
            
            if resolved_question != request.message:
                yield f"data: {json.dumps({'type': 'status', 'stage': 'reference_resolved', 'message': f'Resolved: {resolved_question}'})}\n\n"
            
            # Send processing status
            yield f"data: {json.dumps({'type': 'status', 'stage': 'processing', 'message': 'Processing your question...'})}\n\n"
            
            # Get streaming response from RAG service
            async for chunk in rag_service.get_ai_response_stream_with_context(
                question=resolved_question,
                conversation_context=context
            ):
                if chunk['type'] == 'progress':
                    # Send progress updates
                    yield f"data: {json.dumps({'type': 'progress', 'stage': chunk['phase'], 'message': chunk['message']})}\n\n"
                elif chunk['type'] == 'token':
                    # Send token chunks
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                elif chunk['type'] == 'complete':
                    # Generate follow-up suggestions
                    suggestions = context_service_local.generate_follow_up_suggestions(context, chunk)
                    
                    # Send completion with metadata
                    completion_data = {
                        'type': 'complete',
                        'follow_up_suggestions': suggestions,
                        'context_used': True,
                        'resolved_question': resolved_question,
                        'projects_discussed': [asdict(p) for p in context.discussed_projects],
                        'processing_time': chunk.get('processing_time', 0)
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    
                    # Update context with new information
                    context_service.update_context(
                        conversation_id,
                        {'text': request.message, 'sender': 'user'},
                        chunk
                    )
                    break
                elif chunk['type'] == 'error':
                    yield f"data: {json.dumps({'type': 'error', 'error': chunk['error'], 'details': chunk.get('details', '')})}\n\n"
                    break
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Processing failed', 'details': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )