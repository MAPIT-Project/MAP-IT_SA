# 🔗 System Integration & Migration Guide

## Overview
This guide provides the complete integration of all components and a migration strategy from your current system to the new architecture.

## 1. Integrated Conversation Manager

### File: `app/services/conversation/conversation_manager.py`

```python
"""
Main conversation management system that orchestrates all components.
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import json
import logging

from ..memory.memory_service import MemoryService
from ..memory.context_manager import ConversationContext
from ..rag.conversation_retriever import ConversationAwareRetriever, RetrievalContext
from ..rag.response_generator import GroundedResponseGenerator
from ..tools.tool_orchestrator import ToolOrchestrator

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Central manager for all conversation operations.
    Coordinates memory, RAG, and tool systems.
    """
    
    def __init__(self):
        """Initialize all subsystems"""
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
        self.tool_orchestrator = ToolOrchestrator()
        
        # Configuration
        self.config = self._load_configuration()
    
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
            
            # Phase 5: Retrieve relevant information
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
                return await self._generate_streaming_response(
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

        try:
            response = self.response_generator.model.generate_content(prompt)
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
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
        Retrieve relevant information using conversation-aware RAG.
        """
        # Get conversation metadata
        summary = self.memory_service.ltm.get_summary(conversation_id)
        facts = self.memory_service.ltm.get_facts(conversation_id)
        entities = self.memory_service.ltm.get_entity_cards(conversation_id)
        
        # Build retrieval context
        retrieval_context = RetrievalContext(
            conversation_id=conversation_id,
            current_query=query,
            conversation_summary=summary.summary_text if summary else "",
            recent_topics=[fact.fact_content for fact in facts[:3]],
            entity_mentions=[entity.entity_name for entity in entities[:5]],
            search_history=[]  # Could track this separately
        )
        
        # Perform retrieval
        results = await self.retriever.retrieve(
            context=retrieval_context,
            max_chunks=self.config.get('max_retrieval_chunks', 4),
            use_cache=True
        )
        
        return results
    
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
        # Implementation depends on your database setup
        # This is a placeholder
        import random
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
        # Implementation depends on your database setup
        import random
        return random.randint(1000, 9999)
    
    def _init_hybrid_search(self):
        """Initialize hybrid search pipeline."""
        from ..rag.hybrid_search import HybridSearchPipeline
        from ..services.supabase_client import SupabaseVectorStore
        from ..services.embedding_service import EmbeddingService
        
        return HybridSearchPipeline(
            vector_store=SupabaseVectorStore(),
            keyword_store=None,  # Your PostgreSQL connection
            embedding_service=EmbeddingService()
        )
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load system configuration."""
        return {
            'max_retrieval_chunks': 4,
            'max_context_tokens': 8000,
            'summarize_every_n_turns': 5,
            'cache_ttl': 3600
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            'response': "I apologize, but I encountered an error processing your request.",
            'error': error_message,
            'success': False
        }
```

## 2. Updated API Routes

### File: `app/api/conversation_routes_v2.py`

