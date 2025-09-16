from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator, Dict, Any
import os
import time
import json
import asyncio
from datetime import datetime
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
    routing_decision: Optional[str] = None
    data_source: Optional[str] = None
    intent_confidence: Optional[float] = None

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
        
        # Use Professional AI-Powered Context System
        print(f"🚀 Processing with Professional AI Context System: conversation {conversation_id}")
        print(f"📝 Question: '{request.message}'")
        
        from app.services.professional_context_ai import get_professional_ai_response
        
        # Try professional AI context analysis first
        ai_response = get_professional_ai_response(
            question=request.message,
            conversation_id=conversation_id
        )
        
        # If AI can answer from context, use that response
        if ai_response.get('success'):
            print("✅ Professional AI provided contextual answer")
            response = ai_response
        else:
            print("🔍 AI determined external search needed, using RAG")
            # Use RAG for external search when AI determines it's needed
            # IMPORTANT: Pass the user's original message to preserve intent (e.g., "open calls")
            response = rag_service.get_ai_response_with_routing(
                question=request.message,
                max_projects_to_process=5,
                max_cordis_results=10
            )
            # Telemetry: log routing and intent for regression monitoring
            try:
                print(json.dumps({
                    'telemetry': 'conversation_routing',
                    'conversation_id': conversation_id,
                    'question': request.message,
                    'routing_decision': response.get('routing_decision'),
                    'intent_confidence': response.get('intent_confidence'),
                    'data_source': response.get('data_source')
                }))
            except Exception:
                pass
        
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
            response=response.get('answer') or response.get('response') or '',
            context_used=response.get('context_used', False),
            resolved_question=response.get('resolved_question'),
            follow_up_suggestions=response.get('follow_up_suggestions', []),
            projects_discussed=response.get('discussed_projects', []),
            processing_time=processing_time,
            routing_decision=response.get('routing_decision'),
            data_source=response.get('data_source'),
            intent_confidence=response.get('intent_confidence')
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

def _get_conversation_messages(conversation_id: int) -> List[Dict[str, Any]]:
    """Get conversation messages from database"""
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return []
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute("""
            SELECT text, sender, "created_at"
            FROM message
            WHERE "conversation_id" = %s
            ORDER BY "created_at" ASC
            LIMIT 20
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'text': row['text'],
                'sender': row['sender'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else datetime.now().isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return messages
        
    except Exception as e:
        print(f"⚠️ Failed to get conversation messages: {e}")
        return []

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
            
            # Handle tuple return from resolve_references
            resolution_result = context_service_local.resolve_references(request.message, context)
            if isinstance(resolution_result, tuple):
                resolved_question, needs_detailed_lookup = resolution_result
            else:
                resolved_question = resolution_result
                needs_detailed_lookup = False
            
            if resolved_question != request.message:
                yield f"data: {json.dumps({'type': 'status', 'stage': 'reference_resolved', 'message': f'Resolved: {resolved_question}'})}\n\n"
            
            # Send processing status
            yield f"data: {json.dumps({'type': 'status', 'stage': 'processing', 'message': 'Processing your question intelligently...'})}\n\n"
            
            # Use Professional AI-Powered Context System for streaming
            print(f"🚀 Streaming: Using Professional AI Context System for conversation {conversation_id}")
            print(f"📝 Streaming Question: '{resolved_question}'")
            
            from app.services.professional_context_ai import get_professional_ai_response
            
            # Try professional AI context analysis
            ai_response = get_professional_ai_response(
                question=resolved_question,
                conversation_id=conversation_id
            )
            
            if ai_response.get('success'):
                print("✅ Streaming: Professional AI provided contextual answer")
                
                # Stream the AI response
                answer = ai_response['answer']
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                
                # Send completion
                completion_data = {
                    'type': 'complete',
                    'follow_up_suggestions': [],
                    'context_used': True,
                    'resolved_question': resolved_question,
                    'approach': ai_response.get('approach', 'professional_ai_context'),
                    'processing_time': 0,
                    'success': True
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                
            else:
                print("🔍 Streaming: Professional AI determined external search needed")
                # Determine intent to select appropriate streaming path
                intent, intent_conf = rag_service.determine_user_intent(resolved_question)
                search_query = resolved_question

                if intent == "SEARCH_CALLS" or intent == "FAQ":
                    # For calls and FAQ, use synchronous routing then stream the final answer
                    routed = rag_service.get_ai_response_with_routing(
                        question=search_query,
                        max_projects_to_process=5,
                        max_cordis_results=10
                    )
                    answer_text = routed.get('answer') or ''
                    chunk_size = 50
                    for i in range(0, len(answer_text), chunk_size):
                        chunk = answer_text[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                    completion_data = {
                        'type': 'complete',
                        'follow_up_suggestions': [],
                        'context_used': False,
                        'resolved_question': resolved_question,
                        'processing_time': routed.get('processing_time', 0),
                        'success': routed.get('success', True),
                        'routing_decision': routed.get('routing_decision', intent),
                        'data_source': routed.get('data_source'),
                        'intent_confidence': routed.get('intent_confidence', intent_conf)
                    }
                    try:
                        print(json.dumps({
                            'telemetry': 'conversation_routing_stream',
                            'conversation_id': conversation_id,
                            'question': resolved_question,
                            'routing_decision': completion_data['routing_decision'],
                            'data_source': completion_data.get('data_source')
                        }))
                    except Exception:
                        pass
                    yield f"data: {json.dumps(completion_data)}\n\n"
                else:
                    # Default: project streaming path with added routing metadata
                    async for chunk in rag_service.get_ai_response_stream(
                        question=search_query,
                        max_projects_to_process=5,
                        max_cordis_results=10
                    ):
                        if chunk['type'] == 'progress':
                            yield f"data: {json.dumps({'type': 'progress', 'stage': chunk['phase'], 'message': chunk['message']})}\n\n"
                        elif chunk['type'] == 'token':
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                        elif chunk['type'] == 'complete':
                            completion_data = {
                                'type': 'complete',
                                'follow_up_suggestions': [],
                                'context_used': False,
                                'resolved_question': resolved_question,
                                'processing_time': chunk.get('processing_time', 0),
                                'success': True,
                                'routing_decision': 'SEARCH_PROJECTS',
                                'data_source': chunk.get('data_source'),
                                'intent_confidence': intent_conf
                            }
                            try:
                                print(json.dumps({
                                    'telemetry': 'conversation_routing_stream',
                                    'conversation_id': conversation_id,
                                    'question': resolved_question,
                                    'routing_decision': 'SEARCH_PROJECTS',
                                    'data_source': chunk.get('data_source')
                                }))
                            except Exception:
                                pass
                            yield f"data: {json.dumps(completion_data)}\n\n"
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