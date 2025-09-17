"""
Main conversation management system that orchestrates all components.
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import json
import logging
import os
import random
import re

from ..memory.memory_service import MemoryService
from ..memory.context_manager import ConversationContext
from ..rag.conversation_retriever import ConversationAwareRetriever, RetrievalContext
from ..rag.response_generator import GroundedResponseGenerator
from ..rag.hybrid_search import HybridSearchPipeline, MockVectorStore, MockKeywordStore, MockEmbeddingService
from ..tools.tool_orchestrator import create_research_orchestrator

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Central manager for all conversation operations.
    Coordinates memory, RAG, and tool systems.
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
        Process a user message through the complete pipeline.
        
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
            
            # Phase 2: Analyze intent and plan approach
            intent_analysis = await self._analyze_intent(
                conversation_id, user_message
            )
            
            # Phase 3: Build conversation context
            context = self.memory_service.get_context_for_query(
                conversation_id=conversation_id,
                query=user_message
            )
            
            # Phase 4: AI-powered tool planning
            tool_plan = await self._ai_tool_planner(
                user_message=user_message,
                intent_analysis=intent_analysis,
                context=context,
                conversation_id=conversation_id
            )
            
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
            if streaming:
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
                return await self._generate_response(
                    conversation_id=conversation_id,
                    query=user_message,
                    context=context,
                    retrieval_results=retrieval_results,
                    tool_results=tool_results,
                    intent_analysis=intent_analysis,
                    start_time=start_time
                )
                
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

        # Check if tools are needed based on keywords
        requires_tools = any(keyword in message_lower for keyword in [
            'open calls', 'calls for', 'funding opportunities', 'grant opportunities',
            'available calls', 'current calls', 'calls about', 'calls related to',
            'what calls', 'which calls', 'show me calls', 'find calls',
            'funding calls', 'research calls', 'horizon calls',
            'projects', 'research projects', 'case studies', 'project examples'
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
1. For "open calls", "funding opportunities", "calls for proposals" → Use search_horizon_calls tool
2. For "projects", "research projects", "case studies" → Use search_cordis_projects tool
3. For "document analysis", "specific call details" → Use analyze_document tool
4. For general questions → Use the most appropriate tool based on context

Respond in JSON format:
{{
    "tools_needed": [
        {{
            "tool_name": "search_horizon_calls",
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
            
            # Generate response
            response = self.response_generator.generate_response(
                query=query,
                context_chunks=context_chunks,
                conversation_context=context,
                system_instructions=self._get_system_instructions(intent_analysis)
            )
            
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
        Generate streaming response with progressive output.
        """
        try:
            # Prepare context chunks
            context_chunks = retrieval_results if retrieval_results else []
            
            # Add tool results if available
            if tool_results:
                # Serialize tool results for JSON compatibility
                serialized_tool_results = self._serialize_tool_results(tool_results)
                tool_context = {
                    'content': f"Tool Results:\n{json.dumps(serialized_tool_results, indent=2)}",
                    'citation': 'Tool Execution',
                    'chunk_id': 'tool_results'
                }
                context_chunks.insert(0, tool_context)
            
            # Stream response generation
            accumulated_response = ""
            async for chunk in self.response_generator.generate_streaming_response(
                query=query,
                context_chunks=context_chunks,
                conversation_context=context,
                system_instructions=self._get_system_instructions(intent_analysis)
            ):
                if chunk['type'] == 'token':
                    accumulated_response += chunk['content']
                    yield chunk
                elif chunk['type'] == 'complete':
                    # Store complete response in memory
                    assistant_message_id = await self._store_assistant_message(
                        conversation_id, accumulated_response
                    )
                    
                    self.memory_service.add_conversation_turn(
                        conversation_id=conversation_id,
                        role='assistant',
                        content=accumulated_response,
                        message_id=assistant_message_id
                    )
                    
                    # Add metadata to completion
                    processing_time = (datetime.now() - start_time).total_seconds()
                    chunk.update({
                        'intent': intent_analysis,
                        'chunks_retrieved': len(retrieval_results) if retrieval_results else 0,
                        'tools_executed': tool_results is not None,
                        'processing_time': processing_time,
                        'memory_stats': self.memory_service.stm.get_memory_stats(conversation_id),
                        'retrieval_stats': self.retriever.get_retrieval_stats(conversation_id)
                    })
                    yield chunk
                else:
                    yield chunk
        except Exception as e:
            yield {
                'type': 'error',
                'error': str(e)
            }
    
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

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_conversation_manager())