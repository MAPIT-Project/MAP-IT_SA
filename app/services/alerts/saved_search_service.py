"""
Saved Search Service.

Manages saved searches with alerts for:
- Funding calls (open/upcoming)
- Projects (new matches)
- Partner discovery (new organizations)

Features:
- Store search configurations in PostgreSQL
- Celery periodic tasks for checking new results
- Email and webhook notifications
- Result caching to avoid duplicate alerts
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


class SearchType(str, Enum):
    """Types of saved searches."""
    CALLS = "calls"
    PROJECTS = "projects"
    PARTNERS = "partners"


class AlertFrequency(str, Enum):
    """Alert notification frequency."""
    IMMEDIATE = "immediate"  # As soon as new results found
    DAILY = "daily"          # Daily digest
    WEEKLY = "weekly"        # Weekly digest


class AlertChannel(str, Enum):
    """Notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    BOTH = "both"


@dataclass
class AlertConfig:
    """Alert configuration for a saved search."""
    enabled: bool = False
    frequency: AlertFrequency = AlertFrequency.DAILY
    channel: AlertChannel = AlertChannel.EMAIL
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    min_results_to_alert: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "frequency": self.frequency.value,
            "channel": self.channel.value,
            "email": self.email,
            "webhook_url": self.webhook_url,
            "webhook_secret": self.webhook_secret,
            "min_results_to_alert": self.min_results_to_alert,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertConfig":
        return cls(
            enabled=data.get("enabled", False),
            frequency=AlertFrequency(data.get("frequency", "daily")),
            channel=AlertChannel(data.get("channel", "email")),
            email=data.get("email"),
            webhook_url=data.get("webhook_url"),
            webhook_secret=data.get("webhook_secret"),
            min_results_to_alert=data.get("min_results_to_alert", 1),
        )


