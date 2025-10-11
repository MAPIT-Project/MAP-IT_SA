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
        template = self.template_service.generate_template(call_id)
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
            
            # 5. Analyze draft quality
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

        prompt = f"""You are an expert Horizon Europe proposal writer with 15+ years of experience writing successful RIA, IA, and CSA proposals.

TASK: Write the "{section_name}" section for a Horizon Europe proposal for call {call_id}.

IMPORTANT: This call is specifically about {call_topic}. Your content MUST be relevant to this topic. Do NOT write about unrelated topics like soil health, agriculture, or environmental issues unless they are directly related to {call_topic}.

CALL INFORMATION:
- Call ID: {call_id}
- Main Topic: {call_topic}
- Section: {section_name}

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
1. Write content SPECIFICALLY about {call_topic} - cybersecurity, AI applications, threat detection, etc.
2. Do NOT mention soil, agriculture, environment, or unrelated topics
3. Write a compelling, professional section that DIRECTLY ADDRESSES all evaluation criteria
4. Use clear, concise language appropriate for EU evaluators
5. Include specific, measurable objectives and outcomes relevant to {call_topic}
6. Demonstrate innovation and beyond state-of-the-art thinking in {call_topic}
7. Show EU added value and alignment with EU cybersecurity priorities
8. Use active voice and future-focused language
9. Be concrete and specific - avoid vague statements
10. Include relevant technical details about {call_topic} but keep it accessible
11. Target 800-1200 words for this section

WRITING STYLE:
- Professional and persuasive
- Evidence-based and factual
- Technical but accessible
- Clear structure with headings/subheadings
- EU terminology (TRL levels, work packages, deliverables, etc.)
- Focus on cybersecurity applications and AI technologies

OUTPUT FORMAT:
Generate ONLY the section content. Do not include meta-commentary.
Use clear subsection headings where appropriate.
Write as if this is going directly into the proposal document.
Ensure all content is directly related to {call_topic}.

Begin writing the section now:"""

        return prompt

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

