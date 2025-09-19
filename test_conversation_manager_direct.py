#!/usr/bin/env python3
"""
Direct test of the conversation manager improvements without requiring the full server.
Tests the enhanced project search detection logic.
"""

import asyncio
import sys
import os

# Add the app directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.conversation.conversation_manager import ConversationManager
from services.memory.memory_service import MemoryService
from services.rag.response_generator import GroundedResponseGenerator
from services.tools.tool_orchestrator import create_research_orchestrator
from services.response.unified_formatter import UnifiedResponseFormatter
from services.rag.hybrid_search import HybridSearchPipeline, MockVectorStore, MockKeywordStore, MockEmbeddingService
from services.rag.conversation_retriever import ConversationAwareRetriever, RetrievalContext
from services.memory.context_manager import ConversationContext

class MockRedisClient:
    """Mock Redis client for testing."""
    def ping(self):
        return True

    def get(self, key):
        return None

    def setex(self, key, ttl, value):
        return True

class DirectConversationTester:
    """Test the conversation manager directly without the full server."""

    def __init__(self):
        # Mock the dependencies
        self.memory_service = MemoryService()
        self.memory_service.redis_client = MockRedisClient()

        # Initialize other components
        self.response_generator = GroundedResponseGenerator(gemini_api_key="mock_key")
        self.tool_orchestrator = create_research_orchestrator(cache_client=MockRedisClient())
        self.unified_formatter = UnifiedResponseFormatter()

        # Create conversation manager instance
        self.manager = ConversationManager.__new__(ConversationManager)
        self.manager.memory_service = self.memory_service
        self.manager.response_generator = self.response_generator
        self.manager.tool_orchestrator = self.tool_orchestrator
        self.manager.unified_formatter = self.unified_formatter
        self.manager.config = {'max_retrieval_chunks': 4}

    async def test_project_search_detection(self):
        """Test the improved project search detection."""

        print("🧪 Testing Direct Conversation Manager")
        print("=" * 60)

        # Test questions that should trigger CORDIS project search
        test_questions = [
            "Can you find me projects on renewable energy?",
            "Show me successful AI projects funded by Horizon Europe",
            "What are some completed projects in biotechnology?",
            "Find projects related to climate change adaptation",
            "Show me projects that received funding over 5 million euros",
            "What are some innovative projects in quantum computing?",
            "Find me projects that involve international collaboration",
            "Show me projects focused on sustainable transport",
            "What are some breakthrough projects in health research?",
            "Find projects that combine AI with healthcare applications"
        ]

        conversation_id = 99999

        for i, question in enumerate(test_questions, 1):
            print(f"\n📋 Test {i}: '{question}'")
            print("-" * 50)

            try:
                # Test the combined intent-context-tool planner
                intent_analysis, context, tool_plan = await self.manager._combined_intent_context_tool_planner(
                    conversation_id=conversation_id,
                    user_message=question
                )

                print(f"   Intent Type: {intent_analysis.get('intent_type', 'unknown')}")
                print(f"   Requires Tools: {intent_analysis.get('requires_tools', False)}")
                print(f"   Confidence: {intent_analysis.get('confidence', 0.0):.2f}")

                if tool_plan:
                    tool_names = [tool.tool_name for tool in tool_plan]
                    print(f"   ✅ TOOLS PLANNED: {tool_names}")

                    # Check if CORDIS search is planned
                    if 'search_cordis_projects' in tool_names:
                        print("   🎯 SUCCESS: CORDIS project search correctly triggered!")
                    else:
                        print("   ⚠️  WARNING: Tools planned but not CORDIS search")
                else:
                    print("   ❌ NO TOOLS: Conversational response only")
                    print("   ⚠️  This might be an issue for project search questions")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "=" * 60)
        print("✅ Direct testing completed!")

async def main():
    """Main test function."""
    print("🔬 Direct Conversation Manager Test")
    print("Testing project search detection improvements")
    print()

    tester = DirectConversationTester()
    await tester.test_project_search_detection()

if __name__ == "__main__":
    asyncio.run(main())