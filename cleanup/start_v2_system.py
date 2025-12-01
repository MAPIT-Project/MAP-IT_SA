#!/usr/bin/env python3
"""
Startup script for Context-Aware AI System v2.
Handles setup, validation, and server startup.
"""

import os
import sys
import subprocess
import time
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'redis',
        'psycopg2',
        'google.generativeai',
        'fastapi',
        'uvicorn'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.error(f"Missing packages: {', '.join(missing)}")
        logger.info("Install with: pip install -r requirements-v2.txt")
        return False
    
    logger.info("✅ All required packages are installed")
    return True

def check_services():
    """Check if required services are running."""
    services_ok = True
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379))
        )
        r.ping()
        logger.info("✅ Redis is running")
    except Exception as e:
        logger.error(f"❌ Redis not accessible: {e}")
        logger.info("Start Redis with: docker run -d -p 6379:6379 redis:latest")
        services_ok = False
    
    # Check PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        conn.close()
        logger.info("✅ PostgreSQL is accessible")
    except Exception as e:
        logger.error(f"❌ PostgreSQL not accessible: {e}")
        logger.info("Check your DATABASE_URL environment variable")
        services_ok = False
    
    return services_ok

def check_environment():
    """Check environment variables."""
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
        
        # Create .env template if it doesn't exist
        if not os.path.exists('.env'):
            create_env_template()
            logger.info("Created .env template - please fill in your values")
        
        return False
    
    logger.info("✅ All environment variables are set")
    return True

def create_env_template():
    """Create .env template file."""
    template = """# Context-Aware AI System v2 Configuration

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mapit_sa

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Services
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional Services
SUPABASE_URL=
SUPABASE_KEY=

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

# Application
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
"""
    
    with open('.env', 'w') as f:
        f.write(template)

async def run_system_test():
    """Run a quick system test."""
    logger.info("🧪 Running system test...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        from app.services.conversation.conversation_manager import ConversationManager
        
        manager = ConversationManager()
        
        # Quick test
        response = await manager.process_message(
            conversation_id=99999,
            user_message="Hello, can you help me?",
            user_id=1,
            streaming=False
        )
        
        if response.get('response'):
            logger.info("✅ System test passed!")
            return True
        else:
            logger.error("❌ System test failed - no response generated")
            return False
            
    except Exception as e:
        logger.error(f"❌ System test failed: {e}")
        return False

def start_server():
    """Start the FastAPI server."""
    logger.info("🚀 Starting FastAPI server...")
    
    try:
        # Start uvicorn server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", os.getenv('API_HOST', '0.0.0.0'),
            "--port", os.getenv('API_PORT', '8000'),
            "--reload"
        ]
        
        logger.info(f"Starting server with command: {' '.join(cmd)}")
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")

async def main():
    """Main startup sequence."""
    print("""
╔══════════════════════════════════════════════════════════╗
║     Context-Aware AI System v2 - Startup Sequence       ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment loaded from .env")
    except ImportError:
        logger.info("Using system environment (dotenv not available)")
    
    # Run checks
    checks = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies),
        ("Services", check_services)
    ]
    
    all_checks_passed = True
    for check_name, check_func in checks:
        logger.info(f"🔍 Checking {check_name}...")
        if not check_func():
            all_checks_passed = False
            break
    
    if not all_checks_passed:
        print("""
╔══════════════════════════════════════════════════════════╗
║                  ⚠️  Setup Incomplete                    ║
║                                                          ║
║  Please fix the issues above before starting.          ║
║                                                          ║
║  Quick fixes:                                           ║
║  • pip install -r requirements-v2.txt                  ║
║  • docker run -d -p 6379:6379 redis:latest             ║
║  • Update .env with your API keys                      ║
╚══════════════════════════════════════════════════════════╝
        """)
        return False
    
    # Run system test
    logger.info("🧪 Running system validation...")
    if not await run_system_test():
        print("""
╔══════════════════════════════════════════════════════════╗
║                  ❌ System Test Failed                   ║
║                                                          ║
║  The system is not working correctly.                  ║
║  Please check the logs above for details.              ║
╚══════════════════════════════════════════════════════════╝
        """)
        return False
    
    # All good - start server
    print("""
╔══════════════════════════════════════════════════════════╗
║                  🎉 System Ready! 🎉                     ║
║                                                          ║
║  All checks passed! Starting the server...             ║
║                                                          ║
║  API Endpoints:                                         ║
║  • Health: http://localhost:8000/api/v2/conversation/health ║
║  • Chat: http://localhost:8000/api/v2/conversation/{id}/message ║
║  • Stream: http://localhost:8000/api/v2/conversation/{id}/message/stream ║
║  • Docs: http://localhost:8000/docs                    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Start the server
    start_server()
    return True

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)