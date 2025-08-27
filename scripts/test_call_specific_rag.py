#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced Call-Specific RAG system.
Tests various Horizon Europe call and topic queries to ensure the system works correctly.
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CallSpecificRAGTester:
    """Test the enhanced Call-Specific RAG system."""
    
    def __init__(self):
        from app.services.enhanced_rag_service import HorizonEuropeRAG
        
        self.rag_system = HorizonEuropeRAG()
        logger.info("✅ Call-Specific RAG Tester initialized")
    
    def get_test_queries(self) -> List[Dict[str, Any]]:
        """Get comprehensive test queries for Horizon Europe calls and topics."""
        
        return [
            # Specific call identifier queries
            {
                "query": "What are the requirements for HORIZON-CL4-2024-DATA-01-01?",
                "type": "specific_call",
                "expected_intent": "SPECIFIC_CALL",
                "expected_call_id": "HORIZON-CL4-2024-DATA-01-01"
            },
            {
                "query": "Tell me about HORIZON-CL5-2024-CLIMATE-01 eligibility criteria",
                "type": "specific_call",
                "expected_intent": "SPECIFIC_CALL",
                "expected_call_id": "HORIZON-CL5-2024-CLIMATE-01"
            },
            {
                "query": "HORIZON-CL2-2024-DEMOCRACY-01-05 submission deadline",
                "type": "specific_call",
                "expected_intent": "SPECIFIC_CALL",
                "expected_call_id": "HORIZON-CL2-2024-DEMOCRACY-01-05"
            },
            
            # Topic identifier queries
            {
                "query": "Information about HORIZON-CL4-2024-DATA-01",
                "type": "specific_topic",
                "expected_intent": "SPECIFIC_TOPIC",
                "expected_call_id": "HORIZON-CL4-2024-DATA-01"
            },
            {
                "query": "HORIZON-CL6-2024-BIODIVERSITY-01 funding details",
                "type": "specific_topic",
                "expected_intent": "SPECIFIC_TOPIC",
                "expected_call_id": "HORIZON-CL6-2024-BIODIVERSITY-01"
            },
            
            # Cluster-specific queries
            {
                "query": "What are the health cluster calls for 2024?",
                "type": "cluster_specific",
                "expected_intent": "CLUSTER_SPECIFIC",
                "expected_cluster": "health"
            },
            {
                "query": "Digital transformation topics in Horizon Europe",
                "type": "cluster_specific",
                "expected_intent": "CLUSTER_SPECIFIC",
                "expected_cluster": "digital"
            },
            {
                "query": "Climate energy mobility funding opportunities",
                "type": "cluster_specific",
                "expected_intent": "CLUSTER_SPECIFIC",
                "expected_cluster": "climate"
            },
            {
                "query": "EIC Accelerator grant application process",
                "type": "cluster_specific",
                "expected_intent": "CLUSTER_SPECIFIC",
                "expected_cluster": "eic"
            },
            {
                "query": "ERC grants for frontier research",
                "type": "cluster_specific",
                "expected_intent": "CLUSTER_SPECIFIC",
                "expected_cluster": "erc"
            },
            
            # General call/topic queries
            {
                "query": "What are some open calls for AI research?",
                "type": "general_call",
                "expected_intent": "GENERAL_CALL"
            },
            {
                "query": "Funding opportunities for renewable energy",
                "type": "general_call",
                "expected_intent": "GENERAL_CALL"
            },
            {
                "query": "How to apply for Horizon Europe grants?",
                "type": "general_call",
                "expected_intent": "GENERAL_CALL"
            },
            
            # Eligibility and requirements queries
            {
                "query": "What are the eligibility criteria for Horizon Europe?",
                "type": "eligibility",
                "expected_intent": "GENERAL_QUERY"
            },
            {
                "query": "Consortium requirements for collaborative projects",
                "type": "requirements",
                "expected_intent": "GENERAL_QUERY"
            },
            {
                "query": "Evaluation criteria for Horizon Europe proposals",
                "type": "evaluation",
                "expected_intent": "GENERAL_QUERY"
            }
        ]
    
    def test_intent_detection(self):
        """Test intent detection for call-specific queries."""
        logger.info("🧪 Testing Intent Detection...")
        
        test_queries = self.get_test_queries()
        results = []
        
        for test in test_queries:
            query = test["query"]
            expected_intent = test["expected_intent"]
            
            # Test intent detection
            intent_type, call_identifier, confidence = self.rag_system.detect_call_intent(query)
            
            result = {
                "query": query,
                "expected_intent": expected_intent,
                "detected_intent": intent_type,
                "call_identifier": call_identifier,
                "confidence": confidence,
                "intent_match": intent_type == expected_intent,
                "timestamp": datetime.now().isoformat()
            }
            
            # Check for specific call ID if expected
            if "expected_call_id" in test:
                result["call_id_match"] = call_identifier == test["expected_call_id"]
            if "expected_cluster" in test:
                result["cluster_match"] = call_identifier == test["expected_cluster"]
            
            results.append(result)
            
            status = "✅" if result["intent_match"] else "❌"
            logger.info(f"{status} Query: '{query}' -> Detected: {intent_type} (Expected: {expected_intent}, Confidence: {confidence:.2f})")
        
        # Calculate success rate
        successful = sum(1 for r in results if r["intent_match"])
        success_rate = successful / len(results) if results else 0
        
        logger.info(f"📊 Intent Detection Results: {successful}/{len(results)} successful ({success_rate:.1%})")
        
        return results, success_rate
    
    async def test_call_specific_queries(self):
        """Test call-specific query handling."""
        logger.info("🧪 Testing Call-Specific Query Handling...")
        
        test_queries = self.get_test_queries()
        results = []
        
        for test in test_queries:
            query = test["query"]
            
            logger.info(f"📋 Testing: '{query}'")
            
            try:
                # Handle the query
                result = self.rag_system.handle_call_query(query)
                
                test_result = {
                    "query": query,
                    "type": test["type"],
                    "success": result.get("success", False),
                    "intent": result.get("intent"),
                    "data_source": result.get("data_source"),
                    "confidence": result.get("confidence", 0),
                    "chunks_used": result.get("chunks_used", 0),
                    "answer_length": len(result.get("answer", "")),
                    "processing_time": result.get("processing_time", 0),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Check if we got a meaningful answer
                answer = result.get("answer", "")
                if answer and len(answer) > 100 and not answer.startswith("I couldn't find"):
                    test_result["meaningful_answer"] = True
                    test_result["answer_preview"] = answer[:200] + "..." if len(answer) > 200 else answer
                else:
                    test_result["meaningful_answer"] = False
                    test_result["answer_preview"] = answer
                
                results.append(test_result)
                
                status = "✅" if test_result["meaningful_answer"] else "❌"
                logger.info(f"{status} Result: {test_result['chunks_used']} chunks, {test_result['confidence']:.2f} confidence, {len(answer)} chars")
                
                # Small delay between tests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Test failed for '{query}': {e}")
                results.append({
                    "query": query,
                    "type": test["type"],
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # Calculate success metrics
        successful_tests = sum(1 for r in results if r.get("meaningful_answer", False))
        success_rate = successful_tests / len(results) if results else 0
        
        logger.info(f"📊 Query Handling Results: {successful_tests}/{len(results)} successful ({success_rate:.1%})")
        
        return results, success_rate
    
    def generate_test_report(self, intent_results, query_results, intent_success_rate, query_success_rate):
        """Generate comprehensive test report."""
        report = {
            "test_date": datetime.now().isoformat(),
            "system_version": "Call-Specific RAG Enhanced",
            "summary": {
                "total_tests": len(intent_results) + len(query_results),
                "intent_detection_success_rate": intent_success_rate,
                "query_handling_success_rate": query_success_rate,
                "overall_success_rate": (intent_success_rate + query_success_rate) / 2
            },
            "intent_detection_results": intent_results,
            "query_handling_results": query_results,
            "recommendations": self._generate_recommendations(intent_results, query_results)
        }
        
        # Save report
        report_dir = Path("test_reports")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"call_specific_rag_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Test report saved to: {report_file}")
        
        return report
    
    def _generate_recommendations(self, intent_results, query_results):
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Analyze intent detection issues
        intent_issues = [r for r in intent_results if not r.get("intent_match", False)]
        if intent_issues:
            recommendations.append({
                "type": "intent_detection",
                "issue": f"{len(intent_issues)} intent detection failures",
                "suggestion": "Review intent detection patterns and add more specific call/topic identifier patterns"
            })
        
        # Analyze query handling issues
        query_issues = [r for r in query_results if not r.get("meaningful_answer", False)]
        if query_issues:
            recommendations.append({
                "type": "query_handling",
                "issue": f"{len(query_issues)} query handling failures",
                "suggestion": "Check if comprehensive call documentation is properly ingested and accessible"
            })
        
        # Check for low confidence scores
        low_confidence = [r for r in query_results if r.get("confidence", 0) < 0.6 and r.get("meaningful_answer", False)]
        if low_confidence:
            recommendations.append({
                "type": "confidence",
                "issue": f"{len(low_confidence)} queries with low confidence but meaningful answers",
                "suggestion": "Review confidence calculation and consider adjusting thresholds"
            })
        
        # Check for specific call ID matching issues
        call_id_issues = [r for r in intent_results if "call_id_match" in r and not r["call_id_match"]]
        if call_id_issues:
            recommendations.append({
                "type": "call_id_extraction",
                "issue": f"{len(call_id_issues)} call ID extraction issues",
                "suggestion": "Improve call identifier pattern matching in intent detection"
            })
        
        if not recommendations:
            recommendations.append({
                "type": "general",
                "issue": "No major issues detected",
                "suggestion": "System is performing well. Consider adding more test cases for edge scenarios."
            })
        
        return recommendations
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of the Call-Specific RAG system."""
        logger.info("🚀 Starting Comprehensive Call-Specific RAG Test")
        logger.info("=" * 60)
        
        # Test intent detection
        intent_results, intent_success_rate = self.test_intent_detection()
        
        logger.info("")
        logger.info("=" * 60)
        
        # Test query handling
        query_results, query_success_rate = await self.test_call_specific_queries()
        
        logger.info("")
        logger.info("=" * 60)
        
        # Generate test report
        report = self.generate_test_report(
            intent_results, query_results, intent_success_rate, query_success_rate
        )
        
        # Print summary
        logger.info("📈 TEST SUMMARY:")
        logger.info(f"   Intent Detection Success: {intent_success_rate:.1%}")
        logger.info(f"   Query Handling Success: {query_success_rate:.1%}")
        logger.info(f"   Overall Success Rate: {report['summary']['overall_success_rate']:.1%}")
        logger.info(f"   Total Tests: {report['summary']['total_tests']}")
        
        # Print recommendations
        logger.info("")
        logger.info("💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            logger.info(f"   • {rec['issue']}: {rec['suggestion']}")
        
        logger.info("")
        logger.info("🎉 Comprehensive test completed!")
        
        return report

async def main():
    """Main function to run comprehensive testing."""
    tester = CallSpecificRAGTester()
    
    try:
        report = await tester.run_comprehensive_test()
        
        # Determine overall success
        overall_success = report['summary']['overall_success_rate'] > 0.7
        
        if overall_success:
            logger.info("✅ Call-Specific RAG system is working well!")
            return True
        else:
            logger.warning("⚠️  Call-Specific RAG system needs improvement")
            return False
            
    except Exception as e:
        logger.error(f"💥 Comprehensive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)