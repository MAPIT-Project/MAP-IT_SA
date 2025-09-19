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
    processing_phases = {}
    
    try:
        # Load conversation context
        context_load_start = time.time()
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
        processing_phases['context_loading'] = time.time() - context_load_start
        
        # Resolve references
        resolution_start = time.time()
        resolution_result = context_service.resolve_references(request.message, context)
        if isinstance(resolution_result, tuple):
            resolved_question, needs_detailed_lookup = resolution_result
        else:
            resolved_question = resolution_result
            needs_detailed_lookup = False
        processing_phases['reference_resolution'] = time.time() - resolution_start
        
        # Use context-aware intent detection for optimal routing
        intent_start = time.time()
        from app.services.intent_service import IntentService
        intent, intent_conf = IntentService.determine_intent_with_context(resolved_question, context)
        processing_phases['intent_detection'] = time.time() - intent_start
        
        print(f"🚀 Processing with Context-Aware Intent System: conversation {conversation_id}")
        print(f"📝 Question: '{resolved_question}'")
        print(f"🎯 Context-aware Intent: {intent} (confidence: {intent_conf})")
        
        # Unified processing based on intent
        if intent == "SEARCH_PROJECTS":
            # Use RAG for project searches
            search_start = time.time()
            response = rag_service.get_ai_response_with_routing(
                question=resolved_question,
                max_projects_to_process=5,
                max_cordis_results=10
            )
            processing_phases['search_execution'] = time.time() - search_start
        else:
            # For calls and FAQ, use standard routing
            search_start = time.time()
            response = rag_service.get_ai_response_with_routing(
                question=resolved_question,
                max_projects_to_process=5,
                max_cordis_results=10
            )
            processing_phases['search_execution'] = time.time() - search_start
        
        # Telemetry: log routing and intent for monitoring
        try:
            print(json.dumps({
                'telemetry': 'conversation_routing',
                'conversation_id': conversation_id,
                'question': resolved_question,
                'routing_decision': response.get('routing_decision', intent),
                'intent_confidence': response.get('intent_confidence', intent_conf),
                'data_source': response.get('data_source'),
                'processing_phases': processing_phases
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
        start_time = time.time()
        processing_phases = {}
        phases = []

        try:
            # Load conversation context
            if request.include_context:
                context_load_start = time.time()
                context = context_service.load_context(conversation_id)
                processing_phases['context_loading'] = time.time() - context_load_start
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

            # Send initial status - context resolution
            phases.append('context_resolution')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'context_resolution', 'message': 'Loading conversation context'})}\n\n"

            # Resolve references using the existing context service
            # Handle tuple return from resolve_references
            resolution_start = time.time()
            resolution_result = context_service.resolve_references(request.message, context)
            if isinstance(resolution_result, tuple):
                resolved_question, needs_detailed_lookup = resolution_result
            else:
                resolved_question = resolution_result
                needs_detailed_lookup = False
            processing_phases['reference_resolution'] = time.time() - resolution_start

            if resolved_question != request.message:
                phases.append('reference_resolved')
                yield f"data: {json.dumps({'type': 'status', 'stage': 'reference_resolved', 'message': f'References resolved'})}\n\n"

            # Intent detection status
            phases.append('intent_detection')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'intent_detection', 'message': 'Detecting intent with context'})}\n\n"

            # Early intent detection with context for optimal routing
            intent_start = time.time()
            from app.services.intent_service import IntentService
            intent, intent_conf = IntentService.determine_intent_with_context(resolved_question, context)
            processing_phases['intent_detection'] = time.time() - intent_start

            # Intent detected status
            phases.append('intent_detected')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'intent_detected', 'message': f'Intent detected: {intent}'})}\n\n"

            # Emit route selection event
            phases.append('route_selected')
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'route_selected', 'routing_decision': intent, 'intent_confidence': intent_conf})}\n\n"

            # Query extraction status
            phases.append('query_extraction')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'query_extraction', 'message': 'Extracting search queries'})}\n\n"

            # Queries extracted status
            phases.append('queries_extracted')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'queries_extracted', 'message': 'Queries prepared for search'})}\n\n"

            # Data retrieval status
            phases.append('data_retrieval')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'data_retrieval', 'message': 'Retrieving relevant data'})}\n\n"

            # Data enriched status
            phases.append('data_enriched')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'data_enriched', 'message': 'Enriching retrieved data'})}\n\n"

            # Data selected status
            phases.append('data_selected')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'data_selected', 'message': 'Selecting relevant data'})}\n\n"

            # Reranking status
            phases.append('reranking')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'reranking', 'message': 'Reranking results'})}\n\n"

            # Answer generation status
            phases.append('answer_generation')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'answer_generation', 'message': 'Generating answer'})}\n\n"

            # Context enhancement status
            phases.append('context_enhancement')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'context_enhancement', 'message': 'Enhancing with context'})}\n\n"

            # Streaming response status
            phases.append('streaming_response')
            yield f"data: {json.dumps({'type': 'status', 'stage': 'streaming_response', 'message': 'Streaming response'})}\n\n"

            # Use Professional AI-Powered Context System for streaming
            print(f"🚀 Streaming: Using Professional AI Context System for conversation {conversation_id}")
            print(f"📝 Streaming Question: '{resolved_question}'")
            print(f"🎯 Context-aware Intent: {intent} (confidence: {intent_conf})")
            
            # Unified streaming pipeline based on intent
            if intent == "SEARCH_PROJECTS":
                # Use RAG streaming for project searches
                search_start = time.time()
                async for chunk in rag_service.get_ai_response_stream(
                    question=resolved_question,
                    max_projects_to_process=5,
                    max_cordis_results=10
                ):
                    if chunk['type'] == 'progress':
                        yield f"data: {json.dumps({'type': 'progress', 'stage': chunk['phase'], 'message': chunk['message']})}\n\n"
                    elif chunk['type'] == 'token':
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                    elif chunk['type'] == 'complete':
                        processing_phases['search_execution'] = time.time() - search_start
                        total_time = time.time() - start_time

                        # Build proper logs object
                        logs_data = {
                            'question': resolved_question,
                            'model_used': chunk.get('model_used', 'gemini-2.5-flash-lite'),
                            'phases': phases,
                            'total_processing_time_ms': int(total_time * 1000),
                            'projects_retrieved': chunk.get('projects_retrieved', 0),
                            'projects_processed': chunk.get('projects_processed', 0),
                            'success': True,
                            'average_relevance_score': chunk.get('average_relevance_score', 0.0)
                        }

                        completion_data = {
                            'type': 'complete',
                            'ai_provider': 'google',
                            'ai_version': 'gemini-2.5-flash-lite',
                            'model_used': chunk.get('model_used', 'gemini-2.5-flash-lite'),
                            'data_source': chunk.get('data_source', 'CORDIS Database'),
                            'processing_time': total_time,
                            'projects_found': chunk.get('projects_found', 0),
                            'logs': logs_data,
                            'context_used': request.include_context,
                            'resolved_question': resolved_question,
                            'follow_up_suggestions': chunk.get('follow_up_suggestions', []),
                            'projects_discussed': chunk.get('projects_discussed', []),
                            'routing_decision': intent,
                            'intent_confidence': intent_conf
                        }
                        try:
                            print(json.dumps({
                                'telemetry': 'conversation_routing_stream',
                                'conversation_id': conversation_id,
                                'question': resolved_question,
                                'routing_decision': intent,
                                'data_source': chunk.get('data_source'),
                                'processing_phases': processing_phases
                            }))
                        except Exception:
                            pass
                        yield f"data: {json.dumps(completion_data)}\n\n"
                        break
                    elif chunk['type'] == 'error':
                        yield f"data: {json.dumps({'type': 'error', 'error': chunk['error'], 'details': chunk.get('details', '')})}\n\n"
                        break
            
            else:
                # For calls and FAQ, use synchronous routing then stream the final answer
                search_start = time.time()
                routed = rag_service.get_ai_response_with_routing(
                    question=resolved_question,
                    max_projects_to_process=5,
                    max_cordis_results=10
                )
                processing_phases['search_execution'] = time.time() - search_start
                
                answer_text = routed.get('answer') or ''
                # Ensure verification_url is present for calls
                if intent == "SEARCH_CALLS":
                    verification_url = routed.get('verification_url') or f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword={resolved_question.replace(' ', '%20')};sortQuery=sortStatus;orderBy=asc"
                    answer_text += f"\n\n🔗 Verify on Portal: {verification_url}"
                
                # Stream the response in chunks
                chunk_size = 50
                for i in range(0, len(answer_text), chunk_size):
                    chunk = answer_text[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                
                # Build proper logs object
                logs_data = {
                    'question': resolved_question,
                    'model_used': routed.get('model_used', 'gemini-2.5-flash-lite'),
                    'phases': phases,
                    'total_processing_time_ms': int((time.time() - start_time) * 1000),
                    'projects_retrieved': routed.get('projects_retrieved', 0),
                    'projects_processed': routed.get('projects_processed', 0),
                    'success': routed.get('success', True),
                    'average_relevance_score': routed.get('average_relevance_score', 0.0)
                }

                completion_data = {
                    'type': 'complete',
                    'ai_provider': 'google',
                    'ai_version': 'gemini-2.5-flash-lite',
                    'model_used': routed.get('model_used', 'gemini-2.5-flash-lite'),
                    'data_source': routed.get('data_source', 'CORDIS Database'),
                    'processing_time': time.time() - start_time,
                    'projects_found': routed.get('projects_found', 0),
                    'logs': logs_data,
                    'context_used': request.include_context,
                    'resolved_question': resolved_question,
                    'follow_up_suggestions': routed.get('follow_up_suggestions', []),
                    'projects_discussed': routed.get('projects_discussed', []),
                    'routing_decision': routed.get('routing_decision', intent),
                    'intent_confidence': routed.get('intent_confidence', intent_conf)
                }
                try:
                    print(json.dumps({
                        'telemetry': 'conversation_routing_stream',
                        'conversation_id': conversation_id,
                        'question': resolved_question,
                        'routing_decision': completion_data['routing_decision'],
                        'data_source': completion_data.get('data_source'),
                        'processing_phases': processing_phases
                    }))
                except Exception:
                    pass
                yield f"data: {json.dumps(completion_data)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Processing failed', 'details': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )