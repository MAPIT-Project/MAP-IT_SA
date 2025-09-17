# 🧠 Memory System Implementation Guide

## Overview
This guide provides concrete, implementable code for the memory management system that forms the core of our context-aware AI.

## 1. Short-Term Memory Implementation

### File: `app/services/memory/short_term_memory.py`

```python
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import redis
from redis.exceptions import RedisError

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
            host='localhost',
            port=6379,
            decode_responses=True,
            db=0
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
                'utilization': turn_count / self.max_turns,
                'total_characters': total_chars,
                'estimated_tokens': total_chars // 4,
                'last_update': metadata.get('last_update'),
                'last_role': metadata.get('last_role')
            }
            
        except RedisError as e:
            print(f"Redis error in get_memory_stats: {e}")
            return {}
```

## 2. Long-Term Memory & Summarization

### File: `app/services/memory/long_term_memory.py`

```python
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

@dataclass
class ConversationSummary:
    """Represents a conversation summary"""
    conversation_id: int
    summary_text: str
    key_points: List[str]
    token_count: int
    created_at: datetime
    covers_messages: Tuple[int, int]  # (first_message_id, last_message_id)

@dataclass
class ConversationFact:
    """Represents an extracted fact from conversation"""
    fact_type: str  # 'decision', 'constraint', 'preference', 'entity'
    fact_content: str
    confidence: float
    source_message_id: int
    metadata: Dict[str, Any] = None

@dataclass
class EntityCard:
    """Represents an entity mentioned in conversation"""
    entity_type: str  # 'project', 'organization', 'person', 'topic'
    entity_name: str
    entity_data: Dict[str, Any]
    first_mentioned: datetime
    reference_count: int

class LongTermMemory:
    """
    Manages persistent conversation memory in PostgreSQL.
    Handles summaries, facts, and entity tracking.
    """
    
    def __init__(self, db_url: str):
        """
        Initialize LTM with database connection.
        
        Args:
            db_url: PostgreSQL connection string
        """
        self.db_url = db_url
        
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def store_summary(self, summary: ConversationSummary) -> bool:
        """
        Store or update conversation summary.
        
        Args:
            summary: ConversationSummary object
            
        Returns:
            bool: Success status
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Upsert summary
            cursor.execute("""
                INSERT INTO conversation_memory 
                (conversation_id, memory_type, content, token_count, created_at, updated_at)
                VALUES (%s, 'summary', %s, %s, %s, NOW())
                ON CONFLICT (conversation_id, memory_type) 
                DO UPDATE SET 
                    content = EXCLUDED.content,
                    token_count = EXCLUDED.token_count,
                    updated_at = NOW()
                RETURNING id
            """, (
                summary.conversation_id,
                json.dumps({
                    'summary_text': summary.summary_text,
                    'key_points': summary.key_points,
                    'covers_messages': summary.covers_messages
                }),
                summary.token_count,
                summary.created_at
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Database error in store_summary: {e}")
            return False
    
    def get_summary(self, conversation_id: int) -> Optional[ConversationSummary]:
        """
        Retrieve the latest summary for a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            ConversationSummary object or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT content, token_count, created_at
                FROM conversation_memory
                WHERE conversation_id = %s AND memory_type = 'summary'
                ORDER BY updated_at DESC
                LIMIT 1
            """, (conversation_id,))
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                content = row['content']
                return ConversationSummary(
                    conversation_id=conversation_id,
                    summary_text=content['summary_text'],
                    key_points=content['key_points'],
                    token_count=row['token_count'],
                    created_at=row['created_at'],
                    covers_messages=tuple(content['covers_messages'])
                )
            
            return None
            
        except Exception as e:
            print(f"Database error in get_summary: {e}")
            return None
    
    def store_facts(self, 
                   conversation_id: int, 
                   facts: List[ConversationFact]) -> bool:
        """
        Store extracted facts from conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            facts: List of ConversationFact objects
            
        Returns:
            bool: Success status
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for fact in facts:
                cursor.execute("""
                    INSERT INTO conversation_facts
                    (conversation_id, fact_type, fact_content, confidence, 
                     source_message_id, extracted_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (
                    conversation_id,
                    fact.fact_type,
                    fact.fact_content,
                    fact.confidence,
                    fact.source_message_id
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Database error in store_facts: {e}")
            return False
    
    def get_facts(self, 
                 conversation_id: int,
                 fact_type: Optional[str] = None,
                 min_confidence: float = 0.7) -> List[ConversationFact]:
        """
        Retrieve facts for a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            fact_type: Optional filter by fact type
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of ConversationFact objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT fact_type, fact_content, confidence, source_message_id
                FROM conversation_facts
                WHERE conversation_id = %s AND confidence >= %s
            """
            params = [conversation_id, min_confidence]
            
            if fact_type:
                query += " AND fact_type = %s"
                params.append(fact_type)
            
            query += " ORDER BY confidence DESC, extracted_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            facts = []
            for row in rows:
                facts.append(ConversationFact(
                    fact_type=row['fact_type'],
                    fact_content=row['fact_content'],
                    confidence=row['confidence'],
                    source_message_id=row['source_message_id']
                ))
            
            cursor.close()
            conn.close()
            
            return facts
            
        except Exception as e:
            print(f"Database error in get_facts: {e}")
            return []
    
    def update_entity_card(self, 
                          conversation_id: int,
                          entity: EntityCard) -> bool:
        """
        Update or create an entity card.
        
        Args:
            conversation_id: Unique conversation identifier
            entity: EntityCard object
            
        Returns:
            bool: Success status
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO entity_cards
                (conversation_id, entity_type, entity_name, entity_data,
                 first_mentioned_at, last_referenced_at, reference_count)
                VALUES (%s, %s, %s, %s, %s, NOW(), 1)
                ON CONFLICT (conversation_id, entity_type, entity_name)
                DO UPDATE SET
                    entity_data = EXCLUDED.entity_data,
                    last_referenced_at = NOW(),
                    reference_count = entity_cards.reference_count + 1
            """, (
                conversation_id,
                entity.entity_type,
                entity.entity_name,
                json.dumps(entity.entity_data),
                entity.first_mentioned
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Database error in update_entity_card: {e}")
            return False
    
    def get_entity_cards(self,
                        conversation_id: int,
                        entity_type: Optional[str] = None) -> List[EntityCard]:
        """
        Retrieve entity cards for a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            entity_type: Optional filter by entity type
            
        Returns:
            List of EntityCard objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT entity_type, entity_name, entity_data, 
                       first_mentioned_at, reference_count
                FROM entity_cards
                WHERE conversation_id = %s
            """
            params = [conversation_id]
            
            if entity_type:
                query += " AND entity_type = %s"
                params.append(entity_type)
            
            query += " ORDER BY reference_count DESC, last_referenced_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            entities = []
            for row in rows:
                entities.append(EntityCard(
                    entity_type=row['entity_type'],
                    entity_name=row['entity_name'],
                    entity_data=row['entity_data'],
                    first_mentioned=row['first_mentioned_at'],
                    reference_count=row['reference_count']
                ))
            
            cursor.close()
            conn.close()
            
            return entities
            
        except Exception as e:
            print(f"Database error in get_entity_cards: {e}")
            return []
```

