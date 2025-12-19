"""
Audit Service Module.

Provides functionality for:
- Comprehensive audit logging
- Query audit trails
- Compliance reporting
- SIEM integration support
"""

from app.services.audit.audit_service import (
    AuditEvent,
    AuditEventType,
    AuditService,
    get_audit_service,
)

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditService",
    "get_audit_service",
]
