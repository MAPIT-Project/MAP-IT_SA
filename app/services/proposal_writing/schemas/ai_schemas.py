"""
AI Response Schemas

JSON schemas for structured LLM outputs in proposal writing services.
These schemas ensure consistent, validated responses from the AI.
"""

# Schema for criteria analysis
CRITERIA_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number", "description": "Overall score from 0.0 to 1.0"},
        "criteria_analysis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion_name": {
                        "type": "string",
                        "description": "Name of the evaluation criterion",
                    },
                    "addressed": {
                        "type": "boolean",
                        "description": "Whether the criterion is addressed",
                    },
                    "strength": {"type": "number", "description": "Strength score from 0.0 to 1.0"},
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific evidence from the text",
                    },
                    "gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Identified gaps or weaknesses",
                    },
                    "improvement_suggestion": {
                        "type": "string",
                        "description": "Specific improvement suggestion",
                    },
                },
                "required": ["criterion_name", "addressed", "strength"],
            },
        },
        "summary": {"type": "string", "description": "Brief summary of the analysis"},
        "top_improvements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Top 3 improvements ranked by impact",
        },
    },
    "required": ["overall_score", "criteria_analysis"],
}

# Schema for quality analysis
QUALITY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_quality_score": {
            "type": "number",
            "description": "Overall quality score from 0.0 to 1.0",
        },
        "readability": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "avg_sentence_length": {"type": "number"},
                "issues": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}},
            },
        },
        "terminology": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "found_terms": {"type": "array", "items": {"type": "string"}},
                "missing_terms": {"type": "array", "items": {"type": "string"}},
                "suggestions": {"type": "array", "items": {"type": "string"}},
            },
        },
        "structure": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "has_headings": {"type": "boolean"},
                "has_lists": {"type": "boolean"},
                "paragraph_count": {"type": "integer"},
                "issues": {"type": "array", "items": {"type": "string"}},
            },
        },
        "impact_language": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "strong_verbs_found": {"type": "array", "items": {"type": "string"}},
                "weak_phrases_found": {"type": "array", "items": {"type": "string"}},
                "issues": {"type": "array", "items": {"type": "string"}},
            },
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
                    "example_after": {"type": "string"},
                },
            },
        },
    },
    "required": ["overall_quality_score"],
}

# Schema for call understanding
CALL_UNDERSTANDING_SCHEMA = {
    "type": "object",
    "properties": {
        "main_topic": {
            "type": "string",
            "description": "Brief description of the main research/innovation topic",
        },
        "sub_topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of sub-topics covered by the call",
        },
        "key_objectives": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key objectives from the call",
        },
        "expected_outcomes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Expected outcomes and deliverables",
        },
        "target_trl": {
            "type": "string",
            "description": "Target TRL range (e.g., 'TRL 4-7') or null",
        },
        "action_type": {
            "type": "string",
            "description": "Action type (RIA, IA, CSA, etc.) or null",
        },
        "domain_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Domain-specific technical terms",
        },
        "confidence": {"type": "number", "description": "Confidence score from 0.0 to 1.0"},
    },
    "required": ["main_topic"],
}

# Schema for evaluator simulation
EVALUATOR_SIMULATION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number", "description": "Score from 0 to 5 in 0.5 increments"},
        "criteria_scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "score": {"type": "number"},
                    "justification": {"type": "string"},
                    "improvement_for_half_point": {"type": "string"},
                },
                "required": ["criterion", "score", "justification"],
            },
        },
        "evaluator_summary": {
            "type": "string",
            "description": "3-4 sentence summary as if writing ESR",
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "top_improvements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "improvement": {"type": "string"},
                    "expected_score_increase": {"type": "number"},
                },
            },
        },
    },
    "required": ["overall_score", "criteria_scores", "evaluator_summary"],
}

# Schema for smart rewriting
REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "rewritten_text": {"type": "string", "description": "The improved version of the text"},
        "changes_made": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific changes made",
        },
        "before_after_examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "before": {"type": "string"},
                    "after": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
        "improvement_summary": {
            "type": "string",
            "description": "2-3 sentence summary of improvements",
        },
        "word_count_change": {
            "type": "object",
            "properties": {"before": {"type": "integer"}, "after": {"type": "integer"}},
        },
    },
    "required": ["rewritten_text", "changes_made", "improvement_summary"],
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
                        "enum": [
                            "clarity",
                            "terminology",
                            "impact",
                            "grammar",
                            "eu_alignment",
                            "structure",
                        ],
                    },
                    "explanation": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["original_text", "suggested_text", "issue_type", "priority"],
            },
        },
        "total_issues_found": {"type": "integer"},
        "summary": {"type": "string"},
    },
    "required": ["suggestions"],
}
