"""
Inline Suggestions Service

Provides Grammarly-style inline suggestions for proposal text.
Analyzes sentences and phrases for improvement opportunities.
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.schemas.ai_schemas import INLINE_SUGGESTIONS_SCHEMA

logger = logging.getLogger(__name__)


class SuggestionCategory(str, Enum):
    """Category of inline suggestion."""
    EU_TERMINOLOGY = "eu_terminology"       # Use official EU terms
    CLARITY = "clarity"                     # Clearer language
    SPECIFICITY = "specificity"             # More specific/quantified
    IMPACT = "impact"                       # Stronger impact language
    PASSIVE_VOICE = "passive_voice"         # Active voice preferred
    WORDINESS = "wordiness"                 # Can be more concise
    WEAK_VERB = "weak_verb"                 # Stronger verbs
    VAGUE_CLAIM = "vague_claim"             # Needs evidence/metrics
    MISSING_CONTEXT = "missing_context"     # Add context for evaluators
    FORMATTING = "formatting"               # Structure improvements


class SuggestionPriority(str, Enum):
    """Priority level of suggestion."""
    HIGH = "high"       # Significantly affects score
    MEDIUM = "medium"   # Noticeable improvement
    LOW = "low"         # Nice to have


@dataclass
class TextSpan:
    """A span of text in the document."""
    start: int      # Character offset from start
    end: int        # Character offset end
    text: str       # The actual text


@dataclass
class InlineSuggestion:
    """A single inline suggestion."""
    id: str
    span: TextSpan
    category: SuggestionCategory
    priority: SuggestionPriority
    message: str
    suggestion: str
    replacement: Optional[str]  # Direct replacement text
    learn_more: Optional[str]   # Link or explanation


@dataclass
class AnalysisResult:
    """Result of inline analysis."""
    suggestions: List[InlineSuggestion]
    score_impact: float  # Estimated impact if all accepted
    stats: Dict[str, int]  # Count by category


class InlineSuggestionsService:
    """
    Service for generating Grammarly-style inline suggestions.

    Combines rule-based checks with LLM analysis for comprehensive
    sentence-level feedback on proposal text.
    """

    # EU terminology replacements
    EU_TERMINOLOGY_MAP = {
        # General terms
        "project goals": "project objectives",
        "team members": "consortium partners",
        "results": "outcomes and deliverables",
        "partners": "consortium members",
        "money": "funding / EU contribution",
        "budget": "financial resources",
        "timeline": "project duration / Gantt chart",
        "plan": "work plan / methodology",

        # Impact terms
        "help": "contribute to / enable",
        "improve": "enhance / strengthen",
        "make better": "optimize / advance",
        "change": "transform / revolutionize",

        # Technical terms
        "new technology": "innovative solution / novel approach",
        "cutting edge": "state-of-the-art / beyond state-of-the-art",
        "research": "R&I activities / scientific investigation",

        # EU-specific
        "european union": "EU / European Union",
        "green deal": "European Green Deal",
        "horizon europe": "Horizon Europe programme",
    }

    # Weak verbs to strengthen
    WEAK_VERBS = {
        "do": ["implement", "execute", "conduct", "perform"],
        "make": ["develop", "create", "establish", "build"],
        "get": ["obtain", "acquire", "achieve", "secure"],
        "use": ["employ", "utilize", "leverage", "apply"],
        "have": ["possess", "demonstrate", "exhibit", "maintain"],
        "show": ["demonstrate", "illustrate", "evidence", "prove"],
        "give": ["provide", "deliver", "offer", "contribute"],
        "try": ["endeavor", "strive", "aim", "seek"],
    }

    # Vague words that need quantification
    VAGUE_WORDS = [
        "many", "several", "various", "significant",
        "substantial", "major", "important", "considerable",
        "some", "few", "most", "often", "usually",
        "greatly", "highly", "very", "really", "quite"
    ]

    # Passive voice patterns
    PASSIVE_PATTERNS = [
        r'\b(is|are|was|were|been|being)\s+\w+ed\b',
        r'\b(will be|has been|have been)\s+\w+ed\b',
    ]

    def __init__(self):
        self.ai_service = ProposalAIService()

    async def analyze_text(
        self,
        text: str,
        section_type: str,
        cluster: Optional[str] = None,
        include_llm_analysis: bool = True
    ) -> AnalysisResult:
        """
        Analyze text for inline suggestions.

        Args:
            text: The text to analyze
            section_type: Type of section for context
            cluster: HE cluster for terminology context
            include_llm_analysis: Whether to use LLM for deeper analysis

        Returns:
            AnalysisResult with all suggestions
        """
        suggestions = []

        # Step 1: Rule-based checks (fast, free)
        suggestions.extend(self._check_eu_terminology(text))
        suggestions.extend(self._check_weak_verbs(text))
        suggestions.extend(self._check_vague_words(text))
        suggestions.extend(self._check_passive_voice(text))
        suggestions.extend(self._check_wordiness(text))

        # Step 2: LLM-based analysis (slower, costs tokens)
        if include_llm_analysis and len(text) > 100:
            llm_suggestions = await self._llm_analysis(text, section_type, cluster)
            suggestions.extend(llm_suggestions)

        # Remove duplicates and overlapping suggestions
        suggestions = self._deduplicate_suggestions(suggestions)

        # Assign IDs
        for i, sug in enumerate(suggestions):
            sug.id = f"sug_{i+1}"

        # Calculate stats
        stats = self._calculate_stats(suggestions)

        # Estimate score impact
        score_impact = self._estimate_score_impact(suggestions)

        return AnalysisResult(
            suggestions=suggestions,
            score_impact=score_impact,
            stats=stats
        )

    def _check_eu_terminology(self, text: str) -> List[InlineSuggestion]:
        """Check for non-EU terminology."""
        suggestions = []

        for incorrect, correct in self.EU_TERMINOLOGY_MAP.items():
            pattern = re.compile(r'\b' + re.escape(incorrect) + r'\b', re.IGNORECASE)

            for match in pattern.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.EU_TERMINOLOGY,
                    priority=SuggestionPriority.MEDIUM,
                    message=f"Consider using EU terminology: '{correct}'",
                    suggestion=f"Replace '{match.group()}' with '{correct}'",
                    replacement=correct,
                    learn_more="EU proposals use specific terminology that evaluators expect"
                ))

        return suggestions

    def _check_weak_verbs(self, text: str) -> List[InlineSuggestion]:
        """Check for weak verbs that could be stronger."""
        suggestions = []

        for weak, alternatives in self.WEAK_VERBS.items():
            # Match weak verb as whole word, not as part of compound
            pattern = re.compile(r'\b' + weak + r'\b(?!\s+(to|up|out|in|on))', re.IGNORECASE)

            for match in pattern.finditer(text):
                # Skip if it's part of a common phrase where the verb is appropriate
                context = text[max(0, match.start()-20):min(len(text), match.end()+20)]

                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.WEAK_VERB,
                    priority=SuggestionPriority.LOW,
                    message=f"Consider a stronger verb",
                    suggestion=f"Try: {', '.join(alternatives[:3])}",
                    replacement=alternatives[0],
                    learn_more="Strong verbs convey action and capability more effectively"
                ))

        return suggestions

    def _check_vague_words(self, text: str) -> List[InlineSuggestion]:
        """Check for vague words that need quantification."""
        suggestions = []

        for vague in self.VAGUE_WORDS:
            pattern = re.compile(r'\b' + vague + r'\b', re.IGNORECASE)

            for match in pattern.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.VAGUE_CLAIM,
                    priority=SuggestionPriority.MEDIUM,
                    message=f"'{match.group()}' is vague - can you quantify?",
                    suggestion="Add specific numbers, percentages, or metrics",
                    replacement=None,
                    learn_more="Evaluators prefer quantified claims (e.g., '30%' instead of 'significant')"
                ))

        return suggestions

    def _check_passive_voice(self, text: str) -> List[InlineSuggestion]:
        """Check for passive voice constructions."""
        suggestions = []

        for pattern in self.PASSIVE_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)

            for match in regex.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.PASSIVE_VOICE,
                    priority=SuggestionPriority.LOW,
                    message="Consider active voice for stronger impact",
                    suggestion="Rewrite to show who performs the action",
                    replacement=None,
                    learn_more="Active voice is more direct: 'We will develop...' vs 'will be developed'"
                ))

        return suggestions

    def _check_wordiness(self, text: str) -> List[InlineSuggestion]:
        """Check for wordy phrases."""
        wordy_phrases = {
            "in order to": "to",
            "due to the fact that": "because",
            "at this point in time": "now/currently",
            "in the event that": "if",
            "has the ability to": "can",
            "is able to": "can",
            "for the purpose of": "to/for",
            "in spite of the fact that": "although",
            "with regard to": "regarding/about",
            "in terms of": "regarding",
            "a large number of": "many",
            "the majority of": "most",
            "on a daily basis": "daily",
            "at the present time": "now/currently",
        }

        suggestions = []

        for wordy, concise in wordy_phrases.items():
            pattern = re.compile(r'\b' + re.escape(wordy) + r'\b', re.IGNORECASE)

            for match in pattern.finditer(text):
                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=match.start(),
                        end=match.end(),
                        text=match.group()
                    ),
                    category=SuggestionCategory.WORDINESS,
                    priority=SuggestionPriority.LOW,
                    message=f"Can be more concise: '{concise}'",
                    suggestion=f"Replace with '{concise}'",
                    replacement=concise,
                    learn_more="Concise writing is easier to read and stays within page limits"
                ))

        return suggestions

    async def _llm_analysis(
        self,
        text: str,
        section_type: str,
        cluster: Optional[str]
    ) -> List[InlineSuggestion]:
        """Use LLM for deeper semantic analysis."""
        prompt = f"""Analyze this proposal text for specific improvements.

