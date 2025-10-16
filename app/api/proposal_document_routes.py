"""
API routes for live proposal document management and editing.
Enables real-time collaborative proposal writing with AI assistance.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
from datetime import datetime
import os
import psycopg2.pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proposal-document", tags=["Proposal Document"])

# Database connection helper (singleton)
_db_pool_instance = None

def get_db_pool():
    """Get database connection pool (singleton)"""
    global _db_pool_instance
    
    if _db_pool_instance is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            try:
                _db_pool_instance = psycopg2.pool.SimpleConnectionPool(1, 20, db_url)
                logger.info("✅ Database pool created for proposal document API")
            except Exception as e:
                logger.error(f"❌ Failed to create database pool: {e}")
                return None
    
    return _db_pool_instance

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProposalSectionUpdate(BaseModel):
    """Request model for updating a proposal section"""
    content: str
    metadata: Optional[Dict[str, Any]] = None

class ProposalSectionResponse(BaseModel):
    """Response model for a proposal section"""
    section_id: str
    section_name: str
    content: str
    word_count: int
    estimated_pages: float
    last_updated: str
    quality_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ProposalDocumentResponse(BaseModel):
    """Response model for full proposal document"""
    proposal_id: int
    call_id: str
    proposal_title: str
    proposal_acronym: str
    proposal_type: str
    status: str
    created_at: str
    updated_at: str
    sections: List[ProposalSectionResponse]
    progress: Dict[str, Any]

class AIEditRequest(BaseModel):
    """Request model for AI-powered section editing"""
    instruction: str
    section_id: Optional[str] = None
    context: Optional[str] = None

# ============================================================================
# PROPOSAL DOCUMENT ENDPOINTS
# ============================================================================

@router.get("/{proposal_id}", response_model=ProposalDocumentResponse)
async def get_proposal_document(proposal_id: int):
    """
    Get the complete proposal document with all sections.
    
    **Use Case**: Load proposal in document viewer on frontend
    
    **Returns**:
    - Complete proposal metadata
    - All sections with content
    - Progress tracking information
    - Quality metrics
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        try:
            # Get proposal metadata
            cursor.execute("""
                SELECT 
                    id, user_id, call_id, proposal_title, proposal_acronym,
                    proposal_type, status, created_at, updated_at
                FROM proposals
                WHERE id = %s
            """, (proposal_id,))
            
            proposal_row = cursor.fetchone()
            if not proposal_row:
                raise HTTPException(status_code=404, detail="Proposal not found")
            
            # Get all sections
            cursor.execute("""
                SELECT 
                    section_id, section_name, content, word_count,
                    quality_score, created_at, updated_at
                FROM proposal_sections
                WHERE proposal_id = %s
                ORDER BY section_id
            """, (proposal_id,))
            
            sections = []
            for row in cursor.fetchall():
                sections.append(ProposalSectionResponse(
                    section_id=row[0],
                    section_name=row[1],
                    content=row[2] or "",
                    word_count=row[3] or 0,
                    estimated_pages=round((row[3] or 0) / 500, 1),  # ~500 words per page
                    last_updated=row[6].isoformat() if row[6] else row[5].isoformat(),
                    quality_score=row[4]
                ))
            
            # Calculate progress
            total_sections = len(sections)
            completed_sections = sum(1 for s in sections if s.word_count > 100)
            total_words = sum(s.word_count for s in sections)
            
            progress = {
                "total_sections": total_sections,
                "completed_sections": completed_sections,
                "completion_percentage": round((completed_sections / total_sections * 100) if total_sections > 0 else 0, 1),
                "total_words": total_words,
                "estimated_pages": round(total_words / 500, 1)
            }
            
            return ProposalDocumentResponse(
                proposal_id=proposal_row[0],
                call_id=proposal_row[2],
                proposal_title=proposal_row[3],
                proposal_acronym=proposal_row[4],
                proposal_type=proposal_row[5],
                status=proposal_row[6],
                created_at=proposal_row[7].isoformat(),
                updated_at=proposal_row[8].isoformat() if proposal_row[8] else proposal_row[7].isoformat(),
                sections=sections,
                progress=progress
            )
            
        finally:
            db_pool.putconn(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving proposal document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{proposal_id}/section/{section_id}", response_model=ProposalSectionResponse)
async def get_proposal_section(proposal_id: int, section_id: str):
    """
    Get a specific proposal section.
    
    **Use Case**: Load individual section for editing
    
    **Parameters**:
    - proposal_id: Proposal ID
    - section_id: Section identifier (e.g., 'excellence.objectives')
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    section_id, section_name, content, word_count,
                    quality_score, created_at, updated_at
                FROM proposal_sections
                WHERE proposal_id = %s AND section_id = %s
            """, (proposal_id, section_id))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Section not found")
            
            return ProposalSectionResponse(
                section_id=row[0],
                section_name=row[1],
                content=row[2] or "",
                word_count=row[3] or 0,
                estimated_pages=round((row[3] or 0) / 500, 1),
                last_updated=row[6].isoformat() if row[6] else row[5].isoformat(),
                quality_score=row[4]
            )
            
        finally:
            db_pool.putconn(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{proposal_id}/section/{section_id}")
async def update_proposal_section(
    proposal_id: int,
    section_id: str,
    update: ProposalSectionUpdate
):
    """
    Update a proposal section content.
    
    **Use Case**: Save manual edits or AI-generated content
    
    **Request Body**:
    - content: Updated section content (markdown)
    - metadata: Optional metadata (quality_score, etc.)
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        try:
            # Calculate word count
            word_count = len(update.content.split())
            
            # Check if section exists
            cursor.execute("""
                SELECT id FROM proposal_sections
                WHERE proposal_id = %s AND section_id = %s
            """, (proposal_id, section_id))
            
            if cursor.fetchone():
                # Update existing section
                cursor.execute("""
                    UPDATE proposal_sections
                    SET content = %s,
                        word_count = %s,
                        quality_score = %s,
                        updated_at = NOW()
                    WHERE proposal_id = %s AND section_id = %s
                """, (
                    update.content,
                    word_count,
                    update.metadata.get('quality_score') if update.metadata else None,
                    proposal_id,
                    section_id
                ))
            else:
                # Insert new section
                cursor.execute("""
                    INSERT INTO proposal_sections 
                    (proposal_id, section_id, section_name, content, word_count, quality_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    proposal_id,
                    section_id,
                    section_id.split('.')[-1].title(),  # Use last part as name
                    update.content,
                    word_count,
                    update.metadata.get('quality_score') if update.metadata else None
                ))
            
            # Update proposal timestamp
            cursor.execute("""
                UPDATE proposals
                SET updated_at = NOW()
                WHERE id = %s
            """, (proposal_id,))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "Section updated successfully",
                "word_count": word_count,
                "estimated_pages": round(word_count / 500, 1)
            }
            
        finally:
            db_pool.putconn(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/ai-edit")
async def ai_edit_section(proposal_id: int, request: AIEditRequest):
    """
    Request AI to edit a section based on natural language instruction.
    
    **Use Case**: 
    - "Make the objectives more specific"
    - "Add more detail to the methodology"
    - "Improve the innovation section"
    
    **Request Body**:
    - instruction: Natural language editing instruction
    - section_id: Optional specific section to edit
    - context: Optional additional context
    
    **Returns**: Streaming response with AI edits
    """
    try:
        # This will be handled by the conversation system
        # Return a task ID that can be used to track progress
        task_id = f"edit_{proposal_id}_{datetime.now().timestamp()}"
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "AI editing request received. Use conversation endpoint to see progress.",
            "instruction": request.instruction
        }
        
    except Exception as e:
        logger.error(f"Error creating AI edit task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{proposal_id}/progress")
