"""
Quality Improvement Advisor

AI-powered suggestions to improve proposal quality.
"""

import logging
from typing import Dict, Any, List
import re

logger = logging.getLogger(__name__)


class QualityImprover:
    """
    Analyze and improve proposal quality
    """
    
    def __init__(self, ai_service):
        self.ai_service = ai_service
    
    async def analyze_quality(
        self,
        section_text: str,
        section_type: str,
        call_id: str = None
    ) -> Dict[str, Any]:
        """
        Comprehensive quality analysis
        
        Returns:
            {
                "overall_quality_score": 0.75,
                "readability_score": 0.8,
                "clarity_issues": [...],
                "terminology_suggestions": [...],
                "structure_recommendations": [...],
                "improvement_suggestions": [...]
            }
        """
        
        logger.info(f"Analyzing quality of {section_type} section")
        
        # Run multiple analyses
        readability = self._analyze_readability(section_text)
        terminology = self._check_terminology(section_text)
        structure = self._analyze_structure(section_text, section_type)
        impact_level = self._analyze_impact_language(section_text)
        
        # Generate AI-powered improvements
        improvements = await self._generate_improvements(
            section_text,
            section_type,
            {
                'readability': readability,
                'terminology': terminology,
                'structure': structure,
                'impact': impact_level
            }
        )
        
        # Calculate overall score
        overall_score = (
            readability['score'] * 0.3 +
            terminology['score'] * 0.2 +
            structure['score'] * 0.3 +
            impact_level['score'] * 0.2
        )
        
        return {
            "overall_quality_score": round(overall_score, 2),
            "readability": readability,
            "terminology": terminology,
            "structure": structure,
            "impact_language": impact_level,
            "improvement_suggestions": improvements
        }
    
    def _analyze_readability(self, text: str) -> Dict[str, Any]:
        """
        Analyze text readability
        """
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        words = text.split()
        word_count = len(words)
        sentence_count = len(sentences)
        
        # Average sentence length
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Count complex words (>3 syllables - simplified)
        complex_words = [w for w in words if len(w) > 12]
        complex_word_ratio = len(complex_words) / word_count if word_count > 0 else 0
        
        issues = []
        
        # Ideal for technical writing: 15-20 words per sentence
        if avg_sentence_length > 25:
            issues.append(
                f"Sentences are too long (avg {avg_sentence_length:.1f} words). "
                "Consider breaking into shorter sentences."
            )
        elif avg_sentence_length < 10:
            issues.append(
                "Sentences are very short. Consider combining some for better flow."
            )
        
        if complex_word_ratio > 0.3:
            issues.append(
                f"{complex_word_ratio*100:.0f}% complex words. "
                "Consider using simpler alternatives where possible."
            )
        
        # Calculate score (0-1)
        length_score = 1.0 if 15 <= avg_sentence_length <= 20 else 0.7
        complexity_score = 1.0 if complex_word_ratio < 0.25 else 0.6
        score = (length_score + complexity_score) / 2
        
        return {
            "score": score,
            "avg_sentence_length": avg_sentence_length,
            "complex_word_ratio": complex_word_ratio,
            "issues": issues,
            "strengths": [] if issues else ["Good readability balance"]
        }
    
    def _check_terminology(self, text: str) -> Dict[str, Any]:
        """
        Check for proper EU/Horizon Europe terminology
        """
        
        # Key EU terms that should be present
        recommended_terms = {
            'TRL': 'Technology Readiness Level',
            'KPI': 'Key Performance Indicator',
            'WP': 'Work Package',
            'deliverable': 'Project deliverable',
            'milestone': 'Project milestone',
            'dissemination': 'Results dissemination',
            'exploitation': 'Results exploitation',
            'EU added value': 'European added value',
            'state of the art': 'Current state of the art',
            'beyond': 'Beyond state of the art'
        }
        
        text_lower = text.lower()
        
        missing_terms = []
        found_terms = []
        
        for term, description in recommended_terms.items():
            if term.lower() in text_lower:
                found_terms.append(term)
            else:
                missing_terms.append(term)
        
        # Check for deprecated/wrong terms
        wrong_terms = []
        
        if 'baseline' in text_lower and 'state of the art' not in text_lower:
            wrong_terms.append("Use 'state of the art' instead of 'baseline'")
        
        if 'task' in text_lower and 'work package' not in text_lower:
            wrong_terms.append("Consider using 'Work Package' instead of 'task'")
        
        score = len(found_terms) / len(recommended_terms)
        
        return {
            "score": score,
            "found_terms": found_terms,
            "missing_terms": missing_terms[:5],  # Top 5
            "wrong_terms": wrong_terms,
            "suggestions": [
                f"Consider adding: {term}" for term in missing_terms[:3]
            ]
        }
    
    def _analyze_structure(self, text: str, section_type: str) -> Dict[str, Any]:
        """
        Analyze section structure
        """
        
        # Check for proper headings/subheadings
        has_headings = bool(re.search(r'^#+\s+\w+|^\w+\s*:|\d+\.\d+', text, re.MULTILINE))
        
        # Check for lists/bullet points
        has_lists = bool(re.search(r'^\s*[-*•]\s+|\d+\.\s+', text, re.MULTILINE))
        
        # Check for paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        issues = []
        strengths = []
        
        if not has_headings:
            issues.append("No clear subheadings found. Add structure with headings.")
        else:
            strengths.append("Good use of headings for structure")
        
        if not has_lists and section_type in ['objectives', 'work_plan']:
            issues.append("Consider using bullet points for objectives/tasks")
        
        if paragraph_count < 3:
            issues.append("Section seems underdeveloped. Add more detailed content.")
        elif paragraph_count > 15:
            issues.append("Section is very long. Consider using subsections.")
        else:
            strengths.append("Good paragraph structure")
        
        # Calculate score
        structure_score = 1.0
        if not has_headings:
            structure_score -= 0.3
        if paragraph_count < 3 or paragraph_count > 15:
            structure_score -= 0.2
        
        return {
            "score": max(structure_score, 0),
            "has_headings": has_headings,
            "has_lists": has_lists,
            "paragraph_count": paragraph_count,
            "issues": issues,
            "strengths": strengths
        }
    
    def _analyze_impact_language(self, text: str) -> Dict[str, Any]:
        """
        Analyze use of impactful language
        """
        
        # Strong action verbs
        strong_verbs = [
            'develop', 'create', 'innovate', 'transform', 'advance',
            'pioneer', 'establish', 'demonstrate', 'achieve', 'deliver'
        ]
        
        # Weak phrases to avoid
        weak_phrases = [
            'will try to', 'might', 'possibly', 'could potentially',
            'may be able to', 'hope to'
        ]
        
        text_lower = text.lower()
        
        strong_count = sum(1 for verb in strong_verbs if verb in text_lower)
        weak_count = sum(1 for phrase in weak_phrases if phrase in text_lower)
        
        issues = []
        strengths = []
        
        if weak_count > 2:
            issues.append(
                f"Avoid weak/uncertain language ({weak_count} instances found). "
                "Use confident, definitive statements."
            )
        
        if strong_count < 3:
            issues.append(
                "Use more strong action verbs (develop, create, innovate, etc.)"
            )
        else:
            strengths.append("Good use of strong action verbs")
        
        # Check for future tense (proposals should be future-focused)
        future_indicators = ['will', 'shall', 'aims to', 'intends to']
        has_future = any(indicator in text_lower for indicator in future_indicators)
        
        if not has_future:
            issues.append("Use future tense to describe what the project will achieve")
        
        score = min((strong_count / 5) - (weak_count / 5), 1.0)
        score = max(score, 0)
        
        return {
            "score": score,
            "strong_verbs_count": strong_count,
            "weak_phrases_count": weak_count,
            "issues": issues,
            "strengths": strengths
        }
    
    async def _generate_improvements(
        self,
        text: str,
        section_type: str,
        analyses: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Use AI to generate specific improvement suggestions
        """
        
        # Collect all issues
        all_issues = []
        for analysis_name, analysis in analyses.items():
            all_issues.extend(analysis.get('issues', []))
        
        # Generate AI suggestions
        suggestions = []
        
        # If there are readability issues
        if analyses['readability']['score'] < 0.7:
            suggestions.append({
                "type": "readability",
                "priority": "high",
                "issue": "Text readability can be improved",
                "suggestion": "Break long sentences into shorter ones. Aim for 15-20 words per sentence.",
                "example": self._generate_example_improvement(text[:200])
            })
        
        # If terminology is lacking
        if analyses['terminology']['score'] < 0.5:
            missing = analyses['terminology']['missing_terms'][:2]
            suggestions.append({
                "type": "terminology",
                "priority": "medium",
                "issue": f"Missing key EU terms: {', '.join(missing)}",
                "suggestion": f"Incorporate these terms: {', '.join(missing)}",
                "example": ""
            })
        
        # If impact language is weak
        if analyses['impact']['weak_phrases_count'] > 0:
            suggestions.append({
                "type": "impact",
                "priority": "high",
                "issue": "Weak or uncertain language detected",
                "suggestion": "Replace uncertain phrases ('might', 'could', 'try to') with confident statements ('will', 'shall', 'achieves')",
                "example": "Change 'will try to develop' → 'will develop'"
            })
        
        return suggestions
    
    def _generate_example_improvement(self, text_sample: str) -> str:
        """
        Generate a simple before/after example
        """
        
        sentences = re.split(r'[.!?]+', text_sample)
        if sentences and len(sentences[0].split()) > 25:
            return f"Before: {sentences[0]}...\nAfter: [Break into 2-3 shorter sentences]"
        
        return ""

