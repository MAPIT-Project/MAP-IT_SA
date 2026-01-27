"""
Simple API endpoint for call-specific questions.
Bypasses the complex conversation system and directly uses CallDocumentService.
"""

import logging
import os

import google.generativeai as genai
import psycopg2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.call_document_service import CallDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/call", tags=["call-documents"])

# Initialize database pool and service
db_url = os.getenv("DATABASE_URL")
db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, db_url) if db_url else None
call_doc_service = CallDocumentService(db_pool) if db_pool else None

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")


class CallQuestionRequest(BaseModel):
    question: str
    call_id: str | None = None
    max_chunks: int = 10


class CallQuestionResponse(BaseModel):
    answer: str
    call_id: str
    chunks_used: int
    sources: list[str]
    cached: bool
    processing_time_ms: float


@router.post("/{call_id}/ask", response_model=CallQuestionResponse)
async def ask_call_question(call_id: str, request: CallQuestionRequest):
    """
    Ask a question about a specific call.
    
    This endpoint:
    1. Automatically fetches/caches call documents
    2. Retrieves relevant chunks
    3. Generates an AI answer using the chunks
    
    Example:
        POST /api/call/HORIZON-CL3-2025-02-CS-ECCC-01/ask
        {"question": "What are the eligibility criteria?"}
    """
    
    if not call_doc_service:
        raise HTTPException(status_code=500, detail="Call document service not initialized")
    
    try:
        import time
        start_time = time.time()
        
        logger.info(f"📋 Question for {call_id}: {request.question}")
        
        # Step 1: Get call documents (auto-fetches if needed)
        call_docs = call_doc_service.get_call_documents(call_id)
        
        if not call_docs:
            raise HTTPException(status_code=404, detail=f"Could not fetch documents for call {call_id}")
        
        cached = call_docs['cached']
        
        # Step 2: Search relevant chunks
        chunks = call_doc_service.search_call_chunks(
            call_identifier=call_id,
            query=request.question,
            limit=request.max_chunks
        )
        
        if not chunks:
            return CallQuestionResponse(
                answer="I couldn't find relevant information in the call documents to answer your question.",
                call_id=call_id,
                chunks_used=0,
                sources=[],
                cached=cached,
                processing_time_ms=round((time.time() - start_time) * 1000, 2)
            )
        
        # Step 3: Generate answer using AI
        context = "\n\n---\n\n".join([
            f"**{chunk['document_title']}** - {chunk.get('section_title', 'N/A')}\n\n{chunk['chunk_text']}"
            for chunk in chunks
        ])
        
        prompt = f"""You are a helpful assistant answering questions about the Horizon Europe call {call_id}.

Use ONLY the following context from official call documents to answer the question.
Be specific and cite the document sections.

CONTEXT:
{context}

QUESTION: {request.question}

ANSWER (cite sources):"""
        
        response = model.generate_content(prompt)
        answer = response.text
        
        # Extract unique sources
        sources = list(set([
            f"{chunk['document_title']} - {chunk.get('section_title', 'N/A')}"
            for chunk in chunks
        ]))
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"✅ Answer generated in {processing_time}ms using {len(chunks)} chunks")
        
        return CallQuestionResponse(
            answer=answer,
            call_id=call_id,
            chunks_used=len(chunks),
            sources=sources[:5],  # Top 5 sources
            cached=cached,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{call_id}/documents")
async def get_call_documents_info(call_id: str):
    """Get information about documents available for a call"""
    
    if not call_doc_service:
        raise HTTPException(status_code=500, detail="Call document service not initialized")
    
    try:
        call_docs = call_doc_service.get_call_documents(call_id)
        
        if not call_docs:
            raise HTTPException(status_code=404, detail=f"No documents found for call {call_id}")
        
        return {
            "call_id": call_id,
            "documents_count": call_docs['documents_count'],
            "chunks_count": call_docs['chunks_count'],
            "cached": call_docs['cached'],
            "documents": call_docs['documents']
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


