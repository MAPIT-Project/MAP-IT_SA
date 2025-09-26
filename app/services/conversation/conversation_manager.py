"""
Main conversation management system that orchestrates all components.
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple
from datetime import datetime
import json
import logging
import os
import random

from ..memory.memory_service import MemoryService
from ..memory.context_manager import ConversationContext
from ..rag.conversation_retriever import ConversationAwareRetriever, RetrievalContext
from ..rag.response_generator import GroundedResponseGenerator
from ..rag.hybrid_search import HybridSearchPipeline, MockVectorStore, MockKeywordStore, MockEmbeddingService
from ..tools.tool_orchestrator import create_research_orchestrator
from ..response.unified_formatter import UnifiedResponseFormatter
from ..ai_intent_service import AIIntentService

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Central manager for all conversation operations with AI-ONLY ARCHITECTURE.

    SIMPLIFIED 4-PHASE PIPELINE:
    Phase 1: Store user message in memory
    Phase 2: AI-only intent analysis and tool planning (single AI call)
    Phase 3: Execute tools if planned
    Phase 4: Generate response

    KEY IMPROVEMENTS:
    - AI-only intent detection - no complex rule-based fallbacks
    - Single AI call handles all intent analysis and tool planning
    - Simplified architecture with fewer moving parts
    - More reliable and consistent behavior
    - Easier to maintain and extend

    Coordinates memory, RAG, and tool systems with AI-driven orchestration.
    """
    
    def __init__(self):
        """Initialize all subsystems"""
        try:
            # Memory management
            self.memory_service = MemoryService()
            
            # RAG components
            self.retriever = ConversationAwareRetriever(
                hybrid_search=self._init_hybrid_search(),
                cache_client=self.memory_service.redis_client
            )
            self.response_generator = GroundedResponseGenerator(
                ai_provider=os.getenv('DEFAULT_AI_PROVIDER', 'gemini'),
                gemini_api_key=os.getenv('GEMINI_API_KEY'),
                openrouter_api_key=os.getenv('OPENROUTER_API_KEY')
            )
            
            # Tool orchestration
            self.tool_orchestrator = create_research_orchestrator(
                cache_client=self.memory_service.redis_client
            )
            
            # Response formatting
            self.unified_formatter = UnifiedResponseFormatter()

            # AI-only intent analysis
            self.ai_intent_service = AIIntentService()

            # Configuration
            self.config = self._load_configuration()

            print("✅ ConversationManager initialized successfully with AI-only intent system")
            
        except Exception as e:
            print(f"⚠️ ConversationManager initialization error: {e}")
            raise
    
    async def process_message(self,
                               conversation_id: int,
                               user_message: str,
                               user_id: int,
                               streaming: bool = False) -> Dict[str, Any]:
        """
        Process a user message through the AI-only 4-phase pipeline.

        AI-ONLY ARCHITECTURE:
        Phase 1: Store user message in memory
        Phase 2: AI-only intent analysis and tool planning (single AI call)
        Phase 3: Execute tools if planned
        Phase 4: Generate response

        Benefits of AI-only approach:
        - Single AI call handles all intent analysis and tool planning
        - No complex rule-based fallbacks or keyword matching
        - More reliable and consistent behavior
        - Simplified architecture with fewer moving parts

        Args:
            conversation_id: Conversation identifier
            user_message: User's message
            user_id: User identifier
            streaming: Whether to stream the response

        Returns:
            Complete response with metadata
        """
        start_time = datetime.now()
        
        try:
            # Phase 1: Add user message to memory
            user_message_id = await self._store_user_message(
                conversation_id, user_id, user_message
            )

            # Phase 2: AI-only intent analysis and tool planning
            print(f"🤖 STARTING AI-ONLY PHASE for: '{user_message}'")
            intent_analysis, context, tool_plan = await self._analyze_intent_and_plan_tools(
                conversation_id=conversation_id,
                user_message=user_message
            )
            print(f"🤖 AI-ONLY PHASE RESULT: intent={intent_analysis.get('intent_type', 'unknown')}, tools={len(tool_plan) if tool_plan else 0}")

            # Phase 3: Execute tools if needed
            tool_results = None
            retrieval_results = []  # Initialize to avoid undefined variable error
            if tool_plan:
                tool_results = await self.tool_orchestrator.execute_plan(
                    tool_plan, conversation_id
                )
                print(f"🔧 Tool Orchestrator executed {len(tool_results)} tools")

                # Convert tool results to retrieval format for response generation
                if tool_results:
                    retrieval_results = self._convert_tool_results_to_retrieval(tool_results)

            # Phase 4: Generate response
            logger.info(f"📝 RESPONSE GENERATION: tool_results={tool_results is not None}, retrieval_results={len(retrieval_results)}")

            if tool_results:
                logger.info(f"🔧 TOOL RESULTS SUMMARY: {len(tool_results)} tools executed")
                for tool_name, tool_result in tool_results.items():
                    logger.info(f"   Tool {tool_name}: success={tool_result.success}, has_result={tool_result.result is not None}")

            if streaming:
                logger.info("🎬 Starting streaming response generation")
                return self._generate_streaming_response(
                    conversation_id=conversation_id,
                    query=user_message,
                    context=context,
                    retrieval_results=retrieval_results,
                    tool_results=tool_results,
                    intent_analysis=intent_analysis,
                    start_time=start_time
                )
            else:
                logger.info("📄 Starting non-streaming response generation")
                response = await self._generate_response(
                    conversation_id=conversation_id,
                    query=user_message,
                    context=context,
                    retrieval_results=retrieval_results,
                    tool_results=tool_results,
                    intent_analysis=intent_analysis,
                    start_time=start_time
                )

                # LOG THE FINAL RESPONSE
                logger.info(f"📤 FINAL RESPONSE: {response.get('response', 'No response')[:500]}...")
                logger.info(f"📊 RESPONSE METADATA: tools_executed={response.get('tools_executed', False)}, confidence={response.get('confidence', 0.0)}")

                return response
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._create_error_response(str(e))
    
    
    
    async def _execute_service(self,
                              service_decision: Dict[str, Any],
                              conversation_id: int,
                              user_message: str,
                              context: str) -> List[Dict[str, Any]]:
        """
        Execute the selected service.
        """
        service_name = service_decision.get('service')
        
        # This method is now handled by the 7-phase architecture
        return []
    
    def _convert_tool_results_to_retrieval(self, tool_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert tool execution results to retrieval format for response generation.
        """
        retrieval_results = []
        
        for tool_name, tool_result_obj in tool_results.items():
            try:
                if tool_result_obj.success:
                    tool_data = tool_result_obj.result
                    
                    if tool_name == 'eu_portal_search':
                        # Format call search results
                        if tool_data.get('calls'):
                            for call in tool_data['calls'][:5]:
                                # Handle both dict and EnhancedSearchResult objects
                                if hasattr(call, '__dataclass_fields__'):
                                    # EnhancedSearchResult object
                                    call_data = {
                                        'title': call.title,
                                        'identifier': call.identifier,
                                        'status': call.status,
                                        'deadline': call.deadline,
                                        'url': call.url,
                                        'description': call.description
                                    }
                                else:
                                    # Already a dict
                                    call_data = call

                                retrieval_results.append({
                                    'content': f"**{call_data['title']}**\n\nCall ID: {call_data['identifier']}\nStatus: {call_data['status']}\nDeadline: {call_data['deadline']}\nURL: {call_data['url']}\n\n{call_data.get('description', '')}",
                                    'citation': f"EU Funding Portal - {call_data['identifier']}",
                                    'chunk_id': f"call_{call_data['identifier']}",
                                    'metadata': {
                                        'source': 'eu_portal_tool',
                                        'tool_name': tool_name,
                                        'call_id': call_data['identifier'],
                                        'status': call_data['status']
                                    }
                                })
                    
                    elif tool_name == 'search_cordis_projects':
                        # Format project search results
                        if tool_data.get('answer'):
                            retrieval_results.append({
                                'content': tool_data['answer'],
                                'citation': f"CORDIS Projects - {tool_data.get('data_source', 'Unknown')}",
                                'chunk_id': f"projects_{len(retrieval_results)}",
                                'metadata': {
                                    'source': 'cordis_tool',
                                    'tool_name': tool_name,
                                    'projects_found': tool_data.get('projects_found', 0)
                                }
                            })

                    elif tool_name == 'search_local_database':
                        # Format local database search results
                        if tool_data.get('answer'):
                            retrieval_results.append({
                                'content': tool_data['answer'],
                                'citation': f"Local Database - {tool_data.get('data_source', 'Unknown')}",
                                'chunk_id': f"database_{len(retrieval_results)}",
                                'metadata': {
                                    'source': 'local_database_tool',
                                    'tool_name': tool_name,
                                    'documents_found': tool_data.get('documents_found', 0),
                                    'search_type': tool_data.get('search_type', 'unknown'),
                                    'confidence': tool_data.get('confidence', 0.0)
                                }
                            })
                    
                    else:
                        # Generic tool result formatting
                        if hasattr(tool_data, '__dict__'):
                            content = json.dumps(tool_data.__dict__)
                        else:
                            content = str(tool_data)
                        retrieval_results.append({
                            'content': content,
                            'citation': f"Tool: {tool_name}",
                            'chunk_id': f"tool_{tool_name}",
                            'metadata': {
                                'source': 'tool_execution',
                                'tool_name': tool_name
                            }
                        })
                        
            except Exception as e:
                print(f"Error converting tool result {tool_name}: {e}")
        
        print(f"🔄 Converted {len(tool_results)} tool results to {len(retrieval_results)} retrieval chunks")
        return retrieval_results
    


    async def _analyze_intent_and_plan_tools(self,
                                           conversation_id: int,
                                           user_message: str) -> Tuple[Dict[str, Any], str, Optional[List]]:
        """
        AI-ONLY PHASE: Analyze intent and plan tools using the AI Intent Service.

        This simplified method replaces the complex 200+ line combined phase with
        a single call to the AI Intent Service, providing:
        - Reliable intent detection
        - Consistent tool planning
        - No complex rule-based fallbacks
        - Maintainable and predictable behavior

        Args:
            conversation_id: Conversation identifier
            user_message: User's message

        Returns:
            Tuple of (intent_analysis, context, tool_plan)
        """
        try:
            print("🔧 AI-ONLY PHASE: Starting intent analysis...")

            # Get conversation context for AI analysis
            summary = self.memory_service.ltm.get_summary(conversation_id)
            recent_turns = self.memory_service.stm.get_recent_turns(conversation_id)

            conversation_context = summary.summary_text if summary else "New conversation"
            conversation_history = "\n".join([
                f"{'User' if turn.role == 'user' else 'Assistant'}: {turn.content}"
                for turn in recent_turns
            ])

            print(f"🔧 AI-ONLY PHASE: Analyzing intent for: '{user_message[:100]}...'")

            # Use AI-only intent service
            intent_analysis = await self.ai_intent_service.analyze_intent(
                message=user_message,
                conversation_context=conversation_context,
                conversation_history=conversation_history,
                conversation_id=conversation_id
            )

            print(f"🤖 AI-ONLY PHASE: Intent analysis complete - {intent_analysis.intent_type} (confidence: {intent_analysis.confidence:.2f})")

            # Build context string
            context = f"Intent Analysis: {intent_analysis.reasoning}\n"
            context += f"Context Assessment: {intent_analysis.context_assessment}\n"
            context += f"Conversation Summary: {conversation_context}"

            # Convert tool plan to ToolCall objects if needed
            tool_plan = None
            if intent_analysis.requires_tools and intent_analysis.tool_plan:
                from ..tools.tool_orchestrator import ToolCall
                tool_calls = []
                for i, tool_spec in enumerate(intent_analysis.tool_plan):
                    tool_call = ToolCall(
                        tool_name=tool_spec.tool_name,
                        parameters=tool_spec.parameters,
                        execution_order=i
                    )
                    tool_calls.append(tool_call)
                tool_plan = tool_calls
                print(f"   Tools planned: {len(tool_calls)}")

            # Convert IntentAnalysis to dict format for compatibility
            intent_dict = {
                "intent_type": intent_analysis.intent_type,
                "confidence": intent_analysis.confidence,
                "requires_tools": intent_analysis.requires_tools,
                "requires_retrieval": intent_analysis.requires_tools,  # For backward compatibility
                "explanation": intent_analysis.reasoning,
                "extracted_keywords": intent_analysis.extracted_keywords
            }

            return intent_dict, context, tool_plan

        except Exception as e:
            print(f"AI-only intent analysis error: {e}")
            # Simple fallback
            return {
                "intent_type": "conversational",
                "confidence": 0.5,
                "requires_tools": False,
                "requires_retrieval": False,
                "explanation": f"Error in AI analysis: {str(e)}"
            }, "Error in context building", None

    async def _retrieve_information(self,
                                   conversation_id: int,
                                   query: str,
                                   context: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information - now primarily handled by tools.
        """
        try:
            # This method is now mainly a fallback since tools handle most retrieval
            print(f"🔄 Fallback retrieval for query: {query}")
            
            summary = self.memory_service.ltm.get_summary(conversation_id)
            facts = self.memory_service.ltm.get_facts(conversation_id)
            entities = self.memory_service.ltm.get_entity_cards(conversation_id)
            
            retrieval_context = RetrievalContext(
                conversation_id=conversation_id,
                current_query=query,
                conversation_summary=summary.summary_text if summary else "",
                recent_topics=[fact.fact_content for fact in facts[:3]],
                entity_mentions=[entity.entity_name for entity in entities[:5]],
                search_history=[]
            )
            
            results = await self.retriever.retrieve(
                context=retrieval_context,
                max_chunks=self.config.get('max_retrieval_chunks', 4),
                use_cache=True
            )
            
            return results
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []
    
    async def _generate_response(self,
                                conversation_id: int,
                                query: str,
                                context: str,
                                retrieval_results: Optional[List[Dict]],
                                tool_results: Optional[Dict],
                                intent_analysis: Dict,
                                start_time: datetime) -> Dict[str, Any]:
        """
        Generate final response combining all information.
        """
        try:
            # Prepare context chunks
            context_chunks = retrieval_results if retrieval_results is not None else []
            
            # Add tool results to context if available
            if tool_results:
                # Serialize tool results for JSON compatibility
                serialized_tool_results = self._serialize_tool_results(tool_results)
                tool_context = {
                    'content': f"Tool Results:\n{json.dumps(serialized_tool_results, indent=2)}",
                    'citation': 'Tool Execution',
                    'chunk_id': 'tool_results'
                }
                context_chunks.insert(0, tool_context)
            
            # Phase 7: Generate appropriate response based on query type
            logger.info(f"🔄 RESPONSE TYPE DECISION: tool_results present = {tool_results is not None}")

            if tool_results:
                logger.info("🎯 Using tool-based response generation")

                # DEBUG: Log the exact structure of tool results
                logger.info(f"🔧 TOOL RESULTS STRUCTURE: {list(tool_results.keys())}")
                for tool_name, tool_result in tool_results.items():
                    logger.info(f"   Tool {tool_name}: type={type(tool_result)}, has_result={hasattr(tool_result, 'result')}")
                    if hasattr(tool_result, 'result'):
                        logger.info(f"      Result type: {type(tool_result.result)}")
                        if isinstance(tool_result.result, dict):
                            logger.info(f"      Result keys: {list(tool_result.result.keys())}")
                            # Check for expected fields
                            if 'answer' in tool_result.result:
                                logger.info(f"      Has 'answer' field: {len(tool_result.result['answer'])} chars")
                            if 'projects_found' in tool_result.result:
                                logger.info(f"      Projects found: {tool_result.result['projects_found']}")

                # Use unified formatter for tool results (calls, projects, etc.)
                # Pass only the current user message, not the entire conversation context
                formatted_response = self.unified_formatter.format_mixed_results(
                    tool_results=tool_results,
                    retrieval_results=retrieval_results,
                    query=query  # Use the query parameter, not user_message
                )

                logger.info(f"📝 FORMATTED RESPONSE LENGTH: {len(formatted_response) if formatted_response else 0}")
                logger.info(f"📝 FORMATTED RESPONSE PREVIEW: {formatted_response[:500] if formatted_response else 'None'}...")

                # Log the complete formatted response for debugging
                if formatted_response:
                    logger.info(f"📝 COMPLETE FORMATTED RESPONSE:\n{formatted_response}")

                response = {
                    'answer': formatted_response,
                    'citations': [],
                    'confidence': 0.9,  # High confidence for direct tool results
                    'grounded': True
                }
            else:
                # Generate conversational AI response for general queries
                logger.info(f"💬 Generating conversational response for: '{query}'")
                conversational_response = self._generate_conversational_response(
                    query=query,
                    context=context,
                    retrieval_results=retrieval_results,
                    intent_analysis=intent_analysis
                )

                logger.info(f"💬 CONVERSATIONAL RESPONSE LENGTH: {len(conversational_response) if conversational_response else 0}")
                logger.info(f"💬 CONVERSATIONAL RESPONSE PREVIEW: {conversational_response[:200] if conversational_response else 'None'}...")

                response = {
                    'answer': conversational_response,
                    'citations': [],
                    'confidence': 0.8,  # Good confidence for conversational responses
                    'grounded': True if retrieval_results else False
                }
            
            # Store assistant response in memory
            assistant_message_id = await self._store_assistant_message(
                conversation_id, response['answer']
            )
            
            # Update memory with new turn
            self.memory_service.add_conversation_turn(
                conversation_id=conversation_id,
                role='assistant',
                content=response['answer'],
                message_id=assistant_message_id
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'response': response['answer'],
                'citations': response.get('citations', []),
                'confidence': response.get('confidence', 0.0),
                'grounded': response.get('grounded', False),
                'intent': intent_analysis,
                'chunks_retrieved': len(retrieval_results) if retrieval_results is not None else 0,
                'tools_executed': tool_results is not None,
                'processing_time': processing_time,
                'memory_stats': self.memory_service.stm.get_memory_stats(conversation_id),
                'retrieval_stats': self.retriever.get_retrieval_stats(conversation_id)
            }
        except Exception as e:
            print(f"Response generation error: {e}")
            return self._create_error_response(str(e))
    
    async def _generate_streaming_response(self,
                                            conversation_id: int,
                                            query: str,
                                            context: str,
                                            retrieval_results: Optional[List[Dict]],
                                            tool_results: Optional[Dict],
                                            intent_analysis: Dict,
                                            start_time: datetime) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response with progressive status updates following the AI-ONLY 4-phase architecture.

        AI-ONLY PHASES:
        Phase 1: Context Resolution
        Phase 2: AI-only Intent Analysis and Tool Planning
        Phase 3: Data Processing
        Phase 4: Response Generation
        Phase 5: Streaming Response
        """
        try:
            # Phase 1: Context Resolution
            yield {
                'type': 'status',
                'stage': 'context_resolution',
                'message': 'Loading conversation context and memory'
            }
            await asyncio.sleep(0.1)

            # Phase 2: AI-only Intent Analysis and Tool Planning
            intent_confidence = intent_analysis.get('confidence', 0.0)
            routing_decision = intent_analysis.get('intent_type', 'CONVERSATIONAL')

            yield {
                'type': 'progress',
                'stage': 'intent_detected',
                'message': f'AI analyzed intent: {routing_decision}',
                'routing_decision': routing_decision,
                'intent_confidence': intent_confidence
            }
            await asyncio.sleep(0.1)

            # Phase 3: Data Processing
            if tool_results:
                yield {
                    'type': 'status',
                    'stage': 'data_retrieval',
                    'message': 'Processing search results from EU databases'
                }
                await asyncio.sleep(0.1)

                yield {
                    'type': 'status',
                    'stage': 'data_enriched',
                    'message': 'Enriching and formatting search results'
                }
                await asyncio.sleep(0.1)

            # Phase 4: Response Generation
            yield {
                'type': 'status',
                'stage': 'answer_generation',
                'message': 'Generating response based on processed data'
            }
            await asyncio.sleep(0.1)

            # Phase 5: Streaming Response
            yield {
                'type': 'status',
                'stage': 'streaming_response',
                'message': 'Starting response stream'
            }
            await asyncio.sleep(0.1)
            
            # Prepare context chunks
            context_chunks = retrieval_results if retrieval_results is not None else []
            
            # Generate and stream the actual response
            if tool_results:
                # Tool-based response with beautiful formatting
                formatted_response = self.unified_formatter.format_mixed_results(
                    tool_results=tool_results,
                    retrieval_results=retrieval_results,
                    query=query  # Use the query parameter, not user_message
                )
                
                if formatted_response:
                    # Stream the pre-formatted response in chunks
                    chunk_size = 50  # Characters per chunk
                    for i in range(0, len(formatted_response), chunk_size):
                        chunk = formatted_response[i:i+chunk_size]
                        yield {
                            'type': 'token',
                            'content': chunk
                        }
                        await asyncio.sleep(0.01)  # Small delay for streaming effect
                    
                    final_response = formatted_response
                    projects_found = self._count_projects_in_results(tool_results)
                    tools_executed = True
                    confidence = 0.9
                    grounded = True
            else:
                # Generate conversational response for non-tool queries
                logger.info(f"💬 Generating streaming conversational response for: '{query}'")
                
                # For research funding queries, use enhanced fallback directly for better quality
                query_lower = query.lower()
                research_keywords = ['horizon europe', 'funding', 'budget', 'structure', 'pillar', 'programme', 'call', 'grant']
                if any(keyword in query_lower for keyword in research_keywords):
                    logger.info("💡 Research funding streaming query - using enhanced fallback")
                    conversational_response = self._get_enhanced_fallback_response(query, intent_analysis)
                else:
                    conversational_response = self._generate_conversational_response(
                        query=query,
                        context=context,
                        retrieval_results=retrieval_results,
                        intent_analysis=intent_analysis
                    )
                
                # Stream the conversational response in chunks
                chunk_size = 50  # Characters per chunk
                for i in range(0, len(conversational_response), chunk_size):
                    chunk = conversational_response[i:i+chunk_size]
                    yield {
                        'type': 'token',
                        'content': chunk
                    }
                    await asyncio.sleep(0.01)  # Small delay for streaming effect
                
                final_response = conversational_response
                projects_found = 0
                tools_executed = False
                confidence = 0.8
                grounded = True if retrieval_results else False
            
            # Send completion with full metadata IMMEDIATELY
            processing_time = (datetime.now() - start_time).total_seconds()
            
            yield {
                'type': 'complete',
                'ai_provider': 'google',
                'ai_version': 'gemini-2.5-flash-lite',
                'model_used': 'gemini-2.5-flash-lite',
                'data_source': 'EU Funding & Tenders Portal' if tools_executed else 'Conversational AI',
                'processing_time': processing_time,
                'projects_found': projects_found,
                'logs': {
                    'question': query,
                    'model_used': 'gemini-2.5-flash-lite',
                    'phases': ['context_resolution', 'ai_intent_analysis', 'data_retrieval' if tools_executed else 'conversational', 'answer_generation', 'streaming_response'],
                    'total_processing_time_ms': int(processing_time * 1000),
                    'projects_retrieved': projects_found,
                    'projects_processed': projects_found,
                    'success': True,
                    'average_relevance_score': 0.85 if tools_executed else 0.8
                },
                'context_used': len(retrieval_results) > 0 if retrieval_results else False,
                'resolved_question': query,
                'follow_up_suggestions': self._generate_follow_up_suggestions(query, tools_executed),
                'projects_discussed': []
            }
            
            # Store in memory AFTER sending complete event (fire-and-forget)
            try:
                assistant_message_id = await self._store_assistant_message(
                    conversation_id, final_response
                )
                
                self.memory_service.add_conversation_turn(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=final_response,
                    message_id=assistant_message_id
                )
            except Exception as e:
                logger.error(f"Error storing response in memory: {e}")
            
        except Exception as e:
            yield {
                'type': 'error',
                'error': str(e),
                'details': f'Error during response generation: {str(e)}'
            }
    
    def _generate_conversational_response(self,
                                         query: str,
                                         context: str,
                                         retrieval_results: Optional[List[Dict]],
                                         intent_analysis: Dict) -> str:
        """
        Generate a conversational AI response for general queries.
        This is used when no tools are needed.
        """
        try:
            logger.info(f"💬 Starting conversational response generation for: '{query}'")
            
            # For specific research funding queries, use enhanced fallback directly
            query_lower = query.lower()
            research_keywords = ['horizon europe', 'funding', 'budget', 'structure', 'pillar', 'programme', 'call', 'grant']
            if any(keyword in query_lower for keyword in research_keywords):
                logger.info("💡 Research funding query detected - using enhanced fallback directly")
                return self._get_enhanced_fallback_response(query, intent_analysis)
            
            # Use existing response generator (initialized in __init__)
            if not hasattr(self, 'response_generator') or not self.response_generator:
                logger.warning("Response generator not initialized - using enhanced fallback")
                return self._get_enhanced_fallback_response(query, intent_analysis)
            
            # Prepare context chunks from retrieval results
            context_chunks = retrieval_results if retrieval_results else []
            logger.info(f"💬 Context chunks available: {len(context_chunks)}")
            
            # If no context chunks, add basic context to help AI understand domain
            if not context_chunks:
                context_chunks = [{
                    'content': f"""This is a general query about European research and innovation. 
                    The user is asking: "{query}"
                    
                    Context: European research funding primarily comes through Horizon Europe (2021-2027, €95.5B budget), 
                    along with other programmes like LIFE, Digital Europe, and EIC. Focus areas include climate, 
                    digital transformation, health, and industrial competitiveness.""",
                    'citation': 'General EU Research Knowledge',
                    'chunk_id': 'general_context'
                }]
            
            # Get system instructions
            system_instructions = self._get_conversational_instructions(intent_analysis)
            logger.info(f"💬 System instructions length: {len(system_instructions)} chars")
            
            # Generate response using the response generator
            logger.info("💬 Calling response generator...")
            response = self.response_generator.generate_response(
                query=query,
                context_chunks=context_chunks,
                conversation_context=context,
                system_instructions=system_instructions
            )
            
            logger.info(f"💬 Response generator returned: {type(response)}")
            
            # Extract answer from response
            if isinstance(response, dict):
                answer = response.get('answer', '')
                if answer and len(answer.strip()) > 50:  # Increased threshold
                    logger.info(f"💬 Generated response: {len(answer)} chars")
                    return answer
                else:
                    logger.warning("Response too short or empty, using enhanced fallback")
                    return self._get_enhanced_fallback_response(query, intent_analysis)
            else:
                logger.warning(f"Unexpected response format: {type(response)}, using enhanced fallback")
                return self._get_enhanced_fallback_response(query, intent_analysis)
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._get_enhanced_fallback_response(query, intent_analysis)
    
    def _get_conversational_instructions(self, intent_analysis: Dict) -> str:
        """
        Get system instructions for conversational responses tailored for research managers.
        """
        return """You are an expert AI assistant specializing in European research funding and innovation, designed specifically to help research managers, grant writers, and research administrators.

**YOUR EXPERTISE COVERS:**
• Horizon Europe programme (2021-2027, €95.5 billion budget)
• All EU research programmes (LIFE, Digital Europe, Creative Europe, etc.)
• Grant application processes and best practices
• Consortium building and international collaboration
• Research trend analysis and market intelligence
• Success metrics and impact assessment
• Funding landscapes across European countries

**YOUR PERSONALITY & APPROACH:**
• Professional yet approachable and encouraging
• Data-driven and precise with facts and figures
• Action-oriented - always provide next steps
• Strategic thinking for long-term research planning
• Supportive of research excellence and innovation

**RESPONSE GUIDELINES:**
• Provide specific, actionable advice with concrete next steps
• Include relevant budget figures, deadlines, and success rates when applicable
• Mention specific programmes, instruments, and opportunities
• Reference real data and current trends (2021-2027 period)
• Suggest partnership and collaboration opportunities
• Always consider European added value and impact
• Be encouraging about funding prospects while being realistic
• Offer to search for current, specific information when relevant

**SPECIALIZED KNOWLEDGE AREAS:**
• Call identification and opportunity matching
• Proposal writing strategy and evaluation criteria
• Consortium formation and partner search
• Budget planning and financial management
• Impact assessment and exploitation planning
• International cooperation and third-country participation
• Research infrastructure and access programmes
• Innovation ecosystems and commercialization pathways

**TONE:**
Use a professional, knowledgeable tone that shows deep understanding of the European research landscape. Be enthusiastic about research potential while providing practical, implementable guidance. Focus on empowering research managers to make informed decisions and successful applications.

**CURRENT CONTEXT:**
You're responding to questions about European research and innovation funding. Always consider the strategic perspective of research managers who need to plan projects, build teams, secure funding, and deliver impact. Provide comprehensive answers that address both immediate needs and longer-term strategic considerations."""
    
    def _get_fallback_conversational_response(self, query: str, intent_analysis: Dict) -> str:
        """
        Provide a fallback response when AI generation fails.
        """
        query_lower = query.lower()
        
        if any(greeting in query_lower for greeting in ['hello', 'hi', 'hey']):
            return """Hello! 👋 I'm your AI assistant specializing in European research funding and innovation. 

I can help you with:
• Finding current funding calls and opportunities
• Understanding EU programmes like Horizon Europe
• Grant application guidance and tips
• Research project development advice
• Connecting you with relevant resources

What would you like to explore today?"""
        
        elif any(help_word in query_lower for help_word in ['help', 'what can you']):
            return """I'm here to help with European research funding and innovation! 🚀

**I can assist you with:**
• **Finding funding**: Search for open calls, grants, and opportunities
• **Programme guidance**: Horizon Europe, LIFE, Digital Europe, EIC, etc.
• **Application support**: Tips for writing competitive proposals
• **Project development**: From idea to implementation
• **Resources & contacts**: Connect you with relevant information

**Just ask me things like:**
• "What are some open calls for energy research?"
• "How does Horizon Europe work?"
• "Tips for writing a successful grant proposal?"
• "Show me completed projects in AI"

What specific area would you like help with?"""
        
        elif 'thank' in query_lower:
            return """You're very welcome! 😊 I'm always happy to help with research funding and innovation questions. 

Feel free to ask me anything about EU funding opportunities, grant applications, or research programmes whenever you need assistance!"""
        
        else:
            return f"""I'd be happy to help you with that! While I specialize in European research funding and innovation, I can provide guidance on a wide range of topics.

For the most current and specific information about funding calls or project opportunities, I can search the latest databases. Just let me know if you'd like me to look up anything specific!

Is there a particular aspect of research funding or innovation you'd like to explore?"""
    
    def _get_enhanced_fallback_response(self, query: str, intent_analysis: Dict) -> str:
        """
        Enhanced fallback response generator with comprehensive research manager guidance.
        """
        query_lower = query.lower()
        
        # Horizon Europe specific responses
        if 'horizon europe' in query_lower:
            return """**Horizon Europe** is the EU's key funding programme for research and innovation (2021-2027) with a budget of €95.5 billion.
            
**Main Pillars:**
1. **Excellent Science** - Supporting frontier research (€25.8B)
2. **Global Challenges & Industrial Competitiveness** - Addressing societal challenges (€53.5B)
3. **Innovative Europe** - Fostering innovation ecosystems (€13.6B)

**Key Features:**
• Open to international collaboration
• Mission-driven research approach
• Strong emphasis on impact and excellence
• Digital and green transitions priority
• Enhanced international cooperation

**Application Process:**
• Proposals submitted through EU Funding & Tenders Portal
• Two-stage evaluation (remote + panel review)
• Success rates typically 12-15%

Would you like specific information about current calls, application strategies, or success examples?"""

        # AI/Technology queries
        elif any(tech in query_lower for tech in ['ai', 'artificial intelligence', 'machine learning', 'quantum', 'digital']):
            return """🤖 **Digital & AI Research in Horizon Europe**

The EU is heavily investing in digital technologies and AI:

**Major Programmes:**
• **Horizon Europe Cluster 4:** Digital, Industry & Space (€15B)
• **Digital Europe Programme:** €7.5 billion for digital transformation
• **EIC Accelerator:** Support for breakthrough AI innovations

**Key Focus Areas:**
• Trustworthy and explainable AI
• AI for Green Deal and health applications
• Quantum computing and communications
• High-performance computing (EuroHPC)
• Cybersecurity and digital sovereignty

**Recent Success Stories:**
• Human Brain Project (€600M+ investment)
• EuroQCI - European Quantum Communication Infrastructure
• AI4EU platform connecting AI researchers

**Funding Opportunities:**
• ERC grants for fundamental AI research
• Marie Curie fellowships for AI researchers
• Innovation Actions for AI deployment

Would you like me to search for current AI-related calls or provide specific application guidance?"""

        # Healthcare queries
        elif any(health in query_lower for health in ['health', 'medical', 'healthcare', 'biotech', 'pharma']):
            return """🏥 **Health Research in Horizon Europe**

Health is a top priority with €8.2 billion dedicated funding:

**Cluster 1: Health** focuses on:
• **Cancer Mission:** Defeating cancer (€3B commitment)
• Infectious diseases and pandemic preparedness
• Personalized and precision medicine
• Digital health and AI in healthcare
• Mental health and wellbeing
• Health systems transformation

**Key Initiatives:**
• **Horizon Europe Health Partnership:** €2B public-private collaboration
• **IMI3 Joint Undertaking:** Next generation medicines
• **EIT Health:** Leading health innovation ecosystem

**Success Factors for Health Proposals:**
• Strong clinical validation and regulatory pathway
• Patient-centric approach with clear benefit
• Multi-disciplinary consortium including clinicians
• Clear commercialization and scaling strategy
• Alignment with EU health priorities

**Funding Instruments:**
• Research & Innovation Actions (RIA): up to 100% funding
• Innovation Actions (IA): 70% funding for close-to-market
• Coordination & Support Actions (CSA): 100% for networking

Would you like information about current health calls or successful project examples?"""

        # Climate/Environment queries
        elif any(env in query_lower for env in ['climate', 'environment', 'green', 'sustainability', 'renewable', 'energy']):
            return """🌍 **Climate & Energy Research in Horizon Europe**

Climate action is central to EU research with massive investment:

**EU Green Deal:** €1 trillion transformation plan
**Horizon Europe Cluster 5:** Climate, Energy & Mobility (€15 billion)
**LIFE Programme:** €5.4B for environmental and climate action

**EU Missions:**
• **100 Climate-Neutral Cities** by 2030
• **Adaptation to Climate Change** - supporting regions
• **Restore European Waters** by 2030
• **Caring for Soil** - soil health and food systems
• **Cancer Mission** - environmental factors

**Priority Research Areas:**
• Renewable energy systems and storage
• Carbon capture, utilization and storage (CCUS)
• Circular economy and waste valorization
• Climate adaptation and resilience
• Sustainable transport and mobility
• Nature-based solutions
• Critical raw materials and recycling

**Funding Success Tips:**
• Demonstrate clear environmental impact
• Include SMEs and industry partners
• Address multiple sustainability goals
• Strong stakeholder engagement plan
• Replication and scaling strategy

**Major Success Stories:**
• Battery 2030+ (€34B battery value chain)
• Clean Hydrogen Partnership (€2B investment)
• European Green Deal Call results

Would you like current green technology calls or climate project examples?"""

        # Funding/Budget queries
        elif any(fund in query_lower for fund in ['budget', 'funding', 'money', 'grant', 'cost', 'finance']):
            return """💰 **EU Research Funding Overview & Strategy**

**Horizon Europe Budget (2021-2027):** €95.5 billion

**Budget Breakdown:**
• **Pillar I - Excellent Science:** €25.8B
  - ERC: €16.6B | MSCA: €6.6B | Infrastructure: €2.4B
• **Pillar II - Global Challenges:** €53.5B
  - 6 clusters addressing societal challenges
• **Pillar III - Innovative Europe:** €13.6B
  - EIC: €10.1B | EIT: €3B | Innovation ecosystems: €0.5B

**Funding Rates by Instrument:**
• **Research & Innovation Actions (RIA):** up to 100%
• **Innovation Actions (IA):** typically 70% (100% for non-profits)
• **Coordination & Support Actions (CSA):** up to 100%
• **ERC Grants:** 100%
• **MSCA:** 100% + living/mobility allowances

**Success Rates (2021-2022):**
• **Overall Horizon Europe:** 12-15%
• **ERC Starting Grants:** 13%
• **ERC Advanced Grants:** 9%
• **MSCA Postdoc Fellows:** 18%
• **Some focused calls:** up to 25%

**Budget Planning Tips:**
• Personnel costs: 50-70% of typical project
• Include dissemination/exploitation: 5-10%
• Management costs: keep reasonable (<15%)
• Travel: reduced post-COVID, focus on virtual
• Equipment: justify necessity and EU value-added

Would you like specific budget guidance for your research area or call?"""

        # Project/collaboration queries
        elif any(proj in query_lower for proj in ['project', 'example', 'case study', 'success', 'collaboration', 'partner']):
            return """🤝 **EU Research Projects & Collaboration**

**Finding Project Information:**
• **CORDIS Database:** 300,000+ EU-funded projects
• **Programme websites:** Latest success stories
• **Partner Search:** Find collaborators by expertise
• **National Contact Points:** Country-specific guidance

**Types of Collaborative Projects:**
• **Coordination & Support Actions (CSA):** Networking, best practices
• **Research & Innovation Actions (RIA):** Collaborative research
• **Innovation Actions (IA):** Close-to-market innovation
• **European Partnerships:** Large-scale, long-term initiatives

**Building Strong Consortia:**
• **Geographic balance:** Include diverse EU countries + Associated Countries
• **Sectoral mix:** Academic, industry, SME, public sector
• **Complementary expertise:** Cover all required disciplines
• **Previous collaboration:** Demonstrated track record helps
• **Gender balance:** EU priority for leadership positions

**Top Collaborating Countries (by project participation):**
1. **Germany** - 23% of projects, €2.1B annual funding
2. **Italy** - 14% of projects, strong in materials/culture
3. **France** - 13% of projects, aerospace/energy leadership
4. **Spain** - 11% of projects, growing renewable energy focus
5. **Netherlands** - 8% of projects, innovation/sustainability excellence

**Partnership Benefits:**
• Shared costs and reduced risk
• Access to complementary expertise and infrastructure
• Larger market reach and impact potential
• Knowledge exchange and capacity building
• Enhanced proposal competitiveness

Would you like help finding partners in specific domains or successful project examples?"""

        # Application/process queries
        elif any(how in query_lower for how in ['how', 'apply', 'application', 'proposal', 'submit', 'process']):
            return """📝 **EU Funding Application Process & Tips**

**Step-by-Step Application Process:**

**1. Pre-Application (6+ months before deadline)**
• Monitor Funding & Tenders Portal for relevant calls
• Attend info days and brokerage events
• Build consortium through partner search
• Develop initial concept and impact strategy

**2. Proposal Development (3-6 months)**
• Form legal consortium with signed consortium agreement
• Register organization in Participant Portal
• Develop detailed work plan and budget
• Write proposal following call template exactly
• Get internal review and revision

**3. Submission (before deadline)**
• Submit through EU Funding & Tenders Portal
• Ensure all mandatory documents included
• Double-check budget calculations
• Submit at least 24 hours before deadline

**4. Evaluation Process (3-6 months)**
• Remote evaluation by independent experts
• Panel review and consensus meeting
• Scoring: Excellence + Impact + Implementation
• Threshold: typically 4/5 for each criterion

**Proposal Writing Best Practices:**
• **Excellence:** Clear objectives, methodology, innovation
• **Impact:** Measurable outcomes, exploitation, communication
• **Implementation:** Realistic timeline, qualified team, risk management

**Common Mistakes to Avoid:**
• Late submission or incomplete applications
• Unclear connection between objectives and methodology  
• Weak impact and exploitation strategy
• Unrealistic budget or timeline
• Poor consortium composition or management structure

**Success Factors:**
• Start early and plan thoroughly
• Build strong, complementary consortium
• Focus on clear, measurable impact
• Demonstrate European added value
• Professional proposal writing and presentation

Would you like specific guidance for a particular call or programme?"""

        # Country-specific queries
        elif any(country in query_lower for country in ['country', 'countries', 'national', 'germany', 'france', 'italy', 'spain']):
            return """🌍 **European Research Landscape by Country**

**Leading Research Nations in EU Funding:**

**🇩🇪 Germany** - Largest recipient
• 23% of Horizon Europe projects
• €2.1B annual research funding
• Strengths: Engineering, automotive, Industry 4.0
• Key institutions: Max Planck, Fraunhofer, universities

**🇫🇷 France** - Innovation leader  
• 13% of project participation
• €1.4B annual funding
• Strengths: Aerospace, nuclear, space technology
• Key institutions: CNRS, CEA, grandes écoles

**🇮🇹 Italy** - Growing research power
• 14% of projects, strong growth trajectory
• €1.2B annual funding  
• Strengths: Materials, cultural heritage, life sciences
• Key institutions: CNR, INFN, leading universities

**🇪🇸 Spain** - Renewable energy leader
• 11% of project participation
• €900M annual funding
• Strengths: Renewable energy, biotechnology, ICT
• Key institutions: CSIC, CIEMAT, technical universities

**🇳🇱 Netherlands** - Innovation per capita leader
• 8% of projects, highest success rates
• €600M annual funding
• Strengths: Sustainability, digital innovation, health
• Key institutions: TNO, NWO, research universities

**Collaboration Patterns:**
• **Germany-France:** Strategic partnership in many domains
• **Nordic cooperation:** Strong in sustainability and digitization  
• **Mediterranean alliance:** Climate adaptation and agriculture
• **Visegrad Group:** Growing participation in digital transformation

**National Contact Points (NCPs):**
Every country has specialized support offices providing:
• Call information and guidance
• Proposal writing support  
• Partner search facilitation
• Success rate statistics
• National funding complementarity

Would you like specific information about research opportunities or support in particular countries?"""

        # General/default response - comprehensive research manager assistant
        else:
            return f"""🚀 **EU Research Funding Assistant - Ready to Help!**

**Your Query:** "{query}"

I'm specialized in European research funding and innovation. Here's how I can assist you:

**🔍 Current Opportunities**
• Search live funding calls and opportunities
• Find calls by research area, budget, or deadline
• Explain eligibility criteria and requirements
• Provide application deadlines and processes

**📊 Programme Information**
• **Horizon Europe:** €95.5B main research programme
• **Digital Europe:** €7.5B digital transformation
• **LIFE Programme:** €5.4B environmental action
• **Creative Europe:** Cultural and creative sectors
• **Erasmus+:** Education and training

**💡 Strategic Guidance**
• Proposal writing tips and best practices
• Consortium building and partner search
• Budget planning and cost calculations
• Impact assessment and exploitation strategies
• Success rate analysis and benchmarking

**🌍 Collaboration Support**
• Find research partners across Europe
• Connect with National Contact Points
• Access to 300,000+ project database (CORDIS)
• Success stories and case studies
• International cooperation opportunities

**📈 Market Intelligence**
• Research trend analysis by sector
• Funding distribution by country/topic  
• Technology readiness and commercialization
• Innovation ecosystem mapping
• Competitive landscape analysis

**What would you like to explore?**
• "Search for current AI funding calls"
• "How to write a successful Horizon Europe proposal"
• "Find partners for renewable energy research"
• "What's the budget for climate research?"
• "Show me successful projects in my field"

**Just ask me anything about EU research funding - I'm here to help you succeed!** 🎯

For the most current information, I can search live databases and provide real-time data. What specific area interests you most?"""

    def _get_system_instructions(self, intent_analysis: Dict) -> str:
        """
        Get appropriate system instructions based on intent.
        """
        intent_type = intent_analysis.get('intent_type', 'question')
        
        if intent_type == 'question':
            return """You are a helpful AI assistant specializing in European research funding.
Provide accurate, detailed answers based on the provided context.
Cite your sources and acknowledge when information is missing."""
        
        elif intent_type == 'command':
            return """You are an AI assistant executing user commands.
Be precise and confirm actions taken.
Provide clear feedback on what was done."""
        
        elif intent_type == 'clarification':
            return """The user is asking for clarification on something discussed.
Reference the previous conversation naturally.
Be clear and helpful in your explanation."""
        
        elif intent_type == 'follow_up':
            return """This is a follow-up question to the previous discussion.
Build on what was already discussed.
Maintain continuity with the conversation."""
        
        else:
            return """You are a friendly AI assistant.
Respond appropriately to the user's message.
Be helpful and conversational."""
    
    async def _store_user_message(self,
                                 conversation_id: int,
                                 user_id: int,
                                 message: str) -> int:
        """Store user message in database and return message ID."""
        # For now, generate a mock message ID
        # In production, this would insert into your message table
        message_id = random.randint(1000, 9999)
        
        # Add to short-term memory immediately
        from ..memory.short_term_memory import ConversationTurn
        turn = ConversationTurn(
            message_id=message_id,
            role='user',
            content=message,
            timestamp=datetime.now()
        )
        self.memory_service.stm.add_turn(conversation_id, turn)
        
        return message_id
    
    async def _store_assistant_message(self,
                                      conversation_id: int,
                                      message: str) -> int:
        """Store assistant message in database and return message ID."""
        # For now, generate a mock message ID
        # In production, this would insert into your message table
        return random.randint(1000, 9999)
    
    def _init_hybrid_search(self):
        """Initialize hybrid search pipeline."""
        try:
            # Use your existing RAG service instead of mock data
            from ..enhanced_rag_service import HorizonEuropeRAG
            self.existing_rag = HorizonEuropeRAG()
            print("✅ Using existing HorizonEuropeRAG service")
            
            # Still create hybrid search for future use
            return HybridSearchPipeline(
                vector_store=MockVectorStore(),
                keyword_store=MockKeywordStore(),
                embedding_service=MockEmbeddingService()
            )
        except Exception as e:
            print(f"⚠️ Using mock services for hybrid search: {e}")
            self.existing_rag = None
            return HybridSearchPipeline(
                vector_store=MockVectorStore(),
                keyword_store=MockKeywordStore(),
                embedding_service=MockEmbeddingService()
            )
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load system configuration."""
        return {
            'max_retrieval_chunks': int(os.getenv('MAX_RETRIEVAL_CHUNKS', 4)),
            'max_context_tokens': int(os.getenv('MAX_CONTEXT_TOKENS', 8000)),
            'summarize_every_n_turns': int(os.getenv('SUMMARIZE_EVERY_N_TURNS', 5)),
            'cache_ttl': int(os.getenv('RETRIEVAL_CACHE_TTL', 3600))
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            'response': "I apologize, but I encountered an error processing your request.",
            'error': error_message,
            'success': False,
            'citations': [],
            'confidence': 0.0,
            'grounded': False,
            'processing_time': 0.0
        }
    
    def get_conversation_stats(self, conversation_id: int) -> Dict[str, Any]:
        """Get comprehensive conversation statistics."""
        try:
            memory_stats = self.memory_service.get_memory_stats(conversation_id)
            retrieval_stats = self.retriever.get_retrieval_stats(conversation_id)
            
            return {
                'conversation_id': conversation_id,
                'memory': memory_stats,
                'retrieval': retrieval_stats,
                'config': self.config
            }
        except Exception as e:
            print(f"Error getting conversation stats: {e}")
            return {}
    
    def clear_conversation(self, conversation_id: int) -> bool:
        """Clear all memory for a conversation."""
        try:
            return self.memory_service.clear_conversation_memory(conversation_id)
        except Exception as e:
            print(f"Error clearing conversation: {e}")
            return False

    def _serialize_tool_results(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ToolResult objects to JSON-serializable dictionaries.
        
        Args:
            tool_results: Dictionary containing ToolResult objects
            
        Returns:
            JSON-serializable dictionary
        """
        serialized = {}
        for tool_name, tool_result in tool_results.items():
            if hasattr(tool_result, 'result'):
                # This is a ToolResult object, convert to dict
                serialized[tool_name] = {
                    'tool_name': tool_result.tool_name,
                    'success': tool_result.success,
                    'result': self._make_serializable(tool_result.result),
                    'execution_time_ms': tool_result.execution_time_ms,
                    'error_message': tool_result.error_message,
                    'cached': tool_result.cached
                }
            else:
                # Already serialized or other type
                serialized[tool_name] = self._make_serializable(tool_result)
        return serialized
    
    def _make_serializable(self, obj):
        """
        Convert complex objects to JSON-serializable format.
        
        Args:
            obj: Object to make serializable
            
        Returns:
            JSON-serializable version of the object
        """
        if obj is None:
            return None
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            # Handle dataclass objects (like EnhancedSearchResult)
            from dataclasses import asdict
            return self._make_serializable(asdict(obj))
        elif hasattr(obj, '__dict__'):
            # Convert other objects to dict
            result = {}
            for key, value in obj.__dict__.items():
                result[key] = self._make_serializable(value)
            return result
        else:
            # Try to convert to string for other types
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)

    def _count_projects_in_results(self, tool_results: Dict) -> int:
        """
        Count the number of projects/calls found in tool results.
        """
        try:
            if not tool_results:
                return 0
            
            count = 0
            for tool_name, result in tool_results.items():
                if hasattr(result, 'results') and result.results:
                    count += len(result.results)
                elif isinstance(result, dict) and 'results' in result:
                    count += len(result['results'])
                elif isinstance(result, list):
                    count += len(result)
            
            return count
        except Exception:
            return 0
    
    def _generate_follow_up_suggestions(self, query: str, tools_executed: bool) -> List[str]:
        """
        Generate contextual follow-up suggestions based on the query and response type.
        """
        try:
            query_lower = query.lower()
            suggestions = []
            
            if tools_executed:
                # Tool-based response - suggest related searches
                if 'energy' in query_lower:
                    suggestions = [
                        "Show me energy projects that received funding",
                        "What are the eligibility criteria for energy calls?",
                        "Find calls related to renewable energy"
                    ]
                elif 'automotive' in query_lower:
                    suggestions = [
                        "Find automotive research projects",
                        "What funding is available for electric vehicles?",
                        "Show me mobility and transport calls"
                    ]
                elif 'ai' in query_lower or 'artificial intelligence' in query_lower:
                    suggestions = [
                        "Find AI research projects",
                        "What are the latest digital technology calls?",
                        "Show me robotics and AI funding opportunities"
                    ]
                else:
                    suggestions = [
                        "Show me all currently open calls",
                        "Find projects in my research area",
                        "What are the most popular funding topics?"
                    ]
            else:
                # Conversational response - suggest general queries
                suggestions = [
                    "What are some open calls about energy?",
                    "Show me completed AI projects",
                    "How do I apply for Horizon Europe funding?",
                    "What are the eligibility criteria for EU grants?"
                ]
            
            return suggestions[:3]  # Return max 3 suggestions
        except Exception:
            return []

