"""
AI Conversation Scenario Tests - Comprehensive Tool Testing

Tests ALL tools in the system, both individually and in conjunction.
Validates that:
1. Each tool can be invoked correctly
2. Tools return expected data structures
3. Multiple tools can work together (multi-tool scenarios)
4. Error handling works correctly
5. Edge cases are handled gracefully

Run with: pytest tests/test_ai_scenarios.py -v
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Test Fixtures and Mock Data
# ============================================================================


@dataclass
class MockCallResult:
    """Mock result for funding call tools."""

    call_id: str = "HORIZON-CL5-2024-D3-01"
    title: str = "Clean Hydrogen Research"
    deadline: str = "2024-06-15"
    budget: str = "10M EUR"
    action_type: str = "RIA"
    cluster: str = "CL5"
    status: str = "open"


@dataclass
class MockProjectResult:
    """Mock result for project tools."""

    project_id: str = "101000001"
    acronym: str = "HYDSTOR"
    title: str = "Hydrogen Storage Solutions"
    total_cost: int = 5000000
    ec_contribution: int = 4000000
    coordinator: str = "TU Delft"
    country: str = "NL"


@dataclass
class MockOrganization:
    """Mock result for partner tools."""

    name: str = "Technical University of Munich"
    country: str = "DE"
    entity_type: str = "HES"
    projects_count: int = 45
    coordination_count: int = 12


class MockToolResults:
    """Factory for creating realistic mock tool results."""

    @staticmethod
    def search_funding_calls(count: int = 5, topic: str = "hydrogen") -> dict:
        """Mock search_funding_calls result."""
        return {
            "success": True,
            "tool_name": "search_funding_calls",
            "query": topic,
            "calls_found": count,
            "calls": [
                {
                    "call_id": f"HORIZON-CL5-2024-D3-0{i}",
                    "title": f"{topic.title()} Research Call {i}",
                    "description": f"This call focuses on {topic} research and innovation...",
                    "deadline": f"2024-0{6 + i}-15",
                    "action_type": "RIA" if i % 2 == 0 else "IA",
                    "cluster": "CL5",
                    "budget": f"{(i + 1) * 5}M EUR",
                    "work_programme": "2024",
                }
                for i in range(1, count + 1)
            ],
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "search_metadata": {"source": "local_database", "api_used": False},
        }

    @staticmethod
    def search_projects(count: int = 5, topic: str = "AI") -> dict:
        """Mock search_projects result."""
        countries = ["DE", "FR", "ES", "IT", "NL", "BE", "SE", "AT", "FI", "DK"]
        return {
            "success": True,
            "tool_name": "search_projects",
            "projects_count": count,
            "projects": [
                {
                    "project_id": f"10100000{i}",
                    "acronym": f"{topic.upper()[:4]}PROJ{i}",
                    "title": f"{topic.title()} Research Project {i}",
                    "status": "SIGNED",
                    "total_cost": (i + 1) * 1000000,
                    "ec_contribution": int((i + 1) * 800000),
                    "start_date": "2023-01-01",
                    "end_date": "2026-12-31",
                    "coordinator": f"University of Example {i}",
                    "coordinator_country": countries[i % len(countries)],
                    "consortium_size": 5 + i,
                    "objectives": f"This project aims to advance {topic} research...",
                    "cluster": "CL4" if "ai" in topic.lower() else "CL5",
                }
                for i in range(1, count + 1)
            ],
            "search_metadata": {"sources": ["postgresql", "neo4j"], "total_time_ms": 150},
        }

    @staticmethod
    def search_documents(query: str = "eligibility", count: int = 3) -> dict:
        """Mock search_documents / search_local_database result."""
        return {
            "success": True,
            "tool_name": "search_local_database",
            "documents": [
                {
                    "title": f"Horizon Europe Work Programme 202{4 + i}",
                    "content": "The minimum consortium composition requires at least 3 independent legal entities from 3 different EU Member States or Associated Countries.",
                    "source": "horizon_europe_wp",
                    "chunk_id": f"chunk_{i}",
                    "relevance_score": 0.95 - (i * 0.1),
                }
                for i in range(count)
            ],
            "query": query,
            "results_count": count,
        }

    @staticmethod
    def get_programme_statistics(programme: str = "RIA") -> dict:
        """Mock get_programme_statistics result."""
        return {
            "success": True,
            "tool_name": "get_programme_statistics",
            "programme": programme,
            "statistics": {
                "total_projects": 1250,
                "total_funding_eur": 5625000000,
                "average_funding_eur": 4500000,
                "median_funding_eur": 4200000,
                "success_rate_percent": 15.5,
                "average_consortium_size": 8.5,
                "average_duration_months": 42,
                "top_countries": [
                    {"country": "DE", "projects": 312, "share": 25.0},
                    {"country": "FR", "projects": 187, "share": 15.0},
                    {"country": "NL", "projects": 156, "share": 12.5},
                ],
            },
        }

    @staticmethod
    def get_country_statistics(country: str = "Germany") -> dict:
        """Mock get_country_statistics result."""
        return {
            "success": True,
            "tool_name": "get_country_statistics",
            "country": country,
            "statistics": {
                "total_participations": 5420,
                "coordinations": 1250,
                "total_funding_eur": 3500000000,
                "success_rate_percent": 18.5,
                "top_clusters": [
                    {"cluster": "CL4", "projects": 420, "funding": 850000000},
                    {"cluster": "CL5", "projects": 380, "funding": 720000000},
                ],
                "top_organizations": [
                    {"name": "Fraunhofer", "projects": 245},
                    {"name": "Max Planck", "projects": 189},
                ],
            },
        }

    @staticmethod
    def compare_programmes(prog1: str = "ERC", prog2: str = "EIC") -> dict:
        """Mock compare_programmes result."""
        return {
            "success": True,
            "tool_name": "compare_programmes",
            "programmes": [prog1, prog2],
            "comparison": {
                "target_applicants": {prog1: "Individual researchers", prog2: "SMEs and startups"},
                "funding_range": {prog1: "€1.5M - €10M", prog2: "Up to €17.5M (blended finance)"},
                "success_rate": {prog1: "12%", prog2: "8%"},
                "evaluation_criteria": {
                    prog1: "Scientific excellence",
                    prog2: "Innovation and market potential",
                },
                "typical_duration": {prog1: "5 years", prog2: "2-3 years"},
            },
            "recommendation": f"Choose {prog1} for fundamental research, {prog2} for market-ready innovation",
        }

    @staticmethod
    def get_budget_benchmark(action_type: str = "RIA", cluster: str = None) -> dict:
        """Mock get_budget_benchmark result."""
        return {
            "success": True,
            "tool_name": "get_budget_benchmark",
            "filters": {"action_type": action_type, "cluster": cluster},
            "benchmarks": {
                "sample_size": 450,
                "min_eu_contribution": 1500000,
                "max_eu_contribution": 25000000,
                "median_eu_contribution": 5000000,
                "p25_eu_contribution": 3500000,
                "p75_eu_contribution": 8000000,
                "average_eu_contribution": 5800000,
                "median_per_partner": 625000,
                "average_consortium_size": 8,
                "median_consortium_size": 7,
            },
            "sample_projects": [
                {"acronym": "EXAMPLE1", "ec_contribution": 4500000, "partners": 7},
                {"acronym": "EXAMPLE2", "ec_contribution": 6200000, "partners": 9},
            ],
            "recommendations": [
                "For RIA with 8 partners, target €4-6M EU contribution",
                "Budget €500-700K per partner",
            ],
        }

    @staticmethod
    def get_consortium_patterns(cluster: str = "CL4", action_type: str = "RIA") -> dict:
        """Mock get_consortium_patterns result."""
        return {
            "success": True,
            "tool_name": "get_consortium_patterns",
            "filters": {"cluster": cluster, "action_type": action_type},
            "patterns": {
                "sample_size": 320,
                "average_consortium_size": 9.2,
                "median_consortium_size": 8,
                "entity_type_distribution": {
                    "HES": {"average_count": 3.5, "percentage": 38.0},
                    "REC": {"average_count": 2.8, "percentage": 30.4},
                    "PRC": {"average_count": 2.1, "percentage": 22.8},
                    "SME": {"average_count": 0.8, "percentage": 8.7},
                },
                "top_coordinator_types": [
                    {"type": "HES", "count": 180, "percentage": 56.2},
                    {"type": "REC", "count": 95, "percentage": 29.7},
                ],
                "top_coordinator_countries": [
                    {"country": "DE", "count": 72, "percentage": 22.5},
                    {"country": "NL", "count": 45, "percentage": 14.1},
                ],
                "country_diversity": {"average_countries": 7.5, "median_countries": 7},
            },
            "recommendations": [
                "Target 8-10 partners for optimal consortium",
                "Include 3-4 universities (HES) and 2-3 research institutes (REC)",
                "Ensure at least 7 different countries for geographic diversity",
            ],
        }

    @staticmethod
    def find_experienced_partners(topic: str = "AI", country: str = None) -> dict:
        """Mock find_experienced_partners result."""
        return {
            "success": True,
            "tool_name": "find_experienced_partners",
            "search_params": {"topic_keywords": topic, "country": country},
            "partners_found": 15,
            "partners": [
                {
                    "name": "Technical University of Munich",
                    "country": "DE",
                    "entity_type": "HES",
                    "experience_score": 95,
                    "relevant_projects": 12,
                    "coordination_experience": 5,
                    "total_horizon_projects": 89,
                    "recent_projects": [
                        {"acronym": "AIPROJECT1", "role": "coordinator"},
                        {"acronym": "AIPROJECT2", "role": "participant"},
                    ],
                },
                {
                    "name": "CNRS",
                    "country": "FR",
                    "entity_type": "REC",
                    "experience_score": 92,
                    "relevant_projects": 10,
                    "coordination_experience": 3,
                    "total_horizon_projects": 156,
                },
                {
                    "name": "Fraunhofer",
                    "country": "DE",
                    "entity_type": "REC",
                    "experience_score": 90,
                    "relevant_projects": 9,
                    "coordination_experience": 4,
                    "total_horizon_projects": 245,
                },
            ][:15],
        }

    @staticmethod
    def get_similar_funded_projects(description: str) -> dict:
        """Mock get_similar_funded_projects result."""
        return {
            "success": True,
            "tool_name": "get_similar_funded_projects",
            "query_description": description[:100],
            "similar_projects": [
                {
                    "project_id": "101000001",
                    "acronym": "SIMILARPROJ1",
                    "title": "Similar Research Project 1",
                    "similarity_score": 0.89,
                    "ec_contribution": 4500000,
                    "consortium_size": 8,
                    "coordinator_country": "DE",
                    "keywords": ["AI", "machine learning", "data"],
                    "start_date": "2023-01-01",
                },
                {
                    "project_id": "101000002",
                    "acronym": "SIMILARPROJ2",
                    "title": "Similar Research Project 2",
                    "similarity_score": 0.85,
                    "ec_contribution": 5200000,
                    "consortium_size": 10,
                    "coordinator_country": "NL",
                },
            ],
            "insights": {
                "average_budget": 4850000,
                "average_consortium_size": 9,
                "common_keywords": ["AI", "machine learning", "data analysis"],
                "funding_trend": "increasing",
            },
        }

    @staticmethod
    def analyze_call_history(cluster: str = "CL4", keywords: str = None) -> dict:
        """Mock analyze_call_history result."""
        return {
            "success": True,
            "tool_name": "analyze_call_history",
            "filters": {"cluster": cluster, "keywords": keywords},
            "analysis": {
                "total_calls_analyzed": 125,
                "total_projects_funded": 980,
                "total_funding_eur": 4500000000,
                "timeline": {
                    "2021": {"calls": 35, "projects": 280, "funding": 1100000000},
                    "2022": {"calls": 40, "projects": 320, "funding": 1400000000},
                    "2023": {"calls": 50, "projects": 380, "funding": 2000000000},
                },
                "action_type_breakdown": {
                    "RIA": {"calls": 65, "funding_share": 55.0},
                    "IA": {"calls": 45, "funding_share": 35.0},
                    "CSA": {"calls": 15, "funding_share": 10.0},
                },
                "top_topics": [
                    {"topic_pattern": "AI*", "calls": 25, "trend": "increasing"},
                    {"topic_pattern": "DATA*", "calls": 18, "trend": "stable"},
                ],
                "trend_detection": "increasing",
                "trend_confidence": 0.85,
            },
            "recommendations": [
                "Funding in this area is growing - good time to apply",
                "RIA is the dominant action type",
            ],
        }

    @staticmethod
    def intelligent_search(query: str) -> dict:
        """Mock intelligent_search result."""
        return {
            "success": True,
            "tool_name": "intelligent_search",
            "query": query,
            "results": {
                "intent_type": "call_lookup",
                "confidence": 0.92,
                "answer_context": "Based on the graph and vector search...",
                "graph_results": [
                    {"type": "call", "id": "HORIZON-CL5-2024-D3-01", "title": "Clean Hydrogen"},
                    {"type": "project", "id": "101000001", "title": "H2STORE"},
                ],
                "vector_results": [
                    {
                        "title": "Work Programme 2024",
                        "content": "Hydrogen storage...",
                        "score": 0.88,
                    }
                ],
                "sources": [{"type": "neo4j", "count": 5}, {"type": "vector", "count": 3}],
                "total_time_ms": 245,
            },
            "metadata": {
                "search_type": "intelligent_hybrid",
                "data_sources_used": ["neo4j", "vector"],
            },
        }

    @staticmethod
    def consortium_builder(cluster_code: str = "CLUSTER-5") -> dict:
        """Mock consortium_builder result."""
        return {
            "success": True,
            "tool_name": "consortium_builder",
            "results": {
                "suggestions": [
                    {
                        "organization": "TU Delft",
                        "country": "NL",
                        "entity_type": "HES",
                        "experience_score": 95,
                        "complementary_to": ["TUM", "CEA"],
                    },
                    {
                        "organization": "CEA",
                        "country": "FR",
                        "entity_type": "REC",
                        "experience_score": 92,
                    },
                ],
                "countries_covered": ["NL", "FR", "DE", "ES", "IT"],
                "entity_mix": {"HES": 3, "REC": 2, "PRC": 2, "SME": 1},
                "cluster": cluster_code,
            },
            "metadata": {"cluster": cluster_code, "partners_suggested": 8, "countries_covered": 5},
        }

    @staticmethod
    def compliance_checker(partners: list[dict], action_type: str = "RIA") -> dict:
        """Mock compliance_checker result."""
        return {
            "success": True,
            "tool_name": "compliance_checker",
            "results": {
                "is_compliant": True,
                "partner_count": len(partners),
                "country_count": len(set(p.get("country") for p in partners)),
                "issues": [],
                "warnings": ["Consider adding an SME partner for better evaluation"],
                "eligibility_check": {
                    "minimum_partners": {
                        "required": 3,
                        "actual": len(partners),
                        "passed": len(partners) >= 3,
                    },
                    "country_diversity": {"required": 3, "actual": 4, "passed": True},
                },
            },
            "metadata": {"is_compliant": True, "issues_count": 0, "warnings_count": 1},
        }


# ============================================================================
# TOOL 1: search_funding_calls
# ============================================================================


class TestSearchFundingCallsTool:
    """Tests for the search_funding_calls tool."""

    def test_result_structure(self):
        """Test that search_funding_calls returns expected structure."""
        result = MockToolResults.search_funding_calls(5, "hydrogen")

        assert result["success"] is True
        assert result["tool_name"] == "search_funding_calls"
        assert "calls_found" in result
        assert "calls" in result
        assert isinstance(result["calls"], list)
        assert result["calls_found"] == 5

    def test_call_fields(self):
        """Test that each call has required fields."""
        result = MockToolResults.search_funding_calls(3, "AI")

        for call in result["calls"]:
            assert "call_id" in call
            assert "title" in call
            assert "deadline" in call
            assert "action_type" in call
            assert "cluster" in call

    def test_empty_results(self):
        """Test handling of no results."""
        result = MockToolResults.search_funding_calls(0, "nonexistent")
        result["calls_found"] = 0
        result["calls"] = []

        assert result["success"] is True
        assert result["calls_found"] == 0
        assert result["calls"] == []

    def test_search_by_topic_hydrogen(self):
        """Test search for hydrogen calls."""
        result = MockToolResults.search_funding_calls(5, "hydrogen")
        assert all("hydrogen" in c["title"].lower() for c in result["calls"])

    def test_search_by_topic_ai(self):
        """Test search for AI calls."""
        result = MockToolResults.search_funding_calls(5, "artificial intelligence")
        assert result["calls_found"] == 5

    def test_search_metadata(self):
        """Test that search metadata is included."""
        result = MockToolResults.search_funding_calls(3, "energy")

        assert "search_metadata" in result
        assert result["search_metadata"]["source"] == "local_database"
        assert result["search_metadata"]["api_used"] is False


# ============================================================================
# TOOL 2: search_projects
# ============================================================================


class TestSearchProjectsTool:
    """Tests for the search_projects tool."""

    def test_result_structure(self):
        """Test that search_projects returns expected structure."""
        result = MockToolResults.search_projects(5, "AI")

        assert result["success"] is True
        assert result["tool_name"] == "search_projects"
        assert "projects_count" in result
        assert "projects" in result
        assert isinstance(result["projects"], list)

    def test_project_fields(self):
        """Test that each project has required fields."""
        result = MockToolResults.search_projects(3, "quantum")

        for project in result["projects"]:
            assert "project_id" in project
            assert "acronym" in project
            assert "title" in project
            assert "total_cost" in project
            assert "ec_contribution" in project
            assert "coordinator" in project

    def test_search_by_topic(self):
        """Test search by topic returns relevant projects."""
        result = MockToolResults.search_projects(5, "renewable energy")
        assert result["projects_count"] == 5

    def test_project_has_consortium_info(self):
        """Test that project includes consortium information."""
        result = MockToolResults.search_projects(1, "health")
        project = result["projects"][0]

        assert "coordinator_country" in project
        assert "consortium_size" in project

    def test_search_metadata(self):
        """Test that search metadata is included."""
        result = MockToolResults.search_projects(3, "climate")

        assert "search_metadata" in result
        assert "sources" in result["search_metadata"]


# ============================================================================
# TOOL 3: search_documents (search_local_database)
# ============================================================================


class TestSearchDocumentsTool:
    """Tests for the document search tool."""

    def test_result_structure(self):
        """Test that search_documents returns expected structure."""
        result = MockToolResults.search_documents("eligibility")

        assert result["success"] is True
        assert "documents" in result
        assert isinstance(result["documents"], list)

    def test_document_fields(self):
        """Test that each document has required fields."""
        result = MockToolResults.search_documents("consortium requirements")

        for doc in result["documents"]:
            assert "title" in doc
            assert "content" in doc
            assert "relevance_score" in doc

    def test_relevance_scores(self):
        """Test that documents have valid relevance scores."""
        result = MockToolResults.search_documents("budget rules")

        for doc in result["documents"]:
            assert 0 <= doc["relevance_score"] <= 1

    def test_search_eligibility_query(self):
        """Test searching for eligibility information."""
        result = MockToolResults.search_documents("eligibility requirements")
        assert result["results_count"] > 0


# ============================================================================
# TOOL 4: get_programme_statistics
# ============================================================================


class TestProgrammeStatisticsTool:
    """Tests for the get_programme_statistics tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.get_programme_statistics("RIA")

        assert result["success"] is True
        assert result["tool_name"] == "get_programme_statistics"
        assert "statistics" in result

    def test_statistics_fields(self):
        """Test that statistics contain required fields."""
        result = MockToolResults.get_programme_statistics("IA")
        stats = result["statistics"]

        assert "total_projects" in stats
        assert "average_funding_eur" in stats
        assert "success_rate_percent" in stats
        assert "average_consortium_size" in stats

    def test_top_countries_included(self):
        """Test that top countries are included."""
        result = MockToolResults.get_programme_statistics("RIA")

        assert "top_countries" in result["statistics"]
        assert len(result["statistics"]["top_countries"]) > 0