## 3. Rolling Summarizer with Gemini

### File: `app/services/memory/rolling_summarizer.py`

```python
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import google.generativeai as genai
from .short_term_memory import ConversationTurn
from .long_term_memory import ConversationSummary, ConversationFact, EntityCard

class RollingSummarizer:
    """
    Progressive summarization using Gemini AI.
    Maintains task-focused summaries and extracts facts.
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize summarizer with Gemini.
        
        Args:
            gemini_api_key: Google Gemini API key
        """
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def summarize_turn(self,
                       existing_summary: Optional[str],
                       new_turns: List[ConversationTurn],
                       max_tokens: int = 400) -> ConversationSummary:
        """
        Update summary with new conversation turns.
        
        Args:
            existing_summary: Previous summary text (if any)
            new_turns: New conversation turns to incorporate
            max_tokens: Maximum tokens for summary
            
        Returns:
            Updated ConversationSummary
        """
        # Build context for summarization
        context = self._build_summarization_context(existing_summary, new_turns)
        
        prompt = f"""You are a professional conversation summarizer. Your task is to create or update a conversation summary.

EXISTING SUMMARY (if any):
{existing_summary or "No previous summary"}

NEW CONVERSATION TURNS:
{context}

INSTRUCTIONS:
1. Create a concise summary (max {max_tokens} tokens) that captures:
   - Main topics discussed
   - Key decisions made
   - Important constraints or requirements mentioned
   - Action items or next steps
   - User preferences and goals

2. Focus on TASK-RELEVANT information, not conversational pleasantries

3. Maintain continuity with the existing summary if provided

4. Extract 3-5 KEY POINTS as bullet points

FORMAT YOUR RESPONSE AS JSON:
{{
    "summary": "Your concise summary here",
    "key_points": ["point 1", "point 2", "point 3"]
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=max_tokens + 100
                )
            )
            
            # Parse JSON response
            result = self._parse_json_response(response.text)
            
            # Calculate token count (rough estimate)
            token_count = len(result['summary']) // 4
            
            # Get message ID range
            message_ids = (
                new_turns[0].message_id if new_turns else 0,
                new_turns[-1].message_id if new_turns else 0
            )
            
            return ConversationSummary(
                conversation_id=0,  # Will be set by caller
                summary_text=result['summary'],
                key_points=result['key_points'],
                token_count=token_count,
                created_at=datetime.now(),
                covers_messages=message_ids
            )
            
        except Exception as e:
            print(f"Error in summarize_turn: {e}")
            # Return a basic summary on error
            return ConversationSummary(
                conversation_id=0,
                summary_text="Error generating summary",
                key_points=[],
                token_count=0,
                created_at=datetime.now(),
                covers_messages=(0, 0)
            )
    
    def extract_facts(self,
                     conversation_turns: List[ConversationTurn]) -> List[ConversationFact]:
        """
        Extract facts from conversation turns.
        
        Args:
            conversation_turns: List of conversation turns
            
        Returns:
            List of extracted ConversationFact objects
        """
        if not conversation_turns:
            return []
        
        context = self._build_conversation_context(conversation_turns)
        
        prompt = f"""Analyze this conversation and extract important facts.

CONVERSATION:
{context}

Extract facts in these categories:
1. DECISIONS: Choices or decisions made
2. CONSTRAINTS: Requirements, limitations, or conditions mentioned
3. PREFERENCES: User preferences or priorities stated
4. ENTITIES: Important projects, organizations, or people discussed

For each fact, provide:
- fact_type: One of [decision, constraint, preference, entity]
- fact_content: The specific fact (be precise and complete)
- confidence: Your confidence level (0.0 to 1.0)
- source_message_id: The message ID where this was mentioned

FORMAT YOUR RESPONSE AS JSON:
{{
    "facts": [
        {{
            "fact_type": "constraint",
            "fact_content": "Budget must not exceed 500K EUR",
            "confidence": 0.95,
            "source_message_id": 123
        }}
    ]
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1000
                )
            )
            
            result = self._parse_json_response(response.text)
            
            facts = []
            for fact_data in result.get('facts', []):
                facts.append(ConversationFact(
                    fact_type=fact_data['fact_type'],
                    fact_content=fact_data['fact_content'],
                    confidence=fact_data['confidence'],
                    source_message_id=fact_data['source_message_id']
                ))
            
            return facts
            
        except Exception as e:
            print(f"Error in extract_facts: {e}")
            return []
    
    def extract_entities(self,
                        conversation_turns: List[ConversationTurn]) -> List[EntityCard]:
        """
        Extract and create entity cards from conversation.
        
        Args:
            conversation_turns: List of conversation turns
            
        Returns:
            List of EntityCard objects
        """
        if not conversation_turns:
            return []
        
        context = self._build_conversation_context(conversation_turns)
        
        prompt = f"""Analyze this conversation and extract important entities.

CONVERSATION:
{context}

Extract entities in these categories:
1. PROJECT: Research projects or initiatives mentioned
2. ORGANIZATION: Companies, institutions, or organizations
3. PERSON: Individuals mentioned by name
4. TOPIC: Key topics or domains discussed

For each entity, provide:
- entity_type: One of [project, organization, person, topic]
- entity_name: The entity's name
- entity_data: Additional information about the entity (as key-value pairs)

FORMAT YOUR RESPONSE AS JSON:
{{
    "entities": [
        {{
            "entity_type": "project",
            "entity_name": "HORIZON-2024-CL5",
            "entity_data": {{
                "full_name": "Climate, Energy and Mobility",
                "budget": "1.5M EUR",
                "deadline": "2024-09-15"
            }}
        }}
    ]
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1000
                )
            )
            
            result = self._parse_json_response(response.text)
            
            entities = []
            for entity_data in result.get('entities', []):
                entities.append(EntityCard(
                    entity_type=entity_data['entity_type'],
                    entity_name=entity_data['entity_name'],
                    entity_data=entity_data.get('entity_data', {}),
                    first_mentioned=datetime.now(),
                    reference_count=1
                ))
            
            return entities
            
        except Exception as e:
            print(f"Error in extract_entities: {e}")
            return []
    
    def recompute_from_scratch(self,
                              full_history: List[ConversationTurn],
                              max_tokens: int = 400) -> ConversationSummary:
        """
        Recompute summary from complete conversation history.
        Used periodically to prevent drift.
        
        Args:
            full_history: Complete conversation history
            max_tokens: Maximum tokens for summary
            
        Returns:
            Fresh ConversationSummary
        """
        # For full recomputation, we don't use existing summary
        return self.summarize_turn(None, full_history, max_tokens)
    
    def _build_conversation_context(self, 
                                   turns: List[ConversationTurn]) -> str:
        """Build formatted conversation context"""
        lines = []
        for turn in turns:
            role = "USER" if turn.role == "user" else "ASSISTANT"
            lines.append(f"[Message ID: {turn.message_id}]")
            lines.append(f"{role}: {turn.content}")
            lines.append("")
        return "\n".join(lines)
    
    def _build_summarization_context(self,
                                    existing_summary: Optional[str],
                                    new_turns: List[ConversationTurn]) -> str:
        """Build context for summarization"""
        return self._build_conversation_context(new_turns)
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try parsing the whole response
                return json.loads(response_text)
        except:
            # Return empty structure on parse error
            return {
                'summary': response_text[:400] if response_text else '',
                'key_points': [],
                'facts': [],
                'entities': []
            }
```

