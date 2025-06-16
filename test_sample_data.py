"""
Test script to explore the sample data and find good test queries.
"""
import os
from dotenv import load_dotenv
from cordisBased_RAG_function_new_V5 import CordisRAG

load_dotenv()

def test_sample_data():
    """Test what data is available in the sample database"""
    print("="*60)
    print("TESTING SAMPLE DATA AVAILABILITY")
    print("="*60)
    
    try:
        # Create V5 instance with local database
        rag = CordisRAG(
            ai_provider="gemini",
            use_local_db=True,
            database_url=os.getenv("DATABASE_URL")
        )
        
        # Test queries that should work with your sample data
        test_queries = [
            "What are some urban mobility projects?",
            "EIT projects in Europe",
            "Innovation projects in energy",
            "European research training fellowships",
            "Projects involving SMEs",
            "Marie Curie fellowship projects"
        ]
        
        print("\nTesting queries that should work with sample data:")
        print("-" * 50)
        
        for i, question in enumerate(test_queries, 1):
            print(f"\n🧪 Test {i}: {question}")
            try:
                response = rag.get_ai_response(question, max_projects_to_process=3, max_cordis_results=5)
                success = "I couldn't find any specific project data" not in response
                status = "✅ SUCCESS" if success else "❌ NO RESULTS"
                print(f"{status}: {len(response)} chars")
                if success:
                    print(f"Preview: {response[:150]}...")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

if __name__ == "__main__":
    test_sample_data()
