"""
Multi-tenancy Support.

Provides organization-based data isolation:
- Tenant context management via context variables
- Tenant-aware middleware for automatic context setting
- Base repository with tenant isolation
- Tenant model mixins

Features:
- Automatic tenant ID injection in queries
- Row-level security support
- Cross-tenant access for admins
- Tenant-aware caching
"""

import logging
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# =============================================================================
# Context Variables
# =============================================================================


# Current tenant ID for the request
current_tenant_id: ContextVar[Optional[str]] = ContextVar("current_tenant_id", default=None)

# Current tenant data (full tenant object)
current_tenant: ContextVar[Optional["Tenant"]] = ContextVar("current_tenant", default=None)

# Flag to bypass tenant isolation (for admin operations)
bypass_tenant_isolation: ContextVar[bool] = ContextVar("bypass_tenant_isolation", default=False)


def get_current_tenant_id() -> Optional[str]:
    """Get the current tenant ID from context."""
    return current_tenant_id.get()


def get_current_tenant() -> Optional["Tenant"]:
    """Get the current tenant object from context."""
    return current_tenant.get()


def set_tenant_context(tenant_id: Optional[str], tenant: Optional["Tenant"] = None):
    """Set the tenant context for the current request."""
    current_tenant_id.set(tenant_id)
    if tenant:
        current_tenant.set(tenant)


def clear_tenant_context():
    """Clear the tenant context."""
    current_tenant_id.set(None)
    current_tenant.set(None)
    bypass_tenant_isolation.set(False)


def enable_bypass_isolation():
    """Enable bypass of tenant isolation (for admin operations)."""
    bypass_tenant_isolation.set(True)


def disable_bypass_isolation():
    """Disable bypass of tenant isolation."""
    bypass_tenant_isolation.set(False)


def is_isolation_bypassed() -> bool:
    """Check if tenant isolation is bypassed."""
    return bypass_tenant_isolation.get()


# =============================================================================
# Tenant Model
# =============================================================================


class TenantStatus(str, Enum):
    """Tenant account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    TRIAL = "trial"


class TenantPlan(str, Enum):
    """Tenant subscription plan."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class TenantLimits:
    """Usage limits for a tenant."""
    max_users: int = 5
    max_proposals: int = 10
    max_conversations_per_day: int = 50
    max_storage_mb: int = 1000
    max_api_requests_per_day: int = 1000

    @classmethod
    def for_plan(cls, plan: TenantPlan) -> "TenantLimits":
        """Get limits for a plan."""
        limits_by_plan = {
            TenantPlan.FREE: cls(max_users=3, max_proposals=5, max_conversations_per_day=20, max_storage_mb=100, max_api_requests_per_day=200),
            TenantPlan.BASIC: cls(max_users=10, max_proposals=50, max_conversations_per_day=200, max_storage_mb=1000, max_api_requests_per_day=2000),
            TenantPlan.PREMIUM: cls(max_users=50, max_proposals=500, max_conversations_per_day=1000, max_storage_mb=10000, max_api_requests_per_day=20000),
            TenantPlan.ENTERPRISE: cls(max_users=10000, max_proposals=100000, max_conversations_per_day=100000, max_storage_mb=1000000, max_api_requests_per_day=1000000),
        }
        return limits_by_plan.get(plan, limits_by_plan[TenantPlan.FREE])


