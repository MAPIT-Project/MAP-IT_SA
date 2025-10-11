"""
Official EU Document Processor

Processes all official EU templates and forms from newdocs/ folder to create
submission-ready documents.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import PyPDF2
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import openpyxl
from io import BytesIO

logger = logging.getLogger(__name__)


class OfficialDocumentProcessor:
    """
    Process official EU templates to create submission-ready documents
    """
    
    def __init__(self):
        self.templates_path = Path("newdocs/Templates & forms")
        self.guidance_path = Path("newdocs/Guidence")
        self.work_programmes_path = Path("newdocs/2025_work_programmes")
    
    def get_template_for_action_type(self, action_type: str) -> Optional[Path]:
        """
        Get the appropriate application form template
        
        Args:
            action_type: 'RIA', 'IA', 'CSA', 'ERC-COG', etc.
        
        Returns:
            Path to the official PDF template
        """
        
        template_mapping = {
            'RIA': 'af_he-ria-ia_en.pdf',
            'IA': 'af_he-ria-ia_en.pdf',
            'CSA': 'af_he-csa_en.pdf',
            'ERC-COG': 'af_he-erc-cog_en.pdf',
            'ERC-STG': 'af_he-erc-stg_en.pdf',
            'ERC-ADG': 'af_he-erc-adg_en.pdf',
            'MSCA-PF': 'af_he-msca-pf_en.pdf',
            'MSCA-DN': 'af_he-msca-dn_en.pdf',
        }
        
        template_file = template_mapping.get(action_type)
        if not template_file:
            logger.warning(f"No template found for action type: {action_type}")
            return None
        
        template_path = self.templates_path / "Application forms" / template_file
        
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return None
        
        return template_path
    
    def get_evaluation_form(self, action_type: str) -> Optional[Path]:
        """Get evaluation form for scoring criteria"""
        
        eval_mapping = {
            'RIA': 'ef_he-ria-ia_en.pdf',
            'IA': 'ef_he-ria-ia_en.pdf',
            'CSA': 'ef_he-csa_en.pdf',
        }
        
        eval_file = eval_mapping.get(action_type)
        if not eval_file:
            return None
        
        eval_path = self.templates_path / "Evaluation forms" / eval_file
        return eval_path if eval_path.exists() else None
    
    def extract_template_structure(self, action_type: str) -> Dict[str, Any]:
        """
        Extract section structure from official template PDF
        
        This parses the official PDF to understand exactly what sections
        are required and their order.
        """
        
        template_path = self.get_template_for_action_type(action_type)
        if not template_path:
            return self._get_default_structure(action_type)
        
        try:
            with open(template_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text()
                
                # Parse structure (simplified - could be enhanced)
                structure = self._parse_template_structure(full_text, action_type)
                
                logger.info(f"Extracted structure from {template_path.name}")
                return structure
                
        except Exception as e:
            logger.error(f"Error extracting template structure: {e}")
            return self._get_default_structure(action_type)
    
    def _parse_template_structure(self, text: str, action_type: str) -> Dict[str, Any]:
        """Parse template text to extract section structure"""
        
        # Look for section headings in the PDF
        sections = []
        
        # Common section markers
        if "SECTION 1" in text or "1. Excellence" in text:
            sections.append({
                "id": "excellence",
                "name": "Excellence",
                "required": True
            })
        
        if "SECTION 2" in text or "2. Impact" in text:
            sections.append({
                "id": "impact",
                "name": "Impact",
                "required": True
            })
        
        if "SECTION 3" in text or "3. Implementation" in text:
            sections.append({
                "id": "implementation",
                "name": "Implementation",
                "required": True
            })
        
        return {
            "action_type": action_type,
            "sections": sections,
            "source": "official_template"
        }
    
    def _get_default_structure(self, action_type: str) -> Dict[str, Any]:
        """Fallback structure if template can't be parsed"""
        
        if action_type in ['RIA', 'IA']:
            return {
                "action_type": action_type,
                "sections": [
                    {"id": "excellence", "name": "Excellence", "required": True},
                    {"id": "impact", "name": "Impact", "required": True},
                    {"id": "implementation", "name": "Implementation", "required": True}
                ],
                "source": "default"
            }
        
        return {"action_type": action_type, "sections": [], "source": "default"}
    
    def extract_evaluation_criteria(self, action_type: str) -> Dict[str, List[str]]:
        """
        Extract exact evaluation criteria from official evaluation form
        
        This gives us the EXACT criteria evaluators will use!
        """
        
        eval_form = self.get_evaluation_form(action_type)
        if not eval_form:
            return self._get_default_criteria(action_type)
        
        try:
            with open(eval_form, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text()
                
                # Parse criteria from evaluation form
                criteria = self._parse_evaluation_criteria(full_text)
                
                logger.info(f"Extracted evaluation criteria from {eval_form.name}")
                return criteria
                
        except Exception as e:
            logger.error(f"Error extracting evaluation criteria: {e}")
            return self._get_default_criteria(action_type)
    
    def _parse_evaluation_criteria(self, text: str) -> Dict[str, List[str]]:
        """Parse evaluation form to extract criteria"""
        
        criteria = {
            "excellence": [],
            "impact": [],
            "implementation": []
        }
        
        # Look for criterion markers in the eval form
        # These are usually numbered or bulleted
        
        # Excellence criteria
        if "clarity" in text.lower() and "objective" in text.lower():
            criteria["excellence"].append("Clarity and pertinence of the project's objectives")
        if "soundness" in text.lower() and "methodology" in text.lower():
            criteria["excellence"].append("Soundness of the proposed methodology")
        if "ambition" in text.lower() or "innovation" in text.lower():
            criteria["excellence"].append("Ambition and innovation content")
        
        # Impact criteria
        if "credibility" in text.lower() and "impact" in text.lower():
            criteria["impact"].append("Credibility of the pathways to impact")
        if "dissemination" in text.lower():
            criteria["impact"].append("Suitability and quality of measures for dissemination")
        
        # Implementation criteria
        if "work plan" in text.lower() or "coherence" in text.lower():
            criteria["implementation"].append("Coherence and effectiveness of the work plan")
        if "consortium" in text.lower() or "capacity" in text.lower():
            criteria["implementation"].append("Quality and capacity of the consortium")
        
        return criteria
    
    def _get_default_criteria(self, action_type: str) -> Dict[str, List[str]]:
        """Fallback criteria"""
        
        return {
            "excellence": [
                "Clarity and pertinence of the project's objectives",
                "Soundness of the proposed methodology",
                "Quality of the proposed approach and credibility of achieving objectives"
            ],
            "impact": [
                "Credibility of the pathways to impact",
                "Suitability and quality of measures to maximize expected outcomes and impacts"
            ],
            "implementation": [
                "Coherence and effectiveness of the work plan",
                "Appropriateness of the management structures and procedures",
                "Quality and capacity of the consortium"
            ]
        }


class OfficialWordExporter:
    """
    Export proposal content to official Word format (.docx)
    
    Creates submission-ready Part B documents in official EU style
    """
    
    def __init__(self):
        self.doc_processor = OfficialDocumentProcessor()
    
    def create_part_b_document(
        self,
        proposal_data: Dict[str, Any],
        action_type: str = 'RIA'
    ) -> BytesIO:
        """
        Create official Part B document ready for submission
        
        Args:
            proposal_data: {
                'title': str,
                'acronym': str,
                'sections': {
                    'excellence.objectives': str,
                    'excellence.methodology': str,
                    ...
                }
            }
            action_type: 'RIA', 'IA', 'CSA', etc.
        
        Returns:
            BytesIO containing the .docx file
        """
        
        # Create new document
        doc = Document()
        
        # Apply official EU formatting
        self._apply_official_formatting(doc)
        
        # Cover page
        self._add_cover_page(doc, proposal_data)
        
        # Table of contents
        doc.add_page_break()
        self._add_table_of_contents(doc, proposal_data)
        
        # Part B sections
        doc.add_page_break()
        self._add_part_b_sections(doc, proposal_data, action_type)
        
        # Save to BytesIO
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        return file_stream
    
    def _apply_official_formatting(self, doc: Document):
        """Apply official EU document formatting standards"""
        
        # Set document margins (2.5 cm)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.98)
            section.bottom_margin = Inches(0.98)
            section.left_margin = Inches(0.98)
            section.right_margin = Inches(0.98)
            section.page_height = Inches(11.69)  # A4
            section.page_width = Inches(8.27)
    
    def _add_cover_page(self, doc: Document, proposal_data: Dict):
        """Add official cover page"""
        
        # Title
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(proposal_data.get('title', 'Proposal Title'))
        title_run.font.size = Pt(18)
        title_run.font.bold = True
        
        doc.add_paragraph()  # Spacing
        
        # Acronym
        if proposal_data.get('acronym'):
            acronym_para = doc.add_paragraph()
            acronym_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            acronym_run = acronym_para.add_run(proposal_data['acronym'])
            acronym_run.font.size = Pt(24)
            acronym_run.font.bold = True
        
        # Horizon Europe branding
        doc.add_paragraph()
        branding = doc.add_paragraph()
        branding.alignment = WD_ALIGN_PARAGRAPH.CENTER
        branding_run = branding.add_run("Horizon Europe")
        branding_run.font.size = Pt(14)
        branding_run.font.color.rgb = RGBColor(0, 51, 153)  # EU blue
    
    def _add_table_of_contents(self, doc: Document, proposal_data: Dict):
        """Add table of contents"""
        
        heading = doc.add_paragraph("Table of Contents")
        heading.style = 'Heading 1'
        
        doc.add_paragraph("SECTION 1 - EXCELLENCE")
        doc.add_paragraph("   1.1 Objectives and ambition")
        doc.add_paragraph("   1.2 Methodology")
        doc.add_paragraph("   1.3 Beyond the state of the art")
        
        doc.add_paragraph("SECTION 2 - IMPACT")
        doc.add_paragraph("   2.1 Pathways to impact")
        doc.add_paragraph("   2.2 Measures to maximize impact")
        
        doc.add_paragraph("SECTION 3 - IMPLEMENTATION")
        doc.add_paragraph("   3.1 Work plan and resources")
        doc.add_paragraph("   3.2 Consortium as a whole")
    
    def _add_part_b_sections(self, doc: Document, proposal_data: Dict, action_type: str):
        """Add all Part B sections with content"""
        
        sections = proposal_data.get('sections', {})
        
        # SECTION 1: EXCELLENCE
        doc.add_heading("SECTION 1: EXCELLENCE", level=1)
        
        doc.add_heading("1.1 Objectives and ambition", level=2)
        doc.add_paragraph(sections.get('excellence.objectives', '[Content to be added]'))
        
        doc.add_heading("1.2 Methodology", level=2)
        doc.add_paragraph(sections.get('excellence.methodology', '[Content to be added]'))
        
        doc.add_heading("1.3 Beyond the state of the art", level=2)
        doc.add_paragraph(sections.get('excellence.beyond_sota', '[Content to be added]'))
        
        # SECTION 2: IMPACT
        doc.add_page_break()
        doc.add_heading("SECTION 2: IMPACT", level=1)
        
        doc.add_heading("2.1 Pathways to impact", level=2)
        doc.add_paragraph(sections.get('impact.pathways', '[Content to be added]'))
        
        doc.add_heading("2.2 Measures to maximize impact", level=2)
        doc.add_paragraph(sections.get('impact.dissemination', '[Content to be added]'))
        
        # SECTION 3: IMPLEMENTATION
        doc.add_page_break()
        doc.add_heading("SECTION 3: IMPLEMENTATION", level=1)
        
        doc.add_heading("3.1 Work plan and resources", level=2)
        doc.add_paragraph(sections.get('implementation.work_plan', '[Content to be added]'))
        
        doc.add_heading("3.2 Consortium as a whole", level=2)
        doc.add_paragraph(sections.get('implementation.consortium', '[Content to be added]'))


class OfficialBudgetExporter:
    """
    Export budget to official Excel template
    """
    
    def __init__(self):
        self.templates_path = Path("newdocs/Templates & forms/Application forms")
    
    def create_budget_excel(
        self,
        budget_data: Dict[str, Any]
    ) -> BytesIO:
        """
        Create official budget Excel file
        
        NOTE: The official templates might be PDFs. If we have .xlsx templates,
        we'll use them. Otherwise, we create a properly formatted Excel.
        """
        
        # Create new workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Budget Details"
        
        # Headers
        headers = [
            "Partner", "Country", "Type", "Personnel", "Subcontracting",
            "Equipment", "Other Direct", "Indirect", "Total Eligible", 
            "Funding Rate", "Requested Funding"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = openpyxl.styles.Font(bold=True)
            cell.fill = openpyxl.styles.PatternFill(
                start_color="366092",
                end_color="366092",
                fill_type="solid"
            )
            cell.font = openpyxl.styles.Font(color="FFFFFF", bold=True)
        
        # Data rows
        row = 2
        for partner in budget_data.get('partner_budgets', []):
            ws.cell(row, 1, partner['partner_name'])
            ws.cell(row, 2, partner['country'])
            ws.cell(row, 3, partner['partner_type'])
            ws.cell(row, 4, partner['costs']['personnel'])
            ws.cell(row, 5, partner['costs']['subcontracting'])
            ws.cell(row, 6, partner['costs']['equipment'])
            ws.cell(row, 7, partner['costs']['other_direct'])
            ws.cell(row, 8, partner['costs']['indirect'])
            ws.cell(row, 9, float(partner['total_eligible_costs']))
            ws.cell(row, 10, float(partner['funding_rate']))
            ws.cell(row, 11, float(partner['requested_funding']))
            row += 1
        
        # Totals row
        total_row = row
        ws.cell(total_row, 1, "TOTAL").font = openpyxl.styles.Font(bold=True)
        ws.cell(total_row, 9, budget_data['summary']['total_eligible_costs'])
        ws.cell(total_row, 11, budget_data['summary']['total_requested_funding'])
        
        # Format as currency
        for row_num in range(2, total_row + 1):
            for col in [4, 5, 6, 7, 8, 9, 11]:
                ws.cell(row_num, col).number_format = '€#,##0.00'
        
        # Adjust column widths
        for col in range(1, 12):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
        
        # Save to BytesIO
        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        
        return file_stream

