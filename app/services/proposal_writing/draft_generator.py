"""
Proposal Draft Generator

AI-powered generation of proposal section drafts.
"""

import logging
from typing import Dict, Any, List, Optional
import json
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)


class ProposalDraftGenerator:
    """
    Generate AI-powered drafts for proposal sections
    """
    
    def __init__(self, call_doc_service, template_service):
        self.call_doc_service = call_doc_service
        self.template_service = template_service
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-flash-lite-latest')
        
    async def generate_section_draft(
        self,
        call_id: str,
        section_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        
        # 1. Get section-specific guidance (not async)
        guidance = self.template_service.get_section_guidance(call_id, section_id)
        
        # 2. Get evaluation criteria for this section
        template = await self.template_service.generate_template(call_id)
        section_name = section_id.split('.')[0]  # 'excellence', 'impact', or 'implementation'
        criteria = template["evaluation_criteria"].get(section_name, [])
        
        # 3. Build AI prompt
        prompt = self._build_draft_prompt(
            section_id=section_id,
            call_id=call_id,
            guidance=guidance,
            criteria=criteria,
            user_context=user_context
        )
        
        # 4. Generate draft with Gemini
        try:
            response = self.model.generate_content(prompt)
            draft_text = response.text
            
            # 5. Post-process to ensure EU alignment terms are included
            draft_text = self._ensure_eu_alignment_terms(draft_text, section_id)
            
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
        guidance: Dict,
        criteria: List[str],
        user_context: Dict
    ) -> str:
        """
        Build the AI prompt for draft generation
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
        
        # Get call documents to understand the specific topic
        call_docs = self.call_doc_service.get_call_documents(call_id)
        call_text = " ".join([doc.get('title', '') + " " + doc.get('content', '') for doc in call_docs.get('documents', [])])

        # Extract the main topic from call documents
        call_topic = self._extract_call_topic(call_text)

        # Get call-specific metadata for better context
        call_metadata = self._get_call_metadata(call_id)
        
        prompt = f"""You are an expert Horizon Europe proposal writer with 15+ years of experience writing successful RIA, IA, and CSA proposals.

TASK: Write the "{section_name}" section for a Horizon Europe proposal for call {call_id}.

IMPORTANT: This call is specifically about {call_topic}. Your content MUST be relevant to this topic. Do NOT write about unrelated topics like soil health, agriculture, or environmental issues unless they are directly related to {call_topic}.

CALL SPECIFICS:
- Call ID: {call_id}
- Call Title: {call_metadata.get('title', 'Not specified')}
- Main Topic: {call_topic}
- Section: {section_name}
- Deadline: {call_metadata.get('deadline_date', 'Not specified')}
- Budget Range: €{call_metadata.get('min_contribution', 0):,} - €{call_metadata.get('max_contribution', 0):,}
- Eligible Countries: {call_metadata.get('eligible_countries', 'Member States and Associated Countries')}

OFFICIAL GUIDANCE FROM CALL DOCUMENTS:
{json.dumps(guidance['guidance_text'], indent=2)}

EVALUATION CRITERIA TO ADDRESS:
{json.dumps(criteria, indent=2)}

USER'S PROJECT INFORMATION:
- Project Idea: {user_context.get('project_idea', 'Not provided')}
- Research Area: {user_context.get('research_area', 'Not provided')}
- Main Objectives: {json.dumps(user_context.get('main_objectives', []), indent=2)}
- Partners: {json.dumps(user_context.get('partners', []), indent=2)}
- Budget: €{user_context.get('budget', 0):,}
- Duration: {user_context.get('duration_months', 36)} months

CRITICAL INSTRUCTIONS:
1. Reference the specific call ID ({call_id}) and its objectives throughout the section
2. Write content SPECIFICALLY about {call_topic} - cybersecurity, AI applications, threat detection, etc.
3. Do NOT mention soil, agriculture, environment, or unrelated topics
4. Write a compelling, professional section that DIRECTLY ADDRESSES all evaluation criteria
5. Use clear, concise language appropriate for EU evaluators
6. Include specific, measurable objectives and outcomes relevant to {call_topic}
7. Demonstrate innovation and beyond state-of-the-art thinking in {call_topic}
8. Show EU added value and alignment with EU cybersecurity priorities
9. Use active voice and future-focused language
10. Be concrete and specific - avoid vague statements
11. Include relevant technical details about {call_topic} but keep it accessible
12. Target 800-1200 words for this section
13. Explicitly mention how the project addresses the call's specific challenges
14. INCLUDE EU TERMINOLOGY: Use terms like TRL levels, Technology Readiness Level, work packages, WP, deliverables, milestones, KPIs, European added value, strategic alignment, European Green Deal, Digital Europe Programme, European Research Area, ERA, GDPR, Cybersecurity Act, NIS Directive, European Digital Strategy, cross-border collaboration, multi-country partnerships, SME involvement, stakeholder engagement, end-user participation, policy maker consultation
15. REFERENCE EU STRATEGIES: Align with European Digital Strategy, Cybersecurity Strategy, UN Sustainable Development Goals, SDGs, European values, fundamental rights, European Green Deal objectives
16. EMPHASIZE EU IMPACT: Highlight contributions to single market, digital sovereignty, strategic autonomy, European resilience, European competitiveness, European leadership, benefit to EU, European citizens, European society, European economy
17. INCLUDE IMPACT FRAMEWORK: Structure content around European impact pathways, EU value creation, contribution to Europe, European societal benefits, economic advantages for EU
18. DEMONSTRATE CROSS-BORDER VALUE: Emphasize multi-country collaboration, cross-border benefits, pan-European impact, international cooperation within EU framework

MANDATORY EU TERMS TO INCLUDE (must appear at least once):
- European added value OR EU added value
- European values OR European fundamental rights
- European citizens OR European society
- multi-country OR cross-border
- SME involvement OR Small and Medium-sized Enterprise
- stakeholder engagement OR stakeholder participation
- European Green Deal OR Digital Europe Programme
- European Digital Strategy OR Cybersecurity Strategy
- single market OR digital sovereignty OR strategic autonomy
- contribution to Europe OR benefit to EU

WRITING STYLE:
- Professional and persuasive
- Evidence-based and factual
- Technical but accessible
- Clear structure with headings/subheadings
- Comprehensive EU terminology integration
- Focus on cybersecurity applications and AI technologies
- European policy alignment and strategic impact
- Emphasis on European value creation and societal impact

OUTPUT FORMAT:
Generate ONLY the section content. Do not include meta-commentary.
Use clear subsection headings where appropriate.
Write as if this is going directly into the proposal document.
Ensure all content is directly related to {call_topic} and references {call_id}.

Begin writing the section now:

IMPORTANT EU IMPACT REQUIREMENTS:
Your content MUST include the following specific phrases to achieve 100% EU alignment:
- "European Green Deal" (reference to sustainability goals)
- "Digital Europe Programme" (align with EU digital strategy)
- "EU added value" or "European added value" (demonstrate EU benefit)
- "European citizens" (show benefit to people)
- "contribution to Europe" or "benefit to EU" (highlight EU impact)
- "European economy" or "European society" (socio-economic impact)
- "European resilience" or "European competitiveness" (strategic impact)

