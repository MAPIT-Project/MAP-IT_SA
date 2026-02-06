"""
Simple API endpoint for call-specific questions.
Bypasses the complex conversation system and directly uses CallDocumentService.
"""

import logging
import os

import google.generativeai as genai
import psycopg2
import psycopg2.pool
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.call_document_service import CallDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/call", tags=["call-documents"])

# Lazy initialization of database pool and services
_db_pool = None
_call_doc_service = None
_gemini_model = None


def _get_db_pool():
    """Lazy initialization of database connection pool."""
    global _db_pool
    if _db_pool is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            try:
                _db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, db_url)
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize database pool: {e}")
    return _db_pool


def _get_call_doc_service():
    """Lazy initialization of call document service."""
    global _call_doc_service
    if _call_doc_service is None:
        pool = _get_db_pool()
        if pool:
            _call_doc_service = CallDocumentService(pool)
            logger.info("Call document service initialized")
    return _call_doc_service


def _get_gemini_model():
    """Lazy initialization of Gemini model."""
    global _gemini_model
    if _gemini_model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            _gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
            logger.info("Gemini model initialized")
    return _gemini_model


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
    call_doc_service = _get_call_doc_service()
    model = _get_gemini_model()

    if not call_doc_service:
        raise HTTPException(status_code=500, detail="Call document service not initialized")

    if not model:
        raise HTTPException(status_code=500, detail="Gemini model not initialized")

    try:
        import time

        start_time = time.time()

        logger.info(f"📋 Question for {call_id}: {request.question}")

        # Step 1: Get call documents (auto-fetches if needed)
        call_docs = call_doc_service.get_call_documents(call_id)

        if not call_docs:
            raise HTTPException(
                status_code=404, detail=f"Could not fetch documents for call {call_id}"
            )

        cached = call_docs["cached"]

        # Step 2: Search relevant chunks
        chunks = call_doc_service.search_call_chunks(
            call_identifier=call_id, query=request.question, limit=request.max_chunks
        )

        if not chunks:
            return CallQuestionResponse(
                answer="I couldn't find relevant information in the call documents to answer your question.",
                call_id=call_id,
                chunks_used=0,
                sources=[],
                cached=cached,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
            )

        # Step 3: Generate answer using AI
        context = "\n\n---\n\n".join(
            [
                f"**{chunk['document_title']}** - {chunk.get('section_title', 'N/A')}\n\n{chunk['chunk_text']}"
                for chunk in chunks
            ]
        )

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
        sources = list(
            set(
                [
                    f"{chunk['document_title']} - {chunk.get('section_title', 'N/A')}"
                    for chunk in chunks
                ]
            )
        )

        processing_time = round((time.time() - start_time) * 1000, 2)

        logger.info(f"✅ Answer generated in {processing_time}ms using {len(chunks)} chunks")

        return CallQuestionResponse(
            answer=answer,
            call_id=call_id,
            chunks_used=len(chunks),
            sources=sources[:5],  # Top 5 sources
            cached=cached,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"❌ Error processing question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{call_id}/documents")
async def get_call_documents_info(call_id: str):
    """Get information about documents available for a call"""
    call_doc_service = _get_call_doc_service()

    if not call_doc_service:
        raise HTTPException(status_code=500, detail="Call document service not initialized")

    try:
        call_docs = call_doc_service.get_call_documents(call_id)

        if not call_docs:
            raise HTTPException(status_code=404, detail=f"No documents found for call {call_id}")

        return {
            "call_id": call_id,
            "documents_count": call_docs["documents_count"],
            "chunks_count": call_docs["chunks_count"],
            "cached": call_docs["cached"],
            "documents": call_docs["documents"],
        }

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
