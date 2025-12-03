"""
Partner Discovery Tool for Horizon Europe Projects.

Helps users find potential consortium partners based on their track record
in relevant Horizon Europe projects.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Organization type descriptions
ORG_TYPE_DESCRIPTIONS = {
    "HES": "Higher Education Institution",
    "REC": "Research Organization",
    "PRC": "Private Company (Large)",
    "SME": "Small/Medium Enterprise",
    "PUB": "Public Body",
    "OTH": "Other Organization"
}

# Cluster mapping
CLUSTER_MAP = {
    'CL1': 'HLTH', 'CLUSTER1': 'HLTH', 'CLUSTER-1': 'HLTH', 'HEALTH': 'HLTH',
    'CL2': 'CL2', 'CLUSTER2': 'CL2', 'CLUSTER-2': 'CL2', 'CULTURE': 'CL2',
    'CL3': 'CL3', 'CLUSTER3': 'CL3', 'CLUSTER-3': 'CL3', 'SECURITY': 'CL3',
    'CL4': 'CL4', 'CLUSTER4': 'CL4', 'CLUSTER-4': 'CL4', 'DIGITAL': 'CL4',
    'CL5': 'CL5', 'CLUSTER5': 'CL5', 'CLUSTER-5': 'CL5', 'CLIMATE': 'CL5', 'ENERGY': 'CL5',
    'CL6': 'CL6', 'CLUSTER6': 'CL6', 'CLUSTER-6': 'CL6', 'FOOD': 'CL6',
    'EIC': 'EIC', 'ERC': 'ERC', 'MSCA': 'MSCA',
}

# Country name to code mapping
COUNTRY_CODES = {
    'germany': 'DE', 'german': 'DE', 'de': 'DE',
    'france': 'FR', 'french': 'FR', 'fr': 'FR',
    'italy': 'IT', 'italian': 'IT', 'it': 'IT',
    'spain': 'ES', 'spanish': 'ES', 'es': 'ES',
    'netherlands': 'NL', 'dutch': 'NL', 'nl': 'NL',
    'belgium': 'BE', 'belgian': 'BE', 'be': 'BE',
    'austria': 'AT', 'austrian': 'AT', 'at': 'AT',
    'sweden': 'SE', 'swedish': 'SE', 'se': 'SE',
    'denmark': 'DK', 'danish': 'DK', 'dk': 'DK',
    'finland': 'FI', 'finnish': 'FI', 'fi': 'FI',
    'ireland': 'IE', 'irish': 'IE', 'ie': 'IE',
    'portugal': 'PT', 'portuguese': 'PT', 'pt': 'PT',
    'greece': 'EL', 'greek': 'EL', 'el': 'EL', 'gr': 'EL',
    'poland': 'PL', 'polish': 'PL', 'pl': 'PL',
    'czech': 'CZ', 'czechia': 'CZ', 'cz': 'CZ',
    'romania': 'RO', 'romanian': 'RO', 'ro': 'RO',
    'hungary': 'HU', 'hungarian': 'HU', 'hu': 'HU',
    'switzerland': 'CH', 'swiss': 'CH', 'ch': 'CH',
    'norway': 'NO', 'norwegian': 'NO', 'no': 'NO',
    'uk': 'UK', 'united kingdom': 'UK', 'britain': 'UK', 'british': 'UK', 'gb': 'UK',
    'israel': 'IL', 'israeli': 'IL', 'il': 'IL',
    'slovenia': 'SI', 'slovenian': 'SI', 'si': 'SI',
    'croatia': 'HR', 'croatian': 'HR', 'hr': 'HR',
    'estonia': 'EE', 'estonian': 'EE', 'ee': 'EE',
    'latvia': 'LV', 'latvian': 'LV', 'lv': 'LV',
    'lithuania': 'LT', 'lithuanian': 'LT', 'lt': 'LT',
    'cyprus': 'CY', 'cypriot': 'CY', 'cy': 'CY',
    'malta': 'MT', 'maltese': 'MT', 'mt': 'MT',
    'luxembourg': 'LU', 'lu': 'LU',
    'slovakia': 'SK', 'slovak': 'SK', 'sk': 'SK',
    'bulgaria': 'BG', 'bulgarian': 'BG', 'bg': 'BG',
    'turkey': 'TR', 'turkish': 'TR', 'tr': 'TR',
}

# Organization type mapping from user input
# Note: CORDIS doesn't have a separate SME type - SMEs are classified as PRC
# We map SME requests to PRC but note this in the output
ORG_TYPE_MAP = {
    'university': 'HES', 'universities': 'HES', 'hes': 'HES', 'academic': 'HES',
    'research': 'REC', 'rec': 'REC', 'research organization': 'REC', 'institute': 'REC',
    'company': 'PRC', 'companies': 'PRC', 'prc': 'PRC', 'industry': 'PRC', 'corporate': 'PRC',
    'sme': 'PRC', 'smes': 'PRC', 'small': 'PRC', 'startup': 'PRC', 'startups': 'PRC',  # SMEs are under PRC in CORDIS
    'public': 'PUB', 'pub': 'PUB', 'government': 'PUB',
}


class PartnerDiscoveryTool:
    """Tool to find experienced partners for consortium building."""

    def __init__(self):
        """Initialize with database connection."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set - partner discovery will be limited")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def _normalize_country(self, country: Optional[str]) -> Optional[str]:
        """Normalize country name to code."""
        if not country:
            return None
        country_lower = country.lower().strip()
        # Check if already a 2-letter code
        if len(country_lower) == 2:
            return country_lower.upper()
        return COUNTRY_CODES.get(country_lower, country.upper())

    def _normalize_org_type(self, org_type: Optional[str]) -> Optional[str]:
        """Normalize organization type to code."""
        if not org_type:
            return None
        org_lower = org_type.lower().strip()
        return ORG_TYPE_MAP.get(org_lower, org_type.upper())

    def _normalize_cluster(self, cluster: Optional[str]) -> Optional[str]:
        """Normalize cluster code."""
        if not cluster:
            return None
        cluster_upper = cluster.upper().replace(' ', '').replace('-', '')
        return CLUSTER_MAP.get(cluster_upper, cluster.upper())

    def find_partners(
        self,
        topic_keywords: str,
        country: Optional[str] = None,
        organization_type: Optional[str] = None,
        cluster: Optional[str] = None,
        min_projects: int = 2,
        role_filter: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Find organizations with proven track records in relevant Horizon Europe projects.

        Args:
            topic_keywords: Required keywords describing the research area
            country: Optional country name or code
            organization_type: Optional org type (HES, REC, PRC, SME)
            cluster: Optional cluster code
            min_projects: Minimum projects to be considered experienced
            role_filter: Filter by role (coordinator, participant, or None for both)
            limit: Max results to return

        Returns:
            List of experienced partners with track records
        """
        try:
            conn = self._get_connection()
            if not conn:
                return self._get_fallback_response(topic_keywords)

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Normalize inputs
            country_code = self._normalize_country(country)
            org_type_code = self._normalize_org_type(organization_type)
            cluster_code = self._normalize_cluster(cluster)

            # Build WHERE conditions for projects
            project_conditions = ["p.\"frameworkProgramme\" = 'HORIZON'"]
            params = []

            # Topic keywords filter (search in objective and title)
            keywords = topic_keywords.split()
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append("(p.objective ILIKE %s OR p.title ILIKE %s)")
                params.extend([f"%{kw}%", f"%{kw}%"])
            if keyword_conditions:
                project_conditions.append(f"({' OR '.join(keyword_conditions)})")

            # Cluster filter
            if cluster_code:
                project_conditions.append("p.topics ILIKE %s")
                params.append(f"%{cluster_code}%")

            project_where = " AND ".join(project_conditions)

            # Build organization filter conditions
            org_conditions = []
            if country_code:
                org_conditions.append("o.country = %s")
                params.append(country_code)

            if org_type_code:
                org_conditions.append("o.\"activityType\" = %s")
                params.append(org_type_code)

            if role_filter:
                org_conditions.append("o.role = %s")
                params.append(role_filter.lower())

            org_where = " AND ".join(org_conditions) if org_conditions else "TRUE"

            # Main query: Find organizations with experience in matching projects
            sql = f"""
                WITH matching_projects AS (
                    SELECT DISTINCT p.id, p.acronym, p.title, p."ecMaxContribution", p."startDate"
                    FROM projects p
                    WHERE {project_where}
                ),
                org_participation AS (
                    SELECT
                        o."organisationID",
                        o.name,
                        o."shortName",
                        o.country,
                        o.city,
                        o."activityType",
                        mp.id as project_id,
                        mp.acronym as project_acronym,
                        mp.title as project_title,
                        mp."startDate" as project_start,
                        o.role,
                        o."ecContribution"
                    FROM organizations o
                    JOIN matching_projects mp ON o."projectID" = mp.id
                    WHERE {org_where}
                ),
                org_stats AS (
                    SELECT
                        "organisationID",
                        name,
                        "shortName",
                        country,
                        MAX(city) as city,
                        "activityType",
                        COUNT(DISTINCT project_id) as relevant_projects,
                        SUM(CASE WHEN role = 'coordinator' THEN 1 ELSE 0 END) as as_coordinator,
                        SUM(CASE WHEN role = 'participant' THEN 1 ELSE 0 END) as as_participant,
                        SUM("ecContribution") as funding_in_relevant,
                        ARRAY_AGG(DISTINCT jsonb_build_object(
                            'acronym', project_acronym,
                            'title', project_title,
                            'role', role,
                            'funding', "ecContribution",
                            'start_date', project_start
                        )) as projects
                    FROM org_participation
                    GROUP BY "organisationID", name, "shortName", country, "activityType"
                    HAVING COUNT(DISTINCT project_id) >= %s
                )
                SELECT
                    os.*,
                    (SELECT COUNT(DISTINCT o2."projectID")
                     FROM organizations o2
                     WHERE o2."organisationID" = os."organisationID") as total_he_projects
                FROM org_stats os
                ORDER BY relevant_projects DESC, as_coordinator DESC, funding_in_relevant DESC
                LIMIT %s
            """
            params.extend([min_projects, limit])

            cursor.execute(sql, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            if not results:
                return {
                    "success": True,
                    "tool_name": "find_experienced_partners",
                    "query_params": {
                        "topic_keywords": topic_keywords,
                        "country": country,
                        "organization_type": organization_type,
                        "cluster": cluster
                    },
                    "total_found": 0,
                    "experienced_partners": [],
                    "message": f"No organizations found with {min_projects}+ projects matching '{topic_keywords}'. Try broader keywords or reduce min_projects.",
                    "suggestions": [
                        "Try more general keywords",
                        "Remove country or organization type filters",
                        "Lower min_projects threshold to 1"
                    ],
                    "data_source": "cordis_database",
                    "timestamp": datetime.now().isoformat()
                }

            # Process results
            experienced_partners = []
            for r in results:
                # Parse projects JSON
                projects_list = []
                if r['projects']:
                    for p in r['projects'][:5]:  # Limit to 5 recent projects
                        if isinstance(p, dict):
                            projects_list.append({
                                "acronym": p.get('acronym', 'N/A'),
                                "title": (p.get('title') or '')[:60] + ('...' if len(p.get('title') or '') > 60 else ''),
                                "role": p.get('role', 'participant'),
                                "funding": round(float(p.get('funding') or 0), 0),
                                "start_date": str(p.get('start_date', ''))[:10] if p.get('start_date') else None
                            })

                # Calculate experience score
                experience_score = self._calculate_experience_score(
                    relevant_projects=int(r['relevant_projects'] or 0),
                    as_coordinator=int(r['as_coordinator'] or 0),
                    total_projects=int(r['total_he_projects'] or 0),
                    funding=float(r['funding_in_relevant'] or 0)
                )

                partner = {
                    "name": r['name'] or 'Unknown',
                    "short_name": r['shortName'] or r['name'] or 'Unknown',
                    "country": r['country'] or 'Unknown',
                    "city": r['city'] or '',
                    "type": r['activityType'] or 'Unknown',
                    "type_description": ORG_TYPE_DESCRIPTIONS.get(r['activityType'], r['activityType'] or 'Unknown'),
                    "track_record": {
                        "total_he_projects": int(r['total_he_projects'] or 0),
                        "relevant_projects": int(r['relevant_projects'] or 0),
                        "as_coordinator": int(r['as_coordinator'] or 0),
                        "as_participant": int(r['as_participant'] or 0),
                        "funding_in_relevant": round(float(r['funding_in_relevant'] or 0), 0)
                    },
                    "relevant_projects": projects_list,
                    "experience_score": experience_score
                }

                experienced_partners.append(partner)

            # Sort by experience score
            experienced_partners.sort(key=lambda x: x['experience_score'], reverse=True)

            # Generate insights
            insights = self._generate_insights(experienced_partners, topic_keywords)

            return {
                "success": True,
                "tool_name": "find_experienced_partners",
                "query_params": {
                    "topic_keywords": topic_keywords,
                    "country": country,
                    "organization_type": organization_type,
                    "cluster": cluster,
                    "min_projects": min_projects
                },
                "total_found": len(experienced_partners),
                "experienced_partners": experienced_partners,
                "aggregated_insights": insights,
                "search_tips": self._generate_search_tips(experienced_partners, topic_keywords, country, organization_type),
                "data_source": "cordis_database",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Partner discovery error: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_response(topic_keywords)

    def _calculate_experience_score(
        self,
        relevant_projects: int,
        as_coordinator: int,
        total_projects: int,
        funding: float
    ) -> float:
        """Calculate experience/expertise score for ranking."""
        score = 0.0

        # Relevant project count (max 0.4)
        score += min(relevant_projects / 10, 0.4)

        # Coordinator experience bonus (max 0.25)
        score += min(as_coordinator / 5, 0.25)

        # Total HE experience (max 0.15)
        score += min(total_projects / 50, 0.15)

        # Funding received (max 0.2)
        score += min(funding / 10_000_000, 0.2)

        return round(min(score, 1.0), 2)

    def _generate_insights(
        self,
        partners: List[Dict],
        keywords: str
    ) -> Dict[str, Any]:
        """Generate aggregated insights from results."""
        if not partners:
            return {}

        # Most common partner types
        type_counts = {}
        country_counts = {}
        total_relevant = 0

        for p in partners:
            org_type = p.get('type', 'Unknown')
            country = p.get('country', 'Unknown')
            relevant = p.get('track_record', {}).get('relevant_projects', 0)

            type_counts[org_type] = type_counts.get(org_type, 0) + 1
            country_counts[country] = country_counts.get(country, 0) + 1
            total_relevant += relevant

        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "most_common_partner_types": [t[0] for t in sorted_types[:3]],
            "top_countries_in_topic": [c[0] for c in sorted_countries[:5]],
            "total_relevant_projects_found": total_relevant,
            "average_projects_per_org": round(total_relevant / max(len(partners), 1), 1)
        }

    def _generate_search_tips(
        self,
        partners: List[Dict],
        keywords: str,
        country: Optional[str],
        organization_type: Optional[str] = None
    ) -> List[str]:
        """Generate helpful search tips."""
        tips = []

        if len(partners) < 5:
            tips.append("Consider broadening your search with more general keywords")

        if not country and partners:
            # Suggest top country
            countries = [p.get('country') for p in partners if p.get('country')]
            if countries:
                from collections import Counter
                top_country = Counter(countries).most_common(1)[0][0]
                tips.append(f"Most experienced partners in this area are from {top_country}")

        # Note about SME data
        if organization_type and organization_type.lower() in ['sme', 'smes', 'small', 'startup']:
            tips.append("Note: CORDIS classifies SMEs under 'Private Companies' (PRC). Results show companies which may include SMEs.")

        # Coordinator tip
        coordinators = [p for p in partners if p.get('track_record', {}).get('as_coordinator', 0) > 0]
        if coordinators:
            tips.append(f"{len(coordinators)} organizations have coordination experience in this area")

        return tips

    def _get_fallback_response(self, keywords: str) -> Dict[str, Any]:
        """Return fallback when database unavailable."""
        return {
            "success": False,
            "tool_name": "find_experienced_partners",
            "query_params": {"topic_keywords": keywords},
            "total_found": 0,
            "experienced_partners": [],
            "message": "Database unavailable - cannot search for partners",
            "suggestions": [
                "Check database connection",
                "Try again later"
            ],
            "data_source": "fallback",
            "timestamp": datetime.now().isoformat()
        }


# Async wrapper for tool orchestrator compatibility
async def find_experienced_partners_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute partner discovery tool.

    This tool finds organizations with proven track records in specific Horizon Europe topics.
    Use when users want to find potential consortium partners, identify experienced coordinators,
    or discover organizations working in a specific research area.
    """
    tool = PartnerDiscoveryTool()

    topic_keywords = params.get('topic_keywords') or params.get('keywords', '')
    if not topic_keywords:
        return {
            "success": False,
            "error": "topic_keywords is required",
            "tool_name": "find_experienced_partners"
        }

    return tool.find_partners(
        topic_keywords=topic_keywords,
        country=params.get('country'),
        organization_type=params.get('organization_type'),
        cluster=params.get('cluster'),
        min_projects=params.get('min_projects', 2),
        role_filter=params.get('role_filter'),
        limit=params.get('limit', 20)
    )