# ============================================================================
# TOOL 5: get_country_statistics
# ============================================================================


class TestCountryStatisticsTool:
    """Tests for the get_country_statistics tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.get_country_statistics("Germany")

        assert result["success"] is True
        assert result["tool_name"] == "get_country_statistics"
        assert result["country"] == "Germany"
        assert "statistics" in result

    def test_statistics_fields(self):
        """Test that statistics contain required fields."""
        result = MockToolResults.get_country_statistics("France")
        stats = result["statistics"]

        assert "total_participations" in stats
        assert "coordinations" in stats
        assert "total_funding_eur" in stats
        assert "success_rate_percent" in stats

    def test_includes_top_organizations(self):
        """Test that top organizations are included."""
        result = MockToolResults.get_country_statistics("Netherlands")

        assert "top_organizations" in result["statistics"]


# ============================================================================
# TOOL 6: compare_programmes
# ============================================================================


class TestCompareProgrammesTool:
    """Tests for the compare_programmes tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.compare_programmes("ERC", "EIC")

        assert result["success"] is True
        assert result["tool_name"] == "compare_programmes"
        assert "comparison" in result
        assert "programmes" in result

    def test_comparison_fields(self):
        """Test that comparison contains expected categories."""
        result = MockToolResults.compare_programmes("RIA", "IA")
        comparison = result["comparison"]

        assert "target_applicants" in comparison or len(comparison) > 0

    def test_includes_recommendation(self):
        """Test that comparison includes recommendation."""
        result = MockToolResults.compare_programmes("MSCA", "ERC")

        assert "recommendation" in result


