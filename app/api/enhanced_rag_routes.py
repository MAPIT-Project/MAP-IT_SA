"""
API routes for enhanced RAG functionality with vector search.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

from ..services.enhanced_rag_service import HorizonEuropeRAG
from ..services.vector_search_service import VectorSearchService
from ..models.schemas import QuestionRequest, SearchResponse
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["enhanced-rag"])

# Dependency to get enhanced RAG service
def get_enhanced_rag_service() -> HorizonEuropeRAG:
    return HorizonEuropeRAG()

# Dependency to get vector search service
def get_vector_search_service() -> VectorSearchService:
    return VectorSearchService()

@router.post("/query")
async def enhanced_rag_query(
    request: QuestionRequest,
    rag_service: HorizonEuropeRAG = Depends(get_enhanced_rag_service)
):
    """Enhanced RAG query combining vector search with CORDIS project search."""
    
    try:
        start_time = datetime.utcnow()
        
        # Process the query
        result = rag_service.answer_question(
            question=request.question,
            max_context_chunks=request.max_results or settings.max_chunks_per_query,
            include_projects=getattr(request, 'include_projects', True),
            include_documents=getattr(request, 'include_documents', True),
            search_type=getattr(request, 'search_type', 'hybrid'),
            similarity_threshold=getattr(request, 'similarity_threshold', settings.similarity_threshold)
        )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        result['processing_time'] = round(processing_time, 2)
        
        # Format as SearchResponse
        response = SearchResponse(
            answer=result.get('answer', ''),
            logs=result,  # Include full result as logs
            ai_provider=settings.default_ai_provider,
            ai_version="Enhanced RAG v1.0",
            model_used=settings.openai_model if settings.default_ai_provider == "openai" else settings.gemini_model,
            data_source=result.get('data_source', 'Enhanced RAG'),
            processing_time=processing_time,
            projects_found=result.get('chunks_used', 0),
            success=result.get('success', True)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Enhanced RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.post("/search/semantic")
async def semantic_search(
    query: str,
    num_results: int = Query(5, ge=1, le=20),
    document_type: Optional[str] = Query(None),
    programme_year: Optional[str] = Query(None),
    similarity_threshold: float = Query(0.7, ge=0.1, le=1.0),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Pure semantic search using vector similarity."""
    
    try:
        # Build filters
        filters = {}
        if document_type:
            filters['document_type'] = document_type
        if programme_year:
            filters['year'] = programme_year
        
        # Perform search
        results = vector_search.semantic_search(
            query=query,
            num_results=num_results,
            filters=filters,
            similarity_threshold=similarity_threshold
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'document_id': result.document_id,
                'document_title': result.document_title,
                'document_type': result.document_type,
                'content': result.content,
                'score': result.score,
                'section_title': result.section_title,
                'page_number': result.page_number,
                'metadata': result.metadata
            })
        
        return {
            'query': query,
            'search_type': 'semantic',
            'results': formatted_results,
            'total_results': len(formatted_results),
            'similarity_threshold': similarity_threshold,
            'filters': filters
        }
        
    except Exception as e:
        logger.error(f"❌ Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

@router.post("/search/hybrid")
async def hybrid_search(
    query: str,
    num_results: int = Query(5, ge=1, le=20),
    vector_weight: float = Query(0.6, ge=0.0, le=1.0),
    similarity_threshold: float = Query(0.7, ge=0.1, le=1.0),
    document_type: Optional[str] = Query(None),
    programme_year: Optional[str] = Query(None),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Hybrid search combining semantic and keyword search."""
    
    try:
        # Build filters
        filters = {}
        if document_type:
            filters['document_type'] = document_type
        if programme_year:
            filters['year'] = programme_year
        
        # Perform search
        results = vector_search.hybrid_search(
            query=query,
            num_results=num_results,
            filters=filters,
            similarity_threshold=similarity_threshold,
            vector_weight=vector_weight
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'document_id': result.document_id,
                'document_title': result.document_title,
                'document_type': result.document_type,
                'content': result.content,
                'score': result.score,
                'section_title': result.section_title,
                'page_number': result.page_number,
                'highlights': result.highlights,
                'metadata': result.metadata
            })
        
        return {
            'query': query,
            'search_type': 'hybrid',
            'results': formatted_results,
            'total_results': len(formatted_results),
            'vector_weight': vector_weight,
            'similarity_threshold': similarity_threshold,
            'filters': filters
        }
        
    except Exception as e:
        logger.error(f"❌ Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")

@router.post("/search/keyword")
async def keyword_search(
    query: str,
    num_results: int = Query(5, ge=1, le=20),
    document_type: Optional[str] = Query(None),
    programme_year: Optional[str] = Query(None),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Traditional keyword-based search."""
    
    try:
        # Build filters
        filters = {}
        if document_type:
            filters['document_type'] = document_type
        if programme_year:
            filters['year'] = programme_year
        
        # Perform search
        results = vector_search.keyword_search(
            query=query,
            num_results=num_results,
            filters=filters
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'document_id': result.document_id,
                'document_title': result.document_title,
                'document_type': result.document_type,
                'content': result.content,
                'score': result.score,
                'section_title': result.section_title,
                'page_number': result.page_number,
                'highlights': result.highlights,
                'metadata': result.metadata
            })
        
        return {
            'query': query,
            'search_type': 'keyword',
            'results': formatted_results,
            'total_results': len(formatted_results),
            'filters': filters
        }
        
    except Exception as e:
        logger.error(f"❌ Keyword search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Keyword search failed: {str(e)}")

@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=3),
    limit: int = Query(5, ge=1, le=10),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Get search suggestions based on partial query."""
    
    try:
        suggestions = vector_search.get_search_suggestions(q, limit)
        
        return {
            'query': q,
            'suggestions': suggestions,
            'count': len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"❌ Search suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search suggestions failed: {str(e)}")

@router.get("/chunks/{chunk_id}/similar")
async def get_similar_chunks(
    chunk_id: str,
    num_similar: int = Query(5, ge=1, le=10),
    similarity_threshold: float = Query(0.7, ge=0.1, le=1.0),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Find similar chunks to a given chunk."""
    
    try:
        results = vector_search.get_similar_chunks(
            chunk_id=chunk_id,
            num_similar=num_similar,
            similarity_threshold=similarity_threshold
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'document_id': result.document_id,
                'document_title': result.document_title,
                'document_type': result.document_type,
                'content': result.content,
                'score': result.score,
                'section_title': result.section_title,
                'page_number': result.page_number,
                'metadata': result.metadata
            })
        
        return {
            'source_chunk_id': chunk_id,
            'similar_chunks': formatted_results,
            'total_results': len(formatted_results),
            'similarity_threshold': similarity_threshold
        }
        
    except Exception as e:
        logger.error(f"❌ Similar chunks search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Similar chunks search failed: {str(e)}")

