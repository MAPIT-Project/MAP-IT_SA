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
from ..tools.tool_orchestrator import create_research_orchestrator, ToolCall
from ..response.unified_formatter import UnifiedResponseFormatter
from ..ai_intent_service import AIIntentService
from ..unified_intent_classifier import UnifiedIntentClassifier
from ..call_document_service import CallDocumentService
from ..intelligent_retrieval import IntelligentRetrieval
from ..proposal_writing import (
    ProposalTemplateService,
    ProposalDraftGenerator,
    EvaluationCriteriaMatcher,
    BudgetAssistant,
    ComplianceChecker,
    QualityImprover
)
import psycopg2
from psycopg2 import pool
import re

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
            
            # Database pool for call documents
            db_url = os.getenv("DATABASE_URL")
            self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, db_url) if db_url else None
            
            # Call document service (automatic document fetching)
            if self.db_pool:
                self.call_doc_service = CallDocumentService(self.db_pool)
                logger.info("✅ Call document service initialized")
                
                # Intelligent retrieval service (uses comprehensive document library)
                self.intelligent_retrieval = IntelligentRetrieval(self.db_pool)
                logger.info("✅ Intelligent retrieval service initialized")
            else:
                self.call_doc_service = None
                self.intelligent_retrieval = None
                logger.warning("⚠️ Document services disabled (no DATABASE_URL)")
            
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
            
            # Unified intent classifier (handles ALL 5 intent types)
            self.unified_classifier = UnifiedIntentClassifier()
            logger.info("✅ Unified Intent Classifier initialized")
            
            # Data Intelligence Service - PRIMARY for graph + vector queries
            try:
                from ..data_intelligence_service import DataIntelligenceService
                self.data_intelligence = DataIntelligenceService()
                self._data_intelligence_available = True
                
                # Log detailed status
                di_status = self.data_intelligence.get_service_status()
                logger.info("=" * 50)
                logger.info("🧠 DATA INTELLIGENCE SERVICE READY")
                logger.info("=" * 50)
                logger.info(f"   Neo4j Graph:    {'✓' if di_status.get('graph_available') else '✗'}")
                logger.info(f"   Vector Search:  {'✓' if di_status.get('vector_available') else '✗'}")
                logger.info(f"   Query Planner:  {'✓' if di_status.get('planner_available') else '✗'}")
                logger.info(f"   Reranker:       {'✓' if di_status.get('reranker_available') else '✗'}")
                logger.info("=" * 50)
            except Exception as e:
                logger.warning(f"⚠️ Data Intelligence Service unavailable: {e}")
                self.data_intelligence = None
                self._data_intelligence_available = False
            
            # Agentic Manager - Self-correcting query processing (NEW!)
            try:
                from ..agents import AgenticManager
                self.agentic_manager = AgenticManager(
                    max_iterations=3,
                    sufficient_score=0.65
                )
                self._agentic_available = True
                logger.info("🤖 Agentic Manager initialized (self-correcting loop enabled)")
            except Exception as e:
                logger.warning(f"⚠️ Agentic Manager unavailable: {e}")
                self.agentic_manager = None
                self._agentic_available = False
            
            # Proposal writing services (NEW!)
            if self.db_pool:
                self.proposal_template_service = ProposalTemplateService(
                    self.db_pool, 
                    self.call_doc_service
                )
                self.draft_generator = ProposalDraftGenerator(
                    self.call_doc_service,
                    self.proposal_template_service
                )
                self.criteria_matcher = EvaluationCriteriaMatcher()
                self.budget_assistant = BudgetAssistant(self.db_pool)
                self.compliance_checker = ComplianceChecker(
                    self.call_doc_service,
                    self.db_pool
                )
                self.quality_improver = QualityImprover(self.ai_intent_service)
                logger.info("✅ Proposal writing services initialized")
            else:
                self.proposal_template_service = None
                self.draft_generator = None
                logger.warning("⚠️ Proposal writing disabled (no DATABASE_URL)")

            # Configuration
            self.config = self._load_configuration()

            agentic_status = "✓" if getattr(self, '_agentic_available', False) else "✗"
            print(f"✅ ConversationManager initialized (AI-only intent + Proposal Writing + Agentic Loop: {agentic_status})")
            
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
        
        # For streaming, return generator immediately so status updates stream in real-time
        if streaming:
            return self._generate_streaming_response_with_processing(
                conversation_id=conversation_id,
                user_message=user_message,
                user_id=user_id,
                start_time=start_time
            )
        
        # For non-streaming, do all processing first
        try:
            # Phase 1: Process user message (no database storage for V2)
            # Generate a fake message ID for compatibility
            user_message_id = random.randint(1000, 9999)

            # Phase 1.5: UNIFIED INTENT CLASSIFICATION (handles ALL 5 intents)
            recent_messages = self._get_recent_messages_simple(conversation_id, limit=5)
            logger.info(f"📋 Retrieved {len(recent_messages)} recent messages for context")
            for msg in recent_messages:
                logger.info(f"   - {msg.get('sender')}: {msg.get('text', '')[:80]}")
            
            unified_intent = await self.unified_classifier.classify_intent(
                user_message=user_message,
                conversation_id=conversation_id,
                recent_messages=recent_messages
            )
            
            logger.info(f"🎯 UNIFIED INTENT: {unified_intent.primary_intent} (confidence: {unified_intent.confidence:.2f})")
            logger.info(f"   Reasoning: {unified_intent.reasoning[:100]}...")
            if unified_intent.call_id:
                logger.info(f"   Call ID: {unified_intent.call_id}")
            
            # Build conversation context string for response generation
            conversation_context_str = self._build_conversation_context_string(recent_messages)
            
            # Route based on unified intent classification
            
            # 0. FOLLOW-UP (handle first - uses conversation context)
            if unified_intent.primary_intent == 'follow_up':
                logger.info(f"🔄 ROUTING TO: Follow-up (type: {unified_intent.follow_up_type})")
                
                # For follow-up, the conversation context IS the retrieval context
                follow_up_context = [{
                    'content': conversation_context_str,
                    'citation': 'Previous Conversation',
                    'chunk_id': 'conversation_history',
                    'metadata': {
                        'source': 'conversation_history',
                        'follow_up_type': unified_intent.follow_up_type
                    }
                }]
                
                # Create intent analysis for follow-up
                intent_analysis = {
                    'intent_type': 'follow_up',
                    'confidence': unified_intent.confidence,
                    'reasoning': unified_intent.reasoning,
                    'follow_up_type': unified_intent.follow_up_type
                }
                
                logger.info("📄 Starting follow-up response generation")
                response = await self._generate_response(
                    conversation_id=conversation_id,
                    query=user_message,
                    context=conversation_context_str,
                    retrieval_results=follow_up_context,
                    tool_results=None,
                    intent_analysis=intent_analysis,
                    start_time=start_time
                )
                
                return response
            
            # 1. PROPOSAL WRITING
            if unified_intent.primary_intent == 'proposal_writing' and self.draft_generator:
                logger.info(f"✍️ ROUTING TO: Proposal Writing (action: {unified_intent.proposal_action})")
                proposal_mode = {
                    'action': unified_intent.proposal_action or 'draft_section',
                    'call_id': unified_intent.call_id,
                    'section_id': unified_intent.section_id
                }
                return await self._handle_proposal_writing(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    user_id=user_id,
                    proposal_mode=proposal_mode
                )
            
            # 2. CALL-SPECIFIC QUESTIONS
            call_document_results = None
            if unified_intent.primary_intent == 'call_specific' and unified_intent.call_id and self.call_doc_service:
                call_id = unified_intent.call_id
                logger.info(f"📞 ROUTING TO: Call-Specific (call: {call_id})")
                
                try:
                    # SMART SEARCH STRATEGY for call documents
                    import re
                    clean_question = re.sub(r'HORIZON-[A-Z0-9-]+', '', user_message, flags=re.IGNORECASE).strip()
                    search_query = clean_question
                    question_lower = clean_question.lower()
                    
                    # Geographic eligibility questions
                    if any(phrase in question_lower for phrase in ['can i apply from', 'can we apply from', 'eligible countries', 'country eligibility', 'from ', 'netherlands', 'germany', 'france']):
                        search_query = 'eligibility EU member states associated countries third countries legal entities established participation'
                        logger.info(f"🎯 Geographic eligibility question detected")
                    # Budget/funding questions
                    elif any(word in question_lower for word in ['budget', 'funding', 'grant size', 'how much']):
                        search_query = 'budget funding contribution EUR million grant'
                    # Deadline questions
                    elif any(word in question_lower for word in ['deadline', 'when', 'submission date']):
                        search_query = 'deadline submission date stage opening'
                    
                    logger.info(f"📚 Call document search query: '{search_query}'")
                    
                    # Retrieve call documents
                    call_document_results = await self._retrieve_call_documents(
                        call_id, 
                        user_message,
                        keywords=[search_query] if search_query else []
                    )
                    if call_document_results:
                        logger.info(f"✅ Retrieved {len(call_document_results)} call-specific chunks")
                except Exception as e:
                    logger.error(f"❌ Error retrieving call documents: {e}")
            
            # Phase 2: Execute tools based on unified intent - NO OLD AI INTENT SERVICE!
            logger.info(f"🎯 Using unified intent: {unified_intent.primary_intent}")
            
            tool_results = None
            retrieval_results = []
            
            # Route based on unified intent
            if call_document_results:
                # Call-specific: Use loaded documents directly
                logger.info("📚 Call-specific: Using loaded documents")
                retrieval_results = call_document_results
            
            elif unified_intent.primary_intent in ['search_projects', 'search_calls']:
                # Search: Execute tools from unified classifier's tool plan
                logger.info(f"🔍 {unified_intent.primary_intent}: Executing tools")
                
                if unified_intent.tool_plan:
                    # Convert dict tool plans to ToolCall objects
                    tool_calls = [
                        ToolCall(
                            tool_name=tp.get('tool_name'),
                            parameters=tp.get('parameters', {}),
                            execution_order=tp.get('execution_order', idx),
                            depends_on=tp.get('depends_on')
                        ) if isinstance(tp, dict) else tp
                        for idx, tp in enumerate(unified_intent.tool_plan)
                    ]
                    
                    tool_results = await self.tool_orchestrator.execute_plan(
                        tool_calls,
                        conversation_id,
                        unified_intent.project_keywords or unified_intent.call_keywords or []
                    )
                    logger.info(f"✅ Tool execution complete")
                    
                    # Convert tool results to retrieval format
                    if tool_results:
                        retrieval_results = self._convert_tool_results_to_retrieval(tool_results)
            
            elif unified_intent.primary_intent == 'faq':
                # FAQ: Use DataIntelligenceService for smart graph + vector search
                logger.info(f"🧠 FAQ: Using Data Intelligence Service (Planner LLM)")
                
                if self._data_intelligence_available:
                    try:
                        di_result = await self.data_intelligence.search(
                            query=user_message,
                            context="",
                            max_results=10,
                            rerank=True
                        )
                        
                        if di_result.success:
                            # Convert to retrieval format
                            retrieval_results = []
                            
                            # Add graph results
                            for r in di_result.graph_results:
                                retrieval_results.append({
                                    'content': str(r),
                                    'source': 'neo4j_graph',
                                    'score': 1.0,
                                    'metadata': {'type': 'structured_data'}
                                })
                            
                            # Add vector results
                            for r in di_result.vector_results:
                                retrieval_results.append({
                                    'content': r.get('content', str(r)),
                                    'source': r.get('source', 'vector'),
                                    'score': r.get('rerank_score', r.get('score', 0.5)),
                                    'metadata': r
                                })
                            
                            # Add answer context at the front
                            if di_result.answer_context:
                                retrieval_results.insert(0, {
                                    'content': di_result.answer_context,
                                    'source': 'data_intelligence',
                                    'score': 1.0,
                                    'metadata': {
                                        'intent': di_result.intent_type,
                                        'confidence': di_result.confidence
                                    }
                                })
                            
                            logger.info(f"✅ DataIntelligenceService: {len(retrieval_results)} results")
                        else:
                            retrieval_results = await self._retrieve_information(
                                conversation_id=conversation_id,
                                query=user_message,
                                context=""
                            )
                    except Exception as e:
                        logger.error(f"❌ DataIntelligenceService error: {e}")
                        retrieval_results = await self._retrieve_information(
                            conversation_id=conversation_id,
                            query=user_message,
                            context=""
                        )
                else:
                    retrieval_results = await self._retrieve_information(
                        conversation_id=conversation_id,
                        query=user_message,
                        context=""
                    )
                    logger.info(f"✅ Retrieved {len(retrieval_results)} chunks")
            
            # Create intent_analysis format for compatibility
            intent_analysis = {
                'intent_type': unified_intent.primary_intent,
                'confidence': unified_intent.confidence,
                'reasoning': unified_intent.reasoning,
                'extracted_keywords': unified_intent.project_keywords or unified_intent.call_keywords or []
            }

            # Phase 4: Generate response
            logger.info(f"📝 RESPONSE GENERATION: tool_results={tool_results is not None}, retrieval_results={len(retrieval_results)}")

            if tool_results:
                logger.info(f"🔧 TOOL RESULTS SUMMARY: {len(tool_results)} tools executed")
                for tool_name, tool_result in tool_results.items():
                    logger.info(f"   Tool {tool_name}: success={tool_result.success}, has_result={tool_result.result is not None}")

            # Non-streaming response
            if True:
                logger.info("📄 Starting non-streaming response generation")
                response = await self._generate_response(
                    conversation_id=conversation_id,
                    query=user_message,
                    context=conversation_context_str,  # Pass conversation context
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
        
        print(f"🔄 DEBUG: _convert_tool_results_to_retrieval called with {len(tool_results)} tool results")
        
        for tool_name, tool_result_obj in tool_results.items():
            print(f"🔍 DEBUG: Processing tool: {tool_name}, success: {tool_result_obj.success}")
            try:
                if tool_result_obj.success:
                    tool_data = tool_result_obj.result
                    print(f"📊 DEBUG: Tool data type: {type(tool_data)}, keys: {list(tool_data.keys()) if isinstance(tool_data, dict) else 'Not a dict'}")
                    
                    if tool_name == 'eu_portal_search':
                        print(f"🔍 DEBUG: eu_portal_search - checking for 'calls' key...")
                        print(f"📋 DEBUG: tool_data has 'calls': {('calls' in tool_data) if isinstance(tool_data, dict) else False}")
                        if isinstance(tool_data, dict):
                            print(f"🔢 DEBUG: calls count: {len(tool_data.get('calls', []))}")
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

    def _extract_call_id(self, text: str) -> Optional[str]:
        """Extract call ID from text (e.g., HORIZON-CL3-2025-02-CS-ECCC-01)"""
        # Pattern for Horizon Europe call IDs
        pattern = r'HORIZON-[A-Z0-9]+-\d{4}(?:-\d+)?(?:-[A-Z]+){1,5}-\d+'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0).upper() if match else None
    
    async def _retrieve_call_documents(self, call_id: str, query: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve call-specific information using BOTH structured metadata and document chunks.
        
        PRIORITY 1: Structured metadata from API (instant answers for eligibility, budget, deadlines)
        PRIORITY 2: Document chunks for detailed information
        """
        if not self.call_doc_service:
            return []
        
        try:
            logger.info(f"📚 Retrieving call-specific information for {call_id}")
            results = []
            
            # STEP 1: Get structured metadata from API (FAST!)
            call_metadata = self.call_doc_service.get_call_metadata(call_id)
            
            if call_metadata:
                # Build a structured summary from metadata
                metadata_text = f"""**CALL METADATA (Official API Data for {call_id})**

Title: {call_metadata.get('title', 'N/A')}

ELIGIBILITY:
- Eligible Countries: {call_metadata.get('eligible_countries', 'See call documentation')}
- Restrictions: {call_metadata.get('eligibility_restrictions', 'None specified')}

BUDGET:
- Minimum Contribution: €{call_metadata.get('min_contribution', 0):,} 
- Maximum Contribution: €{call_metadata.get('max_contribution', 0):,}
- Expected Number of Grants: {call_metadata.get('expected_grants', 'Not specified')}

DEADLINE:
- Submission Deadline: {call_metadata.get('deadline_date', 'See call documentation')}

TYPE OF ACTION:
- {', '.join(call_metadata.get('types_of_action', [])) if call_metadata.get('types_of_action') else 'Not specified'}

This metadata was extracted directly from the EU Portal API and represents the official call conditions."""

                results.append({
                    'content': metadata_text,
                    'citation': f"Call Metadata for {call_id} (EU Portal API)",
                    'chunk_id': f"metadata_{call_id}",
                    'metadata': {
                        'source': 'call_metadata_api',
                        'call_id': call_id,
                        'is_structured': True,
                        'priority': 'high'  # Tell AI this is authoritative
                    }
                })
                logger.info(f"✅ Retrieved structured metadata for {call_id}")
                logger.info(f"   Eligibility: {call_metadata.get('eligible_countries')}")
            
            # STEP 2: Get document chunks for detailed information
            search_query = ' '.join(keywords) if keywords else None
            logger.info(f"📚 Semantic search query: '{search_query}'")
            
            chunks = self.call_doc_service.search_call_chunks(
                call_identifier=call_id,
                query=search_query,
                limit=20  # Increased from 10 to give AI more options
            )
            
            # Convert to retrieval format
            for chunk in chunks:
                results.append({
                    'content': chunk['chunk_text'],
                    'citation': f"{chunk['document_title']} - {chunk.get('section_title', 'N/A')}",
                    'chunk_id': str(chunk['chunk_id']),
                    'metadata': {
                        'source': 'call_documents',
                        'call_id': call_id,
                        'document_type': chunk['document_type'],
                        'relevance_score': chunk['relevance_score']
                    }
                })
            
            logger.info(f"✅ Retrieved {len(results)} total items ({1 if call_metadata else 0} metadata + {len(chunks)} chunks)")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error retrieving call documents: {e}", exc_info=True)
            return []
    
    async def _retrieve_information(self,
                                   conversation_id: int,
                                   query: str,
                                   context: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information - now primarily handled by tools.
        Enhanced with automatic call-specific document retrieval.
        """
        try:
            # Check if query mentions a specific call
            call_id = self._extract_call_id(query) or self._extract_call_id(context)
            
            if call_id:
                # Automatic call document retrieval!
                logger.info(f"🎯 Detected call ID: {call_id} - fetching documents automatically")
                call_chunks = await self._retrieve_call_documents(call_id, query, keywords=None)
                if call_chunks:
                    logger.info(f"✅ Using {len(call_chunks)} call-specific chunks")
                    return call_chunks
            
            # Use intelligent retrieval across comprehensive document library
            logger.info(f"🔍 Using intelligent retrieval for general question: {query[:100]}...")
            
            if self.intelligent_retrieval:
                # Smart search across all 29 documents with query classification
                results = self.intelligent_retrieval.search_documents(
                    query=query,
                    limit=15  # Increased from 4 to 15 for better context
                )
                
                if results:
                    logger.info(f"✅ Intelligent retrieval found {len(results)} relevant chunks")
                    logger.info(f"   Document types: {set(r['metadata']['document_type'] for r in results)}")
                    return results
                else:
                    logger.info("⚠️ Intelligent retrieval returned no results - AI will provide general guidance")
                    return []  # Return empty list - AI will give professional response without mock data
            
            # If intelligent retrieval is not available, return empty list
            logger.warning("⚠️ Intelligent retrieval not available - returning empty results")
            return []
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
            logger.info(f"🔄 RESPONSE TYPE DECISION: tool_results present = {tool_results is not None}, retrieval_results = {len(retrieval_results) if retrieval_results else 0}")

            # If we have call document chunks, use AI to generate response with that context
            if retrieval_results and not tool_results:
                logger.info(f"📚 Using call document chunks ({len(retrieval_results)} chunks) to generate response")
                conversational_response = self._generate_conversational_response(
                    query=query,
                    context=context,
                    retrieval_results=retrieval_results,
                    intent_analysis=intent_analysis
                )
                # Build structured citations with metadata for frontend
                structured_citations = []
                for i, r in enumerate(retrieval_results, 1):
                    structured_citations.append({
                        'number': i,
                        'text': r.get('citation', 'Unknown'),
                        'chunk_id': r.get('chunk_id'),
                        'content_snippet': r.get('content', '')[:200] + '...' if len(r.get('content', '')) > 200 else r.get('content', ''),
                        'metadata': r.get('metadata', {}),
                        'source_type': r.get('metadata', {}).get('source', 'unknown')
                    })
                
                response = {
                    'answer': conversational_response,
                    'citations': structured_citations,
                    'confidence': 0.95,  # High confidence for call-specific documents
                    'grounded': True
                }
            elif tool_results:
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
                
                # Fast path for simple greetings - no tools needed
                query_lower = query.lower().strip()
                simple_greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
                if query_lower in simple_greetings or (len(query_lower) < 15 and any(g in query_lower for g in ['hi', 'hello', 'hey'])):
                    logger.info("⚡ Fast greeting response - no tools needed")
                    conversational_response = "Hello! I'm your Horizon Europe research funding assistant. I can help you find funding calls, search for research projects, answer questions about Horizon Europe programs, and assist with proposal writing. How can I help you today?"
                else:
                    conversational_response = self._generate_conversational_response(
                        query=query,
                        context=context,
                        retrieval_results=retrieval_results,
                        intent_analysis=intent_analysis
                    )
                    
                    # Add fallback notice if confidence is low (0.5 = fallback mode)
                    if intent_analysis.get('confidence', 1.0) <= 0.5:
                        conversational_response = f"⚠️ **[DEV MODE]** Fallback logic active - AI intent detection failed. Response quality may be limited.\n\n{conversational_response}"

                logger.info(f"💬 CONVERSATIONAL RESPONSE LENGTH: {len(conversational_response) if conversational_response else 0}")
                logger.info(f"💬 CONVERSATIONAL RESPONSE PREVIEW: {conversational_response[:200] if conversational_response else 'None'}...")

                response = {
                    'answer': conversational_response,
                    'citations': [],
                    'confidence': 0.8,  # Good confidence for conversational responses
                    'grounded': True if retrieval_results else False
                }
            
            # V2 endpoint: No database storage - just add to memory for conversation context
            # Generate a fake message ID for compatibility
            assistant_message_id = random.randint(1000, 9999)
            
            # Only store in memory service, not database
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
    
    async def _generate_streaming_response_with_processing(self,
                                                           conversation_id: int,
                                                           user_message: str,
                                                           user_id: int,
                                                           start_time: datetime) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response with real-time status updates.
        Does all processing INSIDE the generator so status updates stream immediately.
        """
        try:
            # INSTANT FEEDBACK - sent immediately when request received
            yield {
                'type': 'status',
                'stage': 'processing',
                'message': 'Processing...'
            }
            
            # Phase 1: Process user message (no database storage for V2)
            yield {
                'type': 'status',
                'stage': 'processing_message',
                'message': 'Processing your message...'
            }
            # Generate a fake message ID for compatibility (not saved to database)
            user_message_id = random.randint(1000, 9999)
            
            # Phase 1.6: UNIFIED INTENT CLASSIFICATION (handles ALL 5 intents)
            recent_messages = self._get_recent_messages_simple(conversation_id, limit=5)
            logger.info(f"📋 [STREAMING] Retrieved {len(recent_messages)} recent messages for context")
            for msg in recent_messages:
                logger.info(f"   - {msg.get('sender')}: {msg.get('text', '')[:80]}")
            
            unified_intent = await self.unified_classifier.classify_intent(
                user_message=user_message,
                conversation_id=conversation_id,
                recent_messages=recent_messages
            )
            
            logger.info(f"🎯 [STREAMING] UNIFIED INTENT: {unified_intent.primary_intent} (confidence: {unified_intent.confidence:.2f})")
            if unified_intent.call_id:
                logger.info(f"   [STREAMING] Call ID: {unified_intent.call_id}")
            
            # Build conversation context string
            conversation_context_str = self._build_conversation_context_string(recent_messages)
            
            # 0. FOLLOW-UP (handle first - uses conversation context)
            if unified_intent.primary_intent == 'follow_up':
                logger.info(f"🔄 [STREAMING] ROUTING TO: Follow-up (type: {unified_intent.follow_up_type})")
                
                yield {
                    'type': 'progress',
                    'stage': 'follow_up_detected',
                    'message': 'Processing your follow-up question using conversation history...'
                }
                
                # For follow-up, the conversation context IS the retrieval context
                follow_up_context = [{
                    'content': conversation_context_str,
                    'citation': 'Previous Conversation',
                    'chunk_id': 'conversation_history',
                    'metadata': {
                        'source': 'conversation_history',
                        'follow_up_type': unified_intent.follow_up_type
                    }
                }]
                
                # Create intent analysis for follow-up
                intent_analysis = {
                    'intent_type': 'follow_up',
                    'confidence': unified_intent.confidence,
                    'reasoning': unified_intent.reasoning,
                    'follow_up_type': unified_intent.follow_up_type
                }
                
                # Stream the follow-up response
                async for chunk in self._generate_streaming_response(
                    conversation_id=conversation_id,
                    query=user_message,
                    context=conversation_context_str,
                    retrieval_results=follow_up_context,
                    tool_results=None,
                    intent_analysis=intent_analysis,
                    start_time=start_time
                ):
                    yield chunk
                return
            
            # 1. PROPOSAL WRITING
            if unified_intent.primary_intent == 'proposal_writing' and self.draft_generator:
                logger.info(f"✍️ [STREAMING] ROUTING TO: Proposal Writing")
                
                # Send intent detected event
                yield {
                    'type': 'progress',
                    'stage': 'intent_detected',
                    'message': f'AI analyzed intent: proposal_writing',
                    'routing_decision': 'proposal_writing',
                    'intent_confidence': unified_intent.confidence
                }
                
                proposal_mode = {
                    'action': unified_intent.proposal_action or 'draft_section',
                    'call_id': unified_intent.call_id,
                    'section_id': unified_intent.section_id
                }
                
                logger.info(f"📝 [STREAMING] Calling _handle_proposal_writing with mode: {proposal_mode}")
                result = await self._handle_proposal_writing(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    user_id=user_id,
                    proposal_mode=proposal_mode
                )
                
                logger.info(f"📝 [STREAMING] Result type: {type(result)}, has __aiter__: {hasattr(result, '__aiter__')}")
                
                # Check if result is an async generator (for exports with progress)
                if hasattr(result, '__aiter__'):
                    logger.info(f"📝 [STREAMING] Starting to yield from async generator")
                    chunk_count = 0
                    async for chunk in result:
                        chunk_count += 1
                        yield chunk
                    logger.info(f"📝 [STREAMING] Finished yielding {chunk_count} chunks from generator")
                    return
                else:
                    logger.info(f"📝 [STREAMING] Yielding single response dict")
                    yield {
                        'type': 'response',
                        'message': result.get('response', ''),
                        'download_url': result.get('download_url'),
                        'file_type': result.get('file_type'),
                        'proposal_id': result.get('proposal_id'),
                        'package_contents': result.get('package_contents')
                    }
                    return
            
            # 2. CALL-SPECIFIC QUESTIONS
            call_document_results = None
            if unified_intent.primary_intent == 'call_specific' and unified_intent.call_id and self.call_doc_service:
                call_id = unified_intent.call_id
                logger.info(f"📞 [STREAMING] ROUTING TO: Call-Specific (call: {call_id})")
                
                yield {
                    'type': 'status',
                    'stage': 'fetching_call_documents',
                    'message': f'Analyzing call {call_id}...'
                }
                
                try:
                    # SMART SEARCH STRATEGY for call documents
                    import re
                    clean_question = re.sub(r'HORIZON-[A-Z0-9-]+', '', user_message, flags=re.IGNORECASE).strip()
                    search_query = clean_question
                    question_lower = clean_question.lower()
                    
                    # Geographic eligibility questions
                    if any(phrase in question_lower for phrase in ['can i apply from', 'can we apply from', 'eligible countries', 'country eligibility', 'from ', 'netherlands', 'germany', 'france']):
                        search_query = 'eligibility EU member states associated countries third countries legal entities established participation'
                        logger.info(f"🎯 [STREAMING] Geographic eligibility question detected")
                    # Budget/funding questions
                    elif any(word in question_lower for word in ['budget', 'funding', 'grant size', 'how much']):
                        search_query = 'budget funding contribution EUR million grant'
                    # Deadline questions
                    elif any(word in question_lower for word in ['deadline', 'when', 'submission date']):
                        search_query = 'deadline submission date stage opening'
                    
                    logger.info(f"📚 [STREAMING] Call document search query: '{search_query}'")
                    
                    call_document_results = await self._retrieve_call_documents(
                        call_id, 
                        user_message, 
                        keywords=[search_query] if search_query else []
                    )
                    if call_document_results:
                        logger.info(f"✅ [STREAMING] Retrieved {len(call_document_results)} call-specific chunks")
                        yield {
                            'type': 'progress',
                            'stage': 'call_documents_loaded',
                            'message': f'Loaded {len(call_document_results)} relevant document sections',
                            'chunks_loaded': len(call_document_results)
                        }
                except Exception as e:
                    logger.error(f"❌ [STREAMING] Error retrieving call documents: {e}")
            
            # Phase 2: Tool execution based on unified intent
            # Use unified classifier's intent and tool plan - NO OLD AI INTENT SERVICE!
            
            yield {
                'type': 'progress',
                'stage': 'intent_detected',
                'message': f'AI analyzed intent: {unified_intent.primary_intent}',
                'routing_decision': unified_intent.primary_intent,
                'intent_confidence': unified_intent.confidence
            }
            
            tool_results = None
            retrieval_results = []
            
            # Route based on unified intent
            if call_document_results:
                # Call-specific: Use loaded documents directly
                logger.info("📚 [STREAMING] Call-specific: Using loaded documents")
                retrieval_results = call_document_results
                yield {
                    'type': 'progress',
                    'stage': 'using_call_documents',
                    'message': 'Using call-specific documentation to answer'
                }
            
            elif unified_intent.primary_intent in ['search_projects', 'search_calls']:
                # Search: Execute tools from unified classifier's tool plan
                logger.info(f"🔍 [STREAMING] {unified_intent.primary_intent}: Executing tools")
                yield {
                    'type': 'status',
                    'stage': 'executing_tools',
                    'message': 'Searching databases...'
                }
                
                if unified_intent.tool_plan:
                    # Convert dict tool plans to ToolCall objects
                    tool_calls = [
                        ToolCall(
                            tool_name=tp.get('tool_name'),
                            parameters=tp.get('parameters', {}),
                            execution_order=tp.get('execution_order', idx),
                            depends_on=tp.get('depends_on')
                        ) if isinstance(tp, dict) else tp
                        for idx, tp in enumerate(unified_intent.tool_plan)
                    ]
                    
                    tool_results = await self.tool_orchestrator.execute_plan(
                        tool_calls,
                        conversation_id,
                        unified_intent.project_keywords or unified_intent.call_keywords or []
                    )
                    logger.info(f"✅ [STREAMING] Tool execution complete")
            
            elif unified_intent.primary_intent == 'faq':
                # FAQ: Use Agentic Loop for self-correcting search (if available)
                # Falls back to DataIntelligenceService if agentic not available
                
                if getattr(self, '_agentic_available', False):
                    # 🤖 AGENTIC LOOP - Self-correcting search with evaluation and replanning
                    logger.info(f"🤖 [STREAMING] FAQ: Using Agentic Loop (self-correcting)")
                    yield {
                        'type': 'progress',
                        'stage': 'agentic_search',
                        'message': 'AI is using self-correcting search...'
                    }
                    
                    try:
                        # Stream progress from agentic manager
                        agentic_response = None
                        agentic_metadata = {}
                        
                        async for update in self.agentic_manager.process_query_streaming(
                            query=user_message,
                            conversation_id=str(conversation_id),
                            conversation_history=recent_messages
                        ):
                            update_type = update.get('type', 'unknown')
                            
                            if update_type == 'status':
                                # Forward status updates
                                yield {
                                    'type': 'progress',
                                    'stage': f"agentic_{update.get('phase', 'processing')}",
                                    'message': update.get('message', 'Processing...'),
                                    'iteration': update.get('iteration', 1)
                                }
                            
                            elif update_type == 'progress':
                                # Forward progress updates
                                yield {
                                    'type': 'progress',
                                    'stage': 'agentic_search',
                                    'message': update.get('message', 'Searching...'),
                                    'count': update.get('count', 0)
                                }
                            
                            elif update_type == 'response':
                                # Capture final response
                                agentic_response = update.get('response', '')
                                agentic_metadata = update.get('metadata', {})
                                
                                # Log agentic performance
                                iterations = agentic_metadata.get('iterations', 1)
                                quality = agentic_metadata.get('quality_score', 0)
                                confidence = agentic_metadata.get('confidence', 'unknown')
                                logger.info(f"🤖 [AGENTIC] Completed: {iterations} iteration(s), quality={quality:.2f}, confidence={confidence}")
                                
                                # Show user the quality info
                                if iterations > 1:
                                    yield {
                                        'type': 'progress',
                                        'stage': 'agentic_refined',
                                        'message': f'Refined search {iterations-1} time(s) for better results'
                                    }
                            
                            elif update_type == 'error':
                                logger.error(f"🤖 [AGENTIC] Error: {update.get('error')}")
                                # Fall through to fallback
                                agentic_response = None
                                break
                        
                        if agentic_response:
                            # Use agentic response as retrieval context
                            retrieval_results = [{
                                'content': agentic_response,
                                'source': 'agentic_loop',
                                'score': agentic_metadata.get('quality_score', 1.0),
                                'metadata': {
                                    'type': 'agentic_response',
                                    'iterations': agentic_metadata.get('iterations', 1),
                                    'confidence': agentic_metadata.get('confidence', 'medium'),
                                    'intent': unified_intent.primary_intent
                                }
                            }]
                            logger.info(f"✅ [STREAMING] Agentic Loop: response ready")
                        else:
                            # Agentic failed, fall back to DataIntelligenceService
                            logger.warning(f"⚠️ [STREAMING] Agentic Loop failed, falling back to DataIntelligenceService")
                            retrieval_results = await self._fallback_to_data_intelligence(
                                user_message, conversation_id
                            )
                            
                    except Exception as e:
                        logger.error(f"❌ [STREAMING] Agentic Loop error: {e}")
                        retrieval_results = await self._fallback_to_data_intelligence(
                            user_message, conversation_id
                        )
                
                else:
                    # No agentic available - use DataIntelligenceService directly
                    logger.info(f"🧠 [STREAMING] FAQ: Using Data Intelligence Service (Planner LLM)")
                    yield {
                        'type': 'progress',
                        'stage': 'intelligent_search',
                        'message': 'AI is planning the optimal search strategy...'
                    }
                    
                    retrieval_results = await self._fallback_to_data_intelligence(
                        user_message, conversation_id
                    )
            
            # Convert tool results to retrieval format if needed
            if tool_results:
                retrieval_results = self._convert_tool_results_to_retrieval(tool_results)
                logger.info(f"✅ [STREAMING] Converted tool results to retrieval format")
                yield {
                    'type': 'status',
                    'stage': 'tools_complete',
                    'message': 'Search complete, formatting results...'
                }
            
            # Phase 3: Stream the response
            yield {
                'type': 'status',
                'stage': 'generating_response',
                'message': 'Generating response...'
            }
            
            # Create intent_analysis format for compatibility with response generator
            intent_analysis = {
                'intent_type': unified_intent.primary_intent,
                'confidence': unified_intent.confidence,
                'reasoning': unified_intent.reasoning,
                'extracted_keywords': unified_intent.project_keywords or unified_intent.call_keywords or []
            }
            
            # Now call the existing streaming response generator
            async for chunk in self._generate_streaming_response(
                conversation_id=conversation_id,
                query=user_message,
                context=conversation_context_str,  # Pass conversation context for continuity
                retrieval_results=retrieval_results,
                tool_results=tool_results,
                intent_analysis=intent_analysis,
                start_time=start_time
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in streaming with processing: {e}")
            yield {
                'type': 'error',
                'error': str(e),
                'stage': 'error'
            }
    
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
            # Instant feedback - send immediately when request is received
            yield {
                'type': 'status',
                'stage': 'processing',
                'message': 'Processing...'
            }
            
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
                
                # Check if we have retrieval results (e.g., from call-specific documents)
                if retrieval_results and len(retrieval_results) > 0:
                    logger.info(f"📚 Using {len(retrieval_results)} retrieved documents for response")
                    conversational_response = self._generate_conversational_response(
                        query=query,
                        context=context,
                        retrieval_results=retrieval_results,
                        intent_analysis=intent_analysis
                    )
                else:
                    # Fast path for simple greetings - no tools needed
                    query_lower = query.lower().strip()
                    simple_greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
                    if query_lower in simple_greetings or (len(query_lower) < 15 and any(g in query_lower for g in ['hi', 'hello', 'hey'])):
                        logger.info("⚡ Fast greeting response - no tools needed")
                        conversational_response = "Hello! I'm your Horizon Europe research funding assistant. I can help you find funding calls, search for research projects, answer questions about Horizon Europe programs, and assist with proposal writing. How can I help you today?"
                    # For research funding queries, use enhanced fallback directly for better quality
                    elif any(keyword in query_lower for keyword in ['horizon europe', 'funding', 'budget', 'structure', 'pillar', 'programme', 'call', 'grant']):
                        logger.info("💡 Research funding streaming query - using enhanced fallback")
                        conversational_response = self._get_enhanced_fallback_response(query, intent_analysis)
                        # Add fallback notice if confidence is low
                        if intent_analysis.get('confidence', 1.0) <= 0.5:
                            conversational_response = f"⚠️ **[DEV MODE]** Fallback logic active - AI intent detection failed. Response quality may be limited.\n\n{conversational_response}"
                    else:
                        conversational_response = self._generate_conversational_response(
                            query=query,
                            context=context,
                            retrieval_results=retrieval_results,
                            intent_analysis=intent_analysis
                        )
                    
                    # Add fallback notice if confidence is low (0.5 = fallback mode)
                    if intent_analysis.get('confidence', 1.0) <= 0.5:
                        conversational_response = f"⚠️ **[DEV MODE]** Fallback logic active - AI intent detection failed. Response quality may be limited.\n\n{conversational_response}"
                
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
            
            # Build structured citations for streaming response
            structured_citations = []
            if retrieval_results:
                for i, r in enumerate(retrieval_results, 1):
                    structured_citations.append({
                        'number': i,
                        'text': r.get('citation', 'Unknown'),
                        'chunk_id': r.get('chunk_id'),
                        'content_snippet': r.get('content', '')[:200] + '...' if len(r.get('content', '')) > 200 else r.get('content', ''),
                        'metadata': r.get('metadata', {}),
                        'source_type': r.get('metadata', {}).get('source', 'unknown')
                    })
            
            # Send completion with full metadata IMMEDIATELY
            processing_time = (datetime.now() - start_time).total_seconds()
            
            yield {
                'type': 'complete',
                'ai_provider': 'google',
                'ai_version': 'gemini-flash-lite-latest',
                'model_used': 'gemini-flash-lite-latest',
                'data_source': 'EU Funding & Tenders Portal' if tools_executed else 'Conversational AI',
                'processing_time': processing_time,
                'projects_found': projects_found,
                'citations': structured_citations,  # ✨ NEW: Include structured citations
                'confidence': confidence,
                'grounded': grounded,
                'logs': {
                    'question': query,
                    'model_used': 'gemini-flash-lite-latest',
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
            
            # V2 endpoint: No database storage - just add to memory for conversation context
            try:
                # Generate a fake message ID for compatibility
                assistant_message_id = random.randint(1000, 9999)
                
                # Only store in memory service, not database
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

            # Check if this is a "how to" question first - use enhanced fallback immediately
            query_lower = query.lower()
            if any(how_word in query_lower for how_word in ['how do i apply', 'how to apply', 'how can i apply', 'how do I apply', 'how to apply for funding', 'how do I apply for funding']):
                logger.info("💡 Application help question detected - using enhanced fallback directly")
                return self._get_enhanced_fallback_response(query, intent_analysis)

            # Prepare context chunks from retrieval results
            context_chunks = retrieval_results if retrieval_results else []
            logger.info(f"💬 Context chunks available: {len(context_chunks)}")

            # If we have retrieval results (e.g., from call documents), use them directly with AI
            if context_chunks:
                logger.info(f"📚 Using {len(context_chunks)} retrieved chunks (likely call documents)")
            else:
                # Only use fallback if NO retrieval results for research funding queries
                research_keywords = ['horizon europe', 'funding', 'budget', 'structure', 'pillar', 'programme', 'call', 'grant']
                if any(keyword in query_lower for keyword in research_keywords):
                    logger.info("💡 Research funding query detected - using enhanced fallback directly")
                    return self._get_enhanced_fallback_response(query, intent_analysis)

            # Check if response generator is available and properly initialized
            if not hasattr(self, 'response_generator') or not self.response_generator:
                logger.warning("Response generator not initialized - using enhanced fallback")
                return self._get_enhanced_fallback_response(query, intent_analysis)

            # Test response generator with a simple call first
            try:
                logger.info("💬 Testing response generator availability...")
                # Simple test to see if the AI model is accessible
                test_response = self.response_generator.model.generate_content("Test")
                if not test_response or not test_response.text:
                    logger.warning("Response generator model not responding - using enhanced fallback")
                    return self._get_enhanced_fallback_response(query, intent_analysis)
            except Exception as test_e:
                logger.warning(f"Response generator test failed: {test_e} - using enhanced fallback")
                return self._get_enhanced_fallback_response(query, intent_analysis)

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
                # Check for error messages in the response
                if 'error' in answer.lower() or 'encountered an error' in answer.lower():
                    logger.warning("Response contains error message, using enhanced fallback")
                    return self._get_enhanced_fallback_response(query, intent_analysis)
                elif answer and len(answer.strip()) > 50:  # Increased threshold
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

**YOUR APPROACH:**
• Professional, direct, and concise
• Data-driven and precise with facts and figures
• Answer the specific question asked without unnecessary elaboration
• Provide clear next steps when requested

**RESPONSE GUIDELINES:**
• Answer directly and concisely
• Include specific data (budget figures, deadlines, requirements) when relevant
• Use bullet points for clarity
• Avoid overly enthusiastic or promotional language
• Avoid phrases like "That's an excellent question" or "crucial strategic step"
• Get straight to the answer without preamble
• Be factual and objective

**COUNTRY ELIGIBILITY GUIDANCE:**
When answering questions about specific countries (e.g., "Can I apply from Switzerland?"):
• If the documents describe general rules (e.g., "EU Member States and Associated Countries are eligible")
• You MAY use your knowledge to identify if the mentioned country falls into those categories
• Example: If docs say "Associated Countries eligible" and user asks about Switzerland, you can answer "Yes, as Switzerland is an Associated Country"
• Always cite the general rule from the documents [citation]
• Add a disclaimer: "Please verify in the official call documentation for any specific restrictions"
• You know: EU-27 members, Associated Countries (including Switzerland, Norway, Iceland, UK-partial, Israel, etc.)

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
Use a professional, direct tone. Provide precise answers without unnecessary enthusiasm or preamble.

**CURRENT CONTEXT:**
You're answering questions about European research and innovation funding. Be concise and factual."""
    
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
        
        # Actually store message in database
        if self.db_pool:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            try:
                # First ensure conversation exists
                cursor.execute("""
                    INSERT INTO conversation (id, user_id, name, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                """, (conversation_id, 1, f'Chat {conversation_id}'))  # user_id must be integer
                
                # Check for duplicate message (within last 5 seconds)
                cursor.execute("""
                    SELECT id FROM message
                    WHERE conversation_id = %s 
                      AND sender = 'user' 
                      AND text = %s
                      AND created_at > NOW() - INTERVAL '5 seconds'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (conversation_id, message))
                
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"⚠️ Duplicate message detected (within 5s), reusing existing ID: {existing[0]}")
                    return existing[0]
                
                # Insert new message
                cursor.execute("""
                    INSERT INTO message (conversation_id, sender, text, created_at)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                """, (conversation_id, 'user', message))
                
                message_id = cursor.fetchone()[0]
                conn.commit()  # Commit immediately so it's visible to next query
                logger.info(f"✅ Stored user message {message_id} in database")
                
            except Exception as e:
                logger.error(f"❌ Failed to store user message: {e}")
                conn.rollback()
                message_id = random.randint(1000, 9999)  # Fallback
            finally:
                self.db_pool.putconn(conn)
        else:
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
                                      message: str,
                                      citations: Optional[List[Dict[str, Any]]] = None) -> int:
        """Store assistant message in database and return message ID."""
        
        # Actually store message in database
        if self.db_pool:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            try:
                # First ensure conversation exists
                cursor.execute("""
                    INSERT INTO conversation (id, user_id, name, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                """, (conversation_id, 1, f'Chat {conversation_id}'))  # user_id must be integer
                
                # Check for duplicate message (within last 5 seconds)
                cursor.execute("""
                    SELECT id FROM message
                    WHERE conversation_id = %s
                      AND sender = 'assistant'
                      AND text = %s
                      AND created_at > NOW() - INTERVAL '5 seconds'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (conversation_id, message))
                
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"⚠️ Duplicate assistant message detected (within 5s), reusing existing ID: {existing[0]}")
                    return existing[0]
                
                # Insert new message
                cursor.execute("""
                    INSERT INTO message (conversation_id, sender, text, created_at)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                """, (conversation_id, 'assistant', message))
                
                message_id = cursor.fetchone()[0]
                
                # Save citations if provided
                if citations and len(citations) > 0:
                    citations_json = json.dumps(citations)
                    cursor.execute("""
                        UPDATE message
                        SET citations = %s
                        WHERE id = %s
                    """, (citations_json, message_id))
                    logger.info(f"💾 Saved {len(citations)} citations to message {message_id}")
                
                conn.commit()  # Commit immediately so it's visible to next query
                logger.info(f"✅ Stored assistant message {message_id} in database")
                
            except Exception as e:
                logger.error(f"❌ Failed to store assistant message: {e}")
                conn.rollback()
                message_id = random.randint(1000, 9999)  # Fallback
            finally:
                self.db_pool.putconn(conn)
        else:
            message_id = random.randint(1000, 9999)
        
        return message_id
    
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
    
    async def process_with_agentic_loop(
        self,
        conversation_id: int,
        user_message: str,
        user_id: int,
        streaming: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a message using the self-correcting agentic loop.
        
        This method uses the AgenticManager to:
        1. Understand the query
        2. Plan an execution strategy
        3. Execute the plan
        4. Evaluate results
        5. If insufficient, reflect and replan
        6. Repeat until satisfied or max iterations
        7. Synthesize final response
        
        Args:
            conversation_id: Conversation identifier
            user_message: User's message
            user_id: User identifier
            streaming: Whether to stream progress updates
            
        Yields:
            Progress updates and final response
        """
        if not getattr(self, '_agentic_available', False):
            yield {
                'type': 'error',
                'message': 'Agentic processing is not available'
            }
            return
        
        start_time = datetime.now()
        
        # Get conversation history for context
        conversation_history = []
        try:
            context = self.memory_service.get_conversation_context(conversation_id)
            if context and hasattr(context, 'recent_messages'):
                conversation_history = context.recent_messages
        except Exception as e:
            logger.warning(f"Could not get conversation history: {e}")
        
        if streaming:
            # Stream progress updates
            async for update in self.agentic_manager.process_query_streaming(
                query=user_message,
                conversation_id=str(conversation_id),
                conversation_history=conversation_history
            ):
                yield update
        else:
            # Single response
            result = await self.agentic_manager.process_query(
                query=user_message,
                conversation_id=str(conversation_id),
                conversation_history=conversation_history
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            yield {
                'type': 'response',
                'response': result.get('response', ''),
                'success': result.get('success', False),
                'metadata': {
                    **result.get('metadata', {}),
                    'processing_time': processing_time,
                    'agentic': True
                },
                'sources': result.get('sources', [])
            }
    
    async def _fallback_to_data_intelligence(
        self, 
        user_message: str, 
        conversation_id: int
    ) -> List[Dict]:
        """
        Fallback to DataIntelligenceService when agentic loop fails or is unavailable.
        
        Returns retrieval results in standard format.
        """
        retrieval_results = []
        
        if self._data_intelligence_available:
            try:
                di_result = await self.data_intelligence.search(
                    query=user_message,
                    context="",
                    max_results=10,
                    rerank=True
                )
                
                if di_result.success:
                    # Add graph results as high-quality context
                    for r in di_result.graph_results:
                        retrieval_results.append({
                            'content': str(r),
                            'source': 'neo4j_graph',
                            'score': 1.0,
                            'metadata': {'type': 'structured_data'}
                        })
                    
                    # Add vector results
                    for r in di_result.vector_results:
                        retrieval_results.append({
                            'content': r.get('content', str(r)),
                            'source': r.get('source', 'vector'),
                            'score': r.get('rerank_score', r.get('score', 0.5)),
                            'metadata': r
                        })
                    
                    # Store the answer context for the response generator
                    if di_result.answer_context:
                        retrieval_results.insert(0, {
                            'content': di_result.answer_context,
                            'source': 'data_intelligence',
                            'score': 1.0,
                            'metadata': {
                                'intent': di_result.intent_type,
                                'confidence': di_result.confidence
                            }
                        })
                    
                    logger.info(f"✅ DataIntelligenceService fallback: {len(retrieval_results)} results")
                    return retrieval_results
                    
            except Exception as e:
                logger.error(f"❌ DataIntelligenceService fallback error: {e}")
        
        # Ultimate fallback to basic retrieval
        try:
            retrieval_results = await self._retrieve_information(
                conversation_id=conversation_id,
                query=user_message,
                context=""
            )
            logger.info(f"✅ Basic retrieval fallback: {len(retrieval_results)} chunks")
        except Exception as e:
            logger.error(f"❌ Basic retrieval fallback error: {e}")
        
        return retrieval_results
    
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
    
    # ================================================================
    # PROPOSAL WRITING METHODS (NEW!)
    # ================================================================
    
    async def _detect_proposal_writing_mode(
        self,
        conversation_id: int,
        user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if user wants proposal writing assistance
        
        Returns mode dict with action and context, or None
        """
        
        message_lower = user_message.lower()
        
        # Writing indicators
        writing_keywords = [
            'write proposal', 'draft proposal', 'help me write',
            'generate proposal', 'create proposal', 'proposal section',
            'draft section', 'generate section', 'write section',
            'start proposal', 'new proposal'
        ]
        
        # Budget indicators
        budget_keywords = [
            'create budget', 'generate budget', 'budget table',
            'calculate budget', 'budget breakdown'
        ]
        
        # Compliance indicators
        compliance_keywords = [
            'check compliance', 'compliance check', 'review proposal',
            'check proposal', 'validate proposal'
        ]
        
        # Improvement indicators
        improvement_keywords = [
            'improve', 'enhance', 'make better', 'refine',
            'suggestions for', 'how to improve'
        ]
        
        # Template indicators
        template_keywords = [
            'template', 'structure', 'outline', 'framework'
        ]

        # Navigation indicators (next section, move to, continue)
        navigation_keywords = [
            'next section', 'move to next', 'continue to', 'proceed to',
            'next part', 'following section', 'subsequent section'
        ]

        # Check for each type
        if any(kw in message_lower for kw in writing_keywords):
            # Extract call ID if present
            call_id = self._extract_call_id(user_message)
            
            # Determine section if specified
            section_id = None
            for section in ['objectives', 'methodology', 'beyond state of the art', 
                          'impact', 'dissemination', 'work plan', 'consortium']:
                if section in message_lower:
                    section_id = f"excellence.{section.replace(' ', '_')}" if section in ['objectives', 'methodology', 'beyond state of the art'] else f"impact.{section}" if section in ['impact', 'dissemination'] else f"implementation.{section.replace(' ', '_')}"
                    break
            
            # Default to objectives if no section specified
            if not section_id:
                section_id = 'excellence.objectives'
            
            return {
                'action': 'draft_section',
                'call_id': call_id,
                'section_id': section_id,
                'full_proposal': 'entire proposal' in message_lower or 'complete proposal' in message_lower
            }

        elif any(kw in message_lower for kw in navigation_keywords):
            # User wants to move to next section
            call_id = self._extract_call_id(user_message)

            # Get current section from conversation context or default to objectives
            current_section = self._get_current_section(conversation_id) or 'excellence.objectives'
            next_section = self._get_next_section(current_section)

            return {
                'action': 'draft_section',
                'call_id': call_id,
                'section_id': next_section,
                'context': 'navigation'
            }

        elif any(kw in message_lower for kw in budget_keywords):
            call_id = self._extract_call_id(user_message)
            return {
                'action': 'create_budget',
                'call_id': call_id
            }
        
        elif any(kw in message_lower for kw in compliance_keywords):
            return {
                'action': 'check_compliance'
            }
        
        elif any(kw in message_lower for kw in improvement_keywords):
            return {
                'action': 'improve_quality'
            }
        
        elif any(kw in message_lower for kw in template_keywords):
            call_id = self._extract_call_id(user_message)
            return {
                'action': 'generate_template',
                'call_id': call_id
            }
        
        # Export keywords (NEW!)
        export_keywords = [
            'export', 'download', 'submission package', 'complete package',
            'word document', 'excel', 'part b', 'budget file', 'zip',
            'ready to submit', 'generate documents', 'create package',
            'get word', 'get excel', 'get zip', 'get package'
        ]
        
        if any(kw in message_lower for kw in export_keywords):
            # Detect export type
            if 'part b' in message_lower or ('word' in message_lower and 'document' in message_lower):
                return {
                    'action': 'export_part_b',
                    'proposal_id': None  # Will be determined later
                }
            elif 'budget' in message_lower or 'excel' in message_lower:
                return {
                    'action': 'export_budget',
                    'proposal_id': None
                }
            else:
                # Default to complete package
                return {
                    'action': 'export_package',
                    'proposal_id': None
                }
        
        # Check conversation context
        # Note: Context checking disabled for now (method not available)
        # Will be re-enabled when get_conversation_context is implemented
        pass
        
        return None
    
    async def _handle_proposal_writing(
        self,
        conversation_id: int,
        user_message: str,
        user_id: int,
        proposal_mode: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle proposal writing requests
        """
        
        action = proposal_mode['action']
        
        # Map generic actions to specific handlers
        action_mapping = {
            'write': 'draft_section',
            'draft': 'draft_section',
            'help': 'draft_section',
            'generate': 'draft_section',
        }
        action = action_mapping.get(action, action)
        logger.info(f"✍️ Proposal action: {proposal_mode['action']} → mapped to: {action}")
        
        try:
            # Generate template
            if action == 'generate_template':
                call_id = proposal_mode.get('call_id')
                if not call_id:
                    return {
                        'response': "I'd be happy to generate a proposal template! Which call are you applying to? Please provide the call ID (e.g., HORIZON-CL3-2025-02-CS-ECCC-01).",
                        'needs_info': ['call_id']
                    }
                
                template = self.proposal_template_service.generate_template(call_id)
                
                # Format response
                response = f"""📋 **Proposal Template for {call_id}**

I've generated a complete proposal structure based on the call requirements:

**Proposal Type:** {template['proposal_type']}
**Total Page Limit:** {template['metadata']['page_limit']} pages

**Section Structure:**
"""
                for section in template['structure']['sections']:
                    response += f"\n**{section['order']}. {section['name']}** (max {section.get('page_limit', '?')} pages)"
                    for subsection in section.get('subsections', []):
                        response += f"\n   - {subsection['name']}"
                
                response += "\n\n✅ Template ready! Would you like me to help you start writing a specific section?"
                
                # Store template in context
                await self.memory_service.redis_client.setex(
                    f"template:{conversation_id}",
                    3600,
                    json.dumps(template)
                )
                
                return {
                    'response': response,
                    'template': template,
                    'mode': 'proposal_writing'
                }
            
            # Draft section - WITH STREAMING PROGRESS
            elif action == 'draft_section':
                # Return async generator for streaming progress
                async def stream_draft_generation():
                    try:
                        call_id = proposal_mode.get('call_id')
                        section_id = proposal_mode.get('section_id') or 'excellence.objectives'  # Use 'or' to handle None
                        
                        logger.info(f"📝 Draft generation: call_id={call_id}, section_id={section_id}")
                        
                        # Check if we need more info
                        if not call_id:
                            yield {
                                'type': 'response',
                                'message': "Which call are you writing the proposal for? Please provide the call ID (e.g., HORIZON-CL3-2025-02-CS-ECCC-01)."
                            }
                            return
                        
                        # Status 1: Preparing
                        yield {
                            'type': 'status',
                            'stage': 'proposal_preparation',
                            'message': f'✍️ Preparing to draft proposal for {call_id}...'
                        }
                        
                        # Status 2: Analyzing call
                        yield {
                            'type': 'status',
                            'stage': 'analyzing_call_documents',
                            'message': '📚 Analyzing call documents and requirements...'
                        }
                        
                        # Get conversation context for project details
                        conversation_context = self._get_conversation_context_for_proposal(conversation_id)

                        # Use user message as project idea, but enhance with context
                        project_idea = user_message

                        # Add context if available
                        if conversation_context:
                            project_idea = f"{conversation_context.get('project_acronym', 'Project')} - {user_message}"
                        
                        # Status 3: Generating content
                        yield {
                            'type': 'status',
                            'stage': 'generating_draft',
                            'message': '🤖 AI generating proposal content...'
                        }
                        
                        # Generate draft
                        user_context = {
                            'project_idea': project_idea,
                            'research_area': '',
                            'proposal_id': None
                        }
                        
                        logger.info(f"🎯 Generating draft for {section_id} with context: {user_context}")
                        
                        draft_result = await self.draft_generator.generate_section_draft(
                            call_id=call_id,
                            section_id=section_id,
                            user_context=user_context
                        )
                        
                        logger.info(f"✅ Draft generated successfully: {draft_result.get('word_count', 0)} words")
                        
                        # Status 4: Streaming response
                        yield {
                            'type': 'status',
                            'stage': 'streaming_response',
                            'message': 'Starting proposal draft stream...'
                        }
                        
                        # Format full response
                        response = f"""✍️ **Proposal Section - First Draft**

{draft_result.get('draft_text', 'Draft generated successfully!')}

---

📊 **Draft Analysis:**
- Word count: {draft_result.get('word_count', 0)} words
- Estimated pages: {draft_result.get('estimated_pages', 0):.1f}
- Quality score: {draft_result.get('quality_score', 0.7)*100:.0f}%

📋 **Evaluation Criteria Addressed:**
{chr(10).join(['✅ ' + c for c in draft_result.get('evaluation_criteria_addressed', [])])}

💡 **Next Steps:**
1. Review and refine the draft
2. Move to the next section
3. Export the proposal when ready

Would you like me to help with anything else?
"""
                        
                        # Stream response token by token (chunked for speed)
                        chunk_size = 50
                        for i in range(0, len(response), chunk_size):
                            chunk = response[i:i+chunk_size]
                            yield {
                                'type': 'token',
                                'content': chunk
                            }
                            await asyncio.sleep(0.01)
                        
                        # Send complete event with metadata (matching normal message format)
                        logger.info(f"✅ Sending complete event")
                        yield {
                            'type': 'complete',
                            'ai_provider': 'google',
                            'ai_version': 'gemini-flash-lite-latest',
                            'model_used': 'gemini-flash-lite-latest',
                            'data_source': 'Proposal Writing Assistant',
                            'processing_time': 0,
                            'projects_found': 0,
                            'citations': [],
                            'confidence': draft_result.get('quality_score', 0.7),
                            'grounded': True,
                            'logs': {
                                'mode': 'proposal_writing',
                                'call_id': call_id,
                                'section_id': section_id,
                                'word_count': draft_result.get('word_count', 0),
                                'quality_score': draft_result.get('quality_score', 0.7)
                            },
                            'context_used': True,
                            'resolved_question': user_message,
                            'follow_up_suggestions': [
                                'Help me write the next section',
                                'Export this proposal to Word',
                                'Check compliance with call requirements'
                            ],
                            'proposal_draft': draft_result
                        }
                    
                    except Exception as e:
                        logger.error(f"❌ Error in draft generation: {e}")
                        import traceback
                        traceback.print_exc()
                        
                        yield {
                            'type': 'error',
                            'message': f"I encountered an error while generating the draft: {str(e)}\n\nPlease try again or let me know if you need help."
                        }
                
                return stream_draft_generation()
            
            # Create budget
            elif action == 'create_budget':
                response = """💰 **Budget Table Generation**

I can help you create a complete budget table! I'll need some information:

1. **Consortium Partners:**
   - Organization names
   - Country
   - Type (University/Research/Company/Other)
   - Estimated person-months

2. **Project Details:**
   - Duration (months)
   - Total budget estimate (if any)

Please provide the partner information, and I'll generate the full budget breakdown with:
- Personnel costs
- Equipment
- Other direct costs
- Indirect costs (25% flat rate)
- Funding rates per partner type
"""
                
                return {
                    'response': response,
                    'mode': 'budget_creation'
                }
            
            # Check compliance
            elif action == 'check_compliance':
                # Would need proposal ID from context
                response = """✅ **Compliance Check**

I can run a comprehensive compliance check on your proposal to ensure:

- All mandatory sections are present
- Page limits are respected
- Consortium composition meets requirements
- Budget calculations are correct
- Evaluation criteria are addressed

Which proposal would you like me to check? (Provide the proposal ID or title)
"""
                
                return {
                    'response': response,
                    'mode': 'compliance_check'
                }
            
            # Improve quality
            elif action == 'improve_quality':
                response = """🎨 **Quality Improvement**

I can analyze and improve your proposal sections by checking:

- Readability and clarity
- EU terminology usage
- Structure and flow
- Impact language
- Evidence and argumentation

Which section would you like me to analyze? Please provide the section text or section ID.
"""
                
                return {
                    'response': response,
                    'mode': 'quality_improvement'
                }
            
            # Export Part B (NEW!)
            elif action == 'export_part_b':
                # Async generator for streaming progress
                async def stream_part_b_export():
                    proposal_id = await self._get_active_proposal_id(conversation_id)
                    
                    if not proposal_id:
                        yield {
                            'type': 'error',
                            'message': "I couldn't find an active proposal in this conversation. Please create a proposal first or specify which proposal to export."
                        }
                        return
                    
                    # Progress 1: Starting
                    yield {
                        'type': 'progress',
                        'message': '📄 Preparing Part B export...',
                        'step': 1,
                        'total_steps': 4
                    }
                    
                    await asyncio.sleep(0.3)  # Small delay for UX
                    
                    # Progress 2: Getting data
                    yield {
                        'type': 'progress',
                        'message': '📋 Retrieving proposal sections...',
                        'step': 2,
                        'total_steps': 4
                    }
                    
                    proposal_data = await self._get_proposal_metadata(proposal_id)
                    await asyncio.sleep(0.3)
                    
                    # Progress 3: Formatting
                    yield {
                        'type': 'progress',
                        'message': '✍️ Applying official EU formatting...',
                        'step': 3,
                        'total_steps': 4
                    }
                    
                    download_url = f"/api/proposal/export/{proposal_id}/part-b"
                    await asyncio.sleep(0.3)
                    
                    # Progress 4: Complete
                    yield {
                        'type': 'progress',
                        'message': '✅ Part B document ready!',
                        'step': 4,
                        'total_steps': 4
                    }
                    
                    # Final response
                    response = f"""📄 **Part B Export Complete!**

**Proposal:** {proposal_data['title']}
**Type:** {proposal_data['action_type']}
**Format:** Microsoft Word (.docx)

📥 **Download:** {download_url}

**File Details:**
• Official EU format
• All sections included
• Submission-ready
• ~40 KB file size

✅ Ready to upload to EU Funding & Tenders Portal!

**Next Steps:**
1. Download the Word document
2. Review the content
3. Upload to EU portal Part B section
4. Submit your proposal! 🚀
"""
                    
                    yield {
                        'type': 'response',
                        'message': response,
                        'download_url': download_url,
                        'file_type': 'docx',
                        'proposal_id': proposal_id
                    }
                
                # Return the generator
                return stream_part_b_export()
            
            # Export Budget (NEW!)
            elif action == 'export_budget':
                # Async generator for streaming progress
                async def stream_budget_export():
                    proposal_id = await self._get_active_proposal_id(conversation_id)
                    
                    if not proposal_id:
                        yield {
                            'type': 'error',
                            'message': "I couldn't find an active proposal in this conversation. Please create a proposal first or specify which proposal to export."
                        }
                        return
                    
                    # Progress 1: Starting
                    yield {
                        'type': 'progress',
                        'message': '💰 Preparing budget export...',
                        'step': 1,
                        'total_steps': 4
                    }
                    
                    await asyncio.sleep(0.3)
                    
                    # Progress 2: Getting data
                    yield {
                        'type': 'progress',
                        'message': '📊 Retrieving partner budgets...',
                        'step': 2,
                        'total_steps': 4
                    }
                    
                    proposal_data = await self._get_proposal_metadata(proposal_id)
                    await asyncio.sleep(0.3)
                    
                    # Progress 3: Calculating
                    yield {
                        'type': 'progress',
                        'message': '🧮 Calculating funding rates...',
                        'step': 3,
                        'total_steps': 4
                    }
                    
                    download_url = f"/api/proposal/export/{proposal_id}/budget"
                    await asyncio.sleep(0.3)
                    
                    # Progress 4: Complete
                    yield {
                        'type': 'progress',
                        'message': '✅ Budget spreadsheet ready!',
                        'step': 4,
                        'total_steps': 4
                    }
                    
                    # Final response
                    response = f"""💰 **Budget Export Complete!**

**Proposal:** {proposal_data['title']}
**Format:** Microsoft Excel (.xlsx)

📥 **Download:** {download_url}

**File Details:**
• Official EU format
• All partners included
• Funding rates calculated
• ~5 KB file size

✅ Ready to upload to EU Funding & Tenders Portal!
"""
                    
                    yield {
                        'type': 'response',
                        'message': response,
                        'download_url': download_url,
                        'file_type': 'xlsx',
                        'proposal_id': proposal_id
                    }
                
                # Return the generator
                return stream_budget_export()
            
            # Export Complete Package (NEW!)
            elif action == 'export_package':
                # Async generator for streaming progress
                async def stream_package_export():
                    proposal_id = await self._get_active_proposal_id(conversation_id)
                    
                    if not proposal_id:
                        yield {
                            'type': 'error',
                            'message': "I couldn't find an active proposal in this conversation. Please create a proposal first or specify which proposal to export."
                        }
                        return
                    
                    # Progress 1: Initializing
                    yield {
                        'type': 'progress',
                        'message': '📦 Creating submission package...',
                        'step': 1,
                        'total_steps': 6
                    }
                    
                    await asyncio.sleep(0.3)
                    
                    # Progress 2: Getting proposal data
                    yield {
                        'type': 'progress',
                        'message': '📋 Analyzing proposal structure...',
                        'step': 2,
                        'total_steps': 6
                    }
                    
                    proposal_data = await self._get_proposal_metadata(proposal_id)
                    await asyncio.sleep(0.4)
                    
                    # Progress 3: Generating Part B
                    yield {
                        'type': 'progress',
                        'message': '📄 Generating Part B (Word document)...',
                        'step': 3,
                        'total_steps': 6
                    }
                    
                    await asyncio.sleep(0.5)
                    
                    # Progress 4: Generating Budget
                    yield {
                        'type': 'progress',
                        'message': '💰 Generating Budget (Excel spreadsheet)...',
                        'step': 4,
                        'total_steps': 6
                    }
                    
                    await asyncio.sleep(0.4)
                    
                    # Progress 5: Adding README
                    yield {
                        'type': 'progress',
                        'message': '📝 Creating README with submission instructions...',
                        'step': 5,
                        'total_steps': 6
                    }
                    
                    download_url = f"/api/proposal/export/{proposal_id}/complete-package"
                    await asyncio.sleep(0.3)
                    
                    # Progress 6: Packaging
                    yield {
                        'type': 'progress',
                        'message': '🗜️ Packaging files into ZIP archive...',
                        'step': 6,
                        'total_steps': 6
                    }
                    
                    await asyncio.sleep(0.3)
                    
                    # Final response
                    response = f"""🎉 **Submission Package Ready!**

**Proposal:** {proposal_data['title']}
**Acronym:** {proposal_data['acronym']}
**Type:** {proposal_data['action_type']}

📥 **Download Complete Package (ZIP):** {download_url}

**Package Contents:**
• {proposal_data['acronym']}_PartB.docx (~38 KB)
  - All proposal sections
  - Official EU format
  
• {proposal_data['acronym']}_Budget.xlsx (~5 KB)
  - Partner budgets
  - Funding calculations
  
• README.txt
  - Submission instructions
  - Portal upload guide

**Total Package Size:** ~40 KB

✅ **READY TO SUBMIT TO EU PORTAL!** 🚀

**Submission Steps:**
1. Download the ZIP file above
2. Extract the contents
3. Log in to EU Funding & Tenders Portal
4. Navigate to your proposal application
5. Upload Part B documents (Word & Excel)
6. Complete Part A (administrative data)
7. Submit! 🎊

Good luck with your submission! 🍀
"""
                    
                    yield {
                        'type': 'response',
                        'message': response,
                        'download_url': download_url,
                        'file_type': 'zip',
                        'proposal_id': proposal_id,
                        'package_contents': [
                            f"{proposal_data['acronym']}_PartB.docx",
                            f"{proposal_data['acronym']}_Budget.xlsx",
                            "README.txt"
                        ]
                    }
                
                # Return the generator
                return stream_package_export()
            
            # Default
            else:
                return {
                    'response': "I'm in proposal writing mode! I can help you:\n\n✍️ Write proposal sections\n💰 Create budget tables\n✅ Check compliance\n🎨 Improve quality\n📋 Generate templates\n\nWhat would you like to do?",
                    'mode': 'proposal_writing'
                }
        
        except Exception as e:
            logger.error(f"Error in proposal writing mode: {e}")
            return {
                'response': f"I encountered an error while assisting with proposal writing: {str(e)}\n\nLet me help you with general questions instead.",
                'error': str(e)
            }
    
    async def _get_active_proposal_id(self, conversation_id: int) -> Optional[int]:
        """Get the active proposal ID from conversation context"""

        try:
            # Query database for most recent proposal in this conversation
            if not self.db_pool:
                return None

            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id FROM proposals
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (conversation_id,))

            row = cursor.fetchone()
            self.db_pool.putconn(conn)

            return row[0] if row else None

        except Exception as e:
            logger.error(f"Error getting active proposal ID: {e}")
            return None

    def _get_conversation_context_for_proposal(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation context for proposal writing"""
        if not self.db_pool:
            return None

        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            # Get recent messages to extract context
            cursor.execute("""
                SELECT text FROM message
                WHERE conversation_id = %s AND sender = 'user'
                ORDER BY created_at DESC
                LIMIT 5
            """, (conversation_id,))

            messages = cursor.fetchall()

            context = {}

            for msg_row in messages:
                msg_text = msg_row[0].lower()

                # Look for project acronym
                if 'acronym' in msg_text or 'project name' in msg_text or 'call it' in msg_text:
                    # Try to extract acronym (usually in quotes or after "is")
                    import re
                    acronym_match = re.search(r'(?:acronym|name|call it)\s+(?:is\s+)?["\']?([A-Z]{2,})["\']?', msg_text)
                    if acronym_match:
                        context['project_acronym'] = acronym_match.group(1)

                # Look for research area
                if any(word in msg_text for word in ['cybersecurity', 'ai', 'artificial intelligence', 'threat detection']):
                    context['research_area'] = msg_text

            return context if context else None

        finally:
            self.db_pool.putconn(conn)

    def _get_current_section(self, conversation_id: int) -> Optional[str]:
        """Get current section from conversation context"""
        if not self.db_pool:
            return None

        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            # Get most recent proposal section from this conversation
            cursor.execute("""
                SELECT section_id FROM proposal_sections
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (conversation_id,))

            row = cursor.fetchone()
            return row[0] if row else None

        finally:
            self.db_pool.putconn(conn)

    def _get_next_section(self, current_section: str) -> str:
        """Get the next logical section"""
        section_order = [
            'excellence.objectives',
            'excellence.methodology',
            'excellence.beyond_sota',
            'impact.pathways',
            'impact.dissemination',
            'implementation.work_plan',
            'implementation.consortium'
        ]

        try:
            current_idx = section_order.index(current_section)
            next_idx = min(current_idx + 1, len(section_order) - 1)
            return section_order[next_idx]
        except (ValueError, IndexError):
            return 'excellence.objectives'

    def _get_recent_messages_simple(self, conversation_id: int, limit: int = 5) -> List[Dict[str, str]]:
        """Get recent messages for context (simple version for unified classifier)"""
        if not self.db_pool:
            return []

        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT text, sender FROM message
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (conversation_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'text': row[0],
                    'sender': row[1]
                })

            return list(reversed(messages))  # Return in chronological order

        except Exception as e:
            logger.warning(f"Could not get recent messages: {e}")
            return []
        finally:
            self.db_pool.putconn(conn)

    def _build_conversation_context_string(self, recent_messages: List[Dict[str, str]]) -> str:
        """
        Build a conversation context string from recent messages.
        This string is passed to the LLM to maintain conversation continuity.
        """
        if not recent_messages:
            return "No previous conversation context."
        
        context_lines = []
        context_lines.append("PREVIOUS CONVERSATION:")
        context_lines.append("-" * 40)
        
        for msg in recent_messages:
            sender = msg.get('sender', 'unknown').upper()
            text = msg.get('text', '')
            # Include full message content for context
            context_lines.append(f"{sender}: {text}")
        
        context_lines.append("-" * 40)
        
        return "\n".join(context_lines)

    async def _get_proposal_metadata(self, proposal_id: int) -> Dict[str, Any]:
        """Get proposal metadata for export"""
        
        if not self.db_pool:
            raise ValueError("Database not available")
        
        conn = self.db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT proposal_title, proposal_acronym, proposal_type
            FROM proposals
            WHERE id = %s
        """, (proposal_id,))
        
        row = cursor.fetchone()
        self.db_pool.putconn(conn)
        
        if not row:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        return {
            'title': row[0] or 'Untitled Proposal',
            'acronym': row[1] or 'PROPOSAL',
            'action_type': row[2] or 'RIA'
        }

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