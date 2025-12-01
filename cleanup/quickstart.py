#!/usr/bin/env python3
"""
Quick Start Script for Context-Aware AI System v2
This script helps you set up and test the new architecture components.
"""

import os
import sys
import psycopg2
import redis
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        'DATABASE_URL',
        'REDIS_HOST',
        'REDIS_PORT',
        'GEMINI_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        logger.info("Please set them in your .env file or export them")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def test_database_connection():
    """Test PostgreSQL connection and check if migrations are needed."""
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check if new tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'conversation_memory'
        """)
        
        if cursor.fetchone():
            logger.info("✅ Database is migrated and ready")
        else:
            logger.warning("⚠️ Database needs migration. Run: psql $DATABASE_URL < migration/schema_updates.sql")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        r.ping()
        logger.info("✅ Redis is connected and ready")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.info("Make sure Redis is running: sudo service redis-server start")
        return False

def create_minimal_memory_service():
    """Create a minimal working memory service for testing."""
    
    code = '''
import os
import redis
import json
from datetime import datetime

class MinimalMemoryService:
    """Minimal implementation to test the memory system."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        self.db_url = os.getenv('DATABASE_URL')
    
    def add_message(self, conversation_id: int, role: str, content: str):
        """Add a message to short-term memory."""
        key = f"stm:conv:{conversation_id}"
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        self.redis_client.rpush(key, json.dumps(message))
        self.redis_client.ltrim(key, -12, -1)  # Keep last 12 messages
        self.redis_client.expire(key, 86400)  # 24 hour TTL
        return True
    
    def get_recent_messages(self, conversation_id: int, n: int = 5):
        """Get recent messages from memory."""
        key = f"stm:conv:{conversation_id}"
        messages = self.redis_client.lrange(key, -n, -1)
        return [json.loads(msg) for msg in messages]
    
    def get_context(self, conversation_id: int):
        """Get formatted context for LLM."""
        messages = self.get_recent_messages(conversation_id)
        if not messages:
            return "No previous conversation."
        
        context_lines = []
        for msg in messages:
            role = msg['role'].upper()
            context_lines.append(f"{role}: {msg['content']}")
        
        return "\\n\\n".join(context_lines)

# Test the service
if __name__ == "__main__":
    service = MinimalMemoryService()
    
    # Test conversation
    conv_id = 12345
    
    # Add some messages
    service.add_message(conv_id, "user", "What is Horizon Europe?")
    service.add_message(conv_id, "assistant", "Horizon Europe is the EU's key funding programme for research and innovation with a budget of €95.5 billion.")
    service.add_message(conv_id, "user", "Tell me more about its budget")
    
    # Get context
    context = service.get_context(conv_id)
    print("\\nConversation Context:")
    print(context)
    
    print("\\n✅ Memory service is working!")
'''
    
    # Create the service file
    os.makedirs('app/services/memory', exist_ok=True)
    with open('app/services/memory/minimal_memory_service.py', 'w') as f:
        f.write(code)
    
    logger.info("✅ Created minimal memory service at app/services/memory/minimal_memory_service.py")
    return True

def test_minimal_implementation():
    """Test the minimal implementation."""
    try:
        # Import and test the minimal service
        sys.path.insert(0, os.getcwd())
        from app.services.memory.minimal_memory_service import MinimalMemoryService
        
        service = MinimalMemoryService()
        
        # Test adding and retrieving messages
        test_conv_id = 99999
        service.add_message(test_conv_id, "user", "Test message")
        messages = service.get_recent_messages(test_conv_id, 1)
        
        if messages and messages[0]['content'] == "Test message":
            logger.info("✅ Minimal memory service test passed!")
            return True
        else:
            logger.error("❌ Minimal memory service test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to test minimal implementation: {e}")
        return False

def create_example_env():
    """Create an example .env file if it doesn't exist."""
    if not os.path.exists('.env'):
        env_content = """# Context-Aware AI System Configuration

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mapit_sa

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Services
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional
SUPABASE_URL=
SUPABASE_KEY=
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        logger.info("✅ Created .env file - please update with your credentials")
        return False
    return True

def main():
    """Run the quickstart setup and tests."""
    print("""
╔══════════════════════════════════════════════════════════╗
║     Context-Aware AI System v2 - Quick Start Setup       ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    steps = [
        ("Creating .env file", create_example_env),
        ("Checking environment", check_environment),
        ("Testing database", test_database_connection),
        ("Testing Redis", test_redis_connection),
        ("Creating minimal service", create_minimal_memory_service),
        ("Testing implementation", test_minimal_implementation)
    ]
    
    all_passed = True
    for step_name, step_func in steps:
        logger.info(f"\n🔄 {step_name}...")
        if not step_func():
            all_passed = False
            if step_name == "Creating .env file":
                logger.info("Please update .env with your credentials and run again")
                break
    
    if all_passed:
        print("""
╔══════════════════════════════════════════════════════════╗
║                  🎉 Setup Complete! 🎉                    ║
║                                                          ║
║  Your system is ready for implementation!               ║
║                                                          ║
║  Next steps:                                            ║
║  1. Review the minimal memory service                   ║
║  2. Start implementing components from the guides       ║
║  3. Run: python app/services/memory/minimal_memory_service.py ║
║                                                          ║
║  Documentation:                                          ║
║  - IMPLEMENTATION_GUIDE_MEMORY_SYSTEM.md               ║
║  - IMPLEMENTATION_GUIDE_RAG_SYSTEM.md                  ║
║  - IMPLEMENTATION_GUIDE_INTEGRATION.md                 ║
╚══════════════════════════════════════════════════════════╝
        """)
    else:
        print("""
╔══════════════════════════════════════════════════════════╗
║                  ⚠️  Setup Incomplete                    ║
║                                                          ║
║  Please fix the issues above and run again.            ║
║                                                          ║
║  Common fixes:                                          ║
║  1. Start Redis: sudo service redis-server start       ║
║  2. Run migrations: psql $DATABASE_URL < migration/schema_updates.sql ║
║  3. Update .env with your API keys                     ║
╚══════════════════════════════════════════════════════════╝
        """)

if __name__ == "__main__":
    # Load .env if it exists
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
    
    main()