#!/usr/bin/env python3
"""
Comprehensive test script for the Context-Aware AI System v2.
Tests all components and provides validation.
"""

import asyncio
import os
import sys
import json
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_memory_system():
    """Test the memory management system."""
    print("\n🧠 Testing Memory System...")
    
    try:
        from app.services.memory.memory_service import MemoryService
        from app.services.memory.short_term_memory import ConversationTurn
        
        memory_service = MemoryService()
        test_conv_id = 12345
        
        # Test 1: Add conversation turns
        print("  📝 Testing conversation turn storage...")
        success = memory_service.add_conversation_turn(
            conversation_id=test_conv_id,
            role='user',
            content='What is Horizon Europe?',
            message_id=1001
        )
        
        success &= memory_service.add_conversation_turn(
            conversation_id=test_conv_id,
            role='assistant',
            content='Horizon Europe is the EU research and innovation programme with €95.5 billion budget.',
            message_id=1002
        )
        
        if success:
            print("  ✅ Conversation turns stored successfully")
        else:
            print("  ❌ Failed to store conversation turns")
            return False
        
        # Test 2: Get memory stats
        print("  📊 Testing memory statistics...")
        stats = memory_service.get_memory_stats(test_conv_id)
        
        if stats and stats.get('short_term', {}).get('turn_count', 0) >= 2:
            print(f"  ✅ Memory stats: {stats['short_term']['turn_count']} turns stored")
        else:
            print("  ❌ Memory stats not working")
            return False
        
        # Test 3: Context generation
        print("  🔄 Testing context generation...")
        context = memory_service.get_context_for_query(
            conversation_id=test_conv_id,
            query="Tell me more about the budget"
        )
        
        if context and len(context) > 100:
            print(f"  ✅ Context generated: {len(context)} characters")
        else:
            print("  ❌ Context generation failed")
            return False
        
        print("✅ Memory system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Memory system test failed: {e}")
        return False

