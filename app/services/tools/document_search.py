"""
Document Search Tool for Horizon Europe.

Searches official EU documents using vector search (hybrid keyword + semantic)
with rich metadata extraction for citations. Supports filtering by document type
and returns content with full provenance information (source, section, page number,
chunk ID, document ID).

Uses the VectorSearchService for hybrid search across ingested documents including
Horizon Europe regulations, work programmes, and guidance documents.
"""

import asyncio
import logging
from typing import Any

from ..document_content import (
    clean_document_text,
    is_usable_document_text,
    select_document_excerpt,
)

logger = logging.getLogger(__name__)


async def search_documents_execute(
    query: str,
    max_results: int = 15,
    document_type: str | None = None,
) -> dict[str, Any]:
    """
    Search documents using vector search with rich metadata for citations.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 15).
        document_type: Optional filter by document type.

    Returns:
        Dict with matching documents, query echo, and total count.
    """
    try:
        from ..vector_search_service import VectorSearchService

        vector = VectorSearchService()

        # Build filters if document type specified
        filters = None
        if document_type:
            filters = {"document_type": document_type}

        # hybrid_search uses num_results, not limit
        results = await asyncio.to_thread(
            vector.hybrid_search, query=query, num_results=max_results * 3, filters=filters
        )

        # Multiple ingestions of the same PDF must not consume the result limit.
        # For identical text, prefer the copy with an explicit stored page.
        unique = {}
        for r in results:
            content = getattr(r, "content", "")
            if not isinstance(content, str) or not is_usable_document_text(content):
                continue
            content = clean_document_text(content)
            key = " ".join(content.split()).casefold()
            if key not in unique or (
                getattr(unique[key][0], "page_number", None) is None
                and getattr(r, "page_number", None) is not None
            ):
                unique[key] = (r, content)

        # Build rich document response with full metadata for citations.
        documents = []
        for r, content in unique.values():
            doc = {
                "content": select_document_excerpt(content, query),
                "source": r.document_title if hasattr(r, "document_title") else "Unknown",
                "title": r.document_title if hasattr(r, "document_title") else "",
                "section": r.section if hasattr(r, "section") else "",
                "score": r.score if hasattr(r, "score") else 0,
                # Additional metadata for citations
                "chunk_id": r.chunk_id if hasattr(r, "chunk_id") else "",
                "document_id": r.document_id if hasattr(r, "document_id") else "",
                "section_title": r.section_title if hasattr(r, "section_title") else "",
                "page_number": r.page_number if hasattr(r, "page_number") else None,
                "document_type": r.document_type if hasattr(r, "document_type") else "",
                "metadata": r.metadata if hasattr(r, "metadata") else {},
            }
            documents.append(doc)
            if len(documents) >= max_results:
                break

        return {
            "documents": documents,
            "query": query,
            "total_found": len(documents),
            "tool_name": "search_documents",
            "message": ""
            if documents
            else "No usable document excerpts matched this query. Do not infer an answer from empty or unreadable excerpts.",
        }
    except Exception as e:
        return {"error": str(e)}
