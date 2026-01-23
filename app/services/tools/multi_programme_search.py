"""
Multi-Programme Search Tool

Unified search across all EU funding programmes (Horizon Europe, Erasmus+,
Creative Europe, EU4Health, Digital Europe, LIFE).

This is the key differentiator for MAPIT AI - finding the right funding
across ALL EU programmes in one search.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


# Programme metadata for rich results
PROGRAMME_INFO = {
    "horizon_europe": {
        "name": "Horizon Europe",
        "short_name": "HE",
        "budget": "€95.5B",
        "focus": "Research & Innovation",
        "icon": "🔬",
        "website": "https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe_en",
        "resources": {
            "main_portal": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "work_programmes": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON",
            "how_to_participate": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1",
            "partner_search": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search",
            "call_calendar": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar",
            "cordis": "https://cordis.europa.eu/",
            "regulation": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32021R0695",
        },
        # noqa: E501 - Long URLs in user-facing guidance text
        "guidance": (
            "🎯 **Getting Started with Horizon Europe:**\n"
            "• Register on [EU Funding & Tenders Portal]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)\n"
            "• Review the [Work Programmes]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
            "screen/how-to-participate/reference-documents;programCode=HORIZON) for your cluster\n"
            "• Check eligibility via [How to Participate]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
            "screen/how-to-participate/how-to-participate/1)\n"
            "• Find partners using [Partner Search]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
            "screen/how-to-participate/partner-search)\n"
            "• Browse [Call Calendar]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
            "screen/opportunities/calls-calendar)"
        ),
    },
    "erasmus_plus": {
        "name": "Erasmus+",
        "short_name": "E+",
        "budget": "€26.2B",
        "focus": "Education, Training, Youth, Sport",
        "icon": "🎓",
        "website": "https://erasmus-plus.ec.europa.eu/",
        "resources": {
            "main_portal": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "programme_guide": "https://erasmus-plus.ec.europa.eu/programme-guide/introduction",
            "how_to_apply": "https://erasmus-plus.ec.europa.eu/how-to-apply",
        },
        "guidance": """🎯 **Getting Started with Erasmus+:**