## 4. Context Window Manager

### File: `app/services/memory/context_manager.py`

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .short_term_memory import ShortTermMemory, ConversationTurn
from .long_term_memory import LongTermMemory, ConversationSummary, ConversationFact, EntityCard

@dataclass
class ConversationContext:
    """Complete context for LLM input"""
    system_prompt: str
    rolling_summary: str
    facts_and_constraints: List[str]
    entity_cards: List[Dict[str, Any]]
    recent_messages: str
    retrieved_chunks: List[str]
    current_query: str
    
    def to_prompt(self, template: Optional[str] = None) -> str:
        """Convert context to formatted prompt"""
        if template:
            return template.format(
                system_prompt=self.system_prompt,
                rolling_summary=self.rolling_summary,
                facts_and_constraints="\n".join(self.facts_and_constraints),
                entity_cards=self._format_entities(),
                recent_messages=self.recent_messages,
                retrieved_chunks=self._format_chunks(),
                current_query=self.current_query
            )
        else:
            return self._default_format()
    
    def _format_entities(self) -> str:
        """Format entity cards for prompt"""
        if not self.entity_cards:
            return "No entities tracked yet."
        
        lines = []
        for entity in self.entity_cards:
            lines.append(f"- {entity['type']}: {entity['name']}")
            for key, value in entity.get('data', {}).items():
                lines.append(f"  • {key}: {value}")
        return "\n".join(lines)
    
    def _format_chunks(self) -> str:
        """Format retrieved chunks for prompt"""
        if not self.retrieved_chunks:
            return "No additional context retrieved."
        
        formatted = []
        for i, chunk in enumerate(self.retrieved_chunks, 1):
            formatted.append(f"[Context {i}]\n{chunk}")
        return "\n\n".join(formatted)
    
    def _default_format(self) -> str:
        """Default prompt formatting"""
        sections = [
            f"# System Instructions\n{self.system_prompt}",
            f"# Conversation Summary\n{self.rolling_summary}" if self.rolling_summary else "",
            f"# Key Facts\n" + "\n".join(f"- {fact}" for fact in self.facts_and_constraints) if self.facts_and_constraints else "",
            f"# Entities\n{self._format_entities()}" if self.entity_cards else "",
            f"# Recent Conversation\n{self.recent_messages}" if self.recent_messages else "",
            f"# Retrieved Information\n{self._format_chunks()}" if self.retrieved_chunks else "",
            f"# Current Query\nUser: {self.current_query}"
        ]
        
        return "\n\n".join(filter(bool, sections))
    
    def estimate_tokens(self) -> int:
        """Estimate total token count"""
        full_prompt = self.to_prompt()
        # Rough estimation: 1 token ≈ 4 characters
        return len(full_prompt) // 4