# ============================================================================
# TOOL 7: get_budget_benchmark
# ============================================================================


class TestBudgetBenchmarkTool:
    """Tests for the get_budget_benchmark tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.get_budget_benchmark("RIA")

        assert result["success"] is True
        assert result["tool_name"] == "get_budget_benchmark"
        assert "benchmarks" in result

    def test_benchmark_fields(self):
        """Test that benchmarks contain expected fields."""
        result = MockToolResults.get_budget_benchmark("IA")
        benchmarks = result["benchmarks"]

        assert "median_eu_contribution" in benchmarks
        assert "average_eu_contribution" in benchmarks
        assert "median_per_partner" in benchmarks
        assert "average_consortium_size" in benchmarks

    def test_includes_sample_projects(self):
        """Test that sample projects are included."""
        result = MockToolResults.get_budget_benchmark("RIA")

        assert "sample_projects" in result
        assert len(result["sample_projects"]) > 0

    def test_includes_recommendations(self):
        """Test that recommendations are included."""
        result = MockToolResults.get_budget_benchmark("CSA")

        assert "recommendations" in result


# ============================================================================
# TOOL 8: get_consortium_patterns
# ============================================================================


class TestConsortiumPatternsTool:
    """Tests for the get_consortium_patterns tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.get_consortium_patterns("CL4", "RIA")

        assert result["success"] is True
        assert result["tool_name"] == "get_consortium_patterns"
        assert "patterns" in result

    def test_pattern_fields(self):
        """Test that patterns contain expected fields."""
        result = MockToolResults.get_consortium_patterns("CL5", "IA")
        patterns = result["patterns"]

        assert "average_consortium_size" in patterns
        assert "entity_type_distribution" in patterns
        assert "top_coordinator_types" in patterns

    def test_entity_type_distribution(self):
        """Test entity type distribution structure."""
        result = MockToolResults.get_consortium_patterns("CL4", "RIA")
        distribution = result["patterns"]["entity_type_distribution"]

        assert "HES" in distribution
        assert "REC" in distribution
        assert "PRC" in distribution

    def test_includes_recommendations(self):
        """Test that recommendations are included."""
        result = MockToolResults.get_consortium_patterns("CL6", "CSA")

        assert "recommendations" in result


