#!/usr/bin/env python3
"""
Final comprehensive test of the improved conversation AI system.
Tests research manager queries and validates system performance.
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Comprehensive test scenarios for research managers
RESEARCH_MANAGER_TEST_CASES = [
    {
        "id": "basic_horizon_info",
        "query": "What is Horizon Europe and how much funding is available?",
        "category": "program_overview",
        "expected_keywords": ["horizon europe", "budget", "95.5 billion", "2021-2027", "pillars"],
        "success_criteria": ["mentions_budget", "mentions_timeline", "explains_structure"]
    },
    {
        "id": "ai_healthcare_projects", 
        "query": "Find AI projects in healthcare that I can learn from or collaborate with",
        "category": "project_search",
        "expected_keywords": ["artificial intelligence", "healthcare", "projects", "collaboration"],
        "success_criteria": ["actionable_advice", "partnership_guidance", "specific_suggestions"]
    },
    {
        "id": "climate_funding_budget",
        "query": "What's the total budget allocation for climate change research?",
        "category": "funding_analysis", 
        "expected_keywords": ["climate", "budget", "funding", "green deal"],
        "success_criteria": ["specific_numbers", "comprehensive_coverage", "program_breakdown"]
    },
    {
        "id": "quantum_computing_trends",
        "query": "What are the latest trends in quantum computing research funding?",
        "category": "trend_analysis",
        "expected_keywords": ["quantum", "trends", "funding", "research"],
        "success_criteria": ["forward_looking", "technology_focus", "funding_context"]
    },
    {
        "id": "application_process",
        "query": "How do I apply for Horizon Europe funding and what are the success rates?",
        "category": "application_guidance",
        "expected_keywords": ["apply", "process", "success rates", "proposal"],
        "success_criteria": ["step_by_step", "practical_tips", "realistic_expectations"]
    },
    {
        "id": "partnership_building",
        "query": "How can I find European partners for a digital health project?",
        "category": "collaboration",
        "expected_keywords": ["partners", "digital health", "collaboration", "consortium"],
        "success_criteria": ["concrete_resources", "networking_advice", "partnership_strategy"]
    },
    {
        "id": "country_comparison",
        "query": "Which European countries are strongest in renewable energy research?",
        "category": "comparative_analysis", 
        "expected_keywords": ["countries", "renewable energy", "research", "leading"],
        "success_criteria": ["country_ranking", "specific_examples", "data_driven"]
    },
    {
        "id": "innovation_ecosystem",
        "query": "Tell me about the European Innovation Council and how it differs from regular Horizon Europe",
        "category": "program_details",
        "expected_keywords": ["eic", "innovation", "difference", "horizon europe"],
        "success_criteria": ["clear_comparison", "specific_features", "strategic_guidance"]
    },
    {
        "id": "success_metrics",
        "query": "How do I measure and report the impact of my research project?",
        "category": "impact_assessment",
        "expected_keywords": ["impact", "measure", "report", "metrics"],
        "success_criteria": ["practical_framework", "kpi_guidance", "reporting_structure"]
    },
    {
        "id": "memory_follow_up",
        "query": "Based on what we discussed about quantum computing, what specific calls should I target?",
        "category": "memory_integration",
        "expected_keywords": ["quantum", "calls", "specific", "target"],
        "success_criteria": ["memory_reference", "specific_recommendations", "actionable_next_steps"]
    }
]

class ImprovedSystemTester:
    """Comprehensive tester for the improved conversation AI system."""
    
    def __init__(self):
        self.conversation_manager = None
        self.test_results = []
        self.performance_metrics = {}
        
    async def initialize_system(self) -> bool:
        """Initialize and validate the conversation system."""
        try:
            print("🔧 Initializing improved conversation system...")
            
            # Import and initialize
            from app.services.conversation.conversation_manager import ConversationManager
            self.conversation_manager = ConversationManager()
            
            print("✅ ConversationManager initialized successfully")
            
            # Validate key components
            validation_checks = [
                ("Memory Service", hasattr(self.conversation_manager, 'memory_service')),
                ("Response Generator", hasattr(self.conversation_manager, 'response_generator')),
                ("AI Intent Service", hasattr(self.conversation_manager, 'ai_intent_service')),
                ("Tool Orchestrator", hasattr(self.conversation_manager, 'tool_orchestrator')),
                ("Enhanced Fallback", hasattr(self.conversation_manager, '_get_enhanced_fallback_response'))
            ]
            
            all_valid = True
            for check_name, check_result in validation_checks:
                status = "✅" if check_result else "❌"
                print(f"  {status} {check_name}: {'Available' if check_result else 'Missing'}")
                if not check_result:
                    all_valid = False
            
            return all_valid
            
        except Exception as e:
            print(f"❌ Failed to initialize system: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_single_case(self, test_case: dict, conversation_id: int = 1) -> dict:
        """Test a single research manager use case."""
        
        case_id = test_case["id"]
        query = test_case["query"]
        category = test_case["category"]
        
        print(f"\n📋 Testing Case: {case_id}")
        print(f"Category: {category}")
        print(f"Query: '{query}'")
        
        start_time = time.time()
        
        try:
            # Process the query
            result = await self.conversation_manager.process_message(
                conversation_id=conversation_id,
                user_message=query,
                user_id=1,
                streaming=False
            )
            
            processing_time = time.time() - start_time
            
            if isinstance(result, dict) and 'response' in result:
                response = result['response']
                
                # Analyze response quality
                quality_analysis = self._analyze_response_quality(response, test_case)
                
                test_result = {
                    "case_id": case_id,
                    "category": category,
                    "query": query,
                    "response": response,
                    "response_length": len(response),
                    "processing_time": processing_time,
                    "quality_score": quality_analysis["overall_score"],
                    "quality_details": quality_analysis,
                    "metadata": {
                        "confidence": result.get('confidence', 0.0),
                        "grounded": result.get('grounded', False),
                        "tools_executed": result.get('tools_executed', False),
                        "memory_stats": result.get('memory_stats', {}),
                        "chunks_retrieved": result.get('chunks_retrieved', 0)
                    },
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Print results
                score = quality_analysis["overall_score"]
                print(f"✅ Success! Quality: {score:.2f}/1.0 ({processing_time:.2f}s)")
                print(f"Response length: {len(response)} chars")
                print(f"Keywords found: {quality_analysis['keywords_found']}/{quality_analysis['total_keywords']}")
                print(f"Criteria met: {quality_analysis['criteria_met']}/{quality_analysis['total_criteria']}")
                print(f"Response preview: {response[:300]}...")
                
                if score < 0.6:
                    print(f"⚠️ Quality below expected threshold")
                    
            else:
                print(f"❌ Invalid response format")
                test_result = {
                    "case_id": case_id,
                    "category": category, 
                    "query": query,
                    "error": "Invalid response format",
                    "processing_time": processing_time,
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }
            
            self.test_results.append(test_result)
            return test_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ Error: {e}")
            
            error_result = {
                "case_id": case_id,
                "category": category,
                "query": query,
                "error": str(e),
                "processing_time": processing_time,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results.append(error_result)
            return error_result
    
    def _analyze_response_quality(self, response: str, test_case: dict) -> dict:
        """Analyze response quality against expected criteria."""
        
        if not response:
            return {
                "overall_score": 0.0,
                "keywords_found": 0,
                "total_keywords": len(test_case.get("expected_keywords", [])),
                "criteria_met": 0,
                "total_criteria": len(test_case.get("success_criteria", [])),
                "details": "Empty response"
            }
        
        response_lower = response.lower()
        
        # Check expected keywords (40% of score)
        expected_keywords = test_case.get("expected_keywords", [])
        keywords_found = sum(1 for keyword in expected_keywords if keyword.lower() in response_lower)
        keyword_score = (keywords_found / len(expected_keywords)) * 0.4 if expected_keywords else 0
        
        # Check success criteria (40% of score) 
        success_criteria = test_case.get("success_criteria", [])
        criteria_met = sum(1 for criterion in success_criteria if self._check_success_criterion(response, criterion))
        criteria_score = (criteria_met / len(success_criteria)) * 0.4 if success_criteria else 0
        
        # Response quality indicators (20% of score)
        quality_indicators = 0
        
        # Length and structure
        if len(response) > 200:
            quality_indicators += 0.05
        if len(response) > 500:
            quality_indicators += 0.05
            
        # Professional terminology
        professional_terms = ["research", "funding", "programme", "european", "innovation", "project"]
        if sum(1 for term in professional_terms if term in response_lower) >= 3:
            quality_indicators += 0.05
            
        # Actionable content
        actionable_terms = ["recommend", "suggest", "should", "can", "contact", "apply", "consider"]
        if any(term in response_lower for term in actionable_terms):
            quality_indicators += 0.05
            
        overall_score = keyword_score + criteria_score + quality_indicators
        
        return {
            "overall_score": min(overall_score, 1.0),
            "keyword_score": keyword_score,
            "criteria_score": criteria_score,
            "quality_indicators": quality_indicators,
            "keywords_found": keywords_found,
            "total_keywords": len(expected_keywords),
            "criteria_met": criteria_met,
            "total_criteria": len(success_criteria),
            "response_length": len(response)
        }
    
    def _check_success_criterion(self, response: str, criterion: str) -> bool:
        """Check if a specific success criterion is met."""
        
        response_lower = response.lower()
        
        criterion_checks = {
            "mentions_budget": lambda: any(term in response_lower for term in 
                ["budget", "billion", "million", "€", "eur", "funding", "95.5"]),
            "mentions_timeline": lambda: any(term in response_lower for term in 
                ["2021", "2027", "2021-2027", "seven year", "period"]),
            "explains_structure": lambda: any(term in response_lower for term in 
                ["pillar", "cluster", "programme", "structure", "organized"]),
            "actionable_advice": lambda: any(term in response_lower for term in 
                ["recommend", "suggest", "should", "can", "steps", "process"]),
            "partnership_guidance": lambda: any(term in response_lower for term in 
                ["partner", "collaboration", "consortium", "network", "connect"]),
            "specific_suggestions": lambda: any(term in response_lower for term in 
                ["specific", "example", "such as", "including", "particular"]),
            "specific_numbers": lambda: any(char.isdigit() for char in response),
            "comprehensive_coverage": lambda: len(response) > 400,
            "program_breakdown": lambda: any(term in response_lower for term in 
                ["programme", "call", "instrument", "action", "scheme"]),
            "forward_looking": lambda: any(term in response_lower for term in 
                ["future", "emerging", "upcoming", "trends", "next"]),
            "technology_focus": lambda: any(term in response_lower for term in 
                ["technology", "technical", "innovation", "breakthrough"]),
            "funding_context": lambda: any(term in response_lower for term in 
                ["funding", "investment", "budget", "support", "finance"]),
            "step_by_step": lambda: any(term in response_lower for term in 
                ["step", "process", "stage", "phase", "first", "second"]),
            "practical_tips": lambda: any(term in response_lower for term in 
                ["tip", "advice", "recommendation", "best practice", "success"]),
            "realistic_expectations": lambda: any(term in response_lower for term in 
                ["rate", "success", "competitive", "challenging", "typical"]),
            "concrete_resources": lambda: any(term in response_lower for term in 
                ["portal", "website", "database", "contact", "office"]),
            "networking_advice": lambda: any(term in response_lower for term in 
                ["network", "event", "conference", "meeting", "brokerage"]),
            "partnership_strategy": lambda: any(term in response_lower for term in 
                ["strategy", "approach", "plan", "build", "develop"]),
            "country_ranking": lambda: any(term in response_lower for term in 
                ["germany", "france", "italy", "spain", "netherlands", "leading"]),
            "specific_examples": lambda: any(term in response_lower for term in 
                ["example", "such as", "including", "like", "instance"]),
            "data_driven": lambda: any(char.isdigit() for char in response) and len(response) > 300,
            "clear_comparison": lambda: any(term in response_lower for term in 
                ["differ", "compared", "versus", "unlike", "while", "whereas"]),
            "specific_features": lambda: any(term in response_lower for term in 
                ["feature", "characteristic", "aspect", "element", "component"]),
            "strategic_guidance": lambda: any(term in response_lower for term in 
                ["strategic", "strategy", "plan", "approach", "consider"]),
            "practical_framework": lambda: any(term in response_lower for term in 
                ["framework", "approach", "method", "way", "how to"]),
            "kpi_guidance": lambda: any(term in response_lower for term in 
                ["kpi", "metric", "indicator", "measure", "assessment"]),
            "reporting_structure": lambda: any(term in response_lower for term in 
                ["report", "document", "deliverable", "output", "result"]),
            "memory_reference": lambda: any(term in response_lower for term in 
                ["previous", "earlier", "discussed", "mentioned", "quantum"]),
            "specific_recommendations": lambda: any(term in response_lower for term in 
                ["recommend", "suggest", "should apply", "target", "focus"]),
            "actionable_next_steps": lambda: any(term in response_lower for term in 
                ["next", "step", "action", "do", "start", "begin"])
        }
        
        check_function = criterion_checks.get(criterion)
        return check_function() if check_function else False
    
    async def test_memory_functionality(self):
        """Test conversational memory with follow-up questions."""
        
        print(f"\n🧠 Testing Memory & Context Functionality")
        
        # First establish context about quantum computing
        context_case = {
            "id": "memory_context_setup",
            "query": "Tell me about quantum computing research in Horizon Europe",
            "category": "memory_setup",
            "expected_keywords": ["quantum", "research", "horizon europe"],
            "success_criteria": ["technology_focus", "funding_context"]
        }
        
        await self.test_single_case(context_case, conversation_id=99)  # Special conversation ID
        
        # Small delay to ensure memory is stored
        await asyncio.sleep(1)
        
        # Now test the follow-up that requires memory
        memory_case = next(case for case in RESEARCH_MANAGER_TEST_CASES if case["id"] == "memory_follow_up")
        await self.test_single_case(memory_case, conversation_id=99)
    
    def calculate_performance_metrics(self):
        """Calculate overall system performance metrics."""
        
        successful_tests = [r for r in self.test_results if r.get("success", False)]
        total_tests = len(self.test_results)
        
        if not successful_tests:
            return {
                "success_rate": 0.0,
                "avg_quality": 0.0,
                "avg_processing_time": 0.0,
                "total_tests": total_tests,
                "failed_tests": total_tests
            }
        
        # Calculate metrics
        success_rate = len(successful_tests) / total_tests * 100
        avg_quality = sum(r.get("quality_score", 0) for r in successful_tests) / len(successful_tests)
        avg_processing_time = sum(r.get("processing_time", 0) for r in successful_tests) / len(successful_tests)
        avg_response_length = sum(r.get("response_length", 0) for r in successful_tests) / len(successful_tests)
        
        # Category performance
        category_performance = {}
        for result in successful_tests:
            category = result.get("category", "unknown")
            if category not in category_performance:
                category_performance[category] = {"scores": [], "times": []}
            
            category_performance[category]["scores"].append(result.get("quality_score", 0))
            category_performance[category]["times"].append(result.get("processing_time", 0))
        
        # Calculate category averages
        for category, data in category_performance.items():
            data["avg_quality"] = sum(data["scores"]) / len(data["scores"])
            data["avg_time"] = sum(data["times"]) / len(data["times"])
            data["test_count"] = len(data["scores"])
        
        return {
            "success_rate": success_rate,
            "avg_quality": avg_quality,
            "avg_processing_time": avg_processing_time,
            "avg_response_length": avg_response_length,
            "total_tests": total_tests,
            "successful_tests": len(successful_tests),
            "failed_tests": total_tests - len(successful_tests),
            "category_performance": category_performance
        }
    
    def generate_comprehensive_report(self) -> dict:
        """Generate a comprehensive test report."""
        
        metrics = self.calculate_performance_metrics()
        
        # Performance assessment
        quality_grade = "A" if metrics["avg_quality"] >= 0.8 else "B" if metrics["avg_quality"] >= 0.6 else "C" if metrics["avg_quality"] >= 0.4 else "D"
        speed_grade = "A" if metrics["avg_processing_time"] <= 5 else "B" if metrics["avg_processing_time"] <= 10 else "C" if metrics["avg_processing_time"] <= 20 else "D"
        reliability_grade = "A" if metrics["success_rate"] >= 90 else "B" if metrics["success_rate"] >= 80 else "C" if metrics["success_rate"] >= 70 else "D"
        
        # System readiness assessment
        overall_grade = min(quality_grade, speed_grade, reliability_grade)
        
        readiness_status = {
            "A": "PRODUCTION READY",
            "B": "READY WITH MINOR IMPROVEMENTS", 
            "C": "NEEDS IMPROVEMENT",
            "D": "NOT READY"
        }.get(overall_grade, "UNKNOWN")
        
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_test_cases": len(RESEARCH_MANAGER_TEST_CASES),
                "tests_executed": metrics["total_tests"],
                "success_rate": metrics["success_rate"],
                "overall_grade": overall_grade,
                "readiness_status": readiness_status
            },
            "performance_metrics": metrics,
            "quality_assessment": {
                "grade": quality_grade,
                "score": metrics["avg_quality"],
                "threshold_met": metrics["avg_quality"] >= 0.6,
                "excellent_responses": sum(1 for r in self.test_results 
                                         if r.get("success") and r.get("quality_score", 0) >= 0.8)
            },
            "speed_assessment": {
                "grade": speed_grade,
                "avg_time": metrics["avg_processing_time"],
                "threshold_met": metrics["avg_processing_time"] <= 15,
                "fast_responses": sum(1 for r in self.test_results 
                                    if r.get("success") and r.get("processing_time", 0) <= 5)
            },
            "reliability_assessment": {
                "grade": reliability_grade,
                "success_rate": metrics["success_rate"],
                "threshold_met": metrics["success_rate"] >= 80,
                "failed_cases": [r["case_id"] for r in self.test_results if not r.get("success")]
            },
            "category_performance": metrics.get("category_performance", {}),
            "detailed_results": self.test_results,
            "recommendations": []
        }
        
        # Generate recommendations
        if metrics["avg_quality"] < 0.6:
            report["recommendations"].append("Improve response quality - enhance AI prompts and knowledge base")
        if metrics["avg_processing_time"] > 15:
            report["recommendations"].append("Optimize response time - consider caching and performance tuning")
        if metrics["success_rate"] < 80:
            report["recommendations"].append("Improve system reliability - debug failed cases and add error handling")
        if overall_grade in ["A", "B"]:
            report["recommendations"].append("System ready for research manager use - consider pilot deployment")
        
        return report

async def main():
    """Run the comprehensive test suite."""
    
    print("🎯 Final Test: Improved Research Manager AI System")
    print("=" * 60)
    
    tester = ImprovedSystemTester()
    
    # Initialize system
    print("🚀 Initializing system...")
    if not await tester.initialize_system():
        print("❌ System initialization failed. Cannot proceed.")
        return
    
    print(f"\n📋 Running {len(RESEARCH_MANAGER_TEST_CASES)} comprehensive test cases...")
    
    # Run all test cases (except memory follow-up which is handled separately)
    regular_cases = [case for case in RESEARCH_MANAGER_TEST_CASES if case["category"] != "memory_integration"]
    
    for i, test_case in enumerate(regular_cases, 1):
        print(f"\n--- Test {i}/{len(regular_cases)} ---")
        await tester.test_single_case(test_case)
        
        # Brief delay between tests
        await asyncio.sleep(0.5)
    
    # Test memory functionality separately
    await tester.test_memory_functionality()
    
    # Generate comprehensive report
    print(f"\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 60)
    
    report = tester.generate_comprehensive_report()
    
    # Display key metrics
    summary = report["test_summary"]
    metrics = report["performance_metrics"]
    
    print(f"🎯 Overall System Grade: {summary['overall_grade']} - {summary['readiness_status']}")
    print(f"✅ Success Rate: {metrics['success_rate']:.1f}% ({metrics['successful_tests']}/{metrics['total_tests']})")
    print(f"⭐ Quality Score: {metrics['avg_quality']:.2f}/1.0 (Grade: {report['quality_assessment']['grade']})")
    print(f"⏱️  Processing Time: {metrics['avg_processing_time']:.2f}s (Grade: {report['speed_assessment']['grade']})")
    print(f"📏 Avg Response Length: {metrics['avg_response_length']:.0f} characters")
    
    # Category performance
    print(f"\n📋 Performance by Category:")
    for category, performance in report["category_performance"].items():
        print(f"  📁 {category}: {performance['avg_quality']:.2f} quality, {performance['avg_time']:.2f}s ({performance['test_count']} tests)")
    
    # Failed tests
    failed_cases = report["reliability_assessment"]["failed_cases"]
    if failed_cases:
        print(f"\n❌ Failed Test Cases ({len(failed_cases)}):")
        for case_id in failed_cases:
            failed_result = next(r for r in tester.test_results if r.get("case_id") == case_id)
            print(f"  - {case_id}: {failed_result.get('error', 'Unknown error')}")
    
    # Recommendations
    if report["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")
    
    # System readiness conclusion
    print(f"\n🏁 CONCLUSION:")
    if summary["overall_grade"] in ["A", "B"]:
        print(f"✅ System is {summary['readiness_status']} for research manager use!")
        print("   The AI demonstrates strong capability across research funding scenarios.")
    else:
        print(f"⚠️ System {summary['readiness_status']} - needs further development.")
        print("   Focus on the recommendations above before deployment.")
    
    # Save detailed report
    report_filename = f"final_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Detailed report saved to: {report_filename}")
    
    return report

if __name__ == "__main__":
    asyncio.run(main())