"""
Alerts and Saved Searches Service Module.

Provides functionality for:
- Saved search configurations
- Periodic checking for new results
- Email/webhook notifications
"""

from app.services.alerts.saved_search_service import (
    SavedSearch,
    SavedSearchService,
    get_saved_search_service,
)

__all__ = [
    "SavedSearch",
    "SavedSearchService",
    "get_saved_search_service",
]
