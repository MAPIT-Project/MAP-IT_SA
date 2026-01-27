"""
Authentication and Authorization Module

JWT-based authentication with role-based access control for MAP-IT.
"""

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel, Field

load_dotenv()
logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole:
    """Available user roles."""

    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"
    API_USER = "api_user"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    org_id: str | None = None
    tier: str = "free"  # free, basic, premium, enterprise
    exp: datetime
    iat: datetime


class User(BaseModel):
    """Authenticated user model."""

    id: str
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    organization_id: str | None = None
    tier: str = "free"
    is_authenticated: bool = True


class AuthService:
    """JWT-based authentication service."""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=24)
        self.refresh_token_expire = timedelta(days=7)

        # Warn if using default secret in production
        if os.getenv("JWT_SECRET_KEY") is None:
            logger.warning(
                "JWT_SECRET_KEY not set - using generated secret. Set this in production!"
            )

    def create_access_token(
        self,
        user_id: str,
        email: str | None = None,
        roles: list[str] | None = None,
        organization_id: str | None = None,
        tier: str = "free",
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create JWT access token."""
        expires = datetime.now(UTC) + (expires_delta or self.access_token_expire)

        payload = {
            "sub": user_id,
            "email": email,
            "roles": roles or [UserRole.RESEARCHER],
            "org_id": organization_id,
            "tier": tier,
            "exp": expires,
            "iat": datetime.now(UTC),
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token for token renewal."""
        expires = datetime.now(UTC) + self.refresh_token_expire

        payload = {"sub": user_id, "exp": expires, "iat": datetime.now(UTC), "type": "refresh"}

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify token type
            if payload.get("type") != token_type:
                raise InvalidTokenError(f"Invalid token type: expected {token_type}")

            return TokenPayload(
                sub=payload["sub"],
                email=payload.get("email"),
                roles=payload.get("roles", []),
                org_id=payload.get("org_id"),
                tier=payload.get("tier", "free"),
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
            )

        except ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def refresh_access_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh an access token using a refresh token."""
        payload = self.verify_token(refresh_token, token_type="refresh")

        # Create new access token
        new_access_token = self.create_access_token(
            user_id=payload.sub,
            # Note: In production, fetch fresh user data from database
        )

        return {"access_token": new_access_token, "token_type": "bearer"}

    def decode_token_unsafe(self, token: str) -> dict[str, Any] | None:
        """Decode token without verification (for debugging only)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None


# Singleton auth service
_auth_service = None


def get_auth_service() -> AuthService:
    """Get singleton auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# API Key validation
class APIKeyValidator:
    """Validate API keys against database or cache."""

    def __init__(self):
        self.api_keys: dict[str, dict[str, Any]] = {}
        # In production, load from database or environment

        # Load any static API keys from environment
        static_key = os.getenv("STATIC_API_KEY")
        if static_key:
            self.api_keys[static_key] = {
                "user_id": "api_user_static",
                "roles": [UserRole.API_USER],
                "tier": "basic",
                "org_id": None,
            }

    def validate(self, api_key: str) -> User | None:
        """Validate API key and return user if valid."""
        key_data = self.api_keys.get(api_key)
        if key_data:
            return User(
                id=key_data["user_id"],
                roles=key_data["roles"],
                tier=key_data["tier"],
                organization_id=key_data.get("org_id"),
                is_authenticated=True,
            )
        return None


_api_key_validator = None


def get_api_key_validator() -> APIKeyValidator:
    """Get singleton API key validator."""
    global _api_key_validator
    if _api_key_validator is None:
        _api_key_validator = APIKeyValidator()
    return _api_key_validator


# Dependency functions
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
) -> User:
    """
    Get current authenticated user from JWT token or API key.

    This is a FastAPI dependency that can be used in route handlers.
    """
    # Try API key first
    if api_key:
        validator = get_api_key_validator()
        user = validator.validate(api_key)
        if user:
            request.state.user = user
            return user

    # Try JWT token
    if credentials:
        auth_service = get_auth_service()
        try:
            payload = auth_service.verify_token(credentials.credentials)
            user = User(
                id=payload.sub,
                email=payload.email,
                roles=payload.roles,
                organization_id=payload.org_id,
                tier=payload.tier,
                is_authenticated=True,
            )
            request.state.user = user
            return user
        except HTTPException:
            raise

    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
) -> User | None:
    """
    Get current user if authenticated, otherwise return None.

    Use this for endpoints that work for both authenticated and anonymous users.
    """
    try:
        return await get_current_user(request, credentials, api_key)
    except HTTPException:
        # Create anonymous user
        anonymous = User(id="anonymous", roles=[], tier="free", is_authenticated=False)
        request.state.user = anonymous
        return anonymous


def require_roles(required_roles: list[str]):
    """
    Dependency factory that requires specific roles.

    Usage:
        @router.get("/admin/stats")
        async def admin_stats(user: User = Depends(require_roles(["admin"]))):
            ...
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(required_roles)}",
            )
        return user

    return role_checker


def require_tier(min_tier: str):
    """
    Dependency factory that requires minimum subscription tier.

    Tier hierarchy: free < basic < premium < enterprise

    Usage:
        @router.get("/premium/feature")
        async def premium_feature(user: User = Depends(require_tier("premium"))):
            ...
    """
    tier_levels = {"free": 0, "basic": 1, "premium": 2, "enterprise": 3}

    async def tier_checker(user: User = Depends(get_current_user)) -> User:
        user_level = tier_levels.get(user.tier, 0)
        required_level = tier_levels.get(min_tier, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires {min_tier} tier or higher"
            )
        return user

    return tier_checker


# Middleware for setting user context
class AuthMiddleware:
    """Middleware to optionally set user context from token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Try to extract user from Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            auth_service = get_auth_service()
            try:
                payload = auth_service.verify_token(token)
                scope["state"]["user"] = User(
                    id=payload.sub,
                    email=payload.email,
                    roles=payload.roles,
                    organization_id=payload.org_id,
                    tier=payload.tier,
                    is_authenticated=True,
                )
            except Exception:
                # Invalid token - user remains unauthenticated
                pass

        await self.app(scope, receive, send)


# Route decorators for convenience
def authenticated(func):
    """Decorator to require authentication on a route."""

    @wraps(func)
    async def wrapper(*args, user: User = Depends(get_current_user), **kwargs):
        return await func(*args, user=user, **kwargs)

    return wrapper


def admin_only(func):
    """Decorator to require admin role."""

    @wraps(func)
    async def wrapper(*args, user: User = Depends(require_roles([UserRole.ADMIN])), **kwargs):
        return await func(*args, user=user, **kwargs)

    return wrapper