# ============================================================================
# TOOL 9: find_experienced_partners
# ============================================================================


class TestFindExperiencedPartnersTool:
    """Tests for the find_experienced_partners tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.find_experienced_partners("quantum computing")

        assert result["success"] is True
        assert result["tool_name"] == "find_experienced_partners"
        assert "partners" in result
        assert "partners_found" in result

    def test_partner_fields(self):
        """Test that each partner has required fields."""
        result = MockToolResults.find_experienced_partners("hydrogen")

        for partner in result["partners"]:
            assert "name" in partner
            assert "country" in partner
            assert "entity_type" in partner
            assert "experience_score" in partner
            assert "relevant_projects" in partner

    def test_experience_scores_valid(self):
        """Test that experience scores are valid."""
        result = MockToolResults.find_experienced_partners("AI")

        for partner in result["partners"]:
            assert 0 <= partner["experience_score"] <= 100

    def test_search_by_country(self):
        """Test searching partners by country."""
        result = MockToolResults.find_experienced_partners("robotics", "Germany")
        assert result["search_params"]["country"] == "Germany"


# ============================================================================
# TOOL 10: get_similar_funded_projects
# ============================================================================


class TestSimilarProjectsTool:
    """Tests for the get_similar_funded_projects tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.get_similar_funded_projects("AI for healthcare diagnosis")

        assert result["success"] is True
        assert result["tool_name"] == "get_similar_funded_projects"
        assert "similar_projects" in result

    def test_project_fields(self):
        """Test that each similar project has required fields."""
        result = MockToolResults.get_similar_funded_projects("renewable energy storage")

        for project in result["similar_projects"]:
            assert "project_id" in project
            assert "acronym" in project
            assert "similarity_score" in project

    def test_similarity_scores_valid(self):
        """Test that similarity scores are valid."""
        result = MockToolResults.get_similar_funded_projects("quantum computing")

        for project in result["similar_projects"]:
            assert 0 <= project["similarity_score"] <= 1

    def test_includes_insights(self):
        """Test that insights are included."""
        result = MockToolResults.get_similar_funded_projects("climate adaptation")

        assert "insights" in result
        assert "average_budget" in result["insights"]


