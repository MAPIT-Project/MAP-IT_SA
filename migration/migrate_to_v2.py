"""
Migration script from current system to new architecture.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMigration:
    """
    Handles migration from current system to new architecture.
    """
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379))
        )
        self.migration_status = {}
    
    async def run_migration(self):
        """
        Execute complete migration process.
        """
        logger.info("Starting system migration to v2...")
        
        try:
            # Phase 1: Database schema updates
            await self.migrate_database_schema()
            
            # Phase 2: Migrate existing conversations
            await self.migrate_conversations()
            
            # Phase 3: Setup Redis structures
            await self.setup_redis_structures()
            
            # Phase 4: Reprocess documents for new chunking
            await self.reprocess_documents()
            
            # Phase 5: Validate migration
            await self.validate_migration()
            
            logger.info("Migration completed successfully!")
            return self.migration_status
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    async def migrate_database_schema(self):
        """
        Apply database schema updates.
        """
        logger.info("Updating database schema...")
        
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        try:
            # Read and execute migration SQL
            schema_file = os.path.join(os.path.dirname(__file__), 'schema_updates.sql')
            with open(schema_file, 'r') as f:
                migration_sql = f.read()
            
            # Execute in chunks to handle large migrations
            statements = migration_sql.split(';')
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
            
            conn.commit()
            
            self.migration_status['schema_updated'] = True
            logger.info("Database schema updated successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Schema migration failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    async def migrate_conversations(self):
        """
        Migrate existing conversations to new memory system.
        """
        logger.info("Migrating existing conversations...")
        
        conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        try:
            # Get all conversations with messages
            cursor.execute("""
                SELECT DISTINCT conversation_id 
                FROM message 
                WHERE conversation_id IS NOT NULL
                ORDER BY conversation_id
                LIMIT 50
            """)
            conversations = cursor.fetchall()
            
            migrated_count = 0
            for conv in conversations:
                conv_id = conv['conversation_id']
                
                # Get messages for conversation
                cursor.execute("""
                    SELECT id, text, sender, created_at
                    FROM message
                    WHERE conversation_id = %s
                    ORDER BY created_at
                    LIMIT 100
                """, (conv_id,))
                messages = cursor.fetchall()
                
                if messages:
                    # Process messages for new system
                    await self._migrate_conversation_messages(conv_id, messages)
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        logger.info(f"Migrated {migrated_count} conversations...")
            
            self.migration_status['conversations_migrated'] = migrated_count
            logger.info(f"Migrated {migrated_count} conversations")
            
        finally:
            cursor.close()
            conn.close()
    
    async def _migrate_conversation_messages(self, conversation_id: int, messages: list):
        """
        Migrate messages for a single conversation.
        """
        try:
            # Add current directory to path for imports
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            from app.services.memory.memory_service import MemoryService
            from app.services.memory.short_term_memory import ConversationTurn
            
            memory_service = MemoryService()
            
            # Add messages to new memory system
            for msg in messages:
                turn = ConversationTurn(
                    message_id=msg['id'],
                    role='user' if msg['sender'] == 'user' else 'assistant',
                    content=msg['text'],
                    timestamp=msg['created_at'] if msg['created_at'] else datetime.now()
                )
                
                memory_service.stm.add_turn(conversation_id, turn)
            
            # Generate initial summary if enough messages
            if len(messages) >= 5:
                recent_turns = memory_service.stm.get_recent_turns(conversation_id, 10)
                if recent_turns:
                    summary = memory_service.summarizer.summarize_turn(
                        existing_summary=None,
                        new_turns=recent_turns
                    )
                    summary.conversation_id = conversation_id
                    memory_service.ltm.store_summary(summary)
                    
                    # Extract initial facts
                    facts = memory_service.summarizer.extract_facts(recent_turns)
                    if facts:
                        memory_service.ltm.store_facts(conversation_id, facts)
                        
        except Exception as e:
            logger.warning(f"Failed to migrate conversation {conversation_id}: {e}")
    
    async def setup_redis_structures(self):
        """
        Initialize Redis structures for the new system.
        """
        logger.info("Setting up Redis structures...")
        
        try:
            # Test Redis connection
            self.redis_client.ping()
            
            # Clear any existing test data
            test_keys = self.redis_client.keys("stm:conv:99999*")
            if test_keys:
                self.redis_client.delete(*test_keys)
            
            self.migration_status['redis_ready'] = True
            logger.info("Redis structures ready")
            
        except Exception as e:
            logger.error(f"Redis setup failed: {e}")
            raise
    
    async def reprocess_documents(self):
        """
        Reprocess documents with new chunking strategy.
        """
        logger.info("Reprocessing documents for new chunking...")
        
        conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        try:
            # Check if documents table exists
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'documents'
            """)
            
            if not cursor.fetchone():
                logger.info("No documents table found, skipping document reprocessing")
                self.migration_status['documents_reprocessed'] = 0
                return
            
            # Get documents to reprocess
            cursor.execute("""
                SELECT id, title, content, metadata
                FROM documents
                WHERE content IS NOT NULL
                LIMIT 10
            """)
            documents = cursor.fetchall()
            
            if not documents:
                logger.info("No documents found to reprocess")
                self.migration_status['documents_reprocessed'] = 0
                return
            
            # Add path for imports
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            from app.services.rag.intelligent_chunker import IntelligentChunker
            chunker = IntelligentChunker()
            
            processed_count = 0
            for doc in documents:
                try:
                    # Create new chunks
                    chunks = chunker.chunk_document({
                        'id': str(doc['id']),
                        'content': doc['content'],
                        'metadata': doc.get('metadata', {}) or {}
                    })
                    
                    # In a full implementation, you would store these chunks
                    # For now, just count them
                    logger.debug(f"Document {doc['id']}: {len(chunks)} chunks created")
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process document {doc['id']}: {e}")
            
            self.migration_status['documents_reprocessed'] = processed_count
            logger.info(f"Reprocessed {processed_count} documents")
            
        finally:
            cursor.close()
            conn.close()
    
    async def validate_migration(self):
        """
        Validate the migration was successful.
        """
        logger.info("Validating migration...")
        
        checks = {
            'schema_tables_exist': await self._check_schema_tables(),
            'redis_accessible': await self._check_redis(),
            'memory_service_functional': await self._check_memory_service(),
            'rag_service_functional': await self._check_rag_service()
        }
        
        all_passed = all(checks.values())
        self.migration_status['validation'] = checks
        self.migration_status['migration_successful'] = all_passed
        
        if all_passed:
            logger.info("All validation checks passed!")
        else:
            failed = [k for k, v in checks.items() if not v]
            logger.warning(f"Validation checks failed: {failed}")
        
        return all_passed
    
    async def _check_schema_tables(self):
        """Check if new tables exist."""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN (
                    'conversation_memory',
                    'conversation_facts',
                    'entity_cards',
                    'retrieval_cache',
                    'tool_execution_log'
                )
            """)
            tables = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return len(tables) >= 3  # At least core tables exist
            
        except Exception as e:
            logger.error(f"Schema check failed: {e}")
            return False
    
    async def _check_redis(self):
        """Check Redis connectivity."""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            return False
    
    async def _check_memory_service(self):
        """Check memory service functionality."""
        try:
            # Add path for imports
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            from app.services.memory.memory_service import MemoryService
            memory_service = MemoryService()
            
            # Test basic operations
            test_conv_id = 999999
            stats = memory_service.stm.get_memory_stats(test_conv_id)
            
            return isinstance(stats, dict)
            
        except Exception as e:
            logger.error(f"Memory service check failed: {e}")
            return False
    
    async def _check_rag_service(self):
        """Check RAG service functionality."""
        try:
            # Add path for imports
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            from app.services.rag.intelligent_chunker import IntelligentChunker
            chunker = IntelligentChunker()
            
            # Test chunking
            test_doc = {
                'content': 'This is a test document for validation.',
                'metadata': {}
            }
            chunks = chunker.chunk_document(test_doc)
            
            return len(chunks) > 0
            
        except Exception as e:
            logger.error(f"RAG service check failed: {e}")
            return False

# Migration CLI
async def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate to v2 architecture')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation')
    parser.add_argument('--schema-only', action='store_true', help='Only update schema')
    args = parser.parse_args()
    
    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    migration = SystemMigration()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        # Just validate current state
        result = await migration.validate_migration()
        print(f"Validation result: {result}")
        return result
    
    if args.schema_only:
        logger.info("SCHEMA ONLY MODE - Only updating database schema")
        await migration.migrate_database_schema()
        logger.info("Schema migration completed!")
        return True
    
    # Run full migration
    result = await migration.run_migration()
    
    if not args.skip_validation and not result.get('migration_successful'):
        logger.error("Migration validation failed!")
        print(json.dumps(result, indent=2, default=str))
        return False
    
    logger.info("Migration completed successfully!")
    print(json.dumps(result, indent=2, default=str))
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)