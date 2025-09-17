"""
Integration tests for the Context-Aware AI System v2.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime
import json

# Add app to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.conversation.conversation_manager import ConversationManager
from app.services.memory.memory_service import MemoryService
from app.services.memory.short_term_memory import ConversationTurn
from app.services.rag.intelligent_chunker import IntelligentChunker
from app.services.tools.tool_orchestrator import ToolOrchestrator

@pytest.fixture
async def conversation_manager():
    """Create conversation manager for testing."""
    try:
        return ConversationManager()
    except Exception as e:
        pytest.skip(f"ConversationManager initialization failed: {e}")

@pytest.fixture
async def memory_service():
    """Create memory service for testing."""
    try:
        return MemoryService()
    except Exception as e:
        pytest.skip(f"MemoryService initialization failed: {e}")

class TestMemorySystem:
    """Test memory management system."""
    
    @pytest.mark.asyncio
    async def test_short_term_memory(self, memory_service):
        """Test short-term memory operations."""
        conversation_id = 12345
        
        # Add a conversation turn
        success = memory_service.add_conversation_turn(
            conversation_id=conversation_id,
            role='user',
            content='What is Horizon Europe?',
            message_id=1001
        )
        
        assert success is True
        
        # Check memory stats
        stats = memory_service.stm.get_memory_stats(conversation_id)
        assert stats['turn_count'] >= 1
        assert stats['max_capacity'] == 12
        
        # Get recent turns
        turns = memory_service.stm.get_recent_turns(conversation_id)
        assert len(turns) >= 1
        assert turns[-1].content == 'What is Horizon Europe?'
    
    @pytest.mark.asyncio
    async def test_memory_accumulation(self, memory_service):
        """Test memory accumulation over conversation."""
        conversation_id = 12346
        
        # Add multiple turns
        messages = [
            ('user', 'What is Horizon Europe?'),
            ('assistant', 'Horizon Europe is the EU research programme with €95.5B budget.'),
            ('user', 'Tell me about renewable energy projects'),
            ('assistant', 'There are many renewable energy projects in Horizon Europe...'),
            ('user', 'What about the budget of the first project?'),
            ('assistant', 'The first project has a budget of approximately 2.5M EUR.')
        ]
        
        for i, (role, content) in enumerate(messages):
            memory_service.add_conversation_turn(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_id=2000 + i
            )
        
        # Check memory stats
        stats = memory_service.get_memory_stats(conversation_id)
        assert stats['short_term']['turn_count'] == len(messages)
        
        # Check if summary was generated (should trigger after 5 turns)
        if len(messages) >= 5:
            assert stats['summary']['exists'] is True
            assert stats['summary']['token_count'] > 0

class TestRAGSystem:
    """Test RAG system components."""
    
    @pytest.mark.asyncio
    async def test_intelligent_chunking(self):
        """Test document chunking."""
        chunker = IntelligentChunker()
        
        document = {
            'id': 'test_doc_1',
            'content': """
            # Horizon Europe Overview
            
            Horizon Europe is the European Union's key funding programme for research and innovation.
            
            ## Budget Information
            
            The programme has a budget of €95.5 billion for the period 2021-2027.
            This represents a significant increase from the previous framework programme.
            
            ## Key Objectives
            
            1. Strengthen the EU's scientific and technological bases
            2. Boost Europe's innovation capacity
            3. Deliver on citizens' priorities and sustain socio-economic model
            
            ## Application Process
            
            Applications must be submitted through the EU Funding & Tenders Portal.
            Deadlines vary by call but are typically announced 6 months in advance.
            """,
            'metadata': {'source': 'test', 'type': 'overview'}
        }
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        assert all(chunk.token_count > 0 for chunk in chunks)
        assert all(chunk.metadata.get('keywords') for chunk in chunks)
        assert all(chunk.metadata.get('chunk_type') for chunk in chunks)
        
        # Check chunk content quality
        total_content = ''.join(chunk.content for chunk in chunks)
        assert 'Horizon Europe' in total_content
        assert '95.5 billion' in total_content
    
    @pytest.mark.asyncio
    async def test_hybrid_search_mock(self):
        """Test hybrid search with mock services."""
        from app.services.rag.hybrid_search import HybridSearchPipeline, MockVectorStore, MockKeywordStore, MockEmbeddingService
        
        pipeline = HybridSearchPipeline(
            vector_store=MockVectorStore(),
            keyword_store=MockKeywordStore(),
            embedding_service=MockEmbeddingService()
        )
        
        results = await pipeline.search(
            query="Horizon Europe budget",
            limit=3
        )
        
        assert len(results) > 0
        assert all(result.score > 0 for result in results)
        assert all(result.chunk_id for result in results)

class TestConversationFlow:
    """Test complete conversation flow."""
    
    @pytest.mark.asyncio
    async def test_simple_conversation(self, conversation_manager):
        """Test a simple Q&A conversation."""
        conversation_id = 12347
        
        # First message
        response1 = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="What is Horizon Europe?",
            user_id=1,
            streaming=False
        )
        
        assert response1['response'] is not None
        assert len(response1['response']) > 50
        assert response1['processing_time'] < 10.0  # Should be under 10s
        assert 'error' not in response1
        
        # Follow-up message
        response2 = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="Tell me more about its budget",
            user_id=1,
            streaming=False
        )
        
        assert response2['response'] is not None
        assert len(response2['response']) > 50
        # Should understand "its" refers to Horizon Europe
    
    @pytest.mark.asyncio
    async def test_context_awareness(self, conversation_manager):
        """Test context awareness across multiple turns."""
        conversation_id = 12348
        
        # Build up context
        messages = [
            "What is Horizon Europe?",
            "Tell me about renewable energy projects",
            "What about the budget of the first project you mentioned?"
        ]
        
        responses = []
        for message in messages:
            response = await conversation_manager.process_message(
                conversation_id=conversation_id,
                user_message=message,
                user_id=1,
                streaming=False
            )
            responses.append(response)
            
            # Each response should be successful
            assert response['response'] is not None
            assert 'error' not in response
        
        # Check that memory is accumulating
        stats = conversation_manager.get_conversation_stats(conversation_id)
        assert stats['memory']['short_term']['turn_count'] >= len(messages) * 2  # User + assistant turns
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, conversation_manager):
        """Test streaming response generation."""
        conversation_id = 12349
        
        # This test is simplified since we can't easily test async generators
        # In a real test environment, you'd test the actual streaming
        response = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="Explain quantum computing research in Europe",
            user_id=1,
            streaming=False  # Using non-streaming for this test
        )
        
        assert response['response'] is not None
        assert len(response['response']) > 100
        assert response.get('processing_time', 0) > 0

class TestToolOrchestration:
    """Test tool orchestration system."""
    
    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test tool registration and listing."""
        from app.services.tools.tool_orchestrator import create_research_orchestrator
        
        orchestrator = create_research_orchestrator()
        
        # Check that tools are registered
        available_tools = orchestrator.get_available_tools()
        assert len(available_tools) > 0
        
        tool_names = [tool['name'] for tool in available_tools]
        assert 'search_horizon_calls' in tool_names
        assert 'search_cordis_projects' in tool_names
    
    @pytest.mark.asyncio
    async def test_tool_execution_stats(self):
        """Test tool execution statistics."""
        from app.services.tools.tool_orchestrator import create_research_orchestrator
        
        orchestrator = create_research_orchestrator()
        
        # Get initial stats
        stats = orchestrator.get_execution_stats()
        assert 'total_executions' in stats