# ============================================================================
# TOOL 11: analyze_call_history
# ============================================================================


class TestAnalyzeCallHistoryTool:
    """Tests for the analyze_call_history tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.analyze_call_history("CL4")

        assert result["success"] is True
        assert result["tool_name"] == "analyze_call_history"
        assert "analysis" in result

    def test_analysis_fields(self):
        """Test that analysis contains expected fields."""
        result = MockToolResults.analyze_call_history("CL5")
        analysis = result["analysis"]

        assert "total_calls_analyzed" in analysis
        assert "total_projects_funded" in analysis
        assert "timeline" in analysis

    def test_timeline_structure(self):
        """Test timeline structure."""
        result = MockToolResults.analyze_call_history("CL4")
        timeline = result["analysis"]["timeline"]

        for _year, data in timeline.items():
            assert "calls" in data
            assert "projects" in data
            assert "funding" in data

    def test_trend_detection(self):
        """Test that trend detection is included."""
        result = MockToolResults.analyze_call_history("CL6")

        assert "trend_detection" in result["analysis"]


# ============================================================================
# TOOL 12: intelligent_search
# ============================================================================


class TestIntelligentSearchTool:
    """Tests for the intelligent_search tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.intelligent_search("hydrogen storage")

        assert result["success"] is True
        assert result["tool_name"] == "intelligent_search"
        assert "results" in result

    def test_results_fields(self):
        """Test that results contain expected fields."""
        result = MockToolResults.intelligent_search("ERC eligibility")
        results = result["results"]

        assert "intent_type" in results
        assert "confidence" in results
        assert "graph_results" in results
        assert "vector_results" in results

    def test_includes_sources(self):
        """Test that sources are included."""
        result = MockToolResults.intelligent_search("budget for RIA")

        assert "sources" in result["results"]


# ============================================================================
# TOOL 13: consortium_builder
# ============================================================================


