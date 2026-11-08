"""
Call Search and Call Details Tools for Horizon Europe.

Provides two tool functions for funding call operations:

1. search_funding_calls_execute: Search for open/closed funding calls by keywords,
   status, year, and cluster. Returns structured call data with topic codes, deadlines,
   budgets, and scope information.

2. get_call_details_execute: Get detailed information for a specific call ID with
   multi-fallback logic:
   - Primary: dedicated get_call_details method (includes API enrichment)
   - Fallback 1: keyword search for the call ID (including closed calls)
   - Fallback 2: base call identifier search (e.g., HORIZON-CL5-2026-02)
   - Fallback 3: direct EU Portal API fetch via CallEnrichmentService
   - Final: suggest similar calls from the same cluster/year

Uses LocalCallSearchService for local database queries and CallEnrichmentService
for direct EU Portal API access as a last resort.
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def search_funding_calls_execute(
    keywords: str | list,
    status: str | None = None,
    year: int | str | None = None,
    cluster: str | None = None,
) -> dict[str, Any]:
    """
    Search funding calls.

    Args:
        keywords: Search keywords (string or list of strings).
        status: Call status filter - "open", "upcoming", "closed", or "all". Omit to include open AND upcoming calls.
        year: Optional year filter.
        cluster: Optional cluster filter.

    Returns:
        Dict with calls_found count and list of matching calls.
    """
    try:
        from ..local_call_search_service import LocalCallSearchService
        from ..call_catalog import CallCatalog
        from ..call_query import effective_status, query_year

        call_service = await asyncio.to_thread(LocalCallSearchService)

        # Handle keywords being a list or string
        if isinstance(keywords, list):
            keywords = " ".join(keywords)

        if status not in (None, "open", "upcoming", "closed", "all"):
            return {"success": False, "error": "Invalid call status", "calls": [], "calls_found": 0}
        year = year or query_year(keywords)
        include_closed = status in ("closed", "all")
        results = await asyncio.to_thread(
            call_service.search_calls,
            query=keywords,
            num_results=50,
            include_closed=include_closed,
            year_filter=str(year) if year else None,
            cluster=cluster,
            status_filter=status,
        )
        coverage = await asyncio.to_thread(CallCatalog(call_service._db_url).health)
        limitations = []
        if coverage.get("stale"):
            limitations.append(
                "The local catalogue has not completed a successful EU Portal sync in the last "
                "24 hours. An empty result is not evidence that no relevant calls exist."
            )
        if results.get("success") is False:
            return {
                "success": False,
                "error": results.get("error", "Call retrieval failed"),
                "calls": [],
                "calls_found": 0,
                "catalogue": coverage,
                "limitations": limitations,
            }
        filtered_calls = []
        for c in results.get("calls", []):
            c["status"] = effective_status(c)
            if status in ("open", "upcoming", "closed") and c["status"] != status:
                continue
            if status is None and c["status"] not in ("open", "upcoming"):
                continue
            if year and str(c.get("call_year")) != str(year):
                continue
            if cluster and str(c.get("cluster", "")).upper() != cluster.upper():
                continue
            filtered_calls.append(c)

        # Pass through ALL available fields for rich formatting
        return {
            "success": True,
            "catalogue": coverage,
            "limitations": limitations,
            "status_filter": status or "open_and_upcoming",
            "calls_found": len(filtered_calls),
            "calls": [
                {
                    "call_id": c.get("topic_code", ""),  # topic_code is the actual call ID
                    "programme": c.get("programme"),
                    "opening_date": c.get("opening_date"),
                    "second_stage_deadline": c.get("second_stage_deadline"),
                    "title": c.get("title", ""),
                    "deadline": c.get("deadline", ""),
                    "type": c.get("action_type", ""),
                    "cluster": c.get("cluster", ""),
                    "budget": c.get("budget", ""),
                    "scope": c.get("scope", "") or c.get("description", ""),
                    "expected_outcome": c.get("expected_outcome", ""),
                    "status": c.get("status", "open"),
                    "url": c.get("url", ""),
                    "work_programme": c.get("work_programme", ""),
                    "call_year": c.get("call_year", ""),
                }
                for c in filtered_calls[:15]
            ],
        }
    except Exception as e:
        logger.error(f"Funding calls search error: {e}")
        return {"success": False, "error": str(e), "calls": [], "calls_found": 0}


async def get_call_details_execute(call_id: str) -> dict[str, Any]:
    """
    Get details for a specific call.

    Uses a multi-fallback strategy to find call details:
    1. Try dedicated get_call_details method (includes API enrichment)
    2. Fallback: search for call with keyword search (including closed calls)
    3. Fallback: search with base call identifier (split by "-")
    4. Last resort: try direct EU Portal API fetch via CallEnrichmentService
    5. If all fail: find similar calls to suggest

    Args:
        call_id: The call/topic identifier (e.g., HORIZON-CL5-2026-02-D3-01).

    Returns:
        Dict with call details or error/suggestion message.
    """
    try:
        if not call_id:
            return {"error": "call_id is required"}

        logger.info(f"Getting call details for: {call_id}")

        from ..local_call_search_service import LocalCallSearchService

        call_service = LocalCallSearchService()

        # First try the dedicated get_call_details method (includes API enrichment)
        call_details = call_service.get_call_details(call_id)

        # Check if we got valid data (not just empty dict)
        if call_details and (call_details.get("topic_code") or call_details.get("title")):
            logger.info(
                f"Got call details: {call_details.get('topic_code')} - {call_details.get('title', '')[:50]}"
            )
            return {
                "call_id": call_details.get("topic_code"),
                "title": call_details.get("title"),
                "description": call_details.get("scope") or call_details.get("description", ""),
                "expected_outcome": call_details.get("expected_outcome", ""),
                "deadline": (
                    str(call_details.get("deadline")) if call_details.get("deadline") else None
                ),
                "opening_date": call_details.get("opening_date"),
                "second_stage_deadline": call_details.get("second_stage_deadline"),
                "type": call_details.get("action_type"),
                "cluster": call_details.get("cluster"),
                "budget": call_details.get("budget"),
                "status": call_details.get("status"),
                "url": call_details.get("url") or call_details.get("portal_url"),
            }

        # Fallback: Search for the call using keywords
        # Include closed calls since user is looking for a specific call ID
        logger.info(f"Fallback: Searching for {call_id}...")
        results = call_service.search_calls(
            query=call_id,
            num_results=10,
            include_closed=True,  # Include closed calls when looking up specific call IDs
        )

        calls = results.get("calls", [])
        logger.info(f"Search returned {len(calls)} results")

        for call in calls:
            # Check both topic_code and call_id fields
            topic_code = call.get("topic_code", "") or ""
            if call_id.upper() in topic_code.upper():
                logger.info(f"Found matching call: {topic_code}")
                return {
                    "call_id": topic_code,
                    "title": call.get("title"),
                    "description": call.get("scope") or call.get("description", ""),
                    "expected_outcome": call.get("expected_outcome", ""),
                    "deadline": str(call.get("deadline")) if call.get("deadline") else None,
                    "type": call.get("action_type"),
                    "cluster": call.get("cluster"),
                    "budget": call.get("budget"),
                    "status": call.get("status"),
                    "url": call.get("url") or call.get("portal_url"),
                }

        # If still not found, try searching with just the base call identifier
        # e.g., HORIZON-CL5-2026-02-D4-01 -> search for "HORIZON-CL5-2026"
        if "-" in call_id:
            parts = call_id.split("-")
            if len(parts) >= 4:
                base_call = "-".join(parts[:4])  # e.g., HORIZON-CL5-2026-02
                logger.info(f"Trying base call search: {base_call}")
                results = call_service.search_calls(
                    query=base_call, num_results=15, include_closed=True
                )
                calls = results.get("calls", [])
                for call in calls:
                    topic_code = call.get("topic_code", "") or ""
                    if (
                        call_id.upper() in topic_code.upper()
                        or topic_code.upper() in call_id.upper()
                    ):
                        logger.info(f"Found via base search: {topic_code}")
                        return {
                            "call_id": topic_code,
                            "title": call.get("title"),
                            "description": call.get("scope") or call.get("description", ""),
                            "expected_outcome": call.get("expected_outcome", ""),
                            "deadline": (
                                str(call.get("deadline")) if call.get("deadline") else None
                            ),
                            "type": call.get("action_type"),
                            "cluster": call.get("cluster"),
                            "budget": call.get("budget"),
                            "status": call.get("status"),
                            "url": call.get("url") or call.get("portal_url"),
                        }

        logger.warning(f"No details found for {call_id} in local searches")

        # Last resort: Try direct API fetch via enrichment service
        logger.info(f"Trying direct EU Portal API fetch for {call_id}...")
        try:
            from app.core.config import settings

            from ..call_enrichment_service import CallEnrichmentService

            enrichment = CallEnrichmentService(settings.database_url)
            api_result = enrichment.get_call_details(call_id, force_refresh=True)
            if api_result and (api_result.get("topic_code") or api_result.get("title")):
                logger.info(f"Found {call_id} via direct API fetch!")
                return {
                    "call_id": api_result.get("topic_code") or call_id,
                    "title": api_result.get("title"),
                    "description": api_result.get("scope") or api_result.get("description", ""),
                    "expected_outcome": api_result.get("expected_outcome", ""),
                    "deadline": (
                        str(api_result.get("deadline")) if api_result.get("deadline") else None
                    ),
                    "type": api_result.get("action_type"),
                    "cluster": api_result.get("cluster"),
                    "budget": api_result.get("budget") or api_result.get("budget_total"),
                    "status": api_result.get("status"),
                    "url": api_result.get("portal_url")
                    or f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}",
                }
            else:
                logger.info(f"Direct API fetch returned no valid data for {call_id}")
        except Exception as api_err:
            logger.warning(f"Direct API fetch failed: {api_err}")

        # Try to find similar calls to suggest
        similar_calls = []
        if "-" in call_id:
            parts = call_id.split("-")
            # Search for calls in the same cluster/year
            if len(parts) >= 3:
                search_term = "-".join(parts[:3])  # e.g., HORIZON-CL5-2026
                results = call_service.search_calls(
                    query=search_term, num_results=5, include_closed=True
                )
                for call in results.get("calls", [])[:5]:
                    topic_code = call.get("topic_code", "")
                    title = call.get("title", "")
                    if topic_code and title:
                        similar_calls.append(f"- {topic_code}: {title[:60]}...")

        if similar_calls:
            suggestions = "\n".join(similar_calls)
            return {
                "message": f"Call ID '{call_id}' was not found. This may be an invalid or incomplete call ID.\n\n**Similar calls you might be looking for:**\n{suggestions}\n\nYou can also check the EU Portal directly.",
                "similar_calls": similar_calls,
            }
        else:
            return {
                "message": f"No details found for {call_id}. This call ID may be invalid or not yet in our database. Please verify the call ID format (e.g., HORIZON-CL5-2026-02-D3-01) and try again, or check the EU Funding & Tenders Portal directly."
            }
    except Exception as e:
        logger.error(f"Get call details error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