@dataclass
class SavedSearch:
    """A saved search configuration."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    search_type: SearchType
    parameters: Dict[str, Any]
    alert_config: AlertConfig
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime] = None
    last_result_hash: Optional[str] = None
    is_active: bool = True
    run_count: int = 0
    alert_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "search_type": self.search_type.value,
            "parameters": self.parameters,
            "alert_config": self.alert_config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_result_hash": self.last_result_hash,
            "is_active": self.is_active,
            "run_count": self.run_count,
            "alert_count": self.alert_count,
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "SavedSearch":
        """Create SavedSearch from database row."""
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row.get("description"),
            search_type=SearchType(row["search_type"]),
            parameters=row["parameters"] if isinstance(row["parameters"], dict) else json.loads(row["parameters"]),
            alert_config=AlertConfig.from_dict(
                row["alert_config"] if isinstance(row["alert_config"], dict) else json.loads(row["alert_config"])
            ),
            created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(row["created_at"]),
            updated_at=row["updated_at"] if isinstance(row["updated_at"], datetime) else datetime.fromisoformat(row["updated_at"]),
            last_run=row.get("last_run"),
            last_result_hash=row.get("last_result_hash"),
            is_active=row.get("is_active", True),
            run_count=row.get("run_count", 0),
            alert_count=row.get("alert_count", 0),
        )


@dataclass
class SearchResult:
    """Result from running a saved search."""
    search_id: str
    results: List[Dict[str, Any]]
    result_count: int
    new_results: List[Dict[str, Any]]
    new_count: int
    result_hash: str
    execution_time_ms: float
    executed_at: datetime


class SavedSearchService:
    """Service for managing saved searches and alerts."""

    def __init__(self, db_pool=None, redis_client=None):
        """
        Initialize the service.

        Args:
            db_pool: PostgreSQL connection pool
            redis_client: Redis client for caching
        """
        self.db_pool = db_pool
        self.redis = redis_client
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for webhooks."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create_search(
        self,
        user_id: str,
        name: str,
        search_type: SearchType,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        alert_config: Optional[AlertConfig] = None,
    ) -> SavedSearch:
        """
        Create a new saved search.

        Args:
            user_id: User ID
            name: Human-readable name
            search_type: Type of search (calls, projects, partners)
            parameters: Search parameters
            description: Optional description
            alert_config: Optional alert configuration

        Returns:
            Created SavedSearch
        """
        now = datetime.now(timezone.utc)
        search = SavedSearch(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            search_type=search_type,
            parameters=parameters,
            alert_config=alert_config or AlertConfig(),
            created_at=now,
            updated_at=now,
        )

        await self._save_to_db(search)
        logger.info(f"Created saved search: {search.id} for user {user_id}")

        return search

    async def get_search(self, search_id: str) -> Optional[SavedSearch]:
        """Get a saved search by ID."""
        if not self.db_pool:
            return None

        query = "SELECT * FROM saved_searches WHERE id = %s"

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (search_id,))
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return SavedSearch.from_db_row(dict(zip(columns, row)))
        return None

    async def get_user_searches(
        self,
        user_id: str,
        search_type: Optional[SearchType] = None,
        active_only: bool = True,
    ) -> List[SavedSearch]:
        """Get all saved searches for a user."""
        if not self.db_pool:
            return []

        query = "SELECT * FROM saved_searches WHERE user_id = %s"
        params = [user_id]

        if active_only:
            query += " AND is_active = true"

        if search_type:
            query += " AND search_type = %s"
            params.append(search_type.value)

        query += " ORDER BY updated_at DESC"

        searches = []
        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                for row in rows:
                    searches.append(SavedSearch.from_db_row(dict(zip(columns, row))))

        return searches

    async def update_search(
        self,
        search_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        alert_config: Optional[AlertConfig] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[SavedSearch]:
        """Update a saved search."""
        search = await self.get_search(search_id)
        if not search:
            return None

        if name is not None:
            search.name = name
        if description is not None:
            search.description = description
        if parameters is not None:
            search.parameters = parameters
        if alert_config is not None:
            search.alert_config = alert_config
        if is_active is not None:
            search.is_active = is_active

        search.updated_at = datetime.now(timezone.utc)

        await self._update_in_db(search)
        logger.info(f"Updated saved search: {search_id}")

        return search

    async def delete_search(self, search_id: str) -> bool:
        """Delete a saved search (soft delete by setting is_active=False)."""
        return await self.update_search(search_id, is_active=False) is not None

    async def hard_delete_search(self, search_id: str) -> bool:
        """Permanently delete a saved search."""
        if not self.db_pool:
            return False

        query = "DELETE FROM saved_searches WHERE id = %s"

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (search_id,))
                conn.commit()
                return cur.rowcount > 0

    # =========================================================================
    # Search Execution
    # =========================================================================

    async def run_search(self, search: SavedSearch) -> SearchResult:
        """
        Execute a saved search and return results.

        Args:
            search: The saved search to execute

        Returns:
            SearchResult with all results and new results
        """
        import time
        start_time = time.time()

        # Execute the search based on type
        if search.search_type == SearchType.CALLS:
            results = await self._search_calls(search.parameters)
        elif search.search_type == SearchType.PROJECTS:
            results = await self._search_projects(search.parameters)
        elif search.search_type == SearchType.PARTNERS:
            results = await self._search_partners(search.parameters)
        else:
            results = []

        execution_time = (time.time() - start_time) * 1000

        # Calculate result hash for change detection
        result_hash = self._calculate_result_hash(results)

        # Determine new results
        new_results = []
        if search.last_result_hash and search.last_result_hash != result_hash:
            new_results = await self._find_new_results(search, results)
        elif not search.last_result_hash:
            # First run - all results are new
            new_results = results

        search_result = SearchResult(
            search_id=search.id,
            results=results,
            result_count=len(results),
            new_results=new_results,
            new_count=len(new_results),
            result_hash=result_hash,
            execution_time_ms=execution_time,
            executed_at=datetime.now(timezone.utc),
        )

        # Update search metadata
        await self._update_search_run(search, search_result)

        return search_result

    async def _search_calls(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a call search."""
        try:
            from app.services.call_search.local_call_search_service import LocalCallSearchService
            service = LocalCallSearchService()
            result = await service.search(
                keywords=params.get("keywords", ""),
                status=params.get("status", "open"),
                cluster=params.get("cluster"),
                year=params.get("year"),
                limit=params.get("limit", 50),
            )
            return result.get("calls", [])
        except Exception as e:
            logger.error(f"Error searching calls: {e}")
            return []

    async def _search_projects(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a project search."""
        try:
            from app.services.project_search.local_project_search_service import LocalProjectSearchService
            service = LocalProjectSearchService()
            result = await service.search(
                keywords=params.get("keywords", ""),
                cluster=params.get("cluster"),
                country=params.get("country"),
                action_type=params.get("action_type"),
                limit=params.get("limit", 50),
            )
            return result.get("projects", [])
        except Exception as e:
            logger.error(f"Error searching projects: {e}")
            return []

    async def _search_partners(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a partner search."""
        try:
            from app.services.tools.partner_discovery import PartnerDiscoveryTool
            tool = PartnerDiscoveryTool()
            result = await tool.find_experienced_partners(
                keywords=params.get("keywords", ""),
                country=params.get("country"),
                org_type=params.get("org_type"),
                limit=params.get("limit", 50),
            )
            return result.get("experienced_partners", [])
        except Exception as e:
            logger.error(f"Error searching partners: {e}")
            return []

    def _calculate_result_hash(self, results: List[Dict[str, Any]]) -> str:
        """Calculate a hash of the result set for change detection."""
        # Extract IDs or unique identifiers
        ids = sorted([str(r.get("id") or r.get("call_id") or r.get("name") or "") for r in results])
        return hashlib.md5(json.dumps(ids).encode()).hexdigest()

    async def _find_new_results(
        self,
        search: SavedSearch,
        current_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find results that weren't in the previous run."""
        # Get previous result IDs from cache
        cache_key = f"saved_search:results:{search.id}"

        if self.redis:
            try:
                previous_ids_json = self.redis.get(cache_key)
                if previous_ids_json:
                    previous_ids = set(json.loads(previous_ids_json))
                else:
                    previous_ids = set()
            except Exception:
                previous_ids = set()
        else:
            previous_ids = set()

        # Find new results
        new_results = []
        current_ids = []

        for result in current_results:
            result_id = str(result.get("id") or result.get("call_id") or result.get("name") or "")
            current_ids.append(result_id)
            if result_id not in previous_ids:
                new_results.append(result)

        # Cache current IDs for next comparison
        if self.redis:
            try:
                self.redis.setex(
                    cache_key,
                    timedelta(days=30),  # Keep for 30 days
                    json.dumps(current_ids)
                )
            except Exception as e:
                logger.warning(f"Failed to cache result IDs: {e}")

        return new_results

    async def _update_search_run(self, search: SavedSearch, result: SearchResult):
        """Update search after execution."""
        if not self.db_pool:
            return

        query = """
            UPDATE saved_searches
            SET last_run = %s,
                last_result_hash = %s,
                run_count = run_count + 1,
                updated_at = %s
            WHERE id = %s
        """

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    result.executed_at,
                    result.result_hash,
                    datetime.now(timezone.utc),
                    search.id,
                ))
                conn.commit()

    # =========================================================================
    # Alert Processing
    # =========================================================================

    async def get_due_searches(self, frequency: Optional[AlertFrequency] = None) -> List[SavedSearch]:
        """
        Get searches that are due for checking based on their frequency.

        Args:
            frequency: Filter by frequency (None = all frequencies)

        Returns:
            List of searches due for execution
        """
        if not self.db_pool:
            return []

        now = datetime.now(timezone.utc)

        # Build query based on frequency
        query = """
            SELECT * FROM saved_searches
            WHERE is_active = true
            AND (alert_config->>'enabled')::boolean = true
        """
        params = []

        if frequency:
            query += " AND alert_config->>'frequency' = %s"
            params.append(frequency.value)

        # Add timing conditions
        query += """
            AND (
                last_run IS NULL
                OR (
                    (alert_config->>'frequency' = 'immediate' AND last_run < %s - INTERVAL '5 minutes')
                    OR (alert_config->>'frequency' = 'daily' AND last_run < %s - INTERVAL '23 hours')
                    OR (alert_config->>'frequency' = 'weekly' AND last_run < %s - INTERVAL '6 days 23 hours')
                )
            )
        """
        params.extend([now, now, now])

        searches = []
        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                for row in rows:
                    searches.append(SavedSearch.from_db_row(dict(zip(columns, row))))

        return searches

    async def process_alerts(self, frequency: Optional[AlertFrequency] = None) -> Dict[str, Any]:
        """
        Process all due saved search alerts.

        Args:
            frequency: Filter by frequency (None = all frequencies)

        Returns:
            Summary of processed alerts
        """
        searches = await self.get_due_searches(frequency)

        processed = 0
        alerts_sent = 0
        errors = 0

        for search in searches:
            try:
                result = await self.run_search(search)

                # Check if alert should be sent
                if (
                    result.new_count >= search.alert_config.min_results_to_alert
                    and search.alert_config.enabled
                ):
                    await self._send_alert(search, result)
                    alerts_sent += 1

                processed += 1

            except Exception as e:
                logger.error(f"Error processing search {search.id}: {e}")
                errors += 1

        return {
            "searches_processed": processed,
            "alerts_sent": alerts_sent,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _send_alert(self, search: SavedSearch, result: SearchResult):
        """Send alert notification for new results."""
        alert_config = search.alert_config

        # Prepare notification payload
        payload = self._prepare_alert_payload(search, result)

        try:
            if alert_config.channel in (AlertChannel.EMAIL, AlertChannel.BOTH):
                if alert_config.email:
                    await self._send_email_alert(alert_config.email, payload)

            if alert_config.channel in (AlertChannel.WEBHOOK, AlertChannel.BOTH):
                if alert_config.webhook_url:
                    await self._send_webhook_alert(
                        alert_config.webhook_url,
                        payload,
                        alert_config.webhook_secret,
                    )

            # Update alert count
            await self._increment_alert_count(search.id)

        except Exception as e:
            logger.error(f"Failed to send alert for search {search.id}: {e}")
            raise

    def _prepare_alert_payload(
        self,
        search: SavedSearch,
        result: SearchResult
    ) -> Dict[str, Any]:
        """Prepare the alert notification payload."""
        return {
            "event": f"saved_search.{search.search_type.value}.new_results",
            "search_id": search.id,
            "search_name": search.name,
            "search_type": search.search_type.value,
            "new_count": result.new_count,
            "total_count": result.result_count,
            "new_results": result.new_results[:10],  # Limit to first 10
            "executed_at": result.executed_at.isoformat(),
            "parameters": search.parameters,
        }

    async def _send_email_alert(self, email: str, payload: Dict[str, Any]):
        """
        Send email alert notification.

        Note: This is a placeholder. In production, integrate with
        an email service like SendGrid, AWS SES, or SMTP.
        """
        logger.info(f"Sending email alert to {email}: {payload['search_name']} - {payload['new_count']} new results")
        # TODO: Integrate with email service
        # Example:
        # await email_service.send(
        #     to=email,
        #     subject=f"New results for '{payload['search_name']}'",
        #     body=self._format_email_body(payload),
        # )

    async def _send_webhook_alert(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None,
    ):
        """Send webhook alert notification."""
        import hmac

        headers = {"Content-Type": "application/json"}

        if secret:
            # Generate HMAC signature
            message = json.dumps(payload, sort_keys=True).encode()
            signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature

        try:
            response = await self.http_client.post(
                webhook_url,
                json=payload,
                headers=headers,
            )

            if response.status_code >= 400:
                logger.warning(f"Webhook returned {response.status_code}: {response.text}")
            else:
                logger.info(f"Webhook sent successfully to {webhook_url}")

        except Exception as e:
            logger.error(f"Webhook request failed: {e}")
            raise

    async def _increment_alert_count(self, search_id: str):
        """Increment the alert count for a search."""
        if not self.db_pool:
            return

        query = "UPDATE saved_searches SET alert_count = alert_count + 1 WHERE id = %s"

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (search_id,))
                conn.commit()

    # =========================================================================
    # Database Operations
    # =========================================================================

    async def _save_to_db(self, search: SavedSearch):
        """Save a new search to the database."""
        if not self.db_pool:
            logger.warning("No database pool available, search not persisted")
            return

        query = """
            INSERT INTO saved_searches (
                id, user_id, name, description, search_type,
                parameters, alert_config, created_at, updated_at,
                is_active, run_count, alert_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    search.id,
                    search.user_id,
                    search.name,
                    search.description,
                    search.search_type.value,
                    json.dumps(search.parameters),
                    json.dumps(search.alert_config.to_dict()),
                    search.created_at,
                    search.updated_at,
                    search.is_active,
                    search.run_count,
                    search.alert_count,
                ))
                conn.commit()

    async def _update_in_db(self, search: SavedSearch):
        """Update an existing search in the database."""
        if not self.db_pool:
            return

        query = """
            UPDATE saved_searches SET
                name = %s,
                description = %s,
                parameters = %s,
                alert_config = %s,
                updated_at = %s,
                is_active = %s
            WHERE id = %s
        """

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    search.name,
                    search.description,
                    json.dumps(search.parameters),
                    json.dumps(search.alert_config.to_dict()),
                    search.updated_at,
                    search.is_active,
                    search.id,
                ))
                conn.commit()

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get saved search statistics for a user."""
        searches = await self.get_user_searches(user_id, active_only=False)

        active_searches = [s for s in searches if s.is_active]
        total_runs = sum(s.run_count for s in searches)
        total_alerts = sum(s.alert_count for s in searches)

        by_type = {}
        for search in active_searches:
            by_type[search.search_type.value] = by_type.get(search.search_type.value, 0) + 1

        return {
            "total_searches": len(searches),
            "active_searches": len(active_searches),
            "inactive_searches": len(searches) - len(active_searches),
            "total_runs": total_runs,
            "total_alerts_sent": total_alerts,
            "by_type": by_type,
        }


# Singleton instance
_saved_search_service: Optional[SavedSearchService] = None


def get_saved_search_service(
    db_pool=None,
    redis_client=None,
) -> SavedSearchService:
    """Get or create the SavedSearchService singleton."""
    global _saved_search_service

    if _saved_search_service is None:
        _saved_search_service = SavedSearchService(
            db_pool=db_pool,
            redis_client=redis_client,
        )

    return _saved_search_service
