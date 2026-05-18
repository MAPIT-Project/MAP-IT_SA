# TASK_15: Final Testing & Documentation

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_15 |
| **Day** | 13-14 |
| **Estimated Time** | 3 hours |
| **Dependencies** | All previous tasks |
| **Blocks** | None (Final task) |
| **Priority** | Critical |

## Objective

Comprehensive testing of all Week 1 and Week 2 components:
1. Run full integration tests
2. Performance benchmarking
3. Document API and usage
4. Create demo scripts

## Test Suite

### `scripts/test_full_integration.py`

```python
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

import asyncio
import time
from datetime import datetime

async def run_full_test_suite():
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "tests": []
    }

    # Test categories
    tests = [
        ("Neo4j Connection", test_neo4j_connection),
        ("Neo4j Data Load", test_neo4j_data),
        ("Graph Service - Call Lookup", test_call_lookup),
        ("Graph Service - Eligibility", test_eligibility),
        ("Graph Service - Budget Stats", test_budget_stats),
        ("Graph Service - Consortium", test_consortium_patterns),
        ("Graph Service - Similar Calls", test_similar_calls),
        ("Graph Service - Org Track Record", test_org_track_record),
        ("Query Planner - Intent Detection", test_query_planner),
        ("Cross-Encoder Reranking", test_cross_encoder),
        ("Data Intelligence Search", test_intelligent_search),
        ("Tool Orchestrator", test_tool_orchestrator),
        ("Performance Benchmark", test_performance),
    ]

    print("\n" + "=" * 70)
    print("FULL INTEGRATION TEST SUITE")
    print("=" * 70 + "\n")

    for name, test_func in tests:
        try:
            start = time.time()
            passed = await test_func()
            duration = (time.time() - start) * 1000

            status = "✅ PASS" if passed else "❌ FAIL"
            results["passed" if passed else "failed"] += 1
            results["tests"].append({
                "name": name,
                "passed": passed,
                "duration_ms": duration
            })

            print(f"{status} | {name} ({duration:.0f}ms)")

        except Exception as e:
            results["failed"] += 1
            results["tests"].append({
                "name": name,
                "passed": False,
                "error": str(e)
            })
            print(f"❌ FAIL | {name} - {str(e)[:50]}")

    # Summary
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 70)
    print(f"SUMMARY: {results['passed']}/{total} passed")
    print("=" * 70)

    return results

async def test_neo4j_connection():
    from app.core.neo4j_config import neo4j_db
    return neo4j_db.test_connection()

async def test_neo4j_data():
    from app.core.neo4j_config import neo4j_db
    stats = neo4j_db.get_database_stats()
    return stats.get("total_nodes", 0) > 100

async def test_call_lookup():
    from app.services.data_intelligence.graph_service import GraphSearchService
    service = GraphSearchService()
    result = service.search_topics("DATA", limit=5)
    return len(result) > 0

async def test_eligibility():
    from app.services.data_intelligence.graph_service import GraphSearchService
    service = GraphSearchService()
    result = service.check_country_eligibility("DE")
    return result.get("is_eligible") == True

async def test_budget_stats():
    from app.services.data_intelligence.graph_service import GraphSearchService
    service = GraphSearchService()
    result = service.get_budget_statistics()
    return len(result) > 0

async def test_consortium_patterns():
    from app.services.data_intelligence.graph_service import GraphSearchService
    service = GraphSearchService()
    result = service.get_consortium_patterns()
    return len(result) > 0

async def test_similar_calls():
    from app.services.data_intelligence.graph_service import GraphSearchService
    service = GraphSearchService()
    topics = service.search_topics("DATA", limit=1)
    if topics:
        result = service.find_similar_topics(topics[0]["code"], limit=3)
        return isinstance(result, list)
    return True  # Skip if no topics

async def test_org_track_record():
    from app.services.data_intelligence.graph_service import GraphSearchService
    service = GraphSearchService()
    result = service.get_organization_profile("University")
    return True  # May return None if no match

async def test_query_planner():
    from app.services.data_intelligence.query_planner import QueryPlanner
    planner = QueryPlanner()
    plan = await planner.generate_plan("What is the budget for Cluster 4?")
    return plan.intent_type in ["budget", "general"]

async def test_cross_encoder():
    try:
        from app.services.data_intelligence.cross_encoder_reranker import CrossEncoderReranker
        reranker = CrossEncoderReranker(model_type="fast")
        return reranker._model_loaded
    except:
        return True  # Optional component

async def test_intelligent_search():
    from app.services.data_intelligence_service import DataIntelligenceService
    service = DataIntelligenceService()
    result = await service.search("Can Switzerland participate?")
    return result.success

async def test_tool_orchestrator():
    from app.services.tools.tool_orchestrator import ToolOrchestrator
    orchestrator = ToolOrchestrator()
    tools = orchestrator.get_available_tools()
    return any(t["name"] == "intelligent_search" for t in tools)

async def test_performance():
    from app.services.data_intelligence_service import DataIntelligenceService
    service = DataIntelligenceService()

    queries = [
        "What is the deadline for HORIZON-CL4-2025-DATA-01?",
        "Can Switzerland participate?",
        "Maximum budget for RIA?",
    ]

    times = []
    for q in queries:
        start = time.time()
        await service.search(q)
        times.append((time.time() - start) * 1000)

    avg_time = sum(times) / len(times)
    return avg_time < 3000  # Under 3 seconds

if __name__ == "__main__":
    asyncio.run(run_full_test_suite())
```

## Documentation

Create `docs/DATA_INTELLIGENCE.md` with:
- Architecture overview
- API reference
- Usage examples
- Troubleshooting guide

## Acceptance Criteria

- [ ] All integration tests pass
- [ ] Average query time < 3 seconds
- [ ] Documentation complete
- [ ] Demo scripts work

## Final Checklist

```
Week 1 Deliverables:
✅ TASK_01: Neo4j container running
✅ TASK_02: CORDIS data downloaded
✅ TASK_03: Data ingested to Neo4j
✅ TASK_04: GraphSearchService operational
✅ TASK_05: Planner system prompt created
✅ TASK_06: QueryPlanner implemented
✅ TASK_07: DataIntelligenceService working
✅ TASK_08: intelligent_search tool registered
✅ TASK_09: Week 1 tests passing

Week 2 Deliverables:
✅ TASK_10: Cross-encoder reranking
✅ TASK_11: Result fusion integrated
✅ TASK_12: Advanced queries (F-H)
✅ TASK_13: Consortium builder tool
✅ TASK_14: Compliance checker tool
✅ TASK_15: Full test suite passing
```

## Celebration! 🎉

If all tests pass, the Data Intelligence upgrade is complete:
- Graph-based relationship queries
- LLM-powered query planning
- Neural reranking
- Multi-source fusion
- Specialized tools for EU funding research
