# MAPIT Quality Evaluation Skill

This skill enables LLM-as-judge evaluation of MAPIT AI responses using Claude Code subagents instead of shallow keyword/length checks.

## Overview

Traditional response testing uses:
- Keyword matching (fragile, misses semantic equivalents)
- Length thresholds (arbitrary, doesn't measure quality)
- Regex patterns (brittle, high maintenance)

**This skill implements semantic evaluation** using Claude Code subagents that:
- Decompose multi-part queries into checkable components
- Score responses against explicit rubrics
- Cross-reference against tool results for factual accuracy
- Leverage `eu-funding-domain` skill for domain accuracy verification

---

## Evaluation Dimensions

### Scoring Rubrics (100 points total)

| Dimension | Weight | Description | What to Check |
|-----------|--------|-------------|---------------|
| **Query Fulfillment** | 40% | Does it answer what was asked? | All query components addressed |
| **Specificity** | 25% | Concrete details vs vague generalities | Numbers, dates, names, examples |
| **Factual Accuracy** | 25% | Correct information | Cross-ref with eu-funding-domain |
| **Actionability** | 10% | Can user act on this? | Clear next steps, links, deadlines |

### Rubric Details

#### Query Fulfillment (0-40 points)
```
40: All query components fully addressed with relevant detail
32: Most components addressed, minor gaps
24: Main question answered, secondary parts missing
16: Partial answer, significant gaps
8:  Tangentially related, doesn't directly answer
0:  Completely off-topic or non-responsive
```

#### Specificity (0-25 points)
```
25: Rich in specifics - exact figures, dates, programme names, call IDs
20: Good specifics with minor vagueness
15: Mix of specific and general statements
10: Mostly general, few concrete details
5:  Vague generalities only
0:  No actionable specifics at all
```

#### Factual Accuracy (0-25 points)
```
25: All facts verified correct against eu-funding-domain
20: Minor inaccuracies that don't affect usability
15: Some errors but core info correct
10: Significant errors mixed with correct info
5:  More errors than correct facts
0:  Fundamentally incorrect or misleading
```

#### Actionability (0-10 points)
```
10: Clear next steps, relevant links, deadlines mentioned
8:  Good guidance with minor gaps
6:  Some actionable info but incomplete
4:  Vague suggestions only
2:  No clear path forward
0:  Actively unhelpful or confusing
```

---

## Query Decomposition

Complex queries must be decomposed before evaluation. This ensures each part is checked.

### Decomposition Examples

**Original Query:**
> "What are the eligibility requirements for Horizon Europe RIA grants and how do I find open calls?"

**Decomposed:**
1. `eligibility_requirements` - Must explain: 3 partners, 3 countries, entity types
2. `ria_specific` - Must mention: 100% funding rate, TRL 1-5 focus
3. `finding_calls` - Must provide: method to find calls (portal, tool, etc.)

**Original Query:**
> "Compare ERC Starting Grants with EIC Pathfinder for early-stage research"

**Decomposed:**
1. `erc_stg_details` - Budget (€1.5M), duration (5yr), single PI, TRL 1-3
2. `eic_pathfinder_details` - Budget (€3-4M), consortium, TRL 1-4
3. `comparison_analysis` - Key differences, when to choose each
4. `early_stage_fit` - Which suits early-stage better and why

---

## Implementation Architecture

### Using Claude Code Subagents for Evaluation

The evaluation uses the Task tool with specialized prompts:

```python
# Pseudocode for evaluation flow
async def evaluate_response(query: str, response: str, tool_results: dict):
    # Phase 1: Decompose the query
    components = await decompose_query(query)

    # Phase 2: Evaluate each component
    scores = {}
    for component in components:
        score = await evaluate_component(
            component=component,
            response=response,
            tool_results=tool_results
        )
        scores[component.name] = score

    # Phase 3: Calculate final score
    return calculate_weighted_score(scores)
```

### Subagent Prompts

#### Decomposition Subagent Prompt
```
You are a query decomposition specialist for EU funding questions.

Given this query: "{query}"

Break it down into checkable components. For each component:
1. Give it a short identifier (snake_case)
2. List the specific facts/information that MUST be in a good response
3. Reference the eu-funding-domain skill for accurate requirements

Output JSON:
{
  "components": [
    {
      "id": "component_name",
      "description": "What this component checks",
      "required_facts": ["fact1", "fact2"],
      "eu_funding_reference": "relevant section from eu-funding-domain"
    }
  ]
}
```

#### Evaluation Subagent Prompt
```
You are a response quality evaluator for MAPIT AI (EU funding assistant).

## Context
Query: "{query}"
Response to evaluate: "{response}"
Tool results used: {tool_results}

## Component to Check
{component_json}

## Scoring Rubric
{rubric_for_dimension}

## Instructions
1. Check if the response addresses this component
2. Verify facts against eu-funding-domain knowledge
3. Cross-reference with tool_results for accuracy
4. Score according to the rubric

Output JSON:
{
  "component_id": "...",
  "dimension_scores": {
    "query_fulfillment": {"score": N, "reasoning": "..."},
    "specificity": {"score": N, "reasoning": "..."},
    "factual_accuracy": {"score": N, "reasoning": "...", "errors_found": []},
    "actionability": {"score": N, "reasoning": "..."}
  },
  "total_score": N,
  "pass": true/false,
  "fix_suggestions": ["..."]
}
```

---

## File Structure

```
app/services/quality/
├── __init__.py
├── evaluator.py           # Main evaluation orchestrator
├── decomposer.py          # Query decomposition logic
├── rubrics.py             # Rubric definitions and scoring
├── accuracy_checker.py    # Cross-reference against eu-funding-domain
└── test_prompts/
    └── prompts1.py        # Test prompts from prompts1.odt

tests/quality/
├── __init__.py
├── conftest.py            # Fixtures for quality tests
├── test_response_quality.py
└── expected_results/
    └── prompts1_expectations.json
```

---

## Evaluator Implementation

### evaluator.py

```python
"""
MAPIT Response Quality Evaluator

Uses Claude Code subagents for LLM-as-judge evaluation.
"""
import json
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class EvaluationResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"

@dataclass
class ComponentScore:
    component_id: str
    query_fulfillment: float  # 0-40
    specificity: float        # 0-25
    factual_accuracy: float   # 0-25
    actionability: float      # 0-10
    reasoning: dict
    errors_found: list
    fix_suggestions: list

    @property
    def total(self) -> float:
        return (
            self.query_fulfillment +
            self.specificity +
            self.factual_accuracy +
            self.actionability
        )

    @property
    def normalized(self) -> float:
        """Score as 0-1 float"""
        return self.total / 100.0

@dataclass
class EvaluationReport:
    query: str
    response: str
    components: list[ComponentScore]
    overall_score: float
    result: EvaluationResult
    fix_suggestions: list[str]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "overall_score": self.overall_score,
            "result": self.result.value,
            "components": [
                {
                    "id": c.component_id,
                    "score": c.total,
                    "normalized": c.normalized,
                    "breakdown": {
                        "query_fulfillment": c.query_fulfillment,
                        "specificity": c.specificity,
                        "factual_accuracy": c.factual_accuracy,
                        "actionability": c.actionability
                    },
                    "errors": c.errors_found,
                    "fixes": c.fix_suggestions
                }
                for c in self.components
            ],
            "fix_suggestions": self.fix_suggestions
        }

# Thresholds
PASS_THRESHOLD = 0.85      # 85/100 to pass
REVIEW_THRESHOLD = 0.70    # 70-85 needs human review
COMPONENT_MIN = 0.50       # Each component must score at least 50%

def determine_result(overall: float, component_scores: list[ComponentScore]) -> EvaluationResult:
    """Determine pass/fail/review based on scores"""
    # Check if any component is critically low
    for comp in component_scores:
        if comp.normalized < COMPONENT_MIN:
            return EvaluationResult.FAIL

    if overall >= PASS_THRESHOLD:
        return EvaluationResult.PASS
    elif overall >= REVIEW_THRESHOLD:
        return EvaluationResult.NEEDS_REVIEW
    else:
        return EvaluationResult.FAIL
```

### decomposer.py

```python
"""
Query Decomposition for Multi-Part Questions

Breaks complex queries into checkable components.
"""
from dataclasses import dataclass

@dataclass
class QueryComponent:
    id: str
    description: str
    required_facts: list[str]
    eu_funding_reference: str
    weight: float = 1.0  # Relative importance

# Pre-defined decomposition patterns for common query types
DECOMPOSITION_PATTERNS = {
    "eligibility": {
        "pattern": r"eligib|who can|requirements|criteria",
        "components": [
            QueryComponent(
                id="entity_eligibility",
                description="Who can apply (entity types)",
                required_facts=["HES", "REC", "PRC", "SME", "PUB", "OTH"],
                eu_funding_reference="Organization Types table"
            ),
            QueryComponent(
                id="consortium_requirements",
                description="Consortium composition rules",
                required_facts=["minimum partners", "country requirements"],
                eu_funding_reference="Consortium Requirements table"
            ),
            QueryComponent(
                id="country_eligibility",
                description="Which countries can participate",
                required_facts=["EU27", "Associated Countries"],
                eu_funding_reference="Country Eligibility Quick Reference"
            )
        ]
    },
    "funding_rate": {
        "pattern": r"funding rate|how much|percentage|contribution",
        "components": [
            QueryComponent(
                id="rate_by_action",
                description="Funding rate for specific action type",
                required_facts=["percentage", "action type"],
                eu_funding_reference="Action Types and Funding Rates table"
            ),
            QueryComponent(
                id="indirect_costs",
                description="Indirect costs / overhead",
                required_facts=["25% flat rate"],
                eu_funding_reference="Budget Calculation Rules"
            )
        ]
    },
    "comparison": {
        "pattern": r"compare|versus|vs|difference|between",
        "components": [
            QueryComponent(
                id="item_a_details",
                description="Details of first item being compared",
                required_facts=["key characteristics"],
                eu_funding_reference="varies"
            ),
            QueryComponent(
                id="item_b_details",
                description="Details of second item being compared",
                required_facts=["key characteristics"],
                eu_funding_reference="varies"
            ),
            QueryComponent(
                id="comparison_analysis",
                description="Explicit comparison and recommendation",
                required_facts=["differences", "when to use each"],
                eu_funding_reference="varies"
            )
        ]
    },
    "call_search": {
        "pattern": r"open calls|find.*call|funding opportunities|deadline",
        "components": [
            QueryComponent(
                id="call_identification",
                description="Specific calls mentioned",
                required_facts=["call identifiers", "topics"],
                eu_funding_reference="N/A - from tool results"
            ),
            QueryComponent(
                id="deadline_info",
                description="Deadline information",
                required_facts=["dates", "stages"],
                eu_funding_reference="N/A - from tool results"
            ),
            QueryComponent(
                id="budget_info",
                description="Available budget",
                required_facts=["amounts", "typical grant size"],
                eu_funding_reference="N/A - from tool results"
            )
        ]
    },
    "project_search": {
        "pattern": r"funded projects|similar projects|examples|who.*funded",
        "components": [
            QueryComponent(
                id="project_examples",
                description="Relevant project examples",
                required_facts=["project names/acronyms", "relevance to query"],
                eu_funding_reference="N/A - from tool results"
            ),
            QueryComponent(
                id="project_details",
                description="Project details provided",
                required_facts=["budget", "consortium", "objectives"],
                eu_funding_reference="N/A - from tool results"
            )
        ]
    }
}

def decompose_query(query: str) -> list[QueryComponent]:
    """
    Decompose a query into checkable components.

    For complex queries, use Claude Code subagent.
    For common patterns, use pre-defined decomposition.
    """
    import re

    # Check for matching patterns
    for pattern_type, config in DECOMPOSITION_PATTERNS.items():
        if re.search(config["pattern"], query.lower()):
            return config["components"]

    # Default: single component for simple queries
    return [
        QueryComponent(
            id="main_response",
            description="Main response to query",
            required_facts=["direct answer to question"],
            eu_funding_reference="varies"
        )
    ]
```

### rubrics.py

```python
"""
Evaluation Rubrics for Response Quality

Defines scoring criteria for each dimension.
"""

RUBRICS = {
    "query_fulfillment": {
        "max_score": 40,
        "levels": [
            {"score": 40, "description": "All query components fully addressed with relevant detail"},
            {"score": 32, "description": "Most components addressed, minor gaps"},
            {"score": 24, "description": "Main question answered, secondary parts missing"},
            {"score": 16, "description": "Partial answer, significant gaps"},
            {"score": 8,  "description": "Tangentially related, doesn't directly answer"},
            {"score": 0,  "description": "Completely off-topic or non-responsive"}
        ]
    },
    "specificity": {
        "max_score": 25,
        "levels": [
            {"score": 25, "description": "Rich in specifics - exact figures, dates, programme names, call IDs"},
            {"score": 20, "description": "Good specifics with minor vagueness"},
            {"score": 15, "description": "Mix of specific and general statements"},
            {"score": 10, "description": "Mostly general, few concrete details"},
            {"score": 5,  "description": "Vague generalities only"},
            {"score": 0,  "description": "No actionable specifics at all"}
        ],
        "specificity_markers": [
            "exact percentages (e.g., '100% funding rate', '25% indirect costs')",
            "budget figures (e.g., '€3-10M', '€1.5M')",
            "deadline dates",
            "call/topic identifiers (e.g., 'HORIZON-CL5-2024-D3-01')",
            "programme names (e.g., 'ERC Starting Grant', 'MSCA Postdoctoral Fellowship')",
            "TRL levels",
            "consortium sizes (e.g., '3 partners from 3 countries')"
        ]
    },
    "factual_accuracy": {
        "max_score": 25,
        "levels": [
            {"score": 25, "description": "All facts verified correct against eu-funding-domain"},
            {"score": 20, "description": "Minor inaccuracies that don't affect usability"},
            {"score": 15, "description": "Some errors but core info correct"},
            {"score": 10, "description": "Significant errors mixed with correct info"},
            {"score": 5,  "description": "More errors than correct facts"},
            {"score": 0,  "description": "Fundamentally incorrect or misleading"}
        ],
        "common_errors": [
            "Wrong funding rates (RIA=100%, IA=70%)",
            "Wrong consortium requirements",
            "Confused action types",
            "Wrong TRL ranges",
            "Outdated budget figures",
            "Wrong country eligibility status"
        ]
    },
    "actionability": {
        "max_score": 10,
        "levels": [
            {"score": 10, "description": "Clear next steps, relevant links, deadlines mentioned"},
            {"score": 8,  "description": "Good guidance with minor gaps"},
            {"score": 6,  "description": "Some actionable info but incomplete"},
            {"score": 4,  "description": "Vague suggestions only"},
            {"score": 2,  "description": "No clear path forward"},
            {"score": 0,  "description": "Actively unhelpful or confusing"}
        ],
        "actionability_markers": [
            "specific next steps",
            "relevant portal/website links",
            "deadline dates",
            "contact points or NCPs",
            "document references",
            "tool suggestions for further exploration"
        ]
    }
}

def get_rubric_prompt(dimension: str) -> str:
    """Get the rubric as a prompt-friendly string"""
    rubric = RUBRICS[dimension]
    lines = [f"## {dimension.replace('_', ' ').title()} (0-{rubric['max_score']} points)\n"]

    for level in rubric["levels"]:
        lines.append(f"- **{level['score']} points**: {level['description']}")

    if "specificity_markers" in rubric:
        lines.append("\n**Look for these specificity markers:**")
        for marker in rubric["specificity_markers"]:
            lines.append(f"- {marker}")

    if "common_errors" in rubric:
        lines.append("\n**Common factual errors to check:**")
        for error in rubric["common_errors"]:
            lines.append(f"- {error}")

    if "actionability_markers" in rubric:
        lines.append("\n**Actionability markers:**")
        for marker in rubric["actionability_markers"]:
            lines.append(f"- {marker}")

    return "\n".join(lines)
```

### accuracy_checker.py

```python
"""
Accuracy Checker - Cross-references responses against eu-funding-domain knowledge

Uses the eu-funding-domain skill to verify factual claims.
"""

# Key facts from eu-funding-domain that are commonly needed
EU_FUNDING_FACTS = {
    # Funding rates
    "funding_rates": {
        "RIA": "100%",
        "IA": "70% (100% for non-profit)",
        "CSA": "100%",
        "ERC-STG": "100%",
        "ERC-COG": "100%",
        "ERC-ADG": "100%",
        "ERC-POC": "100%",
        "MSCA-PF": "100%",
        "MSCA-DN": "100%",
        "EIC-Pathfinder": "100%",
        "EIC-Transition": "100%",
        "EIC-Accelerator": "70% grant + equity",
    },

    # Typical budgets
    "typical_budgets": {
        "RIA": "€3-10M",
        "IA": "€5-20M",
        "CSA": "€1-3M",
        "ERC-STG": "€1.5M",
        "ERC-COG": "€2M",
        "ERC-ADG": "€2.5M",
        "ERC-POC": "€150K",
        "MSCA-PF": "€200-300K",
        "MSCA-DN": "€2-4M",
        "EIC-Pathfinder": "€3-4M",
        "EIC-Transition": "€0.5-2.5M",
        "EIC-Accelerator": "€2.5M grant + €15M equity",
    },

    # Consortium requirements
    "consortium_requirements": {
        "RIA": {"min_partners": 3, "min_countries": 3},
        "IA": {"min_partners": 3, "min_countries": 3},
        "CSA": {"min_partners": 1, "min_countries": 1},
        "ERC": {"min_partners": 1, "min_countries": 1, "note": "Single PI"},
        "MSCA-PF": {"min_partners": 1, "min_countries": 1},
        "MSCA-DN": {"min_partners": 3, "min_countries": 3},
        "EIC-Pathfinder-Open": {"min_partners": 3, "min_countries": 3},
        "EIC-Accelerator": {"min_partners": 1, "min_countries": 1, "note": "Single company"},
    },

    # TRL ranges
    "trl_ranges": {
        "RIA": "TRL 1-5",
        "IA": "TRL 5-8",
        "ERC": "TRL 1-3",
        "EIC-Pathfinder": "TRL 1-4",
        "EIC-Transition": "TRL 4-6",
        "EIC-Accelerator": "TRL 6-9",
    },

    # Indirect costs
    "indirect_costs": "25% flat rate on direct costs (excluding subcontracting)",

    # EU Member States
    "eu27": ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES",
             "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
             "NL", "PL", "PT", "RO", "SE", "SI", "SK"],
}

def check_fact(claim: str, category: str) -> dict:
    """
    Check a factual claim against known facts.

    Returns: {"correct": bool, "expected": str, "found": str}
    """
    # This would be implemented with actual fact checking logic
    # For now, provides the structure
    pass

def extract_claims(response: str) -> list[dict]:
    """
    Extract factual claims from a response for verification.

    Returns list of {"claim": str, "category": str, "value": str}
    """
    # Would use regex/NLP to extract claims about:
    # - funding rates
    # - budgets
    # - consortium requirements
    # - TRL levels
    # - country eligibility
    pass
```

---

## Pytest Integration

### conftest.py

```python
"""
Pytest fixtures for quality evaluation tests.
"""
import pytest
import json
from pathlib import Path

@pytest.fixture
def evaluator():
    """Quality evaluator instance"""
    from app.services.quality.evaluator import ResponseEvaluator
    return ResponseEvaluator()

@pytest.fixture
def test_prompts():
    """Load test prompts from prompts1"""
    # Would load from prompts1.odt or converted JSON
    return [
        {
            "id": "eligibility_basic",
            "query": "What are the eligibility requirements for Horizon Europe?",
            "category": "eligibility",
            "expected_components": ["entity_types", "consortium", "countries"]
        },
        {
            "id": "funding_rate_ria",
            "query": "What is the funding rate for RIA projects?",
            "category": "funding_rate",
            "expected_facts": ["100%", "indirect costs 25%"]
        },
        # ... more prompts
    ]

@pytest.fixture
def expected_results():
    """Load expected evaluation results"""
    path = Path(__file__).parent / "expected_results" / "prompts1_expectations.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
```

### test_response_quality.py

```python
"""
Quality evaluation tests for MAPIT AI responses.

Uses LLM-as-judge methodology with Claude Code subagents.
"""
import pytest
from app.services.quality.evaluator import EvaluationResult

class TestResponseQuality:
    """Test response quality using semantic evaluation"""

    @pytest.mark.quality
    async def test_eligibility_response_quality(self, evaluator, mapit_client):
        """Test that eligibility responses meet quality threshold"""
        query = "What are the eligibility requirements for Horizon Europe RIA grants?"

        # Get response from MAPIT
        response = await mapit_client.query(query)

        # Evaluate with Claude Code subagent
        result = await evaluator.evaluate(
            query=query,
            response=response.answer,
            tool_results=response.tool_results
        )

        # Assert quality threshold
        assert result.result == EvaluationResult.PASS, (
            f"Response quality below threshold. "
            f"Score: {result.overall_score:.2f}, "
            f"Fix suggestions: {result.fix_suggestions}"
        )

    @pytest.mark.quality
    async def test_comparison_response_quality(self, evaluator, mapit_client):
        """Test that comparison responses address all items"""
        query = "Compare ERC Starting Grants with EIC Pathfinder"

        response = await mapit_client.query(query)
        result = await evaluator.evaluate(
            query=query,
            response=response.answer,
            tool_results=response.tool_results
        )

        # Check that both items were compared
        component_ids = [c.component_id for c in result.components]
        assert "item_a_details" in component_ids or "erc_stg_details" in component_ids
        assert "comparison_analysis" in component_ids

        assert result.result != EvaluationResult.FAIL

    @pytest.mark.quality
    @pytest.mark.parametrize("prompt_data", [
        {"query": "What is the funding rate for IA?", "must_contain": "70%"},
        {"query": "How many partners for RIA?", "must_contain": "3"},
        {"query": "What is the ERC Starting Grant budget?", "must_contain": "1.5"},
    ])
    async def test_factual_accuracy(self, evaluator, mapit_client, prompt_data):
        """Test factual accuracy for specific claims"""
        response = await mapit_client.query(prompt_data["query"])
        result = await evaluator.evaluate(
            query=prompt_data["query"],
            response=response.answer,
            tool_results=response.tool_results
        )

        # Check factual accuracy dimension specifically
        for comp in result.components:
            assert comp.factual_accuracy >= 15, (
                f"Factual accuracy too low: {comp.factual_accuracy}/25. "
                f"Errors found: {comp.errors_found}"
            )

class TestDecomposition:
    """Test query decomposition"""

    def test_eligibility_decomposition(self):
        """Test that eligibility queries decompose correctly"""
        from app.services.quality.decomposer import decompose_query

        query = "What are the eligibility requirements?"
        components = decompose_query(query)

        ids = [c.id for c in components]
        assert "entity_eligibility" in ids
        assert "consortium_requirements" in ids

    def test_comparison_decomposition(self):
        """Test that comparison queries decompose into both items"""
        from app.services.quality.decomposer import decompose_query

        query = "Compare RIA vs IA grants"
        components = decompose_query(query)

        ids = [c.id for c in components]
        assert "item_a_details" in ids
        assert "item_b_details" in ids
        assert "comparison_analysis" in ids
```

---

## Running Quality Tests

### Pytest Markers

```ini
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "quality: marks tests as quality evaluation tests (may be slow)",
    "accuracy: marks tests focused on factual accuracy",
]
```

### Commands

```bash
# Run all quality tests
pytest -m quality tests/quality/

# Run with verbose output showing scores
pytest -m quality tests/quality/ -v --tb=long

# Run specific accuracy tests
pytest -m accuracy tests/quality/

# Run quality tests with coverage
pytest -m quality tests/quality/ --cov=app/services/quality

# Generate quality report
pytest -m quality tests/quality/ --json-report --json-report-file=quality_report.json
```

---

## Claude Code Subagent Usage

### For Manual Evaluation

When you need to evaluate a response manually using Claude Code:

```
I need to evaluate this MAPIT response for quality.

Query: "{query}"
Response: "{response}"

Please:
1. Read the eu-funding-domain skill for accuracy reference
2. Decompose the query into checkable components
3. Score each component on:
   - Query Fulfillment (0-40)
   - Specificity (0-25)
   - Factual Accuracy (0-25)
   - Actionability (0-10)
4. Identify any factual errors
5. Provide fix suggestions if score < 85

Use the rubrics from mapit-quality-eval skill.
```

### For Automated Evaluation via Task Tool

```python
# In test or evaluation code
from claude_code import Task

async def evaluate_with_claude(query: str, response: str) -> dict:
    """Use Claude Code subagent for evaluation"""

    prompt = f"""
    Evaluate this MAPIT AI response using the mapit-quality-eval skill rubrics.

    Query: {query}
    Response: {response}

    Score on all 4 dimensions and return JSON with:
    - component scores
    - overall score (0-100)
    - pass/fail (threshold: 85)
    - factual errors found
    - fix suggestions

    Reference eu-funding-domain skill for accuracy verification.
    """

    result = await Task(
        prompt=prompt,
        subagent_type="general-purpose",
        description="Evaluate response quality"
    )

    return json.loads(result)
```

---

## Integration with CI/CD

### GitHub Actions Workflow

```yaml
# .github/workflows/quality.yml
name: Response Quality Tests

on:
  pull_request:
    paths:
      - 'app/services/**'
      - 'tests/quality/**'

jobs:
  quality-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: make install-dev

      - name: Run quality tests
        run: pytest -m quality tests/quality/ --json-report
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Upload quality report
        uses: actions/upload-artifact@v4
        with:
          name: quality-report
          path: .report.json
```

---

## Quick Reference

### Thresholds
| Metric | Threshold | Action |
|--------|-----------|--------|
| Overall Score | >= 85 | PASS |
| Overall Score | 70-84 | NEEDS_REVIEW |
| Overall Score | < 70 | FAIL |
| Component Min | >= 50% | Required |

### Dimension Weights
| Dimension | Weight | Max Points |
|-----------|--------|------------|
| Query Fulfillment | 40% | 40 |
| Specificity | 25% | 25 |
| Factual Accuracy | 25% | 25 |
| Actionability | 10% | 10 |

### Common Query Types
| Type | Pattern | Key Components |
|------|---------|----------------|
| Eligibility | "eligib", "who can", "requirements" | entity, consortium, country |
| Funding Rate | "funding rate", "how much" | rate, indirect costs |
| Comparison | "compare", "vs", "difference" | item_a, item_b, analysis |
| Call Search | "open calls", "find calls" | identification, deadline, budget |
| Project Search | "funded projects", "examples" | examples, details |

---

## Best Practices

1. **Always decompose multi-part queries** - Don't evaluate as single unit
2. **Cross-reference factual claims** - Use eu-funding-domain for accuracy
3. **Check tool results** - Verify response uses tool data correctly
4. **Provide fix suggestions** - Failed evaluations should be actionable
5. **Use semantic matching** - Don't require exact wording, check meaning
6. **Consider context** - Some queries may have multiple valid answers
7. **Track trends** - Monitor quality scores over time for regressions
