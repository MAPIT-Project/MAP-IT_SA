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
            
            # Phase 4: Determine if tools are needed
            tool_plan = None
            if intent_analysis.get('requires_tools'):
                tool_plan = await self.tool_orchestrator.plan_tools(
                    task=user_message,
                    context=context
                )
            
            # Phase 5: Retrieve relevant information if needed
            retrieval_results = None
            if intent_analysis.get('requires_retrieval'):
                retrieval_results = await self._retrieve_information(
                    conversation_id, user_message, context
                )
            
            # Phase 6: Execute tools if needed
            tool_results = None
            if tool_plan:
                tool_results = await self.tool_orchestrator.execute_plan(
                    tool_plan, conversation_id
                )
            
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
        
        # Fallback to simple heuristics
        return {
            "intent_type": "question",
            "requires_retrieval": True,
            "requires_tools": False,
            "confidence": 0.5,
            "explanation": "Default processing"
        }
    
    async def _retrieve_information(self,
                                   conversation_id: int,
                                   query: str,
                                   context: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information using your existing RAG service.
        """
        try:
            # Use your existing RAG service for real data
            if hasattr(self, 'existing_rag') and self.existing_rag:
                print(f"🔍 Using existing RAG service for query: {query}")
                
                # Use your existing enhanced RAG service
                rag_response = self.existing_rag.answer_question(
                    question=query,
                    max_results=self.config.get('max_retrieval_chunks', 4)
                )
                
                # Convert to expected format
                if rag_response.get('answer'):
                    return [{
                        'content': rag_response['answer'],
                        'citation': f"Enhanced RAG Service - {rag_response.get('data_source', 'Unknown')}",
                        'chunk_id': f"rag_response_{conversation_id}",
                        'metadata': {
                            'source': 'enhanced_rag',
                            'confidence': rag_response.get('confidence', 0.8),
                            'data_source': rag_response.get('data_source', 'Unknown')
                        }
                    }]
            
            # Fallback to new retrieval system
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
                tool_context = {
                    'content': f"Tool Results:\n{json.dumps(tool_results, indent=2)}",
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
                tool_context = {
                    'content': f"Tool Results:\n{json.dumps(tool_results, indent=2)}",
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