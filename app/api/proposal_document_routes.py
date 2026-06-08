"""
API routes for live proposal document management and editing.
Enables real-time collaborative proposal writing with AI assistance.
"""

import logging
import os
from datetime import datetime
from typing import Any

import psycopg2.pool
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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
    metadata: dict[str, Any] | None = None


class ProposalSectionResponse(BaseModel):
    """Response model for a proposal section"""

    section_id: str
    section_name: str
    content: str
    word_count: int
    estimated_pages: float
    last_updated: str
    quality_score: float | None = None
    metadata: dict[str, Any] | None = None


class ProposalDocumentResponse(BaseModel):
    """Response model for full proposal document"""

    proposal_id: int
    call_id: str | None = ""
    proposal_title: str | None = ""
    proposal_acronym: str | None = ""
    proposal_type: str | None = "RIA"
    status: str | None = "draft"
    created_at: str | None = ""
    updated_at: str | None = ""
    sections: list[ProposalSectionResponse] = []
    progress: dict[str, Any] = {}


class AIEditRequest(BaseModel):
    """Request model for AI-powered section editing"""

    instruction: str
    section_id: str | None = None
    context: str | None = None


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
            cursor.execute(
                """
                SELECT
                    id, user_id, call_identifier, proposal_title, proposal_acronym,
                    proposal_type, status, created_at, updated_at
                FROM proposals
                WHERE id = %s
            """,
                (proposal_id,),
            )

            proposal_row = cursor.fetchone()
            if not proposal_row:
                raise HTTPException(status_code=404, detail="Proposal not found")

            # Get all sections (only current versions)
            cursor.execute(
                """
                SELECT
                    section_id, section_name, section_content, word_count,
                    quality_score, created_at, COALESCE(created_at, NOW()) as updated_at
                FROM proposal_sections
                WHERE proposal_id = %s AND is_current = TRUE
                ORDER BY section_order, section_id
            """,
                (proposal_id,),
            )

            sections = []
            for row in cursor.fetchall():
                sections.append(
                    ProposalSectionResponse(
                        section_id=row[0],
                        section_name=row[1],
                        content=row[2] or "",
                        word_count=row[3] or 0,
                        estimated_pages=round((row[3] or 0) / 500, 1),  # ~500 words per page
                        last_updated=row[6].isoformat() if row[6] else row[5].isoformat(),
                        quality_score=row[4],
                    )
                )

            # Calculate progress
            total_sections = len(sections)
            completed_sections = sum(1 for s in sections if s.word_count > 100)
            total_words = sum(s.word_count for s in sections)

            progress = {
                "total_sections": total_sections,
                "completed_sections": completed_sections,
                "completion_percentage": round(
                    (completed_sections / total_sections * 100) if total_sections > 0 else 0, 1
                ),
                "total_words": total_words,
                "estimated_pages": round(total_words / 500, 1),
            }

            return ProposalDocumentResponse(
                proposal_id=proposal_row[0],
                call_id=proposal_row[2] or "",
                proposal_title=proposal_row[3] or "Untitled",
                proposal_acronym=proposal_row[4] or "",
                proposal_type=proposal_row[5] or "RIA",
                status=proposal_row[6] or "draft",
                created_at=proposal_row[7].isoformat() if proposal_row[7] else "",
                updated_at=(
                    proposal_row[8].isoformat()
                    if proposal_row[8]
                    else (proposal_row[7].isoformat() if proposal_row[7] else "")
                ),
                sections=sections,
                progress=progress,
            )

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving proposal document: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{proposal_id}")
async def delete_proposal(proposal_id: int):
    """
    Delete a proposal and its sections.
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")

        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Try to delete sections first (in case ON DELETE CASCADE is missing)
                cursor.execute(
                    "DELETE FROM proposal_sections WHERE proposal_id = %s", (proposal_id,)
                )

                # Delete proposal
                cursor.execute("DELETE FROM proposals WHERE id = %s RETURNING id", (proposal_id,))

                if not cursor.fetchone():
                    conn.rollback()
                    raise HTTPException(status_code=404, detail="Proposal not found")

                conn.commit()
                return {"message": "Proposal deleted successfully"}

        except Exception:
            conn.rollback()
            raise
        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
            cursor.execute(
                """
                SELECT
                    section_id, section_name, section_content, word_count,
                    quality_score, created_at, COALESCE(created_at, NOW()) as updated_at
                FROM proposal_sections
                WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
            """,
                (proposal_id, section_id),
            )

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
                quality_score=row[4],
            )

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving section: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{proposal_id}/section/{section_id}")
async def update_proposal_section(proposal_id: int, section_id: str, update: ProposalSectionUpdate):
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

            # Check if section exists (current version)
            cursor.execute(
                """
                SELECT id FROM proposal_sections
                WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
            """,
                (proposal_id, section_id),
            )

            existing = cursor.fetchone()
            if existing:
                # Update existing section content
                cursor.execute(
                    """
                    UPDATE proposal_sections
                    SET section_content = %s,
                        word_count = %s,
                        quality_score = COALESCE(%s, quality_score)
                    WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
                """,
                    (
                        update.content,
                        word_count,
                        update.metadata.get("quality_score") if update.metadata else None,
                        proposal_id,
                        section_id,
                    ),
                )
            else:
                # Insert new section
                cursor.execute(
                    """
                    INSERT INTO proposal_sections
                    (proposal_id, section_id, section_name, section_content, word_count, quality_score, is_current)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                """,
                    (
                        proposal_id,
                        section_id,
                        section_id.split(".")[-1]
                        .replace("_", " ")
                        .title(),  # Use last part as name
                        update.content,
                        word_count,
                        update.metadata.get("quality_score") if update.metadata else None,
                    ),
                )

            # Update proposal timestamp
            cursor.execute(
                """
                UPDATE proposals
                SET updated_at = NOW()
                WHERE id = %s
            """,
                (proposal_id,),
            )

            conn.commit()

            return {
                "success": True,
                "message": "Section updated successfully",
                "word_count": word_count,
                "estimated_pages": round(word_count / 500, 1),
            }

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating section: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
            "instruction": request.instruction,
        }

    except Exception as e:
        logger.error(f"Error creating AI edit task: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
            # Get all sections with their status (current versions only)
            cursor.execute(
                """
                SELECT
                    section_id, section_name, word_count, quality_score
                FROM proposal_sections
                WHERE proposal_id = %s AND is_current = TRUE
                ORDER BY section_order, section_id
            """,
                (proposal_id,),
            )

            sections_status = []
            for row in cursor.fetchall():
                word_count = row[2] or 0
                sections_status.append(
                    {
                        "section_id": row[0],
                        "section_name": row[1],
                        "word_count": word_count,
                        "status": (
                            "complete"
                            if word_count > 100
                            else "draft"
                            if word_count > 0
                            else "empty"
                        ),
                        "quality_score": row[3],
                        "estimated_pages": round(word_count / 500, 1),
                    }
                )

            # Calculate overall progress
            total_sections = len(sections_status)
            complete = sum(1 for s in sections_status if s["status"] == "complete")
            draft = sum(1 for s in sections_status if s["status"] == "draft")
            empty = sum(1 for s in sections_status if s["status"] == "empty")

            total_words = sum(s["word_count"] for s in sections_status)
            avg_quality = (
                sum(s["quality_score"] or 0 for s in sections_status) / total_sections
                if total_sections > 0
                else 0
            )

            return {
                "proposal_id": proposal_id,
                "overall_progress": {
                    "completion_percentage": round(
                        (complete / total_sections * 100) if total_sections > 0 else 0, 1
                    ),
                    "total_sections": total_sections,
                    "complete_sections": complete,
                    "draft_sections": draft,
                    "empty_sections": empty,
                    "total_words": total_words,
                    "estimated_pages": round(total_words / 500, 1),
                    "average_quality": round(avg_quality, 2),
                },
                "sections": sections_status,
            }

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proposal progress: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
            cursor.execute(
                """
                DELETE FROM proposal_sections
                WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
            """,
                (proposal_id, section_id),
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Section not found")

            conn.commit()

            return {"success": True, "message": "Section deleted successfully"}

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting section: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# LIST & CREATE PROPOSALS
# ============================================================================


class ProposalCreateRequest(BaseModel):
    """Request model for creating a new proposal"""

    call_id: str
    proposal_title: str | None = None
    proposal_acronym: str | None = None
    proposal_type: str | None = "RIA"
    user_id: str | None = None


@router.get("", response_model=list[ProposalDocumentResponse])
async def list_proposals(
    user_id: str | None = Query(None, description="Filter by user ID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max results to return"),
):
    """
    List all proposals, optionally filtered by user or status.

    **Use Case**: Display proposals list on dashboard
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")

        conn = db_pool.getconn()
        cursor = conn.cursor()

        try:
            # Build query with filters
            query = """
                SELECT
                    id, user_id, call_identifier, proposal_title, proposal_acronym,
                    proposal_type, status, created_at, updated_at
                FROM proposals
                WHERE 1=1
            """
            params = []

            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)

            if status:
                query += " AND status = %s"
                params.append(status)

            query += " ORDER BY updated_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            proposals = []

            for row in cursor.fetchall():
                proposal_id = row[0]

                # Get sections for this proposal
                cursor.execute(
                    """
                    SELECT
                        section_id, section_name, section_content, word_count,
                        quality_score, created_at
                    FROM proposal_sections
                    WHERE proposal_id = %s AND is_current = TRUE
                    ORDER BY section_order, section_id
                """,
                    (proposal_id,),
                )

                sections = []
                for sec_row in cursor.fetchall():
                    sections.append(
                        ProposalSectionResponse(
                            section_id=sec_row[0],
                            section_name=sec_row[1],
                            content=sec_row[2] or "",
                            word_count=sec_row[3] or 0,
                            estimated_pages=round((sec_row[3] or 0) / 500, 1),
                            last_updated=sec_row[5].isoformat() if sec_row[5] else "",
                            quality_score=sec_row[4],
                        )
                    )

                # Calculate progress
                total_sections = len(sections) or 12  # Default to 12 if no sections
                completed_sections = sum(1 for s in sections if s.word_count > 100)
                total_words = sum(s.word_count for s in sections)

                progress = {
                    "total_sections": total_sections,
                    "completed_sections": completed_sections,
                    "completion_percentage": round(
                        (completed_sections / total_sections * 100) if total_sections > 0 else 0, 1
                    ),
                    "total_words": total_words,
                    "estimated_pages": round(total_words / 500, 1),
                }

                proposals.append(
                    ProposalDocumentResponse(
                        proposal_id=row[0],
                        call_id=row[2] or "",
                        proposal_title=row[3] or "Untitled",
                        proposal_acronym=row[4] or "",
                        proposal_type=row[5] or "RIA",
                        status=row[6] or "draft",
                        created_at=row[7].isoformat() if row[7] else "",
                        updated_at=row[8].isoformat() if row[8] else "",
                        sections=sections,
                        progress=progress,
                    )
                )

            return proposals

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def get_template_sections(proposal_type: str) -> list[tuple]:
    """
    Get the correct section structure based on proposal type.
    Uses official Horizon Europe Part B templates.
    """
    proposal_type = (proposal_type or "RIA").upper()

    if proposal_type in ["RIA", "IA"]:
        # Standard RIA/IA template (Part B)
        return [
            ("excellence.objectives", "Objectives and ambition", 1),
            ("excellence.methodology", "Methodology", 2),
            ("excellence.beyond_sota", "Beyond the state of the art", 3),
            ("impact.pathways", "Pathways to impact", 4),
            ("impact.dissemination", "Dissemination and exploitation", 5),
            ("implementation.work_plan", "Work plan and resources", 6),
            ("implementation.consortium", "Consortium and management", 7),
        ]

    elif proposal_type == "CSA":
        # Coordination and Support Action template
        return [
            ("excellence.objectives", "Objectives and activities", 1),
            ("excellence.added_value", "European added value", 2),
            ("impact.outcomes", "Expected outcomes", 3),
            ("implementation.work_plan", "Work plan", 4),
        ]

    elif proposal_type in ["ERC-STG", "ERC-COG", "ERC-ADG"]:
        # ERC template (different structure)
        return [
            ("excellence.groundbreaking", "Groundbreaking nature of the research", 1),
            ("excellence.methodology", "Methodology", 2),
            ("excellence.resources", "Resources", 3),
            ("pi.cv", "Principal Investigator CV", 4),
            ("pi.track_record", "Track record", 5),
        ]

    elif proposal_type in ["MSCA-PF", "MSCA-DN"]:
        # MSCA template
        return [
            ("excellence.quality", "Quality and pertinence of the project", 1),
            ("excellence.training", "Quality and appropriateness of the training", 2),
            ("impact.career", "Career development", 3),
            ("impact.contribution", "Contribution to EU policy objectives", 4),
            ("implementation.workplan", "Work packages and methodology", 5),
            ("implementation.institutional", "Institutional environment", 6),
        ]

    elif proposal_type in ["EIC-ACCELERATOR", "EIC-PATHFINDER"]:
        # EIC template
        return [
            ("excellence.breakthrough", "Excellence - Breakthrough innovation", 1),
            ("excellence.approach", "Excellence - Approach", 2),
            ("impact.market", "Impact - Market potential", 3),
            ("impact.scale_up", "Impact - Scale-up potential", 4),
            ("implementation.team", "Implementation - Team", 5),
            ("implementation.resources", "Implementation - Resources", 6),
        ]

    # Default to RIA template
    return get_template_sections("RIA")