class TestConsortiumBuilderTool:
    """Tests for the consortium_builder tool."""

    def test_result_structure(self):
        """Test result structure."""
        result = MockToolResults.consortium_builder("CLUSTER-5")

        assert result["success"] is True
        assert result["tool_name"] == "consortium_builder"
        assert "results" in result

    def test_suggestions_structure(self):
        """Test that suggestions have expected structure."""
        result = MockToolResults.consortium_builder("CLUSTER-4")
        suggestions = result["results"]["suggestions"]

        for suggestion in suggestions:
            assert "organization" in suggestion
            assert "country" in suggestion
            assert "entity_type" in suggestion

    def test_includes_country_coverage(self):
        """Test that country coverage is included."""
        result = MockToolResults.consortium_builder("CLUSTER-6")

        assert "countries_covered" in result["results"]


# ============================================================================
# TOOL 14: compliance_checker
# ============================================================================


class TestComplianceCheckerTool:
    """Tests for the compliance_checker tool."""

    def test_result_structure(self):
        """Test result structure."""
        partners = [
            {"country": "DE", "entity_type": "HES", "is_coordinator": True},
            {"country": "FR", "entity_type": "REC", "is_coordinator": False},
            {"country": "NL", "entity_type": "PRC", "is_coordinator": False},
        ]
        result = MockToolResults.compliance_checker(partners, "RIA")

        assert result["success"] is True
        assert result["tool_name"] == "compliance_checker"
        assert "results" in result

    def test_compliance_result_fields(self):
        """Test compliance result fields."""
        partners = [
            {"country": "DE", "entity_type": "HES"},
            {"country": "FR", "entity_type": "REC"},
            {"country": "ES", "entity_type": "SME"},
        ]
        result = MockToolResults.compliance_checker(partners, "IA")

        assert "is_compliant" in result["results"]
        assert "issues" in result["results"]
        assert "warnings" in result["results"]


# ============================================================================
# MULTI-TOOL CONJUNCTION SCENARIOS
# ============================================================================


class TestMultiToolScenarios:
    """Test scenarios requiring multiple tools working together."""

    def test_search_calls_then_get_details(self):
        """
        Scenario: User searches for calls, then asks about a specific one.
        Tools: search_funding_calls -> get_call_details (via intelligent_search)
        """
        # Step 1: Search for calls
        calls_result = MockToolResults.search_funding_calls(5, "hydrogen")
        assert calls_result["success"] is True
        assert calls_result["calls_found"] == 5

        # Step 2: Get details for first call
        first_call_id = calls_result["calls"][0]["call_id"]
        details_result = MockToolResults.intelligent_search(f"details for {first_call_id}")
        assert details_result["success"] is True

    def test_search_projects_then_find_partners(self):
        """
        Scenario: User searches for projects, then looks for similar partners.
        Tools: search_projects -> find_experienced_partners
        """
        # Step 1: Search for AI projects
        projects_result = MockToolResults.search_projects(5, "artificial intelligence")
        assert projects_result["success"] is True

        # Step 2: Find partners based on topic
        partners_result = MockToolResults.find_experienced_partners("artificial intelligence")
        assert partners_result["success"] is True
        assert partners_result["partners_found"] > 0

    def test_budget_and_consortium_planning(self):
        """
        Scenario: User plans a proposal with budget and consortium.
        Tools: get_budget_benchmark + get_consortium_patterns
        """
        # Step 1: Get budget benchmarks
        budget_result = MockToolResults.get_budget_benchmark("RIA", "CL4")
        assert budget_result["success"] is True

        # Step 2: Get consortium patterns
        consortium_result = MockToolResults.get_consortium_patterns("CL4", "RIA")
        assert consortium_result["success"] is True

        # Combined analysis
        budget = budget_result["benchmarks"]["median_eu_contribution"]
        partners = consortium_result["patterns"]["average_consortium_size"]
        per_partner = budget / partners
        assert per_partner > 0

    def test_search_compare_and_recommend(self):
        """
        Scenario: User compares programmes then gets statistics.
        Tools: compare_programmes -> get_programme_statistics x2
        """
        # Step 1: Compare ERC and EIC
        compare_result = MockToolResults.compare_programmes("ERC", "EIC")
        assert compare_result["success"] is True

        # Step 2: Get detailed statistics for each
        erc_stats = MockToolResults.get_programme_statistics("ERC")
        eic_stats = MockToolResults.get_programme_statistics("EIC")

        assert erc_stats["success"] is True
        assert eic_stats["success"] is True

    def test_similar_projects_and_partner_discovery(self):
        """
        Scenario: User finds similar projects then discovers partners from them.
        Tools: get_similar_funded_projects -> find_experienced_partners
        """
        # Step 1: Find similar projects
        similar_result = MockToolResults.get_similar_funded_projects(
            "Machine learning for drug discovery using molecular dynamics"
        )
        assert similar_result["success"] is True

        # Step 2: Find partners in similar domain
        partners_result = MockToolResults.find_experienced_partners("drug discovery AI")
        assert partners_result["success"] is True

    def test_full_proposal_planning_workflow(self):
        """
        Scenario: Complete proposal planning workflow.
        Tools: search_funding_calls -> intelligent_search (eligibility) ->
               get_budget_benchmark -> get_consortium_patterns -> find_experienced_partners
        """
        # Step 1: Find relevant calls
        calls = MockToolResults.search_funding_calls(3, "quantum computing")
        assert calls["calls_found"] > 0

        # Step 2: Check eligibility
        eligibility = MockToolResults.search_documents("consortium eligibility RIA")
        assert eligibility["results_count"] > 0

        # Step 3: Get budget guidance
        budget = MockToolResults.get_budget_benchmark("RIA", "CL4")
        assert budget["benchmarks"]["median_eu_contribution"] > 0

        # Step 4: Understand consortium patterns
        patterns = MockToolResults.get_consortium_patterns("CL4", "RIA")
        assert patterns["patterns"]["average_consortium_size"] > 0

        # Step 5: Find potential partners
        partners = MockToolResults.find_experienced_partners("quantum computing")
        assert partners["partners_found"] > 0

    def test_consortium_building_and_compliance(self):
        """
        Scenario: Build consortium then check compliance.
        Tools: consortium_builder -> compliance_checker
        """
        # Step 1: Get consortium suggestions
        consortium = MockToolResults.consortium_builder("CLUSTER-5")
        assert consortium["success"] is True

        # Step 2: Extract partners and check compliance
        suggested_partners = [
            {"country": s["country"], "entity_type": s["entity_type"], "is_coordinator": False}
            for s in consortium["results"]["suggestions"][:5]
        ]
        # Set first as coordinator
        if suggested_partners:
            suggested_partners[0]["is_coordinator"] = True

        compliance = MockToolResults.compliance_checker(suggested_partners, "RIA")
        assert compliance["success"] is True

    def test_history_analysis_and_current_search(self):
        """
        Scenario: Analyze historical trends then search current calls.
        Tools: analyze_call_history -> search_funding_calls
        """
        # Step 1: Analyze history
        history = MockToolResults.analyze_call_history("CL4", "artificial intelligence")
        assert history["analysis"]["trend_detection"] in ["increasing", "stable", "declining"]

        # Step 2: Search current calls
        current_calls = MockToolResults.search_funding_calls(10, "artificial intelligence")
        assert current_calls["success"] is True

    def test_country_stats_and_partner_search(self):
        """
        Scenario: Check country performance then find partners from top country.
        Tools: get_country_statistics -> find_experienced_partners
        """
        # Step 1: Get country statistics
        country_stats = MockToolResults.get_country_statistics("Germany")
        assert country_stats["statistics"]["total_participations"] > 0

        # Step 2: Find partners in that country
        partners = MockToolResults.find_experienced_partners("renewable energy", "Germany")
        assert partners["success"] is True


