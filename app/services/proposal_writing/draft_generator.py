"""
Proposal Draft Generator

AI-powered generation of proposal section drafts.
"""

import json
import logging
import os
from typing import Any, Optional

import google.generativeai as genai

from .call_understanding_service import CallUnderstanding, CallUnderstandingService

logger = logging.getLogger(__name__)


class ProposalDraftGenerator:
    """
    Generate AI-powered drafts for proposal sections
    """

    def __init__(self, call_doc_service, template_service):
        self.call_doc_service = call_doc_service
        self.template_service = template_service
        self.call_understanding_service = CallUnderstandingService()

        # Initialize Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
    async def generate_section_draft(
        self,
        call_id: str,
        section_id: str,
        user_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate a draft for a specific proposal section
        
        Args:
            call_id: Call identifier
            section_id: Section ID (e.g., "excellence.objectives")
            user_context: {
                "project_idea": "...",
                "research_area": "...",
                "main_objectives": [...],
                "partners": [...],
                "budget": 2000000,
                "duration_months": 36
            }
        
        Returns:
            {
                "draft_text": "...",
                "word_count": 500,
                "evaluation_criteria_addressed": [...],
                "suggestions": [...]
            }
        """
        
        logger.info(f"Generating draft for {section_id} in call {call_id}")
        
        # 1. Understand the call dynamically (no hardcoded domains)
        call_docs = self.call_doc_service.get_call_documents(call_id)
        call_text = " ".join([
            doc.get('title', '') + " " + doc.get('content', '')
            for doc in call_docs.get('documents', [])
        ])
        call_metadata = self._get_call_metadata(call_id)

        call_understanding = await self.call_understanding_service.understand_call(
            call_id=call_id,
            call_text=call_text,
            call_title=call_metadata.get('title')
        )

        # 2. Get section-specific guidance (not async)
        guidance = self.template_service.get_section_guidance(call_id, section_id)

        # 3. Get evaluation criteria for this section
        template = await self.template_service.generate_template(call_id)
        section_name = section_id.split('.')[0]  # 'excellence', 'impact', or 'implementation'
        criteria = template["evaluation_criteria"].get(section_name, [])

        # 4. Build AI prompt using call understanding
        prompt = self._build_draft_prompt(
            section_id=section_id,
            call_id=call_id,
            call_understanding=call_understanding,
            guidance=guidance,
            criteria=criteria,
            user_context=user_context
        )
        
        # 4. Generate draft with Gemini
        try:
            response = self.model.generate_content(prompt)
            draft_text = response.text
            
            # 5. Post-process to ensure EU alignment terms are included
            draft_text = self._ensure_eu_alignment_terms(draft_text, section_id, call_understanding)
            
            # 6. Analyze draft quality
            analysis = self._analyze_draft(draft_text, criteria)
            
            return {
                "draft_text": draft_text,
                "word_count": len(draft_text.split()),
                "estimated_pages": len(draft_text.split()) / 325,  # ~325 words per page
                "evaluation_criteria_addressed": analysis["criteria_addressed"],
                "suggestions": analysis["suggestions"],
                "quality_score": analysis["quality_score"]
            }
            
        except Exception as e:
            logger.error(f"Error generating draft: {e}")
            raise
    
    def _build_draft_prompt(
        self,
        section_id: str,
        call_id: str,
        call_understanding: CallUnderstanding,
        guidance: dict,
        criteria: list[str],
        user_context: dict
    ) -> str:
        """
        Build the AI prompt for draft generation using dynamic call understanding.
        """

        section_names = {
            "excellence.objectives": "Objectives and Ambition",
            "excellence.methodology": "Methodology",
            "excellence.beyond_sota": "Beyond the State of the Art",
            "impact.pathways": "Pathways to Impact",
            "impact.dissemination": "Dissemination and Exploitation",
            "implementation.work_plan": "Work Plan and Resources",
            "implementation.consortium": "Consortium and Management"
        }

        section_name = section_names.get(section_id, section_id)

        # Get call-specific metadata
        call_metadata = self._get_call_metadata(call_id)

        # Build terminology string from call understanding
        terminology_str = ", ".join(call_understanding.terminology[:15]) if call_understanding.terminology else "standard EU terminology"

        # Build EU priorities string
        priorities_str = ", ".join(call_understanding.eu_priorities[:5]) if call_understanding.eu_priorities else "Horizon Europe objectives"

        # Build sub-topics string
        sub_topics_str = ", ".join(call_understanding.sub_topics[:5]) if call_understanding.sub_topics else "as defined in the call"

        prompt = f"""You are an expert Horizon Europe proposal writer with 15+ years of experience writing successful RIA, IA, and CSA proposals.

TASK: Write the "{section_name}" section for a Horizon Europe proposal for call {call_id}.

CALL UNDERSTANDING:
- Call ID: {call_id}
- Cluster: {call_understanding.cluster.value}
- Main Topic: {call_understanding.topic}
- Sub-topics: {sub_topics_str}
- Target TRL: {call_understanding.target_trl or 'Not specified'}
- Action Type: {call_understanding.action_type or 'Not specified'}

CALL METADATA:
- Call Title: {call_metadata.get('title', 'Not specified')}
- Deadline: {call_metadata.get('deadline_date', 'Not specified')}
- Budget Range: €{call_metadata.get('min_contribution', 0):,} - €{call_metadata.get('max_contribution', 0):,}

OFFICIAL GUIDANCE FROM CALL DOCUMENTS:
{json.dumps(guidance.get('guidance_text', 'Follow standard Horizon Europe guidelines'), indent=2)}

EVALUATION CRITERIA TO ADDRESS:
{json.dumps(criteria, indent=2)}

KEY OBJECTIVES FROM CALL:
{json.dumps(call_understanding.key_objectives, indent=2) if call_understanding.key_objectives else "Address the call's stated objectives"}

EXPECTED OUTCOMES:
{json.dumps(call_understanding.expected_outcomes, indent=2) if call_understanding.expected_outcomes else "Deliver measurable results aligned with EU priorities"}

USER'S PROJECT INFORMATION:
- Project Idea: {user_context.get('project_idea', 'Not provided')}
- Research Area: {user_context.get('research_area', 'Not provided')}
- Main Objectives: {json.dumps(user_context.get('main_objectives', []), indent=2)}
- Partners: {json.dumps(user_context.get('partners', []), indent=2)}
- Budget: €{user_context.get('budget', 0):,}
- Duration: {user_context.get('duration_months', 36)} months

CRITICAL INSTRUCTIONS:
1. Write content SPECIFICALLY about {call_understanding.topic}
2. Reference the call ID ({call_id}) and its objectives throughout
3. DIRECTLY ADDRESS all evaluation criteria listed above
4. Use clear, concise language appropriate for EU evaluators
5. Include specific, measurable objectives and outcomes
6. Demonstrate innovation and beyond state-of-the-art thinking
7. Show EU added value and alignment with EU priorities
8. Use active voice and future-focused language
9. Be concrete and specific - avoid vague statements
10. Target 800-1200 words for this section

DOMAIN-SPECIFIC TERMINOLOGY TO USE:
{terminology_str}

EU PRIORITIES TO REFERENCE:
{priorities_str}

MANDATORY EU TERMS TO INCLUDE (at least once each):
- European added value OR EU added value
- European citizens OR European society
- multi-country OR cross-border collaboration
- stakeholder engagement
- At least one relevant EU policy/strategy from: {priorities_str}

WRITING STYLE:
- Professional and persuasive
- Evidence-based and factual
- Technical but accessible
- Clear structure with headings/subheadings
- Domain-appropriate terminology
- European policy alignment

OUTPUT FORMAT:
Generate ONLY the section content. Do not include meta-commentary.
Use clear subsection headings where appropriate.
Write as if this is going directly into the proposal document.

Begin writing the section now:"""

        return prompt
    
    def _get_call_metadata(self, call_id: str) -> dict[str, Any]:
        """Get call metadata for better context"""
        try:
            # Try to get metadata from call document service
            metadata = self.call_doc_service.get_call_metadata(call_id)
            if metadata:
                return metadata
        except Exception as e:
            logger.warning(f"Could not fetch call metadata: {e}")
        
        # Fallback metadata
        return {
            'title': f'HORIZON Europe Call {call_id}',
            'deadline_date': 'Not specified',
            'min_contribution': 2000000,
            'max_contribution': 5000000,
            'eligible_countries': 'Member States and Associated Countries'
        }

    # Note: _extract_call_topic removed - now handled by CallUnderstandingService

    def _analyze_draft(self, draft_text: str, criteria: list[str]) -> dict[str, Any]:
        """
        Analyze draft quality and criteria coverage
        """
        
        # Simple analysis - can be enhanced with more sophisticated NLP
        word_count = len(draft_text.split())
        
        # Check if criteria are mentioned (basic keyword matching)
        criteria_addressed = []
        for criterion in criteria:
            # Extract key terms from criterion
            key_terms = [word.lower() for word in criterion.split() 
                        if len(word) > 4 and word.lower() not in ['the', 'and', 'for']]
            
            # Check if any key terms appear in draft
            if any(term in draft_text.lower() for term in key_terms):
                criteria_addressed.append(criterion)
        
        # Calculate quality score
        quality_score = len(criteria_addressed) / len(criteria) if criteria else 0.5
        
        # Generate suggestions
        suggestions = []
        
        if word_count < 500:
            suggestions.append({
                "type": "length",
                "priority": "high",
                "text": f"Section is quite short ({word_count} words). Consider expanding with more details and examples."
            })
        
        if quality_score < 0.7:
            missing_criteria = set(criteria) - set(criteria_addressed)
            suggestions.append({
                "type": "criteria_coverage",
                "priority": "critical",
                "text": f"Some evaluation criteria may not be fully addressed: {', '.join(missing_criteria)}"
            })
        
        if "TRL" not in draft_text and "Technology Readiness Level" not in draft_text:
            suggestions.append({
                "type": "terminology",
                "priority": "medium",
                "text": "Consider adding TRL (Technology Readiness Level) information if relevant"
            })
        
        return {
            "criteria_addressed": criteria_addressed,
            "quality_score": quality_score,
            "suggestions": suggestions
        }
    
    def _ensure_eu_alignment_terms(
        self,
        text: str,
        section_id: str,
        call_understanding: CallUnderstanding | None = None
    ) -> str:
        """
        Ensure critical EU alignment terms are included in the draft.
        Now cluster-aware - uses CallUnderstanding to select appropriate terms.
        """

        # Universal terms required for all sections
        universal_terms = {
            'excellence.objectives': [
                "EU added value",
                "European citizens",
                "Horizon Europe",
            ],
            'excellence.methodology': [
                "European Research Area",
                "GDPR",
                "data management"
            ],
            'impact.pathways': [
                "European society",
                "European economy",
                "dissemination",
                "exploitation"
            ],
            'implementation.work_plan': [
                "work package",
                "deliverable",
                "milestone",
                "consortium"
            ]
        }

        # Get base required terms for this section
        required_terms = universal_terms.get(section_id, []).copy()

        # Add cluster-specific terms if we have call understanding
        if call_understanding:
            # Add relevant EU priorities from the cluster
            required_terms.extend(call_understanding.eu_priorities[:2])

        # Check which terms are missing
        text_lower = text.lower()
        missing_terms = [term for term in required_terms if term.lower() not in text_lower]

        # If terms are missing, add them naturally
        if missing_terms:
            logger.info(f"Adding {len(missing_terms)} missing EU terms to {section_id}")

            # Create contextual insertions for missing terms
            insertions = self._create_contextual_insertions(
                missing_terms, section_id, text, call_understanding
            )

            # Insert terms at appropriate positions
            for position, insertion in insertions:
                text = self._insert_at_position(text, position, insertion)

        return text

    def _create_contextual_insertions(
        self,
        missing_terms: list[str],
        section_id: str,
        text: str,
        call_understanding: CallUnderstanding | None = None
    ) -> list[tuple]:
        """
        Create contextual insertions for missing EU terms.
        Now cluster-aware - generates appropriate text based on call topic.
        """
        insertions = []

        # Get topic context for insertions
        topic = call_understanding.topic if call_understanding else "research and innovation"
        cluster = call_understanding.cluster if call_understanding else None

        # Build cluster-appropriate context phrases
        topic_phrase = self._get_topic_phrase(cluster, topic)
        impact_phrase = self._get_impact_phrase(cluster, topic)

        if section_id == 'excellence.objectives':
            if "EU added value" in missing_terms:
                insertions.append((1, f"The EU added value of this project lies in its pan-European approach to {topic_phrase}, creating solutions that benefit all member states."))
            if "European citizens" in missing_terms:
                insertions.append((2, f"Ultimately, this project will {impact_phrase}, strengthening trust and delivering tangible benefits to European citizens."))
            # Add cluster-specific EU priority if missing
            if call_understanding:
                for priority in call_understanding.eu_priorities[:1]:
                    if priority in missing_terms:
                        insertions.append((3, f"This project directly contributes to {priority} objectives through its innovative approach to {topic_phrase}."))

        elif section_id == 'excellence.methodology':
            if "European Research Area" in missing_terms:
                insertions.append((1, "Our methodology aligns with the European Research Area objectives of open science and collaborative research excellence."))
            if "GDPR" in missing_terms:
                insertions.append((2, "All data processing will comply with GDPR requirements, ensuring the highest standards of data protection and privacy."))
            if "data management" in missing_terms:
                insertions.append((3, "A comprehensive data management plan will ensure FAIR principles are followed throughout the project lifecycle."))

        elif section_id == 'impact.pathways':
            if "European economy" in missing_terms:
                insertions.append((1, f"The project will contribute significantly to the European economy by advancing {topic_phrase} and enabling sustainable growth."))
            if "European society" in missing_terms:
                insertions.append((2, f"By {impact_phrase}, this project enhances European society's capacity to address current and future challenges."))
            if "dissemination" in missing_terms:
                insertions.append((3, "A robust dissemination strategy will ensure project results reach relevant stakeholders across Europe."))
            if "exploitation" in missing_terms:
                insertions.append((4, "The exploitation plan identifies clear pathways for commercial uptake and policy implementation."))

        elif section_id == 'implementation.work_plan':
            if "work package" in missing_terms:
                insertions.append((1, "The project will be structured into distinct work packages, each with clear deliverables and milestones."))
            if "deliverable" in missing_terms:
                insertions.append((2, "Each work package produces specific deliverables that contribute to the overall project objectives."))
            if "milestone" in missing_terms:
                insertions.append((3, "Key milestones mark critical decision points and enable effective project monitoring."))
            if "consortium" in missing_terms:
                insertions.append((4, "The consortium brings together complementary expertise from across Europe to achieve the project goals."))

        return insertions

    def _get_topic_phrase(self, cluster: Optional['HorizonCluster'], topic: str) -> str:
        """Generate a cluster-appropriate topic phrase."""
        from .call_understanding_service import HorizonCluster

        if not cluster:
            return topic

        cluster_phrases = {
            HorizonCluster.CL1_HEALTH: "health research and medical innovation",
            HorizonCluster.CL2_CULTURE: "cultural heritage and democratic innovation",
            HorizonCluster.CL3_SECURITY: "civil security and societal resilience",
            HorizonCluster.CL4_DIGITAL: "digital transformation and technological excellence",
            HorizonCluster.CL5_CLIMATE: "climate action and sustainable energy solutions",
            HorizonCluster.CL6_FOOD: "sustainable food systems and bioeconomy",
            HorizonCluster.ERC: "frontier research and scientific excellence",
            HorizonCluster.EIC: "breakthrough innovation and market creation",
            HorizonCluster.MSCA: "researcher mobility and skills development",
        }
        return cluster_phrases.get(cluster, topic)

    def _get_impact_phrase(self, cluster: Optional['HorizonCluster'], topic: str) -> str:
        """Generate a cluster-appropriate impact phrase."""
        from .call_understanding_service import HorizonCluster

        if not cluster:
            return f"advance {topic}"

        impact_phrases = {
            HorizonCluster.CL1_HEALTH: "improve health outcomes and healthcare delivery across Europe",
            HorizonCluster.CL2_CULTURE: "strengthen democratic participation and cultural diversity",
            HorizonCluster.CL3_SECURITY: "enhance security and protect critical infrastructure",
            HorizonCluster.CL4_DIGITAL: "accelerate digital transformation and technological sovereignty",
            HorizonCluster.CL5_CLIMATE: "advance climate neutrality and sustainable development",
            HorizonCluster.CL6_FOOD: "ensure food security and sustainable resource management",
            HorizonCluster.ERC: "push the boundaries of scientific knowledge",
            HorizonCluster.EIC: "bring breakthrough innovations to market",
            HorizonCluster.MSCA: "develop the next generation of research talent",
        }
        return impact_phrases.get(cluster, f"advance {topic}")

    def _insert_at_position(self, text: str, position: int, insertion: str) -> str:
        """
        Insert text at a specific paragraph position
        """
        paragraphs = text.split('\n\n')
        
        if position < len(paragraphs):
            paragraphs.insert(position, insertion)
        else:
            paragraphs.append(insertion)
        
        return '\n\n'.join(paragraphs)
    
    async def improve_draft(
        self,
        original_draft: str,
        improvement_instructions: str,
        call_id: str,
        section_id: str
    ) -> str:
        """
        Improve an existing draft based on user instructions
        """
        
        prompt = f"""You are an expert proposal editor. Improve this proposal section based on the user's instructions.

ORIGINAL DRAFT:
{original_draft}

IMPROVEMENT INSTRUCTIONS:
{improvement_instructions}

REQUIREMENTS:
- Maintain the core message and content
- Address the improvement instructions
- Keep professional EU proposal style
- Ensure all original key points are retained
- Improve clarity and persuasiveness

Generate the improved version:"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error improving draft: {e}")
            raise

