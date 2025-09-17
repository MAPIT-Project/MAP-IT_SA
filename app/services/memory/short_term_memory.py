import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import redis
from redis.exceptions import RedisError
import os

@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    message_id: int
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            'message_id': self.message_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            message_id=data['message_id'],
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )

class ShortTermMemory:
    """
    Manages recent conversation turns in Redis for fast access.
    Maintains a sliding window of the most recent N turns.
    """
    
    def __init__(self, 
                 redis_client: redis.Redis = None,
                 max_turns: int = 12,
                 ttl_hours: int = 24):
        """
        Initialize STM with Redis connection.
        
        Args:
            redis_client: Redis connection instance
            max_turns: Maximum number of turns to keep (default 12)
            ttl_hours: Time-to-live for memory in hours (default 24)
        """
        self.redis = redis_client or redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            db=0,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        self.max_turns = max_turns
        self.ttl_seconds = ttl_hours * 3600
        
    def _get_key(self, conversation_id: int) -> str:
        """Generate Redis key for conversation"""
        return f"stm:conv:{conversation_id}"
    
    def add_turn(self, conversation_id: int, turn: ConversationTurn) -> bool:
        """
        Add a new turn to short-term memory.
        Automatically trims to max_turns capacity.
        
        Args:
            conversation_id: Unique conversation identifier
            turn: ConversationTurn object to add
            
        Returns:
            bool: Success status
        """
        try:
            key = self._get_key(conversation_id)
            
            # Add turn to the list (right push for chronological order)
            self.redis.rpush(key, json.dumps(turn.to_dict()))
            
            # Trim to maintain capacity (keep only the last max_turns)
            self.redis.ltrim(key, -self.max_turns, -1)
            
            # Reset TTL
            self.redis.expire(key, self.ttl_seconds)
            
            # Also store metadata for quick access
            meta_key = f"{key}:meta"
            self.redis.hset(meta_key, mapping={
                'last_update': datetime.now().isoformat(),
                'turn_count': self.redis.llen(key),
                'last_role': turn.role
            })
            self.redis.expire(meta_key, self.ttl_seconds)
            
            return True
            
        except RedisError as e:
            print(f"Redis error in add_turn: {e}")
            return False
    
    def get_recent_turns(self, 
                        conversation_id: int, 
                        n: Optional[int] = None) -> List[ConversationTurn]:
        """
        Retrieve recent turns from memory.
        
        Args:
            conversation_id: Unique conversation identifier
            n: Number of turns to retrieve (None for all)
            
        Returns:
            List of ConversationTurn objects in chronological order
        """
        try:
            key = self._get_key(conversation_id)
            
            # Get all or last n turns
            if n is None:
                turns_data = self.redis.lrange(key, 0, -1)
            else:
                turns_data = self.redis.lrange(key, -n, -1)
            
            # Convert JSON strings back to ConversationTurn objects
            turns = []
            for turn_json in turns_data:
                turn_dict = json.loads(turn_json)
                turns.append(ConversationTurn.from_dict(turn_dict))
            
            return turns
            
        except RedisError as e:
            print(f"Redis error in get_recent_turns: {e}")
            return []
    
    def get_context_window(self, 
                          conversation_id: int,
                          max_tokens: int = 2000) -> str:
        """
        Get recent turns formatted for LLM context, respecting token limit.
        
        Args:
            conversation_id: Unique conversation identifier
            max_tokens: Maximum tokens to include (rough estimate)
            
        Returns:
            Formatted string of recent conversation
        """
        turns = self.get_recent_turns(conversation_id)
        
        if not turns:
            return ""
        
        # Build context from most recent backwards until token limit
        context_lines = []
        estimated_tokens = 0
        
        for turn in reversed(turns):
            # Rough token estimation (1 token ≈ 4 characters)
            turn_text = f"{turn.role.upper()}: {turn.content}"
            turn_tokens = len(turn_text) // 4
            
            if estimated_tokens + turn_tokens > max_tokens:
                break
                
            context_lines.insert(0, turn_text)
            estimated_tokens += turn_tokens
        
        return "\n\n".join(context_lines)
    
    def clear_conversation(self, conversation_id: int) -> bool:
        """
        Clear all short-term memory for a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            bool: Success status
        """
        try:
            key = self._get_key(conversation_id)
            meta_key = f"{key}:meta"
            
            self.redis.delete(key, meta_key)
            return True
            
        except RedisError as e:
            print(f"Redis error in clear_conversation: {e}")
            return False
    
    def get_memory_stats(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get statistics about the short-term memory.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Dictionary with memory statistics
        """
        try:
            key = self._get_key(conversation_id)
            meta_key = f"{key}:meta"
            
            turn_count = self.redis.llen(key)
            metadata = self.redis.hgetall(meta_key)
            
            # Calculate approximate memory size
            turns = self.get_recent_turns(conversation_id)
            total_chars = sum(len(turn.content) for turn in turns)
            
            return {
                'turn_count': turn_count,
                'max_capacity': self.max_turns,
                'utilization': turn_count / self.max_turns if self.max_turns > 0 else 0,
                'total_characters': total_chars,
                'estimated_tokens': total_chars // 4,
                'last_update': metadata.get('last_update'),
                'last_role': metadata.get('last_role')
            }
            
        except RedisError as e:
            print(f"Redis error in get_memory_stats: {e}")
            return {}