@dataclass
class Tenant:
    """A tenant (organization) in the system."""
    id: str
    name: str
    slug: str  # URL-friendly identifier
    status: TenantStatus = TenantStatus.ACTIVE
    plan: TenantPlan = TenantPlan.FREE
    limits: TenantLimits = None
    settings: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None

    # Contact information
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None

    # Feature flags
    features: Dict[str, bool] = None

    def __post_init__(self):
        if self.limits is None:
            self.limits = TenantLimits.for_plan(self.plan)
        if self.settings is None:
            self.settings = {}
        if self.features is None:
            self.features = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "status": self.status.value,
            "plan": self.plan.value,
            "limits": {
                "max_users": self.limits.max_users,
                "max_proposals": self.limits.max_proposals,
                "max_conversations_per_day": self.limits.max_conversations_per_day,
                "max_storage_mb": self.limits.max_storage_mb,
                "max_api_requests_per_day": self.limits.max_api_requests_per_day,
            },
            "settings": self.settings,
            "features": self.features,
            "admin_email": self.admin_email,
            "admin_name": self.admin_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has a feature enabled."""
        return self.features.get(feature, False)

    def is_active(self) -> bool:
        """Check if tenant account is active."""
        return self.status in (TenantStatus.ACTIVE, TenantStatus.TRIAL)


# =============================================================================
# Middleware
# =============================================================================


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set tenant context from JWT or request.

    Extracts organization ID from:
    1. JWT claims (org_id)
    2. X-Tenant-ID header
    3. URL path parameter (for tenant-scoped routes)
    """

    # Paths that don't require tenant context
    EXEMPT_PATHS = {
        "/api/health",
        "/api/v3/conversation/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app, tenant_service=None):
        super().__init__(app)
        self.tenant_service = tenant_service

    async def dispatch(self, request: Request, call_next):
        # Clear any existing context
        clear_tenant_context()

        # Check if path is exempt
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Extract tenant ID
        tenant_id = await self._extract_tenant_id(request)

        if tenant_id:
            # Load tenant and set context
            tenant = await self._load_tenant(tenant_id)
            if tenant:
                if not tenant.is_active():
                    return self._tenant_inactive_response(tenant)
                set_tenant_context(tenant_id, tenant)

        try:
            response = await call_next(request)
            return response
        finally:
            clear_tenant_context()

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from tenant requirements."""
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False

    async def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        # 1. Check request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user and user.get("org_id"):
            return user["org_id"]

        # 2. Check X-Tenant-ID header
        tenant_header = request.headers.get("x-tenant-id")
        if tenant_header:
            return tenant_header

        # 3. Check URL path for tenant routes
        # e.g., /api/tenants/{tenant_id}/...
        path_parts = request.url.path.split("/")
        if "tenants" in path_parts:
            tenant_idx = path_parts.index("tenants")
            if len(path_parts) > tenant_idx + 1:
                return path_parts[tenant_idx + 1]

        return None

    async def _load_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Load tenant from service or cache."""
        if self.tenant_service:
            return await self.tenant_service.get_tenant(tenant_id)

        # Fallback: Create minimal tenant object
        return Tenant(
            id=tenant_id,
            name=f"Tenant {tenant_id}",
            slug=tenant_id,
        )

    def _tenant_inactive_response(self, tenant: Tenant):
        """Return error response for inactive tenant."""
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "TENANT_INACTIVE",
                "message": f"Tenant account is {tenant.status.value}",
                "tenant_id": tenant.id,
            }
        )


# =============================================================================
# Tenant-Aware Repository
# =============================================================================


T = TypeVar("T")


