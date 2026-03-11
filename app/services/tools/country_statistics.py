"""
Country Statistics Tool for Horizon Europe.

Provides country-level participation statistics with graceful degradation:
uses Neo4j graph database as primary source, falls back to PostgreSQL SQL
queries when Neo4j is unavailable or times out.

Includes country code resolution, eligibility checks, top organizations,
and aggregate funding statistics.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

logger = logging.getLogger(__name__)

# Country name/adjective to ISO 3166-1 alpha-2 code mapping
COUNTRY_CODES: dict[str, str] = {
    "germany": "DE",
    "german": "DE",
    "france": "FR",
    "french": "FR",
    "italy": "IT",
    "italian": "IT",
    "spain": "ES",
    "spanish": "ES",
    "netherlands": "NL",
    "dutch": "NL",
    "belgium": "BE",
    "belgian": "BE",
    "austria": "AT",
    "austrian": "AT",
    "sweden": "SE",
    "swedish": "SE",
    "denmark": "DK",
    "danish": "DK",
    "finland": "FI",
    "finnish": "FI",
    "ireland": "IE",
    "irish": "IE",
    "portugal": "PT",
    "portuguese": "PT",
    "greece": "GR",
    "greek": "GR",
    "poland": "PL",
    "polish": "PL",
    "switzerland": "CH",
    "swiss": "CH",
    "norway": "NO",
    "norwegian": "NO",
    "uk": "GB",
    "united kingdom": "GB",
    "britain": "GB",
    "british": "GB",
    "israel": "IL",
    "israeli": "IL",
    "czech": "CZ",
    "czechia": "CZ",
    "romania": "RO",
    "romanian": "RO",
    "hungary": "HU",
    "hungarian": "HU",
    "slovenia": "SI",
    "slovenian": "SI",
    "croatia": "HR",
    "croatian": "HR",
    "estonia": "EE",
    "estonian": "EE",
    "latvia": "LV",
    "latvian": "LV",
    "lithuania": "LT",
    "lithuanian": "LT",
    "cyprus": "CY",
    "cypriot": "CY",
    "malta": "MT",
    "maltese": "MT",
    "luxembourg": "LU",
    "slovakia": "SK",
    "slovak": "SK",
    "bulgaria": "BG",
    "bulgarian": "BG",
    "turkey": "TR",
    "turkish": "TR",
}

# EU Member States (ISO 3166-1 alpha-2)
EU_MEMBERS: set[str] = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}

# Associated Countries to Horizon Europe
ASSOCIATED_COUNTRIES: set[str] = {
    "NO",
    "IS",
    "IL",
    "CH",
    "TR",
    "UA",
    "MD",
    "ME",
    "RS",
    "AL",
    "MK",
    "BA",
    "GE",
    "AM",
    "TN",
    "MA",
    "FO",
    "GB",
}


async def get_country_statistics_execute(country: str) -> dict[str, Any]:
    """
    Get country statistics with graceful degradation.

    Uses Neo4j graph database as primary source, falls back to SQL
    when Neo4j is unavailable or times out.

    Args:
        country: Country name, adjective, or ISO 3166-1 alpha-2 code.

    Returns:
        Dictionary with country statistics including eligibility, top organizations,
        and participation data.
    """
    # Resolve country code
    country_code = None
    country_lower = country.lower()

    if len(country) == 2:
        country_code = country.upper()
    else:
        for name, code in COUNTRY_CODES.items():
            if name in country_lower:
                country_code = code
                break

    if not country_code:
        return {
            "success": False,
            "message": f"Could not identify country code for '{country}'. Try using ISO codes like DE, FR, IT.",
        }

    # Track sources and degradation
    sources_used: list[str] = []
    degradation_reason: str | None = None
    neo4j_timeout = 10.0  # seconds

    # ==================================================================
    # ATTEMPT 1: Try Neo4j graph database (primary source)
    # ==================================================================
    graph_result = None
    try:
        from ..data_intelligence.graph_service import GraphSearchService

        graph = GraphSearchService()

        def get_neo4j_data():
            """Fetch all Neo4j data in a single thread."""
            eligibility = graph.check_country_eligibility(country_code)
            top_orgs = graph.get_top_organizations(None, country_code, 10)
            return {"eligibility": eligibility, "top_orgs": top_orgs}

        # Execute with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_neo4j_data)
            try:
                graph_result = future.result(timeout=neo4j_timeout)
                sources_used.append("neo4j")
                logger.info(f"Neo4j country stats for {country_code}: success")
            except FuturesTimeoutError:
                degradation_reason = "timeout"
                logger.warning(
                    f"Neo4j timeout for country stats ({neo4j_timeout}s) - falling back to SQL"
                )
            except Exception as e:
                degradation_reason = "connection_error"
                logger.warning(f"Neo4j error: {e} - falling back to SQL")

    except ImportError:
        degradation_reason = "service_unavailable"
        logger.warning("Neo4j service not available - falling back to SQL")
    except Exception as e:
        degradation_reason = "initialization_error"
        logger.warning(f"Neo4j initialization error: {e} - falling back to SQL")

    # ==================================================================
    # ATTEMPT 2: Fall back to SQL if Neo4j failed
    # ==================================================================
    sql_result = None
    if not graph_result:
        sql_result = await _get_country_stats_sql(country_code)
        if sql_result:
            sources_used.append("postgresql")
            logger.info(f"SQL fallback for country stats {country_code}: success")

    # ==================================================================
    # Combine results
    # ==================================================================
    if graph_result:
        # Full graph data available
        return {
            "success": True,
            "country": country,
            "country_code": country_code,
            "eligibility": graph_result.get("eligibility"),
            "top_organizations": graph_result.get("top_orgs", []),
            "organization_count": len(graph_result.get("top_orgs", [])),
            "source": "neo4j_graph",
            "metadata": {
                "sources_used": sources_used,
                "search_type": "graph",
                "degraded": False,
            },
        }
    elif sql_result:
        # SQL fallback data
        return {
            "success": True,
            "country": country,
            "country_code": country_code,
            "eligibility": sql_result.get("eligibility"),
            "top_organizations": sql_result.get("top_organizations", []),
            "organization_count": sql_result.get("organization_count", 0),
            "project_count": sql_result.get("project_count", 0),
            "total_funding": sql_result.get("total_funding", 0),
            "source": "sql_fallback",
            "metadata": {
                "sources_used": sources_used,
                "search_type": "sql_fallback",
                "degraded": True,
                "degradation_reason": degradation_reason,
                "limitation": "Graph statistics temporarily unavailable. Showing project participation data from SQL.",
            },
        }
    else:
        # Both sources failed
        return {
            "success": False,
            "country": country,
            "country_code": country_code,
            "error": "Unable to retrieve country statistics - both graph and SQL sources unavailable",
            "metadata": {"sources_used": [], "degradation_reason": degradation_reason},
        }


async def _get_country_stats_sql(country_code: str) -> dict[str, Any] | None:
    """
    SQL-based fallback for country statistics.

    Provides partial country statistics when Neo4j is unavailable:
    - Top organizations by project participation
    - Total project count and funding
    - Basic eligibility info

    Args:
        country_code: ISO 3166-1 alpha-2 country code.

    Returns:
        Dictionary with SQL-based country statistics, or None if unavailable.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not set - SQL fallback unavailable")
        return None

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get top organizations in this country
        top_orgs_query = """
            SELECT
                o.name,
                o."shortName" as short_name,
                o."activityType" as org_type,
                o.city,
                COUNT(DISTINCT o."projectID") as project_count,
                SUM(COALESCE(o."ecContribution", 0)) as total_funding,
                SUM(CASE WHEN o.role = 'coordinator' THEN 1 ELSE 0 END) as coordinations
            FROM organizations o
            WHERE o.country = %s
            AND o."projectID" IS NOT NULL
            GROUP BY o.name, o."shortName", o."activityType", o.city
            HAVING COUNT(DISTINCT o."projectID") >= 3
            ORDER BY project_count DESC, total_funding DESC
            LIMIT 20
        """
        cursor.execute(top_orgs_query, [country_code])
        top_orgs_rows = cursor.fetchall()

        top_organizations = []
        for row in top_orgs_rows:
            top_organizations.append(
                {
                    "name": row["name"],
                    "short_name": row.get("short_name") or row["name"],
                    "type": row.get("org_type", "Unknown"),
                    "city": row.get("city", ""),
                    "project_count": int(row.get("project_count", 0)),
                    "coordinations": int(row.get("coordinations", 0)),
                    "total_funding": float(row.get("total_funding", 0) or 0),
                }
            )

        # Get country aggregates
        country_stats_query = """
            SELECT
                COUNT(DISTINCT o."projectID") as project_count,
                SUM(COALESCE(o."ecContribution", 0)) as total_funding,
                COUNT(DISTINCT CASE WHEN o.role = 'coordinator' THEN o."projectID" END) as coordinations,
                COUNT(DISTINCT o.name) as org_count
            FROM organizations o
            WHERE o.country = %s
        """
        cursor.execute(country_stats_query, [country_code])
        stats_row = cursor.fetchone()

        cursor.close()
        conn.close()

        # Build eligibility info based on known country lists
        if country_code in EU_MEMBERS:
            eligibility_status = "EU Member State - Full eligibility"
            is_eligible = True
        elif country_code in ASSOCIATED_COUNTRIES:
            eligibility_status = "Associated Country - Eligible with conditions"
            is_eligible = True
        else:
            eligibility_status = "Third Country - Limited eligibility"
            is_eligible = False

        return {
            "top_organizations": top_organizations,
            "organization_count": len(top_organizations),
            "project_count": int(stats_row.get("project_count", 0)) if stats_row else 0,
            "total_funding": float(stats_row.get("total_funding", 0) or 0) if stats_row else 0,
            "coordinations": int(stats_row.get("coordinations", 0)) if stats_row else 0,
            "total_organizations": int(stats_row.get("org_count", 0)) if stats_row else 0,
            "eligibility": {
                "country_code": country_code,
                "is_eligible": is_eligible,
                "eligibility_status": eligibility_status,
                "source": "sql_fallback",
            },
        }

    except Exception as e:
        logger.error(f"SQL country stats fallback error: {e}")
        return None
