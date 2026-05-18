# Task 01: Remove Domain Lock-in

> **Phase:** 0 - Foundation Fixes
> **Priority:** P0 (Production Blocker)
> **Estimated Effort:** 4-6 hours
> **Status:** Not Started

---

## Problem Statement

The `ProposalDraftGenerator` in `app/services/proposal_writing/draft_generator.py` is hardcoded to generate cybersecurity content regardless of the actual call topic.

### Current Code (Lines 248-280)
```python
def _extract_call_topic(self, call_text: str) -> str:
    """Extract the main topic from call documents"""
    # Look for cybersecurity-related keywords in the call text
    cybersecurity_keywords = [
        'cybersecurity', 'cyber security', 'cyber-security',
        'threat detection', 'threat intelligence', 'malware',
        # ... more cybersecurity keywords
    ]

    text_lower = call_text.lower()
    found_keywords = [kw for kw in cybersecurity_keywords if kw in text_lower]

    if found_keywords:
        return f"cybersecurity and AI applications, focusing on {', '.join(found_keywords[:3])}"

    # Fallback - still returns cybersecurity!
    return "research and innovation"  # This is too generic
```

### Impact
- **Climate/Energy calls (CL5)** → Gets cybersecurity content
- **Health calls (CL1)** → Gets cybersecurity content
- **Food/Agriculture calls (CL6)** → Gets cybersecurity content
- Users must rewrite everything manually

---

## Solution: Dynamic Topic Extraction

### Approach
Replace hardcoded keyword matching with LLM-based topic extraction that:
1. Analyzes the call text intelligently
2. Identifies the correct cluster (CL1-CL6, ERC, EIC, MSCA)
3. Extracts relevant keywords for that domain
4. Returns structured information for draft generation

---

## Implementation Steps

### Step 1: Create CallUnderstandingService

**File:** `app/services/proposal_writing/call_understanding_service.py`