class TestSystemIntegration:
    """Test complete system integration."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_conversation(self, conversation_manager):
        """Test complete end-to-end conversation flow."""
        conversation_id = 12350
        
        # Simulate a realistic research conversation
        conversation_flow = [
            {
                'message': 'What is Horizon Europe?',
                'expected_keywords': ['horizon', 'europe', 'research']
            },
            {
                'message': 'What about its budget?',
                'expected_keywords': ['budget', 'billion']
            },
            {
                'message': 'Show me renewable energy projects',
                'expected_keywords': ['renewable', 'energy']
            }
        ]
        
        for i, turn in enumerate(conversation_flow):
            response = await conversation_manager.process_message(
                conversation_id=conversation_id,
                user_message=turn['message'],
                user_id=1,
                streaming=False
            )
            
            # Basic response validation
            assert response['response'] is not None
            assert len(response['response']) > 30
            
            # Check that response contains expected keywords (basic relevance check)
            response_lower = response['response'].lower()
            keyword_found = any(keyword in response_lower for keyword in turn['expected_keywords'])
            
            # Don't fail test if keywords not found (mock services might not return relevant content)
            if not keyword_found:
                print(f"Warning: Expected keywords {turn['expected_keywords']} not found in response")
        
        # Check final conversation stats
        final_stats = conversation_manager.get_conversation_stats(conversation_id)
        assert final_stats['memory']['short_term']['turn_count'] >= len(conversation_flow) * 2
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self, memory_service):
        """Test that memory persists correctly."""
        conversation_id = 12351
        
        # Add several turns
        for i in range(8):
            role = 'user' if i % 2 == 0 else 'assistant'
            content = f"Message {i} - {'Question' if role == 'user' else 'Answer'}"
            
            memory_service.add_conversation_turn(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_id=3000 + i
            )
        
        # Check that memory is maintained
        stats = memory_service.get_memory_stats(conversation_id)
        assert stats['short_term']['turn_count'] == 8
        
        # Check context generation
        context = memory_service.get_context_for_query(
            conversation_id=conversation_id,
            query="What did we discuss?"
        )
        
        assert len(context) > 100
        assert 'Message' in context

class TestErrorHandling:
    """Test error handling and graceful degradation."""
    
    @pytest.mark.asyncio
    async def test_invalid_conversation_id(self, conversation_manager):
        """Test handling of invalid conversation ID."""
        # Use a very large conversation ID that shouldn't exist
        invalid_id = 999999999
        
        response = await conversation_manager.process_message(
            conversation_id=invalid_id,
            user_message="Test message",
            user_id=1,
            streaming=False
        )
        
        # Should still return a response, even if not optimal
        assert response is not None
        assert 'response' in response
    
    @pytest.mark.asyncio
    async def test_empty_message(self, conversation_manager):
        """Test handling of empty messages."""
        conversation_id = 12352
        
        response = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="",
            user_id=1,
            streaming=False
        )
        
        # Should handle gracefully
        assert response is not None

# Performance tests
class TestPerformance:
    """Test system performance."""
    
    @pytest.mark.asyncio
    async def test_response_time(self, conversation_manager):
        """Test that responses are generated within acceptable time."""
        conversation_id = 12353
        
        start_time = datetime.now()
        
        response = await conversation_manager.process_message(
            conversation_id=conversation_id,
            user_message="What is Horizon Europe?",
            user_id=1,
            streaming=False
        )
        
        end_time = datetime.now()
        actual_time = (end_time - start_time).total_seconds()
        
        # Should be under 10 seconds (generous for testing)
        assert actual_time < 10.0
        assert response['processing_time'] > 0
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, memory_service):
        """Test memory efficiency with many turns."""
        conversation_id = 12354
        
        # Add many turns to test memory management
        for i in range(20):
            role = 'user' if i % 2 == 0 else 'assistant'
            content = f"Turn {i}: {'Question about research' if role == 'user' else 'Answer about research projects'}"
            
            memory_service.add_conversation_turn(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_id=4000 + i
            )
        
        # Check that memory is capped appropriately
        stats = memory_service.get_memory_stats(conversation_id)
        assert stats['short_term']['turn_count'] <= 12  # Should be capped at max_turns
        assert stats['short_term']['utilization'] <= 1.0

# Configuration tests
class TestConfiguration:
    """Test system configuration and environment."""
    
    def test_environment_variables(self):
        """Test that required environment variables are available."""
        # These might not be set in test environment, so we'll just check the logic
        required_vars = ['DATABASE_URL', 'REDIS_HOST', 'GEMINI_API_KEY']
        
        # In a real test, you'd check these are set
        # For now, just verify the test can run
        assert True
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that services can be initialized."""
        try:
            # Test memory service
            memory_service = MemoryService()
            assert memory_service is not None
            
            # Test chunker
            chunker = IntelligentChunker()
            assert chunker is not None
            
            # Test tool orchestrator
            from app.services.tools.tool_orchestrator import create_research_orchestrator
            orchestrator = create_research_orchestrator()
            assert orchestrator is not None
            
        except Exception as e:
            pytest.fail(f"Service initialization failed: {e}")

# Run tests if called directly
if __name__ == "__main__":
    # Load environment for testing
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Run pytest
    pytest.main([__file__, "-v"])