class TenantAwareRepository:
    """
    Base repository class with automatic tenant isolation.

    All queries automatically filter by tenant_id unless
    bypass is explicitly enabled.
    """

    def __init__(self, db_pool=None, table_name: str = None):
        """
        Initialize the repository.

        Args:
            db_pool: Database connection pool
            table_name: Name of the main table
        """
        self.db_pool = db_pool
        self.table_name = table_name

    def _add_tenant_filter(self, query: str, params: list = None) -> tuple:
        """
        Add tenant filter to SQL query.

        Args:
            query: SQL query string
            params: Query parameters list

        Returns:
            Tuple of (modified_query, params)
        """
        tenant_id = get_current_tenant_id()
        params = params or []

        # Skip if isolation bypassed or no tenant context
        if is_isolation_bypassed() or not tenant_id:
            return query, params

        # Add tenant filter
        query_upper = query.upper()

        if "WHERE" in query_upper:
            # Insert after WHERE
            where_idx = query_upper.index("WHERE")
            insert_pos = where_idx + 5  # After "WHERE"
            query = f"{query[:insert_pos]} organization_id = %s AND{query[insert_pos:]}"
        else:
            # Check for GROUP BY, ORDER BY, LIMIT
            for clause in ["GROUP BY", "ORDER BY", "LIMIT", "OFFSET"]:
                if clause in query_upper:
                    clause_idx = query_upper.index(clause)
                    query = f"{query[:clause_idx]} WHERE organization_id = %s {query[clause_idx:]}"
                    break
            else:
                # No clauses, append WHERE
                query = f"{query} WHERE organization_id = %s"

        # Add tenant_id as first parameter
        params = [tenant_id] + list(params)

        return query, params

    def _add_tenant_to_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add tenant ID to data being inserted."""
        tenant_id = get_current_tenant_id()
        if tenant_id and not is_isolation_bypassed():
            data["organization_id"] = tenant_id
        return data

    async def execute_query(
        self,
        query: str,
        params: list = None,
        add_tenant_filter: bool = True,
    ) -> list:
        """
        Execute a query with optional tenant filtering.

        Args:
            query: SQL query string
            params: Query parameters
            add_tenant_filter: Whether to add tenant filter

        Returns:
            Query results
        """
        if not self.db_pool:
            return []

        params = params or []

        if add_tenant_filter:
            query, params = self._add_tenant_filter(query, params)

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]

    async def execute_insert(
        self,
        data: Dict[str, Any],
        returning: str = "id",
    ) -> Any:
        """
        Execute an insert with automatic tenant ID.

        Args:
            data: Data to insert
            returning: Column to return

        Returns:
            Inserted ID or specified column value
        """
        if not self.db_pool:
            return None

        # Add tenant ID
        data = self._add_tenant_to_insert(data)

        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        query = f"""
            INSERT INTO {self.table_name} ({column_names})
            VALUES ({placeholders})
            RETURNING {returning}
        """

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, list(data.values()))
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else None

    async def execute_update(
        self,
        record_id: str,
        data: Dict[str, Any],
        id_column: str = "id",
    ) -> bool:
        """
        Execute an update with tenant isolation.

        Args:
            record_id: ID of record to update
            data: Data to update
            id_column: Name of ID column

        Returns:
            True if updated successfully
        """
        if not self.db_pool:
            return False

        set_clauses = ", ".join([f"{k} = %s" for k in data.keys()])
        params = list(data.values())

        query = f"UPDATE {self.table_name} SET {set_clauses} WHERE {id_column} = %s"
        params.append(record_id)

        # Add tenant filter
        query, params = self._add_tenant_filter(query, params)

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    async def execute_delete(
        self,
        record_id: str,
        id_column: str = "id",
    ) -> bool:
        """
        Execute a delete with tenant isolation.

        Args:
            record_id: ID of record to delete
            id_column: Name of ID column

        Returns:
            True if deleted successfully
        """
        if not self.db_pool:
            return False

        query = f"DELETE FROM {self.table_name} WHERE {id_column} = %s"
        params = [record_id]

        # Add tenant filter
        query, params = self._add_tenant_filter(query, params)

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0


# =============================================================================
# Decorators
# =============================================================================


def require_tenant(func: Callable) -> Callable:
    """Decorator to require a tenant context."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TENANT_REQUIRED",
                    "message": "A tenant context is required for this operation",
                }
            )
        return await func(*args, **kwargs)
    return wrapper


def require_tenant_feature(feature: str):
    """Decorator to require a specific tenant feature."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant = get_current_tenant()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "TENANT_REQUIRED"}
                )
            if not tenant.has_feature(feature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "FEATURE_NOT_AVAILABLE",
                        "message": f"Feature '{feature}' is not available for your plan",
                        "feature": feature,
                        "plan": tenant.plan.value,
                    }
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def with_tenant(tenant_id: str):
    """Context manager to temporarily set tenant context."""
    class TenantContext:
        def __init__(self, tenant_id: str):
            self.tenant_id = tenant_id
            self.previous_id = None
            self.previous_tenant = None

        async def __aenter__(self):
            self.previous_id = get_current_tenant_id()
            self.previous_tenant = get_current_tenant()
            set_tenant_context(self.tenant_id)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            set_tenant_context(self.previous_id, self.previous_tenant)
            return False

    return TenantContext(tenant_id)


def admin_bypass(func: Callable) -> Callable:
    """Decorator to bypass tenant isolation for admin operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            enable_bypass_isolation()
            return await func(*args, **kwargs)
        finally:
            disable_bypass_isolation()
    return wrapper


