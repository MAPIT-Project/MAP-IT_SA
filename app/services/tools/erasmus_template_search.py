"""
Erasmus+ Template and Guidance Search Tool

Searches Erasmus+ Programme Guide and related documents for application
guidance, quality criteria, budget rules, and sector-specific information.

Uses the existing ingested Erasmus+ documents (Programme Guide 2026, AWP 2026)
to provide targeted answers about application requirements.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Key sections in Erasmus+ Programme Guide
ERASMUS_SECTIONS = {
    "eligibility": {
        "keywords": [
            "eligibility",
            "eligible",
            "who can apply",
            "participating countries",
            "programme countries",
        ],
        "description": "Eligibility criteria for organizations and participants",
    },
    "budget": {
        "keywords": [
            "budget",
            "funding",
            "grant",
            "lump sum",
            "unit cost",
            "financial",
            "contribution",
        ],
        "description": "Budget rules, lump sums, and funding rates",
    },
    "quality_criteria": {
        "keywords": [
            "quality",
            "criteria",
            "evaluation",
            "assessment",
            "award",
            "scoring",
            "points",
        ],
        "description": "Quality assessment criteria and evaluation process",
    },
    "ka1_mobility": {
        "keywords": [
            "mobility",
            "ka1",
            "learning mobility",
            "exchange",
            "staff mobility",
            "student mobility",
        ],
        "description": "KA1 Learning Mobility of Individuals",
    },
    "ka2_partnership": {
        "keywords": ["partnership", "ka2", "cooperation", "consortium", "project management"],
        "description": "KA2 Cooperation Partnerships",
    },
    "ka2_small_scale": {
        "keywords": ["small-scale", "small scale", "ssp", "simplified"],
        "description": "KA2 Small-Scale Partnerships",
    },
    "ka2_capacity_building": {
        "keywords": ["capacity building", "cbhe", "capacity-building", "third countries"],
        "description": "Capacity Building in Higher Education",
    },
    "jean_monnet": {
        "keywords": ["jean monnet", "eu studies", "european studies", "jmo"],
        "description": "Jean Monnet Actions",
    },
    "sport": {
        "keywords": ["sport", "physical activity", "grassroots", "athletic"],
        "description": "Sport Actions",
    },
    "eche": {
        "keywords": ["eche", "erasmus charter", "charter for higher education"],
        "description": "Erasmus Charter for Higher Education requirements",
    },
    "deadlines": {
        "keywords": ["deadline", "submission", "due date", "call", "round"],
        "description": "Application deadlines and submission rounds",
    },
    "reporting": {
        "keywords": ["report", "final report", "interim", "progress", "monitoring"],
        "description": "Reporting requirements and templates",
    },
}


class ErasmusTemplateSearchTool:
    """Tool for searching Erasmus+ guidance and templates."""

    def __init__(self):
        self.sections = ERASMUS_SECTIONS

    def detect_section(self, query: str) -> list[str]:
        """Detect which sections a query is likely about."""
        query_lower = query.lower()
        matching_sections = []

        for section_id, config in self.sections.items():
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    matching_sections.append(section_id)
                    break

        return matching_sections or ["general"]

    def build_enhanced_query(
        self, query: str, key_action: str | None = None, sector: str | None = None
    ) -> str:
        """Build an enhanced query with context keywords."""
        enhanced = query

        if key_action:
            ka_keywords = {
                "KA1": "learning mobility key action 1",
                "KA2": "cooperation partnerships key action 2",
                "KA3": "policy support key action 3",
                "JMO": "jean monnet EU studies",
                "SPORT": "sport cooperation grassroots",
            }
            if key_action.upper() in ka_keywords:
                enhanced = f"{ka_keywords[key_action.upper()]} {enhanced}"

        if sector:
            sector_keywords = {
                "HED": "higher education university",
                "VET": "vocational education training",
                "SCH": "school education primary secondary",
                "ADU": "adult education lifelong learning",
                "YOU": "youth young people",
                "SPORT": "sport physical activity",
            }
            if sector.upper() in sector_keywords:
                enhanced = f"{sector_keywords[sector.upper()]} {enhanced}"

        return enhanced


async def search_erasmus_templates_execute(
    query: str,
    key_action: str | None = None,
    sector: str | None = None,
    document_type: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search Erasmus+ guidance documents for application information.

    Args:
        query: What to search for (e.g., "KA2 eligibility requirements")
        key_action: Filter by KA1, KA2, KA3, JMO, SPORT
        sector: Filter by HED, VET, SCH, ADU, YOU, SPORT
        document_type: Filter type (eligibility, budget, quality_criteria, etc.)
        top_k: Number of results

    Returns:
        Matching excerpts from Erasmus+ Programme Guide with metadata
    """
    try:
        from app.services.vector_search_service import VectorSearchService

        tool = ErasmusTemplateSearchTool()
        service = VectorSearchService()

        # Build enhanced query
        enhanced_query = tool.build_enhanced_query(query, key_action, sector)

        # Detect relevant sections
        sections = tool.detect_section(query)

        # Search with programme filter
        results = service.search(
            query=enhanced_query,
            num_results=top_k * 2,  # Get more to filter
            filters={"programme": "erasmus"},
        )

        # Format results
        formatted_results = []
        seen_content = set()

        for result in results:
            # Skip duplicates
            content_key = result.content[:100]
            if content_key in seen_content:
                continue
            seen_content.add(content_key)

            # Determine section
            content_lower = result.content.lower()
            matched_section = "general"
            for section_id, config in ERASMUS_SECTIONS.items():
                for kw in config["keywords"]:
                    if kw in content_lower:
                        matched_section = section_id
                        break

            formatted_results.append(
                {
                    "content": result.content[:1000],  # Limit content length
                    "document_title": getattr(result, "document_title", "Erasmus+ Programme Guide"),
                    "section": matched_section,
                    "section_description": ERASMUS_SECTIONS.get(matched_section, {}).get(
                        "description", ""
                    ),
                    "relevance_score": getattr(result, "score", 0.0),
                }
            )

            if len(formatted_results) >= top_k:
                break

        return {
            "success": True,
            "results": formatted_results,
            "total_found": len(formatted_results),
            "query": query,
            "enhanced_query": enhanced_query,
            "detected_sections": sections,
            "filters": {
                "key_action": key_action,
                "sector": sector,
                "document_type": document_type,
            },
            "metadata": {
                "tool": "search_erasmus_templates",
                "programme": "erasmus_plus",
                "note": "Results from Erasmus+ Programme Guide 2026",
            },
        }

    except Exception as e:
        logger.error(f"Erasmus template search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }
