#!/usr/bin/env python3
"""
Test script for the Agentic Loop implementation.

Tests the self-correcting query processing flow.
"""

import asyncio
import sys
import os

# Add the app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

async def test_agentic_manager():
    """Test the AgenticManager directly."""
    print("=" * 60)
    print("🧪 Testing AgenticManager")
    print("=" * 60)
    
    try:
        from app.services.agents import AgenticManager
        
        manager = AgenticManager(max_iterations=3, sufficient_score=0.65)
        print("✅ AgenticManager initialized successfully")
        
        # Test queries
        test_queries = [
            "What are the consortium requirements for RIA?",
            "Tell me about hydrogen funding opportunities",
            "Can Switzerland participate in Horizon Europe?",
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"📝 Query: {query}")
            print("=" * 60)
            
            result = await manager.process_query(
                query=query,
                conversation_id="test_123"
            )
            
            print(f"\n📊 Result:")
            print(f"   Success: {result.get('success')}")
            print(f"   Iterations: {result.get('metadata', {}).get('iterations')}")
            print(f"   Quality Score: {result.get('metadata', {}).get('final_quality_score', 0):.2f}")
            print(f"   Confidence: {result.get('metadata', {}).get('confidence')}")
            print(f"   Time: {result.get('metadata', {}).get('total_time_ms', 0):.0f}ms")
            print(f"\n📝 Response preview:")
            response = result.get('response', '')
            print(f"   {response[:300]}..." if len(response) > 300 else f"   {response}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_streaming():
    """Test streaming progress updates."""
    print("\n" + "=" * 60)
    print("🌊 Testing Streaming Progress Updates")
    print("=" * 60)
    
    try:
        from app.services.agents import AgenticManager
        
        manager = AgenticManager(max_iterations=2)
        
        query = "What funding opportunities exist for clean energy research?"
        print(f"📝 Query: {query}\n")
        
        async for update in manager.process_query_streaming(
            query=query,
            conversation_id="test_stream"
        ):
            update_type = update.get('type', 'unknown')
            
            if update_type == 'status':
                print(f"   📡 {update.get('message')} [{update.get('phase')}]")
            elif update_type == 'progress':
                print(f"   📊 {update.get('message')}")
            elif update_type == 'response':
                print(f"\n   ✅ Final response received!")
                print(f"   Iterations: {update.get('metadata', {}).get('iterations')}")
                print(f"   Quality: {update.get('metadata', {}).get('quality_score', 0):.2f}")
            elif update_type == 'error':
                print(f"   ❌ Error: {update.get('error')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_component_chain():
    """Test individual components."""
    print("\n" + "=" * 60)
    print("🔧 Testing Individual Components")
    print("=" * 60)
    
    try:
        # Test ResultEvaluator
        from app.services.agents import ResultEvaluator, EvaluationResult
        
        evaluator = ResultEvaluator()
        
        # Good results
        good_results = {
            'vector': {
                'results': [
                    {'content': 'RIA requires at least 3 independent legal entities from 3 different EU member states.', 'score': 0.85},
                    {'content': 'Consortium must include universities and research organizations.', 'score': 0.82},
                    {'content': 'Budget allocation follows the 70/30 rule for research vs innovation.', 'score': 0.78},
                ]
            }
        }
        
        eval_result = evaluator.evaluate(
            query="What are the consortium requirements for RIA?",
            query_type="procedural",
            results=good_results,
            entities=["RIA", "consortium"]
        )
        
        print(f"\n📊 Evaluator test (good results):")
        print(f"   Score: {eval_result.score:.2f}")
        print(f"   Sufficient: {eval_result.is_sufficient}")
        print(f"   Reasons: {eval_result.reasons[:2]}")
        
        # Bad results
        bad_results = {
            'vector': {
                'results': [
                    {'content': 'Hello world', 'score': 0.3},
                ]
            }
        }
        
        eval_result_bad = evaluator.evaluate(
            query="What are the consortium requirements for RIA?",
            query_type="procedural",
            results=bad_results,
            entities=["RIA", "consortium"]
        )
        
        print(f"\n📊 Evaluator test (bad results):")
        print(f"   Score: {eval_result_bad.score:.2f}")
        print(f"   Sufficient: {eval_result_bad.is_sufficient}")
        print(f"   Suggestions: {eval_result_bad.suggestions[:2]}")
        
        # Test Reflector
        from app.services.agents import Reflector
        
        reflector = Reflector()
        
        reflection = reflector.reflect(
            query="What are the consortium requirements for RIA?",
            evaluation=eval_result_bad,
            current_plan={'steps': [{'source': 'vector', 'operation': 'semantic_search'}]},
            results=bad_results,
            failed_strategies=[],
            entities=["RIA", "consortium"]
        )
        
        print(f"\n🔍 Reflector test:")
        print(f"   Root cause: {reflection.root_cause.value}")
        print(f"   Action: {reflection.improvement_action.value}")
        print(f"   Suggested query: {reflection.suggested_query}")
        
        # Test Replanner
        from app.services.agents import Replanner
        
        replanner = Replanner()
        
        new_plan = replanner.replan(
            query="What are the consortium requirements for RIA?",
            reflection=reflection,
            failed_strategies=["sources=['vector']"],
            tried_queries=["What are the consortium requirements for RIA?"],
            tried_sources=["vector"],
            query_type="procedural",
            entities=["RIA", "consortium"]
        )
        
        print(f"\n📋 Replanner test:")
        print(f"   Strategy: {new_plan.get('strategy')}")
        print(f"   New sources: {[s.get('source') for s in new_plan.get('steps', [])]}")
        print(f"   Reasoning: {new_plan.get('reasoning')}")
        
        print("\n✅ All components working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 AGENTIC LOOP TEST SUITE")
    print("=" * 60)
    
    # Test components first
    component_ok = await test_component_chain()
    
    if component_ok:
        # Test full flow
        await test_agentic_manager()
        
        # Test streaming
        await test_streaming()
    
    print("\n" + "=" * 60)
    print("✨ Tests Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