@router.post("", response_model=dict[str, Any])
async def create_proposal(request: ProposalCreateRequest):
    """
    Create a new proposal with section structure based on proposal type.

    Uses official Horizon Europe templates:
    - RIA/IA: 7 sections (Excellence, Impact, Implementation)
    - CSA: 4 sections
    - ERC: 5 sections
    - MSCA: 6 sections
    - EIC: 6 sections

    **Use Case**: Create new proposal from proposals dashboard

    **Returns**: Created proposal with initialized sections
    """
    try:
        db_pool = get_db_pool()
        if not db_pool:
            raise HTTPException(status_code=503, detail="Database not available")

        conn = db_pool.getconn()
        cursor = conn.cursor()

        try:
            from ..services.call_document_service import CallDocumentService

            # Determine proposal type and other details from call documents
            call_doc_service = CallDocumentService(db_pool)
            call_doc_service.get_call_documents(request.call_id)

            # Get metadata to fill missing fields
            metadata = call_doc_service.get_call_metadata(request.call_id)

            title = request.proposal_title
            acronym = request.proposal_acronym
            proposal_type = request.proposal_type or "RIA"

            if metadata:
                title = title or metadata.get("title") or "New Proposal"
                acronym = acronym or f"PROJ-{request.call_id.split('-')[-1]}"

                types_of_action = metadata.get("types_of_action", [])
                if types_of_action:
                    action_str = types_of_action[0]
                    if "RIA" in action_str:
                        proposal_type = "RIA"
                    elif "IA" in action_str:
                        proposal_type = "IA"
                    elif "CSA" in action_str:
                        proposal_type = "CSA"
            else:
                title = title or "New Proposal"
                acronym = acronym or "NEWPROJ"

            # Insert the proposal
            cursor.execute(
                """
                INSERT INTO proposals
                (call_identifier, proposal_title, proposal_acronym, proposal_type, user_id, status)
                VALUES (%s, %s, %s, %s, %s, 'draft')
                RETURNING id, created_at, updated_at
            """,
                (
                    request.call_id,
                    title,
                    acronym,
                    proposal_type,
                    request.user_id,
                ),
            )

            result = cursor.fetchone()
            proposal_id = result[0]
            created_at = result[1]
            updated_at = result[2]

            # Get correct sections based on proposal type
            template_sections = get_template_sections(proposal_type)

            for section_id, section_name, order in template_sections:
                cursor.execute(
                    """
                    INSERT INTO proposal_sections
                    (proposal_id, section_id, section_name, section_content, word_count, section_order, is_current)
                    VALUES (%s, %s, %s, '', 0, %s, TRUE)
                """,
                    (proposal_id, section_id, section_name, order),
                )

            conn.commit()

            logger.info(
                f"✅ Created proposal {proposal_id} with {len(template_sections)} sections for {proposal_type}"
            )

            # Return the created proposal
            return {
                "success": True,
                "proposal": {
                    "proposal_id": proposal_id,
                    "call_id": request.call_id,
                    "proposal_title": title,
                    "proposal_acronym": acronym,
                    "proposal_type": proposal_type,
                    "status": "draft",
                    "created_at": created_at.isoformat() if created_at else "",
                    "updated_at": updated_at.isoformat() if updated_at else "",
                },
                "sections_created": len(template_sections),
                "message": f"Proposal created successfully with {len(template_sections)} sections for {proposal_type}",
            }

        finally:
            db_pool.putconn(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
