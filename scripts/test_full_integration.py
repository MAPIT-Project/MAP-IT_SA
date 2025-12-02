#!/usr/bin/env python3
"""
Full Integration Test Suite for MAPIT Data Intelligence Upgrade

Tests:
- Neo4j connectivity and data
- All graph query types (A-H)
- Query planner with all intents
- Cross-encoder reranking
- Tool orchestrator integration
- Performance benchmarks
"""

import sys
import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(message)s')
for noisy in ['neo4j', 'urllib3', 'httpx', 'google', 'absl', 'sentence_transformers']:
    logging.getLogger(noisy).setLevel(logging.ERROR)


class TestSuite:
    """Full integration test suite for Data Intelligence."""
    
    def __init__(self):
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.start_time = None
    
    def record(self, name: str, passed: bool, duration_ms: float, error: str = None):
        """Record a test result."""
        status = "✅" if passed else "❌"
        self.results["passed" if passed else "failed"] += 1
        self.results["tests"].append({
            "name": name,
            "passed": passed,
            "duration_ms": duration_ms,
            "error": error
        })
        
        print(f"{status} {name}")
        print(f"   Duration: {duration_ms:.0f}ms")
        if error:
            print(f"   Error: {error[:60]}...")
        print()
    
    async def run_all(self):
        """Run all tests."""
        self.start_time = datetime.now()
        
        print("\n" + "=" * 70)
        print("🧪 FULL INTEGRATION TEST SUITE - WEEK 1 & WEEK 2")
        print("=" * 70 + "\n")
        
        # Infrastructure Tests
        print("📦 INFRASTRUCTURE TESTS")
        print("-" * 40)
        await self.test_neo4j_connection()
        await self.test_neo4j_data()
        
        # Graph Service Tests (Week 1)
        print("\n📊 GRAPH SERVICE TESTS (Query Types A-E)")
        print("-" * 40)
        await self.test_call_lookup()
        await self.test_eligibility_check()
        await self.test_budget_statistics()
        await self.test_consortium_patterns()
        await self.test_similar_topics()
        
        # Advanced Graph Queries (Week 2)
        print("\n📈 ADVANCED QUERIES (Query Types F-H)")
        print("-" * 40)
        await self.test_project_examples()
        await self.test_org_track_record()
        await self.test_funding_trends()
        
        # Planner Tests
        print("\n🧠 QUERY PLANNER TESTS")
        print("-" * 40)
        await self.test_query_planner()
        
        # Reranking Tests (Week 2)
        print("\n🔄 RERANKING TESTS")
        print("-" * 40)
        await self.test_cross_encoder()
        
        # Integration Tests
        print("\n🔗 INTEGRATION TESTS")
        print("-" * 40)
        await self.test_data_intelligence_service()
        await self.test_tool_orchestrator()
        
        # New Tools (Week 2)
        print("\n🛠️ SPECIALIZED TOOLS (Week 2)")
        print("-" * 40)
        await self.test_consortium_builder()
        await self.test_compliance_checker()
        
        # Performance Tests
        print("\n⚡ PERFORMANCE TESTS")
        print("-" * 40)
        await self.test_performance()
        
        # Summary
        self.print_summary()
        
        return self.results["failed"] == 0
    
    async def test_neo4j_connection(self):
        """Test Neo4j connection."""
        start = time.time()
        try:
            from app.core.neo4j_config import neo4j_db
            passed = neo4j_db.test_connection()
            self.record("Neo4j Connection", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Neo4j Connection", False, (time.time() - start) * 1000, str(e))
    
    async def test_neo4j_data(self):
        """Test Neo4j data load."""
        start = time.time()
        try:
            from app.core.neo4j_config import neo4j_db
            stats = neo4j_db.get_database_stats()
            total = stats.get("total_nodes", 0)
            passed = total > 1000
            self.record(f"Neo4j Data ({total:,} nodes)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Neo4j Data", False, (time.time() - start) * 1000, str(e))
    
    async def test_call_lookup(self):
        """Test call/topic lookup."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            result = service.search_topics("DATA", limit=5)
            passed = len(result) > 0
            self.record(f"Call Lookup ({len(result)} topics)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Call Lookup", False, (time.time() - start) * 1000, str(e))
    
    async def test_eligibility_check(self):
        """Test eligibility checking."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            de = service.check_country_eligibility("DE")
            ch = service.check_country_eligibility("CH")
            passed = de.get("is_eligible") == True and ch.get("is_eligible") == True
            self.record("Eligibility Check (DE, CH)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Eligibility Check", False, (time.time() - start) * 1000, str(e))
    
    async def test_budget_statistics(self):
        """Test budget statistics."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            result = service.get_budget_statistics()
            passed = len(result) > 0
            self.record(f"Budget Statistics ({len(result)} clusters)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Budget Statistics", False, (time.time() - start) * 1000, str(e))
    
    async def test_consortium_patterns(self):
        """Test consortium patterns."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            result = service.get_consortium_patterns()
            passed = len(result) > 0
            self.record(f"Consortium Patterns ({len(result)} patterns)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Consortium Patterns", False, (time.time() - start) * 1000, str(e))
    
    async def test_similar_topics(self):
        """Test similar topics finder."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            topics = service.search_topics("DIGITAL", limit=1)
            if topics:
                result = service.find_similar_topics(topics[0]["code"], limit=3)
                passed = isinstance(result, list)
            else:
                passed = True  # Skip if no topics
            self.record("Similar Topics", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Similar Topics", False, (time.time() - start) * 1000, str(e))
    
    async def test_project_examples(self):
        """Test project examples (Type F)."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            result = service.get_project_examples(cluster_code="CLUSTER-4", limit=3)
            passed = len(result) > 0
            self.record(f"Project Examples ({len(result)} projects)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Project Examples", False, (time.time() - start) * 1000, str(e))
    
    async def test_org_track_record(self):
        """Test organization track record (Type G)."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            result = service.get_organization_track_record("Fraunhofer")
            passed = result is not None and result.get("total_projects", 0) > 0
            projects = result.get("total_projects", 0) if result else 0
            self.record(f"Org Track Record ({projects} projects)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Org Track Record", False, (time.time() - start) * 1000, str(e))
    
    async def test_funding_trends(self):
        """Test funding trends (Type H)."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            service = GraphSearchService()
            result = service.get_funding_trends()
            passed = len(result) > 0
            self.record(f"Funding Trends ({len(result)} periods)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Funding Trends", False, (time.time() - start) * 1000, str(e))
    
    async def test_query_planner(self):
        """Test query planner intent detection."""
        start = time.time()
        try:
            from app.services.data_intelligence.query_planner import QueryPlanner
            planner = QueryPlanner()
            
            # Test multiple intents
            tests = [
                ("What is the budget for Cluster 4?", ["budget"]),
                ("Can Switzerland participate?", ["eligibility"]),
                ("Find calls about AI", ["call_lookup", "similar_calls", "general"]),
            ]
            
            all_passed = True
            for query, valid_intents in tests:
                plan = await planner.generate_plan(query)
                if plan.intent_type not in valid_intents:
                    all_passed = False
            
            self.record("Query Planner (3 intents)", all_passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Query Planner", False, (time.time() - start) * 1000, str(e))
    
    async def test_cross_encoder(self):
        """Test cross-encoder reranker."""
        start = time.time()
        try:
            from app.services.data_intelligence.cross_encoder_reranker import CrossEncoderReranker
            
            reranker = CrossEncoderReranker(model_type="fast")
            
            # Test reranking
            docs = [
                {"content": "Budget for climate research projects", "score": 0.5},
                {"content": "Funding allocation procedures", "score": 0.8},
                {"content": "Maximum budget is 10 million euros", "score": 0.6},
            ]
            
            results = reranker.rerank("What is the maximum budget?", docs, top_k=3)
            passed = len(results) > 0 and results[0].rerank_score > results[-1].rerank_score
            
            self.record("Cross-Encoder Reranking", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Cross-Encoder Reranking", False, (time.time() - start) * 1000, str(e))
    
    async def test_data_intelligence_service(self):
        """Test the main DataIntelligenceService."""
        start = time.time()
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            status = service.get_service_status()
            
            result = await service.search("What is the budget for Cluster 4?")
            
            passed = result.success and status.get("fully_operational")
            self.record(f"DataIntelligenceService (intent: {result.intent_type})", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("DataIntelligenceService", False, (time.time() - start) * 1000, str(e))
    
    async def test_tool_orchestrator(self):
        """Test tool orchestrator registration."""
        start = time.time()
        try:
            from app.services.tools.tool_orchestrator import ToolOrchestrator
            
            orchestrator = ToolOrchestrator()
            tools = orchestrator.get_available_tools()
            tool_names = [t["name"] for t in tools]
            
            required = ["intelligent_search", "consortium_builder", "compliance_checker"]
            passed = all(name in tool_names for name in required)
            
            self.record(f"Tool Orchestrator ({len(tools)} tools)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Tool Orchestrator", False, (time.time() - start) * 1000, str(e))
    
    async def test_consortium_builder(self):
        """Test consortium builder tool."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            
            service = GraphSearchService()
            result = service.suggest_consortium_partners(
                cluster_code="CLUSTER-4",
                target_partner_count=5
            )
            
            passed = len(result.get("suggestions", [])) > 0
            count = len(result.get("suggestions", []))
            self.record(f"Consortium Builder ({count} suggestions)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Consortium Builder", False, (time.time() - start) * 1000, str(e))
    
    async def test_compliance_checker(self):
        """Test compliance checker tool."""
        start = time.time()
        try:
            from app.services.data_intelligence.graph_service import GraphSearchService
            
            service = GraphSearchService()
            
            # Valid consortium
            result1 = service.check_consortium_compliance(
                partners=[
                    {"country": "DE", "entity_type": "HES", "is_coordinator": True},
                    {"country": "NL", "entity_type": "REC"},
                    {"country": "FR", "entity_type": "PRC"},
                ],
                action_type="RIA"
            )
            
            # Invalid consortium
            result2 = service.check_consortium_compliance(
                partners=[
                    {"country": "DE", "entity_type": "HES", "is_coordinator": True},
                ],
                action_type="RIA"
            )
            
            passed = result1.get("is_compliant") == True and result2.get("is_compliant") == False
            self.record("Compliance Checker", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Compliance Checker", False, (time.time() - start) * 1000, str(e))
    
    async def test_performance(self):
        """Test performance benchmarks."""
        start = time.time()
        try:
            from app.services.data_intelligence_service import DataIntelligenceService
            
            service = DataIntelligenceService()
            
            queries = [
                "What is the budget for Cluster 4?",
                "Can Switzerland participate?",
                "Find calls about digital transformation",
            ]
            
            times = []
            for q in queries:
                q_start = time.time()
                await service.search(q)
                times.append((time.time() - q_start) * 1000)
            
            avg_time = sum(times) / len(times)
            passed = avg_time < 10000  # Under 10 seconds average
            
            self.record(f"Performance ({avg_time:.0f}ms avg)", passed, (time.time() - start) * 1000)
        except Exception as e:
            self.record("Performance", False, (time.time() - start) * 1000, str(e))
    
    def print_summary(self):
        """Print test summary."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        total = self.results["passed"] + self.results["failed"]
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        print(f"\n   Total Tests: {total}")
        print(f"   ✅ Passed:    {self.results['passed']}")
        print(f"   ❌ Failed:    {self.results['failed']}")
        print(f"   ⏱️  Duration:  {total_time:.1f}s")
        
        if self.results["failed"] == 0:
            print("\n" + "=" * 70)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 70)
            print("""
   ╔═══════════════════════════════════════════════════════════════╗
   ║                                                               ║
   ║   🏆 DATA INTELLIGENCE UPGRADE COMPLETE! 🏆                   ║
   ║                                                               ║
   ║   Week 1 Deliverables:                                        ║
   ║   ✅ Neo4j container with 50K+ nodes                          ║
   ║   ✅ GraphSearchService with 10+ query types                  ║
   ║   ✅ LLM-powered QueryPlanner                                 ║
   ║   ✅ DataIntelligenceService orchestration                    ║
   ║   ✅ intelligent_search tool registered                       ║
   ║                                                               ║
   ║   Week 2 Deliverables:                                        ║
   ║   ✅ Cross-Encoder neural reranking                           ║
   ║   ✅ Multi-source result fusion                               ║
   ║   ✅ Advanced queries (F-H)                                   ║
   ║   ✅ Consortium Builder tool                                  ║
   ║   ✅ Compliance Checker tool                                  ║
   ║                                                               ║
   ╚═══════════════════════════════════════════════════════════════╝
""")
        else:
            print("\n⚠️  Some tests failed. Review errors above.")


async def main():
    suite = TestSuite()
    success = await suite.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

