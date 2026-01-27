"""
LIFE Programme Template and Guidance Search Tool

Searches LIFE Programme documents (Work Programmes, Priority Topics, Regulation)
for application guidance, eligibility criteria, and programme-specific information.

Uses the ingested LIFE documents to provide targeted answers
about sub-programmes, requirements, and funding opportunities.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Key sections in LIFE documents
LIFE_SECTIONS = {
    "nature": {
        "keywords": [
            "nature",
            "biodiversity",
            "natura 2000",
            "habitat",
            "species",
            "protected area",
            "conservation",
            "wildlife",
        ],
        "description": "Nature and Biodiversity sub-programme",
    },
    "circular_economy": {
        "keywords": [
            "circular economy",
            "waste",
            "recycling",
            "resource efficiency",
            "plastic",
            "material",
            "reuse",
        ],
        "description": "Circular Economy and resource management",
    },
    "water": {
        "keywords": [
            "water",
            "river",
            "marine",
            "freshwater",
            "groundwater",
            "flood",
            "drought",
            "water framework",
        ],
        "description": "Water management and quality",
    },
    "air": {
        "keywords": ["air", "air quality", "emissions", "pollution", "particulate"],
        "description": "Air quality improvement",
    },
    "soil": {
        "keywords": ["soil", "land", "contamination", "erosion", "land use"],
        "description": "Soil protection and remediation",
    },
    "climate_mitigation": {
        "keywords": [
            "mitigation",
            "greenhouse gas",
            "ghg",
            "carbon",
            "emission reduction",
            "low carbon",
            "decarbonisation",
        ],
        "description": "Climate change mitigation",
    },
    "climate_adaptation": {
        "keywords": [
            "adaptation",
            "resilience",
            "climate risk",
            "vulnerability",
            "extreme weather",
            "climate-proof",
        ],
        "description": "Climate change adaptation",
    },
    "clean_energy": {
        "keywords": [
            "clean energy",
            "renewable",
            "energy efficiency",
            "energy poverty",
            "building renovation",
            "energy community",
        ],
        "description": "Clean Energy Transition",
    },
    "eligibility": {
        "keywords": [
            "eligibility",
            "eligible",
            "who can apply",
            "applicant",
            "participating countries",
            "legal entity",
        ],
        "description": "Eligibility criteria for organizations",
    },
    "budget": {
        "keywords": [
            "budget",
            "funding",
            "grant",
            "co-financing",
            "financial",
            "contribution",
            "rate",
        ],
        "description": "Budget rules and funding rates",
    },
    "evaluation": {
        "keywords": [
            "evaluation",
            "criteria",
            "assessment",
            "award",
            "scoring",
            "quality",
            "selection",
            "excellence",
        ],
        "description": "Evaluation and selection criteria",
    },
    "project_types": {
        "keywords": [
            "standard action",
            "sap",
            "strategic integrated",
            "sip",
            "snap",
            "technical assistance",
            "operating grant",
        ],
        "description": "Project types (SAP, SIP, SNAP, TA, OG)",
    },
    "deadlines": {
        "keywords": ["deadline", "submission", "call", "calendar", "date", "timeline"],
        "description": "Application deadlines and call calendar",
    },
}


class LIFETemplateSearchTool:
    """Tool for searching LIFE Programme guidance and templates."""

    def __init__(self):
        self.sections = LIFE_SECTIONS

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

    def detect_subprogramme(self, query: str) -> str | None:
        """Detect which sub-programme the query is about."""
        query_lower = query.lower()

        if any(
            kw in query_lower for kw in ["nature", "biodiversity", "natura", "habitat", "species"]
        ):
            return "NAT"
        elif any(
            kw in query_lower for kw in ["circular", "waste", "water", "air", "soil", "resource"]
        ):
            return "ENV"
        elif any(kw in query_lower for kw in ["climate", "mitigation", "adaptation", "greenhouse"]):
            return "CCA"
        elif any(
            kw in query_lower
            for kw in ["clean energy", "energy transition", "renewable", "energy efficiency"]
        ):
            return "CET"

        return None

    def build_enhanced_query(
        self,
        query: str,
        subprogramme: str | None = None,
        section: str | None = None,
    ) -> str:
        """Build an enhanced query with context keywords."""
        enhanced = query

        if subprogramme:
            subprog_keywords = {
                "NAT": "nature biodiversity Natura 2000 habitat species conservation wildlife",
                "ENV": "circular economy waste water air soil resource efficiency environment",
                "CCA": "climate change mitigation adaptation greenhouse gas resilience",
                "CET": "clean energy transition renewable energy efficiency building renovation",
            }
            if subprogramme.upper() in subprog_keywords:
                enhanced = f"{subprog_keywords[subprogramme.upper()]} {enhanced}"

        if section:
            section_keywords = {
                "eligibility": "eligibility criteria requirements legal entity participating country",
                "budget": "budget funding rate co-financing grant contribution",
                "evaluation": "evaluation criteria selection award quality assessment",
                "project_types": "standard action SAP strategic integrated SIP SNAP technical assistance",
            }
            if section.lower() in section_keywords:
                enhanced = f"{section_keywords[section.lower()]} {enhanced}"

        return enhanced


async def search_life_templates_execute(
    query: str,
    subprogramme: str | None = None,
    section: str | None = None,
    topic: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search LIFE Programme guidance documents for application information.

    Args:
        query: What to search for (e.g., "biodiversity funding eligibility")
        subprogramme: Filter by sub-programme (NAT, ENV, CCA, CET)
        section: Filter by section type (eligibility, budget, evaluation, etc.)
        topic: Specific topic to focus on
        top_k: Number of results

    Returns:
        Matching excerpts from LIFE documents with metadata
    """
    try:
        from app.services.vector_search_service import VectorSearchService

        tool = LIFETemplateSearchTool()
        service = VectorSearchService()

        # Build enhanced query
        enhanced_query = tool.build_enhanced_query(query, subprogramme, section)

        # Detect relevant sections and sub-programme
        sections = tool.detect_section(query)
        detected_subprog = subprogramme or tool.detect_subprogramme(query)

        # Search with programme filter for LIFE
        results = service.search(
            query=enhanced_query,
            num_results=top_k * 2,  # Get more to filter
            filters={"programme": "life"},
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

            # Determine section from content
            content_lower = result.content.lower()
            matched_section = "general"
            for section_id, config in LIFE_SECTIONS.items():
                for kw in config["keywords"]:
                    if kw in content_lower:
                        matched_section = section_id
                        break

            # Determine sub-programme from content
            content_subprog = "general"
            if any(
                kw in content_lower for kw in ["nature", "biodiversity", "natura 2000", "habitat"]
            ):
                content_subprog = "NAT"
            elif any(
                kw in content_lower
                for kw in ["circular", "waste", "water quality", "air quality", "soil"]
            ):
                content_subprog = "ENV"
            elif any(
                kw in content_lower
                for kw in ["climate mitigation", "climate adaptation", "greenhouse"]
            ):
                content_subprog = "CCA"
            elif any(
                kw in content_lower for kw in ["clean energy", "energy transition", "renewable"]
            ):
                content_subprog = "CET"

            formatted_results.append(
                {
                    "content": result.content[:1000],  # Limit content length
                    "document_title": getattr(result, "document_title", "LIFE Document"),
                    "section": matched_section,
                    "section_description": LIFE_SECTIONS.get(matched_section, {}).get(
                        "description", ""
                    ),
                    "subprogramme": content_subprog,
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
            "detected_subprogramme": detected_subprog,
            "filters": {
                "subprogramme": subprogramme,
                "section": section,
                "topic": topic,
            },
            "metadata": {
                "tool": "search_life_templates",
                "programme": "life",
                "implementing_agency": "CINEA",
                "programme_budget": "€5.432 billion (2021-2027)",
                "note": "Results from LIFE Programme documents (2021-2027)",
            },
        }

    except Exception as e:
        logger.error(f"LIFE template search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }
