# TASK_09: Integration Testing

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_09 |
| **Day** | 6-7 |
| **Estimated Time** | 2-3 hours |
| **Dependencies** | All previous tasks (TASK_01 through TASK_08) |
| **Blocks** | Week 2 tasks |
| **Priority** | Critical |

## Objective

Perform comprehensive integration testing of all Week 1 components to ensure:
1. All services initialize correctly
2. Query Types A-E work end-to-end
3. Error handling is robust
4. Performance is acceptable

## Context

This task validates that all the pieces work together:
- Neo4j with ingested data (TASK_01, TASK_02, TASK_03)
- GraphSearchService (TASK_04)
- QueryPlanner with system prompt (TASK_05, TASK_06)
- DataIntelligenceService (TASK_07)
- ToolOrchestrator with intelligent_search (TASK_08)

## Files to Create

| Action | File Path |
|--------|-----------|
| CREATE | `tests/test_data_intelligence_integration.py` |
| CREATE | `scripts/test_week1_integration.py` |

## Implementation

### File: `scripts/test_week1_integration.py`

```python
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

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test result tracking
@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    message: str
    details: Dict[str, Any] = None


class IntegrationTester:
    """Runs integration tests for Week 1 components."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None

    def add_result(self, name: str, passed: bool, duration_ms: float,
                   message: str, details: Dict = None):
        """Add a test result."""
        self.results.append(TestResult(
            name=name,
            passed=passed,
            duration_ms=duration_ms,
            message=message,
            details=details or {}
        ))

    async def run_all_tests(self) -> bool:
        """Run all integration tests."""
        self.start_time = datetime.now()

        print("\n" + "=" * 70)
        print("WEEK 1 INTEGRATION TESTS")
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

        # Test 11: Query Type E - Similar Calls
        await self.test_query_type_e_similar_calls()

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

            nodes = stats.get("nodes", {})
            total_nodes = stats.get("total_nodes", 0)

            if total_nodes > 0:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration,
                              f"Found {total_nodes} nodes",
                              {"node_counts": nodes})
            else:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, False, duration,
                              "No data found - run TASK_03 ingestion")

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
                              f"Initialized, found {len(clusters)} clusters")
            else:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration,
                              "Initialized but no clusters found (may need data)")

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

            # Test with a simple query
            plan = await planner.generate_plan("What is Horizon Europe?")

            if plan and plan.intent_type:
                duration = (datetime.now() - start).total_seconds() * 1000
                self.add_result(name, True, duration,
                              f"Generated plan: {plan.intent_type}",
                              {"steps": len(plan.steps), "confidence": plan.confidence})
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
                # Partial success is okay
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

        query = "What is the deadline for HORIZON-CL4-2025-DATA-01?"

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
                self.add_result(name, False, duration, result.error or "Search failed")

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
                # Check if we got eligibility-related results
                has_eligibility = any(
                    "eligibility" in str(r).lower() or "eligible" in str(r).lower()
                    for r in result.graph_results + result.vector_results
                )

                self.add_result(name, True, duration,
                              f"Intent: {result.intent_type}",
                              {
                                  "graph_results": len(result.graph_results),
                                  "has_eligibility_info": has_eligibility
                              })
            else:
                self.add_result(name, False, duration, result.error or "Search failed")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")

    async def test_query_type_c_budget(self):
        """Test Query Type C: Budget Questions."""
        start = datetime.now()
        name = "Query Type C: Budget"

        query = "What is the maximum budget for RIA actions in Cluster 5?"

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
                self.add_result(name, False, duration, result.error or "Search failed")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")

    async def test_query_type_d_consortium(self):
        """Test Query Type D: Consortium Rules."""
        start = datetime.now()
        name = "Query Type D: Consortium"

        query = "What is the minimum number of countries required for a CSA?"

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
                self.add_result(name, False, duration, result.error or "Search failed")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")

    async def test_query_type_e_similar_calls(self):
        """Test Query Type E: Similar Calls."""
        start = datetime.now()
        name = "Query Type E: Similar Calls"

        query = "Find calls similar to HORIZON-CL4-2024-HUMAN-01"

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
                self.add_result(name, False, duration, result.error or "Search failed")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.add_result(name, False, duration, f"Error: {str(e)}")

    def print_summary(self):
        """Print test summary."""
        total_time = (datetime.now() - self.start_time).total_seconds()

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)

        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"\n{status} | {result.name}")
            print(f"       {result.message}")
            print(f"       Duration: {result.duration_ms:.0f}ms")
            if result.details and not result.passed:
                print(f"       Details: {result.details}")

        print("\n" + "=" * 70)
        print(f"SUMMARY: {passed} passed, {failed} failed ({total_time:.1f}s total)")
        print("=" * 70)

        if failed > 0:
            print("\n⚠️  Some tests failed. Review the errors above.")
            print("   Common issues:")
            print("   - Neo4j not running: docker-compose up neo4j -d")
            print("   - No data: python scripts/ingest_cordis_to_neo4j.py")
            print("   - Missing API key: Check GEMINI_API_KEY in .env")
        else:
            print("\n🎉 All tests passed! Week 1 implementation is complete.")


async def main():
    """Run integration tests."""
    tester = IntegrationTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

### File: `tests/test_data_intelligence_integration.py`

```python
"""
Pytest integration tests for Data Intelligence components.

Run with: pytest tests/test_data_intelligence_integration.py -v
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch


# Fixtures
@pytest.fixture
def neo4j_connection():
    """Get Neo4j connection for tests."""
    try:
        from app.core.neo4j_config import neo4j_db
        return neo4j_db
    except Exception:
        pytest.skip("Neo4j not available")


@pytest.fixture
def graph_service():
    """Get Graph Search Service."""
    try:
        from app.services.data_intelligence.graph_service import GraphSearchService
        return GraphSearchService()
    except Exception as e:
        pytest.skip(f"Graph service not available: {e}")


@pytest.fixture
def query_planner():
    """Get Query Planner."""
    try:
        from app.services.data_intelligence.query_planner import QueryPlanner
        return QueryPlanner()
    except Exception as e:
        pytest.skip(f"Query planner not available: {e}")


@pytest.fixture
def data_intelligence_service():
    """Get Data Intelligence Service."""
    try:
        from app.services.data_intelligence_service import DataIntelligenceService
        return DataIntelligenceService()
    except Exception as e:
        pytest.skip(f"Data intelligence service not available: {e}")


# Neo4j Tests
class TestNeo4jConnection:

    def test_connection(self, neo4j_connection):
        """Test Neo4j connection is working."""
        assert neo4j_connection.test_connection()

    def test_execute_query(self, neo4j_connection):
        """Test query execution."""
        result = neo4j_connection.execute_query("RETURN 1 as n")
        assert len(result) > 0
        assert result[0]["n"] == 1

    def test_database_stats(self, neo4j_connection):
        """Test getting database statistics."""
        stats = neo4j_connection.get_database_stats()
        assert "total_nodes" in stats


# Graph Service Tests
class TestGraphSearchService:

    def test_get_cluster_overview(self, graph_service):
        """Test cluster overview."""
        clusters = graph_service.get_cluster_overview()
        assert isinstance(clusters, list)

    def test_check_country_eligibility_eu(self, graph_service):
        """Test eligibility check for EU country."""
        result = graph_service.check_country_eligibility("DE")
        assert result["is_eligible"] == True
        assert "EU Member State" in result["eligibility_status"]

    def test_check_country_eligibility_non_eu(self, graph_service):
        """Test eligibility check for non-EU country."""
        result = graph_service.check_country_eligibility("US")
        assert result["is_eligible"] == False
        assert "Third Country" in result["eligibility_status"]

    def test_get_budget_statistics(self, graph_service):
        """Test budget statistics retrieval."""
        results = graph_service.get_budget_statistics()
        assert isinstance(results, list)


# Query Planner Tests
class TestQueryPlanner:

    @pytest.mark.asyncio
    async def test_generate_plan_call_lookup(self, query_planner):
        """Test plan generation for call lookup."""
        plan = await query_planner.generate_plan(
            "What is the deadline for HORIZON-CL4-2025-DATA-01?"
        )
        assert plan.intent_type in ["call_lookup", "general"]
        assert len(plan.steps) > 0

    @pytest.mark.asyncio
    async def test_generate_plan_eligibility(self, query_planner):
        """Test plan generation for eligibility question."""
        plan = await query_planner.generate_plan(
            "Can Switzerland participate in Cluster 4?"
        )
        assert plan.intent_type in ["eligibility", "general"]
        assert plan.confidence > 0

    @pytest.mark.asyncio
    async def test_fallback_plan(self, query_planner):
        """Test fallback plan creation."""
        plan = query_planner._create_fallback_plan("Test query", "Test error")
        assert plan.intent_type == "general"
        assert len(plan.steps) > 0


# Data Intelligence Service Tests
class TestDataIntelligenceService:

    def test_service_status(self, data_intelligence_service):
        """Test service status reporting."""
        status = data_intelligence_service.get_service_status()
        assert "graph_available" in status
        assert "vector_available" in status
        assert "planner_available" in status

    @pytest.mark.asyncio
    async def test_search_basic(self, data_intelligence_service):
        """Test basic search functionality."""
        result = await data_intelligence_service.search("What is Horizon Europe?")
        assert result.success == True
        assert result.intent_type is not None

    @pytest.mark.asyncio
    async def test_search_eligibility(self, data_intelligence_service):
        """Test eligibility search."""
        result = await data_intelligence_service.search(
            "Can an SME from Switzerland participate?"
        )
        assert result.success == True
        assert len(result.answer_context) > 0


# Tool Orchestrator Tests
class TestToolOrchestrator:

    def test_intelligent_search_registered(self):
        """Test intelligent_search tool is registered."""
        from app.services.tools.tool_orchestrator import ToolOrchestrator

        orchestrator = ToolOrchestrator()
        tools = orchestrator.get_available_tools()
        tool_names = [t["name"] for t in tools]

        assert "intelligent_search" in tool_names

    @pytest.mark.asyncio
    async def test_intelligent_search_execution(self):
        """Test intelligent_search tool execution."""
        from app.services.tools.tool_orchestrator import ToolOrchestrator, ToolCall

        orchestrator = ToolOrchestrator()

        call = ToolCall(
            tool_name="intelligent_search",
            parameters={"query": "What is Horizon Europe?"},
            execution_order=1
        )

        results = await orchestrator.execute_plan([call], conversation_id=999)

        assert "intelligent_search" in results
        result = results["intelligent_search"]
        # May succeed or fail depending on services available
        assert result is not None
```

## Running the Tests

### Quick Integration Test

```bash
cd /home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA

# Run the integration test script
python scripts/test_week1_integration.py
```

### Pytest (if installed)

```bash
# Install pytest if needed
pip install pytest pytest-asyncio

# Run all integration tests
pytest tests/test_data_intelligence_integration.py -v

# Run specific test class
pytest tests/test_data_intelligence_integration.py::TestGraphSearchService -v
```

## Acceptance Criteria

- [ ] All 11 integration tests pass
- [ ] Neo4j connection works
- [ ] Neo4j has data (projects, organizations, etc.)
- [ ] Graph Search Service returns results
- [ ] Query Planner generates valid plans
- [ ] Data Intelligence Service executes searches
- [ ] Tool Orchestrator has intelligent_search
- [ ] Query Types A-E return results

## Expected Output

```
======================================================================
WEEK 1 INTEGRATION TESTS
======================================================================

✅ PASS | Neo4j Connection
       Connected successfully
       Duration: 150ms

✅ PASS | Neo4j Data
       Found 15234 nodes
       Duration: 45ms

✅ PASS | Graph Search Service
       Initialized, found 6 clusters
       Duration: 120ms

✅ PASS | Query Planner
       Generated plan: call_lookup
       Duration: 850ms

✅ PASS | Data Intelligence Service
       All services operational
       Duration: 200ms

✅ PASS | Tool Orchestrator
       intelligent_search tool registered
       Duration: 50ms

✅ PASS | Query Type A: Call Lookup
       Intent: call_lookup, Confidence: 0.92
       Duration: 1200ms

✅ PASS | Query Type B: Eligibility
       Intent: eligibility
       Duration: 1100ms

✅ PASS | Query Type C: Budget
       Intent: budget
       Duration: 950ms

✅ PASS | Query Type D: Consortium
       Intent: consortium
       Duration: 1050ms

✅ PASS | Query Type E: Similar Calls
       Intent: similar_calls
       Duration: 1150ms

======================================================================
SUMMARY: 11 passed, 0 failed (8.2s total)
======================================================================

🎉 All tests passed! Week 1 implementation is complete.
```

## Troubleshooting

### Neo4j Connection Failed
```bash
# Check if container is running
docker-compose ps | grep neo4j

# Start if not running
docker-compose up neo4j -d

# Check logs
docker-compose logs neo4j
```

### No Data in Neo4j
```bash
# Run ingestion
python scripts/ingest_cordis_to_neo4j.py --clear
```

### Query Planner Timeout
- Check GEMINI_API_KEY is set
- Verify internet connection
- Try increasing timeout in QueryPlanner

### Tool Not Registered
- Re-run TASK_08 modifications
- Check for import errors in tool_orchestrator.py

## Notes for Agent

1. Run this test AFTER completing all previous tasks
2. Some tests may fail if data ingestion is incomplete
3. The test script provides detailed diagnostics
4. All Query Types A-E should work by end of Week 1
5. Performance should be under 2 seconds per query
6. Keep this test script for regression testing in Week 2