async def get_proposal_progress(proposal_id: int):
    """
    Get detailed progress information for a proposal.
    
    **Use Case**: Display progress indicators, completion status
    
    **Returns**:
    - Section-by-section completion status
    - Word counts and page estimates
    - Quality scores
    - Missing sections
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        try:
            # Get all sections with their status
            cursor.execute("""
                SELECT 
                    section_id, section_name, word_count, quality_score
                FROM proposal_sections
                WHERE proposal_id = %s
                ORDER BY section_id
            """, (proposal_id,))
            
            sections_status = []
            for row in cursor.fetchall():
                word_count = row[2] or 0
                sections_status.append({
                    "section_id": row[0],
                    "section_name": row[1],
                    "word_count": word_count,
                    "status": "complete" if word_count > 100 else "draft" if word_count > 0 else "empty",
                    "quality_score": row[3],
                    "estimated_pages": round(word_count / 500, 1)
                })
            
            # Calculate overall progress
            total_sections = len(sections_status)
            complete = sum(1 for s in sections_status if s["status"] == "complete")
            draft = sum(1 for s in sections_status if s["status"] == "draft")
            empty = sum(1 for s in sections_status if s["status"] == "empty")
            
            total_words = sum(s["word_count"] for s in sections_status)
            avg_quality = sum(s["quality_score"] or 0 for s in sections_status) / total_sections if total_sections > 0 else 0
            
            return {
                "proposal_id": proposal_id,
                "overall_progress": {
                    "completion_percentage": round((complete / total_sections * 100) if total_sections > 0 else 0, 1),
                    "total_sections": total_sections,
                    "complete_sections": complete,
                    "draft_sections": draft,
                    "empty_sections": empty,
                    "total_words": total_words,
                    "estimated_pages": round(total_words / 500, 1),
                    "average_quality": round(avg_quality, 2)
                },
                "sections": sections_status
            }
            
        finally:
            db_pool.putconn(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proposal progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{proposal_id}/section/{section_id}")
async def delete_proposal_section(proposal_id: int, section_id: str):
    """
    Delete a proposal section.
    
    **Use Case**: Remove unwanted sections or start over
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM proposal_sections
                WHERE proposal_id = %s AND section_id = %s
            """, (proposal_id, section_id))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Section not found")
            
            conn.commit()
            
            return {
                "success": True,
                "message": "Section deleted successfully"
            }
            
        finally:
            db_pool.putconn(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting section: {e}")
        raise HTTPException(status_code=500, detail=str(e))