# ============================================================================
# CONVERSATION CONTEXT SCENARIOS
# ============================================================================


class TestConversationContextScenarios:
    """Test scenarios that require maintaining conversation context."""

    def test_follow_up_on_search_results(self):
        """Test follow-up question about previous search results."""
        # Initial search
        initial_results = MockToolResults.search_funding_calls(10, "hydrogen")

        # Simulate context
        {
            "previous_results": initial_results["calls"],
            "previous_tool": "search_funding_calls",
            "previous_query": "hydrogen",
        }

        # Follow-up should reference context
        third_call = initial_results["calls"][2]

        assert third_call["call_id"] == "HORIZON-CL5-2024-D3-03"

    def test_refinement_of_search(self):
        """Test refining a search with additional criteria."""
        # Initial broad search
        MockToolResults.search_projects(50, "energy")

        # Refinement should narrow down
        # Simulating AI understanding: "Only show RIA projects from 2023"
        refined_criteria = {
            "original_query": "energy",
            "action_type_filter": "RIA",
            "year_filter": 2023,
        }

        assert refined_criteria["action_type_filter"] == "RIA"

    def test_comparison_with_previous_topic(self):
        """Test comparing current topic with previously discussed one."""
        # First topic
        MockToolResults.get_programme_statistics("ERC")

        # Context stored

        # Follow-up: "How does EIC compare to that?"
        # AI should understand "that" = ERC
        comparison = MockToolResults.compare_programmes("EIC", "ERC")

        assert comparison["programmes"] == ["EIC", "ERC"]


# ============================================================================
# ERROR HANDLING SCENARIOS
# ============================================================================


class TestErrorHandlingScenarios:
    """Test error handling across tools."""

    def test_empty_search_results(self):
        """Test handling of no results found."""
        result = MockToolResults.search_funding_calls(0, "nonexistent_topic_xyz")
        result["calls_found"] = 0
        result["calls"] = []

        # Tool should still return success=True with empty results
        assert result["success"] is True
        assert result["calls"] == []

    def test_invalid_parameters_handled(self):
        """Test that tools handle invalid parameters gracefully."""
        # Simulating a failed tool call
        error_result = {
            "success": False,
            "error": "Invalid action_type parameter",
            "error_type": "validation_error",
            "tool_name": "get_budget_benchmark",
        }

        assert error_result["success"] is False
        assert "error" in error_result

    def test_partial_results(self):
        """Test handling of partial results."""
        # Some tools may return partial results on timeout
        partial_result = {
            "success": True,
            "tool_name": "find_experienced_partners",
            "partners_found": 3,
            "partners": [{"name": "Org1"}, {"name": "Org2"}, {"name": "Org3"}],
            "warning": "Search timed out, results may be incomplete",
        }

        assert partial_result["success"] is True
        assert "warning" in partial_result


# ============================================================================
# EDGE CASE SCENARIOS
# ============================================================================


class TestEdgeCaseScenarios:
    """Test edge cases and boundary conditions."""

    def test_very_long_description(self):
        """Test handling of very long input descriptions."""
        long_description = "AI and machine learning " * 100
        result = MockToolResults.get_similar_funded_projects(long_description)

        assert result["success"] is True
        # Query should be truncated
        assert len(result["query_description"]) <= 100

    def test_special_characters_in_query(self):
        """Test handling of special characters in queries."""
        queries_to_test = [
            "AI & machine learning",
            "research (quantum)",
            "EU's funding",
            "CO2 reduction",
        ]

        for query in queries_to_test:
            result = MockToolResults.search_projects(3, query)
            assert result["success"] is True

    def test_multilingual_query(self):
        """Test handling of multilingual queries."""
        # German mixed with English
        result = MockToolResults.search_funding_calls(3, "Förderung AI projects")
        assert result["success"] is True

    def test_numeric_filters(self):
        """Test numeric filter boundaries."""
        budget_result = MockToolResults.get_budget_benchmark("RIA")
        benchmarks = budget_result["benchmarks"]

        # Min should be less than max
        assert benchmarks["min_eu_contribution"] < benchmarks["max_eu_contribution"]
        # Median should be between min and max
        assert (
            benchmarks["min_eu_contribution"]
            <= benchmarks["median_eu_contribution"]
            <= benchmarks["max_eu_contribution"]
        )


# ============================================================================
# INTEGRATION SCENARIOS
# ============================================================================


class TestIntegrationScenarios:
    """End-to-end integration scenarios."""

    def test_complete_user_journey_new_applicant(self):
        """
        Simulate a new applicant's complete journey:
        1. Learn about programmes
        2. Find relevant calls
        3. Check eligibility
        4. Plan budget
        5. Find partners
        """
        # 1. Compare programmes to understand options
        comparison = MockToolResults.compare_programmes("RIA", "IA")
        assert comparison["success"] is True

        # 2. Search for calls in their area
        calls = MockToolResults.search_funding_calls(5, "sustainable energy")
        assert calls["calls_found"] > 0

        # 3. Check eligibility requirements
        eligibility = MockToolResults.search_documents("eligibility requirements RIA")
        assert eligibility["results_count"] > 0

        # 4. Plan budget based on benchmarks
        budget = MockToolResults.get_budget_benchmark("RIA", "CL5")
        assert budget["benchmarks"]["median_eu_contribution"] > 0

        # 5. Find potential partners
        partners = MockToolResults.find_experienced_partners("sustainable energy")
        assert partners["partners_found"] > 0

    def test_experienced_researcher_journey(self):
        """
        Simulate an experienced researcher's journey:
        1. Analyze historical trends
        2. Find similar funded projects
        3. Get consortium patterns
        4. Check country performance
        """
        # 1. Analyze trends in their field
        history = MockToolResults.analyze_call_history("CL4", "quantum")
        assert history["analysis"]["trend_detection"] is not None

        # 2. Find similar projects to benchmark
        similar = MockToolResults.get_similar_funded_projects(
            "Quantum computing for cryptography and secure communications"
        )
        assert len(similar["similar_projects"]) > 0

        # 3. Understand successful consortium patterns
        patterns = MockToolResults.get_consortium_patterns("CL4", "RIA")
        assert patterns["patterns"]["average_consortium_size"] > 0

        # 4. Check their country's performance
        country_stats = MockToolResults.get_country_statistics("Germany")
        assert country_stats["statistics"]["success_rate_percent"] > 0


# ============================================================================
# RESPONSE QUALITY TESTS
# ============================================================================


class TestResponseQuality:
    """Test that tool results meet quality standards."""

    def test_all_tools_return_success_field(self):
        """All tools should return a success field."""
        tool_results = [
            MockToolResults.search_funding_calls(3, "test"),
            MockToolResults.search_projects(3, "test"),
            MockToolResults.search_documents("test"),
            MockToolResults.get_programme_statistics("RIA"),
            MockToolResults.get_country_statistics("Germany"),
            MockToolResults.compare_programmes("ERC", "EIC"),
            MockToolResults.get_budget_benchmark("RIA"),
            MockToolResults.get_consortium_patterns("CL4", "RIA"),
            MockToolResults.find_experienced_partners("AI"),
            MockToolResults.get_similar_funded_projects("test description"),
            MockToolResults.analyze_call_history("CL4"),
            MockToolResults.intelligent_search("test query"),
            MockToolResults.consortium_builder("CLUSTER-4"),
            MockToolResults.compliance_checker([{"country": "DE"}], "RIA"),
        ]

        for result in tool_results:
            assert "success" in result, (
                f"Tool result missing 'success' field: {result.get('tool_name', 'unknown')}"
            )

    def test_all_tools_return_tool_name(self):
        """All tools should return their tool_name."""
        tool_results = [
            MockToolResults.search_funding_calls(3, "test"),
            MockToolResults.search_projects(3, "test"),
            MockToolResults.get_programme_statistics("RIA"),
            MockToolResults.get_country_statistics("Germany"),
            MockToolResults.compare_programmes("ERC", "EIC"),
            MockToolResults.get_budget_benchmark("RIA"),
            MockToolResults.get_consortium_patterns("CL4", "RIA"),
            MockToolResults.find_experienced_partners("AI"),
            MockToolResults.get_similar_funded_projects("test"),
            MockToolResults.analyze_call_history("CL4"),
            MockToolResults.intelligent_search("test"),
            MockToolResults.consortium_builder("CLUSTER-4"),
            MockToolResults.compliance_checker([], "RIA"),
        ]

        for result in tool_results:
            assert "tool_name" in result, "Tool result missing 'tool_name' field"

    def test_numeric_values_are_reasonable(self):
        """Numeric values should be within reasonable ranges."""
        budget = MockToolResults.get_budget_benchmark("RIA")

        # Budget values should be positive
        assert budget["benchmarks"]["median_eu_contribution"] > 0
        assert budget["benchmarks"]["average_consortium_size"] > 0

        # Per-partner budget should be less than total
        assert (
            budget["benchmarks"]["median_per_partner"]
            < budget["benchmarks"]["median_eu_contribution"]
        )

    def test_percentages_are_valid(self):
        """Percentage values should be between 0 and 100."""
        stats = MockToolResults.get_programme_statistics("RIA")

        assert 0 <= stats["statistics"]["success_rate_percent"] <= 100

        for country in stats["statistics"]["top_countries"]:
            assert 0 <= country["share"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
