#!/usr/bin/env python3
"""
Test script for project embeddings implementation.

This script tests:
1. Database table existence
2. Embedding service connectivity
3. LocalProjectSearchService vector search
4. Similar projects by embedding search
5. ToolAwareAgent semantic similarity tool

Usage:
    python scripts/test_project_embeddings.py
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_database_table():
    """Test if project_embeddings table exists."""
    print("\n" + "=" * 60)
    print("Test 1: Database Table Existence")
    print("=" * 60)

    try:
        import psycopg2
        from psycopg2.extras import DictCursor

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False

        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)

        # Check if table exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'project_embeddings'
            )
        """
        )
        table_exists = cursor.fetchone()[0]

        if table_exists:
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM project_embeddings")
            count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*) FROM project_embeddings
                WHERE embedding_status = 'completed' AND combined_embedding IS NOT NULL
            """
            )
            completed = cursor.fetchone()[0]

            print(f"✅ Table exists with {count} rows ({completed} completed embeddings)")
        else:
            print("❌ Table 'project_embeddings' does not exist")
            print("   Run: psql -f scripts/create_project_embeddings_table.sql")
            cursor.close()
            conn.close()
            return False

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


async def test_embedding_service():
    """Test if embedding service is working."""
    print("\n" + "=" * 60)
    print("Test 2: Embedding Service")
    print("=" * 60)

    try:
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        test_text = "Renewable energy integration in smart grids"

        embedding = service.generate_embedding(test_text)

        if embedding is not None and len(embedding) == 768:
            print(f"✅ Embedding service working (dimension: {len(embedding)})")
            return True
        else:
            print(f"❌ Invalid embedding: {type(embedding)}")
            return False

    except Exception as e:
        print(f"❌ Embedding service test failed: {e}")
        return False


async def test_vector_search():
    """Test vector search in LocalProjectSearchService."""
    print("\n" + "=" * 60)
    print("Test 3: Vector Search")
    print("=" * 60)

    try:
        from app.services.local_project_search_service import LocalProjectSearchService

        service = LocalProjectSearchService()

        # Check if embeddings are available
        has_embeddings = service._has_project_embeddings()
        print(f"   Has embeddings: {has_embeddings}")

        if not has_embeddings:
            print("⚠️ No embeddings available - run generate_project_embeddings.py first")
            return False

        # Test search
        results = await service.search_projects(
            query="renewable energy smart grid", include_semantic=True, limit=5
        )

        sources = results.get("sources_used", [])
        projects = results.get("projects", [])

        if "vector" in sources:
            print("✅ Vector search included in results")
            print(f"   Sources used: {sources}")
            print(f"   Projects found: {len(projects)}")
            if projects:
                print(f"   First result: {projects[0].get('title', 'N/A')[:60]}...")
            return True
        else:
            print(f"⚠️ Vector search not used (sources: {sources})")
            return False

    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_similar_projects():
    """Test similar projects by embedding."""
    print("\n" + "=" * 60)
    print("Test 4: Similar Projects by Embedding")
    print("=" * 60)

    try:
        import psycopg2

        from app.services.local_project_search_service import LocalProjectSearchService

        # First, get a project ID that has an embedding
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT project_id FROM project_embeddings
            WHERE embedding_status = 'completed'
            AND combined_embedding IS NOT NULL
            LIMIT 1
        """
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            print("⚠️ No projects with embeddings found")
            return False

        project_id = row[0]
        print(f"   Using project ID: {project_id}")

        service = LocalProjectSearchService()
        results = await service.find_similar_projects_by_embedding(project_id=project_id, limit=5)

        if results.get("success"):
            projects = results.get("projects", [])
            print(f"✅ Found {len(projects)} similar projects")
            if projects:
                for p in projects[:3]:
                    score = p.get("similarity_score", 0)
                    title = p.get("title", "N/A")[:50]
                    print(f"   - [{score:.3f}] {title}...")
            return True
        else:
            print(f"❌ Similar projects search failed: {results.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Similar projects test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tool_aware_agent():
    """Test ToolAwareAgent semantic similarity tool."""
    print("\n" + "=" * 60)
    print("Test 5: ToolAwareAgent Semantic Similarity Tool")
    print("=" * 60)

    try:
        import psycopg2

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Get a project ID
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT project_id FROM project_embeddings
            WHERE embedding_status = 'completed'
            AND combined_embedding IS NOT NULL
            LIMIT 1
        """
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            print("⚠️ No projects with embeddings found")
            return False

        project_id = row[0]

        agent = ToolAwareAgent()

        # Check if tool is registered
        if "find_semantically_similar_projects" in agent.tools:
            print("✅ Tool registered in agent")
        else:
            print("❌ Tool not registered in agent")
            return False

        # Execute the tool
        result = await agent._tool_find_semantically_similar_projects(
            {"project_id": project_id, "limit": 3}
        )

        if result.get("success"):
            print("✅ Tool execution successful")
            projects = result.get("projects", [])
            print(f"   Found {len(projects)} similar projects")
            return True
        else:
            print(f"❌ Tool execution failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ ToolAwareAgent test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Project Embeddings Implementation Tests")
    print("=" * 60)

    results = {}

    # Test 1: Database
    results["database"] = await test_database_table()

    # Test 2: Embedding service
    results["embedding_service"] = await test_embedding_service()

    # Only run remaining tests if database has embeddings
    if results["database"]:
        # Test 3: Vector search
        results["vector_search"] = await test_vector_search()

        # Test 4: Similar projects
        results["similar_projects"] = await test_similar_projects()

        # Test 5: Tool aware agent
        results["tool_agent"] = await test_tool_aware_agent()
    else:
        print("\n⚠️ Skipping remaining tests - no embeddings in database")
        print("   Run: python scripts/generate_project_embeddings.py")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name}: {status}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Project embeddings implementation is ready.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
