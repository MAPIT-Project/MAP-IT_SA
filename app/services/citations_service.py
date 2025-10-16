"""
Citations Service for storing and retrieving citations from streaming responses
"""
import os
import json
import psycopg2
from psycopg2.extras import DictCursor, RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CitationsService:
    """Service for managing citations in the message table"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the citations service"""
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
    
    def save_citations_from_stream_response(
        self, 
        conversation_id: int, 
        message_id: Optional[int],
        completion_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract and save citations from a streaming response completion data to the message table
        
        Args:
            conversation_id: The conversation ID
            message_id: The message ID (optional)
            completion_data: The completion data from the streaming response
            
        Returns:
            List of citations that were saved
        """
        citations = completion_data.get('citations', [])
        if not citations:
            return []
        
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # First, ensure the citations column exists
                    self._ensure_citations_column_exists(cursor)
                    
                    # If message_id is provided, update the existing message
                    if message_id:
                        cursor.execute("""
                            UPDATE message 
                            SET citations = %s
                            WHERE id = %s AND conversation_id = %s
                        """, (json.dumps(citations), message_id, conversation_id))
                        
                        rows_updated = cursor.rowcount
                        logger.info(f"Updated {rows_updated} message(s) with {len(citations)} citations")
                        
                    else:
                        # If no message_id, try to find the most recent assistant message for this conversation
                        cursor.execute("""
                            UPDATE message 
                            SET citations = %s
                            WHERE id = (
                                SELECT id FROM message 
                                WHERE conversation_id = %s AND sender = 'assistant'
                                ORDER BY created_at DESC
                                LIMIT 1
                            )
                            RETURNING id
                        """, (json.dumps(citations), conversation_id))
                        
                        result = cursor.fetchone()
                        if result:
                            logger.info(f"Updated message {result[0]} with {len(citations)} citations")
                        else:
                            logger.warning(f"No assistant message found for conversation {conversation_id}")
                    
                    conn.commit()
                    logger.info(f"Saved {len(citations)} citations to message table")
                    
        except Exception as e:
            logger.error(f"Error saving citations to message table: {e}")
            raise
        
        return citations
    
    def _ensure_citations_column_exists(self, cursor):
        """Ensure the citations column exists in the message table"""
        try:
            # Check if the citations column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'message' 
                AND column_name = 'citations'
            """)
            
            if not cursor.fetchone():
                # Add the citations column
                cursor.execute("""
                    ALTER TABLE message 
                    ADD COLUMN IF NOT EXISTS citations JSONB
                """)
                
                # Create index for better query performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_message_citations 
                    ON message USING GIN (citations)
                """)
                
                logger.info("Added citations column to message table")
                
        except Exception as e:
            logger.error(f"Error ensuring citations column exists: {e}")
            raise
    
    def get_citations_for_conversation(
        self, 
        conversation_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all citations for a conversation from the message table
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            List of citations from all messages in the conversation
        """
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT id, sender, text, citations, created_at
                        FROM message 
                        WHERE conversation_id = %s AND citations IS NOT NULL
                        ORDER BY created_at
                    """
                    
                    cursor.execute(query, (conversation_id,))
                    messages = cursor.fetchall()
                    
                    all_citations = []
                    for message in messages:
                        message_citations = message.get('citations', [])
                        if message_citations:
                            # Add message context to each citation
                            for citation in message_citations:
                                citation['message_id'] = message['id']
                                citation['message_sender'] = message['sender']
                                citation['message_created_at'] = message['created_at']
                            all_citations.extend(message_citations)
                    
                    return all_citations
                    
        except Exception as e:
            logger.error(f"Error getting citations for conversation {conversation_id}: {e}")
            return []
    
    def get_citations_for_message(
        self, 
        conversation_id: int, 
        message_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Get citations for a specific message
        
        Args:
            conversation_id: The conversation ID
            message_id: The message ID
            
        Returns:
            List of citations for the specific message
        """
        if not message_id:
            return []
            
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT citations
                        FROM message 
                        WHERE conversation_id = %s AND id = %s
                    """
                    
                    cursor.execute(query, (conversation_id, message_id))
                    result = cursor.fetchone()
                    
                    if result and result['citations']:
                        return result['citations']
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting citations for message {message_id}: {e}")
            return []
    
    def create_citations_column(self):
        """Create the citations column in the message table if it doesn't exist"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cursor:
                    # Read and execute the migration file
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(os.path.dirname(current_dir))
                    migration_path = os.path.join(project_root, 'migration', '007_add_citations_to_message_table.sql')
                    
                    with open(migration_path, 'r') as f:
                        migration_sql = f.read()
                    
                    cursor.execute(migration_sql)
                    conn.commit()
                    logger.info("Citations column added to message table successfully")
                    
        except Exception as e:
            logger.error(f"Error creating citations column: {e}")
            raise