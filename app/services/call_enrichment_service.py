"""
Call Enrichment Service

Fetches complete call details from the EU Funding & Tenders Portal API
when local data is incomplete. Caches results for future queries.

Strategy:
1. Check local `funding_calls` table first
2. If data is incomplete (missing scope, budget, deadline), fetch from API
3. Cache the enriched data for next time

Rate Limit Handling:
- Detects HTTP 429 (Too Many Requests) responses
- Respects Retry-After header when present
- Exponential backoff with jitter for retries
- In-memory cache to reduce API calls
- Graceful degradation to cached/local data when rate limited
"""

import logging
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

from ..core.config import settings

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when EU Portal API returns 429 Too Many Requests."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class APIUnavailableError(Exception):
    """Raised when EU Portal API is unavailable (5xx errors)."""

    pass


class CallEnrichmentService:
    """
    Service to enrich call data from the EU Portal API.

    Fetches missing information (scope, budget, deadlines) and caches it locally.

    Features:
    - In-memory cache with TTL to reduce API calls
    - Rate limit detection and exponential backoff
    - Graceful degradation to cached/local data when rate limited
    """

    # Class-level in-memory cache for API responses
    _api_cache: dict[str, tuple[dict[str, Any], datetime]] = {}
    _rate_limited_until: datetime | None = None

    def __init__(self, db_url: str):
        """Initialize with database connection."""
        self.db_url = db_url
        self._client = None
        logger.info("✅ CallEnrichmentService initialized")

    @property
    def client(self):
        """Lazy-load HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    @classmethod
    def is_rate_limited(cls) -> bool:
        """Check if we're currently rate limited."""
        if cls._rate_limited_until is None:
            return False
        if datetime.now() >= cls._rate_limited_until:
            cls._rate_limited_until = None
            return False
        return True

    @classmethod
    def set_rate_limited(cls, retry_after: int | None = None):
        """Mark the API as rate limited."""
        wait_time = retry_after or 60  # Default to 60 seconds if no retry-after
        cls._rate_limited_until = datetime.now() + timedelta(seconds=wait_time)
        logger.warning(f"⏳ EU Portal API rate limited. Will retry after {wait_time}s")

    @classmethod
    def get_cached(cls, topic_code: str) -> dict[str, Any] | None:
        """Get cached API response if still valid."""
        cache_key = topic_code.upper()
        if cache_key in cls._api_cache:
            data, cached_at = cls._api_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=settings.call_enrichment_cache_ttl):
                logger.info(f"📦 Using cached API response for {topic_code}")
                return data
            else:
                # Cache expired, remove it
                del cls._api_cache[cache_key]
        return None

    @classmethod
    def set_cached(cls, topic_code: str, data: dict[str, Any]):
        """Cache an API response."""
        cache_key = topic_code.upper()
        cls._api_cache[cache_key] = (data, datetime.now())
        logger.debug(f"📦 Cached API response for {topic_code}")

    @classmethod
    def clear_cache(cls):
        """Clear the API response cache."""
        cls._api_cache.clear()
        cls._rate_limited_until = None
        logger.info("🗑️ API cache cleared")

    def get_call_details(
        self, topic_code: str, force_refresh: bool = False
    ) -> dict[str, Any] | None:
        """
        Get complete call details, fetching from API if needed.

        Implements graceful degradation when rate limited:
        1. Check in-memory cache first
        2. If rate limited, use cached/local data immediately
        3. Otherwise try API with retry logic
        4. Fall back to local data on any failure

        Args:
            topic_code: The call identifier (e.g., HORIZON-CL5-2025-D3-01)
            force_refresh: If True, always fetch from API even if local data exists

        Returns:
            Complete call details dictionary with optional 'rate_limited' flag
        """
        topic_code = topic_code.upper().strip()

        # Step 0: Check in-memory API cache first (fastest)
        cached_data = self.get_cached(topic_code)
        if cached_data and not force_refresh:
            logger.info(f"📦 Returning cached API data for {topic_code}")
            # If we're rate limited, add flag to indicate limitation
            if self.is_rate_limited():
                cached_data = dict(cached_data)  # Copy to avoid mutating cache
                cached_data["_rate_limited"] = True
                cached_data["_rate_limited_message"] = (
                    "EU Portal API temporarily unavailable. Using cached data."
                )
            return cached_data

        # Step 1: Check local database
        local_data = self._get_local_call(topic_code)
        if not force_refresh and local_data and self._is_complete(local_data):
            logger.info(f"✅ Found complete local data for {topic_code}")
            # If we're rate limited, add flag to indicate limitation
            if self.is_rate_limited():
                local_data["_rate_limited"] = True
                local_data["_rate_limited_message"] = (
                    "EU Portal API temporarily unavailable. Using cached data."
                )
            return local_data

        # Step 2: Check if we're rate limited
        if self.is_rate_limited():
            logger.warning(f"⏳ Rate limited - using cached/local data for {topic_code}")
            # Return local data with rate_limited flag
            if local_data:
                local_data["_rate_limited"] = True
                local_data["_rate_limited_message"] = (
                    "EU Portal API temporarily unavailable. Using cached data."
                )
                return local_data
            # Try to return cached data even if expired
            cache_key = topic_code.upper()
            if cache_key in self._api_cache:
                data, _ = self._api_cache[cache_key]
                data["_rate_limited"] = True
                data["_rate_limited_message"] = (
                    "EU Portal API temporarily unavailable. Using cached data."
                )
                return data
            return None

        # Step 3: Fetch from EU Portal API with retry logic
        logger.info(f"🌐 Fetching {topic_code} from EU Portal API...")
        api_data = self._fetch_from_api_with_retry(topic_code)

        if api_data:
            # Check if we got rate limited during fetch
            if api_data.get("_rate_limited"):
                # Still cache and return what we have
                pass
            else:
                # Cache successful API response (both in-memory and database)
                self.set_cached(topic_code, api_data)
                self._cache_call(topic_code, api_data)
                logger.info(f"✅ Cached enriched data for {topic_code}")
            return api_data

        # Fall back to local data if API failed
        if local_data:
            logger.warning(f"⚠️ API fetch failed, using local data for {topic_code}")
            return local_data

        return None

    def _fetch_from_api_with_retry(self, topic_code: str) -> dict[str, Any] | None:
        """
        Fetch from API with exponential backoff retry for rate limits.

        Args:
            topic_code: The call identifier

        Returns:
            API data or None if all retries failed
        """
        for attempt in range(settings.call_enrichment_max_retries + 1):
            try:
                return self._fetch_from_api(topic_code)

            except RateLimitError as e:
                self.set_rate_limited(e.retry_after)

                # Don't retry on last attempt
                if attempt == settings.call_enrichment_max_retries:
                    logger.error(
                        f"❌ Rate limited after {settings.call_enrichment_max_retries + 1} attempts for {topic_code}"
                    )
                    # Return local data with rate limit flag
                    local_data = self._get_local_call(topic_code)
                    if local_data:
                        local_data["_rate_limited"] = True
                        local_data["_rate_limited_message"] = f"EU Portal API rate limited. {e}"
                        return local_data
                    return None

                # Calculate delay with jitter
                delay = min(
                    settings.call_enrichment_base_delay
                    * (settings.call_enrichment_exponential_base**attempt),
                    settings.call_enrichment_max_delay,
                )
                delay = delay * (0.5 + random.random())  # Add jitter

                # Use Retry-After if provided
                if e.retry_after:
                    delay = max(delay, e.retry_after)

                logger.warning(
                    f"⏳ Rate limited (attempt {attempt + 1}/{settings.call_enrichment_max_retries + 1}), "
                    f"retrying in {delay:.1f}s"
                )
                time.sleep(delay)

            except APIUnavailableError as e:
                logger.warning(f"⚠️ API unavailable: {e}")

                if attempt == settings.call_enrichment_max_retries:
                    # Return local data as fallback
                    local_data = self._get_local_call(topic_code)
                    if local_data:
                        local_data["_api_unavailable"] = True
                        local_data["_api_unavailable_message"] = (
                            f"EU Portal API unavailable. Using cached data. {e}"
                        )
                        return local_data
                    return None

                # Shorter delay for 5xx errors
                delay = min(
                    settings.call_enrichment_base_delay
                    * (settings.call_enrichment_exponential_base**attempt),
                    settings.call_enrichment_max_delay / 2,
                )
                delay = delay * (0.5 + random.random())
                logger.warning(f"⏳ Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"❌ Unexpected error fetching {topic_code}: {e}")
                # Don't retry on unexpected errors
                return None

        return None

    def enrich_search_results(self, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich a list of search results with complete data.

        Only fetches from API for calls that are missing critical info.
        """
        enriched = []

        for call in calls:
            topic_code = call.get("topic_code")
            if not topic_code:
                enriched.append(call)
                continue

            # Check if this call needs enrichment
            if self._needs_enrichment(call):
                full_data = self.get_call_details(topic_code)
                if full_data:
                    # Merge enriched data
                    call = {**call, **full_data}

            enriched.append(call)

        return enriched

    def _is_complete(self, call: dict[str, Any]) -> bool:
        """Check if call has all important fields including deadline."""
        required_fields = ["scope", "title"]

        for field in required_fields:
            if not call.get(field) or len(str(call[field])) < 20:
                return False

        # Deadline is required for a call to be considered complete
        if not call.get("deadline"):
            return False

        return True

    def _needs_enrichment(self, call: dict[str, Any]) -> bool:
        """Check if a call needs to be enriched."""
        # Missing or very short scope
        scope = call.get("scope") or call.get("description") or ""
        if len(scope) < 50:
            return True

        # Missing deadline - ALWAYS need to enrich to get deadline
        if not call.get("deadline"):
            return True

        # Missing status
        if not call.get("status"):
            return True

        return False

    def _get_local_call(self, topic_code: str) -> dict[str, Any] | None:
        """Get call from local database."""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT * FROM funding_calls
                WHERE topic_code = %s
            """,
                (topic_code,),
            )

            result = cursor.fetchone()
            conn.close()

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"Database error: {e}")
            return None

    def _fetch_from_api(self, topic_code: str) -> dict[str, Any] | None:
        """
        Fetch call details from EU Portal API.

        First tries the direct topic details endpoint, then falls back to search API.
        """
        # Try direct topic details endpoint first (simpler and more reliable)
        direct_result = self._fetch_direct_topic_details(topic_code)
        if direct_result:
            return direct_result

        # Fall back to search API
        return self._fetch_via_search_api(topic_code)

    def _fetch_direct_topic_details(self, topic_code: str) -> dict[str, Any] | None:
        """
        Fetch topic details directly from the EU Portal topic details JSON endpoint.

        This endpoint returns complete details for a specific topic by ID.

        Raises:
            RateLimitError: If API returns 429 (Too Many Requests)
            APIUnavailableError: If API returns 5xx errors
        """
        try:
            # The EU Portal has a direct JSON endpoint for topic details
            # Format: https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails/{topic_code}.json
            # IMPORTANT: The endpoint requires LOWERCASE topic codes
            url = f"{settings.eu_portal_topic_details_url}/{topic_code.lower()}.json"
            logger.info(f"📡 Fetching direct topic details from: {url}")

            response = self.client.get(url)

            # Check for rate limiting (429)
            if response.status_code == 429:
                retry_after = None
                if "Retry-After" in response.headers:
                    try:
                        retry_after = int(response.headers["Retry-After"])
                    except (ValueError, TypeError):
                        pass
                raise RateLimitError(
                    f"EU Portal API rate limited (429) for {topic_code}",
                    retry_after=retry_after,
                )

            # Check for server errors (5xx)
            if 500 <= response.status_code < 600:
                raise APIUnavailableError(
                    f"EU Portal API unavailable ({response.status_code}) for {topic_code}"
                )

            if response.status_code == 200:
                data = response.json()
                topic_data = data.get("TopicDetails", {})

                if topic_data:
                    logger.info(f"✅ Got direct topic details for {topic_code}")

                    # Extract deadline and status from 'actions' field (primary source)
                    deadline = None
                    status = "unknown"
                    actions = topic_data.get("actions", [])
                    if actions and isinstance(actions, list) and len(actions) > 0:
                        action = actions[0]

                        # Get deadline from deadlineDates (Unix timestamp in milliseconds)
                        deadline_dates = action.get("deadlineDates", [])
                        if deadline_dates and len(deadline_dates) > 0:
                            try:
                                # Parse Unix timestamp (milliseconds)
                                timestamp_ms = int(deadline_dates[0])
                                deadline = datetime.fromtimestamp(timestamp_ms / 1000).date()
                                logger.debug(f"Extracted deadline from actions: {deadline}")
                            except Exception as e:
                                logger.debug(f"Could not parse deadline timestamp: {e}")

                        # Get status from action.status
                        status_info = action.get("status", {})
                        if isinstance(status_info, dict):
                            status_abbr = status_info.get("abbreviation", "").lower()
                            if "open" in status_abbr:
                                status = "open"
                            elif "closed" in status_abbr:
                                status = "closed"
                            elif "forthcoming" in status_abbr or "upcoming" in status_abbr:
                                status = "upcoming"

                    # Fallback to deadlineModel if actions didn't have deadline
                    if not deadline:
                        deadline_model = topic_data.get("deadlineModel", [])
                        if (
                            deadline_model
                            and isinstance(deadline_model, list)
                            and len(deadline_model) > 0
                        ):
                            deadline_str = deadline_model[0].get("deadlineDate", "")
                            if deadline_str:
                                try:
                                    if "T" in deadline_str:
                                        deadline = datetime.fromisoformat(
                                            deadline_str.replace("Z", "+00:00")
                                        ).date()
                                    else:
                                        deadline = datetime.strptime(
                                            deadline_str, "%Y-%m-%d"
                                        ).date()
                                except Exception as e:
                                    logger.debug(
                                        f"Could not parse deadline from deadlineModel: {e}"
                                    )

                    # Fallback to statusOfTopic if actions didn't have status
                    if status == "unknown":
                        status_data = topic_data.get("statusOfTopic", {})
                        status_abbr = (
                            status_data.get("abbreviation", "").lower()
                            if isinstance(status_data, dict)
                            else str(status_data).lower()
                        )
                        if "open" in status_abbr:
                            status = "open"
                        elif "closed" in status_abbr:
                            status = "closed"
                        elif "forthcoming" in status_abbr or "upcoming" in status_abbr:
                            status = "upcoming"
                        else:
                            status = "closed"  # Default to closed for past calls

                    # Extract budget
                    budget = None
                    budget_data = topic_data.get("budgetOverviewModel", {})
                    if budget_data:
                        budget = budget_data.get("budgetTopicActionValue")

                    # Extract action type
                    action_type_data = topic_data.get("typeOfMGA", [])
                    action_type = ""
                    if (
                        action_type_data
                        and isinstance(action_type_data, list)
                        and len(action_type_data) > 0
                    ):
                        action_type = action_type_data[0].get("abbreviation", "")

                    return {
                        "topic_code": topic_data.get("identifier", topic_code).upper(),
                        "title": topic_data.get("title", ""),
                        "scope": topic_data.get("description", ""),
                        "expected_outcome": topic_data.get("expectedImpact", ""),
                        "deadline": deadline,
                        "status": status,
                        "action_type": action_type,
                        "budget": budget,
                        "budget_total": Decimal(str(budget)) if budget else None,
                        "call_identifier": topic_data.get("callIdentifier"),
                        "portal_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_code.lower()}",
                        "enriched_from_api": True,
                        "enriched_at": datetime.now().isoformat(),
                    }

            logger.info(
                f"Direct topic details endpoint returned {response.status_code} for {topic_code}"
            )
            return None

        except (RateLimitError, APIUnavailableError):
            # Re-raise our custom exceptions for retry handling
            raise
        except Exception as e:
            logger.warning(f"Direct topic details fetch failed for {topic_code}: {e}")
            return None

    def _fetch_via_search_api(self, topic_code: str) -> dict[str, Any] | None:
        """
        Fetch call details via the EU Portal search API.

        Uses multipart POST approach.

        Raises:
            RateLimitError: If API returns 429 (Too Many Requests)
            APIUnavailableError: If API returns 5xx errors
        """
        try:
            import json

            # Build search query - include all statuses to find the call
            search_query = {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "must": [
                                    {"terms": {"type": ["1", "2", "8"]}},
                                    # Include all statuses to find any call
                                    {"terms": {"status": ["31094501", "31094502", "31094503"]}},
                                ]
                            }
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "phrase": {
                                            "query": topic_code,
                                            "field": "identifier",
                                            "phraseSlop": 0,
                                            "boost": 1100,
                                        }
                                    },
                                    {
                                        "phrase": {
                                            "query": topic_code,
                                            "field": "title",
                                            "phraseSlop": 1,
                                            "boost": 500,
                                        }
                                    },
                                ]
                            }
                        },
                    ]
                }
            }

            # Prepare form data
            form_data = {
                "apiKey": "SEDIA",
                "text": topic_code,  # Use exact topic code
                "pageSize": "10",
                "pageNumber": "1",
            }

            files = {
                "query": (None, json.dumps(search_query), "application/json"),
                "sort": (
                    None,
                    json.dumps({"order": "DESC", "field": "relevance"}),
                    "application/json",
                ),
            }

            response = self.client.post(settings.eu_portal_base_url, data=form_data, files=files)

            # Check for rate limiting (429)
            if response.status_code == 429:
                retry_after = None
                if "Retry-After" in response.headers:
                    try:
                        retry_after = int(response.headers["Retry-After"])
                    except (ValueError, TypeError):
                        pass
                raise RateLimitError(
                    f"EU Portal Search API rate limited (429) for {topic_code}",
                    retry_after=retry_after,
                )

            # Check for server errors (5xx)
            if 500 <= response.status_code < 600:
                raise APIUnavailableError(
                    f"EU Portal Search API unavailable ({response.status_code}) for {topic_code}"
                )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                logger.info(f"API returned {len(results)} results for {topic_code}")

                # Find matching topic - try exact match first, then partial
                for result in results:
                    metadata = result.get("metadata", {})
                    # metadata values are lists, get first item
                    identifiers = metadata.get("identifier", [])
                    if identifiers:
                        result_id = (
                            identifiers[0].upper()
                            if isinstance(identifiers, list)
                            else str(identifiers).upper()
                        )
                        # Exact match
                        if result_id == topic_code.upper():
                            logger.info(f"✅ Found exact match for {topic_code}")
                            return self._parse_search_result(result, topic_code)

                # Try partial match (topic_code contained in identifier or vice versa)
                for result in results:
                    metadata = result.get("metadata", {})
                    identifiers = metadata.get("identifier", [])
                    if identifiers:
                        result_id = (
                            identifiers[0].upper()
                            if isinstance(identifiers, list)
                            else str(identifiers).upper()
                        )
                        if topic_code.upper() in result_id or result_id in topic_code.upper():
                            logger.info(f"✅ Found partial match: {result_id} for {topic_code}")
                            return self._parse_search_result(result, topic_code)

                # If no match but we have results, use the first one as fallback
                if results:
                    first_id = results[0].get("metadata", {}).get("identifier", ["unknown"])[0]
                    logger.info(
                        f"⚠️ No exact match for {topic_code}, using closest result: {first_id}"
                    )
                    return self._parse_search_result(results[0], topic_code)

            logger.warning(f"API returned status {response.status_code} for {topic_code}")
            return None

        except (RateLimitError, APIUnavailableError):
            # Re-raise our custom exceptions for retry handling
            raise
        except Exception as e:
            logger.error(f"API fetch error for {topic_code}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _parse_api_response(self, data: dict[str, Any], topic_code: str) -> dict[str, Any]:
        """Parse the topic details API response."""
        # The API response structure varies, handle different formats
        topic_data = data.get("topicDetails", data)

        # Extract deadline
        deadline = None
        deadlines = topic_data.get("deadlineDates", [])
        if deadlines:
            deadline_str = (
                deadlines[0] if isinstance(deadlines[0], str) else deadlines[0].get("date")
            )
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00")).date()
                except Exception:
                    pass

        # Extract budget
        budget = None
        budget_info = topic_data.get("budget", {})
        if isinstance(budget_info, dict):
            budget = budget_info.get("budgetTopicActionValue")
        elif isinstance(budget_info, int | float):
            budget = budget_info

        # Determine status
        status_code = topic_data.get("status", {})
        if isinstance(status_code, dict):
            status_str = status_code.get("abbreviation", "").lower()
        else:
            status_str = str(status_code).lower()

        if "open" in status_str:
            status = "open"
        elif "closed" in status_str:
            status = "closed"
        elif "forthcoming" in status_str or "upcoming" in status_str:
            status = "upcoming"
        else:
            status = "unknown"

        return {
            "topic_code": topic_code,
            "title": topic_data.get("title", topic_code),
            "scope": topic_data.get("description", ""),
            "expected_outcome": topic_data.get("expectedImpact", ""),
            "deadline": deadline,
            "status": status,
            "budget_total": Decimal(str(budget)) if budget else None,
            "action_type": topic_data.get("actionType", {}).get("abbreviation"),
            "call_identifier": topic_data.get("callIdentifier"),
            "portal_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_code}",
            "enriched_from_api": True,
            "enriched_at": datetime.now().isoformat(),
        }

    def _parse_search_result(self, result: dict[str, Any], topic_code: str) -> dict[str, Any]:
        """Parse a search API result."""
        # Metadata is a dict where values are lists
        metadata = result.get("metadata", {})

        def get_first(key: str, default: str = "") -> str:
            """Get first value from metadata list."""
            val = metadata.get(key, [default])
            if isinstance(val, list):
                return val[0] if val else default
            return val or default

        # Extract fields - metadata values are lists, take first item
        identifier = get_first("identifier", topic_code)
        title = get_first("title") or get_first("callTitle") or result.get("title", topic_code)
        description = (
            get_first("description") or get_first("esSummary") or result.get("summary", "")
        )
        deadline_str = get_first("deadlineDate", "")
        status_code = get_first("status", "")

        # Parse deadline
        deadline = None
        if deadline_str:
            try:
                # Handle ISO format: 2024-10-01T22:00:00.000+0000
                if "T" in deadline_str:
                    # Remove timezone for simpler parsing
                    clean_date = deadline_str.split("T")[0]
                    deadline = datetime.strptime(clean_date, "%Y-%m-%d").date()
                else:
                    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except Exception as e:
                logger.debug(f"Could not parse deadline '{deadline_str}': {e}")

        # Map status code to string
        status_map = {
            "31094501": "upcoming",  # Forthcoming
            "31094502": "open",  # Open
            "31094503": "closed",  # Closed
        }
        status = status_map.get(status_code, "unknown")

        # Map typeOfMGAs numeric IDs to action type abbreviations
        # These IDs come from the EU Portal search API metadata
        action_type_map = {
            "43027843": "RIA",  # Research and Innovation Action
            "43027844": "IA",  # Innovation Action
            "43027845": "CSA",  # Coordination and Support Action
            "43027846": "LUMP-SUM",  # Lump Sum
            "43027847": "PCP",  # Pre-Commercial Procurement
            "43027848": "PPI",  # Public Procurement of Innovation
            "43027849": "LUMP-SUM",  # Lump Sum (alternative ID)
            "43027850": "COFUND",  # Co-fund
        }
        raw_action_type = get_first("typeOfMGAs")
        action_type = action_type_map.get(
            raw_action_type, raw_action_type if not raw_action_type.isdigit() else ""
        )

        logger.info(
            f"✅ Parsed API result: {identifier} - {title[:50] if title else 'No title'}..."
        )

        return {
            "topic_code": identifier.upper() if identifier else topic_code.upper(),
            "title": title,
            "scope": description,
            "expected_outcome": "",  # Not in search results
            "deadline": deadline,
            "status": status,
            "action_type": action_type,
            "call_identifier": get_first("callIdentifier"),
            "portal_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{identifier or topic_code}",
            "enriched_from_api": True,
            "enriched_at": datetime.now().isoformat(),
        }

    def _cache_call(self, topic_code: str, data: dict[str, Any]) -> bool:
        """Cache enriched call data to database."""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()

            # Upsert the call data
            cursor.execute(
                """
                INSERT INTO funding_calls (
                    programme, topic_code, title, scope, expected_outcome,
                    deadline, status, budget_total, action_type,
                    call_identifier, portal_url, metadata
                ) VALUES (
                    'horizon_europe', %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s::jsonb
                )
                ON CONFLICT (topic_code) DO UPDATE SET
                    title = COALESCE(EXCLUDED.title, funding_calls.title),
                    scope = COALESCE(EXCLUDED.scope, funding_calls.scope),
                    expected_outcome = COALESCE(EXCLUDED.expected_outcome, funding_calls.expected_outcome),
                    deadline = COALESCE(EXCLUDED.deadline, funding_calls.deadline),
                    status = COALESCE(EXCLUDED.status, funding_calls.status),
                    budget_total = COALESCE(EXCLUDED.budget_total, funding_calls.budget_total),
                    action_type = COALESCE(EXCLUDED.action_type, funding_calls.action_type),
                    portal_url = COALESCE(EXCLUDED.portal_url, funding_calls.portal_url),
                    metadata = funding_calls.metadata || EXCLUDED.metadata,
                    updated_at = NOW()
            """,
                (
                    topic_code,
                    data.get("title"),
                    data.get("scope"),
                    data.get("expected_outcome"),
                    data.get("deadline"),
                    data.get("status", "unknown"),
                    float(data["budget_total"]) if data.get("budget_total") else None,
                    data.get("action_type"),
                    data.get("call_identifier"),
                    data.get("portal_url"),
                    '{"enriched_from_api": true}',
                ),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Cache error for {topic_code}: {e}")
            return False

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
