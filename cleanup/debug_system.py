#!/usr/bin/env python3
"""
Debug script to check system components and identify issues.
"""

import os
import sys
import traceback
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check environment variables and configuration."""
    print("🔧 Checking Environment...")
    
    # Check critical environment variables
    critical_vars = [
        'GEMINI_API_KEY', 
        'OPENAI_API_KEY',
        'DEFAULT_AI_PROVIDER'
    ]
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            # Show partial key for security
            if 'key' in var.lower():
                display_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '[HIDDEN]'
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: Not set")
    
    print()

def check_imports():
    """Check if core modules can be imported."""
    print("📦 Checking Core Imports...")
    
    modules_to_test = [
        ('fastapi', 'FastAPI framework'),
        ('redis', 'Redis client'),
        ('google.generativeai', 'Gemini AI'),
        ('openai', 'OpenAI client'),
        ('psycopg2', 'PostgreSQL client'),
        ('app.core.config', 'App configuration'),
        ('app.services.memory.memory_service', 'Memory service'),
        ('app.services.conversation.conversation_manager', 'Conversation manager'),
        ('app.services.ai_intent_service', 'AI Intent service'),
    ]
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}: OK")
        except ImportError as e:
            print(f"  ❌ {module_name}: FAILED - {e}")
        except Exception as e:
            print(f"  ⚠️  {module_name}: ERROR - {e}")
    
    print()

def check_services():
    """Test individual service initialization."""
    print("🛠️ Checking Service Initialization...")
    
    # Test configuration
    try:
        from app.core.config import settings
        print(f"  ✅ Configuration: {settings.app_name} v{settings.app_version}")
    except Exception as e:
        print(f"  ❌ Configuration: {e}")
    
    # Test memory service  
    try:
        from app.services.memory.memory_service import MemoryService
        memory = MemoryService()
        print(f"  ✅ Memory Service: Initialized")
        
        # Test Redis connection
        if hasattr(memory, 'redis_client') and memory.redis_client:
            try:
                memory.redis_client.ping()
                print(f"  ✅ Redis Connection: OK")
            except Exception as e:
                print(f"  ❌ Redis Connection: {e}")
        
    except Exception as e:
        print(f"  ❌ Memory Service: {e}")
    
    # Test AI intent service
    try:
        from app.services.ai_intent_service import AIIntentService
        intent_service = AIIntentService()
        print(f"  ✅ AI Intent Service: Initialized")
    except Exception as e:
        print(f"  ❌ AI Intent Service: {e}")
    
    # Test conversation manager (this is the most complex one)
    try:
        from app.services.conversation.conversation_manager import ConversationManager
        manager = ConversationManager()
        print(f"  ✅ Conversation Manager: Initialized")
    except Exception as e:
        print(f"  ❌ Conversation Manager: {e}")
        traceback.print_exc()
    
    print()

def test_basic_functionality():
    """Test basic AI functionality."""
    print("🤖 Testing Basic AI Functionality...")
    
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("  ❌ No Gemini API key found")
            return
        
        genai.configure(api_key=api_key)
        
        # Test basic generation
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("What is 2+2? Respond with just the number.")
        
        if response and response.text:
            print(f"  ✅ Gemini Test: {response.text.strip()}")
        else:
            print(f"  ❌ Gemini Test: No response")
            
    except Exception as e:
        print(f"  ❌ Gemini Test: {e}")
    
    print()

def test_endpoints():
    """Test if we can at least import the endpoint definitions."""
    print("🌐 Testing Endpoint Definitions...")
    
    try:
        from app.api.conversation_routes_v2 import router
        print(f"  ✅ V2 Conversation Routes: {len(router.routes)} routes defined")
        
        # List the routes
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ', '.join(route.methods) if route.methods else 'GET'
                print(f"    - {methods} {route.path}")
        
    except Exception as e:
        print(f"  ❌ V2 Conversation Routes: {e}")
    
    print()

def main():
    """Run all diagnostic checks."""
    print("🏥 System Diagnostic Report")
    print("=" * 50)
    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print()
    
    check_environment()
    check_imports()
    check_services()
    test_basic_functionality()
    test_endpoints()
    
    print("✅ Diagnostic complete!")
    print("\nNext steps:")
    print("1. If all checks pass, try running the server with: python test_endpoints_directly.py")
    print("2. If there are import errors, check requirements installation")
    print("3. If Redis/DB errors, ensure those services are running")
    print("4. If API errors, check your API keys in .env file")

if __name__ == "__main__":
    main()