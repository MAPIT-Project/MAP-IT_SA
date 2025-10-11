"""
Proposal Writing API Routes

Complete API endpoints for AI-powered proposal writing assistance.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..services.proposal_writing import (
    ProposalTemplateService,
    ProposalDraftGenerator,
    EvaluationCriteriaMatcher,
    BudgetAssistant,
    ComplianceChecker,
    QualityImprover,
    SubmissionExporter
)
from ..services.call_document_service import CallDocumentService
from ..services.ai_intent_service import AIIntentService
import psycopg2.pool
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proposal", tags=["Proposal Writing"])

# ================================================================
# REQUEST/RESPONSE MODELS
# ================================================================

class ProposalCreate(BaseModel):
    call_id: str = Field(..., description="Call identifier")
    title: str = Field(..., description="Proposal title")
    acronym: Optional[str] = Field(None, description="Proposal acronym")
    project_idea: str = Field(..., description="Brief project description")
    research_area: Optional[str] = None
    duration_months: Optional[int] = 36
    estimated_budget: Optional[float] = None
    conversation_id: Optional[int] = None

class PartnerInfo(BaseModel):
    name: str
    country: str
    type: str = Field(..., description="HES, REC, PRC, or OTH")
    expertise: Optional[str] = None
    person_months: Optional[float] = None
    avg_monthly_rate: Optional[float] = 5000

class SectionDraftRequest(BaseModel):
    call_id: str
    section_id: str = Field(..., description="e.g., excellence.objectives")
    user_context: Dict[str, Any] = Field(..., description="Project context and details")
    
class SectionImproveRequest(BaseModel):
    section_id: int = Field(..., description="Database section ID")
    improvement_instructions: str

class BudgetGenerationRequest(BaseModel):
    call_id: str
    proposal_type: str = Field(..., description="RIA, IA, or CSA")
    partners: List[PartnerInfo]
    duration_months: int = 36
    total_budget: Optional[float] = None

class ComplianceCheckRequest(BaseModel):
    proposal_id: int
    sections: Dict[str, str] = Field(..., description="Section ID -> content mapping")
    consortium: Optional[List[PartnerInfo]] = []
    budget: Optional[Dict[str, Any]] = {}

# ================================================================
# DEPENDENCY INJECTION
# ================================================================

def get_db_pool():
    """Get database connection pool"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return psycopg2.pool.SimpleConnectionPool(1, 10, db_url)

def get_call_doc_service(db_pool = Depends(get_db_pool)):
    """Get CallDocumentService instance"""
    return CallDocumentService(db_pool)

def get_template_service(
    db_pool = Depends(get_db_pool),
    call_doc_service = Depends(get_call_doc_service)
):
    """Get ProposalTemplateService instance"""
    return ProposalTemplateService(db_pool, call_doc_service)

def get_draft_generator(
    call_doc_service = Depends(get_call_doc_service),
    template_service = Depends(get_template_service)
):
    """Get ProposalDraftGenerator instance"""
    return ProposalDraftGenerator(call_doc_service, template_service)

# ================================================================
# PROPOSAL MANAGEMENT ENDPOINTS
# ================================================================

