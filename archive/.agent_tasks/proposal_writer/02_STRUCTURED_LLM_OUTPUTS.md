# Task 02: Implement Structured LLM Outputs

> **Phase:** 0 - Foundation Fixes
> **Priority:** P0 (Production Blocker)
> **Estimated Effort:** 3-4 hours
> **Status:** Not Started
> **Depends On:** Task 01 (Can be done in parallel)

---

## Problem Statement

The current implementation uses regex to parse free-form LLM text responses, which is fragile and error-prone.

### Current Code (criteria_matcher.py, lines 115-170)
```python
def _parse_analysis_response(self, response_text: str, criteria: List[str]) -> Dict[str, Any]:
    # Split by criterion sections
    sections = response_text.split('CRITERION:')[1:]  # Fragile!

    for section, criterion in zip(sections, criteria):
        # Extract information using regex - VERY FRAGILE
        addressed_match = re.search(r'ADDRESSED:\s*(Yes|No)', section, re.IGNORECASE)
        strength_match = re.search(r'STRENGTH:\s*([\d.]+)', section)
        evidence_match = re.search(r'EVIDENCE:\s*(.+?)(?=GAPS:|IMPROVEMENT:|$)', section, re.DOTALL)
        # ... more regex parsing
```

### Problems
1. **Format variations break parsing** - LLM might format output slightly differently
2. **Missing fields cause crashes** - If LLM omits a field, regex returns None
3. **No validation** - Strength could be "high" instead of "0.8"
4. **Debugging nightmare** - Hard to know what went wrong

---

## Solution: Use Gemini JSON Mode

Gemini supports structured JSON output with schema validation. This ensures:
1. Output is always valid JSON
2. All required fields are present
3. Types are correct (numbers are numbers)
4. Consistent format every time

---

## Implementation Steps

### Step 1: Create Base AI Service with JSON Support

**File:** `app/services/proposal_writing/proposal_ai_service.py`

```python
"""
Proposal AI Service

Unified AI service for proposal writing with structured outputs.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel
import google.generativeai as genai

logger = logging.getLogger(__name__)


class ProposalAIService:
    """
    AI service for proposal writing with structured JSON outputs.

    Features:
    - Guaranteed JSON responses
    - Schema validation
    - Automatic retry on parse failure
    - Multi-provider support (future)
    """

    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.3,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.

        Args:
            prompt: The prompt to send
            response_schema: JSON schema for the expected response
            temperature: LLM temperature (lower = more deterministic)
            max_retries: Number of retries on failure

        Returns:
            Parsed JSON response matching the schema
        """

        for attempt in range(max_retries + 1):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": response_schema,
                        "temperature": temperature
                    }
                )

                result = json.loads(response.text)
                return result

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    raise
                # Add explicit JSON instruction on retry
                prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no markdown or explanation."

            except Exception as e:
                logger.error(f"Generation error (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    raise

        raise RuntimeError("Failed to generate structured response")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate free-form text response.
        Use for draft generation where structure isn't needed.
        """

        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )

        return response.text
```

---

### Step 2: Define Response Schemas

**File:** `app/services/proposal_writing/schemas/ai_schemas.py`

```python
"""
AI Response Schemas

JSON schemas for structured LLM outputs.
"""

# Schema for criteria analysis
CRITERIA_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {
            "type": "number",
            "description": "Overall score from 0.0 to 1.0"
        },
        "criteria_analysis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion_name": {
                        "type": "string",
                        "description": "Name of the evaluation criterion"
                    },
                    "addressed": {
                        "type": "boolean",
                        "description": "Whether the criterion is addressed"
                    },
                    "strength": {
                        "type": "number",
                        "description": "Strength score from 0.0 to 1.0"
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific evidence from the text"
                    },
                    "gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Identified gaps or weaknesses"
                    },
                    "improvement_suggestion": {
                        "type": "string",
                        "description": "Specific improvement suggestion"
                    }
                },
                "required": ["criterion_name", "addressed", "strength"]
            }
        },
        "summary": {
            "type": "string",
            "description": "Brief summary of the analysis"
        },
        "top_improvements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Top 3 improvements ranked by impact"
        }
    },
    "required": ["overall_score", "criteria_analysis"]
}

# Schema for quality analysis
QUALITY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_quality_score": {
            "type": "number",
            "description": "Overall quality score from 0.0 to 1.0"
        },
        "readability": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "avg_sentence_length": {"type": "number"},
                "issues": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}}
            }
        },
        "terminology": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "found_terms": {"type": "array", "items": {"type": "string"}},
                "missing_terms": {"type": "array", "items": {"type": "string"}},
                "suggestions": {"type": "array", "items": {"type": "string"}}
            }
        },
        "structure": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "has_headings": {"type": "boolean"},
                "has_lists": {"type": "boolean"},
                "paragraph_count": {"type": "integer"},
                "issues": {"type": "array", "items": {"type": "string"}}
            }
        },
        "impact_language": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "strong_verbs_found": {"type": "array", "items": {"type": "string"}},
                "weak_phrases_found": {"type": "array", "items": {"type": "string"}},
                "issues": {"type": "array", "items": {"type": "string"}}
            }
        },
        "improvement_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "example_before": {"type": "string"},
                    "example_after": {"type": "string"}
                }
            }
        }
    },
    "required": ["overall_quality_score"]
}

# Schema for call understanding
CALL_UNDERSTANDING_SCHEMA = {
    "type": "object",
    "properties": {
        "cluster": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "name": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["code", "name"]
        },
        "topic": {
            "type": "object",
            "properties": {
                "main_topic": {"type": "string"},
                "technical_keywords": {"type": "array", "items": {"type": "string"}},
                "policy_keywords": {"type": "array", "items": {"type": "string"}},
                "domain_specific_terms": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["main_topic", "technical_keywords"]
        },
        "action_type": {"type": "string"},
        "expected_trl": {
            "type": "object",
            "properties": {
                "start": {"type": "integer"},
                "end": {"type": "integer"},
                "description": {"type": "string"}
            }
        },
        "eu_alignment": {
            "type": "object",
            "properties": {
                "strategies": {"type": "array", "items": {"type": "string"}},
                "priorities": {"type": "array", "items": {"type": "string"}},
                "sdgs": {"type": "array", "items": {"type": "string"}}
            }
        },
        "specific_requirements": {"type": "array", "items": {"type": "string"}},
        "key_challenges": {"type": "array", "items": {"type": "string"}},
        "expected_outcomes": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["cluster", "topic"]
}

# Schema for evaluator simulation
EVALUATOR_SIMULATION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {
            "type": "number",
            "description": "Score from 0 to 5 in 0.5 increments"
        },
        "criteria_scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "score": {"type": "number"},
                    "justification": {"type": "string"},
                    "improvement_for_half_point": {"type": "string"}
                },
                "required": ["criterion", "score", "justification"]
            }
        },
        "evaluator_summary": {
            "type": "string",
            "description": "3-4 sentence summary as if writing ESR"
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"}
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"}
        },
        "top_improvements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "improvement": {"type": "string"},
                    "expected_score_increase": {"type": "number"}
                }
            }
        }
    },
    "required": ["overall_score", "criteria_scores", "evaluator_summary"]
}

# Schema for smart rewriting
REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "rewritten_text": {
            "type": "string",
            "description": "The improved version of the text"
        },
        "changes_made": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific changes made"
        },
        "before_after_examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "before": {"type": "string"},
                    "after": {"type": "string"},
                    "reason": {"type": "string"}
                }
            }
        },
        "improvement_summary": {
            "type": "string",
            "description": "2-3 sentence summary of improvements"
        },
        "word_count_change": {
            "type": "object",
            "properties": {
                "before": {"type": "integer"},
                "after": {"type": "integer"}
            }
        }
    },
    "required": ["rewritten_text", "changes_made", "improvement_summary"]
}

# Schema for inline suggestions
INLINE_SUGGESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_index": {"type": "integer"},
                    "end_index": {"type": "integer"},
                    "original_text": {"type": "string"},
                    "suggested_text": {"type": "string"},
                    "issue_type": {
                        "type": "string",
                        "enum": ["clarity", "terminology", "impact", "grammar", "eu_alignment", "structure"]
                    },
                    "explanation": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": ["original_text", "suggested_text", "issue_type", "priority"]
            }
        },
        "total_issues_found": {"type": "integer"},
        "summary": {"type": "string"}
    },
    "required": ["suggestions"]
}
```

---

### Step 3: Update EvaluationCriteriaMatcher

**File:** `app/services/proposal_writing/criteria_matcher.py`

```python
"""
Evaluation Criteria Matcher - Updated with Structured Outputs
"""

import logging
from typing import Dict, Any, List
from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.schemas.ai_schemas import CRITERIA_ANALYSIS_SCHEMA

logger = logging.getLogger(__name__)


class EvaluationCriteriaMatcher:
    """
    Match proposal content to evaluation criteria using structured AI analysis.
    """

    def __init__(self):
        self.ai_service = ProposalAIService()

    async def analyze_section(
        self,
        section_text: str,
        evaluation_criteria: List[str],
        call_id: str
    ) -> Dict[str, Any]:
        """
        Analyze how well a section addresses evaluation criteria.

        Returns structured analysis with guaranteed fields.
        """

        logger.info(f"Analyzing section against {len(evaluation_criteria)} criteria")

        prompt = self._build_analysis_prompt(section_text, evaluation_criteria)

        try:
            # Use structured output - no more regex parsing!
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=CRITERIA_ANALYSIS_SCHEMA,
                temperature=0.2  # Low temperature for consistent evaluation
            )

            # Transform to expected format
            return self._transform_result(result, evaluation_criteria)

        except Exception as e:
            logger.error(f"Error analyzing section: {e}")
            return self._simple_criteria_analysis(section_text, evaluation_criteria)

    def _build_analysis_prompt(
        self,
        section_text: str,
        criteria: List[str]
    ) -> str:
        """Build prompt for structured criteria analysis."""

        criteria_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(criteria)])

        return f"""You are an expert Horizon Europe proposal evaluator. Analyze this proposal section against the evaluation criteria.

PROPOSAL SECTION:
{section_text}

EVALUATION CRITERIA:
{criteria_list}

TASK:
For each criterion, provide:
1. Whether it's addressed (true/false)
2. Strength score (0.0 to 1.0)
3. Specific evidence from the text
4. Any gaps or weaknesses
5. Specific improvement suggestion

Also provide:
- Overall score (average of all criteria strengths)
- Summary of the analysis
- Top 3 improvements ranked by impact

Be thorough but concise. Base scores on actual content, not assumptions."""

    def _transform_result(
        self,
        result: Dict[str, Any],
        criteria: List[str]
    ) -> Dict[str, Any]:
        """Transform structured result to expected format."""

        # Build criteria coverage dict
        coverage = {}
        recommendations = []

        for analysis in result.get("criteria_analysis", []):
            criterion_name = analysis.get("criterion_name", "")

            # Find matching criterion from input list
            matched_criterion = None
            for c in criteria:
                if criterion_name.lower() in c.lower() or c.lower() in criterion_name.lower():
                    matched_criterion = c
                    break

            if matched_criterion:
                coverage[matched_criterion] = {
                    "addressed": analysis.get("addressed", False),
                    "strength": analysis.get("strength", 0.5),
                    "evidence": analysis.get("evidence", []),
                    "gaps": analysis.get("gaps", [])
                }

                # Add recommendation if there are gaps
                if analysis.get("gaps"):
                    recommendations.append({
                        "criterion": matched_criterion,
                        "type": "gap",
                        "priority": "high" if analysis.get("strength", 0.5) < 0.5 else "medium",
                        "text": analysis.get("improvement_suggestion", "")
                    })

        return {
            "overall_score": result.get("overall_score", 0.5),
            "criteria_coverage": coverage,
            "recommendations": recommendations,
            "summary": result.get("summary", ""),
            "top_improvements": result.get("top_improvements", [])
        }

    def _simple_criteria_analysis(
        self,
        section_text: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """Fallback: Simple keyword-based analysis (unchanged from before)."""

        coverage = {}
        total_score = 0

        for criterion in criteria:
            keywords = [
                word.lower() for word in criterion.split()
                if len(word) > 4 and word.lower() not in ['the', 'and', 'for', 'with', 'that']
            ]

            matches = sum(1 for kw in keywords if kw in section_text.lower())
            strength = min(matches / len(keywords) if keywords else 0, 1.0)

            coverage[criterion] = {
                "addressed": strength > 0.3,
                "strength": strength,
                "evidence": [],
                "gaps": [] if strength > 0.5 else ["Limited evidence found"]
            }

            total_score += strength

        return {
            "overall_score": round(total_score / len(criteria), 2) if criteria else 0,
            "criteria_coverage": coverage,
            "recommendations": [],
            "summary": "Fallback analysis used - AI analysis unavailable",
            "top_improvements": []
        }
```