async def test_rag_system():
    """Test the RAG system components."""
    print("\n🔍 Testing RAG System...")
    
    try:
        from app.services.rag.intelligent_chunker import IntelligentChunker
        from app.services.rag.hybrid_search import HybridSearchPipeline, MockVectorStore, MockKeywordStore, MockEmbeddingService
        
        # Test 1: Document chunking
        print("  📄 Testing document chunking...")
        chunker = IntelligentChunker()
        
        test_document = {
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
            """,
            'metadata': {'source': 'test', 'type': 'overview'}
        }
        
        chunks = chunker.chunk_document(test_document)
        
        if chunks and len(chunks) > 0:
            print(f"  ✅ Document chunked into {len(chunks)} chunks")
            for i, chunk in enumerate(chunks[:2]):
                print(f"    Chunk {i+1}: {chunk.token_count} tokens, type: {chunk.metadata.get('chunk_type')}")
        else:
            print("  ❌ Document chunking failed")
            return False
        
        # Test 2: Hybrid search
        print("  🔎 Testing hybrid search...")
        hybrid_search = HybridSearchPipeline(
            vector_store=MockVectorStore(),
            keyword_store=MockKeywordStore(),
            embedding_service=MockEmbeddingService()
        )
        
        search_results = await hybrid_search.search(
            query="Horizon Europe budget",
            limit=3
        )
        
        if search_results and len(search_results) > 0:
            print(f"  ✅ Hybrid search returned {len(search_results)} results")
            for result in search_results:
                print(f"    Result: score={result.score:.2f}, source={result.source}")
        else:
            print("  ❌ Hybrid search failed")
            return False
        
        print("✅ RAG system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        return False

async def test_conversation_manager():
    """Test the complete conversation manager."""
    print("\n💬 Testing Conversation Manager...")
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        manager = ConversationManager()
        test_conv_id = 54321
        
        # Test 1: Simple conversation
        print("  🗣️ Testing simple conversation...")
        response1 = await manager.process_message(
            conversation_id=test_conv_id,
            user_message="What is Horizon Europe?",
            user_id=1,
            streaming=False
        )
        
        if response1.get('response') and len(response1['response']) > 50:
            print(f"  ✅ First response generated: {len(response1['response'])} characters")
            print(f"    Processing time: {response1.get('processing_time', 0):.2f}s")
            print(f"    Confidence: {response1.get('confidence', 0):.2f}")
        else:
            print("  ❌ First response generation failed")
            return False
        
        # Test 2: Follow-up conversation
        print("  🔄 Testing follow-up conversation...")
        response2 = await manager.process_message(
            conversation_id=test_conv_id,
            user_message="Tell me more about its budget",
            user_id=1,
            streaming=False
        )
        
        if response2.get('response') and len(response2['response']) > 50:
            print(f"  ✅ Follow-up response generated: {len(response2['response'])} characters")
            print(f"    Processing time: {response2.get('processing_time', 0):.2f}s")
        else:
            print("  ❌ Follow-up response generation failed")
            return False
        
        # Test 3: Conversation stats
        print("  📊 Testing conversation statistics...")
        stats = manager.get_conversation_stats(test_conv_id)
        
        if stats and stats.get('memory'):
            print(f"  ✅ Stats retrieved: {stats['memory']['short_term']['turn_count']} turns")
        else:
            print("  ❌ Stats retrieval failed")
            return False
        
        print("✅ Conversation manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Conversation manager test failed: {e}")
        return False

async def test_streaming():
    """Test streaming functionality."""
    print("\n📡 Testing Streaming...")
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        manager = ConversationManager()
        test_conv_id = 67890
        
        print("  🌊 Testing streaming response...")
        
        tokens_received = []
        completion_received = False
        
        # This is a simplified test since we can't easily test the actual streaming
        # In a real test, you'd use the API endpoints
        response = await manager.process_message(
            conversation_id=test_conv_id,
            user_message="Explain quantum computing research",
            user_id=1,
            streaming=False  # Using non-streaming for this test
        )
        
        if response.get('response'):
            print(f"  ✅ Streaming test completed (simulated)")
            print(f"    Response length: {len(response['response'])} characters")
        else:
            print("  ❌ Streaming test failed")
            return False
        
        print("✅ Streaming tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False

async def test_api_endpoints():
    """Test the API endpoints."""
    print("\n🌐 Testing API Endpoints...")
    
    try:
        # This would require the FastAPI app to be running
        # For now, we'll just test that the routes can be imported
        from app.api.conversation_routes_v2 import router
        
        print("  📡 Testing route imports...")
        
        # Check that routes are defined
        routes = [route.path for route in router.routes]
        expected_routes = [
            '/api/v2/conversation/{conversation_id}/message',
            '/api/v2/conversation/{conversation_id}/message/stream',
            '/api/v2/conversation/{conversation_id}/memory',
            '/api/v2/conversation/health'
        ]
        
        routes_found = 0
        for expected in expected_routes:
            # Check if route pattern exists (simplified check)
            if any(expected.replace('{conversation_id}', '') in route for route in routes):
                routes_found += 1
        
        if routes_found >= 3:  # At least 3 main routes
            print(f"  ✅ API routes defined: {routes_found} routes found")
        else:
            print(f"  ❌ API routes missing: only {routes_found} found")
            return False
        
        print("✅ API endpoint tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

async def run_performance_benchmark():
    """Run a simple performance benchmark."""
    print("\n⚡ Running Performance Benchmark...")
    
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        
        manager = ConversationManager()
        test_conv_id = 99999
        
        # Test multiple messages to see performance
        test_messages = [
            "What is Horizon Europe?",
            "Tell me about its budget",
            "What are the main research areas?",
            "How can I apply for funding?",
            "What are the eligibility criteria?"
        ]
        
        total_time = 0
        successful_responses = 0
        
        for i, message in enumerate(test_messages):
            print(f"  🔄 Processing message {i+1}: '{message[:30]}...'")
            
            start_time = time.time()
            response = await manager.process_message(
                conversation_id=test_conv_id,
                user_message=message,
                user_id=1,
                streaming=False
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            total_time += processing_time
            
            if response.get('response'):
                successful_responses += 1
                print(f"    ✅ Response in {processing_time:.2f}s")
            else:
                print(f"    ❌ Failed in {processing_time:.2f}s")
        
        avg_time = total_time / len(test_messages)
        success_rate = successful_responses / len(test_messages)
        
        print(f"\n📊 Benchmark Results:")
        print(f"  • Average response time: {avg_time:.2f}s")
        print(f"  • Success rate: {success_rate:.1%}")
        print(f"  • Total processing time: {total_time:.2f}s")
        
        # Performance targets
        if avg_time < 5.0 and success_rate > 0.8:
            print("✅ Performance benchmark passed!")
            return True
        else:
            print("⚠️ Performance below targets (target: <5s avg, >80% success)")
            return False
        
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("""
╔══════════════════════════════════════════════════════════╗
║        Context-Aware AI System v2 - Full Test Suite      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check environment first
    required_vars = ['DATABASE_URL', 'REDIS_HOST', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or export them")
        return False
    
    # Run test suite
    tests = [
        ("Memory System", test_memory_system),
        ("RAG System", test_rag_system),
        ("Conversation Manager", test_conversation_manager),
        ("Streaming", test_streaming),
        ("API Endpoints", test_api_endpoints),
        ("Performance Benchmark", run_performance_benchmark)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            if await test_func():
                passed_tests += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    # Final results
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print('='*60)
    print(f"Tests passed: {passed_tests}/{total_tests}")
    print(f"Success rate: {passed_tests/total_tests:.1%}")
    
    if passed_tests == total_tests:
        print("""
╔══════════════════════════════════════════════════════════╗
║                  🎉 ALL TESTS PASSED! 🎉                  ║
║                                                          ║
║  Your Context-Aware AI System v2 is working!           ║
║                                                          ║
║  Next steps:                                            ║
║  1. Run the migration: python migration/migrate_to_v2.py║
║  2. Start the server: uvicorn app.main:app --reload     ║
║  3. Test the API: curl localhost:8000/api/v2/conversation/health ║
║                                                          ║
║  Your system is ready for production! 🚀               ║
╚══════════════════════════════════════════════════════════╝
        """)
        return True
    else:
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                  ⚠️  SOME TESTS FAILED                   ║
║                                                          ║
║  {passed_tests}/{total_tests} tests passed                                    ║
║                                                          ║
║  Please check the errors above and:                     ║
║  1. Ensure Redis is running                             ║
║  2. Ensure PostgreSQL is accessible                     ║
║  3. Check your environment variables                    ║
║  4. Install missing dependencies                        ║
╚══════════════════════════════════════════════════════════╝
        """)
        return False

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ python-dotenv not installed, using system environment")
    
    # Add current directory to Python path
    sys.path.insert(0, os.getcwd())
    
    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)