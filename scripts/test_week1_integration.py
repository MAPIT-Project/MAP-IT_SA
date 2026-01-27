#!/usr/bin/env python3
"""
Week 1 Integration Test Script

Tests all components of the Data Intelligence upgrade:
1. Neo4j connection and data
2. Graph Search Service
3. Query Planner
4. Data Intelligence Service
5. Tool Orchestrator integration

Run with: python scripts/test_week1_integration.py
"""

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Configure logging - suppress verbose output
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for noisy in ['neo4j', 'urllib3', 'httpx', 'google', 'absl']:
    logging.getLogger(noisy).setLevel(logging.ERROR)


@dataclass
class TestResult:
    """Container for test results."""
    name: str
    passed: bool
    duration_ms: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class IntegrationTester:
    """Runs integration tests for Week 1 components."""
    
    def __init__(self):
        self.results: list[TestResult] = []
        self.start_time = None
    
    def add_result(self, name: str, passed: bool, duration_ms: float, 
                   message: str, details: dict = None):
        """Add a test result."""
        self.results.append(TestResult(
            name=name,
            passed=passed,
            duration_ms=duration_ms,
            message=message,
            details=details or {}
        ))
        # Print immediately
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}")
        print(f"       {message}")
        print(f"       Duration: {duration_ms:.0f}ms")
        if details and not passed:
            print(f"       Details: {details}")
        print()
    
    async def run_all_tests(self) -> bool:
        """Run all integration tests."""
        self.start_time = datetime.now()
        
        print("\n" + "=" * 70)
        print("🧪 WEEK 1 INTEGRATION TESTS")
        print("=" * 70 + "\n")
        
        # Test 1: Neo4j Connection
        await self.test_neo4j_connection()
        
        # Test 2: Neo4j Data
        await self.test_neo4j_data()
        
        # Test 3: Graph Search Service
        await self.test_graph_search_service()
        
        # Test 4: Query Planner
        await self.test_query_planner()
        
        # Test 5: Data Intelligence Service
        await self.test_data_intelligence_service()
        
        # Test 6: Tool Orchestrator
        await self.test_tool_orchestrator()
        
        # Test 7: Query Type A - Call Lookup
        await self.test_query_type_a_call_lookup()
        
        # Test 8: Query Type B - Eligibility
        await self.test_query_type_b_eligibility()
        
        # Test 9: Query Type C - Budget
        await self.test_query_type_c_budget()
        
        # Test 10: Query Type D - Consortium
        await self.test_query_type_d_consortium()
        
        # Test 11: Query Type E - Similar Topics
        await self.test_query_type_e_similar_topics()
        
        # Print summary
        self.print_summary()
        
        # Return overall success
        return all(r.passed for r in self.results)
    
    async def test_neo4j_connection(self):
        """Test Neo4j database connection."""
        start = datetime.now()
        name = "Neo4j Connection"
        
        try:
            from app.core.neo4j_config import neo4j_db
            
            if neo4j_db.test_connection():
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration, "Connected successfully")
            else:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, False, duration, "Connection test failed")
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_neo4j_data(self):
        """Test Neo4j has data loaded."""
        start = datetime.now()
        name = "Neo4j Data"
        
        try:
            from app.core.neo4j_config import neo4j_db
            
            stats = neo4j_db.get_database_stats()
            
            if "error" not in stats:
                total = stats.get('total_nodes', 0)
                nodes = stats.get('nodes', {})
                
                if total > 0:
                    duration = (datetime.now() - start).total_seconds() * 1000
                    self.add_result(name, True, duration, 
                                  f"Found {total:,} nodes across {len(nodes)} types",
                                  {"node_counts": nodes})
                else:
                    duration = (datetime.now() - start).total_seconds() * 1000
                    self.add_result(name, False, duration, 
                                  "No data found - run TASK_03 ingestion")
            else:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, False, duration, 
                              f"Stats error: {stats.get('error')}")
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_graph_search_service(self):
        """Test Graph Search Service initialization."""
        start = datetime.now()
        name = "Graph Search Service"
        
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            
            service = GraphSearchService()
            
            # Test cluster overview
            clusters = service.get_cluster_overview()
            
            if clusters:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration, 
                              f"Initialized, found {len(clusters)} clusters",
                              {"clusters": [c.get('cluster_code') for c in clusters[:3]]})
            else:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration, 
                              "Initialized (no cluster data yet)")
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_query_planner(self):
        """Test Query Planner initialization and basic planning."""
        start = datetime.now()
        name = "Query Planner"
        
        try:
            from app.services.data_intelligence.query_planner import QueryPlanner
            
            planner = QueryPlanner()
            
            # Test with a simple query (async method)
            plan = await planner.generate_plan("What is the average budget in Cluster 4?")
            
            if plan and plan.intent_type:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration, 
                              f"Generated plan: {plan.intent_type}",
                              {
                                  "confidence": plan.confidence,
                                  "steps": len(plan.steps)
                              })
            else:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, False, duration, "Failed to generate plan")
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_data_intelligence_service(self):
        """Test Data Intelligence Service initialization."""
        start = datetime.now()
        name = "Data Intelligence Service"
        
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            status = service.get_service_status()
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if status.get("fully_operational"):
                self.add_result(name, True, duration, 
                              "All services operational", status)
            else:
                # Partial success is okay (vector might be unavailable)
                self.add_result(name, True, duration, 
                              "Initialized with partial services", status)
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_tool_orchestrator(self):
        """Test Tool Orchestrator has intelligent_search registered."""
        start = datetime.now()
        name = "Tool Orchestrator"
        
        try:
            from app.services.tools.tool_orchestrator import ToolOrchestrator
            
            orchestrator = ToolOrchestrator()
            tools = orchestrator.get_available_tools()
            
            intelligent = [t for t in tools if t['name'] == 'intelligent_search']
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if intelligent:
                self.add_result(name, True, duration, 
                              "intelligent_search tool registered",
                              {"total_tools": len(tools)})
            else:
                self.add_result(name, False, duration, 
                              "intelligent_search tool NOT found",
                              {"available_tools": [t['name'] for t in tools]})
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_query_type_a_call_lookup(self):
        """Test Query Type A: Call/Topic Lookup."""
        start = datetime.now()
        name = "Query Type A: Call Lookup"
        
        # Use an actual topic from the database
        query = "Tell me about topic HORIZON-CL4-2022-DATA-01-02"
        
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            result = await service.search(query)
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if result.success:
                self.add_result(name, True, duration,
                              f"Intent: {result.intent_type}, Confidence: {result.confidence:.2f}",
                              {
                                  "graph_results": len(result.graph_results),
                                  "vector_results": len(result.vector_results)
                              })
            else:
                self.add_result(name, False, duration, 
                              result.error or 'Search failed')
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_query_type_b_eligibility(self):
        """Test Query Type B: Eligibility Check."""
        start = datetime.now()
        name = "Query Type B: Eligibility"
        
        query = "Can an SME from Switzerland participate in Cluster 4 calls?"
        
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            result = await service.search(query)
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if result.success:
                self.add_result(name, True, duration,
                              f"Intent: {result.intent_type}",
                              {
                                  "graph_results": len(result.graph_results),
                                  "vector_results": len(result.vector_results)
                              })
            else:
                self.add_result(name, False, duration, 
                              result.error or 'Search failed')
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_query_type_c_budget(self):
        """Test Query Type C: Budget Questions."""
        start = datetime.now()
        name = "Query Type C: Budget"
        
        query = "What is the average budget in Cluster 5?"
        
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            result = await service.search(query)
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if result.success:
                self.add_result(name, True, duration,
                              f"Intent: {result.intent_type}",
                              {
                                  "graph_results": len(result.graph_results),
                                  "vector_results": len(result.vector_results)
                              })
            else:
                self.add_result(name, False, duration, 
                              result.error or 'Search failed')
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_query_type_d_consortium(self):
        """Test Query Type D: Consortium Patterns."""
        start = datetime.now()
        name = "Query Type D: Consortium"
        
        query = "What is the typical consortium size for Cluster 4 projects?"
        
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            result = await service.search(query)
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if result.success:
                self.add_result(name, True, duration,
                              f"Intent: {result.intent_type}",
                              {
                                  "graph_results": len(result.graph_results),
                                  "vector_results": len(result.vector_results)
                              })
            else:
                self.add_result(name, False, duration, 
                              result.error or 'Search failed')
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    async def test_query_type_e_similar_topics(self):
        """Test Query Type E: Similar Topics."""
        start = datetime.now()
        name = "Query Type E: Similar Topics"
        
        query = "Find topics similar to artificial intelligence in healthcare"
        
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            result = await service.search(query)
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if result.success:
                self.add_result(name, True, duration,
                              f"Intent: {result.intent_type}",
                              {
                                  "graph_results": len(result.graph_results),
                                  "vector_results": len(result.vector_results)
                              })
            else:
                self.add_result(name, False, duration, 
                              result.error or 'Search failed')
                
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")
    
    def print_summary(self):
        """Print test summary."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        print(f"\n   Total Tests: {len(self.results)}")
        print(f"   ✅ Passed:    {passed}")
        print(f"   ❌ Failed:    {failed}")
        print(f"   ⏱️  Duration:  {total_time:.1f}s")
        
        if failed > 0:
            print("\n" + "-" * 70)
            print("⚠️  FAILED TESTS:")
            for r in self.results:
                if not r.passed:
                    print(f"   • {r.name}: {r.message}")
            
            print("\n💡 Troubleshooting:")
            print("   - Neo4j not running: docker-compose up neo4j -d")
            print("   - No data: python scripts/ingest_cordis_to_neo4j.py")
            print("   - Missing API key: Check GEMINI_API_KEY in .env")
        else:
            print("\n" + "=" * 70)
            print("🎉 ALL TESTS PASSED! Week 1 implementation is complete.")
            print("=" * 70)
            print("\n   Ready for Week 2:")
            print("   - TASK_10: Cross-Encoder Reranking")
            print("   - TASK_11: Result Fusion")
            print("   - TASK_12: Advanced Queries")
            print("   - TASK_13: Consortium Builder")
            print("   - TASK_14: Compliance Checker")
            print("   - TASK_15: Final Testing")


async def main():
    """Run integration tests."""
    tester = IntegrationTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