```python
"""
Call Understanding Service

Dynamically extracts topic, cluster, and context from Horizon Europe calls.
"""

import logging
import json
import os
from typing import Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class CallUnderstandingService:
    """
    Intelligently analyze Horizon Europe calls to extract:
    - Main research topic
    - Cluster classification
    - Key technical keywords
    - EU policy alignment
    - Specific call requirements
    """

    # Horizon Europe cluster definitions
    CLUSTERS = {
        "CL1": {
            "name": "Health",
            "full_name": "Health",
            "keywords": ["health", "medical", "disease", "clinical", "patient", "healthcare",
                        "pharmaceutical", "biomedical", "diagnosis", "treatment", "therapy"]
        },
        "CL2": {
            "name": "Culture, Creativity and Inclusive Society",
            "full_name": "Culture, Creativity and Inclusive Society",
            "keywords": ["culture", "heritage", "democracy", "governance", "social", "inclusive",
                        "migration", "citizenship", "arts", "creative"]
        },
        "CL3": {
            "name": "Civil Security for Society",
            "full_name": "Civil Security for Society",
            "keywords": ["security", "cybersecurity", "crime", "terrorism", "border", "disaster",
                        "resilience", "protection", "law enforcement", "critical infrastructure"]
        },
        "CL4": {
            "name": "Digital, Industry and Space",
            "full_name": "Digital, Industry and Space",
            "keywords": ["digital", "AI", "artificial intelligence", "manufacturing", "industry",
                        "space", "robotics", "electronics", "photonics", "advanced materials"]
        },
        "CL5": {
            "name": "Climate, Energy and Mobility",
            "full_name": "Climate, Energy and Mobility",
            "keywords": ["climate", "energy", "renewable", "transport", "mobility", "emissions",
                        "hydrogen", "battery", "green", "sustainable", "carbon", "decarbonisation"]
        },
        "CL6": {
            "name": "Food, Bioeconomy, Natural Resources, Agriculture and Environment",
            "full_name": "Food, Bioeconomy, Natural Resources, Agriculture and Environment",
            "keywords": ["food", "agriculture", "biodiversity", "environment", "bioeconomy",
                        "forestry", "fisheries", "soil", "water", "circular", "ecosystem"]
        },
        "ERC": {
            "name": "European Research Council",
            "full_name": "European Research Council",
            "keywords": ["frontier research", "excellent science", "investigator-driven",
                        "breakthrough", "fundamental", "basic research"]
        },
        "EIC": {
            "name": "European Innovation Council",
            "full_name": "European Innovation Council",
            "keywords": ["innovation", "startup", "scale-up", "market", "breakthrough technology",
                        "disruptive", "commercialization", "venture"]
        },
        "MSCA": {
            "name": "Marie Skłodowska-Curie Actions",
            "full_name": "Marie Skłodowska-Curie Actions",
            "keywords": ["training", "mobility", "fellowship", "doctoral", "postdoctoral",
                        "researcher", "career development", "exchange"]
        }
    }

    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

    async def analyze_call(
        self,
        call_id: str,
        call_text: str,
        call_title: str = None
    ) -> Dict[str, Any]:
        """
        Comprehensively analyze a Horizon Europe call.

        Args:
            call_id: The call identifier (e.g., HORIZON-CL5-2025-D3-01)
            call_text: Full text of the call/topic description
            call_title: Optional call title

        Returns:
            {
                "call_id": "HORIZON-CL5-2025-D3-01",
                "cluster": {
                    "code": "CL5",
                    "name": "Climate, Energy and Mobility"
                },
                "topic": {
                    "main_topic": "Hydrogen production and storage",
                    "description": "Development of efficient hydrogen production...",
                    "technical_keywords": ["hydrogen", "electrolysis", "storage", ...],
                    "policy_keywords": ["European Green Deal", "REPowerEU", ...]
                },
                "action_type": "RIA",
                "expected_trl": {"start": 3, "end": 6},
                "eu_alignment": {
                    "strategies": ["European Green Deal", "REPowerEU"],
                    "priorities": ["Clean energy transition", "Energy security"]
                },
                "specific_requirements": [
                    "Must include at least one industrial partner",
                    "Should demonstrate pilot scale feasibility"
                ],
                "confidence": 0.92
            }
        """

        # Step 1: Quick cluster detection from call_id
        detected_cluster = self._detect_cluster_from_id(call_id)

        # Step 2: LLM analysis for detailed understanding
        llm_analysis = await self._llm_analyze_call(
            call_id, call_text, call_title, detected_cluster
        )

        # Step 3: Merge and validate
        result = self._merge_analysis(detected_cluster, llm_analysis)

        logger.info(f"Analyzed call {call_id}: cluster={result['cluster']['code']}, "
                   f"topic={result['topic']['main_topic'][:50]}...")

        return result

    def _detect_cluster_from_id(self, call_id: str) -> Optional[str]:
        """
        Quick cluster detection from call ID pattern.

        Examples:
            HORIZON-CL5-2025-D3-01 → CL5
            HORIZON-HLTH-2025-... → CL1 (Health)
            ERC-2025-STG → ERC
            HORIZON-EIC-2025-... → EIC
            HORIZON-MSCA-2025-... → MSCA
        """
        call_upper = call_id.upper()

        # Direct cluster codes
        for cluster_code in ["CL1", "CL2", "CL3", "CL4", "CL5", "CL6"]:
            if cluster_code in call_upper:
                return cluster_code

        # Alternative codes
        cluster_map = {
            "HLTH": "CL1",
            "HEALTH": "CL1",
            "CL-HLTH": "CL1",
            "CULTURE": "CL2",
            "DEMOCRACY": "CL2",
            "SECURITY": "CL3",
            "SEC": "CL3",
            "DIGITAL": "CL4",
            "INFRA": "CL4",
            "CLIMATE": "CL5",
            "ENERGY": "CL5",
            "FOOD": "CL6",
            "BIO": "CL6",
            "ERC": "ERC",
            "EIC": "EIC",
            "MSCA": "MSCA"
        }

        for pattern, cluster in cluster_map.items():
            if pattern in call_upper:
                return cluster

        return None

    async def _llm_analyze_call(
        self,
        call_id: str,
        call_text: str,
        call_title: str,
        detected_cluster: str
    ) -> Dict[str, Any]:
        """
        Use LLM to deeply analyze the call content.
        """

        cluster_hint = ""
        if detected_cluster:
            cluster_info = self.CLUSTERS.get(detected_cluster, {})
            cluster_hint = f"""
Based on the call ID, this appears to be a {cluster_info.get('full_name', detected_cluster)} call.
Verify this and provide detailed analysis specific to this domain.
"""

        prompt = f"""Analyze this Horizon Europe funding call and extract structured information.

CALL ID: {call_id}
CALL TITLE: {call_title or 'Not provided'}
{cluster_hint}

CALL TEXT:
{call_text[:4000]}  # Limit to avoid token issues

TASK: Provide a comprehensive analysis in JSON format with these fields:

{{
    "cluster": {{
        "code": "CL1-CL6, ERC, EIC, or MSCA",
        "name": "Full cluster name",
        "confidence": 0.0-1.0
    }},
    "topic": {{
        "main_topic": "2-3 sentence description of the main research topic",
        "technical_keywords": ["list", "of", "10-15", "technical", "keywords"],
        "policy_keywords": ["relevant", "EU", "policy", "terms"],
        "domain_specific_terms": ["specialized", "terminology", "for", "this", "field"]
    }},
    "action_type": "RIA, IA, CSA, or Unknown",
    "expected_trl": {{
        "start": 2,
        "end": 6,
        "description": "Brief TRL progression description"
    }},
    "eu_alignment": {{
        "strategies": ["European Green Deal", "other relevant strategies"],
        "priorities": ["specific EU priorities this addresses"],
        "sdgs": ["relevant UN SDG numbers"]
    }},
    "specific_requirements": [
        "List of specific requirements mentioned in the call",
        "e.g., consortium composition, demonstration requirements"
    ],
    "key_challenges": [
        "Main technical/scientific challenges to address"
    ],
    "expected_outcomes": [
        "What the EU expects from funded projects"
    ]
}}

Return ONLY valid JSON, no explanation."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1  # Low temperature for consistency
                }
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_analysis(call_id, call_text, detected_cluster)

    def _fallback_analysis(
        self,
        call_id: str,
        call_text: str,
        detected_cluster: str
    ) -> Dict[str, Any]:
        """
        Fallback analysis using keyword matching when LLM fails.
        """

        # Determine cluster
        if not detected_cluster:
            detected_cluster = self._keyword_cluster_detection(call_text)

        cluster_info = self.CLUSTERS.get(detected_cluster, self.CLUSTERS["CL4"])

        # Extract keywords from text
        text_lower = call_text.lower()
        found_keywords = [kw for kw in cluster_info["keywords"] if kw in text_lower]

        return {
            "cluster": {
                "code": detected_cluster or "UNKNOWN",
                "name": cluster_info["name"],
                "confidence": 0.5
            },
            "topic": {
                "main_topic": f"Research and innovation in {cluster_info['name']}",
                "technical_keywords": found_keywords[:10],
                "policy_keywords": ["Horizon Europe", "European added value"],
                "domain_specific_terms": []
            },
            "action_type": "Unknown",
            "expected_trl": {"start": 3, "end": 6, "description": "Standard TRL progression"},
            "eu_alignment": {
                "strategies": ["Horizon Europe Strategic Plan"],
                "priorities": [],
                "sdgs": []
            },
            "specific_requirements": [],
            "key_challenges": [],
            "expected_outcomes": []
        }

    def _keyword_cluster_detection(self, call_text: str) -> str:
        """
        Detect cluster based on keyword frequency in text.
        """
        text_lower = call_text.lower()
        cluster_scores = {}

        for code, info in self.CLUSTERS.items():
            score = sum(1 for kw in info["keywords"] if kw in text_lower)
            cluster_scores[code] = score

        if cluster_scores:
            return max(cluster_scores, key=cluster_scores.get)
        return "CL4"  # Default to Digital/Industry

    def _merge_analysis(
        self,
        detected_cluster: str,
        llm_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge and validate cluster detection with LLM analysis.
        """

        # Use LLM cluster if confident, otherwise use ID-based detection
        llm_cluster = llm_analysis.get("cluster", {})

        if detected_cluster and llm_cluster.get("confidence", 0) < 0.8:
            # Override with ID-based detection
            llm_cluster["code"] = detected_cluster
            llm_cluster["name"] = self.CLUSTERS.get(detected_cluster, {}).get("name", detected_cluster)

        llm_analysis["cluster"] = llm_cluster
        return llm_analysis

    def get_cluster_terminology(self, cluster_code: str) -> Dict[str, Any]:
        """
        Get cluster-specific EU terminology for draft generation.
        """

        cluster_terminology = {
            "CL1": {
                "strategies": ["EU4Health", "European Health Union", "Pharmaceutical Strategy"],
                "terms": ["patient outcomes", "health systems", "clinical validation",
                         "regulatory approval", "healthcare providers", "medical devices"],
                "impact_areas": ["public health", "healthcare access", "disease prevention"]
            },
            "CL2": {
                "strategies": ["European Democracy Action Plan", "New European Bauhaus"],
                "terms": ["cultural heritage", "social cohesion", "democratic participation",
                         "inclusive societies", "cultural diversity", "creative industries"],
                "impact_areas": ["social inclusion", "democratic resilience", "cultural preservation"]
            },
            "CL3": {
                "strategies": ["EU Security Union Strategy", "EU Cybersecurity Strategy", "NIS2 Directive"],
                "terms": ["threat detection", "cyber resilience", "critical infrastructure",
                         "law enforcement", "border security", "crisis management"],
                "impact_areas": ["citizen security", "cyber defense", "crisis preparedness"]
            },
            "CL4": {
                "strategies": ["Digital Europe Programme", "AI Act", "Data Act", "European Chips Act"],
                "terms": ["digital transformation", "AI systems", "data spaces", "digital sovereignty",
                         "advanced manufacturing", "space technologies", "quantum computing"],
                "impact_areas": ["digital leadership", "technological sovereignty", "industrial competitiveness"]
            },
            "CL5": {
                "strategies": ["European Green Deal", "Fit for 55", "REPowerEU", "EU Hydrogen Strategy"],
                "terms": ["decarbonisation", "renewable energy", "energy efficiency", "clean mobility",
                         "hydrogen economy", "climate neutrality", "circular economy"],
                "impact_areas": ["climate mitigation", "energy security", "sustainable transport"]
            },
            "CL6": {
                "strategies": ["Farm to Fork Strategy", "Biodiversity Strategy", "EU Forest Strategy"],
                "terms": ["sustainable food systems", "agroecology", "biodiversity protection",
                         "bioeconomy", "ecosystem services", "circular bioeconomy"],
                "impact_areas": ["food security", "environmental protection", "rural development"]
            },
            "ERC": {
                "strategies": ["European Research Area"],
                "terms": ["frontier research", "scientific excellence", "breakthrough discovery",
                         "fundamental understanding", "paradigm shift"],
                "impact_areas": ["scientific leadership", "knowledge creation"]
            },
            "EIC": {
                "strategies": ["European Innovation Agenda", "Scale-up Europe"],
                "terms": ["market disruption", "technology commercialization", "venture building",
                         "deep tech", "market validation", "scale-up"],
                "impact_areas": ["innovation leadership", "economic growth", "job creation"]
            },
            "MSCA": {
                "strategies": ["European Research Area", "European Skills Agenda"],
                "terms": ["researcher mobility", "skills development", "international collaboration",
                         "career development", "knowledge transfer"],
                "impact_areas": ["research capacity", "talent circulation", "knowledge society"]
            }
        }

        return cluster_terminology.get(cluster_code, cluster_terminology["CL4"])
```

