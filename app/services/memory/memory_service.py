"""
Unified memory service that combines all memory components.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional

import redis

from .context_manager import ContextWindowManager
from .long_term_memory import LongTermMemory
from .rolling_summarizer import RollingSummarizer
from .short_term_memory import ConversationTurn, ShortTermMemory

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Unified service for managing conversation memory.
    """
    
    def __init__(self):
        """Initialize all memory components"""
        # Redis for STM with connection handling
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"⚠️ Redis connection failed: {e}")
            logger.info("🔄 Creating fallback Redis client")
            # Create a mock Redis client that doesn't fail
            self.redis_client = self._create_fallback_redis()
        
        # Initialize components
        self.stm = ShortTermMemory(self.redis_client)
        self.ltm = LongTermMemory(os.getenv('DATABASE_URL'))
        self.summarizer = RollingSummarizer(
            ai_provider=os.getenv('DEFAULT_AI_PROVIDER', 'gemini'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            openrouter_api_key=os.getenv('OPENROUTER_API_KEY')
        )
        self.context_manager = ContextWindowManager(self.stm, self.ltm)
        
        # Configuration
        self.summarize_every_n_turns = 5
    
    def add_conversation_turn(self,
                             conversation_id: int,
                             role: str,
                             content: str,
                             message_id: int) -> bool:
        """
        Add a new turn and update memory.
        
        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            message_id: Database message ID
            
        Returns:
            Success status
        """
        # Create turn object
        turn = ConversationTurn(
            message_id=message_id,
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        
        # Add to STM
        success = self.stm.add_turn(conversation_id, turn)
        
        # Check if we should update summary
        stats = self.stm.get_memory_stats(conversation_id)
        if stats.get('turn_count', 0) % self.summarize_every_n_turns == 0:
            self._update_summary(conversation_id)
        
        # Extract entities if assistant response
        if role == 'assistant':
            self._extract_and_store_entities(conversation_id, [turn])
        
        return success
    
    def get_context_for_query(self,
                             conversation_id: int,
                             query: str,
                             retrieved_chunks: Optional[List[str]] = None) -> str:
        """
        Get optimized context for a query.
        
        Args:
            conversation_id: Conversation ID
            query: User query
            retrieved_chunks: Optional RAG chunks
            
        Returns:
            Formatted context string
        """
        context = self.context_manager.build_context(
            conversation_id=conversation_id,
            current_query=query,
            retrieved_chunks=retrieved_chunks
        )
        
        return context.to_prompt()
    
    def _update_summary(self, conversation_id: int):
        """Update rolling summary"""
        try:
            # Get recent turns
            recent_turns = self.stm.get_recent_turns(conversation_id)
            
            if not recent_turns:
                return
            
            # Get existing summary
            existing_summary = self.ltm.get_summary(conversation_id)
            existing_text = existing_summary.summary_text if existing_summary else None
            
            # Generate new summary
            new_summary = self.summarizer.summarize_turn(
                existing_summary=existing_text,
                new_turns=recent_turns
            )
            new_summary.conversation_id = conversation_id
            
            # Store summary
            self.ltm.store_summary(new_summary)
            
            # Extract and store facts
            facts = self.summarizer.extract_facts(recent_turns)
            if facts:
                self.ltm.store_facts(conversation_id, facts)
                
        except Exception as e:
            logger.error(f"Error updating summary: {e}")
    
    def _extract_and_store_entities(self,
                                   conversation_id: int,
                                   turns: List[ConversationTurn]):
        """Extract and store entity cards"""
        try:
            entities = self.summarizer.extract_entities(turns)
            for entity in entities:
                self.ltm.update_entity_card(conversation_id, entity)
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
    
    def clear_conversation_memory(self, conversation_id: int) -> bool:
        """Clear all memory for a conversation"""
        return self.stm.clear_conversation(conversation_id)
    
    def get_memory_stats(self, conversation_id: int) -> dict:
        """Get comprehensive memory statistics"""
        try:
            stm_stats = self.stm.get_memory_stats(conversation_id)
            summary = self.ltm.get_summary(conversation_id)
            facts = self.ltm.get_facts(conversation_id)
            entities = self.ltm.get_entity_cards(conversation_id)
            
            return {
                'short_term': stm_stats,
                'summary': {
                    'exists': summary is not None,
                    'token_count': summary.token_count if summary else 0,
                    'key_points_count': len(summary.key_points) if summary else 0
                },
                'facts_count': len(facts),
                'entities_count': len(entities)
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {
                'short_term': {'turn_count': 0, 'max_capacity': 12, 'utilization': 0},
                'summary': {'exists': False, 'token_count': 0, 'key_points_count': 0},
                'facts_count': 0,
                'entities_count': 0
            }
    
    def _create_fallback_redis(self):
        """Create a fallback Redis client that doesn't fail"""
        class FallbackRedis:
            def ping(self): return True
            def rpush(self, *args): return 1
            def ltrim(self, *args): return True
            def expire(self, *args): return True
            def hset(self, *args, **kwargs): return True
            def llen(self, *args): return 0
            def hgetall(self, *args): return {}
            def lrange(self, *args): return []
            def delete(self, *args): return True
            def get(self, *args): return None
            def setex(self, *args): return True
            def lpush(self, *args): return 1
            def sadd(self, *args): return 1
            def sismember(self, *args): return False
            def scard(self, *args): return 0
        
        return FallbackRedis()