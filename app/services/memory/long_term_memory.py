import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os


logger = logging.getLogger(__name__)
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
    
    def __init__(self, db_url: str = None):
        """
        Initialize LTM with database connection.
        
        Args:
            db_url: PostgreSQL connection string
        """
        self.db_url = db_url or os.getenv('DATABASE_URL')
        
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
            
            # Check if summary exists
            cursor.execute("""
                SELECT id FROM conversation_memory
                WHERE conversation_id = %s AND memory_type = 'summary'
            """, (summary.conversation_id,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing summary
                cursor.execute("""
                    UPDATE conversation_memory
                    SET content = %s, token_count = %s, updated_at = NOW()
                    WHERE conversation_id = %s AND memory_type = 'summary'
                """, (
                    json.dumps({
                        'summary_text': summary.summary_text,
                        'key_points': summary.key_points,
                        'covers_messages': summary.covers_messages
                    }),
                    summary.token_count,
                    summary.conversation_id
                ))
            else:
                # Insert new summary
                cursor.execute("""
                    INSERT INTO conversation_memory
                    (conversation_id, memory_type, content, token_count, created_at, updated_at)
                    VALUES (%s, 'summary', %s, %s, %s, NOW())
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
            logger.info(f"Database error in store_summary: {e}")
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
            logger.info(f"Database error in get_summary: {e}")
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
            logger.info(f"Database error in store_facts: {e}")
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
            logger.info(f"Database error in get_facts: {e}")
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
            logger.info(f"Database error in update_entity_card: {e}")
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
            logger.info(f"Database error in get_entity_cards: {e}")
            return []