---

### Step 2: Update ProposalDraftGenerator

**File:** `app/services/proposal_writing/draft_generator.py`

**Changes:**

1. Import and use `CallUnderstandingService`
2. Replace `_extract_call_topic()` with call understanding
3. Update prompt building to use dynamic context

```python
# Add to imports
from app.services.proposal_writing.call_understanding_service import CallUnderstandingService

class ProposalDraftGenerator:
    def __init__(self, call_doc_service, template_service):
        self.call_doc_service = call_doc_service
        self.template_service = template_service
        self.call_understanding = CallUnderstandingService()  # NEW

        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

    async def generate_section_draft(
        self,
        call_id: str,
        section_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:

        # NEW: Get comprehensive call understanding
        call_docs = self.call_doc_service.get_call_documents(call_id)
        call_text = " ".join([
            doc.get('title', '') + " " + doc.get('content', '')
            for doc in call_docs.get('documents', [])
        ])

        call_analysis = await self.call_understanding.analyze_call(
            call_id=call_id,
            call_text=call_text,
            call_title=call_docs.get('title')
        )

        # Get cluster-specific terminology
        cluster_terms = self.call_understanding.get_cluster_terminology(
            call_analysis['cluster']['code']
        )

        # Build context-aware prompt
        prompt = self._build_context_aware_prompt(
            section_id=section_id,
            call_id=call_id,
            call_analysis=call_analysis,
            cluster_terms=cluster_terms,
            user_context=user_context,
            guidance=self.template_service.get_section_guidance(call_id, section_id)
        )

        # ... rest of generation logic
```

---

### Step 3: Update Prompt Building

```python
def _build_context_aware_prompt(
    self,
    section_id: str,
    call_id: str,
    call_analysis: Dict[str, Any],
    cluster_terms: Dict[str, Any],
    user_context: Dict[str, Any],
    guidance: Dict
) -> str:
    """
    Build prompt using dynamic call understanding.
    """

    cluster = call_analysis['cluster']
    topic = call_analysis['topic']
    eu_alignment = call_analysis['eu_alignment']

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

    prompt = f"""You are an expert Horizon Europe proposal writer with extensive experience in {cluster['name']} research.

TASK: Write the "{section_name}" section for a Horizon Europe proposal.

=== CALL CONTEXT ===
Call ID: {call_id}
Cluster: {cluster['code']} - {cluster['name']}
Action Type: {call_analysis.get('action_type', 'RIA')}
Main Topic: {topic['main_topic']}

Key Technical Areas:
{', '.join(topic.get('technical_keywords', [])[:10])}

Expected TRL Progression: TRL {call_analysis.get('expected_trl', {}).get('start', 3)} → TRL {call_analysis.get('expected_trl', {}).get('end', 6)}

=== EU POLICY ALIGNMENT ===
Relevant EU Strategies:
{chr(10).join(['- ' + s for s in eu_alignment.get('strategies', [])])}

EU Priorities to Address:
{chr(10).join(['- ' + p for p in eu_alignment.get('priorities', [])])}

=== CLUSTER-SPECIFIC TERMINOLOGY ===
Use these terms naturally throughout your text:
- Strategies: {', '.join(cluster_terms.get('strategies', []))}
- Key terms: {', '.join(cluster_terms.get('terms', [])[:8])}
- Impact areas: {', '.join(cluster_terms.get('impact_areas', []))}

=== SPECIFIC CALL REQUIREMENTS ===
{chr(10).join(['- ' + r for r in call_analysis.get('specific_requirements', ['No specific requirements identified'])])}

=== USER'S PROJECT ===
Project Idea: {user_context.get('project_idea', 'Not provided')}
Research Area: {user_context.get('research_area', 'Not provided')}
Main Objectives: {json.dumps(user_context.get('main_objectives', []))}
Budget: €{user_context.get('budget', 0):,}
Duration: {user_context.get('duration_months', 36)} months

=== WRITING INSTRUCTIONS ===
1. Write content SPECIFICALLY about {topic['main_topic']}
2. Address ALL evaluation criteria for this section
3. Use professional EU proposal language
4. Include specific, measurable outcomes
5. Reference relevant EU strategies: {', '.join(eu_alignment.get('strategies', [])[:3])}
6. Demonstrate clear European added value
7. Target 800-1200 words
8. Use clear subsection headings

=== EVALUATION CRITERIA ===
{json.dumps(guidance.get('criteria', []), indent=2)}

Generate the section now. Write as if this is going directly into the proposal document."""

    return prompt
```

