#!/usr/bin/env python3
"""
Simple conversation test to verify the system works without external dependencies.
"""

import asyncio
import sys
import os
from pathlib import Path
import time

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_basic_conversation():
    """Test basic conversation functionality."""
    
    print("🔄 Testing Basic Conversation System")
    print("=" * 50)
    
    try:
        # Import conversation manager
        from app.services.conversation.conversation_manager import ConversationManager
        
        print("✅ ConversationManager imported successfully")
        
        # Initialize
        print("🔧 Initializing ConversationManager...")
        manager = ConversationManager()
        print("✅ ConversationManager initialized")
        
        # Test queries that a research manager might ask
        test_queries = [
            "What is Horizon Europe?",
            "Find AI projects in healthcare",
            "What are the main funding opportunities?",
            "How can I apply for research funding?",
            "What are the success metrics for projects?"
        ]
        
        conversation_id = 1
        user_id = 1
        
        print(f"\n📋 Testing {len(test_queries)} research manager queries...")
        
        results = []
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Query {i}: {query} ---")
            
            try:
                start_time = time.time()
                
                # Process message
                result = await manager.process_message(
                    conversation_id=conversation_id,
                    user_message=query,
                    user_id=user_id,
                    streaming=False
                )
                
                processing_time = time.time() - start_time
                
                if isinstance(result, dict) and 'response' in result:
                    response = result['response']
                    
                    # Basic quality checks
                    quality_score = 0.0
                    
                    # Length check
                    if len(response) > 100:
                        quality_score += 0.3
                    if len(response) > 300:
                        quality_score += 0.2
                    
                    # Content relevance (simple keyword matching)
                    query_words = query.lower().split()
                    response_lower = response.lower()
                    relevant_words = sum(1 for word in query_words if word in response_lower)
                    quality_score += (relevant_words / len(query_words)) * 0.3
                    
                    # Research-specific terms
                    research_terms = ['research', 'project', 'funding', 'europe', 'horizon', 'innovation']
                    research_found = sum(1 for term in research_terms if term in response_lower)
                    quality_score += (min(research_found, 3) / 3) * 0.2
                    
                    quality_score = min(quality_score, 1.0)
                    
                    # Store result
                    test_result = {
                        'query': query,
                        'response': response,
                        'processing_time': processing_time,
                        'quality_score': quality_score,
                        'response_length': len(response),
                        'metadata': {
                            'memory_stats': result.get('memory_stats', {}),
                            'retrieval_stats': result.get('retrieval_stats', {}),
                            'tools_executed': result.get('tools_executed', []),
                            'confidence': result.get('confidence', 0.0)
                        }
                    }
                    
                    results.append(test_result)
                    
                    # Print result
                    print(f"✅ Success! ({processing_time:.2f}s, Quality: {quality_score:.2f})")
                    print(f"Length: {len(response)} chars")
                    print(f"Tools used: {result.get('tools_executed', [])}")
                    print(f"Confidence: {result.get('confidence', 0.0)}")
                    print(f"Response preview: {response[:200]}...")
                    
                else:
                    print(f"❌ Unexpected result format: {type(result)}")
                    results.append({
                        'query': query,
                        'error': 'Invalid result format',
                        'processing_time': processing_time
                    })
                
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                results.append({
                    'query': query,
                    'error': str(e),
                    'processing_time': time.time() - start_time
                })
        
        # Generate summary
        successful_results = [r for r in results if 'response' in r]
        total_tests = len(results)
        success_count = len(successful_results)
        
        print(f"\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {success_count} ({success_count/total_tests*100:.1f}%)")
        print(f"Failed: {total_tests - success_count}")
        
        if successful_results:
            avg_quality = sum(r['quality_score'] for r in successful_results) / len(successful_results)
            avg_time = sum(r['processing_time'] for r in successful_results) / len(successful_results)
            avg_length = sum(r['response_length'] for r in successful_results) / len(successful_results)
            
            print(f"\nPerformance Metrics:")
            print(f"Average Quality Score: {avg_quality:.2f}/1.0")
            print(f"Average Processing Time: {avg_time:.2f}s")
            print(f"Average Response Length: {avg_length:.0f} characters")
            
            # Tool usage analysis
            all_tools_used = []
            for r in successful_results:
                tools = r.get('metadata', {}).get('tools_executed', [])
                if isinstance(tools, list):
                    all_tools_used.extend(tools)
                elif tools:  # Non-empty value
                    all_tools_used.append(str(tools))
            
            unique_tools = set(all_tools_used)
            print(f"Tools Used: {', '.join(unique_tools) if unique_tools else 'None detected'}")
            
            # Quality assessment
            print(f"\nQuality Assessment:")
            if avg_quality >= 0.8:
                print("✅ Excellent - System provides high-quality responses")
            elif avg_quality >= 0.6:
                print("✅ Good - System provides adequate responses") 
            elif avg_quality >= 0.4:
                print("⚠️ Fair - System needs improvement")
            else:
                print("❌ Poor - System requires significant improvement")
        
        # Failed tests
        failed_tests = [r for r in results if 'error' in r]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for failed in failed_tests:
                print(f"  - '{failed['query']}': {failed['error']}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if success_count == total_tests:
            print("✅ All tests passed - system is functional")
        elif success_count >= total_tests * 0.8:
            print("✅ Most tests passed - minor improvements needed")
        else:
            print("⚠️ Many tests failed - system needs debugging")
        
        if successful_results:
            if avg_quality < 0.6:
                print("🎯 Focus on improving response quality and relevance")
            if avg_time > 10:
                print("⚡ Consider optimizing response time")
            if not any(r.get('metadata', {}).get('tools_executed') for r in successful_results):
                print("🔧 Investigate tool integration - no tools appear to be executing")
        
        # Test memory functionality
        print(f"\n🧠 Testing Memory Functionality...")
        
        try:
            # First message to establish context
            context_result = await manager.process_message(
                conversation_id=99,  # Different conversation ID
                user_message="Tell me about AI projects in Horizon Europe",
                user_id=user_id,
                streaming=False
            )
            
            # Follow-up that requires memory
            memory_result = await manager.process_message(
                conversation_id=99,
                user_message="What was the budget for those projects we just discussed?",
                user_id=user_id,
                streaming=False
            )
            
            if isinstance(memory_result, dict) and 'response' in memory_result:
                memory_response = memory_result['response'].lower()
                
                # Check if it references previous conversation
                memory_indicators = ['previous', 'earlier', 'discussed', 'mentioned', 'those projects']
                memory_working = any(indicator in memory_response for indicator in memory_indicators)
                
                if memory_working:
                    print("✅ Memory system appears to be working")
                else:
                    print("⚠️ Memory system may not be working properly")
                    print(f"Response: {memory_result['response'][:200]}...")
            else:
                print("❌ Memory test failed - no valid response")
                
        except Exception as e:
            print(f"❌ Memory test error: {e}")
        
        return results
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed.")
        return []
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Main function."""
    print("🧪 Simple Conversation AI Test")
    print("Testing the conversation system directly...")
    
    # Run the test
    results = asyncio.run(test_basic_conversation())
    
    print(f"\n🏁 Test completed! Results available for analysis.")
    
    if results:
        successful = len([r for r in results if 'response' in r])
        total = len(results)
        
        if successful == total:
            print("🎉 All tests passed! System appears to be working well.")
        elif successful >= total * 0.5:
            print("👍 Most tests passed. System is functional with some issues.")
        else:
            print("⚠️ Many tests failed. System needs attention.")
    else:
        print("❌ No results - system may have critical issues.")

if __name__ == "__main__":
    main()