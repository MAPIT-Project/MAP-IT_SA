
"""
API routes for document management and ingestion.
"""

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

from ..core.config import settings
from ..services.ingestion_service import DocumentIngestionService
from ..services.supabase_client import SupabaseVectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Dependency to get ingestion service
def get_ingestion_service() -> DocumentIngestionService:
    return DocumentIngestionService()

# Dependency to get supabase client
def get_supabase_client() -> SupabaseVectorStore:
    return SupabaseVectorStore()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str | None = None,
    programme_year: str | None = None,
    metadata: str | None = None,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """Upload a document for processing and ingestion."""
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.supported_file_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_extension}. Supported types: {settings.supported_file_types}"
            )
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size} bytes. Maximum size: {settings.max_file_size_mb}MB"
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"{file_id}_{file.filename}"
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"📁 File uploaded: {file.filename} -> {file_path}")
        
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Invalid metadata JSON: {metadata}")
        
        # Start ingestion in background
        background_tasks.add_task(
            ingestion_service.ingest_file,
            str(file_path),
            document_type,
            programme_year,
            None,  # source_url
            parsed_metadata
        )
        
        return {
            "message": "File uploaded successfully and ingestion started",
            "file_id": file_id,
            "filename": file.filename,
            "size": file_size,
            "document_type": document_type,
            "programme_year": programme_year,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/ingest-url")
async def ingest_web_url(
    background_tasks: BackgroundTasks,
    url: str,
    document_type: str | None = None,
    programme_year: str | None = None,
    metadata: dict[str, Any] | None = None,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """Ingest a web page URL."""
    
    try:
        # Validate URL
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL provided")
        
        # Check if URL is from allowed domains
        allowed_domains = [
            'europa.eu',
            'ec.europa.eu',
            'cordis.europa.eu',
            'research-and-innovation.ec.europa.eu'
        ]
        
        if not any(domain in parsed_url.netloc for domain in allowed_domains):
            raise HTTPException(
                status_code=400,
                detail=f"URL domain not allowed. Allowed domains: {allowed_domains}"
            )
        
        logger.info(f"🌐 Starting web ingestion for: {url}")
        
        # Start ingestion in background
        background_tasks.add_task(
            ingestion_service.ingest_web_page,
            url,
            document_type,
            programme_year,
            metadata
        )
        
        return {
            "message": "Web page ingestion started",
            "url": url,
            "document_type": document_type,
            "programme_year": programme_year,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Web ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Web ingestion failed: {str(e)}")

@router.get("/list")
async def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    document_type: str | None = Query(None),
    supabase: SupabaseVectorStore = Depends(get_supabase_client)
):
    """List documents with pagination and filtering."""
    
    try:
        documents, total_count = supabase.list_documents(
            limit=limit,
            offset=offset,
            status=status,
            document_type=document_type
        )
        
        return {
            "documents": documents,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
        
    except Exception as e:
        logger.error(f"❌ List documents failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    include_chunks: bool = Query(False),
    supabase: SupabaseVectorStore = Depends(get_supabase_client)
):
    """Get a specific document by ID."""
    
    try:
        document = supabase.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = {"document": document}
        
        if include_chunks:
            chunks = supabase.get_chunks_by_document(document_id)
            result["chunks"] = chunks
            result["chunk_count"] = len(chunks)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get document failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """Get the processing status of a document."""
    
    try:
        status = ingestion_service.get_ingestion_status(document_id)
        
        if 'error' in status:
            raise HTTPException(status_code=404, detail=status['error'])
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get status failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """Reprocess a failed or existing document."""
    
    try:
        # Start reprocessing in background
        background_tasks.add_task(
            ingestion_service.reprocess_document,
            document_id
        )
        
        return {
            "message": "Document reprocessing started",
            "document_id": document_id,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Reprocess failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reprocess document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    supabase: SupabaseVectorStore = Depends(get_supabase_client)
):
    """Delete a document and all its chunks."""
    
    try:
        # Check if document exists
        document = supabase.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document (chunks will be deleted automatically due to CASCADE)
        success = supabase.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document")
        
        # Clean up file if it exists
        if document.get('file_path'):
            try:
                file_path = Path(document['file_path'])
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"🗑️ Deleted file: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete file: {e}")
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    supabase: SupabaseVectorStore = Depends(get_supabase_client)
):
    """Get chunks for a specific document."""
    
    try:
        # Check if document exists
        document = supabase.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get all chunks (we'll implement pagination later if needed)
        all_chunks = supabase.get_chunks_by_document(document_id)
        
        # Apply pagination
        total_count = len(all_chunks)
        chunks = all_chunks[offset:offset + limit]
        
        return {
            "document_id": document_id,
            "document_title": document['title'],
            "chunks": chunks,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get chunks failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")

@router.get("/stats/overview")
async def get_document_stats(
    supabase: SupabaseVectorStore = Depends(get_supabase_client)
):
    """Get overview statistics about documents."""
    
    try:
        stats = supabase.get_document_stats()
        return stats
        
    except Exception as e:
        logger.error(f"❌ Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/batch-upload")
async def batch_upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    document_type: str | None = None,
    programme_year: str | None = None,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """Upload multiple documents for batch processing."""
    
    try:
        if len(files) > 10:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum 10 files per batch")
        
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(exist_ok=True)
        
        file_paths = []
        file_info = []
        
        # Save all files first
        for file in files:
            if not file.filename:
                continue
                
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in settings.supported_file_types:
                continue
            
            content = await file.read()
            file_size = len(content)
            
            if file_size > settings.max_file_size_mb * 1024 * 1024:
                continue
            
            file_id = str(uuid.uuid4())
            file_path = upload_dir / f"{file_id}_{file.filename}"
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            file_paths.append(str(file_path))
            file_info.append({
                "file_id": file_id,
                "filename": file.filename,
                "size": file_size
            })
        
        if not file_paths:
            raise HTTPException(status_code=400, detail="No valid files to process")
        
        # Start batch ingestion in background
        background_tasks.add_task(
            ingestion_service.ingest_batch,
            file_paths,
            document_type,
            programme_year
        )
        
        return {
            "message": f"Batch upload successful, processing {len(file_paths)} files",
            "files": file_info,
            "document_type": document_type,
            "programme_year": programme_year,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")