# =============================================================================
# Tenant Service
# =============================================================================


class TenantService:
    """Service for managing tenants."""

    def __init__(self, db_pool=None, redis_client=None):
        self.db_pool = db_pool
        self.redis = redis_client
        self._cache: Dict[str, Tenant] = {}

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID with caching."""
        # Check cache
        if tenant_id in self._cache:
            return self._cache[tenant_id]

        # Check Redis cache
        if self.redis:
            try:
                import json
                cached = self.redis.get(f"tenant:{tenant_id}")
                if cached:
                    data = json.loads(cached)
                    tenant = self._dict_to_tenant(data)
                    self._cache[tenant_id] = tenant
                    return tenant
            except Exception:
                pass

        # Load from database
        if not self.db_pool:
            return None

        query = "SELECT * FROM tenants WHERE id = %s"

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (tenant_id,))
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    tenant = self._row_to_tenant(dict(zip(columns, row)))
                    self._cache_tenant(tenant)
                    return tenant

        return None

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by URL slug."""
        if not self.db_pool:
            return None

        query = "SELECT * FROM tenants WHERE slug = %s"

        with self.db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (slug,))
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return self._row_to_tenant(dict(zip(columns, row)))

        return None

    async def create_tenant(
        self,
        name: str,
        slug: str,
        admin_email: str,
        admin_name: str = None,
        plan: TenantPlan = TenantPlan.FREE,
    ) -> Tenant:
        """Create a new tenant."""
        from uuid import uuid4

        tenant = Tenant(
            id=str(uuid4()),
            name=name,
            slug=slug,
            status=TenantStatus.ACTIVE,
            plan=plan,
            admin_email=admin_email,
            admin_name=admin_name,
        )

        if self.db_pool:
            query = """
                INSERT INTO tenants (id, name, slug, status, plan, admin_email, admin_name, settings, features, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            import json

            with self.db_pool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        tenant.id,
                        tenant.name,
                        tenant.slug,
                        tenant.status.value,
                        tenant.plan.value,
                        tenant.admin_email,
                        tenant.admin_name,
                        json.dumps(tenant.settings),
                        json.dumps(tenant.features),
                        tenant.created_at,
                        tenant.updated_at,
                    ))
                    conn.commit()

        self._cache_tenant(tenant)
        return tenant

    def _cache_tenant(self, tenant: Tenant):
        """Cache tenant locally and in Redis."""
        import json

        self._cache[tenant.id] = tenant

        if self.redis:
            try:
                self.redis.setex(
                    f"tenant:{tenant.id}",
                    3600,  # 1 hour TTL
                    json.dumps(tenant.to_dict()),
                )
            except Exception:
                pass

    def _row_to_tenant(self, row: Dict[str, Any]) -> Tenant:
        """Convert database row to Tenant object."""
        import json

        settings = row.get("settings", {})
        if isinstance(settings, str):
            settings = json.loads(settings)

        features = row.get("features", {})
        if isinstance(features, str):
            features = json.loads(features)

        return Tenant(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            status=TenantStatus(row.get("status", "active")),
            plan=TenantPlan(row.get("plan", "free")),
            settings=settings,
            features=features,
            admin_email=row.get("admin_email"),
            admin_name=row.get("admin_name"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _dict_to_tenant(self, data: Dict[str, Any]) -> Tenant:
        """Convert dict to Tenant object."""
        return Tenant(
            id=data["id"],
            name=data["name"],
            slug=data["slug"],
            status=TenantStatus(data.get("status", "active")),
            plan=TenantPlan(data.get("plan", "free")),
            limits=TenantLimits(**data.get("limits", {})) if data.get("limits") else None,
            settings=data.get("settings", {}),
            features=data.get("features", {}),
            admin_email=data.get("admin_email"),
            admin_name=data.get("admin_name"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )


# Singleton instance
_tenant_service: Optional[TenantService] = None


def get_tenant_service(db_pool=None, redis_client=None) -> TenantService:
    """Get or create the TenantService singleton."""
    global _tenant_service

    if _tenant_service is None:
        _tenant_service = TenantService(db_pool=db_pool, redis_client=redis_client)

    return _tenant_service
