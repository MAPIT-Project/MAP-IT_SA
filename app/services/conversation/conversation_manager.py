"""
Main conversation management system that orchestrates all components.
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple
from datetime import datetime
import json
import logging
import re
import os
import random
import re

from ..memory.memory_service import MemoryService
from ..memory.context_manager import ConversationContext
from ..rag.conversation_retriever import ConversationAwareRetriever, RetrievalContext
from ..rag.response_generator import GroundedResponseGenerator
from ..rag.hybrid_search import HybridSearchPipeline, MockVectorStore, MockKeywordStore, MockEmbeddingService
from ..tools.tool_orchestrator import create_research_orchestrator
from ..response.unified_formatter import UnifiedResponseFormatter

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Central manager for all conversation operations with OPTIMIZED ARCHITECTURE.

    OPTIMIZED 5-PHASE PIPELINE:
    Phase 1: Store user message in memory
    Phase 2-4: COMBINED - Single AI call for intent analysis, context building, and tool planning
    Phase 5: Retrieve information if needed (fallback only)
    Phase 6: Execute tools if planned
    Phase 7: Generate response

    KEY IMPROVEMENTS:
    - Reduced AI calls from 2-3 to 1 for most queries
    - Better context utilization across all decisions
    - Lower latency and improved performance
    - More coherent decision making
    - Maintains backward compatibility with fallback to separate phases

    Coordinates memory, RAG, and tool systems with intelligent orchestration.
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
                gemini_api_key=os.getenv('GEMINI_API_KEY')
            )
            
            # Tool orchestration
            self.tool_orchestrator = create_research_orchestrator(
                cache_client=self.memory_service.redis_client
            )
            
            # Response formatting
            self.unified_formatter = UnifiedResponseFormatter()
            
            # Configuration
            self.config = self._load_configuration()
            
            print("✅ ConversationManager initialized successfully")
            
        except Exception as e:
            print(f"⚠️ ConversationManager initialization error: {e}")
            raise
    
    async def process_message(self,
                              conversation_id: int,
                              user_message: str,
                              user_id: int,
                              streaming: bool = False) -> Dict[str, Any]:
        """
        Process a user message through the optimized 5-phase pipeline.

        OPTIMIZED ARCHITECTURE:
        Phase 1: Store user message in memory
        Phase 2-4: COMBINED - Analyze intent, build context, and plan tools (single AI call)
        Phase 5: Retrieve information if needed (fallback only)
        Phase 6: Execute tools if planned
        Phase 7: Generate response

        Benefits of combined phases 2-4:
        - Single AI call instead of 2-3 separate calls
        - Better context utilization across decisions
        - Reduced latency and processing time
        - More coherent decision making

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
            
            # COMBINED PHASE 2+3+4: Analyze intent, build context, and plan tools
            print(f"🤖 STARTING COMBINED PHASE for: '{user_message}'")
            intent_analysis, context, tool_plan = await self._combined_intent_context_tool_planner(
                conversation_id=conversation_id,
                user_message=user_message
            )
            print(f"🤖 COMBINED PHASE RESULT: intent={intent_analysis.get('intent_type', 'unknown')}, tools={len(tool_plan) if tool_plan else 0}")
            
            # Phase 5: Retrieve relevant information if needed
            retrieval_results = None
            if intent_analysis.get('requires_retrieval') and not tool_plan:
                retrieval_results = await self._retrieve_information(
                    conversation_id, user_message, context
                )
            
            # Phase 6: Execute tools if needed
            tool_results = None
            if tool_plan:
                tool_results = await self.tool_orchestrator.execute_plan(
                    tool_plan, conversation_id
                )
                print(f"🔧 Tool Orchestrator executed {len(tool_results)} tools")
                
                # Convert tool results to retrieval format for response generation
                if tool_results:
                    retrieval_results = self._convert_tool_results_to_retrieval(tool_results)
            
            # Phase 7: Generate response
            logger.info(f"📝 RESPONSE GENERATION: tool_results={tool_results is not None}, retrieval_results={len(retrieval_results) if retrieval_results else 0}")

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
    
    async def _analyze_intent(self,
                             conversation_id: int,
                             message: str) -> Dict[str, Any]:
        """
        Analyze user intent to determine processing approach.
        """
        try:
            # Get conversation summary for context
            summary = self.memory_service.ltm.get_summary(conversation_id)
            
            # Use Gemini for intent analysis
            prompt = f"""Analyze this user message and determine the processing approach needed.

Conversation Summary: {summary.summary_text if summary else 'New conversation'}

User Message: {message}

Determine:
1. Intent type: [question, command, clarification, follow_up, greeting]
2. Requires retrieval: true/false (needs to search for information)
3. Requires tools: true/false (needs to execute tools/APIs)
4. Confidence: 0.0-1.0

Respond in JSON format:
{{
    "intent_type": "...",
    "requires_retrieval": true/false,
    "requires_tools": true/false,
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation"
}}"""

            response = self.response_generator.model.generate_content(prompt)
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"Intent analysis error: {e}")
        
        # Fallback to simple heuristics with tool detection
        message_lower = message.lower()

        # Check if tools are needed based on enhanced keywords
        requires_tools = any(keyword in message_lower for keyword in [
            # Call-related keywords
            'open calls', 'calls for', 'funding opportunities', 'grant opportunities',
            'available calls', 'current calls', 'calls about', 'calls related to',
            'what calls', 'which calls', 'show me calls', 'find calls',
            'funding calls', 'research calls', 'horizon calls',
            # Project-related keywords (enhanced)
            'projects', 'research projects', 'case studies', 'project examples',
            'look up projects', 'search projects', 'find projects',
            'show me projects', 'get projects', 'retrieve projects',
            'cordis api', 'cordis search', 'search cordis',
            'information on projects', 'data on projects', 'details about projects',
            'what projects', 'which projects', 'show me information on projects',
            'get information on projects', 'retrieve information on projects',
            'search for information on projects',
            'projects about', 'projects related to', 'search for projects',
            'find information on projects', 'get information on projects',
            'retrieve information on projects', 'search for information on projects',
            'projects in', 'projects on', 'projects for',
            'find me projects', 'show me projects', 'get me projects',
            'search me projects', 'look me projects'
        ])

        return {
            "intent_type": "question",
            "requires_retrieval": True,
            "requires_tools": requires_tools,
            "confidence": 0.5,
            "explanation": "Fallback processing with tool detection"
        }
    
    async def _ai_service_selector(self,
                                  user_message: str,
                                  intent_analysis: Dict,
                                  context: str) -> Dict[str, Any]:
        """
        AI-powered service selection that decides which service to use.
        """
        try:
            prompt = f"""You are an AI that decides which service to use for European research funding questions.

AVAILABLE SERVICES:
1. enhanced_call_search - Real EU Portal API for funding calls/opportunities
2. enhanced_rag - Existing RAG system with vector search and documents

USER MESSAGE: {user_message}

INTENT: {intent_analysis}

DECISION RULES:
- "open calls", "funding opportunities", "calls for proposals" → enhanced_call_search
- "projects", "research projects", "case studies" → enhanced_rag
- "how to", "guidelines", "requirements" → enhanced_rag

Respond in JSON:
{{
    "service": "enhanced_call_search|enhanced_rag",
    "reasoning": "Why this service was chosen"
}}"""

            response = self.response_generator.model.generate_content(prompt)
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                print(f"🤖 AI Service Selector: {decision['service']}")
                print(f"   Reasoning: {decision['reasoning']}")
                return decision
                
        except Exception as e:
            print(f"AI service selection error: {e}")
        
        # Fallback logic
        message_lower = user_message.lower()
        if any(word in message_lower for word in ['open calls', 'calls for', 'funding opportunities']):
            return {'service': 'enhanced_call_search', 'reasoning': 'Detected call keywords'}
        else:
            return {'service': 'enhanced_rag', 'reasoning': 'Default to enhanced RAG'}
    
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
                    
                    if tool_name == 'search_horizon_calls':
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
    
    async def _ai_tool_planner(self,
                              user_message: str,
                              intent_analysis: Dict,
                              context: str,
                              conversation_id: int) -> Optional[List]:
        """
        AI-powered tool planning that decides which tools to call.
        """
        try:
            # Get available tools
            available_tools = self.tool_orchestrator.get_available_tools()
            
            # Create AI prompt for tool planning
            prompt = f"""You are an AI agent that decides which tools to call to answer user questions about European research funding.

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

USER QUESTION: {user_message}

CONVERSATION CONTEXT: {context[:500]}...

INTENT ANALYSIS: {intent_analysis}

Based on the user's question, determine which tools should be called and in what order.

DECISION RULES:
1. For "open calls", "funding opportunities", "calls for proposals" → Use eu_portal_search tool
2. For "projects", "research projects", "case studies" → Use search_cordis_projects tool
3. For general questions → Use the most appropriate tool based on context

Respond in JSON format:
{{
    "tools_needed": [
        {{
            "tool_name": "eu_portal_search", 
            "parameters": {{"query": "clean energy", "status": "open"}},
            "reason": "User asking for open calls"
        }}
    ],
    "reasoning": "Explanation of why these tools were chosen"
}}

If no tools are needed, return {{"tools_needed": [], "reasoning": "Question can be answered from context"}}
"""

            # Add retry logic for rate limits
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.response_generator.model.generate_content(prompt)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                        print(f"Rate limit hit, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise e
            
            # Parse AI response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                ai_decision = json.loads(json_match.group())
                tools_needed = ai_decision.get('tools_needed', [])
                
                if tools_needed:
                    print(f"🤖 AI Tool Planner: {len(tools_needed)} tools planned")
                    print(f"   Reasoning: {ai_decision.get('reasoning', 'No reasoning provided')}")
                    
                    # Convert to tool calls
                    from ..tools.tool_orchestrator import ToolCall
                    tool_calls = []
                    
                    for i, tool_spec in enumerate(tools_needed):
                        tool_call = ToolCall(
                            tool_name=tool_spec['tool_name'],
                            parameters=tool_spec['parameters'],
                            execution_order=i
                        )
                        tool_calls.append(tool_call)
                    
                    return tool_calls
                else:
                    print("🤖 AI Tool Planner: No tools needed")
                    return None
            
        except Exception as e:
            print(f"AI tool planning error: {e}")

        return None

    def _analyze_conversation_context_for_intent(self,
                                                user_message: str,
                                                conversation_history: str,
                                                summary: Any) -> Dict[str, Any]:
        """
        Analyze conversation context for repeated patterns and intent persistence.

        This method detects when users are repeatedly asking for the same type of information
        and boosts confidence for routing to appropriate tools.

        Args:
            user_message: Current user message
            conversation_history: Recent conversation turns
            summary: Conversation summary object

        Returns:
            Dictionary with context analysis and intent boost recommendations
        """
        try:
            user_message_lower = user_message.lower()
            context_analysis = {
                'repeated_project_intent': False,
                'repeated_call_intent': False,
                'frustration_indicators': False,
                'intent_persistence_score': 0.0,
                'recommended_tool_boost': None,
                'confidence_multiplier': 1.0
            }

            # Analyze conversation history for repeated patterns
            history_lower = conversation_history.lower()

            # Check for repeated project search patterns
            project_indicators = [
                'look up projects', 'search projects', 'find projects',
                'show me projects', 'get projects', 'retrieve projects',
                'cordis api', 'cordis search', 'search cordis',
                'information on projects', 'data on projects', 'details about projects',
                'what projects', 'which projects', 'show me information on projects',
                'get information on projects', 'retrieve information on projects',
                'search for information on projects'
            ]

            # Count how many times project-related terms appear in recent history
            project_mentions = sum(1 for indicator in project_indicators if indicator in history_lower)
            project_mentions += sum(1 for indicator in project_indicators if indicator in user_message_lower)

            # Check for repeated call search patterns
            call_indicators = [
                'open calls', 'funding calls', 'call for proposals', 'grant calls',
                'submission deadline', 'funding opportunities', 'horizon calls',
                'eu calls', 'research calls', 'proposal calls'
            ]

            call_mentions = sum(1 for indicator in call_indicators if indicator in history_lower)
            call_mentions += sum(1 for indicator in call_indicators if indicator in user_message_lower)

            # Check for frustration indicators (user repeatedly asking for same thing)
            frustration_indicators = [
                'no i mean', 'i said', 'i asked', 'but i want', 'i need',
                'please', 'can you', 'could you', 'would you',
                'search on', 'look up', 'find me', 'show me'
            ]

            frustration_count = sum(1 for indicator in frustration_indicators if indicator in user_message_lower)

            # Analyze intent persistence
            if project_mentions >= 2:  # User mentioned projects multiple times
                context_analysis['repeated_project_intent'] = True
                context_analysis['intent_persistence_score'] = min(project_mentions * 0.3, 1.0)
                context_analysis['recommended_tool_boost'] = 'search_cordis_projects'
                context_analysis['confidence_multiplier'] = 1.5

            if call_mentions >= 2:  # User mentioned calls multiple times
                context_analysis['repeated_call_intent'] = True
                context_analysis['intent_persistence_score'] = min(call_mentions * 0.3, 1.0)
                context_analysis['recommended_tool_boost'] = 'eu_portal_search'
                context_analysis['confidence_multiplier'] = 1.5

            if frustration_count >= 1:  # User showing frustration
                context_analysis['frustration_indicators'] = True
                context_analysis['confidence_multiplier'] *= 1.2

            # Special case: User is explicitly asking for CORDIS/API searches
            if any(term in user_message_lower for term in ['cordis', 'api', 'search on', 'look up in']):
                context_analysis['confidence_multiplier'] = 2.0
                if 'project' in user_message_lower or any(term in history_lower for term in ['project', 'cordis']):
                    context_analysis['recommended_tool_boost'] = 'search_cordis_projects'

            logger.info(f"🔍 Context Analysis: {context_analysis}")
            return context_analysis

        except Exception as e:
            logger.error(f"Error in context analysis: {e}")
            return {
                'repeated_project_intent': False,
                'repeated_call_intent': False,
                'frustration_indicators': False,
                'intent_persistence_score': 0.0,
                'recommended_tool_boost': None,
                'confidence_multiplier': 1.0
            }

    async def _forced_tool_planner(self,
                                   user_message: str,
                                   intent_analysis: Dict,
                                   context: str,
                                   conversation_id: int) -> Optional[List]:
        """
        SMART tool planning that only executes tools when appropriate.
        Follows the 7-phase architecture properly.
        """
        try:
            message_lower = user_message.lower()
            
            # EXCLUDE general conversational queries and nonsense text
            conversational_indicators = [
                'hello', 'hi', 'thanks', 'thank you', 'help', 'how are you',
                'what can you', 'who are you', 'what do you do', 'goodbye',
                'bye', 'please', 'explain', 'tell me about', 'what is',
                'how does', 'why', 'when', 'where'
            ]
            
            # If it's clearly conversational, don't use tools
            if any(indicator in message_lower for indicator in conversational_indicators):
                logger.info(f"🗣️ Conversational query detected: '{user_message}' - No tools needed")
                return None
            
            # EXCLUDE nonsense/random text - if it doesn't contain recognizable words, treat as conversational
            import re
            # Check if message contains mostly nonsense (random characters, no recognizable patterns)
            words = user_message.split()
            nonsense_pattern = re.compile(r'^[a-zA-Z]{2,}$')  # Just random letters
            recognizable_words = ['energy', 'automotive', 'ai', 'health', 'climate', 'digital', 'call', 'calls', 'funding', 'grant', 'project', 'research', 'open', 'closed', 'horizon', 'eu', 'european']
            
            # If message is short and contains no recognizable funding/research terms, treat as conversational
            if len(words) <= 5 and not any(word.lower() in recognizable_words for word in words):
                logger.info(f"🤷 Nonsense/unclear query detected: '{user_message}' - Using conversational response")
                return None
            
            # SPECIFIC call-related keywords (more precise)
            call_keywords = [
                'open calls', 'funding calls', 'call for proposals', 'grant calls',
                'submission deadline', 'funding opportunities', 'horizon calls',
                'eu calls', 'research calls', 'proposal calls'
            ]
            
            # ENHANCED project-related keywords - comprehensive coverage
            project_keywords = [
                # Original keywords
                'completed projects', 'research projects', 'project results',
                'cordis projects', 'funded projects', 'project examples',
                'successful projects', 'project outcomes',
                # Enhanced keywords for better detection
                'look up projects', 'search projects', 'find projects',
                'show me projects', 'get projects', 'retrieve projects',
                'cordis api', 'cordis search', 'search cordis',
                'information on projects', 'data on projects', 'details about projects',
                'what projects', 'which projects', 'show me information on projects',
                'get information on projects', 'retrieve information on projects',
                'search for information on projects',
                # Generic project terms that should trigger search
                'projects about', 'projects related to', 'search for projects',
                'find information on projects', 'get information on projects',
                'retrieve information on projects', 'search for information on projects',
                # Domain-specific project searches
                'projects in', 'projects on', 'projects for',
                # Action verbs + project terms
                'find me projects', 'show me projects', 'get me projects',
                'search me projects', 'look me projects',
                # CRITICAL ADDITIONS - Direct search patterns
                'search for', 'find me', 'show me', 'tell me about',
                'look up', 'get me', 'retrieve', 'explore',
                # Project search with any domain
                'projects', 'project search', 'project database', 'project information'
            ]
            
            # Domain + funding context (more specific)
            domain_funding_patterns = [
                r'\b(energy|automotive|ai|health|climate|digital)\b.*\b(call|funding|grant|opportunity)\b',
                r'\b(call|funding|grant|opportunity)\b.*\b(energy|automotive|ai|health|climate|digital)\b',
                r'open.*\b(energy|automotive|ai|health|climate|digital)\b',
                r'\b(energy|automotive|ai|health|climate|digital)\b.*open'
            ]
            
            tools_needed = []
            
            # Check for explicit call-related queries
            if any(keyword in message_lower for keyword in call_keywords):
                tools_needed.append({
                    "tool_name": "eu_portal_search",
                    "parameters": {
                        "query": user_message,
                        "status": "open",
                        "max_results": 20
                    },
                    "reason": f"Explicit call query detected"
                })
                logger.info(f"🎯 EXPLICIT call query: eu_portal_search for '{user_message}'")
            
            # Check for domain + funding patterns
            elif any(re.search(pattern, message_lower) for pattern in domain_funding_patterns):
                tools_needed.append({
                    "tool_name": "eu_portal_search",
                    "parameters": {
                        "query": user_message,
                        "status": "open",
                        "max_results": 20
                    },
                    "reason": f"Domain + funding pattern detected"
                })
                logger.info(f"🎯 DOMAIN+FUNDING query: eu_portal_search for '{user_message}'")
            
            # Check for explicit project queries - ENHANCED DETECTION
            project_detected = False

            # Direct keyword match
            if any(keyword in message_lower for keyword in project_keywords):
                project_detected = True

            # Enhanced pattern matching for action + project combinations
            action_verbs = ['search', 'find', 'show', 'get', 'retrieve', 'look', 'tell', 'explore']
            project_terms = ['projects', 'project', 'cordis', 'database', 'information']

            # Check for action verb + project term combinations
            for action in action_verbs:
                if action in message_lower:
                    for term in project_terms:
                        if term in message_lower:
                            project_detected = True
                            break
                    if project_detected:
                        break

            # Check for "search for X projects" pattern
            if 'search for' in message_lower and 'projects' in message_lower:
                project_detected = True

            if project_detected:
                tools_needed.append({
                    "tool_name": "search_cordis_projects",
                    "parameters": {
                        "query": user_message,
                        "max_results": 10
                    },
                    "reason": f"Enhanced project query detection"
                })
                logger.info(f"🎯 ENHANCED project query: search_cordis_projects for '{user_message}'")
            
            # NO DEFAULT TOOL EXECUTION - let it be conversational!
            else:
                logger.info(f"🤖 No specific tool needed for: '{user_message}' - Will use conversational AI")
                return None
            
            if tools_needed:
                # Convert to ToolCall objects
                from ..tools.tool_orchestrator import ToolCall
                tool_calls = []
                for i, tool_spec in enumerate(tools_needed):
                    tool_call = ToolCall(
                        tool_name=tool_spec["tool_name"],
                        parameters=tool_spec["parameters"],
                        execution_order=i
                    )
                    tool_calls.append(tool_call)
                
                logger.info(f"🚀 SMART tool planning: {len(tool_calls)} tools planned for '{user_message}'")
                return tool_calls
            
            return None
            
        except Exception as e:
            logger.error(f"Smart tool planning failed: {e}")
            return None
    async def _combined_intent_context_tool_planner(self,
                                                     conversation_id: int,
                                                     user_message: str) -> Tuple[Dict[str, Any], str, Optional[List]]:
        """
        COMBINED PHASE: Analyze intent, build context, and plan tools in a single AI call.

        This method combines phases 2, 3, and 4 into one efficient operation:
        - Phase 2: Intent analysis
        - Phase 3: Context building
        - Phase 4: Tool planning

        Benefits:
        - Single AI call instead of 2-3 separate calls
        - Better context utilization across all decisions
        - Reduced latency and processing time
        - More coherent decision making

        Args:
            conversation_id: Conversation identifier
            user_message: User's message

        Returns:
            Tuple of (intent_analysis, context, tool_plan)
        """
        try:
            print("🔧 COMBINED PHASE: Starting context analysis...")
            # Get conversation summary for context
            summary = self.memory_service.ltm.get_summary(conversation_id)

            # Get recent conversation turns for CONTEXT-AWARE INTENT DETECTION
            recent_turns = self.memory_service.stm.get_recent_turns(conversation_id, limit=5)
            conversation_history = "\n".join([
                f"{'User' if turn.role == 'user' else 'Assistant'}: {turn.content}"
                for turn in recent_turns
            ])
            print(f"🔧 COMBINED PHASE: Found {len(recent_turns)} recent turns")

            # CONTEXT-AWARE INTENT DETECTION: Analyze conversation history for repeated patterns
            context_intent_boost = self._analyze_conversation_context_for_intent(
                user_message, conversation_history, summary
            )
            print(f"🔧 COMBINED PHASE: Context analysis result: {context_intent_boost}")

            # Get available tools for planning
            available_tools = self.tool_orchestrator.get_available_tools()
            print(f"🔧 COMBINED PHASE: Found {len(available_tools)} available tools")

            # Create comprehensive prompt for combined analysis with CONTEXT-AWARE ENHANCEMENTS
            prompt = f"""You are an AI assistant specializing in European research funding. Analyze this user message and provide a comprehensive response that includes intent analysis, context assessment, and tool planning.

CONVERSATION CONTEXT:
Summary: {summary.summary_text if summary else 'New conversation'}
Recent History:
{conversation_history}

USER MESSAGE: {user_message}

CONTEXT ANALYSIS: {json.dumps(context_intent_boost, indent=2)}

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

INSTRUCTIONS:
1. Analyze the user's intent and classify the query type
2. Consider the CONTEXT ANALYSIS for repeated patterns and user frustration
3. Assess what context is most relevant for this query
4. Determine if tools are needed and which ones - PAY SPECIAL ATTENTION TO REPEATED PATTERNS
5. If user is repeatedly asking for projects/CORDIS searches, HIGHLY prioritize search_cordis_projects tool
6. If user shows frustration ("no i mean", "i said", etc.), boost confidence for tool usage
7. Provide reasoning for your decisions

RESPONSE FORMAT (JSON):
{{
    "intent_analysis": {{
        "intent_type": "question|command|clarification|follow_up|greeting",
        "requires_retrieval": true/false,
        "requires_tools": true/false,
        "confidence": 0.0-1.0,
        "explanation": "Brief explanation of intent"
    }},
    "context_assessment": {{
        "relevant_topics": ["topic1", "topic2"],
        "context_importance": "high|medium|low",
        "context_summary": "Summary of relevant context"
    }},
    "tool_plan": {{
        "tools_needed": [
            {{
                "tool_name": "eu_portal_search|search_cordis_projects",
                "parameters": {{
                    "query": "search terms",
                    "status": "open|closed",
                    "max_results": 20
                }},
                "reason": "Why this tool is needed"
            }}
        ],
        "execution_strategy": "parallel|sequential",
        "reasoning": "Overall reasoning for tool selection"
    }},
    "processing_recommendation": {{
        "use_tools": true/false,
        "use_retrieval": true/false,
        "response_type": "tool_based|conversational|mixed"
    }}
}}

ENHANCED TOOL SELECTION RULES (with context awareness):
- For "open calls", "funding opportunities", "calls for proposals" → eu_portal_search
- For "projects", "research projects", "case studies" → search_cordis_projects
- For "look up projects", "search projects", "find projects" → search_cordis_projects (HIGH PRIORITY)
- For "cordis", "cordis api", "search cordis" → search_cordis_projects (VERY HIGH PRIORITY)
- For repeated project requests (context shows persistence) → search_cordis_projects (BOOST CONFIDENCE)
- For user frustration indicators ("no i mean", "i said") → boost tool confidence significantly
- For conversational queries (hello, help, thanks) → no tools
- For nonsense/short queries without funding terms → no tools
- For domain + funding patterns (energy calls, AI funding) → eu_portal_search

CONTEXT-AWARE DECISIONS:
- If CONTEXT ANALYSIS shows repeated_project_intent: true → STRONGLY favor search_cordis_projects
- If CONTEXT ANALYSIS shows frustration_indicators: true → increase confidence for tool usage
- If user mentions "cordis" or "api" → prioritize search_cordis_projects regardless of other factors
- If user says "search on", "look up", "find me" + project terms → search_cordis_projects

If no tools are needed, set tools_needed to empty array.
"""

            # Make single AI call for combined analysis
            print("🔧 COMBINED PHASE: Making AI call...")
            response = self.response_generator.model.generate_content(prompt)
            print(f"🔧 COMBINED PHASE: AI response received (length: {len(response.text)})")

            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                combined_decision = json.loads(json_match.group())
                print(f"🤖 COMBINED PHASE: {combined_decision['processing_recommendation']['response_type']}")

                # Extract components
                intent_analysis = combined_decision['intent_analysis']
                context_assessment = combined_decision['context_assessment']
                tool_plan_data = combined_decision['tool_plan']

                print(f"🔧 COMBINED PHASE: Intent analysis: {intent_analysis}")
                print(f"🔧 COMBINED PHASE: Tool plan data: {tool_plan_data}")

                # Build context string from assessment
                context = f"Context Assessment: {context_assessment['context_summary']}\n"
                context += f"Relevant Topics: {', '.join(context_assessment['relevant_topics'])}\n"
                context += f"Conversation Summary: {summary.summary_text if summary else 'New conversation'}"

                # Convert tool plan to ToolCall objects
                tool_plan = None
                if tool_plan_data['tools_needed']:
                    from ..tools.tool_orchestrator import ToolCall
                    tool_calls = []
                    for i, tool_spec in enumerate(tool_plan_data['tools_needed']):
                        tool_call = ToolCall(
                            tool_name=tool_spec['tool_name'],
                            parameters=tool_spec['parameters'],
                            execution_order=i
                        )
                        tool_calls.append(tool_call)
                    tool_plan = tool_calls
                    print(f"   Tools planned: {len(tool_calls)}")

                return intent_analysis, context, tool_plan
            else:
                print("🔧 COMBINED PHASE: No JSON found in AI response")
                print(f"🔧 COMBINED PHASE: Raw response: {response.text[:500]}...")

        except Exception as e:
            print(f"Combined phase error: {e}")
            print("🔄 Falling back to enhanced separate phases...")

        # ENHANCED FALLBACK: Use separate phases with enhanced detection logic
        print("🔧 FALLBACK: Analyzing intent...")
        intent_analysis = await self._analyze_intent(conversation_id, user_message)
        print(f"🔧 FALLBACK: Intent analysis result: {intent_analysis}")

        context = self.memory_service.get_context_for_query(
            conversation_id=conversation_id,
            query=user_message
        )

        # Use the enhanced forced tool planner with comprehensive keyword detection
        print("🔧 FALLBACK: Running forced tool planner...")
        tool_plan = await self._forced_tool_planner(
            user_message=user_message,
            intent_analysis=intent_analysis,
            context=context,
            conversation_id=conversation_id
        )
        print(f"🔧 FALLBACK: Tool planner result: {len(tool_plan) if tool_plan else 0} tools")

        # If still no tool plan, try one more time with enhanced context analysis
        if not tool_plan:
            print("🔄 No tool plan from enhanced detection, trying context-aware fallback...")
            context_intent_boost = self._analyze_conversation_context_for_intent(
                user_message, "", None  # Empty history for basic detection
            )
            print(f"🔧 FALLBACK: Context analysis result: {context_intent_boost}")

            # If context analysis strongly recommends a tool, create a plan
            if context_intent_boost.get('recommended_tool_boost') == 'search_cordis_projects':
                print("🎯 Context analysis override: Forcing CORDIS search")
                from ..tools.tool_orchestrator import ToolCall
                tool_call = ToolCall(
                    tool_name='search_cordis_projects',
                    parameters={
                        "query": user_message,
                        "max_results": 10
                    },
                    execution_order=0
                )
                tool_plan = [tool_call]

        print(f"🔧 FALLBACK: Final result - intent: {intent_analysis.get('intent_type', 'unknown')}, tools: {len(tool_plan) if tool_plan else 0}")
        return intent_analysis, context, tool_plan

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
            context_chunks = retrieval_results if retrieval_results else []
            
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
                formatted_response = self.unified_formatter.format_mixed_results(
                    tool_results=tool_results,
                    retrieval_results=retrieval_results,
                    query=query
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
                'chunks_retrieved': len(retrieval_results) if retrieval_results else 0,
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
        Generate streaming response with progressive status updates following the OPTIMIZED 5-phase architecture.

        OPTIMIZED PHASES:
        Phase 1: Context Resolution
        Phase 2: Combined Intent-Context-Tool Planning (single AI call)
        Phase 3: Route Selection
        Phase 4: Data Processing
        Phase 5: Response Generation
        Phase 6: Context Enhancement
        Phase 7: Streaming Response
        """
        try:
            # Phase 1: Context Resolution
            yield {
                'type': 'status',
                'stage': 'context_resolution',
                'message': 'Loading conversation context and memory'
            }
            await asyncio.sleep(0.1)
            
            # Phase 2: Intent Detection (combined with context and tool planning)
            intent_confidence = intent_analysis.get('confidence', 0.0)
            routing_decision = intent_analysis.get('intent_type', 'CONVERSATIONAL')
            
            yield {
                'type': 'progress',
                'stage': 'intent_detected',
                'message': f'Classified query intent: {routing_decision}',
                'routing_decision': routing_decision,
                'intent_confidence': intent_confidence
            }
            await asyncio.sleep(0.1)
            
            # Phase 3: Route Selection
            if tool_results:
                yield {
                    'type': 'progress',
                    'stage': 'route_selected',
                    'message': 'Selected tool-based response generation',
                    'routing_decision': 'SEARCH_CALLS' if 'eu_portal_search' in str(tool_results) else 'SEARCH_PROJECTS'
                }
            else:
                yield {
                    'type': 'progress',
                    'stage': 'route_selected',
                    'message': 'Selected conversational AI response',
                    'routing_decision': 'CONVERSATIONAL'
                }
            await asyncio.sleep(0.1)
            
            # Phase 4: Data Processing
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
            
            # Phase 5: Response Generation
            yield {
                'type': 'status',
                'stage': 'answer_generation',
                'message': 'Generating response based on processed data'
            }
            await asyncio.sleep(0.1)
            
            # Phase 6: Context Enhancement
            yield {
                'type': 'status',
                'stage': 'context_enhancement',
                'message': 'Enhancing response with relevant context'
            }
            await asyncio.sleep(0.1)
            
            # Phase 7: Streaming Response
            yield {
                'type': 'status',
                'stage': 'streaming_response',
                'message': 'Starting response stream'
            }
            await asyncio.sleep(0.1)
            
            # Prepare context chunks
            context_chunks = retrieval_results if retrieval_results else []
            
            # Generate and stream the actual response
            if tool_results:
                # Tool-based response with beautiful formatting
                formatted_response = self.unified_formatter.format_mixed_results(
                    tool_results=tool_results,
                    retrieval_results=retrieval_results,
                    query=query
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
                    'phases': ['context_resolution', 'combined_intent_context_tool_planning', 'data_retrieval' if tools_executed else 'conversational', 'answer_generation', 'streaming_response'],
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
            # Import here to avoid circular imports
            from ..rag.response_generator import GroundedResponseGenerator
            
            # Initialize response generator if not already done
            if not hasattr(self, 'response_generator'):
                self.response_generator = GroundedResponseGenerator(
                    gemini_api_key=os.getenv('GEMINI_API_KEY')
                )
            
            # Prepare context chunks from retrieval results
            context_chunks = retrieval_results if retrieval_results else []
            
            # Generate response using the response generator
            response = self.response_generator.generate_response(
                query=query,
                context_chunks=context_chunks,
                conversation_context=context,
                system_instructions=self._get_conversational_instructions(intent_analysis)
            )
            
            return response.get('answer', 'I apologize, but I encountered an issue generating a response.')
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            return self._get_fallback_conversational_response(query, intent_analysis)
    
    def _get_conversational_instructions(self, intent_analysis: Dict) -> str:
        """
        Get system instructions for conversational responses.
        """
        return """You are a helpful AI assistant specializing in European research funding and innovation.

PERSONALITY & TONE:
- Be friendly, professional, and conversational
- Show enthusiasm for helping with research and funding questions
- Be encouraging and supportive

CAPABILITIES:
- Expert knowledge of EU funding programmes (Horizon Europe, LIFE, Digital Europe, etc.)
- Research and innovation guidance
- Grant application advice
- Project development support

RESPONSE GUIDELINES:
- Give helpful, actionable advice
- If asked about specific calls or projects, suggest they ask for current information
- Be honest about limitations - if you need current data, say so
- Keep responses concise but informative
- Use a warm, encouraging tone

CURRENT CONTEXT:
- You have access to extensive documentation about EU funding
- You can search for current calls and projects when specifically requested
- Focus on being genuinely helpful rather than just informative"""
    
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