• Review the [Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/introduction)
• Check [How to Apply](https://erasmus-plus.ec.europa.eu/how-to-apply)
• Find open calls on [EU Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)""",
    },
    "creative_europe": {
        "name": "Creative Europe",
        "short_name": "CE",
        "budget": "€2.44B",
        "focus": "Culture & Media",
        "icon": "🎨",
        "website": "https://creative-europe.ec.europa.eu/",
        "resources": {
            "main_portal": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "culture_strand": "https://creative-europe.ec.europa.eu/culture",
            "media_strand": "https://creative-europe.ec.europa.eu/media",
        },
        "guidance": """🎯 **Getting Started with Creative Europe:**
• Explore [Culture Strand](https://creative-europe.ec.europa.eu/culture)
• Explore [MEDIA Strand](https://creative-europe.ec.europa.eu/media)
• Find open calls on [EU Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)""",
    },
    "eu4health": {
        "name": "EU4Health",
        "short_name": "E4H",
        "budget": "€5.3B",
        "focus": "Health & Crisis Preparedness",
        "icon": "🏥",
        "website": "https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en",
        "resources": {
            "main_portal": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "programme_info": "https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en",
        },
        "guidance": """🎯 **Getting Started with EU4Health:**
• Review [Programme Information](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en)
• Find open calls on [EU Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)""",
    },
    "digital_europe": {
        "name": "Digital Europe",
        "short_name": "DEP",
        "budget": "€7.5B",
        "focus": "Digital Transformation",
        "icon": "💻",
        "website": "https://digital-strategy.ec.europa.eu/en/activities/digital-programme",
        "resources": {
            "main_portal": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "programme_info": "https://digital-strategy.ec.europa.eu/en/activities/digital-programme",
        },
        "guidance": """🎯 **Getting Started with Digital Europe:**
• Review [Programme Overview](https://digital-strategy.ec.europa.eu/en/activities/digital-programme)
• Find open calls on [EU Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)""",
    },
    "life": {
        "name": "LIFE Programme",
        "short_name": "LIFE",
        "budget": "€5.4B",
        "focus": "Environment & Climate",
        "icon": "🌍",
        "website": "https://cinea.ec.europa.eu/programmes/life_en",
        "resources": {
            "main_portal": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "programme_info": "https://cinea.ec.europa.eu/programmes/life_en",
        },
        "guidance": """🎯 **Getting Started with LIFE:**
• Review [Programme Information](https://cinea.ec.europa.eu/programmes/life_en)
• Find open calls on [EU Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)""",
    },
}

# Keywords to programme mapping for smart programme detection
PROGRAMME_KEYWORDS = {
    "horizon_europe": [
        "research",
        "innovation",
        "RIA",
        "IA",
        "CSA",
        "ERC",
        "EIC",
        "MSCA",
        "cluster",
        "pillar",
        "widening",
        "synergies",
        "missions",
        "scientific",
        "technology development",
        "TRL",
        "breakthrough",
        "excellence",
    ],
    "erasmus_plus": [
        "education",
        "training",
        "learning",
        "mobility",
        "student",
        "teacher",
        "vocational",
        "youth",
        "sport",
        "school",
        "university",
        "higher education",
        "VET",
        "adult education",
        "Jean Monnet",
        "exchange",
        "ECHE",
    ],
    "creative_europe": [
        "culture",
        "creative",
        "arts",
        "heritage",
        "media",
        "audiovisual",
        "film",
        "music",
        "theatre",
        "publishing",
        "television",
        "cinema",
        "distribution",
        "festival",
        "literary",
        "cultural sector",
    ],
    "eu4health": [
        "health",
        "healthcare",
        "disease",
        "prevention",
        "pandemic",
        "crisis",
        "pharmaceutical",
        "medical device",
        "AMR",
        "antimicrobial",
        "cancer",
        "mental health",
        "public health",
        "health system",
        "HERA",
        "vaccine",
    ],
    "digital_europe": [
        "digital",
        "cybersecurity",
        "AI",
        "artificial intelligence",
        "HPC",
        "supercomputing",
        "cloud",
        "data space",
        "digital skills",
        "e-government",
        "digital transformation",
        "blockchain",
        "quantum computing",
    ],
    "life": [
        "environment",
        "biodiversity",
        "nature",
        "climate",
        "circular economy",
        "clean energy",
        "sustainability",
        "ecosystem",
        "conservation",
        "pollution",
        "waste",
        "water",
        "air quality",
        "species protection",
        "habitat",
    ],
}


@dataclass
class MultiProgrammeSearchResult:
    """A unified result from multi-programme search."""

    topic_code: str
    title: str
    programme: str
    programme_name: str
    programme_icon: str
    status: str
    deadline: date | None
    action_type: str | None
    budget_min: float | None
    budget_max: float | None
    funding_rate: int | None
    scope: str | None
    eligibility: str | None
    cluster: str | None
    portal_url: str | None
    relevance_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "topic_code": self.topic_code,
            "title": self.title,
            "programme": self.programme,
            "programme_name": self.programme_name,
            "programme_icon": self.programme_icon,
            "status": self.status,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "action_type": self.action_type,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "funding_rate": self.funding_rate,
            "scope": self.scope,
            "eligibility": self.eligibility,
            "cluster": self.cluster,
            "portal_url": self.portal_url,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }


class MultiProgrammeSearchTool:
    """
    Unified search tool across all EU funding programmes.

    This tool enables:
    - Cross-programme keyword search
    - Programme-specific filtering
    - Status filtering (open, upcoming, closed)
    - Smart programme recommendation based on query
    - Unified result format with programme context
    """

    def __init__(self):
        """Initialize the multi-programme search tool."""
        from ...core.config import settings

        self._db_url = settings.database_url
        self._available = False
        self._programme_counts: dict[str, int] = {}

        # Check database connection and get programme counts
        try:
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor()

            # Check if funding_calls table exists
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'funding_calls'
                )
            """
            )
            table_exists = cursor.fetchone()[0]

            if table_exists:
                # Get counts per programme
                cursor.execute(
                    """
                    SELECT programme, COUNT(*)
                    FROM funding_calls
                    GROUP BY programme
                """
                )
                for row in cursor.fetchall():
                    self._programme_counts[row[0]] = row[1]

                total = sum(self._programme_counts.values())
                num_progs = len(self._programme_counts)
                logger.info(f"✅ MultiProgrammeSearchTool: {total} calls, {num_progs} progs")
                self._available = True
            else:
                logger.warning("funding_calls table not found")

            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize MultiProgrammeSearchTool: {e}")

    def search(
        self,
        keywords: str,
        programmes: list[str] | None = None,
        status: str | None = None,
        year: int | None = None,
        action_type: str | None = None,
        limit: int = 20,
        include_closed: bool = False,
    ) -> dict[str, Any]:
        """
        Search for funding calls across multiple EU programmes.

        Args:
            keywords: Search keywords (e.g., "renewable energy", "youth mobility")
            programmes: List of programmes to search (None = all programmes)
            status: Filter by status ('open', 'upcoming', 'closed')
            year: Filter by call year
            action_type: Filter by action type
            limit: Maximum results per programme
            include_closed: Include closed calls in results

        Returns:
            Dictionary with results grouped by programme and metadata
        """
        if not self._available:
            return {
                "success": False,
                "error": "Multi-programme search not available",
                "results": [],
            }

        # Detect relevant programmes from keywords if not specified
        detected_programmes = self._detect_programmes(keywords)

        # Use specified programmes or all if none specified
        target_programmes = programmes or list(PROGRAMME_INFO.keys())

        results = []
        programme_results: dict[str, list[dict]] = {}

        try:
            conn = psycopg2.connect(self._db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            for programme in target_programmes:
                if programme not in PROGRAMME_INFO:
                    continue

                # Build query for this programme
                query, params = self._build_programme_query(
                    programme=programme,
                    keywords=keywords,
                    status=status,
                    year=year,
                    action_type=action_type,
                    limit=limit,
                    include_closed=include_closed,
                )

                cursor.execute(query, params)
                rows = cursor.fetchall()

                programme_info = PROGRAMME_INFO[programme]
                prog_results = []

                for row in rows:
                    result = MultiProgrammeSearchResult(
                        topic_code=row["topic_code"],
                        title=row["title"],
                        programme=programme,
                        programme_name=programme_info["name"],
                        programme_icon=programme_info["icon"],
                        status=row["status"],
                        deadline=row["deadline"] if isinstance(row["deadline"], date) else None,
                        action_type=row.get("action_type"),
                        budget_min=(
                            float(row["budget_per_project_min"])
                            if row.get("budget_per_project_min")
                            else None
                        ),
                        budget_max=(
                            float(row["budget_per_project_max"])
                            if row.get("budget_per_project_max")
                            else None
                        ),
                        funding_rate=row.get("funding_rate"),
                        scope=row.get("scope"),
                        eligibility=row.get("eligibility"),
                        cluster=row.get("cluster") or row.get("programme_part"),
                        portal_url=row.get("portal_url"),
                        relevance_score=row.get("relevance_score", 0.0),
                        metadata=row.get("metadata", {}),
                    )
                    prog_results.append(result.to_dict())
                    results.append(result.to_dict())

                if prog_results:
                    programme_results[programme] = prog_results

            conn.close()

            # Sort all results by relevance
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

            # Build response
            return {
                "success": True,
                "query": keywords,
                "total_results": len(results),
                "programmes_searched": target_programmes,
                "programmes_with_results": list(programme_results.keys()),
                "detected_relevant_programmes": detected_programmes,
                "results": results[: limit * 2],  # Return top results across all programmes
                "results_by_programme": programme_results,
                "metadata": {
                    "available_programmes": list(PROGRAMME_INFO.keys()),
                    "programme_info": PROGRAMME_INFO,
                },
            }

        except Exception as e:
            logger.error(f"Multi-programme search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    def _build_programme_query(
        self,
        programme: str,
        keywords: str,
        status: str | None,
        year: int | None,
        action_type: str | None,
        limit: int,
        include_closed: bool,
    ) -> tuple:
        """Build SQL query for a specific programme."""
        conditions = ["programme = %s"]
        params = [programme]

        # Status filter
        if status:
            conditions.append("status = %s")
            params.append(status)
        elif not include_closed:
            conditions.append("status != 'closed'")

        # Year filter
        if year:
            conditions.append("call_year = %s")
            params.append(year)

        # Action type filter
        if action_type:
            conditions.append("action_type ILIKE %s")
            params.append(f"%{action_type}%")

        # Keyword search using full-text
        if keywords:
            # Add full-text search condition
            conditions.append(
                """
                (
                    to_tsvector('english', COALESCE(title, '') || ' ' ||
                        COALESCE(scope, '') || ' ' || COALESCE(expected_outcome, ''))
                    @@ plainto_tsquery('english', %s)
                    OR title ILIKE %s
                    OR scope ILIKE %s
                    OR topic_code ILIKE %s
                )
            """
            )
            keyword_pattern = f"%{keywords}%"
            params.extend([keywords, keyword_pattern, keyword_pattern, keyword_pattern])

        where_clause = " AND ".join(conditions)

        # Build query with relevance scoring
        query = f"""
            SELECT *,
                ts_rank(
                    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(scope, '')),
                    plainto_tsquery('english', %s)
                ) as relevance_score
            FROM funding_calls
            WHERE {where_clause}
            ORDER BY
                CASE status
                    WHEN 'open' THEN 1
                    WHEN 'upcoming' THEN 2
                    ELSE 3
                END,
                relevance_score DESC,
                deadline ASC NULLS LAST
            LIMIT %s
        """

        params.insert(0, keywords)  # For ts_rank
        params.append(limit)

        return query, params

    def _detect_programmes(self, keywords: str) -> list[str]:
        """Detect relevant programmes based on keywords."""
        keywords_lower = keywords.lower()
        scores: dict[str, int] = {}

        for programme, prog_keywords in PROGRAMME_KEYWORDS.items():
            score = 0
            for kw in prog_keywords:
                if kw.lower() in keywords_lower:
                    score += 1
            if score > 0:
                scores[programme] = score

        # Sort by score and return top programmes
        sorted_programmes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_programmes[:3]]

    def get_programme_recommendations(
        self,
        description: str,
        organization_type: str | None = None,
        sector: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recommend programmes based on project/organization description.

        Args:
            description: Project or activity description
            organization_type: Type of organization (university, SME, NGO, etc.)
            sector: Primary sector (health, education, culture, etc.)

        Returns:
            List of recommended programmes with reasoning
        """
        recommendations = []
        desc_lower = description.lower()

        # Detect organization type from description if not provided
        inferred_org_type = organization_type
        if not inferred_org_type:
            if any(
                x in desc_lower
                for x in ["university", "universities", "academic", "higher education", "hei"]
            ):
                inferred_org_type = "university"
            elif any(x in desc_lower for x in ["sme", "startup", "small business", "company"]):
                inferred_org_type = "sme"
            elif any(x in desc_lower for x in ["school", "primary", "secondary"]):
                inferred_org_type = "school"
            elif any(x in desc_lower for x in ["hospital", "clinic", "medical"]):
                inferred_org_type = "health_org"
            elif any(x in desc_lower for x in ["ngo", "non-profit", "nonprofit", "foundation"]):
                inferred_org_type = "ngo"

        # Score each programme
        for programme, info in PROGRAMME_INFO.items():
            score = 0
            reasons = []

            # Check keywords
            keywords = PROGRAMME_KEYWORDS.get(programme, [])
            matched_keywords = [kw for kw in keywords if kw.lower() in desc_lower]

            if matched_keywords:
                score += len(matched_keywords) * 10
                kw_count = len(matched_keywords)
                kw_list = ", ".join(matched_keywords[:3])
                reasons.append(f"Matches {kw_count} programme keywords: {kw_list}")

            # Organization type bonuses (use inferred or provided)
            org_type_to_check = inferred_org_type or organization_type
            if org_type_to_check:
                org_lower = org_type_to_check.lower()
                if programme == "horizon_europe":
                    if any(x in org_lower for x in ["university", "research", "institute"]):
                        score += 15
                        reasons.append("Strong match for research organizations")
                    elif any(x in org_lower for x in ["sme", "startup", "company"]):
                        score += 20
                        reasons.append("EIC Accelerator targets SMEs with breakthrough innovation")
                elif programme == "erasmus_plus" and any(
                    x in org_lower for x in ["school", "university", "education", "training"]
                ):
                    score += 15
                    reasons.append("Designed for educational institutions")
                elif programme == "creative_europe" and any(
                    x in org_lower for x in ["cultural", "arts", "media", "creative"]
                ):
                    score += 15
                    reasons.append("Tailored for cultural/creative organizations")
                elif programme == "eu4health":
                    health_orgs = ["hospital", "health", "medical", "ngo", "health_org"]
                    if any(x in org_lower for x in health_orgs):
                        score += 15
                        reasons.append("Focus on health sector organizations")
                    # SMEs in health sector can also benefit from EU4Health
                    if any(x in org_lower for x in ["sme", "startup", "company"]):
                        if "health" in desc_lower or "medical" in desc_lower:
                            score += 10
                            reasons.append("SMEs with health focus eligible for EU4Health")
                elif programme == "digital_europe":
                    if any(x in org_lower for x in ["sme", "startup", "company"]):
                        score += 10
                        reasons.append("Supports SME digital transformation")

            if score > 0:
                recommendations.append(
                    {
                        "programme": programme,
                        "programme_name": info["name"],
                        "programme_icon": info["icon"],
                        "budget": info["budget"],
                        "focus": info["focus"],
                        "score": score,
                        "reasons": reasons,
                        "website": info["website"],
                    }
                )

        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        # If no specific matches found, provide an overview of all programmes
        # This handles broad queries like "looking for EU funding"
        if not recommendations:
            # Return overview of main programmes for universities/general
            overview_programmes = ["horizon_europe", "erasmus_plus", "creative_europe"]
            if inferred_org_type:
                if "university" in inferred_org_type.lower():
                    overview_programmes = ["horizon_europe", "erasmus_plus"]
                elif "health" in inferred_org_type.lower():
                    overview_programmes = ["horizon_europe", "eu4health"]
                elif any(x in inferred_org_type.lower() for x in ["creative", "cultural", "arts"]):
                    overview_programmes = ["creative_europe", "horizon_europe"]

            for programme in overview_programmes:
                if programme in PROGRAMME_INFO:
                    info = PROGRAMME_INFO[programme]
                    recommendations.append(
                        {
                            "programme": programme,
                            "programme_name": info["name"],
                            "programme_icon": info["icon"],
                            "budget": info["budget"],
                            "focus": info["focus"],
                            "score": 5,  # Base score for overview
                            "reasons": ["Potentially relevant for your organization type"],
                            "website": info["website"],
                            "is_overview": True,  # Mark as overview recommendation
                        }
                    )

        return recommendations[:5]

    def get_all_programme_info(self) -> dict[str, Any]:
        """Get information about all supported programmes."""
        return {
            "programmes": PROGRAMME_INFO,
            "programme_counts": self._programme_counts,
            "total_calls": sum(self._programme_counts.values()),
            "keywords_by_programme": PROGRAMME_KEYWORDS,
        }


# Create standalone execute function for tool orchestration
def search_all_programmes_execute(
    keywords: str,
    programmes: list[str] | None = None,
    status: str | None = None,
    year: int | None = None,
    action_type: str | None = None,
    limit: int = 20,
    include_closed: bool = False,
) -> dict[str, Any]:
    """
    Execute multi-programme search.

    This is the main entry point for the multi-programme search tool.
    It searches across all supported EU funding programmes.

    Args:
        keywords: Search keywords
        programmes: List of programmes to search (None = all)
        status: Filter by status ('open', 'upcoming')
        year: Filter by call year
        action_type: Filter by action type
        limit: Maximum results per programme
        include_closed: Include closed calls

    Returns:
        Search results with programme context
    """
    tool = MultiProgrammeSearchTool()
    return tool.search(
        keywords=keywords,
        programmes=programmes,
        status=status,
        year=year,
        action_type=action_type,
        limit=limit,
        include_closed=include_closed,
    )


def get_programme_recommendations_execute(
    description: str,
    organization_type: str | None = None,
    sector: str | None = None,
) -> dict[str, Any]:
    """
    Get programme recommendations based on project description.

    Args:
        description: Project or activity description
        organization_type: Type of organization
        sector: Primary sector

    Returns:
        List of recommended programmes with reasoning
    """
    tool = MultiProgrammeSearchTool()
    recommendations = tool.get_programme_recommendations(
        description=description,
        organization_type=organization_type,
        sector=sector,
    )

    return {
        "success": True,
        "recommendations": recommendations,
        "total_programmes": len(PROGRAMME_INFO),
        "available_programmes": list(PROGRAMME_INFO.keys()),
    }


def get_programme_info_execute(
    programme: str | None = None,
) -> dict[str, Any]:
    """
    Get information about EU funding programmes.

    Args:
        programme: Specific programme to get info for (None = all)

    Returns:
        Programme information including actionable guidance and official links
    """
    if programme and programme in PROGRAMME_INFO:
        # Get info for specific programme
        from ..call_extractors import EXTRACTORS

        info = PROGRAMME_INFO[programme].copy()

        # Add extractor info if available
        if programme in EXTRACTORS:
            extractor = EXTRACTORS[programme]()
            if hasattr(extractor, "get_programme_info"):
                detailed_info = extractor.get_programme_info()
                info.update(detailed_info)

        # Build response with prominent actionable guidance
        response = {
            "success": True,
            "programme": programme,
            "info": info,
        }

        # Add top-level actionable content for easy agent access
        if "guidance" in info:
            response["actionable_guidance"] = info["guidance"]
        if "resources" in info:
            response["official_resources"] = info["resources"]
        if "website" in info:
            response["official_website"] = info["website"]

        return response

    # Return all programmes
    tool = MultiProgrammeSearchTool()
    all_info = tool.get_all_programme_info()

    # Add guidance for all programmes
    all_guidance = {}
    for prog_key, prog_info in PROGRAMME_INFO.items():
        if "guidance" in prog_info:
            all_guidance[prog_key] = prog_info["guidance"]

    return {
        "success": True,
        "programmes": all_info,
        "actionable_guidance": all_guidance,
    }
