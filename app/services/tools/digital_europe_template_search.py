"""
Digital Europe Template and Guidance Search Tool

Searches Digital Europe documents (Work Programmes, Regulation, Implementing Decisions)
for application guidance, eligibility criteria, and programme-specific information.

Uses the ingested Digital Europe documents to provide targeted answers
about objectives, requirements, and funding opportunities.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Key sections in Digital Europe documents
DIGITAL_EUROPE_SECTIONS = {
    "hpc": {
        "keywords": [
            "hpc",
            "supercomputing",
            "high performance computing",
            "eurohpc",
            "exascale",
            "petascale",
            "data infrastructure",
        ],
        "description": "High Performance Computing infrastructure and services",
    },
    "ai": {
        "keywords": [
            "artificial intelligence",
            " ai ",
            "machine learning",
            "ai factory",
            "testing facility",
            "tef",
            "data space",
            "ai act",
        ],
        "description": "Artificial Intelligence development and deployment",
    },
    "cybersecurity": {
        "keywords": [
            "cybersecurity",
            "cyber",
            "soc",
            "security operation",
            "eccc",
            "national coordination",
            "resilience",
            "threat",
        ],
        "description": "Cybersecurity infrastructure and ECCC initiatives",
    },
    "skills": {
        "keywords": [
            "digital skills",
            "training",
            "education",
            "specialised programme",
            "workforce",
            "competence",
            "certification",
            "academy",
        ],
        "description": "Advanced Digital Skills programmes",
    },
    "deployment": {
        "keywords": [
            "deployment",
            "edih",
            "digital innovation hub",
            "best use",
            "interoperability",
            "digital transformation",
            "multicountry",
        ],
        "description": "Deployment and EDIHs",
    },
    "semiconductors": {
        "keywords": [
            "semiconductor",
            "chips",
            "microelectronics",
            "pilot line",
            "design",
            "chips act",
        ],
        "description": "Semiconductors and Chips Act initiatives",
    },
    "eligibility": {
        "keywords": [
            "eligibility",
            "eligible",
            "who can apply",
            "applicant",
            "participating countries",
            "legal entity",
            "consortium",
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
            "lump sum",
        ],
        "description": "Budget rules, grant amounts, and funding rates",
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
    "governance": {
        "keywords": [
            "governance",
            "management",
            "hadea",
            "commission",
            "eccc",
            "eurohpc ju",
            "implementing",
        ],
        "description": "Programme governance and management",
    },
    "synergies": {
        "keywords": [
            "synergy",
            "synergies",
            "horizon",
            "cef",
            "connecting europe",
            "structural fund",
            "complementarity",
        ],
        "description": "Synergies with other EU programmes",
    },
    "deadlines": {
        "keywords": ["deadline", "submission", "call", "calendar", "date", "cutoff"],
        "description": "Application deadlines and call calendar",
    },
}


class DigitalEuropeTemplateSearchTool:
    """Tool for searching Digital Europe guidance and templates."""

    def __init__(self):
        self.sections = DIGITAL_EUROPE_SECTIONS

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

    def detect_objective(self, query: str) -> str | None:
        """Detect which objective the query is about."""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["hpc", "supercomputing", "eurohpc", "exascale"]):
            return "HPC"
        elif any(
            kw in query_lower
            for kw in ["artificial intelligence", " ai ", "machine learning", "ai factory"]
        ):
            return "AI"
        elif any(kw in query_lower for kw in ["cybersecurity", "cyber", "soc", "eccc"]):
            return "CYBERSECURITY"
        elif any(
            kw in query_lower for kw in ["digital skills", "training", "education", "academy"]
        ):
            return "SKILLS"
        elif any(
            kw in query_lower for kw in ["deployment", "edih", "digital innovation hub", "best use"]
        ):
            return "DEPLOYMENT"
        elif any(kw in query_lower for kw in ["semiconductor", "chips", "microelectronics"]):
            return "SEMICONDUCTORS"

        return None

    def build_enhanced_query(
        self,
        query: str,
        objective: str | None = None,
        section: str | None = None,
    ) -> str:
        """Build an enhanced query with context keywords."""
        enhanced = query

        if objective:
            objective_keywords = {
                "HPC": "high performance computing supercomputing EuroHPC exascale data infrastructure",
                "AI": "artificial intelligence AI machine learning testing experimentation facility data space",
                "CYBERSECURITY": "cybersecurity ECCC security operation centre SOC national coordination",
                "SKILLS": "advanced digital skills training education specialised programme workforce",
                "DEPLOYMENT": "deployment EDIH European digital innovation hub best use interoperability",
                "SEMICONDUCTORS": "semiconductor chips microelectronics pilot line design competence",
            }
            if objective.upper() in objective_keywords:
                enhanced = f"{objective_keywords[objective.upper()]} {enhanced}"

        if section:
            section_keywords = {
                "eligibility": "eligibility criteria requirements legal entity participating country",
                "budget": "budget funding rate co-financing grant contribution",
                "evaluation": "evaluation criteria selection award quality assessment",
                "governance": "governance management implementing agency HaDEA ECCC",
            }
            if section.lower() in section_keywords:
                enhanced = f"{section_keywords[section.lower()]} {enhanced}"

        return enhanced


async def search_digital_europe_templates_execute(
    query: str,
    objective: str | None = None,
    section: str | None = None,
    topic: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search Digital Europe guidance documents for application information.

    Args:
        query: What to search for (e.g., "AI funding eligibility")
        objective: Filter by objective (HPC, AI, CYBERSECURITY, SKILLS, DEPLOYMENT, SEMICONDUCTORS)
        section: Filter by section type (eligibility, budget, evaluation, etc.)
        topic: Specific topic to focus on
        top_k: Number of results

    Returns:
        Matching excerpts from Digital Europe documents with metadata
    """
    try:
        from app.services.vector_search_service import VectorSearchService

        tool = DigitalEuropeTemplateSearchTool()
        service = VectorSearchService()

        # Build enhanced query
        enhanced_query = tool.build_enhanced_query(query, objective, section)

        # Detect relevant sections and objective
        sections = tool.detect_section(query)
        detected_objective = objective or tool.detect_objective(query)

        # Search with programme filter for Digital Europe
        results = service.search(
            query=enhanced_query,
            num_results=top_k * 2,  # Get more to filter
            filters={"programme": "digital_europe"},
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
            for section_id, config in DIGITAL_EUROPE_SECTIONS.items():
                for kw in config["keywords"]:
                    if kw in content_lower:
                        matched_section = section_id
                        break

            # Determine objective from content
            content_objective = "general"
            if any(kw in content_lower for kw in ["hpc", "supercomputing", "eurohpc"]):
                content_objective = "HPC"
            elif any(
                kw in content_lower
                for kw in ["artificial intelligence", " ai ", "machine learning"]
            ):
                content_objective = "AI"
            elif any(kw in content_lower for kw in ["cybersecurity", "eccc", "soc"]):
                content_objective = "CYBERSECURITY"
            elif any(kw in content_lower for kw in ["digital skills", "training", "education"]):
                content_objective = "SKILLS"
            elif any(kw in content_lower for kw in ["deployment", "edih", "innovation hub"]):
                content_objective = "DEPLOYMENT"
            elif any(kw in content_lower for kw in ["semiconductor", "chips", "microelectronics"]):
                content_objective = "SEMICONDUCTORS"

            formatted_results.append(
                {
                    "content": result.content[:1000],  # Limit content length
                    "document_title": getattr(result, "document_title", "Digital Europe Document"),
                    "section": matched_section,
                    "section_description": DIGITAL_EUROPE_SECTIONS.get(matched_section, {}).get(
                        "description", ""
                    ),
                    "objective": content_objective,
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
            "detected_objective": detected_objective,
            "filters": {
                "objective": objective,
                "section": section,
                "topic": topic,
            },
            "metadata": {
                "tool": "search_digital_europe_templates",
                "programme": "digital_europe",
                "implementing_agency": "DG CONNECT / HaDEA",
                "programme_budget": "€7.588 billion (2021-2027)",
                "note": "Results from Digital Europe Programme documents (2021-2027)",
            },
        }

    except Exception as e:
        logger.error(f"Digital Europe template search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }
