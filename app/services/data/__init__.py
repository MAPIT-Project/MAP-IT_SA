"""
Data access layer for CORDIS project data.

This module provides repository classes for accessing project data
from the local PostgreSQL database.
"""

from .cordis_repository import CordisProjectDTO, CordisProjectRepository

__all__ = ["CordisProjectRepository", "CordisProjectDTO"]
