"""
Evaluation Criteria Matcher

Analyzes proposal content against evaluation criteria.
"""

import logging
from typing import Dict, Any, List
import re
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)


class EvaluationCriteriaMatcher:
    """
    Match proposal content to evaluation criteria
    """
    
    def __init__(self):
        # Initialize Gemini for AI analysis
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-flash-lite-latest')
    
    async def analyze_section(
        self,
        section_text: str,
        evaluation_criteria: List[str],
        call_id: str
    ) -> Dict[str, Any]:
        """
        Analyze how well a section addresses evaluation criteria
        
        Returns:
            {
                "overall_score": 0.85,
                "criteria_coverage": {
                    "Scientific excellence": {
                        "addressed": True,
                        "strength": 0.9,
                        "evidence": ["paragraph 2", "paragraph 5"],
                        "gaps": []
                    },
                    ...
                },
                "recommendations": [...]
            }
        """
        
        logger.info(f"Analyzing section against {len(evaluation_criteria)} criteria")
        
        # Build AI prompt for detailed analysis
        prompt = self._build_analysis_prompt(section_text, evaluation_criteria)
        
        try:
            # Get AI analysis
            response = self.model.generate_content(prompt)
            
            # Parse response (would use structured output in production)
            analysis_text = response.text
            
            # Extract structured data from AI response
            analysis = self._parse_analysis_response(
                analysis_text,
                evaluation_criteria
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing section: {e}")
            # Fallback to simple analysis
            return self._simple_criteria_analysis(section_text, evaluation_criteria)
    
    def _build_analysis_prompt(
        self,
        section_text: str,
        criteria: List[str]
    ) -> str:
        """
        Build prompt for AI-powered criteria analysis
        """
        
        return f"""You are an expert Horizon Europe proposal evaluator. Analyze this proposal section against the evaluation criteria.

PROPOSAL SECTION:
{section_text}

EVALUATION CRITERIA:
{chr(10).join([f"{i+1}. {c}" for i, c in enumerate(criteria)])}

TASK:
For each evaluation criterion:
1. Determine if it's addressed (yes/no)
2. Rate the strength of addressing (0.0 to 1.0)
3. Identify specific evidence (which paragraphs/sentences)
4. Identify any gaps or weaknesses
5. Suggest specific improvements

OUTPUT FORMAT:
For each criterion, provide:

CRITERION: [criterion name]
ADDRESSED: [Yes/No]
STRENGTH: [0.0-1.0]
EVIDENCE: [specific quotes or paragraph references]
GAPS: [what's missing or weak]
IMPROVEMENT: [specific suggestion]

---

Begin analysis:"""

    def _parse_analysis_response(
        self,
        response_text: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """
        Parse AI response into structured format
        """
        
        # Initialize result
        coverage = {}
        recommendations = []
        total_strength = 0
        criteria_count = len(criteria)
        
        # Split by criterion sections
        sections = response_text.split('CRITERION:')[1:]  # Skip first empty split
        
        for section, criterion in zip(sections, criteria):
            # Extract information using regex
            addressed_match = re.search(r'ADDRESSED:\s*(Yes|No)', section, re.IGNORECASE)
            strength_match = re.search(r'STRENGTH:\s*([\d.]+)', section)
            evidence_match = re.search(r'EVIDENCE:\s*(.+?)(?=GAPS:|IMPROVEMENT:|$)', section, re.DOTALL)
            gaps_match = re.search(r'GAPS:\s*(.+?)(?=IMPROVEMENT:|$)', section, re.DOTALL)
            improvement_match = re.search(r'IMPROVEMENT:\s*(.+?)(?=---|\Z)', section, re.DOTALL)
            
            addressed = addressed_match.group(1).lower() == 'yes' if addressed_match else False
            strength = float(strength_match.group(1)) if strength_match else 0.5
            evidence = evidence_match.group(1).strip() if evidence_match else ""
            gaps = gaps_match.group(1).strip() if gaps_match else ""
            improvement = improvement_match.group(1).strip() if improvement_match else ""
            
            coverage[criterion] = {
                "addressed": addressed,
                "strength": strength,
                "evidence": evidence.split('\n') if evidence else [],
                "gaps": gaps.split('\n') if gaps else []
            }
            
            total_strength += strength
            
            # Add to recommendations if gaps exist
            if gaps:
                recommendations.append({
                    "criterion": criterion,
                    "type": "gap",
                    "priority": "high" if strength < 0.5 else "medium",
                    "text": improvement
                })
        
        overall_score = total_strength / criteria_count if criteria_count > 0 else 0
        
        return {
            "overall_score": round(overall_score, 2),
            "criteria_coverage": coverage,
            "recommendations": recommendations
        }
    
    def _simple_criteria_analysis(
        self,
        section_text: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """
        Fallback: Simple keyword-based analysis
        """
        
        coverage = {}
        total_score = 0
        
        for criterion in criteria:
            # Extract keywords from criterion
            keywords = [
                word.lower() for word in criterion.split()
                if len(word) > 4 and word.lower() not in [
                    'the', 'and', 'for', 'with', 'that', 'this', 'from'
                ]
            ]
            
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in section_text.lower())
            strength = min(matches / len(keywords) if keywords else 0, 1.0)
            
            coverage[criterion] = {
                "addressed": strength > 0.3,
                "strength": strength,
                "evidence": [],
                "gaps": [] if strength > 0.5 else ["Limited evidence found"]
            }
            
            total_score += strength
        
        overall_score = total_score / len(criteria) if criteria else 0
        
        return {
            "overall_score": round(overall_score, 2),
            "criteria_coverage": coverage,
            "recommendations": []
        }
    
    async def compare_versions(
        self,
        version1: str,
        version2: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """
        Compare two versions of a section against criteria
        """
        
        analysis1 = await self.analyze_section(version1, criteria, "")
        analysis2 = await self.analyze_section(version2, criteria, "")
        
        # Calculate improvement
        score_change = analysis2["overall_score"] - analysis1["overall_score"]
        
        # Identify specific improvements per criterion
        criterion_changes = {}
        for criterion in criteria:
            old_strength = analysis1["criteria_coverage"].get(criterion, {}).get("strength", 0)
            new_strength = analysis2["criteria_coverage"].get(criterion, {}).get("strength", 0)
            
            criterion_changes[criterion] = {
                "old_strength": old_strength,
                "new_strength": new_strength,
                "improvement": new_strength - old_strength
            }
        
        return {
            "version1_score": analysis1["overall_score"],
            "version2_score": analysis2["overall_score"],
            "improvement": score_change,
            "criterion_changes": criterion_changes,
            "recommendation": "Version 2" if score_change > 0 else "Version 1"
        }