class ContextWindowManager:
    """
    Manages context window optimization for LLM input.
    Combines different memory sources into optimal context.
    """
    
    def __init__(self,
                 stm: ShortTermMemory,
                 ltm: LongTermMemory,
                 max_tokens: int = 8000):
        """
        Initialize context manager.
        
        Args:
            stm: Short-term memory instance
            ltm: Long-term memory instance
            max_tokens: Maximum context window size
        """
        self.stm = stm
        self.ltm = ltm
        self.max_tokens = max_tokens
        
        # Token allocation strategy (can be adjusted)
        self.token_allocation = {
            'system': 200,
            'summary': 400,
            'facts': 300,
            'entities': 200,
            'recent_turns': 2000,
            'retrieved': 2000,
            'query': 100,
            'buffer': 800  # Safety buffer
        }
    
    def build_context(self,
                     conversation_id: int,
                     current_query: str,
                     retrieved_chunks: Optional[List[str]] = None,
                     system_prompt: Optional[str] = None) -> ConversationContext:
        """
        Build optimized context for LLM.
        
        Args:
            conversation_id: Unique conversation identifier
            current_query: Current user query
            retrieved_chunks: Optional retrieved context chunks
            system_prompt: Optional custom system prompt
            
        Returns:
            ConversationContext object
        """
        # Get components from memory
        summary = self.ltm.get_summary(conversation_id)
        facts = self.ltm.get_facts(conversation_id, min_confidence=0.7)
        entities = self.ltm.get_entity_cards(conversation_id)
        recent_turns = self.stm.get_recent_turns(conversation_id)
        
        # Build context with token limits
        context = ConversationContext(
            system_prompt=self._get_system_prompt(system_prompt),
            rolling_summary=self._format_summary(summary),
            facts_and_constraints=self._format_facts(facts),
            entity_cards=self._format_entity_cards(entities),
            recent_messages=self._format_recent_turns(recent_turns),
            retrieved_chunks=self._format_retrieved_chunks(retrieved_chunks),
            current_query=current_query
        )
        
        # Optimize if over token limit
        if context.estimate_tokens() > self.max_tokens:
            context = self._optimize_context(context)
        
        return context
    
    def _get_system_prompt(self, custom_prompt: Optional[str]) -> str:
        """Get system prompt within token limit"""
        default_prompt = """You are a helpful AI assistant specializing in European research funding.
Your responses should be:
- Accurate and grounded in provided context
- Professional yet conversational
- Citing sources when available
- Acknowledging when information is missing"""
        
        prompt = custom_prompt or default_prompt
        max_tokens = self.token_allocation['system']
        
        # Truncate if needed
        if len(prompt) // 4 > max_tokens:
            prompt = prompt[:max_tokens * 4] + "..."
        
        return prompt
    
    def _format_summary(self, summary: Optional[ConversationSummary]) -> str:
        """Format summary within token limit"""
        if not summary:
            return ""
        
        text = summary.summary_text
        if summary.key_points:
            text += "\n\nKey Points:\n" + "\n".join(f"- {point}" for point in summary.key_points)
        
        max_tokens = self.token_allocation['summary']
        if len(text) // 4 > max_tokens:
            text = text[:max_tokens * 4] + "..."
        
        return text
    
    def _format_facts(self, facts: List[ConversationFact]) -> List[str]:
        """Format facts within token limit"""
        if not facts:
            return []
        
        formatted = []
        tokens_used = 0
        max_tokens = self.token_allocation['facts']
        
        # Sort by confidence and take most important
        facts.sort(key=lambda f: f.confidence, reverse=True)
        
        for fact in facts:
            fact_text = f"[{fact.fact_type}] {fact.fact_content}"
            fact_tokens = len(fact_text) // 4
            
            if tokens_used + fact_tokens > max_tokens:
                break
            
            formatted.append(fact_text)
            tokens_used += fact_tokens
        
        return formatted
    
    def _format_entity_cards(self, entities: List[EntityCard]) -> List[Dict[str, Any]]:
        """Format entity cards within token limit"""
        if not entities:
            return []
        
        formatted = []
        tokens_used = 0
        max_tokens = self.token_allocation['entities']
        
        # Sort by reference count (most referenced first)
        entities.sort(key=lambda e: e.reference_count, reverse=True)
        
        for entity in entities:
            entity_dict = {
                'type': entity.entity_type,
                'name': entity.entity_name,
                'data': entity.entity_data
            }
            
            # Estimate tokens
            entity_text = str(entity_dict)
            entity_tokens = len(entity_text) // 4
            
            if tokens_used + entity_tokens > max_tokens:
                break
            
            formatted.append(entity_dict)
            tokens_used += entity_tokens
        
        return formatted
    
    def _format_recent_turns(self, turns: List[ConversationTurn]) -> str:
        """Format recent turns within token limit"""
        if not turns:
            return ""
        
        max_tokens = self.token_allocation['recent_turns']
        
        # Get context with token limit
        context = []
        tokens_used = 0
        
        # Process from most recent backwards
        for turn in reversed(turns):
            turn_text = f"{turn.role.upper()}: {turn.content}"
            turn_tokens = len(turn_text) // 4
            
            if tokens_used + turn_tokens > max_tokens:
                break
            
            context.insert(0, turn_text)
            tokens_used += turn_tokens
        
        return "\n\n".join(context)
    
    def _format_retrieved_chunks(self, chunks: Optional[List[str]]) -> List[str]:
        """Format retrieved chunks within token limit"""
        if not chunks:
            return []
        
        max_tokens = self.token_allocation['retrieved']
        
        formatted = []
        tokens_used = 0
        
        for chunk in chunks:
            chunk_tokens = len(chunk) // 4
            
            if tokens_used + chunk_tokens > max_tokens:
                # Try to fit partial chunk
                remaining_tokens = max_tokens - tokens_used
                if remaining_tokens > 50:  # Only include if meaningful
                    truncated = chunk[:remaining_tokens * 4] + "..."
                    formatted.append(truncated)
                break
            
            formatted.append(chunk)
            tokens_used += chunk_tokens
        
        return formatted
    
    def _optimize_context(self, context: ConversationContext) -> ConversationContext:
        """
        Optimize context when over token limit.
        Progressively reduce less important information.
        """
        # Priority order for reduction:
        # 1. Retrieved chunks (keep most relevant)
        # 2. Entity cards (keep most referenced)
        # 3. Facts (keep highest confidence)
        # 4. Older conversation turns
        # 5. Summary (truncate if needed)
        
        while context.estimate_tokens() > self.max_tokens:
            # Reduce retrieved chunks
            if len(context.retrieved_chunks) > 3:
                context.retrieved_chunks = context.retrieved_chunks[:3]
                continue
            
            # Reduce entity cards
            if len(context.entity_cards) > 5:
                context.entity_cards = context.entity_cards[:5]
                continue
            
            # Reduce facts
            if len(context.facts_and_constraints) > 10:
                context.facts_and_constraints = context.facts_and_constraints[:10]
                continue
            
            # Truncate recent messages
            if len(context.recent_messages) > 1000:
                context.recent_messages = context.recent_messages[-1000:]
                continue
            
            # Last resort: truncate summary
            if len(context.rolling_summary) > 200:
                context.rolling_summary = context.rolling_summary[:200] + "..."
                continue
            
            # If still over limit, break to avoid infinite loop
            break
        
        return context