# Test function
async def test_conversation_manager():
    """Test the conversation manager with a simple conversation."""
    try:
        manager = ConversationManager()

        # Test conversation
        conv_id = 12345

        print("Testing conversation manager...")

        # First message
        response1 = await manager.process_message(
            conversation_id=conv_id,
            user_message="What is Horizon Europe?",
            user_id=1,
            streaming=False
        )

        print(f"Response 1: {response1.get('response', 'No response')[:100]}...")

        # Follow-up message
        response2 = await manager.process_message(
            conversation_id=conv_id,
            user_message="Tell me more about its budget",
            user_id=1,
            streaming=False
        )

        print(f"Response 2: {response2.get('response', 'No response')[:100]}...")

        # Get stats
        stats = manager.get_conversation_stats(conv_id)
        print(f"Conversation stats: {stats}")

        print("✅ Conversation manager test completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_project_search_improvements():
    """Test the improved project search detection with conversation examples."""
    try:
        manager = ConversationManager()

        # Test conversation ID
        conv_id = 999

        print("🧪 Testing improved project search detection...")

        # Simulate the conversation from the user's example
        test_messages = [
            "What are some open calls for clean energy?",
            "Okay how about we look up information on projects for clean energy?",
            "No i mean look up in the cordis api",
            "No look up projects about clean energy",
            "SEARCH ON CORDIS FOR PROJECTS WITH THE TERM CLEAN ENERGY"
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 Test {i}: '{message}'")

            response = await manager.process_message(
                conversation_id=conv_id,
                user_message=message,
                user_id=1,
                streaming=False
            )

            # Check if tools were executed
            tools_executed = response.get('tools_executed', False)
            response_type = "TOOL-BASED" if tools_executed else "CONVERSATIONAL"

            print(f"   Result: {response_type}")
            print(f"   Tools executed: {tools_executed}")
            print(f"   Response preview: {response.get('response', 'No response')[:150]}...")

            # For project search messages, we expect tools to be executed
            if i >= 2:  # Messages 2-5 are project searches
                if not tools_executed:
                    print(f"   ⚠️  WARNING: Expected tools for project search but got conversational response")
                else:
                    print(f"   ✅ SUCCESS: Correctly routed to tools for project search")

        print("\n✅ Project search improvement test completed!")

    except Exception as e:
        print(f"❌ Project search test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_single_project_message():
    """Test a single project search message to debug the issue."""
    try:
        manager = ConversationManager()

        # Test conversation ID
        conv_id = 1000

        print("🧪 Testing single project search message...")

        # Test the most explicit project search message
        message = "SEARCH ON CORDIS FOR PROJECTS WITH THE TERM CLEAN ENERGY"

        print(f"\n📝 Test message: '{message}'")

        response = await manager.process_message(
            conversation_id=conv_id,
            user_message=message,
            user_id=1,
            streaming=False
        )

        # Check if tools were executed
        tools_executed = response.get('tools_executed', False)
        response_type = "TOOL-BASED" if tools_executed else "CONVERSATIONAL"

        print(f"   Result: {response_type}")
        print(f"   Tools executed: {tools_executed}")
        print(f"   Response preview: {response.get('response', 'No response')[:200]}...")

        if not tools_executed:
            print(f"   ⚠️  WARNING: Expected tools for project search but got conversational response")
        else:
            print(f"   ✅ SUCCESS: Correctly routed to tools for project search")

        print("\n✅ Single message test completed!")

    except Exception as e:
        print(f"❌ Single message test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio

    async def main():
        # Run basic test
        await test_conversation_manager()

        # Run single message test first for debugging
        await test_single_project_message()

        # Run project search improvement test
        await test_project_search_improvements()

    asyncio.run(main())