@router.post("/query/stream")
async def enhanced_rag_query_stream(
    request: QuestionRequest,
    rag_service: HorizonEuropeRAG = Depends(get_enhanced_rag_service)
):
    """Streaming version of enhanced RAG query."""
    
    async def generate_stream():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing enhanced RAG query...'})}\n\n"
            
            # Process the query
            result = rag_service.answer_question(
                question=request.question,
                max_context_chunks=request.max_results or settings.max_chunks_per_query,
                include_projects=getattr(request, 'include_projects', True),
                include_documents=getattr(request, 'include_documents', True),
                search_type=getattr(request, 'search_type', 'hybrid')
            )
            
            # Stream the answer in chunks
            answer = result.get('answer', '')
            if answer:
                words = answer.split()
                current_chunk = ""
                
                for word in words:
                    current_chunk += word + " "
                    if len(current_chunk.split()) % 10 == 0:  # Send every 10 words
                        yield f"data: {json.dumps({'type': 'chunk', 'content': current_chunk.strip()})}\n\n"
                        current_chunk = ""
                        await asyncio.sleep(0.1)  # Small delay for streaming effect
                
                # Send remaining chunk
                if current_chunk.strip():
                    yield f"data: {json.dumps({'type': 'chunk', 'content': current_chunk.strip()})}\n\n"
            
            # Send metadata
            metadata = {
                'type': 'metadata',
                'intent': result.get('intent'),
                'data_source': result.get('data_source'),
                'confidence': result.get('confidence'),
                'sources': result.get('sources', []),
                'chunks_used': result.get('chunks_used', 0)
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Processing failed', 'details': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.get("/search/by-document-type/{document_type}")
async def search_by_document_type(
    document_type: str,
    query: str,
    num_results: int = Query(5, ge=1, le=20),
    search_type: str = Query("hybrid"),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Search within a specific document type."""
    
    try:
        results = vector_search.search_by_document_type(
            query=query,
            document_type=document_type,
            num_results=num_results,
            search_type=search_type
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'document_id': result.document_id,
                'document_title': result.document_title,
                'document_type': result.document_type,
                'content': result.content,
                'score': result.score,
                'section_title': result.section_title,
                'page_number': result.page_number,
                'highlights': result.highlights,
                'metadata': result.metadata
            })
        
        return {
            'query': query,
            'document_type': document_type,
            'search_type': search_type,
            'results': formatted_results,
            'total_results': len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"❌ Document type search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document type search failed: {str(e)}")

@router.get("/search/by-programme-year/{programme_year}")
async def search_by_programme_year(
    programme_year: str,
    query: str,
    num_results: int = Query(5, ge=1, le=20),
    search_type: str = Query("hybrid"),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Search within a specific programme year."""
    
    try:
        results = vector_search.search_by_programme_year(
            query=query,
            programme_year=programme_year,
            num_results=num_results,
            search_type=search_type
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'document_id': result.document_id,
                'document_title': result.document_title,
                'document_type': result.document_type,
                'content': result.content,
                'score': result.score,
                'section_title': result.section_title,
                'page_number': result.page_number,
                'highlights': result.highlights,
                'metadata': result.metadata
            })
        
        return {
            'query': query,
            'programme_year': programme_year,
            'search_type': search_type,
            'results': formatted_results,
            'total_results': len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"❌ Programme year search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Programme year search failed: {str(e)}")

@router.get("/status")
async def get_rag_status(
    rag_service: HorizonEuropeRAG = Depends(get_enhanced_rag_service)
):
    """Get the status of all RAG services."""
    
    try:
        status = rag_service.get_service_status()
        return status
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/stats")
async def get_search_stats(
    vector_search: VectorSearchService = Depends(get_vector_search_service)
):
    """Get search performance and usage statistics."""
    
    try:
        stats = vector_search.get_search_stats()
        return stats
        
    except Exception as e:
        logger.error(f"❌ Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")