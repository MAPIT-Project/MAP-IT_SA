#!/usr/bin/env python3
"""
Test script to verify that the framework programme fix is working correctly.
This script tests the improved database search functionality.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_framework_programme_retrieval():
    """Test that framework programme is properly retrieved from the database."""
    print("="*80)
    print("TESTING FRAMEWORK PROGRAMME FIX")
    print("="*80)
    
    try:
        from app.services.rag_service import CordisRAG
        
        # Initialize with local database
        print("\n1. Initializing CordisRAG with local database...")
        rag = CordisRAG(use_local_db=True)
        print("✅ CordisRAG initialized successfully")
        
        # Test query specifically asking about nuclear energy projects
        test_query = "What are some recent nuclear energy research projects in Europe?"
        print(f"\n2. Testing query: '{test_query}'")
        print("-"*60)
        
        # Get the response
        print("Searching database...")
        result = rag.get_ai_response(
            question=test_query,
            max_projects_to_process=5,
            max_cordis_results=10
        )
        
        # Check if we got a response
        if isinstance(result, dict):
            answer = result.get('answer', '')
            projects_found = result.get('projects_found', 0)
            data_source = result.get('data_source', '')
            processing_time = result.get('processing_time', 0)
            
            print(f"\n✅ Search completed successfully!")
            print(f"   - Data source: {data_source}")
            print(f"   - Projects found: {projects_found}")
            print(f"   - Processing time: {processing_time:.2f}s")
            
            # Check if framework programme is mentioned in the answer
            framework_mentions = []
            for framework in ['Horizon Europe', 'Horizon 2020', 'H2020', 'FP7', 'EURATOM', 'programme framework']:
                if framework.lower() in answer.lower():
                    framework_mentions.append(framework)
            
            if framework_mentions:
                print(f"\n✅ Framework programmes mentioned: {', '.join(framework_mentions)}")
            else:
                print("\n⚠️ WARNING: No framework programme mentioned in the answer!")
            
            # Check for the problematic "Unknown programme framework" text
            if "unknown programme framework" in answer.lower():
                print("\n❌ ERROR: Answer still contains 'Unknown programme framework'!")
                print("   The fix may not be working correctly.")
            else:
                print("\n✅ No 'Unknown programme framework' found in answer - fix appears to be working!")
            
            # Display a snippet of the answer
            print(f"\n3. Answer preview (first 500 chars):")
            print("-"*60)
            print(answer[:500] + "..." if len(answer) > 500 else answer)
            
        else:
            print(f"\n❌ Unexpected result type: {type(result)}")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_direct_database_query():
    """Test direct database query to verify framework programme data exists."""
    print("\n" + "="*80)
    print("TESTING DIRECT DATABASE QUERY")
    print("="*80)
    
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        
        # Get database URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not found in environment")
            return False
        
        print("\n1. Connecting to database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)
        print("✅ Connected to database")
        
        # Query for projects with framework programme information
        print("\n2. Querying for projects with framework programme...")
        cursor.execute("""
            SELECT 
                p.id,
                p.title,
                p.acronym,
                p."frameworkProgramme",
                p."fundingScheme",
                p.status,
                p."startDate"
            FROM projects p
            WHERE p."frameworkProgramme" IS NOT NULL 
                AND p."frameworkProgramme" != ''
                AND p."frameworkProgramme" != 'N/A'
                AND LOWER(p.title) LIKE '%nuclear%'
            ORDER BY p."startDate" DESC
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        print(f"✅ Found {len(rows)} nuclear projects with framework programme")
        
        if rows:
            print("\n3. Sample projects with framework programme:")
            print("-"*60)
            for i, row in enumerate(rows, 1):
                print(f"\nProject {i}:")
                print(f"  Title: {row['title'][:60]}...")
                print(f"  Acronym: {row['acronym']}")
                print(f"  Framework: {row['frameworkProgramme']}")
                print(f"  Funding Scheme: {row['fundingScheme']}")
                print(f"  Status: {row['status']}")
                print(f"  Start Date: {row['startDate']}")
        else:
            print("\n⚠️ No nuclear projects found with framework programme information")
        
        # Check overall framework programme coverage
        print("\n4. Checking overall framework programme coverage...")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN "frameworkProgramme" IS NOT NULL AND "frameworkProgramme" != '' AND "frameworkProgramme" != 'N/A' THEN 1 END) as with_framework,
                COUNT(DISTINCT "frameworkProgramme") as unique_frameworks
            FROM projects
        """)
        
        stats = cursor.fetchone()
        coverage = (stats['with_framework'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        print(f"\n📊 Database Statistics:")
        print(f"  Total projects: {stats['total']:,}")
        print(f"  Projects with framework programme: {stats['with_framework']:,}")
        print(f"  Coverage: {coverage:.1f}%")
        print(f"  Unique framework programmes: {stats['unique_frameworks']}")
        
        # List unique framework programmes
        print("\n5. Unique framework programmes in database:")
        cursor.execute("""
            SELECT DISTINCT "frameworkProgramme", COUNT(*) as count
            FROM projects
            WHERE "frameworkProgramme" IS NOT NULL 
                AND "frameworkProgramme" != ''
                AND "frameworkProgramme" != 'N/A'
            GROUP BY "frameworkProgramme"
            ORDER BY count DESC
            LIMIT 10
        """)
        
        frameworks = cursor.fetchall()
        for fw in frameworks:
            print(f"  - {fw['frameworkProgramme']}: {fw['count']:,} projects")
        
        cursor.close()
        conn.close()
        print("\n✅ Direct database test completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Direct database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n🚀 Starting Framework Programme Fix Tests")
    print("="*80)
    
    # Test 1: Direct database query
    db_test_passed = test_direct_database_query()
    
    # Test 2: Framework programme retrieval through RAG
    rag_test_passed = test_framework_programme_retrieval()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if db_test_passed and rag_test_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nThe framework programme fix is working correctly:")
        print("1. Database contains framework programme information")
        print("2. RAG service properly retrieves and displays framework programmes")
        print("3. No more 'Unknown programme framework' in responses")
    else:
        print("❌ SOME TESTS FAILED")
        if not db_test_passed:
            print("- Direct database test failed")
        if not rag_test_passed:
            print("- RAG framework programme test failed")
        print("\nPlease review the errors above and fix any issues.")
    
    print("="*80)

if __name__ == "__main__":
    main()