---

### Step 4: Update EU Term Enforcement

Replace the hardcoded cybersecurity terms with cluster-aware terms:

```python
def _ensure_eu_alignment_terms(
    self,
    text: str,
    section_id: str,
    cluster_code: str
) -> str:
    """
    Ensure critical EU alignment terms are included based on cluster.
    """

    # Get cluster-specific terms
    cluster_terms = self.call_understanding.get_cluster_terminology(cluster_code)

    # Common terms for all sections
    common_terms = [
        "European added value",
        "European citizens",
        "contribution to Europe"
    ]

    # Section-specific terms
    section_terms = {
        "excellence.objectives": [
            "European Commission",
            "Horizon Europe",
            "state of the art"
        ] + cluster_terms.get('strategies', [])[:2],

        "impact.pathways": [
            "European society",
            "European economy",
            "dissemination",
            "exploitation"
        ] + cluster_terms.get('impact_areas', [])[:2]
    }

    required_terms = common_terms + section_terms.get(section_id, [])

    # Check and insert missing terms
    # ... (similar logic to current implementation but with dynamic terms)
```

---

## Testing Plan

### Unit Tests
```python
# tests/test_call_understanding.py

import pytest
from app.services.proposal_writing.call_understanding_service import CallUnderstandingService

@pytest.fixture
def service():
    return CallUnderstandingService()

def test_cluster_detection_from_id(service):
    """Test cluster detection from call IDs"""
    assert service._detect_cluster_from_id("HORIZON-CL5-2025-D3-01") == "CL5"
    assert service._detect_cluster_from_id("HORIZON-HLTH-2025-001") == "CL1"
    assert service._detect_cluster_from_id("ERC-2025-STG") == "ERC"

@pytest.mark.asyncio
async def test_analyze_climate_call(service):
    """Test analysis of a climate/energy call"""
    result = await service.analyze_call(
        call_id="HORIZON-CL5-2025-D3-01",
        call_text="Development of advanced hydrogen production through electrolysis...",
        call_title="Hydrogen Production Technologies"
    )

    assert result['cluster']['code'] == "CL5"
    assert "hydrogen" in result['topic']['technical_keywords']
    assert "European Green Deal" in result['eu_alignment']['strategies']

@pytest.mark.asyncio
async def test_analyze_health_call(service):
    """Test analysis of a health call"""
    result = await service.analyze_call(
        call_id="HORIZON-HLTH-2025-DISEASE-01",
        call_text="Novel therapeutic approaches for rare diseases using gene therapy...",
        call_title="Gene Therapy for Rare Diseases"
    )

    assert result['cluster']['code'] == "CL1"
    assert any("therapy" in kw or "gene" in kw for kw in result['topic']['technical_keywords'])
```