```python
"""
Updated conversation routes using the new architecture.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import asyncio

from ..services.conversation.conversation_manager import ConversationManager

router = APIRouter(prefix="/api/v2/conversation", tags=["conversation-v2"])

# Initialize conversation manager (singleton)
conversation_manager = ConversationManager()

class MessageRequest(BaseModel):
    message: str
    include_context: bool = True
    memory_strategy: str = "full"  # full, summary, minimal
    retrieval_config: Optional[Dict[str, Any]] = None
    tools_enabled: Optional[list] = None

class MessageResponse(BaseModel):
    response: str
    memory_used: Dict[str, Any]
    retrieval_stats: Dict[str, Any]
    tools_executed: list
    processing_time_ms: float
    confidence: float
    grounded: bool
    citations: list

@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: int,
    request: MessageRequest,
    user_id: int = 1  # Would come from auth
) -> MessageResponse:
    """
    Send a message and get a response using the new architecture.
    """
    try:
        # Process message
        result = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message=request.message,
            user_id=user_id,
            streaming=False
        )
        
        # Format response
        return MessageResponse(
            response=result['response'],
            memory_used=result.get('memory_stats', {}),
            retrieval_stats=result.get('retrieval_stats', {}),
            tools_executed=result.get('tools_executed', []),
            processing_time_ms=result.get('processing_time', 0) * 1000,
            confidence=result.get('confidence', 0.0),
            grounded=result.get('grounded', False),
            citations=result.get('citations', [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: int,
    request: MessageRequest,
    user_id: int = 1
):
    """
    Send a message and stream the response.
    """
    async def generate_stream():
        try:
            async for chunk in conversation_manager.process_message(
                conversation_id=conversation_id,
                user_message=request.message,
                user_id=user_id,
                streaming=True
            ):
                # Format as SSE
                if chunk.get('type') == 'token':
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk.get('type') == 'complete':
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk.get('type') == 'error':
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
        except Exception as e:
            error_chunk = {'type': 'error', 'error': str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/{conversation_id}/memory")
async def get_conversation_memory(conversation_id: int):
    """
    Get memory statistics for a conversation.
    """
    try:
        stm_stats = conversation_manager.memory_service.stm.get_memory_stats(conversation_id)
        summary = conversation_manager.memory_service.ltm.get_summary(conversation_id)
        facts = conversation_manager.memory_service.ltm.get_facts(conversation_id)
        entities = conversation_manager.memory_service.ltm.get_entity_cards(conversation_id)
        
        return {
            'short_term_memory': stm_stats,
            'summary': {
                'text': summary.summary_text if summary else None,
                'key_points': summary.key_points if summary else [],
                'token_count': summary.token_count if summary else 0
            },
            'facts': [
                {
                    'type': fact.fact_type,
                    'content': fact.fact_content,
                    'confidence': fact.confidence
                }
                for fact in facts[:10]
            ],
            'entities': [
                {
                    'type': entity.entity_type,
                    'name': entity.entity_name,
                    'references': entity.reference_count
                }
                for entity in entities[:10]
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{conversation_id}/memory")
async def clear_conversation_memory(conversation_id: int):
    """
    Clear memory for a conversation.
    """
    try:
        success = conversation_manager.memory_service.stm.clear_conversation(conversation_id)
        return {"success": success, "message": "Memory cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 3. Migration Strategy

### File: `migration/migrate_to_v2.py`

```python
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
            with open('migration/schema_updates.sql', 'r') as f:
                migration_sql = f.read()
            
            cursor.execute(migration_sql)
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
            # Get all conversations
            cursor.execute("""
                SELECT DISTINCT conversation_id 
                FROM message 
                ORDER BY conversation_id
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
            
            self.migration_status['conversations_migrated'] = migrated_count
            logger.info(f"Migrated {migrated_count} conversations")
            
        finally:
            cursor.close()
            conn.close()
    
    async def _migrate_conversation_messages(self, conversation_id: int, messages: list):
        """
        Migrate messages for a single conversation.
        """
        from app.services.memory.memory_service import MemoryService
        from app.services.memory.short_term_memory import ConversationTurn
        
        memory_service = MemoryService()
        
        # Add messages to new memory system
        for msg in messages:
            turn = ConversationTurn(
                message_id=msg['id'],
                role='user' if msg['sender'] == 'user' else 'assistant',
                content=msg['text'],
                timestamp=msg['created_at']
            )
            
            memory_service.stm.add_turn(conversation_id, turn)
        
        # Generate initial summary if enough messages
        if len(messages) >= 5:
            recent_turns = memory_service.stm.get_recent_turns(conversation_id, 10)
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
    
    async def setup_redis_structures(self):
        """
        Initialize Redis structures for the new system.
        """
        logger.info("Setting up Redis structures...")
        
        try:
            # Create Redis indices if needed
            # This depends on your Redis setup
            
            # Test Redis connection
            self.redis_client.ping()
            
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
            # Get documents to reprocess
            cursor.execute("""
                SELECT id, title, content, metadata
                FROM documents
                WHERE processing_status = 'completed'
                LIMIT 100
            """)
            documents = cursor.fetchall()
            
            from app.services.rag.intelligent_chunker import IntelligentChunker
            chunker = IntelligentChunker()
            
            processed_count = 0
            for doc in documents:
                # Create new chunks
                chunks = chunker.chunk_document({
                    'id': doc['id'],
                    'content': doc['content'],
                    'metadata': doc.get('metadata', {})
                })
                
                # Store new chunks (implementation depends on your setup)
                # ...
                
                processed_count += 1
            
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
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        try:
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
            return len(tables) == 5
            
        finally:
            cursor.close()
            conn.close()
    
    async def _check_redis(self):
        """Check Redis connectivity."""
        try:
            return self.redis_client.ping()
        except:
            return False
    
    async def _check_memory_service(self):
        """Check memory service functionality."""
        try:
            from app.services.memory.memory_service import MemoryService
            memory_service = MemoryService()
            
            # Test basic operations
            test_conv_id = 999999
            stats = memory_service.stm.get_memory_stats(test_conv_id)
            
            return True
        except:
            return False
    
    async def _check_rag_service(self):
        """Check RAG service functionality."""
        try:
            from app.services.rag.intelligent_chunker import IntelligentChunker
            chunker = IntelligentChunker()
            
            # Test chunking
            test_doc = {
                'content': 'This is a test document.',
                'metadata': {}
            }
            chunks = chunker.chunk_document(test_doc)
            
            return len(chunks) > 0
        except:
            return False

# Migration CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate to v2 architecture')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation')
    args = parser.parse_args()
    
    migration = SystemMigration()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        # Just validate current state
        asyncio.run(migration.validate_migration())
    else:
        # Run full migration
        result = asyncio.run(migration.run_migration())
        
        if not args.skip_validation and not result.get('migration_successful'):
            logger.error("Migration validation failed!")
            sys.exit(1)
        
        logger.info("Migration completed!")
        print(json.dumps(result, indent=2))
```

## 4. Configuration & Environment Setup

### File: `.env.example`

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mapit_sa

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI Services
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
GOOGLE_EMBEDDING_API_KEY=your-embedding-api-key

# Application
APP_ENV=development
APP_DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# Memory Configuration
STM_MAX_TURNS=12
STM_TTL_HOURS=24
SUMMARIZE_EVERY_N_TURNS=5

# RAG Configuration
CHUNK_SIZE=500
CHUNK_OVERLAP=100
MAX_RETRIEVAL_CHUNKS=4
RETRIEVAL_CACHE_TTL=3600

# Context Window
MAX_CONTEXT_TOKENS=8000
```

### File: `docker-compose.yml`

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_HOST=redis
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./app:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mapit_sa
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migration/schema_updates.sql:/docker-entrypoint-initdb.d/01-schema.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

## 5. Testing Framework

### File: `tests/test_integration.py`

```python
"""
Integration tests for the new system.
"""

import pytest
import asyncio
from datetime import datetime

from app.services.conversation.conversation_manager import ConversationManager
from app.services.memory.memory_service import MemoryService

@pytest.fixture
async def conversation_manager():
    """Create conversation manager for testing."""
    return ConversationManager()

@pytest.fixture
async def memory_service():
    """Create memory service for testing."""
    return MemoryService()

class TestConversationFlow:
    """Test complete conversation flow."""
    
    @pytest.mark.asyncio
    async def test_simple_conversation(self, conversation_manager):
        """Test a simple Q&A conversation."""
        conversation_id = 12345
        
        # First message
        response1 = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="What is Horizon Europe?",
            user_id=1,
            streaming=False
        )
        
        assert response1['response'] is not None
        assert response1['grounded'] is True
        assert response1['processing_time'] < 5.0
        
        # Follow-up message
        response2 = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="Tell me more about its budget",
            user_id=1,
            streaming=False
        )
        
        assert response2['response'] is not None
        assert 'budget' in response2['response'].lower()
    
    @pytest.mark.asyncio
    async def test_memory_accumulation(self, memory_service):
        """Test memory accumulation over conversation."""
        conversation_id = 12346
        
        # Add multiple turns
        for i in range(10):
            from app.services.memory.short_term_memory import ConversationTurn
            turn = ConversationTurn(
                message_id=i,
                role='user' if i % 2 == 0 else 'assistant',
                content=f"Message {i}",
                timestamp=datetime.now()
            )
            memory_service.stm.add_turn(conversation_id, turn)
        
        # Check memory stats
        stats = memory_service.stm.get_memory_stats(conversation_id)
        assert stats['turn_count'] == 10
        
        # Check summary generation
        recent_turns = memory_service.stm.get_recent_turns(conversation_id)
        summary = memory_service.summarizer.summarize_turn(
            existing_summary=None,
            new_turns=recent_turns
        )
        
        assert summary is not None
        assert len(summary.key_points) > 0
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, conversation_manager):
        """Test streaming response generation."""
        conversation_id = 12347
        
        tokens_received = []
        async for chunk in conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="Explain quantum computing",
            user_id=1,
            streaming=True
        ):
            if chunk.get('type') == 'token':
                tokens_received.append(chunk['content'])
            elif chunk.get('type') == 'complete':
                assert chunk.get('processing_time') is not None
        
        # Check we received tokens
        assert len(tokens_received) > 0
        complete_response = ''.join(tokens_received)
        assert len(complete_response) > 100

class TestRAGSystem:
    """Test RAG system components."""
    
    @pytest.mark.asyncio
    async def test_intelligent_chunking(self):
        """Test document chunking."""
        from app.services.rag.intelligent_chunker import IntelligentChunker
        
        chunker = IntelligentChunker()
        
        document = {
            'content': """
            # Introduction
            This is a test document about Horizon Europe.
            
            ## Objectives
            The main objectives are:
            - Support research
            - Foster innovation
            - Address global challenges
            
            ## Budget
            The total budget is 95.5 billion EUR.
            """,
            'metadata': {'source': 'test'}
        }
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        assert all(chunk.token_count > 0 for chunk in chunks)
        assert all(chunk.metadata.get('keywords') for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid search functionality."""
        from app.services.rag.hybrid_search import HybridSearchPipeline
        
        # This would need mock vector and keyword stores
        # Implementation depends on your test setup
        pass

class TestMigration:
    """Test migration process."""
    
    @pytest.mark.asyncio
    async def test_migration_validation(self):
        """Test migration validation checks."""
        from migration.migrate_to_v2 import SystemMigration
        
        migration = SystemMigration()
        
        # Test individual checks
        redis_ok = await migration._check_redis()
        assert redis_ok is True
        
        # Test full validation (may fail if not migrated)
        # validation_result = await migration.validate_migration()
```

## Summary

This integration guide provides:

1. **Complete Conversation Manager** that orchestrates all components
2. **Updated API routes** following the new architecture
3. **Migration strategy** to move from current system to v2
4. **Configuration setup** with Docker support
5. **Testing framework** for validation

The system is now ready for implementation following the phased approach outlined in the architecture document.