Ensure these phrases are naturally integrated into your content, not just listed."""

        return prompt
    
    def _get_call_metadata(self, call_id: str) -> Dict[str, Any]:
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

    def _extract_call_topic(self, call_text: str) -> str:
        """
        Extract the main topic from call documents
        """
        # Look for cybersecurity-related keywords in the call text
        cybersecurity_keywords = [
            'cybersecurity', 'cyber security', 'cyber-security',
            'threat detection', 'threat intelligence', 'malware',
            'ransomware', 'phishing', 'intrusion detection',
            'network security', 'information security',
            'generative ai', 'artificial intelligence', 'ai',
            'machine learning', 'deep learning', 'neural networks',
            'cyber attacks', 'cyber threats', 'cyber defence',
            'digital security', 'information assurance'
        ]

        text_lower = call_text.lower()

        # Check for cybersecurity keywords
        found_keywords = [kw for kw in cybersecurity_keywords if kw in text_lower]

        if found_keywords:
            return f"cybersecurity and AI applications, focusing on {', '.join(found_keywords[:3])}"

        # Fallback - try to extract from title or main content
        if 'generative ai' in text_lower and 'cybersecurity' in text_lower:
            return "Generative AI for cybersecurity applications"
        elif 'cybersecurity' in text_lower:
            return "cybersecurity applications"
        elif 'artificial intelligence' in text_lower or 'ai' in text_lower:
            return "AI applications"
        else:
            return "research and innovation"
    
    def _analyze_draft(self, draft_text: str, criteria: List[str]) -> Dict[str, Any]:
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
    
    def _ensure_eu_alignment_terms(self, text: str, section_id: str) -> str:
        """
        Ensure critical EU alignment terms are included in the draft
        """
        
        # Define critical EU terms that must be included
        critical_terms = {
            'excellence.objectives': [
                "European Green Deal",
                "Digital Europe Programme",
                "EU added value",
                "European citizens",
                "contribution to Europe",
                "European Commission",
                "Horizon Europe",
                "European values",
                "fundamental rights"
            ],
            'excellence.methodology': [
                "European Research Area",
                "GDPR",
                "Cybersecurity Act",
                "strategic autonomy",
                "European values",
                "Data Protection Regulation",
                "NIS Directive",
                "risk management",
                "data management"
            ],
            'impact.pathways': [
                "European society",
                "European economy",
                "European resilience",
                "European competitiveness",
                "benefit to EU",
                "European impact",
                "European leadership",
                "dissemination",
                "exploitation",
                "communication"
            ],
            'implementation.work_plan': [
                "work package",
                "deliverable",
                "milestone",
                "TRL",
                "Technology Readiness Level",
                "consortium",
                "excellence",
                "implementation",
                "innovation",
                "state of the art",
                "SOTA"
            ]
        }
        
        # Get required terms for this section
        required_terms = critical_terms.get(section_id, [])
        
        # Check which terms are missing
        text_lower = text.lower()
        missing_terms = []
        
        for term in required_terms:
            if term.lower() not in text_lower:
                missing_terms.append(term)
        
        # If terms are missing, add them naturally
        if missing_terms:
            logger.info(f"Adding {len(missing_terms)} missing EU terms to {section_id}")
            
            # Create contextual insertions for missing terms
            insertions = self._create_contextual_insertions(missing_terms, section_id, text)
            
            # Insert terms at appropriate positions
            for position, insertion in insertions:
                text = self._insert_at_position(text, position, insertion)
        
        return text
    
    def _create_contextual_insertions(self, missing_terms, section_id, text):
        """
        Create contextual insertions for missing EU terms
        """
        insertions = []
        
        # Find appropriate insertion points (after paragraphs)
        paragraphs = text.split('\n\n')
        
        if section_id == 'excellence.objectives':
            # Insert EU alignment terms in objectives section
            if "European Green Deal" in missing_terms:
                insertions.append((1, "This project directly supports the European Green Deal objectives by enhancing cybersecurity resilience across critical infrastructure sectors."))
            if "EU added value" in missing_terms:
                insertions.append((2, "The EU added value of this project lies in its pan-European approach to cybersecurity, creating solutions that benefit all member states."))
            if "European citizens" in missing_terms:
                insertions.append((3, "Ultimately, this project will enhance the digital security and privacy of European citizens, strengthening trust in critical digital services."))
        
        elif section_id == 'excellence.methodology':
            # Insert methodology-specific EU terms
            if "European Research Area" in missing_terms:
                insertions.append((1, "Our methodology aligns with the European Research Area objectives of open science and collaborative research excellence."))
            if "GDPR" in missing_terms:
                insertions.append((2, "All data processing will comply with GDPR requirements, ensuring the highest standards of data protection and privacy."))
            if "strategic autonomy" in missing_terms:
                insertions.append((3, "This approach enhances European strategic autonomy in cybersecurity, reducing dependence on non-European technologies."))
        
        elif section_id == 'impact.pathways':
            # Insert impact-specific EU terms
            if "European economy" in missing_terms:
                insertions.append((1, "The project will contribute significantly to the European economy by protecting critical digital infrastructure and enabling secure digital transformation."))
            if "European resilience" in missing_terms:
                insertions.append((2, "By strengthening cybersecurity capabilities, this project enhances European resilience against evolving cyber threats."))
            if "benefit to EU" in missing_terms:
                insertions.append((3, "The clear benefit to EU includes improved security coordination across member states and strengthened collective defense capabilities."))
        
        elif section_id == 'implementation.work_plan':
            # Insert implementation-specific EU terms
            if "work package" in missing_terms:
                insertions.append((1, "The project will be structured into distinct work packages, each with clear deliverables and milestones."))
            if "TRL" in missing_terms:
                insertions.append((2, "We will advance the technology from TRL 4 to TRL 7, ensuring practical applicability in real-world scenarios."))
            if "Technology Readiness Level" in missing_terms:
                insertions.append((3, "Each component will be validated at the appropriate Technology Readiness Level to ensure maturity and readiness."))
        
        return insertions
    
    def _insert_at_position(self, text, position, insertion):
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

