"""
Webhook notifications service for MAP-IT.

Provides webhook notification capabilities for async operations,
proposal events, and deadline reminders.

Implements Priority 4.3 from IMPROVEMENT_ROADMAP.md
"""

from .webhook_service import (
    WebhookConfig,
    WebhookEvent,
    WebhookEventType,
    WebhookService,
    get_webhook_service,
)

__all__ = [
    "WebhookService",
    "WebhookEvent",
    "WebhookConfig",
    "WebhookEventType",
    "get_webhook_service",
]