@router.post("/create", summary="Create a new proposal")
async def create_proposal(
    proposal: ProposalCreate,
    db_pool = Depends(get_db_pool)
):
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
        call_docs = await call_doc_service.get_call_documents(proposal.call_id)
        
        # Simple type detection (can be enhanced)
        proposal_type = "RIA"  # Default
        
        # Insert proposal
        cursor.execute("""
            INSERT INTO proposals (
                call_identifier, proposal_title, proposal_acronym,
                proposal_type, project_summary, research_area,
                duration_months, total_budget, conversation_id,
                status, completion_percentage
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', 0)
            RETURNING id
        """, (
            proposal.call_id,
            proposal.title,
            proposal.acronym,
            proposal_type,
            proposal.project_idea,
            proposal.research_area,
            proposal.duration_months,
            proposal.estimated_budget,
            proposal.conversation_id
        ))
        
        proposal_id = cursor.fetchone()[0]
        
        conn.commit()
        db_pool.putconn(conn)
        
        # Generate template (not async)
        template_service = ProposalTemplateService(db_pool, call_doc_service)
        template = template_service.generate_template(proposal.call_id)
        
        # Log activity
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO proposal_activity_log (proposal_id, activity_type, activity_description)
            VALUES (%s, 'created', %s)
        """, (proposal_id, f"Proposal '{proposal.title}' created"))
        conn.commit()
        db_pool.putconn(conn)
        
        return {
            "proposal_id": proposal_id,
            "call_id": proposal.call_id,
            "title": proposal.title,
            "status": "draft",
            "template": template,
            "message": "Proposal created successfully! Ready to start writing sections."
        }
        
    except Exception as e:
        logger.error(f"Error creating proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{proposal_id}", summary="Get proposal details")
async def get_proposal(
    proposal_id: int,
    db_pool = Depends(get_db_pool)
):
    """Get complete proposal information"""
    
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Get proposal overview
        cursor.execute("""
            SELECT * FROM proposal_overview WHERE id = %s
        """, (proposal_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Get current sections
        cursor.execute("""
            SELECT section_id, section_name, section_content, word_count, quality_score
            FROM proposal_sections
            WHERE proposal_id = %s AND is_current = TRUE
            ORDER BY section_order
        """, (proposal_id,))
        
        sections = cursor.fetchall()
        
        db_pool.putconn(conn)
        
        return {
            "proposal_id": proposal_id,
            "overview": dict(zip([desc[0] for desc in cursor.description], row)),
            "sections": [
                {
                    "section_id": s[0],
                    "section_name": s[1],
                    "content": s[2],
                    "word_count": s[3],
                    "quality_score": float(s[4]) if s[4] else None
                }
                for s in sections
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", summary="List all proposals")
async def list_proposals(
    status: Optional[str] = None,
    limit: int = 50,
    db_pool = Depends(get_db_pool)
):
    """List proposals with optional status filter"""
    
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT id, call_identifier, proposal_title, status, 
                       completion_percentage, updated_at
                FROM proposals
                WHERE status = %s
                ORDER BY updated_at DESC
                LIMIT %s
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT id, call_identifier, proposal_title, status,
                       completion_percentage, updated_at
                FROM proposals
                ORDER BY updated_at DESC
                LIMIT %s
            """, (limit,))
        
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
                    "updated_at": p[5].isoformat() if p[5] else None
                }
                for p in proposals
            ],
            "count": len(proposals)
        }
        
    except Exception as e:
        logger.error(f"Error listing proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# TEMPLATE GENERATION
# ================================================================

@router.get("/template/{call_id}", summary="Generate proposal template")
async def generate_template(
    call_id: str,
    template_service: ProposalTemplateService = Depends(get_template_service)
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
            "message": f"Template generated for {call_id}"
        }
        
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/template/{call_id}/section/{section_id}", summary="Get section guidance")
async def get_section_guidance(
    call_id: str,
    section_id: str,
    template_service: ProposalTemplateService = Depends(get_template_service)
):
    """Get specific guidance for a proposal section"""
    
    try:
        guidance = template_service.get_section_guidance(call_id, section_id)
        
        return {
            "section_id": section_id,
            "guidance": guidance
        }
        
    except Exception as e:
        logger.error(f"Error retrieving section guidance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# DRAFT GENERATION
# ================================================================

@router.post("/draft/generate", summary="Generate section draft")
async def generate_section_draft(
    request: SectionDraftRequest,
    draft_generator: ProposalDraftGenerator = Depends(get_draft_generator),
    db_pool = Depends(get_db_pool)
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
            user_context=request.user_context
        )
        
        # If proposal_id is in context, save to database
        proposal_id = request.user_context.get('proposal_id')
        if proposal_id:
            conn = db_pool.getconn()
            cursor = conn.cursor()
            
            # Check for existing section
            cursor.execute("""
                UPDATE proposal_sections
                SET is_current = FALSE
                WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
            """, (proposal_id, request.section_id))
            
            # Insert new version
            cursor.execute("""
                INSERT INTO proposal_sections (
                    proposal_id, section_id, section_name, section_content,
                    quality_score, version, is_current
                ) VALUES (%s, %s, %s, %s, %s, 1, TRUE)
                RETURNING id
            """, (
                proposal_id,
                request.section_id,
                request.section_id.split('.')[-1].replace('_', ' ').title(),
                draft_result['draft_text'],
                draft_result.get('quality_score', 0.7)
            ))
            
            section_id = cursor.fetchone()[0]
            
            conn.commit()
            db_pool.putconn(conn)
            
            draft_result['section_id'] = section_id
            draft_result['saved'] = True
        
        return {
            "success": True,
            "call_id": request.call_id,
            "section_id": request.section_id,
            "draft": draft_result,
            "message": "Draft generated successfully!"
        }
        
    except Exception as e:
        logger.error(f"Error generating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/draft/improve", summary="Improve existing draft")
async def improve_draft(
    request: SectionImproveRequest,
    draft_generator: ProposalDraftGenerator = Depends(get_draft_generator),
    db_pool = Depends(get_db_pool)
):
    """Improve an existing section draft based on user instructions"""
    
    try:
        # Get current section content
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT section_content, section_id, proposal_id
            FROM proposal_sections
            WHERE id = %s
        """, (request.section_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")
        
        original_content, section_id_str, proposal_id = row
        
        # Improve draft
        improved_text = await draft_generator.improve_draft(
            original_draft=original_content,
            improvement_instructions=request.improvement_instructions,
            call_id="",  # Can be retrieved from proposal
            section_id=section_id_str
        )
        
        # Save as new version
        cursor.execute("""
            UPDATE proposal_sections
            SET is_current = FALSE
            WHERE id = %s
        """, (request.section_id,))
        
        cursor.execute("""
            INSERT INTO proposal_sections (
                proposal_id, section_id, section_name, section_content,
                version, parent_version_id, is_current
            )
            SELECT proposal_id, section_id, section_name, %s,
                   version + 1, id, TRUE
            FROM proposal_sections
            WHERE id = %s
            RETURNING id
        """, (improved_text, request.section_id))
        
        new_section_id = cursor.fetchone()[0]
        
        conn.commit()
        db_pool.putconn(conn)
        
        return {
            "success": True,
            "original_section_id": request.section_id,
            "new_section_id": new_section_id,
            "improved_text": improved_text,
            "message": "Draft improved successfully!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error improving draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# EVALUATION & COMPLIANCE
# ================================================================

@router.post("/evaluate/criteria", summary="Evaluate criteria coverage")
async def evaluate_criteria(
    section_id: int,
    criteria: List[str],
    db_pool = Depends(get_db_pool)
):
    """Analyze how well a section addresses evaluation criteria"""
    
    try:
        # Get section content
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT section_content, proposal_id
            FROM proposal_sections
            WHERE id = %s AND is_current = TRUE
        """, (section_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")
        
        section_content, proposal_id = row
        
        # Get call_id from proposal
        cursor.execute("""
            SELECT call_identifier FROM proposals WHERE id = %s
        """, (proposal_id,))
        call_id = cursor.fetchone()[0]
        
        db_pool.putconn(conn)
        
        # Analyze
        criteria_matcher = EvaluationCriteriaMatcher()
        analysis = await criteria_matcher.analyze_section(
            section_text=section_content,
            evaluation_criteria=criteria,
            call_id=call_id
        )
        
        # Store results
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        for criterion, data in analysis['criteria_coverage'].items():
            cursor.execute("""
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
            """, (
                section_id,
                criterion,
                data['addressed'],
                data['strength'],
                data['evidence'],
                data['gaps']
            ))
        
        conn.commit()
        db_pool.putconn(conn)
        
        return {
            "section_id": section_id,
            "analysis": analysis,
            "message": "Criteria evaluation complete"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating criteria: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check/compliance", summary="Run compliance checks")
async def check_compliance(
    request: ComplianceCheckRequest,
    call_doc_service = Depends(get_call_doc_service),
    db_pool = Depends(get_db_pool)
):
    """Run comprehensive compliance checks on a proposal"""
    
    try:
        # Get proposal details
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT call_identifier, proposal_type
            FROM proposals
            WHERE id = %s
        """, (request.proposal_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        call_id, proposal_type = row
        db_pool.putconn(conn)
        
        # Build proposal data
        proposal_data = {
            "sections": request.sections,
            "consortium": [p.dict() for p in request.consortium],
            "budget": request.budget
        }
        
        # Run compliance checks
        compliance_checker = ComplianceChecker(call_doc_service, db_pool)
        compliance_result = await compliance_checker.run_compliance_check(
            call_id=call_id,
            proposal_data=proposal_data
        )
        
        # Store compliance results
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Clear old checks
        cursor.execute("""
            DELETE FROM compliance_checks WHERE proposal_id = %s
        """, (request.proposal_id,))
        
        # Insert new checks
        for check in compliance_result['detailed_checks']:
            for issue in check['issues']:
                cursor.execute("""
                    INSERT INTO compliance_checks (
                        proposal_id, check_type, check_category,
                        check_result, result_message
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    request.proposal_id,
                    check['check_name'],
                    'mandatory' if check['priority'] == 'critical' else 'recommended',
                    check['status'],
                    issue
                ))
        
        conn.commit()
        db_pool.putconn(conn)
        
        return {
            "proposal_id": request.proposal_id,
            "compliance": compliance_result,
            "message": "Compliance check complete"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "total_budget": request.total_budget
        }
        
        # Generate budget
        budget_result = await budget_assistant.generate_budget_table(
            call_id=request.call_id,
            proposal_type=request.proposal_type,
            project_params=project_params
        )
        
        return {
            "success": True,
            "call_id": request.call_id,
            "budget": budget_result,
            "message": "Budget generated successfully!"
        }
        
    except Exception as e:
        logger.error(f"Error generating budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# QUALITY IMPROVEMENT
# ================================================================

@router.post("/quality/analyze", summary="Analyze section quality")
async def analyze_quality(
    section_id: int,
    db_pool = Depends(get_db_pool)
):
    """Run comprehensive quality analysis on a section"""
    
    try:
        # Get section content
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT section_content, section_id
            FROM proposal_sections
            WHERE id = %s AND is_current = TRUE
        """, (section_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")
        
        section_content, section_id_str = row
        db_pool.putconn(conn)
        
        # Analyze quality
        ai_service = AIIntentService()
        quality_improver = QualityImprover(ai_service)
        
        analysis = await quality_improver.analyze_quality(
            section_text=section_content,
            section_type=section_id_str
        )
        
        # Store improvement suggestions
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        for suggestion in analysis.get('improvement_suggestions', []):
            cursor.execute("""
                INSERT INTO improvement_suggestions (
                    section_id, proposal_id, suggestion_type,
                    suggestion_text, priority
                )
                SELECT %s, proposal_id, %s, %s, %s
                FROM proposal_sections
                WHERE id = %s
            """, (
                section_id,
                suggestion['type'],
                suggestion['suggestion'],
                suggestion['priority'],
                section_id
            ))
        
        conn.commit()
        db_pool.putconn(conn)
        
        return {
            "section_id": section_id,
            "quality_analysis": analysis,
            "message": "Quality analysis complete"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# EXPORT & FINALIZATION
# ================================================================

@router.get("/{proposal_id}/export/summary", summary="Export proposal summary")
async def export_summary(
    proposal_id: int,
    db_pool = Depends(get_db_pool)
):
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
        cursor.execute("""
            SELECT section_id, section_name, section_content, word_count
            FROM proposal_sections
            WHERE proposal_id = %s AND is_current = TRUE
            ORDER BY section_order
        """, (proposal_id,))
        sections = cursor.fetchall()
        
        # Get consortium
        cursor.execute("""
            SELECT partner_name, partner_country, partner_type, partner_role
            FROM proposal_consortium
            WHERE proposal_id = %s
        """, (proposal_id,))
        consortium = cursor.fetchall()
        
        # Get budget
        cursor.execute("""
            SELECT partner_name, total_eligible_costs, requested_funding
            FROM proposal_budgets
            WHERE proposal_id = %s
        """, (proposal_id,))
        budget = cursor.fetchall()
        
        db_pool.putconn(conn)
        
        return {
            "proposal_id": proposal_id,
            "overview": {
                "title": overview[2],
                "call_id": overview[1],
                "status": overview[4],
                "completion": overview[5]
            },
            "sections": [
                {
                    "id": s[0],
                    "name": s[1],
                    "content": s[2],
                    "words": s[3]
                }
                for s in sections
            ],
            "consortium": [
                {
                    "name": c[0],
                    "country": c[1],
                    "type": c[2],
                    "role": c[3]
                }
                for c in consortium
            ],
            "budget_summary": {
                "total_eligible": sum(b[1] for b in budget) if budget else 0,
                "total_funding": sum(b[2] for b in budget) if budget else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        db_url = os.getenv('DATABASE_URL')
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
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting Part B: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        db_url = os.getenv('DATABASE_URL')
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
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{proposal_id}/complete-package")
async def export_complete_package(
    proposal_id: int,
    include_budget: bool = True,
    include_ethics: bool = True,
    include_security: bool = False
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
        db_url = os.getenv('DATABASE_URL')
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 2, db_url)
        
        exporter = SubmissionExporter(db_pool)
        zip_buffer = await exporter.export_proposal_package(
            proposal_id,
            include_budget=include_budget,
            include_ethics=include_ethics,
            include_security=include_security
        )
        
        db_pool.closeall()
        
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=proposal_{proposal_id}_SUBMISSION_PACKAGE.zip"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{proposal_id}/ethics")
async def export_ethics_assessment(proposal_id: int):
    """Export ethics self-assessment document"""
    
    try:
        db_url = os.getenv('DATABASE_URL')
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
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting ethics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