### Integration Tests
```python
# tests/test_draft_generator_integration.py

@pytest.mark.asyncio
async def test_generate_climate_draft():
    """Test that climate call generates climate-relevant content"""
    generator = ProposalDraftGenerator(...)

    result = await generator.generate_section_draft(
        call_id="HORIZON-CL5-2025-D3-01",
        section_id="excellence.objectives",
        user_context={
            "project_idea": "Novel hydrogen storage solutions",
            "research_area": "Clean energy"
        }
    )

    # Should NOT contain cybersecurity terms
    assert "cybersecurity" not in result['draft_text'].lower()
    assert "malware" not in result['draft_text'].lower()

    # Should contain climate/energy terms
    assert "hydrogen" in result['draft_text'].lower()
    assert any(term in result['draft_text'].lower()
               for term in ["energy", "climate", "green deal", "decarbonisation"])
```

---

## Acceptance Criteria

- [ ] `CallUnderstandingService` correctly identifies cluster from call ID
- [ ] LLM analysis extracts relevant topic and keywords
- [ ] Fallback works when LLM fails
- [ ] Draft generator uses dynamic context instead of hardcoded cybersecurity
- [ ] Generated drafts contain cluster-appropriate terminology
- [ ] All existing tests still pass
- [ ] New unit tests cover all clusters

---

## Files to Modify

| File | Change |
|------|--------|
| `app/services/proposal_writing/call_understanding_service.py` | NEW - Create service |
| `app/services/proposal_writing/draft_generator.py` | Update to use CallUnderstandingService |
| `app/services/proposal_writing/__init__.py` | Export new service |
| `tests/test_call_understanding.py` | NEW - Unit tests |
| `tests/test_draft_generator_integration.py` | NEW - Integration tests |

---

## Rollback Plan

If issues arise:
1. The old `_extract_call_topic()` method can be restored
2. `CallUnderstandingService` can be bypassed with a feature flag
3. Add `USE_DYNAMIC_TOPIC_EXTRACTION=false` environment variable option

---

## Next Task

After completing this task, proceed to:
→ **Task 02: Structured LLM Outputs**
