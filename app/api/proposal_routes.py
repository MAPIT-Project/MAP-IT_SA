"""
Proposal Writing API Routes

Complete API endpoints for AI-powered proposal writing assistance.
"""

import logging
import os
from typing import Any

import psycopg2.pool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.call_document_service import CallDocumentService
from ..services.proposal_writing import (  # Phase 2 - Evaluator Simulation; Phase 2 - Gap Analysis; Phase 2 - Score Storage; Phase 3 - Smart Rewriter
    BudgetAssistant,
    ComplianceChecker,
    EvaluationCriteriaMatcher,
    EvaluatorSimulator,
    GapAnalysisService,
    GapProgressTracker,
    InlineSuggestionsService,
    ProposalDraftGenerator,
    ProposalTemplateService,
    QualityImprover,
    RealTimeAnalyzer,
    ScoreStorageService,
    SmartRewriter,
    SubmissionExporter,
    TriggerType,
    generate_score_summary,
    generate_section_report,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proposal", tags=["Proposal Writing"])

# ================================================================
# REQUEST/RESPONSE MODELS
# ================================================================


class ProposalCreate(BaseModel):
    call_id: str = Field(..., description="Call identifier")
    title: str | None = Field(None, description="Proposal title")
    acronym: str | None = Field(None, description="Proposal acronym")
    project_idea: str | None = Field(None, description="Brief project description")
    research_area: str | None = None
    duration_months: int | None = 36
    estimated_budget: float | None = None
    conversation_id: int | None = None


class PartnerInfo(BaseModel):
    name: str
    country: str
    type: str = Field(..., description="HES, REC, PRC, or OTH")
    expertise: str | None = None
    person_months: float | None = None
    avg_monthly_rate: float | None = 5000


class SectionDraftRequest(BaseModel):
    call_id: str
    section_id: str = Field(..., description="e.g., excellence.objectives")
    user_context: dict[str, Any] = Field(..., description="Project context and details")


class SectionImproveRequest(BaseModel):
    section_id: int = Field(..., description="Database section ID")
    improvement_instructions: str


class BudgetGenerationRequest(BaseModel):
    call_id: str
    proposal_type: str = Field(..., description="RIA, IA, or CSA")
    partners: list[PartnerInfo]
    duration_months: int = 36
    total_budget: float | None = None


class ComplianceCheckRequest(BaseModel):
    proposal_id: int
    sections: dict[str, str] = Field(..., description="Section ID -> content mapping")
    consortium: list[PartnerInfo] | None = []
    budget: dict[str, Any] | None = {}


# ================================================================
# DEPENDENCY INJECTION
# ================================================================


def get_db_pool():
    """Get database connection pool"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return psycopg2.pool.SimpleConnectionPool(1, 10, db_url)


def get_call_doc_service(db_pool=Depends(get_db_pool)):
    """Get CallDocumentService instance"""
    return CallDocumentService(db_pool)


def get_template_service(
    db_pool=Depends(get_db_pool), call_doc_service=Depends(get_call_doc_service)
):
    """Get ProposalTemplateService instance"""
    return ProposalTemplateService(db_pool, call_doc_service)


def get_draft_generator(
    call_doc_service=Depends(get_call_doc_service), template_service=Depends(get_template_service)
):
    """Get ProposalDraftGenerator instance"""
    return ProposalDraftGenerator(call_doc_service, template_service)


# ================================================================
# PROPOSAL MANAGEMENT ENDPOINTS
# ================================================================


@router.post("/create", summary="Create a new proposal")
async def create_proposal(proposal: ProposalCreate, db_pool=Depends(get_db_pool)):
    """
    Create a new proposal project

    This initializes a proposal with basic information and generates
    a template structure based on the call requirements.
    """

    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Determine proposal type from call documents
        call_doc_service = CallDocumentService(db_pool)
        call_doc_service.get_call_documents(proposal.call_id)

        # Get metadata to fill missing fields
        metadata = call_doc_service.get_call_metadata(proposal.call_id)

        title = proposal.title
        acronym = proposal.acronym
        project_idea = proposal.project_idea
        proposal_type = "RIA"  # Default

        if metadata:
            title = title or metadata.get("title") or "New Proposal"
            project_idea = project_idea or metadata.get("summary") or ""
            acronym = acronym or f"PROJ-{proposal.call_id.split('-')[-1]}"

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
            project_idea = project_idea or ""

        # Insert proposal
        cursor.execute(
            """
            INSERT INTO proposals (
                call_identifier, proposal_title, proposal_acronym,
                proposal_type, project_summary, research_area,
                duration_months, total_budget, conversation_id,
                status, completion_percentage
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', 0)
            RETURNING id
        """,
            (
                proposal.call_id,
                title,
                acronym,
                proposal_type,
                project_idea,
                proposal.research_area,
                proposal.duration_months,
                proposal.estimated_budget,
                proposal.conversation_id,
            ),
        )

        proposal_id = cursor.fetchone()[0]

        conn.commit()
        db_pool.putconn(conn)

        # Generate template (not async)
        template_service = ProposalTemplateService(db_pool, call_doc_service)
        template = template_service.generate_template(proposal.call_id)

        # Log activity
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO proposal_activity_log (proposal_id, activity_type, activity_description)
            VALUES (%s, 'created', %s)
        """,
            (proposal_id, f"Proposal '{proposal.title}' created"),
        )
        conn.commit()
        db_pool.putconn(conn)

        return {
            "proposal_id": proposal_id,
            "call_id": proposal.call_id,
            "title": proposal.title,
            "status": "draft",
            "template": template,
            "message": "Proposal created successfully! Ready to start writing sections.",
        }

    except Exception as e:
        logger.error(f"Error creating proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{proposal_id}", summary="Get proposal details")
async def get_proposal(proposal_id: int, db_pool=Depends(get_db_pool)):
    """Get complete proposal information"""

    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Get proposal overview
        cursor.execute(
            """
            SELECT * FROM proposal_overview WHERE id = %s
        """,
            (proposal_id,),
        )

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # Get current sections
        cursor.execute(
            """
            SELECT section_id, section_name, section_content, word_count, quality_score
            FROM proposal_sections
            WHERE proposal_id = %s AND is_current = TRUE
            ORDER BY section_order
        """,
            (proposal_id,),
        )

        sections = cursor.fetchall()

        db_pool.putconn(conn)

        return {
            "proposal_id": proposal_id,
            "overview": dict(zip([desc[0] for desc in cursor.description], row, strict=False)),
            "sections": [
                {
                    "section_id": s[0],
                    "section_name": s[1],
                    "content": s[2],
                    "word_count": s[3],
                    "quality_score": float(s[4]) if s[4] else None,
                }
                for s in sections
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list", summary="List all proposals")
async def list_proposals(status: str | None = None, limit: int = 50, db_pool=Depends(get_db_pool)):
    """List proposals with optional status filter"""

    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        if status:
            cursor.execute(
                """
                SELECT id, call_identifier, proposal_title, status,
                       completion_percentage, updated_at
                FROM proposals
                WHERE status = %s
                ORDER BY updated_at DESC
                LIMIT %s
            """,
                (status, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, call_identifier, proposal_title, status,
                       completion_percentage, updated_at
                FROM proposals
                ORDER BY updated_at DESC
                LIMIT %s
            """,
                (limit,),
            )

        proposals = cursor.fetchall()
        db_pool.putconn(conn)

        return {
            "proposals": [
                {
                    "id": p[0],
                    "call_id": p[1],
                    "title": p[2],
                    "status": p[3],
                    "completion": p[4],
                    "updated_at": p[5].isoformat() if p[5] else None,
                }
                for p in proposals
            ],
            "count": len(proposals),
        }

    except Exception as e:
        logger.error(f"Error listing proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# TEMPLATE GENERATION
# ================================================================


@router.get("/template/{call_id}", summary="Generate proposal template")
async def generate_template(
    call_id: str, template_service: ProposalTemplateService = Depends(get_template_service)
):
    """
    Generate a structured proposal template based on call requirements

    Returns the complete section structure, evaluation criteria mapping,
    and page limits for the specified call.
    """

    try:
        template = template_service.generate_template(call_id)

        return {
            "call_id": call_id,
            "template": template,
            "message": f"Template generated for {call_id}",
        }

    except Exception as e:
        logger.error(f"Error generating template: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/template/{call_id}/section/{section_id}", summary="Get section guidance")
async def get_section_guidance(
    call_id: str,
    section_id: str,
    template_service: ProposalTemplateService = Depends(get_template_service),
):
    """Get specific guidance for a proposal section"""

    try:
        guidance = template_service.get_section_guidance(call_id, section_id)

        return {"section_id": section_id, "guidance": guidance}

    except Exception as e:
        logger.error(f"Error retrieving section guidance: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# DRAFT GENERATION
# ================================================================


@router.post("/draft/generate", summary="Generate section draft")
async def generate_section_draft(
    request: SectionDraftRequest,
    draft_generator: ProposalDraftGenerator = Depends(get_draft_generator),
    db_pool=Depends(get_db_pool),
):
    """
    Generate an AI-powered draft for a proposal section

    Provide the call ID, section ID, and project context to generate
    a professional draft that addresses evaluation criteria.
    """

    try:
        # Generate draft
        draft_result = await draft_generator.generate_section_draft(
            call_id=request.call_id,
            section_id=request.section_id,
            user_context=request.user_context,
        )

        # If proposal_id is in context, save to database
        proposal_id = request.user_context.get("proposal_id")
        if proposal_id:
            conn = db_pool.getconn()
            cursor = conn.cursor()

            # Check for existing section
            cursor.execute(
                """
                UPDATE proposal_sections
                SET is_current = FALSE
                WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
            """,
                (proposal_id, request.section_id),
            )

            # Insert new version
            cursor.execute(
                """
                INSERT INTO proposal_sections (
                    proposal_id, section_id, section_name, section_content,
                    quality_score, version, is_current
                ) VALUES (%s, %s, %s, %s, %s, 1, TRUE)
                RETURNING id
            """,
                (
                    proposal_id,
                    request.section_id,
                    request.section_id.split(".")[-1].replace("_", " ").title(),
                    draft_result["draft_text"],
                    draft_result.get("quality_score", 0.7),
                ),
            )

            section_id = cursor.fetchone()[0]

            conn.commit()
            db_pool.putconn(conn)

            draft_result["section_id"] = section_id
            draft_result["saved"] = True

        return {
            "success": True,
            "call_id": request.call_id,
            "section_id": request.section_id,
            "draft": draft_result,
            "message": "Draft generated successfully!",
        }

    except Exception as e:
        logger.error(f"Error generating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/draft/improve", summary="Improve existing draft")
async def improve_draft(
    request: SectionImproveRequest,
    draft_generator: ProposalDraftGenerator = Depends(get_draft_generator),
    db_pool=Depends(get_db_pool),
):
    """Improve an existing section draft based on user instructions"""

    try:
        # Get current section content
        conn = db_pool.getconn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT section_content, section_id, proposal_id
            FROM proposal_sections
            WHERE id = %s
        """,
            (request.section_id,),
        )

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")

        original_content, section_id_str, proposal_id = row

        # Improve draft
        improved_text = await draft_generator.improve_draft(
            original_draft=original_content,
            improvement_instructions=request.improvement_instructions,
            call_id="",  # Can be retrieved from proposal
            section_id=section_id_str,
        )

        # Save as new version
        cursor.execute(
            """
            UPDATE proposal_sections
            SET is_current = FALSE
            WHERE id = %s
        """,
            (request.section_id,),
        )

        cursor.execute(
            """
            INSERT INTO proposal_sections (
                proposal_id, section_id, section_name, section_content,
                version, parent_version_id, is_current
            )
            SELECT proposal_id, section_id, section_name, %s,
                   version + 1, id, TRUE
            FROM proposal_sections
            WHERE id = %s
            RETURNING id
        """,
            (improved_text, request.section_id),
        )

        new_section_id = cursor.fetchone()[0]

        conn.commit()
        db_pool.putconn(conn)

        return {
            "success": True,
            "original_section_id": request.section_id,
            "new_section_id": new_section_id,
            "improved_text": improved_text,
            "message": "Draft improved successfully!",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error improving draft: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# EVALUATION & COMPLIANCE
# ================================================================


@router.post("/evaluate/criteria", summary="Evaluate criteria coverage")
async def evaluate_criteria(section_id: int, criteria: list[str], db_pool=Depends(get_db_pool)):
    """Analyze how well a section addresses evaluation criteria"""

    try:
        # Get section content
        conn = db_pool.getconn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT section_content, proposal_id
            FROM proposal_sections
            WHERE id = %s AND is_current = TRUE
        """,
            (section_id,),
        )

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")

        section_content, proposal_id = row

        # Get call_id from proposal
        cursor.execute(
            """
            SELECT call_identifier FROM proposals WHERE id = %s
        """,
            (proposal_id,),
        )
        call_id = cursor.fetchone()[0]

        db_pool.putconn(conn)

        # Analyze
        criteria_matcher = EvaluationCriteriaMatcher()
        analysis = await criteria_matcher.analyze_section(
            section_text=section_content, evaluation_criteria=criteria, call_id=call_id
        )

        # Store results
        conn = db_pool.getconn()
        cursor = conn.cursor()

        for criterion, data in analysis["criteria_coverage"].items():
            cursor.execute(
                """
                INSERT INTO section_criteria_mapping (
                    section_id, criterion_name, addressed, strength_score,
                    evidence, gaps
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (section_id, criterion_name)
                DO UPDATE SET
                    addressed = EXCLUDED.addressed,
                    strength_score = EXCLUDED.strength_score,
                    evidence = EXCLUDED.evidence,
                    gaps = EXCLUDED.gaps,
                    last_checked = NOW()
            """,
                (
                    section_id,
                    criterion,
                    data["addressed"],
                    data["strength"],
                    data["evidence"],
                    data["gaps"],
                ),
            )

        conn.commit()
        db_pool.putconn(conn)

        return {
            "section_id": section_id,
            "analysis": analysis,
            "message": "Criteria evaluation complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/check/compliance", summary="Run compliance checks")
async def check_compliance(
    request: ComplianceCheckRequest,
    call_doc_service=Depends(get_call_doc_service),
    db_pool=Depends(get_db_pool),
):
    """Run comprehensive compliance checks on a proposal"""

    try:
        # Get proposal details
        conn = db_pool.getconn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT call_identifier, proposal_type
            FROM proposals
            WHERE id = %s
        """,
            (request.proposal_id,),
        )

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        call_id, proposal_type = row
        db_pool.putconn(conn)

        # Build proposal data
        proposal_data = {
            "sections": request.sections,
            "consortium": [p.dict() for p in request.consortium],
            "budget": request.budget,
        }

        # Run compliance checks
        compliance_checker = ComplianceChecker(call_doc_service, db_pool)
        compliance_result = await compliance_checker.run_compliance_check(
            call_id=call_id, proposal_data=proposal_data
        )

        # Store compliance results
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Clear old checks
        cursor.execute(
            """
            DELETE FROM compliance_checks WHERE proposal_id = %s
        """,
            (request.proposal_id,),
        )

        # Insert new checks
        for check in compliance_result["detailed_checks"]:
            for issue in check["issues"]:
                cursor.execute(
                    """
                    INSERT INTO compliance_checks (
                        proposal_id, check_type, check_category,
                        check_result, result_message
                    ) VALUES (%s, %s, %s, %s, %s)
                """,
                    (
                        request.proposal_id,
                        check["check_name"],
                        "mandatory" if check["priority"] == "critical" else "recommended",
                        check["status"],
                        issue,
                    ),
                )

        conn.commit()
        db_pool.putconn(conn)

        return {
            "proposal_id": request.proposal_id,
            "compliance": compliance_result,
            "message": "Compliance check complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# BUDGET GENERATION
# ================================================================


@router.post("/budget/generate", summary="Generate budget table")
async def generate_budget(request: BudgetGenerationRequest):
    """Generate a complete budget table with all calculations"""

    try:
        budget_assistant = BudgetAssistant()

        # Prepare project params
        project_params = {
            "duration_months": request.duration_months,
            "partners": [p.dict() for p in request.partners],
            "total_budget": request.total_budget,
        }

        # Generate budget
        budget_result = await budget_assistant.generate_budget_table(
            call_id=request.call_id,
            proposal_type=request.proposal_type,
            project_params=project_params,
        )

        return {
            "success": True,
            "call_id": request.call_id,
            "budget": budget_result,
            "message": "Budget generated successfully!",
        }

    except Exception as e:
        logger.error(f"Error generating budget: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# QUALITY IMPROVEMENT
# ================================================================


@router.post("/quality/analyze", summary="Analyze section quality")
async def analyze_quality(section_id: int, db_pool=Depends(get_db_pool)):
    """Run comprehensive quality analysis on a section"""

    try:
        # Get section content
        conn = db_pool.getconn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT section_content, section_id
            FROM proposal_sections
            WHERE id = %s AND is_current = TRUE
        """,
            (section_id,),
        )

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")

        section_content, section_id_str = row
        db_pool.putconn(conn)

        # Analyze quality (uses ProposalAIService internally)
        quality_improver = QualityImprover()

        analysis = await quality_improver.analyze_quality(
            section_text=section_content, section_type=section_id_str
        )

        # Store improvement suggestions
        conn = db_pool.getconn()
        cursor = conn.cursor()

        for suggestion in analysis.get("improvement_suggestions", []):
            cursor.execute(
                """
                INSERT INTO improvement_suggestions (
                    section_id, proposal_id, suggestion_type,
                    suggestion_text, priority
                )
                SELECT %s, proposal_id, %s, %s, %s
                FROM proposal_sections
                WHERE id = %s
            """,
                (
                    section_id,
                    suggestion["type"],
                    suggestion["suggestion"],
                    suggestion["priority"],
                    section_id,
                ),
            )

        conn.commit()
        db_pool.putconn(conn)

        return {
            "section_id": section_id,
            "quality_analysis": analysis,
            "message": "Quality analysis complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing quality: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# EXPORT & FINALIZATION
# ================================================================


@router.get("/{proposal_id}/export/summary", summary="Export proposal summary")
async def export_summary(proposal_id: int, db_pool=Depends(get_db_pool)):
    """Export a complete proposal summary in JSON format"""

    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Get proposal overview
        cursor.execute("SELECT * FROM proposal_overview WHERE id = %s", (proposal_id,))
        overview = cursor.fetchone()

        if not overview:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # Get sections
        cursor.execute(
            """
            SELECT section_id, section_name, section_content, word_count
            FROM proposal_sections
            WHERE proposal_id = %s AND is_current = TRUE
            ORDER BY section_order
        """,
            (proposal_id,),
        )
        sections = cursor.fetchall()

        # Get consortium
        cursor.execute(
            """
            SELECT partner_name, partner_country, partner_type, partner_role
            FROM proposal_consortium
            WHERE proposal_id = %s
        """,
            (proposal_id,),
        )
        consortium = cursor.fetchall()

        # Get budget
        cursor.execute(
            """
            SELECT partner_name, total_eligible_costs, requested_funding
            FROM proposal_budgets
            WHERE proposal_id = %s
        """,
            (proposal_id,),
        )
        budget = cursor.fetchall()

        db_pool.putconn(conn)

        return {
            "proposal_id": proposal_id,
            "overview": {
                "title": overview[2],
                "call_id": overview[1],
                "status": overview[4],
                "completion": overview[5],
            },
            "sections": [
                {"id": s[0], "name": s[1], "content": s[2], "words": s[3]} for s in sections
            ],
            "consortium": [
                {"name": c[0], "country": c[1], "type": c[2], "role": c[3]} for c in consortium
            ],
            "budget_summary": {
                "total_eligible": sum(b[1] for b in budget) if budget else 0,
                "total_funding": sum(b[2] for b in budget) if budget else 0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# OFFICIAL DOCUMENT EXPORT ENDPOINTS
# ================================================================


@router.get("/export/{proposal_id}/part-b")
async def export_part_b_docx(proposal_id: int):
    """
    Export Part B in official Word format (.docx)

    Returns submission-ready Word document with:
    - Proper EU formatting
    - All sections (Excellence, Impact, Implementation)
    - Official structure and styling
    """

    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)

        exporter = SubmissionExporter(db_pool)
        docx_buffer = await exporter.export_part_b(proposal_id)

        db_pool.closeall()

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=proposal_{proposal_id}_PartB.docx"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting Part B: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/export/{proposal_id}/budget")
async def export_budget_excel(proposal_id: int):
    """
    Export budget in official Excel format (.xlsx)

    Returns submission-ready Excel with:
    - All partner budgets
    - Cost categories breakdown
    - Funding calculations
    - Official formatting
    """

    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)

        exporter = SubmissionExporter(db_pool)
        xlsx_buffer = await exporter.export_budget(proposal_id)

        db_pool.closeall()

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            xlsx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=proposal_{proposal_id}_Budget.xlsx"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting budget: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/export/{proposal_id}/complete-package")
async def export_complete_package(
    proposal_id: int,
    include_budget: bool = True,
    include_ethics: bool = True,
    include_security: bool = False,
):
    """
    Export complete submission package as ZIP

    Returns ZIP file containing:
    - Part B Word document
    - Budget Excel file
    - Ethics assessment (if applicable)
    - Security questionnaire (if applicable)
    - README with instructions

    READY TO SUBMIT TO EU PORTAL! 🚀
    """

    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)

        exporter = SubmissionExporter(db_pool)
        zip_buffer = await exporter.export_proposal_package(
            proposal_id,
            include_budget=include_budget,
            include_ethics=include_ethics,
            include_security=include_security,
        )

        db_pool.closeall()

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=proposal_{proposal_id}_SUBMISSION_PACKAGE.zip"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting package: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/export/{proposal_id}/ethics")
async def export_ethics_assessment(proposal_id: int):
    """Export ethics self-assessment document"""

    try:
        db_url = os.getenv("DATABASE_URL")
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)

        exporter = SubmissionExporter(db_pool)
        docx_buffer = await exporter.export_ethics_assessment(proposal_id)

        db_pool.closeall()

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=proposal_{proposal_id}_Ethics.docx"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting ethics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 2: EVALUATOR SIMULATION (Task 08)
# ================================================================


class EvaluateSectionRequest(BaseModel):
    """Request to evaluate a proposal section."""

    section_text: str = Field(..., min_length=50, description="Section content to evaluate")
    section_type: str = Field(..., description="excellence, impact, or implementation")
    section_id: str = Field(..., description="Specific section like objectives, methodology")
    action_type: str = Field(default="RIA", description="RIA, IA, or CSA")
    call_id: str | None = Field(None, description="Optional call ID for context")


class EvaluateProposalRequest(BaseModel):
    """Request to evaluate multiple sections."""

    sections: dict[str, str] = Field(..., description="section_id -> text mapping")
    action_type: str = Field(default="RIA")


@router.post("/evaluate/section", summary="Evaluate a section like an EU evaluator")
async def evaluate_section(request: EvaluateSectionRequest):
    """
    Simulate EU evaluator scoring for a proposal section.

    Returns:
    - Score on 0-5 scale (like real Horizon Europe evaluators)
    - Criterion-by-criterion breakdown
    - ESR-style summary comments
    - Specific improvements to increase score

    This helps users understand how evaluators will perceive their proposal
    and what changes would improve their score.
    """
    try:
        evaluator = EvaluatorSimulator()

        result = await evaluator.evaluate_section(
            section_text=request.section_text,
            section_type=request.section_type,
            section_id=request.section_id,
            call_id=request.call_id,
            action_type=request.action_type,
        )

        # Generate human-readable report
        report = generate_section_report(result)

        return {
            "overall_score": result.overall_score,
            "threshold_status": result.threshold_status,
            "esr_summary": result.esr_summary,
            "criterion_scores": [
                {
                    "criterion": cs.criterion,
                    "score": cs.score,
                    "justification": cs.justification,
                    "strengths": cs.strengths,
                    "weaknesses": cs.weaknesses,
                    "improvement_for_half_point": cs.improvement_for_half_point,
                }
                for cs in result.criterion_scores
            ],
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "top_improvements": result.top_improvements,
            "confidence": result.confidence,
            "formatted_report": report,
        }

    except Exception as e:
        logger.error(f"Error evaluating section: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/evaluate/proposal", summary="Evaluate full proposal")
async def evaluate_full_proposal(request: EvaluateProposalRequest):
    """
    Evaluate all sections and calculate total score with funding probability.

    Provides:
    - Total score out of 15 (like real evaluation)
    - Section-by-section breakdown
    - Funding probability estimate based on typical success rates
    - Overall assessment and prioritized recommendations
    """
    try:
        evaluator = EvaluatorSimulator()

        result = await evaluator.evaluate_full_proposal(
            sections=request.sections, action_type=request.action_type
        )

        # Add formatted summary
        result["formatted_summary"] = generate_score_summary(result)

        return result

    except Exception as e:
        logger.error(f"Error evaluating proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 2: SCORE STORAGE & TRACKING (Task 09)
# ================================================================


class SaveScoreRequest(BaseModel):
    """Request to save an evaluation score."""

    proposal_id: str
    section_id: str
    section_type: str
    content: str
    score_result: dict[str, Any]
    trigger: str = Field(default="manual", description="manual, auto, save, or batch")


@router.post("/scores/save", summary="Save section score")
async def save_section_score(request: SaveScoreRequest):
    """
    Save an evaluation score for a section.

    Stores both current score and adds to history for trend tracking.
    Deduplicates if content hasn't changed.
    """
    try:
        storage = ScoreStorageService()

        # Map trigger string to enum
        trigger_map = {
            "manual": TriggerType.MANUAL,
            "auto": TriggerType.AUTO,
            "save": TriggerType.SAVE,
            "batch": TriggerType.BATCH,
        }
        trigger = trigger_map.get(request.trigger, TriggerType.MANUAL)

        stored = await storage.save_score(
            proposal_id=request.proposal_id,
            section_id=request.section_id,
            section_type=request.section_type,
            content=request.content,
            score_result=request.score_result,
            trigger=trigger,
        )

        return {
            "id": stored.id,
            "section_id": stored.section_id,
            "predicted_score": stored.predicted_score,
            "score_tier": stored.score_tier,
            "confidence": stored.confidence,
            "created_at": stored.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error saving score: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/scores/section/{section_id}", summary="Get section score")
async def get_section_score(section_id: str):
    """Get the current predicted score for a section."""
    try:
        storage = ScoreStorageService()
        score = await storage.get_section_score(section_id)

        if not score:
            raise HTTPException(status_code=404, detail="No score found for section")

        return {
            "section_id": score.section_id,
            "predicted_score": score.predicted_score,
            "confidence": score.confidence,
            "score_tier": score.score_tier,
            "criterion_scores": score.criterion_scores,
            "strengths": score.strengths,
            "weaknesses": score.weaknesses,
            "evaluator_comments": score.evaluator_comments,
            "created_at": score.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting score: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/scores/proposal/{proposal_id}", summary="Get all proposal scores")
async def get_proposal_scores(proposal_id: str):
    """Get all section scores for a proposal."""
    try:
        storage = ScoreStorageService()
        scores = await storage.get_proposal_scores(proposal_id)

        return {
            "proposal_id": proposal_id,
            "sections": [
                {
                    "section_id": s.section_id,
                    "section_type": s.section_type,
                    "predicted_score": s.predicted_score,
                    "score_tier": s.score_tier,
                    "confidence": s.confidence,
                }
                for s in scores
            ],
            "count": len(scores),
        }

    except Exception as e:
        logger.error(f"Error getting proposal scores: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/scores/proposal/{proposal_id}/summary", summary="Get proposal score summary")
async def get_proposal_score_summary(proposal_id: str):
    """Get aggregated scores for a proposal with funding probability."""
    try:
        storage = ScoreStorageService()
        summary = await storage.get_proposal_summary(proposal_id)

        if not summary:
            raise HTTPException(status_code=404, detail="No scores found for proposal")

        completion = (
            (summary.sections_scored / summary.total_sections * 100)
            if summary.total_sections > 0
            else 0
        )

        return {
            "proposal_id": summary.proposal_id,
            "excellence_score": summary.excellence_score,
            "impact_score": summary.impact_score,
            "implementation_score": summary.implementation_score,
            "overall_score": summary.overall_score,
            "funding_probability": summary.funding_probability,
            "threshold_distance": summary.threshold_distance,
            "sections_scored": summary.sections_scored,
            "total_sections": summary.total_sections,
            "completion_percentage": round(completion, 1),
            "last_updated": summary.last_updated.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proposal summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/scores/section/{section_id}/history", summary="Get score history")
async def get_score_history(section_id: str, limit: int = 20):
    """Get score history for a section to track improvement over time."""
    try:
        storage = ScoreStorageService()

        history = await storage.get_score_history(section_id, limit=limit)
        trend_data = await storage.get_improvement_trend(section_id, days=7)

        return {
            "section_id": section_id,
            "entries": [
                {
                    "id": h.id,
                    "predicted_score": h.predicted_score,
                    "confidence": h.confidence,
                    "content_length": h.content_length,
                    "trigger_type": h.trigger_type,
                    "created_at": h.created_at.isoformat(),
                    "previous_score": h.previous_score,
                    "score_change": h.score_change,
                }
                for h in history
            ],
            "trend": trend_data["trend"],
            "trend_data": trend_data.get("data", []),
            "total_improvement": trend_data.get("total_improvement", 0),
        }

    except Exception as e:
        logger.error(f"Error getting score history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 2: GAP ANALYSIS (Task 10)
# ================================================================


class GapAnalysisRequest(BaseModel):
    """Request for gap analysis."""

    content: str = Field(..., min_length=100, description="Section content to analyze")
    section_type: str = Field(..., description="Type of section")
    current_score: float = Field(..., ge=0, le=5, description="Current predicted score")
    target_score: float | None = Field(None, ge=0, le=5, description="Target score")
    cluster: str | None = Field(None, description="HE cluster for context")


class GapClosureRequest(BaseModel):
    """Request for gap closure suggestion."""

    gap_id: str
    gap_title: str
    gap_description: str
    current_state: str
    target_state: str
    specific_action: str
    content: str
    section_type: str


@router.post("/gaps/analyze", summary="Analyze gaps to target score")
async def analyze_gaps(request: GapAnalysisRequest):
    """
    Analyze gaps between current content and target score.

    Returns:
    - List of specific gaps preventing higher score
    - Prioritized by impact-to-effort ratio
    - Specific actions to close each gap
    - Example text showing improvements
    """
    try:
        service = GapAnalysisService()

        result = await service.analyze_gaps(
            content=request.content,
            section_type=request.section_type,
            current_score=request.current_score,
            target_score=request.target_score,
            cluster=request.cluster,
        )

        return {
            "current_score": result.current_score,
            "target_score": result.target_score,
            "score_gap": result.score_gap,
            "gaps": [
                {
                    "id": g.id,
                    "category": g.category.value,
                    "severity": g.severity.value,
                    "title": g.title,
                    "description": g.description,
                    "current_state": g.current_state,
                    "target_state": g.target_state,
                    "estimated_score_impact": g.estimated_score_impact,
                    "effort": g.effort.value,
                    "specific_action": g.specific_action,
                    "example_text": g.example_text,
                    "related_criterion": g.related_criterion,
                }
                for g in result.gaps
            ],
            "critical_count": result.critical_count,
            "total_estimated_impact": result.total_estimated_impact,
            "recommended_priority_order": result.recommended_priority_order,
            "estimated_total_effort": result.estimated_total_effort,
            "achievable_score": result.achievable_score,
        }

    except Exception as e:
        logger.error(f"Error analyzing gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/gaps/close-suggestion", summary="Get gap closure suggestion")
async def get_gap_closure_suggestion(request: GapClosureRequest):
    """
    Get specific rewrite suggestion to close a gap.

    Returns text that can be directly applied to improve the section.
    """
    try:
        from ..services.proposal_writing import EffortLevel, Gap, GapCategory, GapSeverity

        service = GapAnalysisService()

        # Reconstruct gap object
        gap = Gap(
            id=request.gap_id,
            category=GapCategory.CONTENT_WEAK,
            severity=GapSeverity.MAJOR,
            title=request.gap_title,
            description=request.gap_description,
            current_state=request.current_state,
            target_state=request.target_state,
            estimated_score_impact=0.3,
            effort=EffortLevel.MODERATE,
            specific_action=request.specific_action,
        )

        result = await service.get_gap_closure_suggestion(
            gap=gap, content=request.content, section_type=request.section_type
        )

        return result

    except Exception as e:
        logger.error(f"Error getting gap closure suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/gaps/section/{section_id}/gap/{gap_id}/resolve", summary="Mark gap resolved")
async def mark_gap_resolved(section_id: str, gap_id: str, resolved: bool = True):
    """Mark a gap as resolved or unresolved for progress tracking."""
    try:
        service = GapAnalysisService()

        await service.track_gap_progress(section_id=section_id, gap_id=gap_id, resolved=resolved)

        return {
            "status": "success",
            "section_id": section_id,
            "gap_id": gap_id,
            "resolved": resolved,
        }

    except Exception as e:
        logger.error(f"Error marking gap resolved: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/gaps/section/{section_id}/progress", summary="Get section gap progress")
async def get_section_gap_progress(section_id: str):
    """Get gap closure progress for a section."""
    try:
        tracker = GapProgressTracker()
        result = await tracker.get_section_progress(section_id)

        return {
            "section_id": section_id,
            "total_gaps_identified": result["total_gaps_identified"],
            "gaps_resolved": result["gaps_resolved"],
            "completion_percentage": result["completion_percentage"],
            "score_history": result["score_history"],
            "score_improvement": result["score_improvement"],
        }

    except Exception as e:
        logger.error(f"Error getting section progress: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/gaps/proposal/{proposal_id}/progress", summary="Get proposal gap progress")
async def get_proposal_gap_progress(proposal_id: str):
    """Get overall gap progress for a proposal."""
    try:
        tracker = GapProgressTracker()
        result = await tracker.get_proposal_progress(proposal_id)

        return {
            "proposal_id": proposal_id,
            "total_gaps": result["total_gaps"],
            "resolved_gaps": result["resolved_gaps"],
            "completion_percentage": result["completion_percentage"],
            "current_avg_score": result["current_avg_score"],
        }

    except Exception as e:
        logger.error(f"Error getting proposal progress: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 2: COMBINED EVALUATE & ANALYZE ENDPOINT
# ================================================================


class EvaluateAndAnalyzeRequest(BaseModel):
    """Request to evaluate and analyze gaps in one call."""

    content: str = Field(..., min_length=100)
    section_type: str
    section_id: str
    action_type: str = "RIA"
    target_score: float | None = None
    cluster: str | None = None


@router.post("/evaluate-and-analyze", summary="Evaluate section and analyze gaps")
async def evaluate_and_analyze(request: EvaluateAndAnalyzeRequest):
    """
    Combined endpoint that:
    1. Evaluates the section like an EU evaluator
    2. Analyzes gaps to reach the target score
    3. Returns both in a single response

    This is the recommended endpoint for real-time feedback during editing.
    """
    try:
        evaluator = EvaluatorSimulator()
        gap_service = GapAnalysisService()

        # Evaluate section
        eval_result = await evaluator.evaluate_section(
            section_text=request.content,
            section_type=request.section_type,
            section_id=request.section_id,
            action_type=request.action_type,
        )

        # Analyze gaps
        gap_result = await gap_service.analyze_gaps(
            content=request.content,
            section_type=request.section_type,
            current_score=eval_result.overall_score,
            target_score=request.target_score,
            evaluation_result={
                "weaknesses": eval_result.weaknesses,
                "strengths": eval_result.strengths,
            },
            cluster=request.cluster,
        )

        return {
            "evaluation": {
                "overall_score": eval_result.overall_score,
                "threshold_status": eval_result.threshold_status,
                "esr_summary": eval_result.esr_summary,
                "strengths": eval_result.strengths,
                "weaknesses": eval_result.weaknesses,
                "top_improvements": eval_result.top_improvements,
                "confidence": eval_result.confidence,
            },
            "gap_analysis": {
                "current_score": gap_result.current_score,
                "target_score": gap_result.target_score,
                "achievable_score": gap_result.achievable_score,
                "gaps": [
                    {
                        "id": g.id,
                        "severity": g.severity.value,
                        "title": g.title,
                        "specific_action": g.specific_action,
                        "estimated_score_impact": g.estimated_score_impact,
                        "effort": g.effort.value,
                    }
                    for g in gap_result.gaps
                ],
                "priority_order": gap_result.recommended_priority_order,
                "estimated_effort": gap_result.estimated_total_effort,
            },
        }

    except Exception as e:
        logger.error(f"Error in evaluate-and-analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 3: SMART REWRITER (Task 11)
# ================================================================


class RewriteRequest(BaseModel):
    """Request to rewrite text with specific improvement focus."""

    original_text: str = Field(..., min_length=50, description="Text to rewrite")
    improvement_focus: str = Field(
        default="clarity",
        description="Focus: clarity, impact, EU terminology, conciseness, structure, persuasiveness",
    )
    section_type: str = Field(default="objectives", description="Type of section")
    preserve_length: bool = Field(default=False, description="Try to maintain similar word count")


class RewriteOptionsRequest(BaseModel):
    """Request to generate multiple rewrite options."""

    original_text: str = Field(..., min_length=50, description="Text to rewrite")
    section_type: str = Field(default="objectives", description="Type of section")


class StyleTransferRequest(BaseModel):
    """Request to rewrite using style from funded proposals."""

    original_text: str = Field(..., min_length=50, description="Text to rewrite")
    cluster: str | None = Field(None, description="HE cluster for finding similar proposals")
    action_type: str | None = Field(None, description="RIA, IA, or CSA")
    section_type: str = Field(default="objectives", description="Type of section")


class SentenceRewriteRequest(BaseModel):
    """Request to rewrite a single sentence."""

    sentence: str = Field(..., min_length=10, description="Sentence to rewrite")
    context: str = Field(default="", description="Surrounding context")
    improvement: str = Field(default="clarity", description="What to improve")


@router.post("/rewrite/improve", summary="Rewrite text with specific improvement")
async def rewrite_for_improvement(request: RewriteRequest):
    """
    Rewrite text focusing on a specific improvement.

    Improvement options:
    - clarity: Clearer language, better flow
    - impact: Stronger verbs, more persuasive
    - EU terminology: More EU terms and policy alignment
    - conciseness: Shorter, more direct
    - structure: Better headings and organization
    - persuasiveness: Stronger arguments, evidence

    Returns the rewritten text with explanations of changes made.
    """
    try:
        rewriter = SmartRewriter()

        result = await rewriter.rewrite_for_improvement(
            original_text=request.original_text,
            improvement_focus=request.improvement_focus,
            section_type=request.section_type,
            preserve_length=request.preserve_length,
        )

        return {
            "original": {"text": result.original_text, "word_count": result.word_count_original},
            "rewritten": {"text": result.rewritten_text, "word_count": result.word_count_rewritten},
            "style": result.style,
            "changes_made": result.changes_made,
            "before_after_examples": result.before_after_examples,
            "summary": result.improvement_summary,
            "predicted_score_improvement": result.predicted_score_improvement,
        }

    except Exception as e:
        logger.error(f"Error rewriting text: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rewrite/options", summary="Generate multiple rewrite versions")
async def generate_rewrite_options(request: RewriteOptionsRequest):
    """
    Generate multiple rewrite versions to choose from.

    Returns three options:
    - Concise: Shorter, more direct
    - Impactful: Stronger language, more persuasive
    - EU-aligned: More EU terminology and policy alignment

    User can pick the version that best fits their needs.
    """
    try:
        rewriter = SmartRewriter()

        options = await rewriter.generate_rewrite_options(
            original_text=request.original_text, section_type=request.section_type
        )

        return {
            "original_word_count": len(request.original_text.split()),
            "options": {
                style: {
                    "text": result.rewritten_text,
                    "word_count": result.word_count_rewritten,
                    "changes": result.changes_made[:3],  # Top 3 changes
                    "summary": result.improvement_summary,
                }
                for style, result in options.items()
            },
        }

    except Exception as e:
        logger.error(f"Error generating rewrite options: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rewrite/style-transfer", summary="Rewrite using funded proposal style")
async def rewrite_with_style_transfer(request: StyleTransferRequest):
    """
    Rewrite text using style from successful funded proposals.

    Finds similar funded projects and uses their language patterns
    to transform your text into something that sounds like a winner.
    """
    try:
        rewriter = SmartRewriter()

        result = await rewriter.rewrite_like_successful_proposal(
            original_text=request.original_text,
            cluster=request.cluster,
            action_type=request.action_type,
            section_type=request.section_type,
        )

        return {
            "original": {"text": result.original_text, "word_count": result.word_count_original},
            "rewritten": {"text": result.rewritten_text, "word_count": result.word_count_rewritten},
            "style_source": f"Funded {request.cluster or 'similar'} projects",
            "changes_made": result.changes_made,
            "before_after_examples": result.before_after_examples,
            "summary": result.improvement_summary,
            "predicted_score_improvement": result.predicted_score_improvement,
        }

    except Exception as e:
        logger.error(f"Error in style transfer rewrite: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rewrite/sentence", summary="Rewrite a single sentence")
async def rewrite_sentence(request: SentenceRewriteRequest):
    """
    Rewrite a single sentence with alternatives.

    Useful for inline editing - get 2-3 alternatives ranked by quality.
    """
    try:
        rewriter = SmartRewriter()

        result = await rewriter.rewrite_sentence(
            sentence=request.sentence, context=request.context, improvement=request.improvement
        )

        return result

    except Exception as e:
        logger.error(f"Error rewriting sentence: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rewrite/compare", summary="Compare rewrite options with scores")
async def compare_rewrite_versions(request: RewriteOptionsRequest):
    """
    Generate multiple rewrites and compare with predicted scores.

    Shows which version would likely score highest based on
    evaluator simulation.
    """
    try:
        rewriter = SmartRewriter()

        # Generate options
        options = await rewriter.generate_rewrite_options(
            original_text=request.original_text, section_type=request.section_type
        )

        # Compare versions
        comparison = await rewriter.compare_versions(
            original=request.original_text,
            rewrites=list(options.values()),
            section_type=request.section_type,
        )

        return comparison

    except Exception as e:
        logger.error(f"Error comparing rewrite versions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rewrite/all-styles", summary="Generate all 5 rewrite styles")
async def generate_all_styles(request: RewriteOptionsRequest):
    """
    Generate all five rewrite styles for maximum choice.

    Returns: concise, impactful, eu_aligned, technical, accessible

    Use this when you want to see all possible improvements.
    """
    try:
        rewriter = SmartRewriter()

        options = await rewriter.rewrite_all_styles(
            original_text=request.original_text, section_type=request.section_type
        )

        return {
            "original_word_count": len(request.original_text.split()),
            "options": {
                style: {
                    "text": result.rewritten_text,
                    "word_count": result.word_count_rewritten,
                    "changes": result.changes_made,
                    "summary": result.improvement_summary,
                    "predicted_improvement": result.predicted_score_improvement,
                }
                for style, result in options.items()
            },
            "available_styles": list(options.keys()),
        }

    except Exception as e:
        logger.error(f"Error generating all styles: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 3: INLINE SUGGESTIONS (Task 13)
# ================================================================


class InlineAnalyzeRequest(BaseModel):
    """Request for inline suggestions analysis."""

    text: str = Field(..., min_length=10, description="Text to analyze")
    section_type: str = Field(default="general", description="Type of section")
    cluster: str | None = Field(None, description="HE cluster for context")
    include_llm: bool = Field(
        default=True, description="Include AI analysis (slower but more thorough)"
    )


class QuickAnalyzeRequest(BaseModel):
    """Request for quick inline analysis (no LLM)."""

    text: str = Field(..., min_length=5, description="Text to analyze")


class TextSpanResponse(BaseModel):
    """Response model for text span."""

    start: int
    end: int
    text: str


class SuggestionResponse(BaseModel):
    """Response model for a single suggestion."""

    id: str
    span: TextSpanResponse
    category: str
    priority: str
    message: str
    suggestion: str
    replacement: str | None
    learn_more: str | None


class InlineAnalysisResponse(BaseModel):
    """Response model for inline analysis."""

    suggestions: list[SuggestionResponse]
    score_impact: float
    stats: dict[str, int]


@router.post("/suggestions/analyze", summary="Analyze text for inline suggestions")
async def analyze_inline_suggestions(request: InlineAnalyzeRequest):
    """
    Analyze text for Grammarly-style inline suggestions.

    Combines rule-based checks with optional LLM analysis for:
    - EU terminology improvements
    - Clarity issues
    - Vague claims needing quantification
    - Passive voice
    - Wordiness
    - Weak verbs
    - Impact improvements

    Returns suggestions with exact text positions for highlighting.
    """
    try:
        service = InlineSuggestionsService()

        result = await service.analyze_text(
            text=request.text,
            section_type=request.section_type,
            cluster=request.cluster,
            include_llm_analysis=request.include_llm,
        )

        return {
            "suggestions": [
                {
                    "id": s.id,
                    "span": {"start": s.span.start, "end": s.span.end, "text": s.span.text},
                    "category": s.category.value,
                    "priority": s.priority.value,
                    "message": s.message,
                    "suggestion": s.suggestion,
                    "replacement": s.replacement,
                    "learn_more": s.learn_more,
                }
                for s in result.suggestions
            ],
            "score_impact": result.score_impact,
            "stats": result.stats,
            "total_suggestions": len(result.suggestions),
        }

    except Exception as e:
        logger.error(f"Error analyzing inline suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/suggestions/analyze-quick", summary="Quick analysis (no LLM)")
async def analyze_quick(request: QuickAnalyzeRequest):
    """
    Quick analysis for real-time feedback during typing.

    Uses only rule-based checks - responds in <50ms.
    Call this on debounced input for instant feedback.
    """
    try:
        analyzer = RealTimeAnalyzer()

        result = await analyzer.analyze_quick(request.text)

        return {
            "suggestions": [
                {
                    "id": s.id,
                    "span": {"start": s.span.start, "end": s.span.end, "text": s.span.text},
                    "category": s.category.value,
                    "priority": s.priority.value,
                    "message": s.message,
                    "suggestion": s.suggestion,
                    "replacement": s.replacement,
                    "learn_more": s.learn_more,
                }
                for s in result.suggestions
            ],
            "score_impact": result.score_impact,
            "stats": result.stats,
        }

    except Exception as e:
        logger.error(f"Error in quick analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/suggestions/feedback", summary="Get quick feedback counts")
async def get_quick_feedback(request: QuickAnalyzeRequest):
    """
    Get quick feedback counts without full analysis.

    Returns category counts for UI indicators (badges, status).
    Even faster than analyze-quick - use for toolbar badges.
    """
    try:
        analyzer = RealTimeAnalyzer()
        feedback = analyzer.get_quick_feedback(request.text)

        return feedback

    except Exception as e:
        logger.error(f"Error getting quick feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/suggestions/categories", summary="Get suggestion categories")
async def get_suggestion_categories():
    """
    Get available suggestion categories with descriptions.

    Use for building category filters in the UI.
    """
    return {
        "categories": [
            {
                "id": "eu_terminology",
                "name": "EU Terminology",
                "description": "Use official European Union terminology",
                "icon": "flag-eu",
                "color": "#003399",
            },
            {
                "id": "clarity",
                "name": "Clarity",
                "description": "Make the text clearer and easier to understand",
                "icon": "lightbulb",
                "color": "#fbbf24",
            },
            {
                "id": "specificity",
                "name": "Specificity",
                "description": "Add specific details, numbers, or evidence",
                "icon": "target",
                "color": "#ef4444",
            },
            {
                "id": "impact",
                "name": "Impact",
                "description": "Strengthen impact statements",
                "icon": "trending-up",
                "color": "#10b981",
            },
            {
                "id": "passive_voice",
                "name": "Passive Voice",
                "description": "Consider using active voice",
                "icon": "edit",
                "color": "#8b5cf6",
            },
            {
                "id": "wordiness",
                "name": "Wordiness",
                "description": "Can be more concise",
                "icon": "scissors",
                "color": "#6366f1",
            },
            {
                "id": "weak_verb",
                "name": "Weak Verb",
                "description": "Consider a stronger verb",
                "icon": "zap",
                "color": "#f59e0b",
            },
            {
                "id": "vague_claim",
                "name": "Vague Claim",
                "description": "Needs quantification or evidence",
                "icon": "help-circle",
                "color": "#ef4444",
            },
        ]
    }


# ================================================================
# PHASE 3: COMBINED REWRITE WITH SUGGESTIONS
# ================================================================


class RewriteWithSuggestionsRequest(BaseModel):
    """Request for combined rewrite + suggestions."""

    original_text: str = Field(..., min_length=50)
    section_type: str = Field(default="objectives")
    improvement_focus: str = Field(default="clarity")
    include_alternatives: bool = Field(default=True)


@router.post("/rewrite/with-suggestions", summary="Rewrite and get inline suggestions")
async def rewrite_with_suggestions(request: RewriteWithSuggestionsRequest):
    """
    Combined endpoint that:
    1. Rewrites the text with specified focus
    2. Analyzes the rewritten version for remaining suggestions
    3. Optionally includes alternative rewrite options

    Use this for a complete improvement workflow in one call.
    """
    try:
        rewriter = SmartRewriter()
        suggestion_service = InlineSuggestionsService()

        # Rewrite the text
        rewrite_result = await rewriter.rewrite_for_improvement(
            original_text=request.original_text,
            improvement_focus=request.improvement_focus,
            section_type=request.section_type,
        )

        # Analyze the rewritten text for remaining issues
        suggestion_result = await suggestion_service.analyze_text(
            text=rewrite_result.rewritten_text,
            section_type=request.section_type,
            include_llm_analysis=False,  # Quick check only
        )

        response = {
            "rewritten": {
                "text": rewrite_result.rewritten_text,
                "word_count": rewrite_result.word_count_rewritten,
                "changes_made": rewrite_result.changes_made,
                "summary": rewrite_result.improvement_summary,
            },
            "remaining_suggestions": [
                {
                    "id": s.id,
                    "span": {"start": s.span.start, "end": s.span.end, "text": s.span.text},
                    "category": s.category.value,
                    "message": s.message,
                    "replacement": s.replacement,
                }
                for s in suggestion_result.suggestions
            ],
            "remaining_issues_count": len(suggestion_result.suggestions),
        }

        # Optionally include alternative styles
        if request.include_alternatives:
            alternatives = await rewriter.generate_rewrite_options(
                original_text=request.original_text, section_type=request.section_type
            )
            response["alternatives"] = {
                style: {"text": result.rewritten_text, "summary": result.improvement_summary}
                for style, result in alternatives.items()
            }

        return response

    except Exception as e:
        logger.error(f"Error in rewrite with suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ================================================================
# PHASE 4: USER EXPERIENCE ENDPOINTS
# ================================================================

# Import Phase 4 services
import json

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ..services.proposal_writing.dashboard_service import DashboardService
from ..services.proposal_writing.progress_tracking_service import ProgressTrackingService
from ..services.proposal_writing.realtime_quality_service import RealTimeQualityService

# --- Real-Time Quality Streaming Endpoints ---


class QuickScoreRequest(BaseModel):
    content: str = Field(..., description="Text content to analyze")
    section_type: str = Field(default="general", description="Type of section")


@router.post("/quality/quick-score", summary="Get quick score estimate")
async def get_quick_score(request: QuickScoreRequest):
    """
    Get quick score estimate without streaming (for polling).

    Returns instant heuristic-based score estimate.
    Very fast (<50ms), no LLM calls.
    """
    try:
        analyzer = RealTimeAnalyzer()
        service = RealTimeQualityService()

        quick_result = analyzer.get_quick_feedback(request.content)
        estimated_score = service._estimate_quick_score(request.content, quick_result)
        tier = service._get_quality_tier(estimated_score)

        return {
            "score": estimated_score,
            "tier": tier.value,
            "suggestion_count": quick_result.get("total", 0),
            "tier_message": service._get_tier_message(tier),
        }
    except Exception as e:
        logger.error(f"Error getting quick score: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


class StreamQualityRequest(BaseModel):
    content: str = Field(..., description="Text content to analyze")
    section_type: str = Field(default="general", description="Type of section")
    section_id: str = Field(..., description="Section ID for tracking")
    cluster: str | None = Field(None, description="HE cluster for context")


@router.post("/quality/stream/{section_id}", summary="Stream quality feedback (SSE)")
async def stream_quality_sse(
    section_id: str, content: str, section_type: str = "general", cluster: str | None = None
):
    """
    Server-Sent Events endpoint for streaming quality feedback.

    Alternative to WebSocket for simpler client implementation.
    Streams multiple feedback items as analysis progresses.
    """
    service = RealTimeQualityService()

    async def generate():
        async for feedback in service.stream_feedback(
            content=content, section_type=section_type, section_id=section_id, cluster=cluster
        ):
            yield f"data: {json.dumps(feedback.to_dict())}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.websocket("/quality/ws/{section_id}")
async def quality_websocket(websocket: WebSocket, section_id: str):
    """
    WebSocket endpoint for real-time quality feedback.

    Send content updates, receive streaming feedback.
    Protocol:
    - Send: {"type": "analyze", "content": "...", "section_type": "..."}
    - Receive: Multiple feedback items as JSON
    """
    await websocket.accept()
    service = RealTimeQualityService()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "analyze":
                content = data.get("content", "")
                section_type = data.get("section_type", "general")
                cluster = data.get("cluster")

                async for feedback in service.stream_feedback(
                    content=content,
                    section_type=section_type,
                    section_id=section_id,
                    cluster=cluster,
                ):
                    await websocket.send_json(feedback.to_dict())

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Quality WebSocket disconnected for section {section_id}")


# --- Progress Tracking Endpoints ---


class ProgressResponse(BaseModel):
    completion_percentage: float
    sections_completed: int
    total_sections: int
    average_score: float | None
    highest_score: float | None
    lowest_score: float | None
    gaps_resolved: int
    total_gaps: int
    suggestions_accepted: int
    rewrites_applied: int
    time_spent_minutes: int


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_activity_date: str | None
    is_active: bool


class AchievementResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    rarity: str
    icon: str
    points: int
    earned: bool = False


class CheckAchievementsRequest(BaseModel):
    user_id: str
    proposal_id: str
    word_count: int | None = 0
    total_words: int | None = 0
    score: float | None = None
    score_improvement: float | None = 0


@router.get(
    "/progress/{proposal_id}", response_model=ProgressResponse, summary="Get proposal progress"
)
async def get_proposal_progress(proposal_id: str):
    """Get progress snapshot for a proposal."""
    try:
        service = ProgressTrackingService()
        progress = await service.get_progress(proposal_id)

        return ProgressResponse(
            completion_percentage=progress.completion_percentage,
            sections_completed=progress.sections_completed,
            total_sections=progress.total_sections,
            average_score=progress.average_score,
            highest_score=progress.highest_score,
            lowest_score=progress.lowest_score,
            gaps_resolved=progress.gaps_resolved,
            total_gaps=progress.total_gaps,
            suggestions_accepted=progress.suggestions_accepted,
            rewrites_applied=progress.rewrites_applied,
            time_spent_minutes=progress.time_spent_minutes,
        )
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/progress/user/{user_id}/streak", response_model=StreakResponse, summary="Get user streak"
)
async def get_user_streak(user_id: str):
    """Get user's current writing streak."""
    try:
        service = ProgressTrackingService()
        streak = await service.get_streak(user_id)

        return StreakResponse(
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            last_activity_date=(
                str(streak.last_activity_date) if streak.last_activity_date else None
            ),
            is_active=streak.is_active,
        )
    except Exception as e:
        logger.error(f"Error getting streak: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/progress/user/{user_id}/record-activity", summary="Record user activity")
async def record_user_activity(user_id: str):
    """Record user activity for streak tracking."""
    try:
        service = ProgressTrackingService()
        streak = await service.record_activity(user_id)

        return {"current_streak": streak.current_streak, "is_active": streak.is_active}
    except Exception as e:
        logger.error(f"Error recording activity: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/progress/achievements/all", summary="Get all achievements")
async def get_all_achievements(user_id: str | None = None):
    """Get all available achievements, optionally with user's earned status."""
    try:
        service = ProgressTrackingService()
        achievements = await service.get_all_achievements(user_id)

        return {"achievements": achievements}
    except Exception as e:
        logger.error(f"Error getting achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/progress/check-achievements", summary="Check and award achievements")
async def check_achievements(request: CheckAchievementsRequest):
    """Check and award any newly earned achievements."""
    try:
        service = ProgressTrackingService()

        context = {
            "word_count": request.word_count,
            "total_words": request.total_words,
            "score": request.score,
            "score_improvement": request.score_improvement,
        }

        new_achievements = await service.check_achievements(
            user_id=request.user_id, proposal_id=request.proposal_id, context=context
        )

        return {
            "new_achievements": [
                {
                    "id": a.achievement_id,
                    "name": a.achievement.name,
                    "description": a.achievement.description,
                    "icon": a.achievement.icon,
                    "points": a.achievement.points,
                    "rarity": a.achievement.rarity.value,
                }
                for a in new_achievements
            ]
        }
    except Exception as e:
        logger.error(f"Error checking achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Dashboard Endpoints ---


class SectionSummaryResponse(BaseModel):
    id: str
    title: str
    section_type: str
    status: str
    word_count: int
    score: float | None
    gap_count: int
    suggestion_count: int


class NextActionResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    section_id: str | None
    section_title: str | None
    action_type: str
    estimated_minutes: int
    impact: str


class ReadinessCheckResponse(BaseModel):
    id: str
    category: str
    title: str
    description: str
    passed: bool
    details: str | None
    blocking: bool


class DashboardResponse(BaseModel):
    proposal_id: str
    proposal_title: str
    call_title: str | None
    deadline: str | None

    completion_percentage: float
    overall_score: float | None
    funding_probability: float | None
    submission_ready: bool

    sections: list[SectionSummaryResponse]
    sections_by_status: dict[str, int]

    next_actions: list[NextActionResponse]
    readiness_checks: list[ReadinessCheckResponse]
    readiness_score: float

    time_spent_minutes: int
    days_until_deadline: int | None
    streak: int


@router.get(
    "/dashboard/{proposal_id}", response_model=DashboardResponse, summary="Get proposal dashboard"
)
async def get_proposal_dashboard(proposal_id: str, user_id: str):
    """
    Get complete dashboard data for a proposal.

    Returns comprehensive view including:
    - Section summaries with scores
    - Prioritized next actions
    - Submission readiness checks
    - Progress metrics
    """
    try:
        service = DashboardService()
        data = await service.get_dashboard(proposal_id, user_id)

        return DashboardResponse(
            proposal_id=data.proposal_id,
            proposal_title=data.proposal_title,
            call_title=data.call_title,
            deadline=data.deadline.isoformat() if data.deadline else None,
            completion_percentage=data.completion_percentage,
            overall_score=data.overall_score,
            funding_probability=data.funding_probability,
            submission_ready=data.submission_ready,
            sections=[
                SectionSummaryResponse(
                    id=s.id,
                    title=s.title,
                    section_type=s.section_type,
                    status=s.status.value,
                    word_count=s.word_count,
                    score=s.score,
                    gap_count=s.gap_count,
                    suggestion_count=s.suggestion_count,
                )
                for s in data.sections
            ],
            sections_by_status=data.sections_by_status,
            next_actions=[
                NextActionResponse(
                    id=a.id,
                    title=a.title,
                    description=a.description,
                    priority=a.priority.value,
                    section_id=a.section_id,
                    section_title=a.section_title,
                    action_type=a.action_type,
                    estimated_minutes=a.estimated_minutes,
                    impact=a.impact,
                )
                for a in data.next_actions
            ],
            readiness_checks=[
                ReadinessCheckResponse(
                    id=c.id,
                    category=c.category,
                    title=c.title,
                    description=c.description,
                    passed=c.passed,
                    details=c.details,
                    blocking=c.blocking,
                )
                for c in data.readiness_checks
            ],
            readiness_score=data.readiness_score,
            time_spent_minutes=data.time_spent_minutes,
            days_until_deadline=data.days_until_deadline,
            streak=data.streak,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/dashboard/{proposal_id}/summary", summary="Get quick dashboard summary")
async def get_dashboard_summary(proposal_id: str):
    """Get a quick summary (lighter than full dashboard)."""
    try:
        service = DashboardService()
        summary = await service.get_quick_summary(proposal_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