---

### Step 4: Update QualityImprover

**File:** `app/services/proposal_writing/quality_improver.py`

```python
"""
Quality Improvement Advisor - Updated with AI-Powered Analysis
"""

import logging
from typing import Dict, Any, List
from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.schemas.ai_schemas import QUALITY_ANALYSIS_SCHEMA

logger = logging.getLogger(__name__)


class QualityImprover:
    """
    Analyze and improve proposal quality using AI.
    """

    def __init__(self):
        self.ai_service = ProposalAIService()

    async def analyze_quality(
        self,
        section_text: str,
        section_type: str,
        call_id: str = None
    ) -> Dict[str, Any]:
        """
        Comprehensive AI-powered quality analysis.
        """

        logger.info(f"Analyzing quality of {section_type} section")

        prompt = self._build_quality_prompt(section_text, section_type)

        try:
            result = await self.ai_service.generate_structured(
                prompt=prompt,
                response_schema=QUALITY_ANALYSIS_SCHEMA,
                temperature=0.3
            )

            return result

        except Exception as e:
            logger.error(f"AI quality analysis failed: {e}")
            # Fallback to rule-based analysis
            return self._rule_based_analysis(section_text, section_type)

    def _build_quality_prompt(
        self,
        section_text: str,
        section_type: str
    ) -> str:
        """Build prompt for quality analysis."""

        return f"""Analyze the quality of this Horizon Europe proposal section.

SECTION TYPE: {section_type}

SECTION TEXT:
{section_text}

Analyze the following aspects:

1. READABILITY
   - Average sentence length (ideal: 15-20 words)
   - Complex word usage
   - Overall readability for EU evaluators

2. EU TERMINOLOGY
   - Check for key Horizon Europe terms: TRL, KPI, WP, deliverable, milestone, dissemination, exploitation, EU added value, state of the art
   - Identify missing recommended terms
   - Suggest terminology improvements

3. STRUCTURE
   - Presence of clear headings/subheadings
   - Use of bullet points or numbered lists
   - Paragraph organization
   - Logical flow

4. IMPACT LANGUAGE
   - Use of strong action verbs (develop, create, innovate, transform)
   - Presence of weak/uncertain language (might, could, try to)
   - Future-focused language

5. IMPROVEMENT SUGGESTIONS
   - Provide specific, actionable suggestions
   - Include before/after examples where possible
   - Prioritize by impact (critical, high, medium, low)

Be specific and constructive in your analysis."""

    def _rule_based_analysis(
        self,
        section_text: str,
        section_type: str
    ) -> Dict[str, Any]:
        """Fallback rule-based analysis."""

        # Simplified version of original heuristic analysis
        import re

        sentences = re.split(r'[.!?]+', section_text)
        words = section_text.split()
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])

        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        # Check for EU terms
        eu_terms = ['trl', 'kpi', 'deliverable', 'milestone', 'dissemination', 'exploitation']
        found_terms = [t for t in eu_terms if t in section_text.lower()]

        return {
            "overall_quality_score": 0.5,
            "readability": {
                "score": 0.7 if 15 <= avg_sentence_length <= 25 else 0.5,
                "avg_sentence_length": avg_sentence_length,
                "issues": ["Fallback analysis - limited accuracy"],
                "strengths": []
            },
            "terminology": {
                "score": len(found_terms) / len(eu_terms),
                "found_terms": found_terms,
                "missing_terms": [t for t in eu_terms if t not in found_terms],
                "suggestions": []
            },
            "structure": {
                "score": 0.5,
                "has_headings": bool(re.search(r'^#+\s+\w+', section_text, re.MULTILINE)),
                "has_lists": bool(re.search(r'^\s*[-*•]\s+', section_text, re.MULTILINE)),
                "paragraph_count": len(section_text.split('\n\n')),
                "issues": ["Fallback analysis - limited accuracy"]
            },
            "impact_language": {
                "score": 0.5,
                "strong_verbs_found": [],
                "weak_phrases_found": [],
                "issues": ["Fallback analysis - limited accuracy"]
            },
            "improvement_suggestions": [{
                "type": "general",
                "priority": "medium",
                "issue": "AI analysis unavailable",
                "suggestion": "Please retry for detailed AI-powered analysis",
                "example_before": "",
                "example_after": ""
            }]
        }
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_proposal_ai_service.py

import pytest
from app.services.proposal_writing.proposal_ai_service import ProposalAIService
from app.services.proposal_writing.schemas.ai_schemas import CRITERIA_ANALYSIS_SCHEMA

@pytest.fixture
def ai_service():
    return ProposalAIService()

@pytest.mark.asyncio
async def test_structured_output_returns_valid_json(ai_service):
    """Test that structured output returns valid JSON."""

    result = await ai_service.generate_structured(
        prompt="Analyze this text: 'We will develop innovative solutions'",
        response_schema=CRITERIA_ANALYSIS_SCHEMA
    )

    assert isinstance(result, dict)
    assert "overall_score" in result
    assert isinstance(result["overall_score"], (int, float))

@pytest.mark.asyncio
async def test_structured_output_matches_schema(ai_service):
    """Test that output matches expected schema."""

    result = await ai_service.generate_structured(
        prompt="Analyze this text against criterion 'Innovation level': 'We will develop breakthrough technology'",
        response_schema=CRITERIA_ANALYSIS_SCHEMA
    )

    assert "criteria_analysis" in result
    if result["criteria_analysis"]:
        analysis = result["criteria_analysis"][0]
        assert "addressed" in analysis
        assert "strength" in analysis
        assert isinstance(analysis["addressed"], bool)
        assert isinstance(analysis["strength"], (int, float))

@pytest.mark.asyncio
async def test_retry_on_invalid_json(ai_service, mocker):
    """Test that service retries on invalid JSON."""

    # Mock first call to return invalid JSON, second to return valid
    call_count = 0
    original_generate = ai_service.model.generate_content

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            class MockResponse:
                text = "not valid json"
            return MockResponse()
        return original_generate(*args, **kwargs)

    mocker.patch.object(ai_service.model, 'generate_content', mock_generate)

    # Should succeed on retry
    result = await ai_service.generate_structured(
        prompt="Test prompt",
        response_schema=CRITERIA_ANALYSIS_SCHEMA
    )

    assert call_count == 2  # Retried once
```

### Integration Tests

```python
# tests/test_criteria_matcher_structured.py

import pytest
from app.services.proposal_writing.criteria_matcher import EvaluationCriteriaMatcher

@pytest.fixture
def matcher():
    return EvaluationCriteriaMatcher()

@pytest.mark.asyncio
async def test_analyze_section_returns_structured_result(matcher):
    """Test that analysis returns all expected fields."""

    result = await matcher.analyze_section(
        section_text="We will develop innovative AI solutions for healthcare. "
                     "The methodology includes machine learning and clinical validation.",
        evaluation_criteria=["Innovation level", "Soundness of methodology"],
        call_id="TEST-CALL"
    )

    # Check all expected fields exist
    assert "overall_score" in result
    assert "criteria_coverage" in result
    assert "recommendations" in result
    assert "summary" in result

    # Check score is valid
    assert 0 <= result["overall_score"] <= 1

    # Check criteria coverage structure
    for criterion, coverage in result["criteria_coverage"].items():
        assert "addressed" in coverage
        assert "strength" in coverage
        assert isinstance(coverage["addressed"], bool)
        assert 0 <= coverage["strength"] <= 1
```

---

## Acceptance Criteria

- [ ] `ProposalAIService` reliably returns structured JSON
- [ ] All schemas are defined in `ai_schemas.py`
- [ ] `EvaluationCriteriaMatcher` no longer uses regex parsing
- [ ] `QualityImprover` uses AI for analysis with rule-based fallback
- [ ] Retry logic handles transient failures
- [ ] All existing tests pass
- [ ] New unit tests cover schema validation

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/services/proposal_writing/proposal_ai_service.py` | CREATE |
| `app/services/proposal_writing/schemas/__init__.py` | CREATE |
| `app/services/proposal_writing/schemas/ai_schemas.py` | CREATE |
| `app/services/proposal_writing/criteria_matcher.py` | MODIFY |
| `app/services/proposal_writing/quality_improver.py` | MODIFY |
| `tests/test_proposal_ai_service.py` | CREATE |
| `tests/test_criteria_matcher_structured.py` | CREATE |

---

## Next Task

After completing this task, proceed to:
→ **Task 03: Multi-Provider AI Support**
