"""
Submission Exporter Service

Creates complete submission packages with all required documents
in official EU formats.
"""

import logging
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Any

from .official_document_processor import (
    OfficialBudgetExporter,
    OfficialDocumentProcessor,
    OfficialWordExporter,
)

logger = logging.getLogger(__name__)


class SubmissionExporter:
    """
    Create complete submission packages ready for EU portal upload
    
    Generates:
    - Part B (Word document with all sections)
    - Budget tables (Excel)
    - Ethics self-assessment
    - Security questionnaire (if applicable)
    - Complete ZIP package ready to upload
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.doc_processor = OfficialDocumentProcessor()
        self.word_exporter = OfficialWordExporter()
        self.budget_exporter = OfficialBudgetExporter()
    
    async def export_proposal_package(
        self,
        proposal_id: int,
        include_budget: bool = True,
        include_ethics: bool = True,
        include_security: bool = False
    ) -> BytesIO:
        """
        Create complete submission package as ZIP file
        
        Args:
            proposal_id: Database ID of the proposal
            include_budget: Include budget Excel file
            include_ethics: Include ethics self-assessment
            include_security: Include security questionnaire
        
        Returns:
            BytesIO containing ZIP file with all documents
        """
        
        logger.info(f"📦 Creating submission package for proposal {proposal_id}")
        
        # Get proposal data from database
        proposal_data = await self._get_proposal_data(proposal_id)
        
        # Create ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # 1. Part B (main proposal document)
            logger.info("📄 Generating Part B document...")
            part_b_doc = await self.export_part_b(proposal_id)
            zip_file.writestr(
                f"{proposal_data['acronym']}_PartB.docx",
                part_b_doc.getvalue()
            )
            
            # 2. Budget (if requested)
            if include_budget:
                logger.info("💰 Generating budget Excel...")
                budget_doc = await self.export_budget(proposal_id)
                zip_file.writestr(
                    f"{proposal_data['acronym']}_Budget.xlsx",
                    budget_doc.getvalue()
                )
            
            # 3. Ethics (if requested and applicable)
            if include_ethics and proposal_data.get('has_ethics_issues'):
                logger.info("⚖️ Generating ethics assessment...")
                ethics_doc = await self.export_ethics_assessment(proposal_id)
                zip_file.writestr(
                    f"{proposal_data['acronym']}_Ethics.docx",
                    ethics_doc.getvalue()
                )
            
            # 4. Security (if requested)
            if include_security:
                logger.info("🔒 Generating security questionnaire...")
                security_doc = await self.export_security_questionnaire(proposal_id)
                zip_file.writestr(
                    f"{proposal_data['acronym']}_Security.docx",
                    security_doc.getvalue()
                )
            
            # 5. Add README
            readme_content = self._generate_readme(proposal_data)
            zip_file.writestr("README.txt", readme_content)
        
        zip_buffer.seek(0)
        logger.info("✅ Submission package created successfully")
        
        return zip_buffer
    
    async def export_part_b(self, proposal_id: int) -> BytesIO:
        """
        Export Part B document in official Word format
        
        This is the main proposal document (Excellence, Impact, Implementation)
        """
        
        # Get all proposal data
        proposal_data = await self._get_proposal_data(proposal_id)
        
        # Get all sections
        sections_data = await self._get_all_sections(proposal_id)
        
        # Combine data
        full_data = {
            **proposal_data,
            'sections': sections_data
        }
        
        # Create Word document using official template
        doc_buffer = self.word_exporter.create_part_b_document(
            full_data,
            action_type=proposal_data.get('action_type', 'RIA')
        )
        
        # Log to activity log
        await self._log_activity(proposal_id, "Exported Part B document")
        
        return doc_buffer
    
    async def export_budget(self, proposal_id: int) -> BytesIO:
        """Export budget in official Excel format"""
        
        budget_data = await self._get_budget_data(proposal_id)
        
        excel_buffer = self.budget_exporter.create_budget_excel(budget_data)
        
        await self._log_activity(proposal_id, "Exported budget Excel")
        
        return excel_buffer
    
    async def export_ethics_assessment(self, proposal_id: int) -> BytesIO:
        """Export ethics self-assessment"""
        
        from docx import Document
        
        ethics_data = await self._get_ethics_data(proposal_id)
        
        doc = Document()
        doc.add_heading("Ethics Self-Assessment", level=1)
        
        # Ethics questions
        doc.add_heading("1. Human Participants", level=2)
        doc.add_paragraph(
            f"Involves human participants: {'Yes' if ethics_data.get('human_participants') else 'No'}"
        )
        if ethics_data.get('human_participants'):
            doc.add_paragraph(ethics_data.get('human_participants_details', ''))
        
        doc.add_heading("2. Personal Data", level=2)
        doc.add_paragraph(
            f"Processes personal data: {'Yes' if ethics_data.get('personal_data') else 'No'}"
        )
        if ethics_data.get('personal_data'):
            doc.add_paragraph(ethics_data.get('gdpr_measures', ''))
        
        doc.add_heading("3. Vulnerable Populations", level=2)
        doc.add_paragraph(
            f"Involves vulnerable groups: {'Yes' if ethics_data.get('vulnerable_groups') else 'No'}"
        )
        
        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    async def export_security_questionnaire(self, proposal_id: int) -> BytesIO:
        """Export security questionnaire"""
        
        from docx import Document
        
        security_data = await self._get_security_data(proposal_id)
        
        doc = Document()
        doc.add_heading("Security Questionnaire", level=1)
        
        doc.add_paragraph(
            "This section describes any security-sensitive aspects of the project."
        )
        
        doc.add_heading("Security Issues", level=2)
        doc.add_paragraph(security_data.get('security_description', 'None identified'))
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    async def _get_proposal_data(self, proposal_id: int) -> dict[str, Any]:
        """Get proposal metadata from database"""
        
        conn = self.db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.proposal_title,
                p.proposal_acronym,
                p.call_identifier,
                p.proposal_type,
                p.created_at,
                p.user_id
            FROM proposals p
            WHERE p.id = %s
        """, (proposal_id,))
        
        row = cursor.fetchone()
        self.db_pool.putconn(conn)
        
        if not row:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        return {
            'title': row[0],
            'acronym': row[1],
            'call_id': row[2],
            'action_type': row[3],
            'created_at': row[4],
            'creator_name': row[5]
        }
    
    async def _get_all_sections(self, proposal_id: int) -> dict[str, str]:
        """Get all proposal sections"""
        
        conn = self.db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT section_id, section_content
            FROM proposal_sections
            WHERE proposal_id = %s AND is_current = TRUE
            ORDER BY section_order
        """, (proposal_id,))
        
        sections = {row[0]: row[1] for row in cursor.fetchall()}
        
        self.db_pool.putconn(conn)
        
        return sections
    
    async def _get_budget_data(self, proposal_id: int) -> dict[str, Any]:
        """Get budget data"""
        
        conn = self.db_pool.getconn()
        cursor = conn.cursor()
        
        # Get all partners and their budgets
        cursor.execute("""
            SELECT 
                pc.partner_name,
                pc.partner_country,
                pc.partner_type,
                pb.personnel_costs,
                pb.subcontracting_costs,
                pb.equipment_costs,
                pb.other_direct_costs,
                pb.indirect_costs,
                pb.total_eligible_costs,
                pb.funding_rate,
                pb.requested_funding
            FROM proposal_consortium pc
            LEFT JOIN proposal_budgets pb ON pc.partner_name = pb.partner_name AND pc.proposal_id = pb.proposal_id
            WHERE pc.proposal_id = %s
        """, (proposal_id,))
        
        partners = []
        total_eligible = 0
        total_requested = 0
        
        for row in cursor.fetchall():
            partner = {
                'partner_name': row[0],
                'country': row[1],
                'partner_type': row[2],
                'costs': {
                    'personnel': row[3] or 0,
                    'subcontracting': row[4] or 0,
                    'equipment': row[5] or 0,
                    'other_direct': row[6] or 0,
                    'indirect': row[7] or 0
                },
                'total_eligible_costs': row[8] or 0,
                'funding_rate': row[9] or 100,
                'requested_funding': row[10] or 0
            }
            partners.append(partner)
            total_eligible += partner['total_eligible_costs']
            total_requested += partner['requested_funding']
        
        self.db_pool.putconn(conn)
        
        return {
            'partner_budgets': partners,
            'summary': {
                'total_eligible_costs': total_eligible,
                'total_requested_funding': total_requested,
                'average_funding_rate': (total_requested / total_eligible * 100) if total_eligible > 0 else 0
            }
        }
    
    async def _get_ethics_data(self, proposal_id: int) -> dict[str, Any]:
        """Get ethics assessment data"""
        
        conn = self.db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                human_participants,
                human_participants_details,
                personal_data_processing,
                gdpr_compliance_measures,
                vulnerable_populations
            FROM ethics_assessments
            WHERE proposal_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (proposal_id,))
        
        row = cursor.fetchone()
        self.db_pool.putconn(conn)
        
        if not row:
            return {}
        
        return {
            'human_participants': row[0],
            'human_participants_details': row[1],
            'personal_data': row[2],
            'gdpr_measures': row[3],
            'vulnerable_groups': row[4]
        }
    
    async def _get_security_data(self, proposal_id: int) -> dict[str, Any]:
        """Get security questionnaire data"""
        
        # Placeholder - would query security_questionnaires table
        return {
            'security_description': 'No security-sensitive aspects identified.'
        }
    
    async def _log_activity(self, proposal_id: int, activity: str):
        """Log activity to database"""
        
        conn = self.db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO proposal_activity_log 
            (proposal_id, activity_type, activity_description)
            VALUES (%s, 'export', %s)
        """, (proposal_id, activity))
        
        conn.commit()
        self.db_pool.putconn(conn)
    
    def _generate_readme(self, proposal_data: dict) -> str:
        """Generate README for submission package"""
        
        return f"""
HORIZON EUROPE PROPOSAL SUBMISSION PACKAGE
==========================================

Proposal: {proposal_data['title']}
Acronym: {proposal_data['acronym']}
Call: {proposal_data['call_id']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CONTENTS:
---------
1. {proposal_data['acronym']}_PartB.docx
   Main proposal document (Excellence, Impact, Implementation)
   
2. {proposal_data['acronym']}_Budget.xlsx
   Detailed budget breakdown
   
3. {proposal_data['acronym']}_Ethics.docx (if applicable)
   Ethics self-assessment
   
4. {proposal_data['acronym']}_Security.docx (if applicable)
   Security questionnaire

SUBMISSION INSTRUCTIONS:
------------------------
1. Review all documents for completeness and accuracy
2. Upload to EU Funding & Tenders Portal
3. Complete Part A (administrative data) online
4. Attach these Part B documents
5. Submit before deadline!

GENERATED BY:
-------------
MAP-IT Proposal Writing Assistant
https://map-it.eu

For support: support@map-it.eu

Good luck with your submission! 🍀
"""

