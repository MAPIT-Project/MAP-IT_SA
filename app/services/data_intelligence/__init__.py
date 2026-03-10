"""
Data Intelligence package for graph-based and hybrid search capabilities.
"""

from .cross_encoder_reranker import CrossEncoderReranker, RankedDocument, get_reranker
from .query_planner import ExecutionStep, QueryPlan, QueryPlanner

# Lazy import GraphSearchService to avoid failing when neo4j is unavailable
try:
    from .graph_service import GraphSearchService
except ImportError:
    GraphSearchService = None

__all__ = [
    "GraphSearchService",
    "QueryPlanner",
    "QueryPlan",
    "ExecutionStep",
    "CrossEncoderReranker",
    "RankedDocument",
    "get_reranker",
]