```

## Usage Example

### File: `app/services/memory/memory_service.py`

```python
"""
Unified memory service that combines all memory components.
"""

import os
import redis
from typing import Optional
from .short_term_memory import ShortTermMemory, ConversationTurn
from .long_term_memory import LongTermMemory
from .rolling_summarizer import RollingSummarizer
from .context_manager import ContextWindowManager

class MemoryService:
    """
    Unified service for managing conversation memory.
    """
    
    def __init__(self):
        """Initialize all memory components"""
        # Redis for STM
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Initialize components
        self.stm = ShortTermMemory(self.redis_client)
        self.ltm = LongTermMemory(os.getenv('DATABASE_URL'))
        self.summarizer = RollingSummarizer(os.getenv('GEMINI_API_KEY'))
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
        if stats['turn_count'] % self.summarize_every_n_turns == 0:
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
        # Get recent turns
        recent_turns = self.stm.get_recent_turns(conversation_id)
        
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
    
    def _extract_and_store_entities(self,
                                   conversation_id: int,
                                   turns: List[ConversationTurn]):
        """Extract and store entity cards"""
        entities = self.summarizer.extract_entities(turns)
        for entity in entities:
            self.ltm.update_entity_card(conversation_id, entity)
```

This implementation guide provides a complete, production-ready memory system that follows the architecture design and best practices from the Perplexity recommendations.