SECTION TYPE: {section_type}
CLUSTER: {cluster or 'General'}

TEXT:
{text[:2000]}

Find 3-5 specific sentences or phrases that could be improved.
Focus on:
1. Claims that need evidence or quantification
2. Impact statements that could be stronger
3. Missing EU policy connections
4. Technical descriptions that need clarity
5. Weak conclusions or transitions

For each issue, provide the EXACT text span (copy the text exactly) and a specific improvement.

Only include suggestions where you can identify the exact text span."""

        try:
            response = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=INLINE_SUGGESTIONS_SCHEMA,
                temperature=0.3
            )

            suggestions = []
            for sug_data in response.get('suggestions', []):
                # Find the text span
                original = sug_data.get('original_text', '')
                start = text.find(original)

                if start == -1:
                    continue  # Skip if we can't find exact text

                # Map category string to enum
                category_str = sug_data.get('issue_type', 'clarity')
                try:
                    category = SuggestionCategory(category_str)
                except ValueError:
                    category = SuggestionCategory.CLARITY

                # Map priority string to enum
                priority_str = sug_data.get('priority', 'medium')
                try:
                    priority = SuggestionPriority(priority_str)
                except ValueError:
                    priority = SuggestionPriority.MEDIUM

                suggestions.append(InlineSuggestion(
                    id="",
                    span=TextSpan(
                        start=start,
                        end=start + len(original),
                        text=original
                    ),
                    category=category,
                    priority=priority,
                    message=sug_data.get('explanation', ''),
                    suggestion=sug_data.get('suggested_text', ''),
                    replacement=sug_data.get('suggested_text'),
                    learn_more=None
                ))

            return suggestions

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return []

    def _deduplicate_suggestions(
        self,
        suggestions: List[InlineSuggestion]
    ) -> List[InlineSuggestion]:
        """Remove duplicate and overlapping suggestions."""
        if not suggestions:
            return []

        # Sort by start position
        sorted_sugs = sorted(suggestions, key=lambda s: s.span.start)

        result = []
        for sug in sorted_sugs:
            # Check if overlaps with any existing suggestion
            overlaps = False
            for existing in result:
                if (sug.span.start < existing.span.end and
                    sug.span.end > existing.span.start):
                    # Keep higher priority one
                    priority_order = {
                        SuggestionPriority.HIGH: 3,
                        SuggestionPriority.MEDIUM: 2,
                        SuggestionPriority.LOW: 1
                    }
                    if priority_order[sug.priority] > priority_order[existing.priority]:
                        result.remove(existing)
                        result.append(sug)
                    overlaps = True
                    break

            if not overlaps:
                result.append(sug)

        return result

    def _calculate_stats(self, suggestions: List[InlineSuggestion]) -> Dict[str, int]:
        """Calculate suggestion statistics by category."""
        stats = {cat.value: 0 for cat in SuggestionCategory}

        for sug in suggestions:
            stats[sug.category.value] += 1

        return stats

    def _estimate_score_impact(self, suggestions: List[InlineSuggestion]) -> float:
        """Estimate potential score improvement if all suggestions accepted."""
        impact_weights = {
            SuggestionPriority.HIGH: 0.1,
            SuggestionPriority.MEDIUM: 0.05,
            SuggestionPriority.LOW: 0.02
        }

        total = sum(impact_weights[s.priority] for s in suggestions)
        return min(1.0, total)  # Cap at 1.0 point improvement


class RealTimeAnalyzer:
    """
    Lightweight analyzer for real-time feedback during typing.

    Uses only rule-based checks for instant response.
    """

    def __init__(self):
        self.service = InlineSuggestionsService()

    async def analyze_quick(self, text: str) -> AnalysisResult:
        """
        Quick analysis without LLM (for real-time use).

        Returns within ~10ms.
        """
        return await self.service.analyze_text(
            text=text,
            section_type="general",
            include_llm_analysis=False
        )

    def analyze_sentence(self, sentence: str) -> List[InlineSuggestion]:
        """Analyze a single sentence (synchronous, for typing)."""
        suggestions = []
        suggestions.extend(self.service._check_eu_terminology(sentence))
        suggestions.extend(self.service._check_vague_words(sentence))
        suggestions.extend(self.service._check_passive_voice(sentence))
        return suggestions

    def get_quick_feedback(self, text: str) -> Dict[str, Any]:
        """
        Get quick feedback counts without full analysis.

        Returns category counts for UI indicators.
        """
        suggestions = []
        suggestions.extend(self.service._check_eu_terminology(text))
        suggestions.extend(self.service._check_weak_verbs(text))
        suggestions.extend(self.service._check_vague_words(text))
        suggestions.extend(self.service._check_passive_voice(text))
        suggestions.extend(self.service._check_wordiness(text))

        # Deduplicate
        suggestions = self.service._deduplicate_suggestions(suggestions)

        # Count by priority
        high_count = sum(1 for s in suggestions if s.priority == SuggestionPriority.HIGH)
        medium_count = sum(1 for s in suggestions if s.priority == SuggestionPriority.MEDIUM)
        low_count = sum(1 for s in suggestions if s.priority == SuggestionPriority.LOW)

        return {
            "total": len(suggestions),
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "categories": self.service._calculate_stats(suggestions)
        }
