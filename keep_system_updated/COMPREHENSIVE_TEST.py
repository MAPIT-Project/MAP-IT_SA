#!/usr/bin/env python3
"""
Comprehensive Test Script for Horizon Europe Call Search System

This script tests the system's ability to answer all the target questions
and provides a detailed report on coverage and accuracy.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from services.enhanced_call_search import EnhancedCallSearchService
from services.intelligent_query_parser import IntelligentQueryParser

class ComprehensiveTester:
    """Comprehensive test class for the Horizon Europe call search system."""
    
    def __init__(self):
        self.service = EnhancedCallSearchService()
        self.parser = IntelligentQueryParser()
        self.results = {}
        
    def load_test_questions(self) -> List[Dict[str, Any]]:
        """Load the comprehensive test questions."""
        return [
            {
                "category": "Call discovery",
                "questions": [
                    "What are the currently open Horizon Europe calls in Cluster 4 (Digital, Industry and Space)?",
                    "Which topics under the latest work programme match advanced AI, cybersecurity, and edge computing?",
                    "What calls close in the next 60 days that target TRL 5–7 demonstrators?",
                    "Which topics support living labs for digital public services or GovTech?",
                    "Are there open topics that fund standardisation activities for data interoperability?",
                    "Which calls fund digital twins for manufacturing or energy?",
                    "What's the difference between 'calls' and 'topics' on the Funding & Tenders Portal?",
                    "How to filter calls by budget, type of action, and expected outcomes?",
                    "Which work programmes are relevant to digital transition and data spaces?",
                    "How to find co-funded European Partnerships that have open calls?",
                    "Where to find cascade funding (Financial Support to Third Parties) in ongoing projects?",
                    "Which EIC Accelerator cut-offs are upcoming for deep tech SMEs?",
                    "Are there mission calls relevant to climate-neutral and smart cities with digital solutions?",
                    "How to identify topics with lump-sum funding vs actual cost funding?",
                    "Which topics encourage social sciences and humanities (SSH) integration in digital projects?"
                ]
            }
        ]
    
    def test_question(self, question: str, category: str) -> Dict[str, Any]:
        """Test a single question and return detailed results."""
        print(f"🧪 Testing: {question}")
        
        start_time = time.time()
        
        try:
            # First parse the query to understand intent
            parsed_filters = self.parser.parse_query(question)
            
            # Execute the search
            result = self.service.search_calls_enhanced(
                query=question,
                max_results=5,
                enable_facet_analysis=True
            )
            
            elapsed = time.time() - start_time
            
            # Analyze the results
            analysis = self.analyze_results(result, parsed_filters, question)
            
            return {
                "question": question,
                "category": category,
                "result": result,
                "parsed_filters": parsed_filters.__dict__ if hasattr(parsed_filters, '__dict__') else str(parsed_filters),
                "processing_time": elapsed,
                "analysis": analysis,
                "success": result.get('status') == 'success',
                "error": result.get('search_metadata', {}).get('error') if result.get('status') == 'error' else None
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "question": question,
                "category": category,
                "result": None,
                "processing_time": elapsed,
                "analysis": {"error": str(e)},
                "success": False,
                "error": str(e)
            }
    
    def analyze_results(self, result: Dict[str, Any], parsed_filters: Any, question: str) -> Dict[str, Any]:
        """Analyze the search results for quality and relevance."""
        if result.get('status') != 'success':
            return {"error": "Search failed", "details": result}
        
        results = result.get('results', [])
        metadata = result.get('search_metadata', {})
        
        analysis = {
            "total_results": len(results),
            "filters_applied": metadata.get('filters_applied', []),
            "filter_intention": metadata.get('filter_intention', 'unknown'),
            "query_understood": self._assess_query_understanding(parsed_filters, question),
            "relevance_score": self._calculate_relevance_score(results, question),
            "result_quality": self._assess_result_quality(results),
            "coverage_analysis": self._analyze_coverage(parsed_filters, results)
        }
        
        return analysis
    
    def _assess_query_understanding(self, parsed_filters: Any, question: str) -> Dict[str, Any]:
        """Assess how well the query was understood."""
        if not hasattr(parsed_filters, 'user_intent_detected'):
            return {"score": 0, "details": "No intent detection available"}
        
        # Count detected intents
        detected_intents = len(parsed_filters.user_intent_detected)
        
        # Check if key elements were detected
        question_lower = question.lower()
        key_elements = {
            "cluster_4": "cluster 4" in question_lower,
            "ai": any(word in question_lower for word in ["ai", "artificial intelligence"]),
            "cybersecurity": "cybersecurity" in question_lower,
            "edge_computing": "edge computing" in question_lower,
            "trl": "trl" in question_lower,
            "living_labs": "living labs" in question_lower or "govtech" in question_lower,
            "standardization": any(word in question_lower for word in ["standardization", "standardisation"]),
            "digital_twins": "digital twins" in question_lower,
            "eic": "eic" in question_lower,
            "mission_calls": "mission calls" in question_lower,
            "lump_sum": "lump sum" in question_lower,
            "ssh": "ssh" in question_lower
        }
        
        # Calculate detection score
        detected_count = sum(1 for element, present in key_elements.items() 
                           if present and any(intent.endswith(element) for intent in parsed_filters.user_intent_detected))
        total_relevant = sum(1 for present in key_elements.values() if present)
        
        score = detected_count / total_relevant if total_relevant > 0 else 1.0
        
        return {
            "score": score,
            "detected_intents": parsed_filters.user_intent_detected,
            "key_elements_present": key_elements,
            "detected_count": detected_count,
            "total_relevant": total_relevant
        }
    
    def _calculate_relevance_score(self, results: List[Any], question: str) -> float:
        """Calculate overall relevance score for the results."""
        if not results:
            return 0.0
        
        question_lower = question.lower()
        total_score = 0.0
        
        for result in results:
            # Check title relevance
            title = getattr(result, 'title', '').lower()
            title_score = 1.0 if any(word in title for word in question_lower.split()) else 0.3
            
            # Check description relevance
            description = getattr(result, 'description', '').lower()
            desc_score = 0.5 if any(word in description for word in question_lower.split()) else 0.1
            
            # Check status relevance (prefer open calls)
            status = getattr(result, 'status', '').lower()
            status_score = 1.0 if status == 'open' else 0.7 if status == 'forthcoming' else 0.3
            
            total_score += (title_score * 0.4 + desc_score * 0.3 + status_score * 0.3)
        
        return total_score / len(results)
    
    def _assess_result_quality(self, results: List[Any]) -> Dict[str, Any]:
        """Assess the quality of the returned results."""
        if not results:
            return {"score": 0, "details": "No results"}
        
        quality_metrics = {
            "open_calls": sum(1 for r in results if getattr(r, 'status', '').lower() == 'open'),
            "forthcoming_calls": sum(1 for r in results if getattr(r, 'status', '').lower() == 'forthcoming'),
            "recent_calls": sum(1 for r in results if '2024' in getattr(r, 'deadline', '') or '2025' in getattr(r, 'deadline', '')),
            "avg_title_length": sum(len(getattr(r, 'title', '')) for r in results) / len(results),
            "avg_description_length": sum(len(getattr(r, 'description', '')) for r in results) / len(results)
        }
        
        # Calculate overall quality score
        quality_score = (
            (quality_metrics["open_calls"] / len(results) * 0.4) +
            (quality_metrics["recent_calls"] / len(results) * 0.3) +
            (min(quality_metrics["avg_description_length"] / 100, 1.0) * 0.3)
        )
        
        return {
            "score": quality_score,
            "metrics": quality_metrics
        }
    
    def _analyze_coverage(self, parsed_filters: Any, results: List[Any]) -> Dict[str, Any]:
        """Analyze how well the results cover the requested filters."""
        coverage = {
            "status_coverage": self._check_status_coverage(parsed_filters, results),
            "temporal_coverage": self._check_temporal_coverage(parsed_filters, results),
            "domain_coverage": self._check_domain_coverage(parsed_filters, results)
        }
        
        return coverage
    
    def _check_status_coverage(self, parsed_filters: Any, results: List[Any]) -> Dict[str, Any]:
        """Check if results match the requested status filter."""
        if not hasattr(parsed_filters, 'status_filter') or not parsed_filters.status_filter:
            return {"applied": False, "match_score": 1.0}
        
        expected_statuses = set(parsed_filters.status_filter)
        matched = sum(1 for r in results if getattr(r, 'status_code', '') in expected_statuses)
        
        return {
            "applied": True,
            "expected_statuses": list(expected_statuses),
            "matched_results": matched,
            "total_results": len(results),
            "match_score": matched / len(results) if results else 0.0
        }
    
    def _check_temporal_coverage(self, parsed_filters: Any, results: List[Any]) -> Dict[str, Any]:
        """Check if results match temporal filters (simplified check)."""
        # This is a simplified check - actual temporal filtering would require date parsing
        if not hasattr(parsed_filters, 'filter_intention'):
            return {"applied": False, "match_score": 1.0}
        
        intention = parsed_filters.filter_intention
        if '60' in intention or 'days' in intention:
            # Check if we have recent results (simplified)
            recent_count = sum(1 for r in results if '2024' in getattr(r, 'deadline', '') or '2025' in getattr(r, 'deadline', ''))
            return {
                "applied": True,
                "intention": intention,
                "recent_results": recent_count,
                "match_score": recent_count / len(results) if results else 0.0
            }
        
        return {"applied": False, "match_score": 1.0}
    
    def _check_domain_coverage(self, parsed_filters: Any, results: List[Any]) -> Dict[str, Any]:
        """Check domain-specific coverage."""
        if not hasattr(parsed_filters, 'specific_filters'):
            return {"applied": False, "match_score": 1.0}
        
        coverage = {}
        for domain, enabled in parsed_filters.specific_filters.items():
            if enabled:
                # Simplified domain matching
                domain_count = sum(1 for r in results if domain in str(r.__dict__).lower())
                coverage[domain] = {
                    "enabled": True,
                    "matched_results": domain_count,
                    "match_score": domain_count / len(results) if results else 0.0
                }
        
        return coverage if coverage else {"applied": False, "match_score": 1.0}
    
    def run_comprehensive_test(self):
        """Run the comprehensive test suite."""
        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 60)
        
        test_questions = self.load_test_questions()
        all_results = []
        
        for category_data in test_questions:
            category = category_data["category"]
            print(f"\n📋 Testing Category: {category}")
            print("-" * 40)
            
            for question in category_data["questions"]:
                result = self.test_question(question, category)
                all_results.append(result)
                
                # Print quick summary
                status = "✅" if result["success"] else "❌"
                results_count = len(result["result"]["results"]) if result["success"] and result["result"] else 0
                print(f"{status} {question[:50]}... -> {results_count} results")
        
        # Generate comprehensive report
        self.generate_report(all_results)
        
        return all_results
    
    def generate_report(self, results: List[Dict[str, Any]]):
        """Generate a comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        # Overall statistics
        total_questions = len(results)
        successful_questions = sum(1 for r in results if r["success"])
        success_rate = (successful_questions / total_questions) * 100
        
        print(f"\n📈 Overall Success Rate: {success_rate:.1f}% ({successful_questions}/{total_questions})")
        
        # Category breakdown
        categories = {}
        for result in results:
            category = result["category"]
            if category not in categories:
                categories[category] = {"total": 0, "successful": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["successful"] += 1
        
        print("\n📋 Category Breakdown:")
        for category, stats in categories.items():
            rate = (stats["successful"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"   {category}: {rate:.1f}% ({stats['successful']}/{stats['total']})")
        
        # Performance statistics
        avg_time = sum(r["processing_time"] for r in results) / total_questions
        max_time = max(r["processing_time"] for r in results)
        min_time = min(r["processing_time"] for r in results)
        
        print(f"\n⏱️ Performance:")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Maximum time: {max_time:.2f}s")
        print(f"   Minimum time: {min_time:.2f}s")
        
        # Query understanding analysis
        understanding_scores = []
        for result in results:
            if result["success"] and "analysis" in result and "query_understood" in result["analysis"]:
                understanding_scores.append(result["analysis"]["query_understood"]["score"])
        
        avg_understanding = sum(understanding_scores) / len(understanding_scores) if understanding_scores else 0
        print(f"\n🧠 Query Understanding: {avg_understanding:.1%}")
        
        # Result quality analysis
        quality_scores = []
        for result in results:
            if result["success"] and "analysis" in result and "result_quality" in result["analysis"]:
                quality_scores.append(result["analysis"]["result_quality"]["score"])
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        print(f"⭐ Result Quality: {avg_quality:.1%}")
        
        # Detailed results for failed queries
        failed_queries = [r for r in results if not r["success"]]
        if failed_queries:
            print(f"\n❌ Failed Queries ({len(failed_queries)}):")
            for query in failed_queries:
                print(f"   - {query['question'][:60]}...")
                if query['error']:
                    print(f"     Error: {query['error'][:100]}...")
        
        # Save detailed results to file
        self.save_detailed_results(results)
        
        print(f"\n📝 Detailed results saved to: comprehensive_test_results.json")
        print("🎉 Test completed!")
    
    def save_detailed_results(self, results: List[Dict[str, Any]]):
        """Save detailed results to a JSON file."""
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            serializable = result.copy()
            # Remove non-serializable objects
            if 'result' in serializable and serializable['result']:
                serializable['result'] = {
                    'status': serializable['result'].get('status'),
                    'results_count': len(serializable['result'].get('results', [])),
                    'search_metadata': serializable['result'].get('search_metadata', {})
                }
            serializable_results.append(serializable)
        
        with open('comprehensive_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

def main():
    """Main function to run the comprehensive test."""
    tester = ComprehensiveTester()
    results = tester.run_comprehensive_test()
    
    # Return exit code based on success rate
    success_rate = sum(1 for r in results if r["success"]) / len(results) if results else 0
    return 0 if success_rate >= 0.7 else 1

if __name__ == "__main__":
    sys.exit(main())