"""
Proposal Template Service

Generates structured proposal templates based on call requirements.
"""

import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ProposalTemplateService:
    """
    Generate proposal templates from call documents
    """
    
    def __init__(self, db_pool, call_doc_service):
        self.db_pool = db_pool
        self.call_doc_service = call_doc_service
        
    def generate_template(self, call_id: str) -> Dict[str, Any]:
        """
        Generate a complete proposal template for a specific call
        
        Args:
            call_id: The call identifier (e.g., HORIZON-CL3-2025-02-CS-ECCC-01)
            
        Returns:
            Template structure with sections, criteria, and guidance
        """
        
        logger.info(f"Generating proposal template for {call_id}")
        
        # 1. Get call documents (not async)
        call_docs = self.call_doc_service.get_call_documents(call_id)
        
        # 2. Extract proposal type (RIA, IA, CSA, etc.)
        proposal_type = self._extract_proposal_type(call_id, call_docs)
        
        # 3. Get standard template structure
        base_template = self._get_base_template(proposal_type)
        
        # 4. Extract call-specific requirements
        requirements = self._extract_requirements(call_id)
        
        # 5. Map evaluation criteria to sections
        criteria_mapping = self._map_evaluation_criteria(call_id, requirements)
        
        # 6. Build complete template
        template = {
            "call_id": call_id,
            "proposal_type": proposal_type,
            "generated_at": datetime.utcnow().isoformat(),
            "structure": base_template,
            "requirements": requirements,
            "evaluation_criteria": criteria_mapping,
            "metadata": {
                "page_limit": requirements.get("page_limit", 45),
                "duration_months": requirements.get("duration_range", [24, 48]),
                "budget_range": requirements.get("budget_range", [2000000, 5000000])
            }
        }
        
        logger.info(f"✅ Template generated with {len(base_template['sections'])} sections")
        
        return template
    
    def _get_base_template(self, proposal_type: str) -> Dict[str, Any]:
        """
        Get base template structure based on proposal type
        """
        
        # Standard Horizon Europe Part B structure
        if proposal_type in ["RIA", "IA"]:
            return {
                "sections": [
                    {
                        "id": "excellence",
                        "name": "Excellence",
                        "order": 1,
                        "page_limit": 30,
                        "subsections": [
                            {
                                "id": "excellence.objectives",
                                "name": "Objectives and ambition",
                                "order": 1,
                                "guidance": "State the specific, measurable objectives and ambition of the project"
                            },
                            {
                                "id": "excellence.methodology",
                                "name": "Methodology",
                                "order": 2,
                                "guidance": "Describe the overall methodology and approach"
                            },
                            {
                                "id": "excellence.beyond_sota",
                                "name": "Beyond the state of the art",
                                "order": 3,
                                "guidance": "Demonstrate innovation beyond current state of the art"
                            }
                        ]
                    },
                    {
                        "id": "impact",
                        "name": "Impact",
                        "order": 2,
                        "page_limit": 10,
                        "subsections": [
                            {
                                "id": "impact.pathways",
                                "name": "Pathways to impact",
                                "order": 1,
                                "guidance": "Describe how results will achieve expected impacts"
                            },
                            {
                                "id": "impact.dissemination",
                                "name": "Dissemination and exploitation",
                                "order": 2,
                                "guidance": "Outline dissemination, exploitation, and communication strategy"
                            }
                        ]
                    },
                    {
                        "id": "implementation",
                        "name": "Implementation",
                        "order": 3,
                        "page_limit": 15,
                        "subsections": [
                            {
                                "id": "implementation.work_plan",
                                "name": "Work plan and resources",
                                "order": 1,
                                "guidance": "Describe work packages, deliverables, and resources"
                            },
                            {
                                "id": "implementation.consortium",
                                "name": "Consortium and management",
                                "order": 2,
                                "guidance": "Describe consortium composition and management structure"
                            }
                        ]
                    }
                ]
            }
        
        elif proposal_type == "CSA":
            # Coordination and Support Actions have different structure
            return {
                "sections": [
                    {
                        "id": "excellence",
                        "name": "Excellence",
                        "order": 1,
                        "page_limit": 20,
                        "subsections": [
                            {
                                "id": "excellence.objectives",
                                "name": "Objectives and activities",
                                "order": 1,
                                "guidance": "Describe objectives and main activities"
                            },
                            {
                                "id": "excellence.added_value",
                                "name": "European added value",
                                "order": 2,
                                "guidance": "Explain EU added value of coordination/support"
                            }
                        ]
                    },
                    {
                        "id": "impact",
                        "name": "Impact",
                        "order": 2,
                        "page_limit": 8,
                        "subsections": [
                            {
                                "id": "impact.outcomes",
                                "name": "Expected outcomes",
                                "order": 1,
                                "guidance": "Describe expected outcomes and target groups"
                            }
                        ]
                    },
                    {
                        "id": "implementation",
                        "name": "Implementation",
                        "order": 3,
                        "page_limit": 12,
                        "subsections": [
                            {
                                "id": "implementation.work_plan",
                                "name": "Work plan",
                                "order": 1,
                                "guidance": "Outline work plan and activities"
                            }
                        ]
                    }
                ]
            }
        
        # Default to RIA structure
        return self._get_base_template("RIA")
    
    def _extract_proposal_type(self, call_id: str, call_docs: List[Dict]) -> str:
        """
        Extract proposal type from call documents
        
        Returns: 'RIA', 'IA', 'CSA', 'ERC-COG', etc.
        """
        
        # Search for type indicators in call text (not async)
        type_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            "type of action research innovation coordination",
            limit=5
        )
        
        # Simple heuristic - look for keywords
        combined_text = " ".join([chunk["chunk_text"] for chunk in type_chunks])
        
        if "Research and Innovation Action" in combined_text or "RIA" in combined_text:
            return "RIA"
        elif "Innovation Action" in combined_text and "Research" not in combined_text:
            return "IA"
        elif "Coordination and Support Action" in combined_text or "CSA" in combined_text:
            return "CSA"
        
        # Default to RIA
        logger.warning(f"Could not determine proposal type for {call_id}, defaulting to RIA")
        return "RIA"
    
    def _extract_requirements(self, call_id: str) -> Dict[str, Any]:
        """
        Extract specific requirements from call documents
        """
        
        requirements = {}
        
        # Extract budget information (not async)
        budget_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            "budget indicative funding maximum grant",
            limit=3
        )
        requirements["budget_info"] = [chunk["chunk_text"] for chunk in budget_chunks]
        
        # Extract consortium requirements
        consortium_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            "consortium eligibility minimum entities countries",
            limit=3
        )
        requirements["consortium_info"] = [chunk["chunk_text"] for chunk in consortium_chunks]
        
        # Extract duration
        duration_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            "duration months project length",
            limit=2
        )
        requirements["duration_info"] = [chunk["chunk_text"] for chunk in duration_chunks]
        
        # Extract page limits (usually 45 for Part B)
        requirements["page_limit"] = 45  # Standard for most calls
        
        return requirements
    
    def _map_evaluation_criteria(
        self,
        call_id: str,
        requirements: Dict
    ) -> Dict[str, List[str]]:
        """
        Map evaluation criteria to proposal sections
        """
        
        # Get evaluation criteria from call documents (not async)
        criteria_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            "evaluation criteria award score",
            limit=5
        )
        
        # Standard Horizon Europe criteria mapping
        criteria_mapping = {
            "excellence": [
                "Clarity and pertinence of the objectives",
                "Soundness of the proposed methodology",
                "Quality and appropriateness of the approach",
                "Credibility of the pathways to achieve the project's objectives"
            ],
            "impact": [
                "Credibility of the pathways to deliver impacts",
                "Suitability and quality of the measures to maximize expected outcomes",
                "The magnitude and importance of the project's contribution to the expected impacts"
            ],
            "implementation": [
                "Coherence and effectiveness of the work plan",
                "Appropriateness of the allocation of tasks and resources",
                "Quality and relevance of the consortium",
                "Appropriateness of the management structure"
            ]
        }
        
        return criteria_mapping
    
    def get_section_guidance(
        self,
        call_id: str,
        section_id: str
    ) -> Dict[str, Any]:
        """
        Get specific guidance for a section
        """
        
        # Map section ID to search query
        section_queries = {
            "excellence.objectives": "objectives ambition project goals",
            "excellence.methodology": "methodology approach methods",
            "excellence.beyond_sota": "state of the art innovation novelty",
            "impact.pathways": "impact expected outcomes results",
            "impact.dissemination": "dissemination exploitation communication",
            "implementation.work_plan": "work plan packages deliverables",
            "implementation.consortium": "consortium partners management"
        }
        
        query = section_queries.get(section_id, section_id)
        
        # Retrieve relevant guidance from call documents (not async)
        guidance_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            query,
            limit=5
        )
        
        return {
            "section_id": section_id,
            "guidance_text": [chunk["chunk_text"] for chunk in guidance_chunks],
            "source_documents": [chunk["document_title"] for chunk in guidance_chunks]
        }

