#!/usr/bin/env python3
"""
Test script for OpenRouter integration.
This script tests the OpenRouter functionality without making actual API calls.
"""

import os
import sys
from unittest.mock import patch

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_openrouter_configuration():
    """Test that OpenRouter configuration is properly loaded."""
    print("🧪 Testing OpenRouter configuration...")

    from app.core.config import settings

    # Check that OpenRouter configuration exists
    assert hasattr(settings, 'openrouter_api_key'), "OpenRouter API key config missing"
    assert hasattr(settings, 'openrouter_model'), "OpenRouter model config missing"
    assert hasattr(settings, 'openrouter_base_url'), "OpenRouter base URL config missing"

    print("✅ OpenRouter configuration loaded successfully")
    print(f"   Model: {settings.openrouter_model}")
    print(f"   Base URL: {settings.openrouter_base_url}")

    # Verify the specific model is set
    assert settings.openrouter_model == "x-ai/grok-4-fast:free", f"Expected 'x-ai/grok-4-fast:free', got '{settings.openrouter_model}'"
    print("✅ Grok-4-Fast model configured correctly")


def test_ai_agent_openrouter():
    """Test AI agent with OpenRouter provider."""
    print("\n🧪 Testing AI agent with OpenRouter...")

    from app.services.ai_agent import AIAgent

    # Test initialization with OpenRouter
    agent = AIAgent(ai_provider="openrouter", openrouter_api_key="test_key")

    assert agent.ai_provider == "openrouter", "AI provider not set correctly"
    assert agent.openrouter_api_key == "test_key", "OpenRouter API key not set correctly"

    print("✅ AI agent OpenRouter initialization successful")


def test_ai_query_parser_openrouter():
    """Test AI query parser with OpenRouter provider."""
    print("\n🧪 Testing AI query parser with OpenRouter...")

    from app.services.ai_query_parser import AIQueryParser

    # Test initialization with OpenRouter
    parser = AIQueryParser(ai_provider="openrouter", openrouter_api_key="test_key")

    assert parser.ai_provider == "openrouter", "AI provider not set correctly"
    assert parser.openai_client is not None, "OpenAI client not initialized for OpenRouter"

    print("✅ AI query parser OpenRouter initialization successful")


def test_response_generator_openrouter():
    """Test response generator with OpenRouter provider."""
    print("\n🧪 Testing response generator with OpenRouter...")

    from app.services.rag.response_generator import GroundedResponseGenerator

    # Test initialization with OpenRouter
    generator = GroundedResponseGenerator(ai_provider="openrouter", openrouter_api_key="test_key")

    assert generator.ai_provider == "openrouter", "AI provider not set correctly"
    assert generator.openai_client is not None, "OpenAI client not initialized for OpenRouter"

    print("✅ Response generator OpenRouter initialization successful")


def test_rolling_summarizer_openrouter():
    """Test rolling summarizer with OpenRouter provider."""
    print("\n🧪 Testing rolling summarizer with OpenRouter...")

    from app.services.memory.rolling_summarizer import RollingSummarizer

    # Test initialization with OpenRouter
    summarizer = RollingSummarizer(ai_provider="openrouter", openrouter_api_key="test_key")

    assert summarizer.ai_provider == "openrouter", "AI provider not set correctly"
    assert summarizer.openai_client is not None, "OpenAI client not initialized for OpenRouter"

    print("✅ Rolling summarizer OpenRouter initialization successful")


def test_conversation_manager_openrouter():
    """Test conversation manager with OpenRouter provider."""
    print("\n🧪 Testing conversation manager with OpenRouter...")

    # Mock environment variables
    with patch.dict(os.environ, {
        'DEFAULT_AI_PROVIDER': 'openrouter',
        'OPENROUTER_API_KEY': 'test_key',
        'GEMINI_API_KEY': 'test_key'
    }):
        from app.services.conversation.conversation_manager import ConversationManager

        # Test initialization
        manager = ConversationManager()

        assert manager.response_generator.ai_provider == "openrouter", "AI provider not set correctly"

        print("✅ Conversation manager OpenRouter initialization successful")


def test_provider_switching():
    """Test switching between AI providers."""
    print("\n🧪 Testing AI provider switching...")

    from app.services.ai_agent import AIAgent

    # Test Gemini provider
    gemini_agent = AIAgent(ai_provider="gemini", gemini_api_key="test_key")
    assert gemini_agent.ai_provider == "gemini", "Gemini provider not set correctly"

    # Test OpenRouter provider
    openrouter_agent = AIAgent(ai_provider="openrouter", openrouter_api_key="test_key")
    assert openrouter_agent.ai_provider == "openrouter", "OpenRouter provider not set correctly"

    # Test fallback to Gemini for unsupported provider
    fallback_agent = AIAgent(ai_provider="unsupported", gemini_api_key="test_key")
    assert fallback_agent.ai_provider == "gemini", f"Expected 'gemini', got '{fallback_agent.ai_provider}'"

    print("✅ AI provider switching works correctly")


def main():
    """Run all tests."""
    print("🚀 Starting OpenRouter integration tests...\n")

    try:
        test_openrouter_configuration()
        test_ai_agent_openrouter()
        test_ai_query_parser_openrouter()
        test_response_generator_openrouter()
        test_rolling_summarizer_openrouter()
        test_conversation_manager_openrouter()
        test_provider_switching()

        print("\n🎉 All OpenRouter integration tests passed!")
        print("\n📋 Summary:")
        print("   ✅ Configuration loading")
        print("   ✅ AI agent integration")
        print("   ✅ AI query parser integration")
        print("   ✅ Response generator integration")
        print("   ✅ Rolling summarizer integration")
        print("   ✅ Conversation manager integration")
        print("   ✅ Provider switching")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())