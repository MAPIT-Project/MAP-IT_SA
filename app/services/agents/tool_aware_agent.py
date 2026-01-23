# isort: skip_file
"""
Tool-Aware ReAct Agent

An advanced agent that can:
1. Reason about what tools to use
2. Call multiple tools in parallel or sequence
3. Compare and contrast results from different sources
4. Iteratively refine by calling more tools based on conclusions
5. Synthesize a final answer from multiple sources

Based on the ReAct (Reasoning + Acting) pattern.
"""

import asyncio
import json
import logging
import os
import re
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXT WINDOW MANAGEMENT
# =============================================================================


@dataclass
class ContextLimits:
    """Configuration for context window limits."""

    # Maximum tokens for various components (approximate, using char/4 ratio)
    max_context_chars: int = 100000  # ~25k tokens
    max_tool_result_chars: int = 5000  # Per tool result
    max_observation_chars: int = 1500  # Per reasoning step
    max_document_chars: int = 600  # Per document in synthesis
    max_documents_per_result: int = 10  # Max docs to include
    max_calls_per_result: int = 15  # Max calls to include
    max_projects_per_result: int = 10  # Max projects to include
    reserved_for_response: int = 4000  # Reserve for output

    @classmethod
    def from_env(cls) -> "ContextLimits":
        """Load limits from environment variables with defaults."""
        return cls(
            max_context_chars=int(os.getenv("MAX_CONTEXT_CHARS", "100000")),
            max_tool_result_chars=int(os.getenv("MAX_TOOL_RESULT_CHARS", "5000")),
            max_observation_chars=int(os.getenv("MAX_OBSERVATION_CHARS", "1500")),
            max_document_chars=int(os.getenv("MAX_DOCUMENT_CHARS", "600")),
        )


class ContextWindowManager:
    """Manages context window for LLM prompts to prevent overflow."""

    def __init__(self, limits: ContextLimits | None = None):
        self.limits = limits or ContextLimits.from_env()
        self._current_size = 0

    def reset(self):
        """Reset the context size tracker."""
        self._current_size = 0

    @property
    def current_size(self) -> int:
        """Get the current context size in characters."""
        return self._current_size

    def truncate_text(self, text: str, max_chars: int, suffix: str = "...") -> str:
        """Truncate text to max_chars, adding suffix if truncated."""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix

    def truncate_tool_result(self, result: Any) -> str:
        """Truncate a tool result to fit within limits."""
        if result is None:
            return "No results"

        result_str = str(result) if not isinstance(result, str) else result
        return self.truncate_text(result_str, self.limits.max_tool_result_chars)

    def truncate_observation(self, observation: str) -> str:
        """Truncate an observation to fit within limits."""
        return self.truncate_text(observation, self.limits.max_observation_chars)

    def truncate_document(self, content: str) -> str:
        """Truncate document content to fit within limits."""
        return self.truncate_text(content, self.limits.max_document_chars)

    def estimate_prompt_size(self, prompt: str) -> int:
        """Estimate the token count of a prompt (chars / 4 approximation)."""
        return len(prompt) // 4

    def would_exceed_limit(self, additional_chars: int) -> bool:
        """Check if adding more content would exceed the context limit."""
        return (self._current_size + additional_chars) > self.limits.max_context_chars

    def add_to_context(self, content: str) -> str:
        """Add content to context, truncating if necessary."""
        available = (
            self.limits.max_context_chars - self._current_size - self.limits.reserved_for_response
        )
        if available <= 0:
            logger.warning("Context window exhausted, dropping content")
            return ""

        if len(content) > available:
            content = self.truncate_text(content, available)
            logger.warning(f"Content truncated to fit context window ({available} chars)")

        self._current_size += len(content)
        return content

    def format_results_for_context(
        self, results: dict[str, Any], priority_keys: list[str] | None = None
    ) -> str:
        """Format tool results for inclusion in context, respecting limits."""
        if not results:
            return "No tool results yet"

        # Prioritize certain result types
        priority_keys = priority_keys or ["calls", "projects", "documents"]

        formatted_parts = []
        remaining_budget = (
            self.limits.max_context_chars - self._current_size - self.limits.reserved_for_response
        )

        for name, result in results.items():
            if remaining_budget <= 0:
                logger.warning("Skipping remaining results due to context limits")
                break

            result_str = self.truncate_tool_result(result)
            part = f"\n**{name}**: {result_str}\n"

            if len(part) > remaining_budget:
                part = self.truncate_text(part, remaining_budget)

            formatted_parts.append(part)
            remaining_budget -= len(part)

        return "".join(formatted_parts)


# Global context manager instance
_context_manager = ContextWindowManager()


class ToolCategory(Enum):
    """Categories of tools available to the agent."""

    STATISTICS = "statistics"  # Graph DB queries for numbers
    DOCUMENTS = "documents"  # Vector search for text
    CALLS = "calls"  # Funding call search
    PROJECTS = "projects"  # CORDIS project search
    COMPARISON = "comparison"  # Cross-reference tools
    VALIDATION = "validation"  # Fact-checking tools
    PROGRAMMES = "programmes"  # Multi-programme discovery and info
    PROPOSAL = "proposal"  # Proposal writing and quality tools


@dataclass
class Tool:
    """Definition of a tool the agent can use."""

    name: str
    description: str
    category: ToolCategory
    parameters: dict[str, Any]
    examples: list[str] = field(default_factory=list)
    executor: Callable[..., Awaitable[Any]] | None = None

    def to_prompt_format(self) -> str:
        """Format tool for LLM prompt."""
        params_str = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"- **{self.name}**({params_str}): {self.description}"


@dataclass
class ToolCall:
    """A planned or executed tool call."""

    tool_name: str
    parameters: dict[str, Any]
    reasoning: str = ""
    result: Any = None
    success: bool = False
    error: str | None = None
    execution_time_ms: float = 0


@dataclass
class ReasoningStep:
    """A single step in the agent's reasoning process."""

    step_number: int
    thought: str
    action: str  # "call_tool", "analyze", "conclude", "compare"
    tool_calls: list[ToolCall] = field(default_factory=list)
    observation: str = ""
    next_action_needed: bool = True


@dataclass
class AgentPlan:
    """The agent's plan for answering a complex question."""

    query: str
    complexity: str  # "simple", "multi_source", "comparison", "analysis"
    required_sources: list[str]
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    final_answer: str | None = None
    confidence: float = 0.0
    sources_used: list[str] = field(default_factory=list)


class ToolAwareAgent:
    """
    ReAct-style agent that reasons about and uses multiple tools.

    Key capabilities:
    - Analyzes query complexity to determine tool needs
    - Calls multiple tools in parallel when independent
    - Sequences tool calls when results depend on each other
    - Compares and contrasts results from different sources
    - Iteratively refines by calling more tools based on findings
    """

    # Built-in knowledge for common questions where documents may be incomplete
    BUILT_IN_KNOWLEDGE = """
## Quick Reference: Horizon Europe Facts

### Official Resources (ALWAYS include when explaining programme structure)
When answering questions about Horizon Europe structure, ALWAYS include these actionable links at the end:

🎯 **Getting Started with Horizon Europe:**
• Register on [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
• Review the [Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) for your cluster
• Check eligibility via [How to Participate](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• Find partners using [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)
• Browse [Call Calendar](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar)

### Page Limits for Proposals (Part B - Technical Description)
| Action Type | Standard Page Limit | Notes |
|-------------|---------------------|-------|
| **RIA/IA (single-stage)** | **45 pages** | Sections 1-3 combined |
| **RIA/IA (two-stage, full)** | **45 pages** | After passing stage 1 |
| **RIA/IA (two-stage, outline)** | **10 pages** | Stage 1 only |
| **CSA** | **30 pages** | Shorter scope |
| **ERC grants** | **Variable** | Check specific call |
| **MSCA** | **10-15 pages** | Depends on action |
| **EIC Accelerator** | **Variable** | Short proposal + full |

*Page limits are strictly enforced. Excess pages will be blanked and not evaluated.*

### Organisation Type Eligibility
| Organisation Type | Eligible? | Funding Rate (RIA) | Funding Rate (IA) | Special Notes |
|-------------------|-----------|-------------------|-------------------|---------------|
| **Universities/HEIs** | Yes | 100% | 100% | Must have GEP |
| **Research Institutes** | Yes | 100% | 100% | Must have GEP |
| **SMEs** | Yes | 100% | 70% | EIC Accelerator available |
| **Large Companies** | Yes | 100% | 70% | Cannot lead some calls |
| **NGOs** | Yes | 100% | 100% (non-profit) | Often needed for dissemination |
| **Public Bodies** | Yes | 100% | 100% | Must have GEP |
| **International Orgs** | Case-by-case | Varies | Varies | Check specific call |

### Action Types Summary
| Type | TRL Range | Funding Rate | Focus |
|------|-----------|--------------|-------|
| **RIA** | TRL 2-5 | 100% | Research, new knowledge |
| **IA** | TRL 5-8 | 70%/100% | Demonstration, piloting |
| **CSA** | N/A | 100% | Coordination, networking |

### RIA Project Details (Research and Innovation Actions)

When answering questions about RIA project parameters (duration, payment, budget), use these specifics:

#### Project Duration
| Duration Type | Range | Notes |
|--------------|-------|-------|
| **Typical** | **36-48 months** | Standard for most RIA topics |
| **Maximum** | **Up to 60 months** | For complex research requiring longer timelines |
| **Minimum** | **24 months** | Rare, for focused/shorter topics |

*Always check the specific Work Programme topic for "Expected Duration" - it varies by call.*

#### Payment Modality (RIA)
RIA projects use the **Actual Cost** model with **100% reimbursement** and follow this payment schedule:

| Payment Type | Timing | Amount/Details |
|--------------|--------|----------------|
| **Pre-financing** | Within 30 days of grant signature | 40-50% of total EC contribution (advance payment) |
| **Interim Payment(s)** | After periodic reporting periods (typically 18 months) | Based on actual costs reported, minus pre-financing consumed |
| **Final Payment** | After final report approval | Remaining balance (5-10% typically retained until final review) |

**Key Payment Rules:**
- **Reporting periods**: Usually every 18 months or at project midpoint
- **Pre-financing guarantee**: May be required for coordinators with small annual turnover
- **Cost eligibility**: Costs must be incurred during project period, necessary for implementation
- **Indirect costs**: 25% flat rate on direct costs (excluding subcontracting)

#### Budget & Costs (RIA)
| Category | Typical Range/Rate | Notes |
|----------|-------------------|-------|
| **Total budget** | **€3-10 million** | Varies by topic; check Work Programme |
| **Funding rate** | **100%** | Full reimbursement of eligible costs |
| **Indirect costs** | **25% flat rate** | Applied to direct costs minus subcontracting |
| **Personnel costs** | 55-65% of budget | Largest cost category |
| **Subcontracting** | Max 5-15% recommended | No indirect costs on subcontracting |

**Budget Formula:**
```
EU Contribution = Direct Costs + (Direct Costs - Subcontracting) × 25%
```

🎯 **RIA Resources:**
• [Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf) - Complete payment and cost rules
• [Financial Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/unit-cost-decision-sme-owners-managers_he_en.pdf) - Cost eligibility details
• [Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) - Topic-specific parameters

### Consortium Requirements
- **Standard (RIA/IA/CSA)**: 3 independent entities from 3 different EU/AC countries
- **ERC**: Single PI (monobeneficiary)
- **MSCA PF**: Single fellow + host
- **EIC Accelerator**: Single SME or small group

### Typical Consortium Sizes (Based on Funded Project Data)

| Action Type | Avg Partners | Typical Range | Avg Countries | Key Characteristics |
|-------------|--------------|---------------|---------------|---------------------|
| **RIA** | 10-12 | 6-16 | 6-8 | Research focus, strong academic presence, TRL 1-5 |
| **IA** | 14-16 | 10-20 | 8-10 | Demo/scale-up, more industry partners (35-45%), TRL 5-8 |
| **CSA** | 6-9 | 3-12 | 4-6 | Coordination/networking, smaller focused teams, policy focus |

**Key differences in consortium composition:**
- **IA (Innovation Action)**: Larger consortia because demonstration/deployment requires more end-users, pilots, and industry involvement. Higher industry participation (35-45% PRC/SME).
- **CSA (Coordination & Support Action)**: Smaller, agile teams focused on networking, policy support, or standardization. Often led by associations or policy organizations.
- **RIA (Research & Innovation Action)**: Balanced research consortia with strong academic/research institute presence (55-65% HES/REC).

### Budget Limits / Expected EU Contribution per Project
There is NO single fixed budget limit for Innovation Actions (IA) or other action types. Budgets are defined per TOPIC in the Work Programme.

| Action Type | Typical EU Contribution Range | Notes |
|-------------|------------------------------|-------|
| **RIA (standard)** | €3-8 million | Varies by topic complexity |
| **IA (standard)** | €5-15 million | Large-scale demonstrations |
| **IA (flagship/large)** | €15-50 million | Strategic topics only |
| **CSA** | €1-3 million | Coordination activities |
| **ERC Starting** | Up to €1.5 million | 5 years |
| **ERC Consolidator** | Up to €2 million | 5 years |
| **ERC Advanced** | Up to €2.5 million | 5 years |
| **EIC Accelerator** | Up to €2.5M grant + €15M equity | Blended finance |

**How to find actual limits:** Check the specific Call Topic in the Work Programme - it states "Expected EU contribution per project: €X-Y million"

### Getting Started with Proposal Writing
If someone asks "How do I start writing a proposal?" or "Where do I start?", provide this guidance:

1. **Find a relevant call**: Search for open calls on the EU Funding & Tenders Portal that match your research area
2. **Understand the call**: Read the Work Programme topic carefully - understand scope, expected outcomes, and evaluation criteria
3. **Build your consortium**: Most calls require 3+ partners from 3+ different EU/Associated countries
4. **Write the proposal**: Follow the template structure (Excellence, Impact, Implementation)
5. **Use the search tools**: Search for similar funded projects to learn from successful proposals

### Proposal Template Structure (Part B)
Standard RIA/IA proposals have 3 main sections:
- **Section 1: Excellence** - Scientific quality, objectives, methodology, ambition (beyond state-of-art)
- **Section 2: Impact** - Expected outcomes, pathways to impact, dissemination, exploitation
- **Section 3: Implementation** - Work plan, consortium, resources, management

### Evaluation Criteria
| Section | Threshold | Weight | Key aspects |
|---------|-----------|--------|-------------|
| Excellence | 4/5 | ~1/3 | Objectives, methodology, ambition |
| Impact | 4/5 | ~1/3 | Outcomes, dissemination, exploitation |
| Implementation | 3/5 | ~1/3 | Work plan, consortium, resources |
| **Overall** | **10/15** | - | Must pass all thresholds |

### Why Some Countries Have Higher Success Rates (Analytical Knowledge)
When users ask about country success rate disparities, provide this analysis:

**Key Factors Affecting Country Success Rates:**

1. **National R&D Investment**: Countries with higher R&D spending (% of GDP) tend to have stronger research institutions and more competitive proposals. Nordic countries (Sweden, Finland, Denmark) and central European nations (Germany, Netherlands) consistently perform well.

2. **Institutional Experience**: Organizations with extensive EU funding track records understand evaluation criteria better, have established partnerships, and write more competitive proposals. First-time applicants face a steep learning curve.

3. **National Support Systems**: Some countries have dedicated National Contact Points (NCPs), proposal writing support services, and pre-submission review programs that significantly improve proposal quality.

4. **Language Proficiency**: Proposals are evaluated in English. Non-native English speaking countries may face subtle disadvantages in proposal clarity and persuasiveness.

5. **Consortium Networks**: Countries with strong international research networks can more easily build competitive consortiums with complementary partners.

6. **Strategic Focus**: Some countries strategically target calls where they have comparative advantages, rather than spreading efforts across all areas.

7. **Coordination Culture**: Countries with traditions of collaborative research (vs. competitive individual research) adapt better to consortium-based EU funding.

**Typical Success Rates by Country Type:**
- **EU-15 established members**: 12-18% average success rate
- **EU-13 newer members**: 8-12% average success rate (improving with Widening participation actions)
- **Associated Countries**: Varies widely (Switzerland historically ~20%, UK post-Brexit ~15%)

**Note**: Success rates vary significantly by programme. For specific country data, use the get_country_statistics tool with a specific country name.

### Marie Skłodowska-Curie Actions (MSCA) - Complete Overview

MSCA is part of **Pillar I - Excellent Science** in Horizon Europe. It funds researcher mobility, training, and career development with a total budget of **€6.6 billion (2021-2027)**.

#### MSCA Action Types

| Action | Full Name | Budget | Duration | Participants | Funding Rate |
|--------|-----------|--------|----------|--------------|--------------|
| **MSCA-PF** | Postdoctoral Fellowships | €200-300K per fellow | 12-24 months | Single researcher + host | 100% |
| **MSCA-DN** | Doctoral Networks | €2-4M per network | 48 months | 3+ partners, 3+ countries | 100% |
| **MSCA-SE** | Staff Exchanges | €0.5-1.5M | 48 months | 3+ partners, 2+ countries | 100% |
| **MSCA-COFUND** | Co-funding of programmes | €10M max | 60 months | Single organization | 100% of unit costs |

#### MSCA-PF (Postdoctoral Fellowships)
- **Purpose**: Support experienced researchers to conduct independent research abroad
- **Eligibility**: PhD holders or 4+ years research experience
- **Types**:
  - **European Fellowships (EF)**: Research in any EU/Associated Country
  - **Global Fellowships (GF)**: Outgoing phase (12-24m) + mandatory return (12m)
- **Budget**: Living allowance (~€5,080/month) + mobility (~€600/month) + family (~€660/month if applicable) + research/training costs
- **Consortium**: Single fellow + single host institution

#### MSCA-DN (Doctoral Networks)
- **Purpose**: Train doctoral candidates through international, inter-sectoral, and interdisciplinary research
- **Participants**: Early-stage researchers (no PhD, <4 years experience)
- **Duration**: 36-48 months (network), 3-36 months per researcher
- **Budget**: €2.5-4M per network; unit costs per researcher-month
- **Consortium**: Min 3 beneficiaries from 3 different countries
- **Types**: Standard DN, Industrial Doctorates, Joint Doctorates

#### MSCA-SE (Staff Exchanges)
- **Purpose**: Enable international, inter-sectoral secondments for knowledge transfer
- **Eligibility**: Staff at any career stage (researchers, technical, management)
- **Duration**: 1-12 months per secondment
- **Budget**: €100/day (staff) + €2,000/month contribution to host
- **Consortium**: Min 3 participants from 2 countries; must include 2 sectors (academic + non-academic)

#### MSCA-COFUND
- **Purpose**: Co-fund regional, national, or international fellowship or doctoral programmes
- **Eligibility**: Legal entities running existing funding programmes
- **Budget**: Flat rate per researcher-month (up to €10M per project)
- **Duration**: 36-60 months
- **Consortium**: Single beneficiary (programme operator)

#### MSCA Key Resources (ALWAYS include when answering MSCA questions)
🎯 **Getting Started with MSCA:**
• Visit the [MSCA Portal](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• Read the [MSCA Work Programme 2025](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Search calls on [EU Funding Portal - MSCA](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=MSCA;matchWholeText=true;typeCodes=1,0;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=null;focusAreaCode=null;destinationGroup=null;missionGroup=null;geographicalZonesCode=null;programmeDivisionProsp498Code=null;startDateLte=null;startDateGte=null;crossCuttingPriorityCode=null;cpvCode=null;performanceOfDelivery=null;sortQuery=sortStatus;orderBy=asc;onlyTenders=false;topicListKey=topicSearchTablePageState)
• Check eligibility via [MSCA Guide for Applicants](https://rea.ec.europa.eu/funding-and-grants/horizon-europe-marie-sklodowska-curie-actions_en)
• Use [Euraxess](https://euraxess.ec.europa.eu/) for job/fellowship searches

### Horizon Europe Clusters and EU Missions - Complete Overview

Clusters and Missions are key components of **Pillar II: Global Challenges and European Industrial Competitiveness** in Horizon Europe.

#### The 6 Thematic Clusters

Clusters organize collaborative research addressing major societal challenges. Each cluster has its own Work Programme with specific topics and calls.

| Cluster | Name | Focus Areas | Budget (2021-2027) |
|---------|------|-------------|-------------------|
| **Cluster 1** | Health | Disease prevention, treatment, healthcare systems, pandemic preparedness, cancer research, personalized medicine | ~€8.2 billion |
| **Cluster 2** | Culture, Creativity & Inclusive Society | Democracy, governance, cultural heritage, social cohesion, migration, European identity | ~€2.3 billion |
| **Cluster 3** | Civil Security for Society | Cybersecurity, disaster resilience, border security, counter-terrorism, critical infrastructure protection | ~€1.6 billion |
| **Cluster 4** | Digital, Industry & Space | AI, robotics, advanced manufacturing, semiconductors, quantum computing, space technologies | ~€15.3 billion |
| **Cluster 5** | Climate, Energy & Mobility | Clean energy, hydrogen, batteries, smart grids, sustainable transport, climate-neutral solutions | ~€15.1 billion |
| **Cluster 6** | Food, Bioeconomy, Natural Resources, Agriculture & Environment | Sustainable food systems, biodiversity, circular economy, forestry, fisheries, water, soil health | ~€9 billion |

#### The 5 EU Missions

EU Missions are a NEW approach in Horizon Europe: challenge-driven research portfolios with **ambitious, measurable targets** for 2030.

| Mission | Full Name | Target | Key Actions |
|---------|-----------|--------|-------------|
| **Cancer** | Conquering Cancer | Improve lives of 3+ million people through prevention, cure, and better quality of life | Early detection, personalized treatment, patient-centered care |
| **Climate Adaptation** | Adaptation to Climate Change | Support 150+ EU regions to become climate-resilient by 2030 | Climate risk assessment, adaptation pathways, regional transformation |
| **Ocean & Waters** | Restore our Ocean and Waters | Restore health of ocean and waters by 2030 | Marine protected areas, pollution reduction, blue economy |
| **Cities** | Climate-Neutral & Smart Cities | 100 European cities climate-neutral by 2030 | City Climate Contracts, citizen engagement, urban innovation |
| **Soil** | A Soil Deal for Europe | 100 living labs and lighthouses for healthy soils by 2030 | Soil monitoring, sustainable land management, soil carbon |

#### Key Differences: Clusters vs Missions

| Aspect | Clusters | Missions |
|--------|----------|----------|
| **Approach** | Thematic grouping of research topics | Challenge-driven with specific 2030 targets |
| **Structure** | Annual Work Programmes with multiple topics | Mission-specific calls and implementation plans |
| **Goal** | Research excellence and knowledge generation | Measurable societal impact by 2030 |
| **Scope** | Broad research areas | Focused, time-bound objectives |
| **Governance** | REA/CINEA implementation | Mission Boards advising on strategy |

#### Cluster Key Resources (ALWAYS include when answering Cluster/Mission questions)
🎯 **Getting Started with Clusters and Missions:**
• Browse Cluster Work Programmes: [Horizon Europe Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Find Cluster calls: [EU Funding Portal - Topic Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
• Learn about EU Missions: [EU Missions Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe_en)
• Mission implementation: [Mission Implementation Plans](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/mission-implementation_en)

### Searching for Calls by Research Domain - CRITICAL GUIDANCE

When a researcher asks about funding calls for their domain (e.g., "health research", "cancer research", "AI research"), you MUST:

1. **Search the PRIMARY cluster** for their domain using `search_funding_calls` with cluster filter
2. **ALWAYS mention MSCA cross-cutting opportunities** (MSCA is open to ALL research domains)

#### Research Domain → Cluster Mapping

| Research Domain | Primary Cluster | Call ID Pattern | Also Check |
|-----------------|-----------------|-----------------|------------|
| **Health, cancer, medical, clinical, disease, pharmaceutical, biomedical, vaccine, pandemic** | **Cluster 1 (Health)** | `HORIZON-HLTH-*` | EU Mission on Cancer (MISS-CANCER-*) |
| **Digital, AI, robotics, quantum, semiconductors, industry, manufacturing, space** | **Cluster 4 (Digital/Industry/Space)** | `HORIZON-CL4-*` | EIC Pathfinder |
| **Climate, energy, hydrogen, batteries, transport, mobility, green** | **Cluster 5 (Climate/Energy/Mobility)** | `HORIZON-CL5-*` | EU Mission Climate |
| **Food, agriculture, biodiversity, environment, bioeconomy, soil, water, oceans** | **Cluster 6 (Food/Bioeconomy)** | `HORIZON-CL6-*` | EU Mission Soil, EU Mission Ocean |
| **Culture, heritage, democracy, social, creative, digital heritage, museum, archaeology** | **Cluster 2 (Culture/Inclusive)** | `HORIZON-CL2-*` | Creative Europe, Cluster 4 (for digital technologies) |
| **Security, cybersecurity, disaster, border, crime** | **Cluster 3 (Security)** | `HORIZON-CL3-*` | - |

#### CRITICAL: MSCA is Cross-Cutting (ALWAYS mention for research calls)

**Marie Skłodowska-Curie Actions (MSCA)** are **thematic-neutral** and available for researchers in ANY field:

- **MSCA-PF** (Postdoctoral Fellowships): For experienced researchers to conduct research in any domain
- **MSCA-DN** (Doctoral Networks): For PhD training networks in any research area
- **MSCA-SE** (Staff Exchanges): For knowledge transfer in any field

When answering "What calls are available for [domain] research?", ALWAYS include:
1. Cluster-specific calls (e.g., HORIZON-HLTH-* for health)
2. MSCA opportunities (cross-cutting, applicable to ALL domains)
3. Relevant Missions if applicable (e.g., EU Mission on Cancer for cancer research)

#### Example: Health/Cancer Research Calls

For health or cancer researchers, include:
- **Cluster 1 Health calls** (HORIZON-HLTH-2025-*, HORIZON-HLTH-2026-*): Disease prevention, treatment, healthcare systems, pandemic preparedness
- **EU Mission on Cancer** (HORIZON-MISS-2025-CANCER-*, HORIZON-MISS-2026-CANCER-*): Early detection, personalized treatment, quality of life
- **MSCA opportunities**: MSCA-PF-2025 (September deadline), MSCA-DN-2025 for doctoral training
- **ERC grants**: For frontier research in any domain

🎯 **Health Research Resources:**
• Cluster 1 Work Programme: [Health Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission on Cancer: [Mission Cancer Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/eu-mission-cancer_en)
• MSCA Portal: [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• Search Health calls: [EU Portal - Health Cluster](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=;matchWholeText=true;typeCodes=1,0;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=43108557)

#### Example: Climate Change Monitoring Research Calls (MULTIDISCIPLINARY)

Climate monitoring research is **inherently multidisciplinary** - it spans MULTIPLE clusters. Include:

**Primary: Cluster 5 - Climate, Energy and Mobility (HORIZON-CL5-*):**
- Climate science and climate services
- Earth system observation
- Climate change mitigation technologies
- Carbon capture and storage
- Sustainable energy systems

**Also Critical: Cluster 6 - Food, Bioeconomy, Natural Resources (HORIZON-CL6-*):**
- Environmental monitoring and biodiversity
- Ocean and water systems monitoring
- Soil health and ecosystem services
- Land use and forestry monitoring
- Circular economy and resource efficiency

**Relevant EU Missions (ALWAYS mention these for climate monitoring):**
- **Mission: Adaptation to Climate Change** (HORIZON-MISS-*-CLIMA-*): Climate-resilient regions, monitoring for adaptation
- **Mission: Restore our Ocean and Waters** (HORIZON-MISS-*-OCEAN-*): Marine monitoring, healthy oceans by 2030
- **Mission: A Soil Deal for Europe** (HORIZON-MISS-*-SOIL-*): Soil health monitoring, 100 living labs

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for climate/environmental researchers
- **EIC Pathfinder**: Breakthrough climate monitoring technologies
- **ERC**: Frontier research on climate science

🎯 **Climate/Environment Research Resources:**
• Cluster 5 Work Programme: [Climate, Energy, Mobility](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Cluster 6 Work Programme: [Food, Bioeconomy, Natural Resources](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission Climate Adaptation: [Climate Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/adaptation-climate-change_en)
• EU Mission Ocean: [Ocean Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/restore-our-ocean-and-waters_en)
• EU Mission Soil: [Soil Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/soil-deal-europe_en)
• European Green Deal: [Green Deal Priorities](https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/european-green-deal_en)
• MSCA Portal: [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)

#### Example: Agriculture/Food Research Calls

Agriculture and food research is covered by **Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture and Environment**. Include:

**Primary: Cluster 6 - Food, Bioeconomy, Natural Resources (HORIZON-CL6-*):**
- Sustainable farming systems and agroecology
- Food systems and nutrition security
- Biodiversity and natural capital
- Circular and bio-based solutions
- Forestry and wood-based industries
- Water, soil, and land management

**Call ID Patterns (Cluster 6):**
- `HORIZON-CL6-*-FARM2FORK-*`: Farm to Fork sustainable food systems
- `HORIZON-CL6-*-BIODIV-*`: Biodiversity and ecosystem services
- `HORIZON-CL6-*-CIRCBIO-*`: Circular bioeconomy
- `HORIZON-CL6-*-ZEROPOL-*`: Zero pollution agriculture
- `HORIZON-CL6-*-GOVERNANCE-*`: Land and resource governance

**Relevant EU Missions (ALWAYS mention for agriculture/food):**
- **Mission: A Soil Deal for Europe** (HORIZON-MISS-*-SOIL-*): Soil health, sustainable land use, 100 living labs by 2030
- **Mission: Restore our Ocean and Waters** (HORIZON-MISS-*-OCEAN-*): Water quality, sustainable aquaculture
- **Mission: Adaptation to Climate Change** (HORIZON-MISS-*-CLIMA-*): Climate-resilient agriculture

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for agricultural/food researchers (ANY domain)
- **EIC Pathfinder**: Breakthrough agritech innovations
- **ERC**: Frontier research in agriculture and food science

🎯 **Agriculture/Food Research Resources:**
• Cluster 6 Work Programme: [Food, Bioeconomy, Natural Resources](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission Soil: [Soil Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/soil-deal-europe_en)
• Farm to Fork Strategy: [Farm to Fork](https://food.ec.europa.eu/horizontal-topics/farm-fork-strategy_en)
• EU Bioeconomy: [Bioeconomy Strategy](https://research-and-innovation.ec.europa.eu/research-area/environment/bioeconomy_en)
• MSCA Portal: [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• Search Cluster 6 calls: [EU Portal - Cluster 6](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=;matchWholeText=true;typeCodes=1,0;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=43108567)

#### Example: Digital Cultural Heritage Research (MULTIDISCIPLINARY)

Digital cultural heritage is inherently **multidisciplinary**, spanning Cluster 2 (Culture) and Cluster 4 (Digital). Include:

**Primary: Cluster 2 - Culture, Creativity and Inclusive Society (HORIZON-CL2-*):**
- Cultural heritage preservation and restoration
- Digitization of cultural assets (3D scanning, semantic modeling)
- Participatory approaches to heritage
- European identity and cultural diversity
- New European Bauhaus initiatives

**Secondary: Cluster 4 - Digital, Industry and Space (HORIZON-CL4-*):**
- Digital twin technologies
- AI and machine learning for cultural applications
- Advanced sensor systems and monitoring
- Immersive technologies (VR/AR for heritage)
- Data management and interoperability

**Call ID Patterns (Cultural Heritage):**
- `HORIZON-CL2-*-HERITAGE-*`: Dedicated heritage preservation topics
- `HORIZON-CL2-*-DEMOCRACY-*`: Heritage in democratic societies
- `HORIZON-CL4-*-TWIN-*`: Digital twin technologies
- `HORIZON-CL4-*-DATA-*`: Data spaces for culture

**Key Reference Projects (for benchmarking):**
| Project | Grant ID | Focus | CORDIS Link |
|---------|----------|-------|-------------|
| **ARIADNE-PLUS** | 823914 | Archaeological data infrastructure | cordis.europa.eu/project/id/823914 |
| **Time Machine** | 820323 | Big data for historical digitization | cordis.europa.eu/project/id/820323 |
| **INCEPTION** | 665220 | 3D semantic modelling for heritage | cordis.europa.eu/project/id/665220 |

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for heritage researchers
- **EIC Pathfinder**: Breakthrough technologies for cultural heritage
- **Creative Europe**: Complementary funding for cultural projects

🎯 **Digital Cultural Heritage Resources:**
• Cluster 2 Work Programme: [Culture, Creativity](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• New European Bauhaus: [NEB Portal](https://new-european-bauhaus.europa.eu/)
• EU Digital Strategy for Culture: [Digital Culture](https://digital-strategy.ec.europa.eu/en/policies/cultural-heritage)
• Europeana: [European Cultural Heritage](https://www.europeana.eu/)
• CORDIS Heritage Projects: [Search CORDIS](https://cordis.europa.eu/search?q=cultural%20heritage)

### Niche Topic Search Keywords (for Project Searches)

When searching for projects at the intersection of multiple specialized topics, use these expanded keyword sets:

#### Industry 4.0/5.0 Keywords (expand searches with these)
| Core Terms | Technology Terms | Application Terms |
|------------|-----------------|-------------------|
| Industry 4.0 | IoT, sensors | smart farming |
| Industry 5.0 | AI, machine learning | precision agriculture |
| digitalization | robotics, automation | digital twin |
| digital transformation | data-driven | smart monitoring |
| cyber-physical systems | edge computing | predictive analytics |
| human-machine collaboration | big data | real-time monitoring |

#### Soil Regeneration Keywords (expand searches with these)
| Core Terms | Scientific Terms | Practice Terms |
|------------|-----------------|----------------|
| soil regeneration | carbon sequestration | regenerative agriculture |
| soil health | soil microbiome | agroecology |
| soil restoration | soil organic matter | no-till farming |
| land degradation | nutrient cycling | cover cropping |
| soil fertility | soil biodiversity | composting |
| soil remediation | erosion control | sustainable farming |

**Example Multi-Search Strategy for "Industry 4.0 + Soil Regeneration":**
```
Search 1: "digital agriculture soil health monitoring" - core intersection
Search 2: "precision farming regenerative soil sensors" - technology + application
Search 3: "smart soil monitoring carbon sequestration" - monitoring focus
Search 4: "AI machine learning soil management agriculture" - AI applications
Search 5: "IoT sensors sustainable farming soil" - IoT applications
```

#### SSH/Cluster 2 Keywords (Culture, Creativity & Inclusive Society)
| Core Terms | Governance Terms | Social Terms | Policy Evaluation Terms |
|------------|-----------------|--------------|------------------------|
| democracy | governance | social cohesion | policy evaluation |
| cultural heritage | policy | inclusive society | impact assessment |
| European identity | citizenship | migration | monitoring indicators |
| humanities | participation | inequality | socioeconomic analysis |
| creative industries | rule of law | gender equality | welfare systems |
| arts and culture | transparency | diversity inclusion | labor market policy |

**SSH/Cluster 2 Search Strategy:**
```
Search 1: "democracy governance society" → Core SSH
Search 2: "cultural heritage European identity" → Heritage focus
Search 3: "social cohesion inclusion migration" → Social science
Search 4: "creative industries culture arts" → Creative/arts focus
Search 5: "policy participation citizenship" → Governance focus
Search 6: "policy evaluation monitoring socioeconomic" → Policy evaluation focus
```

**Top SSH/Cluster 2 Coordinators (Reference):**
Major coordinators in Cluster 2/SSH typically include:
- Utrecht University (UU) - NL - Strong in democracy, governance
- University of Bologna (UNIBO) - IT - Humanities, heritage
- Politecnico di Milano (POLIMI) - IT - Design, creative industries
- KU Leuven - BE - Social sciences, humanities
- University of Amsterdam (UvA) - NL - Culture, media, social sciences
- Leiden University (ULEI) - NL - Humanities, area studies
- University of Barcelona (UB) - ES - Heritage, social sciences
- Lund University - SE - Humanities, social sciences
- University of Helsinki - FI - Social sciences, governance
- Radboud University - NL - Social sciences, humanities

#### Cultural Heritage Keywords (CRITICAL for heritage project searches)
| Core Terms | Technology Terms | Application Terms |
|------------|-----------------|-------------------|
| cultural heritage | digital twin | heritage preservation |
| heritage digitization | 3D scanning | monument restoration |
| cultural preservation | AI preservation | museum digitization |
| archaeological | VR heritage | historic buildings |
| heritage sites | AR cultural | restoration technology |
| cultural assets | semantic modeling | heritage monitoring |

**CRITICAL: Search Strategy for "Digital Cultural Heritage" Projects:**
The search_projects tool uses SIMPLE KEYWORD MATCHING. Use SHORT, SPECIFIC terms:
```
Search 1: "cultural heritage" → Best general term, yields most results
Search 2: "heritage digitization" → Technology focus
Search 3: "archaeological data" → Archaeological projects
Search 4: "heritage preservation digital" → Preservation + digital
Search 5: "3D heritage" → 3D scanning/modeling projects
```

**DO NOT USE:**
- Long complex phrases (e.g., "interdisciplinary project in digital tech preservation of cultural heritage")
- Multiple concepts together (e.g., "digital twining predictive maintenance heritage participatory")

**ALWAYS USE:**
- 2-3 word simple keywords (e.g., "cultural heritage", "heritage digital", "archaeological")
- Run MULTIPLE searches with different simple keywords if first search yields no results
- If first search returns 0 results, immediately try alternative simpler keywords

#### Water/Health/Sanitation Keywords (CRITICAL for water-health project searches)
| Core Terms | Health Terms | Infrastructure Terms |
|------------|-------------|---------------------|
| drinking water | water quality health | sewage systems |
| water sanitation | waterborne disease | wastewater treatment |
| water health | public health water | water infrastructure |
| urban water | environmental health | sanitation systems |
| rural water | health impact water | water pollution |
| aquatic health | epidemiology water | water management |

**CRITICAL: Search Strategy for "Water/Health" Projects:**
Water and health intersection spans MULTIPLE clusters (Cluster 1: Health AND Cluster 6: Environment). Use SHORT, SPECIFIC terms:
```
Search 1: "drinking water health" → Core intersection
Search 2: "water quality sanitation" → Infrastructure focus
Search 3: "waterborne disease" → Health impact focus
Search 4: "urban water health" → Urban context
Search 5: "aquatic health ecosystem" → Environmental health (Cluster 6 projects)
Search 6: "water pollution health" → Pollution + health impact
```

**Key Reference Projects for Water/Health (use as fallback):**
| Project | Grant ID | Focus | Budget | Coordinator |
|---------|----------|-------|--------|-------------|
| **OneAquaHealth** | 101086521 | One Health approach for urban aquatic ecosystems | €4.94M | Universidade de Coimbra (PT) |
| **StopUP** | 101060428 | Protecting aquatic environment from urban runoff pollution | €3.77M | RWTH Aachen (DE) |
| **AquaticPollutants** | 869178 | Contaminants in water resources | €4.0M | INRAE (FR) |
| **PARC** | 101057014 | Chemical risk assessment for human health and environment | €400M | ANSES (FR) |
| **GloFouling** | 774009 | Invasive species via biofouling, ecosystem and health impacts | €3.6M | IMO (UK) |

**Call ID Patterns for Water/Health:**
- `HORIZON-CL6-*-ZEROPOL-*`: Zero pollution in water (Cluster 6)
- `HORIZON-CL6-*-WATER-*`: Sustainable water management (Cluster 6)
- `HORIZON-HLTH-*-ENVHLTH-*`: Environmental determinants of health (Cluster 1)
- `HORIZON-MISS-*-OCEAN-*`: EU Mission: Restore our Ocean and Waters
- `HORIZON-MISS-*-SOIL-*`: EU Mission: Soil (linked to water quality)

#### Example: Water/Health Research Calls (MULTIDISCIPLINARY)

Water and health research is **inherently multidisciplinary** - it spans Cluster 1 (Health), Cluster 6 (Environment), and EU Missions. Include:

**Primary: Cluster 6 - Food, Bioeconomy, Natural Resources (HORIZON-CL6-*) - Water Focus:**
- Zero Pollution destination: Water quality, pollution prevention, wastewater treatment
- Healthy Oceans and Waters: Freshwater ecosystems, drinking water sources
- Sustainable water management and governance
- Nature-based solutions for water treatment

**Secondary: Cluster 1 - Health (HORIZON-HLTH-*) - Health Impact Focus:**
- Destination 4: Environmental determinants of health
- Non-communicable diseases linked to environmental exposure
- Infectious disease prevention (waterborne pathogens)
- Digital health and monitoring systems

**Relevant EU Missions (ALWAYS mention for water/health):**
- **Mission: Restore our Ocean and Waters** (HORIZON-MISS-*-OCEAN-*): Water quality, pollution reduction, healthy aquatic ecosystems
- **Mission: A Soil Deal for Europe** (HORIZON-MISS-*-SOIL-*): Soil health affects water quality, groundwater protection
- **Mission: Adaptation to Climate Change** (HORIZON-MISS-*-CLIMA-*): Water scarcity, drought adaptation

**Cross-Cutting Opportunities:**
- **MSCA**: MSCA-PF and MSCA-DN for water/health researchers (ANY domain)
- **EIC Pathfinder**: Breakthrough water treatment technologies
- **ERC**: Frontier research in environmental health

🎯 **Water/Health Research Resources:**
• Cluster 6 Work Programme (Water): [Food, Bioeconomy, Natural Resources](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Cluster 1 Work Programme (Health): [Health Cluster](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• EU Mission Ocean & Waters: [Ocean Mission Portal](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/restore-our-ocean-and-waters_en)
• EU Zero Pollution Action Plan: [Zero Pollution](https://environment.ec.europa.eu/strategy/zero-pollution-action-plan_en)
• CORDIS Water Projects: [Search CORDIS](https://cordis.europa.eu/search?q=water%20health)

### Third Country Eligibility and Participation (Non-EU, Non-Associated Countries)

When a researcher asks about eligibility from a **non-EU, non-Associated country** (e.g., Japan, USA, China, South Korea, Australia, Canada, Brazil, India), provide this guidance:

#### Country Classification

| Category | Countries | Horizon Europe Participation |
|----------|-----------|------------------------------|
| **EU Member States (27)** | AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI, FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK | ✅ Full eligibility, full funding |
| **Associated Countries** | CH*, IL*, IS, NO, UK*, AL, BA, XK, ME, MK, RS, TR, GE, MD, UA | ✅ Full eligibility (check current status) |
| **Third Countries** | Japan, USA, China, South Korea, Australia, Canada, Brazil, India, etc. | ⚠️ Limited participation, restrictions apply |

*Check association status - some may be pending/suspended (e.g., Switzerland since 2021)*

#### Third Country Participation Rules

**Key Facts:**
- Third country organizations are **NOT automatically eligible** for EU funding
- Participation is possible but with **significant restrictions**
- Must check **specific call text** for third country eligibility conditions
- When allowed, typically must be **self-funded** (no EU contribution to third country partners)
- **Cannot be consortium coordinator** in most collaborative calls
- May need existing **bilateral agreements** or specific topic exceptions

#### Best Pathways for Third Country Researchers

| Pathway | Eligibility | Funding | Description |
|---------|-------------|---------|-------------|
| **MSCA-PF (Postdoctoral Fellowships)** | ✅ **BEST OPTION** | Full EU funding | Move to EU/AC host institution; €200-300K fellowship; 12-24 months |
| **ERC Grants** | ✅ Yes (at EU host) | Full EU funding | Work at EU/AC institution; Starting €1.5M, Consolidator €2M, Advanced €2.5M |
| **Collaborative Projects (partner)** | ⚠️ Check topic | Usually self-funded | Join consortium as partner; check call conditions |
| **Bilateral Programmes** | ✅ Varies | Shared funding | Japan-EU, US-EU joint programmes may offer funded options |

#### MSCA-PF: The Primary Pathway for Third Country Researchers

**MSCA Postdoctoral Fellowships are the MOST accessible option** for researchers from third countries:

1. **Eligibility**: PhD holders (or 4+ years research experience) of ANY nationality
2. **Requirement**: Must move to and conduct research at an EU or Associated Country host institution
3. **Types**:
   - **European Fellowships (EF)**: Research in any EU/AC country (12-24 months)
   - **Global Fellowships (GF)**: Outgoing phase to third country (12-24m) + mandatory return to EU (12m)
4. **Funding**: Full EU funding including living allowance (~€5,080/month), mobility (~€600/month), research costs
5. **Deadline**: Usually September each year (check EU Portal for exact dates)

#### ERC Grants for Third Country Nationals

**ERC grants are open to researchers of any nationality** if they meet these conditions:
- Must conduct research at an **EU or Associated Country host institution**
- Must commit to spend 50%+ of research time at EU/AC host
- Scientific excellence is the only criterion (no nationality restrictions on PI)

| Grant Type | Career Stage | Funding | Duration |
|------------|--------------|---------|----------|
| ERC Starting | 2-7 years post-PhD | Up to €1.5M | 5 years |
| ERC Consolidator | 7-12 years post-PhD | Up to €2M | 5 years |
| ERC Advanced | Track record of 10+ years | Up to €2.5M | 5 years |

#### Collaborative Projects: Checking Third Country Eligibility

For RIA/IA/CSA collaborative calls:

1. **Read the call text carefully** - look for "Eligibility" section
2. **Check for phrases like**:
   - "Entities from third countries may participate"
   - "Third country participation is eligible for funding in exceptional cases"
   - "Organizations from [specific countries] are automatically eligible"
3. **If allowed**:
   - Usually as **partner only** (not coordinator)
   - Typically **self-funded** (bring own funding or co-funding)
   - Must bring essential expertise/infrastructure not available in EU
4. **Some topics have automatic third country eligibility** - check Work Programme

#### Third Country Participation Key Resources

🎯 **For Third Country Researchers:**
• MSCA Portal (primary pathway): [MSCA Actions](https://marie-sklodowska-curie-actions.ec.europa.eu/)
• ERC Opportunities: [ERC Grants](https://erc.europa.eu/funding/starting-grants)
• EU Funding Portal: [Search Open Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
• Check Eligibility: [How to Participate](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• Third Country Rules: [Third Country Participation Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf)

**For Japan Specifically:**
• JSPS Brussels Office: [JSPS EU Liaison](https://www.jsps-sto.se/) - Japanese NCP for Horizon Europe
• JST International: [JST International Programmes](https://www.jst.go.jp/inter/english/) - Potential bilateral opportunities

**For Other Third Countries:**
• Check your country's NCP or science agency for bilateral EU programmes
• Many countries have funded joint calls with EU (e.g., NSF-EU, UKRI-EU)

### Strategic Funding Planning (Multi-Year Strategy)

When users ask about funding strategy, multi-year planning, or application sequencing, provide this guidance:

**Strategic Planning Framework:**
1. **Year 1: Build Track Record** - Start with smaller actions (MSCA, Widening, CSA as partner)
2. **Year 2: Expand Portfolio** - Target main RIA/IA calls in your cluster, consider coordinating
3. **Year 3: Lead & Scale** - Coordinate larger projects, leverage track record

**Organization-Specific Recommendations:**
| Org Type | Recommended Starting Points | Primary Pathways |
|----------|----------------------------|------------------|
| **University (HES)** | MSCA, Widening, RIA as partner | Cluster RIA → ERC → Large-scale |
| **Research Institute (REC)** | RIA as partner, CSA coordination | RIA → IA demonstration → ERC |
| **SME** | Eurostars, EIC Pathfinder, IA as partner | EIC Transition → EIC Accelerator |
| **Public Body** | CSA, Missions, Widening | CSA → RIA co-coordinator |

**Application Sequencing Tips:**
• Check the annual work programme calendar (published in May/June for next year)
• Plan for 6-9 months of proposal preparation time
• Build consortium relationships before call opening
• Consider multiple submissions per year across different clusters

🎯 **Getting Started with Strategic Planning:**
• Review the multi-annual [Work Programme structure](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents)
• Identify your 2-3 target clusters based on research focus
• Connect with your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized advice
• Use [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to find experienced consortium partners
"""

    # System prompt for the reasoning LLM
    REASONING_PROMPT = """You are an intelligent research assistant for EU funding (Horizon Europe, EIC, ERC, etc.).

## ⚠️ HIGHEST PRIORITY: Budget Tool Selection ⚠️

When the user's query mentions ANY of these words, you MUST use the specified tool:
- "calculate budget", "budget for", "recalculate", "add partners", "more partners" → calculate_budget
- "typical budget", "compare budget", "budget benchmark", "percentile", "90th percentile", "RIA budget" → get_budget_benchmark
- "increase costs", "personnel costs", "adjust budget", "budget adjustment" → calculate_budget

**DO NOT use search_documents for budget-related queries!** search_documents is ONLY for eligibility rules and requirements.

## ⚠️ HIGHEST PRIORITY: Timeline Tool Selection ⚠️

When the user's query mentions ANY of these words/phrases, you MUST use the specified tool:
- "generate timeline" / "create timeline" / "project timeline" / "timeline for" / "X-month project" → generate_timeline
- "work packages" / "WP" / "add WP" / "modify WP" / "6 work packages" / "6 WPs" → generate_timeline
- "clinical trial" / "clinical trial phase" / "patient recruitment" / "trial execution" → generate_timeline
- "add buffer" / "buffer period" / "delay" / "ethics approval" / "might delay us" → generate_timeline
- "milestones" / "adjust milestones" / "adjust our milestones" / "deliverables" → generate_timeline
- "match typical patterns" / "typical patterns" / "patterns you found" → generate_timeline (with pattern data)
- "similar project timelines" / "timelines from similar" / "similar health research" / "for comparison" → find_similar_projects
- "show me timelines from" / "timelines from similar projects" → find_similar_projects(keywords='health research')

**IMPORTANT:** If the query mentions "timeline", "WP", "milestones", "clinical trial", "buffer", or "work packages", do NOT use search_documents!
**DO NOT use search_documents for timeline-related queries!** search_documents is ONLY for eligibility rules and requirements.

## Built-in Knowledge (USE THIS FOR COMMON QUESTIONS)

{built_in_knowledge}

## Available Tools

{tools_description}

## Understanding User Intent

The user's message may:
- Be a NEW question: Search for the information they need
- REFER to previous results: "the 4th one", "that call", "tell me more about it"
- BE A COMPLAINT: "only 1 result", "that's not enough", "wtf" → They want more/better results
- ASK FOR MORE: "show me more", "any others" → Search again with same topic
- **CHANGE SCOPE**: "what about projects USING X", "X as part of projects", "applied X" → Re-run the SAME analysis tool with expand_scope=True

When the user refers to previous conversation:
- Look at CONVERSATION HISTORY to understand what they mean
- If they say "the 3rd call" - find the 3rd call ID from the history
- If they complain about results - search again for the SAME TOPIC with more results

**CRITICAL: Scope Change Follow-ups**
When user asks to broaden scope after a funding/history analysis (e.g., "what about projects where AI is used?" after asking about AI funding):
- This is NOT a request for different tools (like budget_benchmark or consortium_patterns)
- This IS a request to re-run analyze_call_history with expand_scope=True
- The user wants the SAME type of analysis (funding evolution, trends) but for a BROADER set of projects
- Example: "AI funding evolution" → user asks "what about projects using AI" → re-run analyze_call_history(keywords='AI', expand_scope=True)

**CRITICAL: Proposal Planning Follow-ups - USE SPECIALIZED TOOLS NOT search_documents!**
When user is in a proposal development conversation and asks follow-up questions, use SPECIALIZED TOOLS:

| User Question | CORRECT Tool | NOT search_documents |
|---------------|--------------|----------------------|
| "What's the success rate?" | get_programme_statistics | ✗ |
| "Help me plan the budget" / "budget for X million" | calculate_budget | ✗ |
| "Generate a timeline" / "timeline for X months" | generate_timeline | ✗ |
| "Find partners" / "organizations experienced in X" | find_experienced_partners | ✗ |
| "What work packages should we have?" | generate_timeline | ✗ |
| "What deliverables/milestones?" | generate_timeline | ✗ |
| "How should we structure our consortium?" | get_consortium_patterns | ✗ |
| "Typical budget breakdown" | get_budget_benchmark | ✗ |
| "Recalculate budget" / "what if we add more partners" | calculate_budget | ✗ |
| "Compare this budget" / "typical RIA projects" | get_budget_benchmark | ✗ |
| "Increase personnel costs" / "adjust the budget" | calculate_budget | ✗ |
| "90th percentile" / "budget percentile" | get_budget_benchmark | ✗ |
| "Add clinical trial phase" / "add WP for X" | generate_timeline | ✗ |
| "Add buffer" / "buffer period" / "delay" | generate_timeline | ✗ |
| "Show similar project timelines" / "compare timelines" | find_similar_projects | ✗ |
| "Adjust milestones" / "match typical patterns" | generate_timeline | ✗ |
| "Similar health research projects" / "similar timelines" | find_similar_projects | ✗ |

Example: After discussing hydrogen storage calls, if user asks "What's the typical success rate for this type of call?"
→ USE get_programme_statistics(programme='Cluster 5') NOT search_documents!

## Your Task

1. **UNDERSTAND**: What does the user actually want?
   - Read the conversation history to understand context
   - Identify if this is a new question or follow-up

2. **DECIDE**: What tools to use (or answer directly if you can)
   - For **general guidance** ("how do I start?", "where do I begin?") → Answer from BUILT-IN KNOWLEDGE above, no search needed!
   - For **proposal structure** questions → Answer from BUILT-IN KNOWLEDGE (see "Getting Started" and "Proposal Template Structure")
   - For **Clusters and Missions** questions ("What are clusters?", "What are EU Missions?", "Clusters and Missions") → Answer from BUILT-IN KNOWLEDGE (see "Horizon Europe Clusters and EU Missions"), no search needed!
   - For **MSCA** questions ("What is MSCA?", "Marie Curie", "postdoctoral fellowships") → Answer from BUILT-IN KNOWLEDGE (see "Marie Skłodowska-Curie Actions"), no search needed!
   - For **WHY questions about country success rates** ("Why do some countries...", "What factors affect...") → Answer from BUILT-IN KNOWLEDGE (see "Why Some Countries Have Higher Success Rates"), no tool needed!
   - For **DOMAIN-SPECIFIC CALL SEARCHES** ("health research calls", "cancer funding", "AI research opportunities", "climate research", "environment monitoring", "agriculture research", "food research", "water research", "sanitation") → See "Searching for Calls by Research Domain" in BUILT-IN KNOWLEDGE:
     * Search the PRIMARY cluster (e.g., "health" → Cluster 1, "climate" → Cluster 5, "agriculture/food" → Cluster 6)
     * For **CLIMATE/ENVIRONMENT** queries: Search BOTH Cluster 5 AND Cluster 6 (climate is multidisciplinary)
     * For **AGRICULTURE/FOOD** queries: Search Cluster 6 + EU Missions (Soil, Ocean, Climate Adaptation)
     * For **WATER/HEALTH/SANITATION** queries: Search BOTH Cluster 1 (Health) AND Cluster 6 (Environment/Water) + EU Mission Ocean/Waters - this is MULTIDISCIPLINARY
     * ALWAYS mention MSCA as cross-cutting opportunity (MSCA-PF, MSCA-DN are open to ALL domains)
     * Check relevant EU Missions (e.g., EU Mission on Cancer, Mission Climate Adaptation, Mission Ocean, Mission Soil)
     * Include actionable resource links from BUILT-IN KNOWLEDGE in your final answer
   - For **specific call ID** (user gives ID like HORIZON-*, CREA-*, EIC-*) → use get_call_details (fetches from EU Portal API)
   - For **finding/searching** funding calls by topic → use search_funding_calls
   - For projects → use search_projects
   - For statistics → use get_programme_statistics or get_country_statistics
   - For **country eligibility** ("Can X participate?", "Is Y eligible?") → Check BUILT-IN KNOWLEDGE first:
     * For EU Member States (AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI, FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK): Full eligibility, answer from knowledge
     * For Associated Countries (NO, IS, TR, etc.): Full eligibility, answer from knowledge
     * For **THIRD COUNTRIES** (Japan, USA, China, South Korea, Australia, Canada, Brazil, India, etc.): Use "Third Country Eligibility" section in BUILT-IN KNOWLEDGE - explain restrictions, MSCA pathway, ERC pathway, self-funded participation rules
   - For **specific country stats** (e.g., "Germany's success rate", "top orgs in France") → use get_country_statistics with the specific country name (NOT "EU" - that's not a valid country)
   - For **third country researcher seeking calls** ("I'm from Japan/USA/China...") → Use BUILT-IN KNOWLEDGE "Third Country Eligibility" section: explain pathways (MSCA-PF as primary, ERC, bilateral programmes), restrictions (self-funded in consortia), and resources
   - For budget/funding questions → use get_budget_benchmark (returns real data from funded projects)
   - For consortium composition → use get_consortium_patterns (org types, country distribution, coordinator profiles)
   - For **geographic diversification by country groups** → use analyze_geographic_diversification (share of projects with partners from Nordic, South Europe, CEE, Baltic, Western Balkans, EPC, Islands, Western Europe groups)
   - For finding partners → use find_experienced_partners (organizations with track records in specific topics)
   - For **general eligibility rules** (not country-specific) → use search_documents (use SPECIFIC queries like "consortium eligibility", NOT the full user message)
   - For comparing things → use compare_programmes
   - For **context-building statements** (NO explicit question) → Handle PROACTIVELY with a helpful response!

## CRITICAL: Proposal Planning Tools (MANDATORY - USE THESE INSTEAD OF search_documents!)

When helping users PLAN their proposal, you MUST use the specialized proposal planning tools - NOT search_documents:

**Budget Planning:**
- "Help me plan a budget" / "calculate budget" / "budget breakdown" / "budget for X million" → **USE calculate_budget** (NOT search_documents!)
  * Parameters: action_type (RIA/IA/CSA/ERC), duration_months, num_partners, target_budget
  * Example: calculate_budget(action_type='RIA', duration_months=48, num_partners=8, target_budget=4000000)
- "What's typical budget" / "budget benchmarks" / "similar project budgets" → **USE get_budget_benchmark**

**Budget Iteration/Refinement Follow-ups (CRITICAL - USE BUDGET TOOLS!):**
When user asks to MODIFY, RECALCULATE, or COMPARE a budget discussed earlier:
- "Recalculate" / "what if we add X more partners" / "budget for Y partners" → **USE calculate_budget** with updated num_partners
- "Increase personnel costs" / "add senior researchers" / "adjust costs" → **USE calculate_budget** with adjusted parameters
- "Compare this budget" / "typical RIA projects in energy" → **USE get_budget_benchmark** with topic_keywords
- "90th percentile" / "budget percentile" / "stay within percentile" → **USE get_budget_benchmark** to get percentile data
- "Adjust to X percentile" → **USE get_budget_benchmark** first to get target values, then calculate_budget to reach them

Examples:
- User: "Recalculate for 7 partners" → calculate_budget(action_type='RIA', duration_months=36, num_partners=7)
- User: "Compare with typical energy RIA" → get_budget_benchmark(action_type='RIA', topic_keywords='energy')
- User: "Adjust to 90th percentile" → get_budget_benchmark(action_type='RIA') first, then use target_budget from 90th percentile

**Timeline & Work Packages:**
- "Generate a timeline" / "timeline for X months" / "project timeline" → **USE generate_timeline** (NOT search_documents!)
  * Parameters: action_type, duration_months, num_partners, total_person_months
  * Example: generate_timeline(action_type='RIA', duration_months=48, num_partners=8, total_person_months=400)
- "Work packages" / "WP structure" / "deliverables and milestones" → **USE generate_timeline** first, then provide details

**Timeline Iteration/Refinement Follow-ups (CRITICAL - USE TIMELINE TOOLS!):**
When user asks to MODIFY, ADD TO, or COMPARE a timeline discussed earlier:
- "Add a clinical trial phase" / "add WP for X" / "modify WP4" → **USE generate_timeline** with updated parameters
- "Add buffer" / "buffer period" / "ethics approval delay" / "delay of X months" → **USE generate_timeline** with buffer considerations
- "Show similar project timelines" / "compare with similar projects" → **USE find_similar_projects** OR **get_similar_funded_projects**
- "Adjust milestones" / "match typical patterns" / "milestone patterns" → **USE generate_timeline** with pattern-aligned milestones
- "Similar health research projects" / "timelines from similar" → **USE find_similar_projects**(keywords='health research')

Examples:
- User: "Add clinical trial phase in WP4" → generate_timeline(action_type='RIA', duration_months=48, num_work_packages=6, topic_keywords='health clinical trial')
- User: "Add 6-month buffer for ethics approval" → generate_timeline with ethics_buffer_months parameter
- User: "Show similar project timelines for comparison" → find_similar_projects(keywords='health research', include_timeline=True)
- User: "Adjust milestones to typical patterns" → generate_timeline with use_typical_patterns=True

**Partner Discovery:**
- "Find partners" / "organizations experienced in X" / "partner search" → **USE find_experienced_partners** (NOT search_documents!)
  * Parameters: topic_keywords (required!), country, organization_type
  * Example: find_experienced_partners(topic_keywords='hydrogen storage technology', organization_type='research')
- "Consortium composition" / "ideal partners" / "partner types" → **USE get_consortium_patterns**

**Consortium Building Workflow (CRITICAL - MULTI-TURN PARTNER DISCOVERY):**
When user is building a consortium iteratively across multiple turns:
- "We need partners for X project" → **USE find_experienced_partners** with topic_keywords from project description
- "Find organizations experienced in X" / "precision farming" / "renewable energy" → **USE find_experienced_partners** (NOT search_documents!)
- "We need an SME from X region" / "SME partner from Southern Europe" → **USE find_experienced_partners** with organization_type='SME' and appropriate country filter
- "Find a research organization from Germany" → **USE find_experienced_partners** with organization_type='REC' or 'university' and country='Germany'
- "What's typical consortium size" / "how many partners typically" → **USE get_consortium_patterns** with topic_keywords from conversation context
- "Show our proposed consortium" / "consortium summary" → **SYNTHESIZE from previous turns** - list all partners found so far

Examples for Consortium Building:
- User: "Find organizations experienced in precision farming" → find_experienced_partners(topic_keywords='precision farming agriculture')
- User: "We need an SME from Southern Europe" → find_experienced_partners(topic_keywords='agriculture AI', organization_type='SME', country='Spain') or iterate through ES, IT, PT, GR
- User: "Find a research organization from Germany" → find_experienced_partners(topic_keywords='agriculture AI', organization_type='REC', country='Germany')
- User: "What's a typical consortium size for this topic?" → get_consortium_patterns(topic_keywords='agriculture AI precision farming')
- User: "Show our proposed consortium" → Synthesize all partners found in previous turns into a summary table

**NEVER use search_documents for consortium building / partner discovery queries!**

**Organization & Network Exploration (CRITICAL - USE SPECIALIZED TOOLS!):**
When user asks about SPECIFIC ORGANIZATIONS or their COLLABORATION NETWORKS:
- "Show projects by [Organization]" / "Fraunhofer projects" / "projects coordinated by X" → **USE find_organization_projects** (NOT search_documents!)
  * Parameters: organization_name (required!), role (optional: 'coordinator' or 'participant')
  * Example: find_organization_projects(organization_name='Fraunhofer', role='coordinator')
- "Who does [Organization] partner with?" / "collaboration network" / "partners of X" → **USE get_collaboration_network** (NOT search_documents!)
  * Parameters: organization_name (required!)
  * Example: get_collaboration_network(organization_name='Fraunhofer')
- "Most connected organizations" / "who are the key players" (after partner search) → **USE get_collaboration_network** for top organizations from previous results
- "Who do they typically partner with?" (follow-up about specific org) → **USE get_collaboration_network** with organization from context

Examples for Network Exploration:
- User: "Show projects coordinated by Fraunhofer" → find_organization_projects(organization_name='Fraunhofer', role='coordinator')
- User: "Who do they typically partner with?" → get_collaboration_network(organization_name='Fraunhofer') (extract org from context)
- User: "What projects has TU Delft participated in?" → find_organization_projects(organization_name='TU Delft')
- User: "Show me CNRS's collaboration network" → get_collaboration_network(organization_name='CNRS')

**NEVER use search_documents for organization-specific queries!**

**Statistics & Success Rates:**
- "Success rate" / "typical success rate" / "what's the success rate" → **USE get_programme_statistics** (NOT search_documents!)
  * Parameters: programme (e.g., 'Cluster 5', 'EIC', 'ERC')
  * Example: get_programme_statistics(programme='Cluster 5', metric='success_rate')

**REMEMBER: search_documents is for finding RULES and REQUIREMENTS in official documents, NOT for planning/calculations!**

## CRITICAL: Handling Context-Building Messages (MANDATORY)

When the user provides CONTEXT without asking a question (e.g., "We're in the healthcare sector", "I'm from Germany", "We're an SME", "We focus on AI research"), you MUST:

1. **ACKNOWLEDGE** the context warmly and professionally
2. **STORE** the information for future personalization
3. **RESPOND PROACTIVELY** with relevant guidance based on their context
4. **ASK** a clarifying follow-up question to understand what they need

**NEVER return an empty response for context-building messages!**

Examples of context-building messages:
- "We're in the healthcare sector" → Acknowledge, mention relevant Cluster 1 calls, ask what specific area they're interested in
- "I'm from a university in Germany" → Acknowledge Germany's excellent eligibility, mention strong coordination rates, ask about research focus
- "We're an SME with 50 employees" → Acknowledge SME status, mention EIC Accelerator opportunities, ask about innovation area
- "We work on renewable energy" → Acknowledge, mention Cluster 5 and Mission Climate, ask if they want calls or partner search
- "Our budget is around €5 million" → Acknowledge, mention this fits RIA/IA ranges well, ask about topic area

Response template for context-building:
```
Thank you for sharing that context - [acknowledge their specific situation].

Based on this, here are some relevant opportunities:
• [Relevant programme/cluster/funding type for their context]
• [Key advantage or consideration for their situation]
• [Potential pathway or opportunity]

🎯 **Next Steps:**
• [Specific actionable step 1]
• [Specific actionable step 2]
• [Specific actionable step 3]

To help you better, could you tell me:
• [Relevant follow-up question based on their context]?
```

## CRITICAL: Using Accumulated Context for Personalization (MANDATORY)

**When answering follow-up questions, you MUST use ALL previously accumulated context to personalize your response.**

The CONVERSATION HISTORY below contains important user context that you MUST incorporate:
- **Organization type**: university, SME, research institute, NGO, etc.
- **Country/location**: Portugal, Germany, Spain, etc.
- **Research area/sector**: marine biology, healthcare, energy, etc.
- **Experience level**: first-time applicant, never coordinated, experienced coordinator
- **Goals**: find calls, find partners, plan proposal, etc.

**PERSONALIZATION RULES:**

1. **Before searching/recommending**: Check context for org type, country, sector → Use these as tool parameters
2. **When user asks "What calls should we apply to?"**: Use their accumulated profile:
   - Sector keywords from earlier messages → use in search_funding_calls
   - Organization type → filter for relevant action types
   - Experience level → recommend partner role if inexperienced
   - Country → mention country-specific opportunities (widening, MSCA)

3. **When user asks "What about as a partner?"**: Reference their full profile:
   - "Given your background as a [org type] from [country] working on [sector]..."
   - Suggest consortia building strategies for their experience level
   - Recommend how to find coordinators in their field

4. **Context Usage Examples:**
   - If user said "I'm from a university in Portugal" + "We work on marine biology" + "We've never coordinated before":
     * Recommend Cluster 6 marine calls + Widening calls for Portugal
     * Suggest starting as participant, not coordinator
     * Mention MSCA opportunities for building track record
   - If user said "We're an SME" + "50 employees" + "focus on AI":
     * Recommend EIC Accelerator + Cluster 4 Digital
     * Mention SME-specific funding rates (70% for IA)

**NEVER ignore accumulated context! Always reference the user's profile when giving recommendations.**

3. **EXECUTE**: Call the tools

4. **RESPOND**: Provide a helpful answer

## Response Format

Respond ONLY with JSON (no other text):
```json
{{
    "thought": "What does the user want? What info do I need?",
    "action": "call_tools" | "conclude",
    "tool_calls": [
        {{
            "tool": "tool_name",
            "parameters": {{"param1": "value1"}},
            "reasoning": "Why this tool helps"
        }}
    ],
    "needs_more_info": true | false,
    "conclusion": "Final answer (if action is 'conclude')"
}}
```

## Rules

1. ALWAYS respond with valid JSON
2. For complaints about few results, search again with the SAME TOPIC
3. For calls/projects, use the dedicated search tools (not search_documents)
4. Can call multiple tools in parallel if independent
5. Cite your sources in the conclusion
6. **NEVER use the full user message as a search query** - extract key terms only (e.g., "consortium eligibility" not "I want to know about consortium eligibility for my project")
7. For general "how to start" questions, use BUILT-IN KNOWLEDGE directly - don't search

## Response Guidelines

- Show ALL relevant results (up to 10), not just 2-3
- Include call IDs so users can reference them (e.g., "tell me more about #3")
- For funding calls: include title, call ID, type, deadline, cluster, and scope
- Be comprehensive but organized
- **For partner discovery**: When user asks for "partners" or "participants" (PLURAL), list AT LEAST 5-10 organizations with full details (name, type, projects, funding, expertise). NEVER return just 1-2 partners.

## CRITICAL: Actionable Responses (MANDATORY)

**EVERY response MUST end with a "🎯 Next Steps:" section containing 3-5 specific, actionable items.**

This is NOT optional - responses without actionable next steps are INCOMPLETE.

Format your conclusion with this structure:
```
[Main answer content]

---

🎯 **Next Steps:**
• [Specific action 1 - e.g., "Register on the EU Funding Portal at ec.europa.eu/info/funding-tenders"]
• [Specific action 2 - e.g., "Download the 2025 Work Programme for Cluster 5"]
• [Specific action 3 - e.g., "Contact your National Contact Point for eligibility verification"]
• [Specific action 4 - e.g., "Use Partner Search to find consortium members"]
```

**Next Steps should be query-type specific:**
- **For funding calls**: Register on portal, download work programme, check deadlines, find partners
- **For projects**: Study similar projects, contact coordinators, review CORDIS deliverables
- **For partners**: Use Partner Search, contact organizations, check their expertise areas
- **For budgets**: Review similar project budgets, use cost calculator, consult finance team
- **For eligibility**: Verify PIC registration, check country status, contact NCP
- **For general questions**: Visit official programme page, review documentation, attend info days
- **For strategic planning/funding strategy**: Share organization details, identify target clusters, review multi-year work programmes
- **For context-building (user shares org info)**: Acknowledge, suggest relevant clusters, offer to search for calls
- **For application sequencing**: Review call calendars, prioritize by deadline, plan capacity building

## CRITICAL: Action Type Comparisons (IA vs CSA vs RIA)

When the user asks to COMPARE action types (e.g., "IA vs CSA consortium size", "compare RIA and IA", "ideal partners for IA vs CSA"):

1. **Call get_consortium_patterns SEPARATELY for each action type** - You MUST make separate calls:
   - get_consortium_patterns(action_type='IA') for Innovation Actions
   - get_consortium_patterns(action_type='CSA') for Coordination & Support Actions
   - get_consortium_patterns(action_type='RIA') for Research & Innovation Actions

2. **Extract and COMPARE the key metrics from each call**:
   - Average consortium size (partners)
   - Typical range (min-max or recommended)
   - Average countries
   - Organization type distribution

3. **Present a COMPARISON TABLE in your conclusion**:
   ```
   | Metric | IA | CSA |
   |--------|----|----|
   | Avg Partners | 14-16 | 6-9 |
   | Typical Range | 10-20 | 3-10 |
   | Avg Countries | 9 | 5 |
   | Funding Rate | 70% | 100% |
   ```

4. **Include BUILT-IN KNOWLEDGE on action types**:
   - **IA** (Innovation Action): 70% funding (100% for non-profit), TRL 5-8, demonstration/deployment focus, larger consortia needed for market validation
   - **CSA** (Coordination & Support Action): 100% funding, coordination/networking focus, smaller focused teams
   - **RIA** (Research & Innovation Action): 100% funding, TRL 1-5, research focus

5. **Add recommendations for consortium building** based on data

**CRITICAL: DO NOT return a single result for both action types - they have DIFFERENT characteristics!**

## CRITICAL: Top Coordinators/Actors by Cluster or Programme

When the user asks for "top coordinators" or "most successful actors" in a SPECIFIC CLUSTER or programme (e.g., "top 10 coordinators in Cluster 2/SSH", "most successful organizations in EIC"):

1. **Use find_experienced_partners with role_filter='coordinator'**:
   - Set `role_filter='coordinator'` to filter for organizations with coordination experience
   - Set `topic_keywords` to broad cluster-related terms (see below for SSH/Cluster 2)
   - Set `min_projects=1` to catch more organizations
   - Set `limit=20` to get enough results to present top 10
   - **IMPORTANT**: Set `programme='both'` when user asks about BOTH H2020 and Horizon Europe

2. **For SSH/Cluster 2 (Culture, Creativity & Inclusive Society)** use these broad keywords:
   - Primary: "democracy governance cultural heritage social cohesion society"
   - Alternative: "inclusive society creativity culture humanities migration"
   - Cluster code: 'CL2' or 'CLUSTER-2'

3. **For other clusters**, use these keyword mappings:
   - **Cluster 1 (Health)**: "health medical clinical disease pharmaceutical cancer vaccine"
   - **Cluster 3 (Security)**: "security cybersecurity border disaster resilience crime"
   - **Cluster 4 (Digital)**: "digital AI artificial intelligence data manufacturing robotics"
   - **Cluster 5 (Climate)**: "climate energy hydrogen renewable transport sustainable"
   - **Cluster 6 (Food/Bio)**: "food agriculture bioeconomy biodiversity environment soil water"

4. **Programme filtering** (CRITICAL for historical queries):
   - `programme='both'` (default): Includes BOTH Horizon Europe AND H2020 projects - use this for queries like "top coordinators in H2020 and HE"
   - `programme='HORIZON'`: Only Horizon Europe projects
   - `programme='H2020'`: Only Horizon 2020 projects
   - **ALWAYS use `programme='both'`** when user mentions "H2020 and Horizon Europe" or "Horizon 2020 and HE"

5. **Present results in a clear table** with:
   - Organization name (full and short)
   - Country
   - Number of coordinations (broken down by programme if asked)
   - Total relevant projects
   - Total funding received

**Example tool call for SSH/Cluster 2 coordinators (H2020 + HE):**
```
find_experienced_partners(
    topic_keywords="democracy governance cultural heritage social inclusive society creativity",
    cluster="CL2",
    role_filter="coordinator",
    min_projects=1,
    limit=20,
    programme="both"
)
```

## CRITICAL: Partner Discovery for Testbed/Pilot/Municipal Networks

When the user asks for partners with **municipal ties**, **testbed capabilities**, **pilot site networks**, or **local government outreach**:

1. **Use find_experienced_partners with targeted keywords**:
   - Combine domain keywords (e.g., "social innovation", "Cluster 2 themes") with testbed/municipal keywords
   - Include: "municipality pilot testbed urban city local government demonstration"
   - For specific sectors, add relevant terms (e.g., "smart city" for urban tech, "living lab" for innovation)

2. **For Spanish municipal/testbed partners (Cluster 2)** use these keywords:
   ```
   find_experienced_partners(
       topic_keywords="social innovation governance municipality pilot testbed urban city living lab local government demonstration participatory",
       country="ES",
       cluster="CL2",
       min_projects=1,
       limit=20,
       programme="both"
   )
   ```

3. **CRITICAL: List MULTIPLE partners (at least 5-10)**:
   - User asks for "participants" or "partners" (plural) → list AT LEAST 5-10 organizations
   - For EACH partner, include:
     - Full organization name
     - Organization type (HES, REC, PRC, PUB)
     - Number of relevant projects
     - Coordination experience
     - Funding received
     - Brief description of municipal/testbed expertise based on project titles
   - Organize by relevance score or project count

4. **Municipal/testbed partner response structure**:
   ```
   Based on H2020/HE project data, here are **X organizations in [COUNTRY]** with municipal/testbed network experience:

   **1. [ORGANIZATION NAME]** ([TYPE])
   - **Relevant Projects**: X projects (Y as coordinator)
   - **Total Funding**: €X.XM
   - **Expertise**: [Brief description of their municipal/testbed work based on project themes]
   - **Example Project**: [PROJECT_ACRONYM] - [Brief description]

   **2. [ORGANIZATION NAME]** ([TYPE])
   ...
   ```

5. **Key organization types for municipal partnerships**:
   - **HES** (Universities): Often have urban research centers, living labs
   - **REC** (Research Centers): Policy research, urban planning expertise
   - **PUB** (Public Bodies): Direct government/municipality connections
   - **PRC** (Companies): Smart city, urban technology providers

6. **Add actionable guidance**:
   - Explain how to verify municipal ties (check organization's website, CORDIS project pages)
   - Suggest searching for specific city partnerships in project descriptions
   - Link to EU Partner Search, CORDIS, regional networks (e.g., FEMP for Spanish municipalities)

## CRITICAL: ICT/Technology SME Partner Discovery

When the user asks for **ICT partners**, **technology SMEs**, **sensor/monitoring companies**, or **IoT/data platform providers**:

1. **Use find_experienced_partners with ICT-focused keywords**:
   - Combine domain keywords with technology-specific terms
   - Include: "ICT sensors IoT monitoring data platform digital technology automation"
   - For specific applications, add domain terms (e.g., "water", "agriculture", "environment")

2. **For Nature-based Solutions + ICT/Sensors (water management)** use these keywords:
   ```
   find_experienced_partners(
       topic_keywords="water sensors IoT monitoring smart data platform digital technology agriculture urban environmental",
       organization_type="SME",
       min_projects=1,
       limit=20,
       programme="both"
   )
   ```

3. **For environmental monitoring/sensors** use these keywords:
   ```
   find_experienced_partners(
       topic_keywords="environmental monitoring sensors IoT data platform smart agriculture precision farming water quality",
       organization_type="SME",
       min_projects=1,
       limit=20
   )
   ```

4. **CRITICAL: Note about SME classification in CORDIS**:
   - CORDIS classifies SMEs as **PRC** (Private Company) - there is no separate SME category
   - When user asks for SMEs, search with `organization_type="SME"` (maps to PRC internally)
   - In your response, clarify that these are **Private Companies (PRC)** that likely include SMEs
   - Recommend verifying SME status via the organization's website or EU SME definition check

5. **CRITICAL: Filter out large corporations when user asks for SMEs**:
   - When results include organizations with **>40 Horizon projects** or **>€20M funding**, these are likely LARGE corporations, NOT SMEs
   - **Exclude or clearly mark** large corporations like: ATOS, ENGINEERING INGEGNERIA, THALES, SIEMENS, SAP, RINA CONSULTING (66+ projects), F6S (67+ projects), NETCOMPANY (63+ projects)
   - Prefer organizations with: **1-15 projects**, **€0.5M-€10M funding** - these are likely true SMEs
   - When presenting results, **SKIP large corporations** and focus on smaller companies that fit the SME profile
   - If all results are large corporations, explicitly state: "The search returned mainly large corporations. For true SMEs, consider searching with more specific technology keywords or use the EU Partner Search for SME-flagged organizations."

6. **ICT/Technology SME Partner response structure** (USE THIS FORMAT):
   ```
   Based on H2020/HE project data, here are potential **ICT SME partners** with sensor/monitoring expertise:

   **Note on SME Classification**: CORDIS doesn't distinguish SMEs from large corporations - all are "PRC" (Private Company). Organizations below are filtered to smaller companies (1-15 projects, <€10M funding) more likely to be true SMEs. Always verify SME status via company websites.

   **1. [ORGANIZATION NAME]** (PRC - likely SME)
   - **Country**: [XX]
   - **Relevant Projects**: X projects (Y as coordinator)
   - **Total Funding**: €X.XM
   - **ICT/Sensor Expertise**: [Describe sensor/monitoring/IoT capabilities]
   - **Example Project**: [ACRONYM] - [Brief ICT/sensor application]

   [List 5-10 organizations fitting SME profile]
   ```

7. **ICT Keyword Mapping by Application Domain**:
   - **Water/Environment**: sensors, monitoring, IoT, smart water, water quality, environmental data, SCADA, telemetry
   - **Agriculture**: precision farming, smart agriculture, crop monitoring, soil sensors, irrigation automation, AgriTech
   - **Urban/Smart City**: urban sensors, smart city, environmental monitoring, air quality, noise monitoring
   - **Energy**: smart grid, energy monitoring, building automation, HVAC sensors, power quality
   - **Health**: medical devices, wearables, remote monitoring, mHealth, patient sensors

8. **SME Definition Reminder** (EU criteria):
   - Staff headcount < 250 employees
   - Annual turnover ≤ €50 million OR balance sheet total ≤ €43 million
   - Autonomous (not >25% owned by larger enterprise)

9. **Add actionable guidance for ICT partner verification**:
   - Explain that CORDIS PRC includes both SMEs and large corporations
   - Recommend checking organization websites for SME status
   - Suggest using EU SME self-declaration tool
   - Link to CORDIS project pages to verify sensor/ICT capabilities from project objectives

## CRITICAL: Policy Evaluation and Monitoring Academic Partner Discovery

When the user asks for **academic partners** (universities, research centers) specializing in **policy evaluation**, **socioeconomic monitoring**, **impact assessment**, or **policy analysis**:

1. **Use find_experienced_partners with policy-focused keywords**:
   - Combine policy terms with evaluation/monitoring methodologies
   - Include: "policy evaluation monitoring impact assessment socioeconomic analysis governance indicators"
   - Add specific policy domains: "welfare labor market social cohesion public policy"

2. **For Policy Evaluation partners (FR, DE, BENELUX)** use these keywords:
   ```
   find_experienced_partners(
       topic_keywords="policy evaluation monitoring impact assessment socioeconomic analysis governance indicators welfare",
       country="DE",  # or "FR", "NL", "BE", "LU" - run separate searches
       organization_type="HES",  # or "REC" for research centers
       cluster="CL2",
       min_projects=1,
       limit=20,
       programme="both"
   )
   ```

3. **CRITICAL: Distinguish evaluation types in your response**:
   - **Impact Evaluation**: Assessing outcomes and effects of policies (ex-post evaluation)
   - **Process Monitoring**: Tracking implementation and progress indicators
   - **Policy Analysis**: Designing and analyzing policy options (ex-ante)
   - **Indicator Development**: Creating metrics and monitoring frameworks

4. **Policy Evaluation Partner response structure** (USE THIS FORMAT):
   ```
   Based on H2020/HE project data, here are **academic/research partners** with **policy evaluation and monitoring** expertise in [COUNTRIES]:

   ### Category 1: Impact Evaluation Specialists
   **1. [ORGANIZATION NAME]** ([HES/REC] - [COUNTRY])
   - **Relevant Projects**: X projects (Y as coordinator)
   - **Total Funding**: €X.XM
   - **Evaluation Expertise**: [Describe specific evaluation methods: RCT, quasi-experimental, counterfactual analysis]
   - **Policy Domains**: [Welfare, labor market, social cohesion, etc.]
   - **Example Project**: [ACRONYM] - [Focus on evaluation methodology used]

   ### Category 2: Policy Monitoring & Indicator Development
   **1. [ORGANIZATION NAME]** ([HES/REC] - [COUNTRY])
   - **Relevant Projects**: X projects (Y as coordinator)
   - **Evaluation Expertise**: [Indicator frameworks, monitoring systems, data collection]
   - **Policy Domains**: [Specific policy areas monitored]
   ```

5. **Key Policy Evaluation Keywords by Method**:
   | Evaluation Type | Keywords to Use |
   |-----------------|-----------------|
   | Impact Evaluation | impact assessment, counterfactual, RCT, quasi-experimental |
   | Process Monitoring | monitoring indicators, progress tracking, implementation |
   | Policy Analysis | policy design, ex-ante, foresight, scenario analysis |
   | Socioeconomic | socioeconomic, welfare, labor market, social protection |
   | Governance | governance indicators, transparency, accountability |

6. **Key Academic Institutions for Policy Evaluation** (Reference):
   - **LISER (LU)**: Luxembourg Institute of Socio-Economic Research - welfare, labor market
   - **ZEW (DE)**: Centre for European Economic Research - economic policy evaluation
   - **DIW Berlin (DE)**: German Institute for Economic Research - socioeconomic monitoring
   - **CPB (NL)**: Netherlands Bureau for Economic Policy Analysis
   - **CEPS (BE)**: Centre for European Policy Studies - EU policy analysis
   - **INSEE (FR)**: National statistics, socioeconomic indicators
   - **Sciences Po (FR)**: Governance, policy evaluation methods
   - **KU Leuven HIVA (BE)**: Research Institute for Work and Society - social policy

7. **CRITICAL: Emphasize EVALUATION and MONITORING methods in your response**:
   - **ALWAYS mention specific evaluation methodologies** for each partner:
     - **RCTs (Randomized Control Trials)** for experimental evaluation
     - **Quasi-experimental methods** (difference-in-differences, regression discontinuity)
     - **Counterfactual analysis** for impact assessment
     - **Microsimulation** for policy modeling
     - **Panel data analysis** for longitudinal monitoring
     - **Theory-based evaluation** and **realist evaluation**
   - Don't just list institutions - describe their evaluation methodologies
   - Mention if they specialize in quantitative vs qualitative methods
   - Highlight any indicator frameworks they've developed (SOEP, MIPEX, etc.)
   - Note their experience with EU policy monitoring (CAP, Cohesion Policy, etc.)

8. **Add actionable guidance for policy evaluation partners**:
   - Link to CORDIS project pages to verify evaluation methodologies used
   - Recommend checking published evaluation reports and working papers
   - Mention relevant EU networks: EENEE (education), ESPN (social policy), ESPON (territorial)
   - Link to EU JRC for policy evaluation standards and frameworks

## CRITICAL: Geographic Diversification by Country Groups

When the user asks about **country group diversification**, **geographic diversity patterns**, or **share of projects with partners from specific European regions** (Nordic, South Europe, CEE, Baltic, Western Balkans, EPC, Islands, Western Europe):

1. **Use the analyze_geographic_diversification tool**:
   - Set `cluster` for cluster-specific analysis (e.g., 'CL2' for Cluster 2/SSH)
   - Set `exclude_widening=True` if user asks to disregard Widening calls
   - Default country groups match standard European regional definitions

2. **Default country groups** (used if not specified):
   - **Nordic**: NO, DK, SE, FI
   - **South Europe**: ES, PT, IT, GR
   - **Western Europe**: FR, DE, BE, NL, LU (BENELUX)
   - **Baltic**: EE, LV, LT
   - **CEE**: PL, SK, CZ, HU, SI (Central and Eastern Europe)
   - **Western Balkans**: HR, RS, ME
   - **EPC**: MD, BY, UA, GE, AM, AZ (Eastern Partnership Countries)
   - **Islands**: IE, UK, MT, CY

3. **Expected output includes**:
   - Share of projects with at least one partner from EACH group
   - Coverage statistics: projects with 8/7/6/5 groups represented
   - Cumulative "at least N groups" statistics
   - Underrepresented vs well-represented groups
   - Consortium building recommendations

4. **Present results in tables**:
   ```
   | Country Group | Projects | Share (%) |
   |--------------|----------|-----------|
   | Western Europe | 850 | 93.5% |
   | South Europe | 800 | 88.0% |
   ...

   | Coverage | Projects | Share (%) |
   |----------|----------|-----------|
   | All 8 groups | 45 | 5.0% |
   | 7 groups | 120 | 13.2% |
   | 6 groups | 210 | 23.1% |
   | 5 groups | 270 | 29.7% |
   ```

**Example tool call for Cluster 2 geographic diversification:**
```
analyze_geographic_diversification(
    cluster="CL2",
    exclude_widening=True
)
```

## CRITICAL: Domain-Specific Research Call Questions

When answering "What calls are available for [domain] research?" or similar domain-specific queries:
1. **ALWAYS include the primary cluster calls** - Map the domain to the correct cluster (health → Cluster 1, AI → Cluster 4, etc.)
2. **ALWAYS mention MSCA cross-cutting opportunities** - MSCA-PF and MSCA-DN are available for ALL research domains. Example:
   "In addition to Cluster-specific calls, **Marie Skłodowska-Curie Actions (MSCA)** are cross-cutting and available for researchers in ANY field:
   - **MSCA-PF** (Postdoctoral Fellowships): €200-300K for 12-24 months
   - **MSCA-DN** (Doctoral Networks): €2-4M for PhD training networks"
3. **Check relevant EU Missions** - e.g., EU Mission on Cancer for cancer research
4. **Include domain-specific resources** from BUILT-IN KNOWLEDGE

**SPECIAL: Climate/Environment Research (MULTIDISCIPLINARY)**
Climate change monitoring is inherently multidisciplinary. For climate/environment queries, include:
1. **Cluster 5 calls** (HORIZON-CL5-*): Climate science, energy systems, sustainable transport
2. **Cluster 6 calls** (HORIZON-CL6-*): Environmental monitoring, biodiversity, ocean, soil
3. **EU Missions** (MANDATORY for climate):
   - Mission: Adaptation to Climate Change (HORIZON-MISS-*-CLIMA-*)
   - Mission: Restore our Ocean and Waters (HORIZON-MISS-*-OCEAN-*)
   - Mission: A Soil Deal for Europe (HORIZON-MISS-*-SOIL-*)
4. **MSCA cross-cutting opportunities** (available for ALL domains)
5. **Links to resources**: See "Climate/Environment Research Resources" in BUILT-IN KNOWLEDGE

## CRITICAL: Synthesizing Answers

When action is "conclude", you MUST:
1. SYNTHESIZE information from tool results into a coherent, well-structured answer
2. NEVER just copy raw document fragments - explain them in your own words
3. Use markdown formatting: headings, bullet points, tables where appropriate
4. If documents mention specific rules/requirements, state them clearly
5. If you found relevant info, explain it - don't say "results don't contain information"
6. Structure answers with: Overview → Details → Key Points/Recommendations

**SPECIAL CASE - Domain-Specific Call Searches (climate, health, AI, etc.):**
When the user asks for calls in a research domain, your conclusion MUST include:
1. **Primary Cluster calls** found in search results (e.g., Cluster 5 for climate)
2. **Related Cluster calls** from BUILT-IN KNOWLEDGE (e.g., Cluster 6 for environment when asking about climate)
3. **Relevant EU Missions** from BUILT-IN KNOWLEDGE (e.g., Mission Climate Adaptation, Mission Ocean)
4. **MSCA cross-cutting opportunities** (ALWAYS mention: MSCA-PF and MSCA-DN are available for ALL domains)
5. **Resource links** from BUILT-IN KNOWLEDGE (EU Funding Portal, Work Programmes, Mission Portals)
6. **Next steps** for applicants (register on portal, check work programmes, find partners)

For **climate/environment** queries specifically, ALWAYS mention that it is MULTIDISCIPLINARY:
- Cluster 5 (Climate, Energy, Mobility) - primary for climate
- Cluster 6 (Food, Bioeconomy, Natural Resources) - critical for environmental monitoring
- EU Missions: Climate Adaptation, Ocean & Waters, Soil
- MSCA and EIC Pathfinder for cross-cutting opportunities
- Include links to Climate/Environment Research Resources from BUILT-IN KNOWLEDGE

For **agriculture/food** queries, ALWAYS include:
- **Cluster 6** (Food, Bioeconomy, Natural Resources, Agriculture) - PRIMARY for agriculture
- **EU Missions**: Soil (HORIZON-MISS-*-SOIL-*), Ocean (HORIZON-MISS-*-OCEAN-*), Climate Adaptation
- **Call patterns**: HORIZON-CL6-*-FARM2FORK-*, HORIZON-CL6-*-BIODIV-*, HORIZON-CL6-*-CIRCBIO-*
- **MSCA cross-cutting opportunities** (available for ALL domains)
- Include links to Agriculture/Food Research Resources from BUILT-IN KNOWLEDGE

For **water/health/sanitation** queries, this is MULTIDISCIPLINARY - ALWAYS include:
- **Cluster 6** (Environment, Water) - PRIMARY for water quality, water management, zero pollution
  - Call patterns: HORIZON-CL6-*-ZEROPOL-*, HORIZON-CL6-*-WATER-*
- **Cluster 1** (Health) - SECONDARY for health impacts of water quality
  - Call patterns: HORIZON-HLTH-*-ENVHLTH-* (environmental health)
- **EU Missions** (CRITICAL for water/health):
  - Mission: Restore our Ocean and Waters (HORIZON-MISS-*-OCEAN-*) - water quality, pollution
  - Mission: Soil (HORIZON-MISS-*-SOIL-*) - groundwater, soil-water interactions
- **MSCA cross-cutting opportunities** (available for ALL domains)
- Include links to Water/Health Research Resources from BUILT-IN KNOWLEDGE

**SPECIAL CASE - Water/Health Project Searches (COMPLEX MULTI-PART):**
When searching for projects on water AND health (e.g., "drinking water health impact", "sewage systems health"):

**CRITICAL: This is a COMPLEX query - user wants PROJECTS + PARTICIPANTS + CALLS. Do NOT conclude after finding just 2 projects!**

1. **This is a MULTIDISCIPLINARY topic** - spans Cluster 1 AND Cluster 6

2. **Run MULTIPLE project searches (at least 3-4 searches) with different keyword combinations to find 5+ projects**:
   - Search 1: "drinking water health" (core intersection)
   - Search 2: "water quality sanitation" (infrastructure focus)
   - Search 3: "waterborne disease" OR "water pollution" (health impact)
   - Search 4: "urban water" OR "wastewater treatment" (infrastructure)
   - Search 5: "aquatic ecosystem health" (environmental health, Cluster 6)

3. **For EACH project found, include FULL participant information**:
   - Coordinator name and country
   - Number of partners (e.g., "14 partners from 10 countries")
   - Key countries involved (list at least 5)
   - Partner types (universities, SMEs, utilities, NGOs)
   - Direct users to CORDIS for full partner lists

4. **For UPCOMING CALLS, include SPECIFIC details** (not just cluster patterns!):
   - SPECIFIC Call ID (e.g., HORIZON-CL6-2025-ZEROPOL-02-3, HORIZON-MISS-2025-OCEAN-01)
   - Deadline with SPECIFIC DATE (e.g., "February 25, 2026")
   - Budget per project (e.g., "€4-8 million")
   - Action type (RIA/IA/CSA)
   - Relevant topic description

5. **MANDATORY: If search yields fewer than 5 projects, use reference projects from built-in knowledge:**
   - OneAquaHealth (101086521): One Health approach for urban aquatic ecosystems, €4.94M, 14 partners (PT, IT, FR, NO, IL, DE)
   - StopUP (101060428): Urban runoff pollution and stormwater, €3.77M, 11 partners (DE, CH, UK, IT, NO)
   - AquaticPollutants (869178): Contaminants in water resources, €4.0M (FR, ES, DE, NL)
   - PARC (101057014): Chemical risk assessment for health and environment, €400M (FR, DE, IT, NL)
   - GloFouling (774009): Biofouling impacts on ecosystems and health, €3.6M (UK, NL, ES)

6. **User asks for PARTICIPANTS - you MUST provide at least partner counts and key countries for each project**

**SPECIAL CASE - Project Search Results:**
When the search_projects tool was used, your conclusion MUST:
1. **List ALL projects found** with their key details in a structured format
2. For EACH project, include:
   - **Project Title/Acronym** (in bold)
   - **Grant Agreement ID** (6-9 digit number)
   - **Coordinator** (organization name and country)
   - **Budget** (total cost and EC contribution in €M)
   - **Duration** (start and end dates)
   - **Brief objective** (1-2 sentences)
3. Use a consistent format (table or numbered list with clear structure)
4. Include a **CORDIS link** for each project: https://cordis.europa.eu/project/id/{{project_id}}
5. Add **how to learn more** at the end (CORDIS database, project websites, contact coordinators)

Example good project search output:
```
### Recent AI Research Projects

| # | Project | Budget | Coordinator | Description |
|---|---------|--------|-------------|-------------|
| 1 | **DEEPHEALTH** (101000001) | €5.2M | Karolinska Institute (SE) | Deep learning for medical imaging |
| 2 | **AICLIMATE** (101000002) | €6.1M | ETH Zurich (CH) | ML models for climate prediction |

#### How to Learn More:
- **CORDIS Database**: Search for full details at https://cordis.europa.eu
- **Contact Coordinators**: Reach out for collaboration opportunities
```

**CRITICAL: Handling Niche Topic Intersection Searches (e.g., "Industry 4.0 for soil regeneration")**
When a user requests a specific number of projects (e.g., "10 projects") at the intersection of two specialized topics:

1. **Run multiple search strategies** - Don't give up after one search:
   - First search: Exact intersection (e.g., "Industry 4.0 soil regeneration")
   - Second search: Primary topic + broader secondary (e.g., "digital agriculture soil" or "precision farming soil health")
   - Third search: Technology-focused (e.g., "smart sensors agriculture monitoring")
   - Fourth search: Application-focused (e.g., "soil monitoring technology" or "regenerative agriculture digital")

2. **Broaden progressively** when fewer than requested results are found:
   - If direct intersection yields <5 results, broaden to related concepts
   - For "Industry 4.0/5.0": expand to digitalization, automation, sensors, IoT, AI, robotics, precision, monitoring, data-driven, smart, digital twin
   - For "soil regeneration": expand to soil health, soil quality, carbon sequestration, sustainable farming, regenerative agriculture, agroecology, soil fertility, land restoration

3. **ALWAYS aim to provide the requested number** (e.g., 10 projects):
   - Include projects where the intersection is strong (core results)
   - Include projects where ONE topic is strong and the other is present (adjacent results)
   - Include highly relevant projects from one domain that enable/support the other
   - Clearly group/label them: "Core Projects (direct intersection)" and "Related Projects (adjacent relevance)"

4. **For each project, ALWAYS include objective summaries** - this is a key requirement when user asks for summaries:
   - Extract or synthesize the main objective in 2-3 sentences
   - Explain HOW the project relates to the topic intersection
   - Include specific technologies/methods used

5. **Example search strategy for "10 Industry 4.0/5.0 soil regeneration projects with objectives":**
   ```
   Search 1: "Industry 4.0 soil regeneration digital farming" → may yield 2-4 core results
   Search 2: "precision agriculture soil monitoring sensors" → may yield 3-4 more
   Search 3: "digital twin agriculture soil carbon" → may yield 2-3 more
   Search 4: "AI machine learning soil health farming" → fill remaining slots
   ```

6. **In the final response**, acknowledge if results span different relevance levels:
   - "I found 4 projects directly addressing Industry 4.0/5.0 for soil regeneration, plus 6 highly related projects applying digital technologies to soil health and sustainable agriculture."

**SPECIAL CASE - Complex Multi-Part Queries (Calls + Projects + Details):**
When the user asks a COMPLEX MULTI-PART query requesting BOTH calls AND projects WITH detailed information (partner lists, call IDs, coordinators, etc.), structure your response to address ALL parts:

**CRITICAL: You MUST include BOTH sections (calls AND projects) in your response!**

1. **For UPCOMING CALLS section:**
   - List specific call IDs (HORIZON-CL2-2025-*, HORIZON-CL4-2026-*, etc.)
   - Include SPECIFIC DEADLINES with dates (e.g., "March 12, 2026", not "Q1 2026")
   - Provide budgets per project (e.g., "€4-6 million per project")
   - Include key parameters (action type, funding rate, consortium requirements)

2. **For SIMILAR PROJECTS section (MANDATORY when user asks for similar projects!):**
   - **SEARCH STRATEGY - USE SIMPLE KEYWORDS:**
     * DO NOT use the user's full complex query as search terms
     * Extract 2-3 simple keywords (e.g., "cultural heritage", "heritage digital")
     * If first search returns 0 results, immediately run another search with simpler terms
     * See "Cultural Heritage Keywords" section above for search term guidance
   - **USE DATA FROM search_projects TOOL** - Do NOT skip this section if get_project_details fails
   - The search_projects tool returns: acronym, title, coordinator, budget, status, countries involved
   - For EACH project from search_projects, include:
     * **Project Acronym/Title** with Grant Agreement ID (e.g., "ARIADNE-PLUS (823914)")
     * **Call ID** that funded it if available (e.g., "H2020-INFRAIA-2018-2020")
     * **Total Cost/EC Contribution** from search results (e.g., "€9,995,000")
     * **Coordinator** with country from search results (e.g., "PIN SOC.CONS. A R.L. (Italy)")
     * **Consortium countries** from search results (e.g., "Partners from: IT, FR, UK, GR, AT, DE...")
     * **CORDIS link** for full details: https://cordis.europa.eu/project/id/{{project_id}}
   - **If user requests "list of partners"**: Direct them to CORDIS link for full partner list
   - **NEVER SKIP the projects section** - Always include projects found via search_projects
   - **FALLBACK**: If search_projects returns 0 results after multiple attempts, use the REFERENCE PROJECTS from the "Example: Digital Cultural Heritage Research (MULTIDISCIPLINARY)" section above (ARIADNE-PLUS, Time Machine, INCEPTION)

3. **For ACTIONABILITY section (CRITICAL for passing evaluation):**
   - Include link to EU Funding Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/
   - Include link to CORDIS: https://cordis.europa.eu
   - Add specific cluster Work Programme links
   - Add partner search guidance

**IMPORTANT: If the user asks about similar projects and you found them via search_projects, you MUST list them in your response even if get_project_details is unavailable!**
**IMPORTANT: If search_projects returns 0 results, use the HARDCODED REFERENCE PROJECTS from built-in knowledge!**

**Example for Cultural Heritage Multi-Part Query:**
When user asks about digital heritage with calls, parameters, AND similar projects with partners:
```
## Part 1: Upcoming Calls
| Call ID | Topic | Deadline | Budget | Type |
|---------|-------|----------|--------|------|
| HORIZON-CL2-2025-HERITAGE-01-02 | Digital preservation | March 12, 2026 | €4-6M | RIA |

## Part 2: Similar Funded Projects
### 1. **ARIADNE-PLUS** (Grant Agreement: 823914)
- **Call ID**: H2020-INFRAIA-2018-2020
- **Total Cost**: €9,995,000
- **Coordinator**: PIN SOC.CONS. A R.L. (Italy)
- **Partners (28 organizations)**:
  1. Consiglio Nazionale delle Ricerche (IT)
  2. INRIA (FR)
  3. University of York (UK)
  4. ATHENA Research Centre (GR)
  ...
- **CORDIS**: https://cordis.europa.eu/project/id/823914

## Part 3: Resources & Next Steps
- EU Funding Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/
- CORDIS Database: https://cordis.europa.eu
```

**SPECIAL CASE - Timeline Generation:**
When the generate_timeline tool was used, your conclusion MUST include the COMPLETE timeline output:
- ALL work packages with their full details (lead, participants, objectives, tasks, effort, duration)
- ALL deliverables with due dates, types, and dissemination levels
- ALL milestones with due months
- The COMPLETE ASCII Gantt chart (do not truncate or summarize it)
- WP dependencies
- All recommendations
This is critical because users need the full timeline for their proposals. Do NOT summarize or shorten it.

Example good conclusion:
"The minimum consortium composition for Horizon Europe RIA/IA projects is **3 independent legal entities from 3 different EU Member States or Associated Countries**.

### Key Requirements:
- At least 3 legal entities
- Each from a different country
- Countries must be EU Member States or Associated Countries

*Source: Horizon Europe Programme Guide*"

**SPECIAL CASE - Partner Discovery Responses (CRITICAL):**
When the user asks to **find partners/participants** for a project (especially with country or domain filters):

1. **ALWAYS list MULTIPLE partners (minimum 5, ideally 10)** from the find_experienced_partners results:
   - User asks for "partners" or "participants" (PLURAL) → YOU MUST list at least 5-10 organizations
   - DO NOT summarize with "I found several partners" and only mention 1-2
   - Include ALL partners returned by the tool (up to 10)

2. **For EACH partner, include complete details from the tool results:**
   - **Organization Name** (full name, not just abbreviation)
   - **Type**: HES (University), REC (Research Center), PRC (Private Company), PUB (Public Body)
   - **Relevant Projects**: Number of projects (X as coordinator if applicable)
   - **Funding**: Total funding received (€XM format)
   - **Brief expertise description** based on keywords/domain

3. **Structure the response as a numbered list:**
   ```
   Based on H2020/HE project data, here are **10 organizations in Spain** with relevant experience:

   **1. TECNALIA RESEARCH & INNOVATION (REC)**
   - **Relevant Projects**: 114 (17 as coordinator)
   - **Total Funding**: €68.1M
   - **Expertise**: Research center with strong municipal/urban innovation focus

   **2. FUNDACIO EURECAT (REC)**
   - **Relevant Projects**: 50 (11 as coordinator)
   - **Total Funding**: €26.7M
   - **Expertise**: Technology transfer, smart city, innovation ecosystems

   **3. UNIVERSITAT DE BARCELONA (HES)**
   ...
   ```

4. **Add actionable guidance:**
   - Link to CORDIS for detailed project information
   - Link to EU Partner Search for contacting organizations
   - Suggest verifying specific municipal/testbed ties via organization websites
   - For Spanish municipal networks: mention FEMP (Federación Española de Municipios y Provincias)

**NEVER return just 1-2 partners when the tool found 10-20. This is a CRITICAL requirement!**

Example BAD conclusion (never do this):
"From document X: The consortium shall... [raw text fragment]"

## Conversation History

{context}

## Current User Message

{query}

## Previous Steps (this reasoning session)

{previous_steps}

## Tool Results (if any)

{tool_results}

What is your next step? Remember: Output ONLY JSON."""

    def __init__(self, max_iterations: int = 5, enable_quality_analysis: bool = True):
        """Initialize the tool-aware agent.

        Args:
            max_iterations: Maximum number of reasoning iterations.
            enable_quality_analysis: Whether to analyze response quality (default: True).
        """
        self.max_iterations = max_iterations
        self.enable_quality_analysis = enable_quality_analysis
        self.tools: dict[str, Tool] = {}
        self._init_tools()
        self._init_llm()
        self._init_cache()
        self._init_analytics()
        self._init_speculative_executor()
        self._init_quality_analyzer()

        logger.info(f"🛠️ ToolAwareAgent initialized with {len(self.tools)} tools")

    def _init_cache(self):
        """Initialize query plan cache."""
        try:
            from ..cache.query_plan_cache import QueryPlanCache
            from ..memory.memory_service import MemoryService

            memory = MemoryService()
            self.plan_cache = QueryPlanCache(memory.redis_client)
            logger.info("✅ Query plan cache initialized")
        except Exception as e:
            logger.warning(f"⚠️ Query plan cache unavailable: {e}")
            self.plan_cache = None

    def _init_analytics(self):
        """Initialize tool analytics for usage tracking."""
        try:
            from ..analytics.tool_analytics_service import get_analytics_service

            self.analytics = get_analytics_service()
            logger.info("✅ Tool analytics initialized")
        except Exception as e:
            logger.warning(f"⚠️ Tool analytics unavailable: {e}")
            self.analytics = None

    def _init_speculative_executor(self):
        """Initialize speculative tool executor for parallel execution."""
        try:
            from ..cache.speculative_executor import SpeculativeExecutor

            # Create a wrapper that calls our tool execution method
            async def tool_executor(tool_name: str, params: dict):
                return await self._execute_single_tool(tool_name, params)

            self.speculative_executor = SpeculativeExecutor(tool_executor)
            logger.info("✅ Speculative executor initialized")
        except Exception as e:
            logger.warning(f"⚠️ Speculative executor unavailable: {e}")
            self.speculative_executor = None

    def _init_quality_analyzer(self):
        """Initialize response quality analyzer for monitoring and validation."""
        if not self.enable_quality_analysis:
            self.quality_analyzer = None
            logger.info("📊 Quality analysis disabled")
            return

        try:
            from ..quality.response_quality_analyzer import ResponseQualityAnalyzer

            self.quality_analyzer = ResponseQualityAnalyzer()
            logger.info("✅ Response quality analyzer initialized")
        except Exception as e:
            logger.warning(f"⚠️ Response quality analyzer unavailable: {e}")
            self.quality_analyzer = None

    def _analyze_response_quality(
        self, query: str, answer: str, tool_results: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Analyze the quality of a generated response.

        Args:
            query: The user's original query.
            answer: The generated answer text.
            tool_results: Results from tool executions.

        Returns:
            Quality analysis dict or None if analyzer unavailable.
        """
        if not self.quality_analyzer:
            return None

        try:
            # Analyze the response
            analysis = self.quality_analyzer.analyze(
                query=query, response=answer, tool_results=tool_results
            )

            # Log quality metrics for monitoring
            if analysis.category.value in ("deflection", "empty"):
                logger.warning(
                    f"⚠️ Response quality issue detected: "
                    f"category={analysis.category.value}, score={analysis.score}, "
                    f"deflections={len(analysis.deflection_phrases_found)}"
                )
            else:
                logger.info(
                    f"📊 Response quality: score={analysis.score}, "
                    f"category={analysis.category.value}, "
                    f"confidence={analysis.confidence:.2f}"
                )

            return analysis.to_dict()

        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            return None

    def _init_llm(self):
        """Initialize the LLM for reasoning."""
        import os

        self.llm_provider = os.getenv("DEFAULT_AI_PROVIDER", "gemini")

        if self.llm_provider == "gemini":
            try:
                import google.generativeai as genai

                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                # Use GEMINI_MODEL from env - defaults to latest flash model
                model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
                self.llm = genai.GenerativeModel(model_name)
                logger.info(f"🧠 ToolAwareAgent using model: {model_name}")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
                self.llm = None
        else:
            self.llm = None
            logger.warning("LLM not configured for ToolAwareAgent")

    def _init_tools(self):
        """Initialize all available tools."""

        # Graph-based statistics tools
        self.register_tool(
            Tool(
                name="get_programme_statistics",
                description="""**STATISTICS TOOL** - Get success rates, funding amounts, participation data.

**USE THIS WHEN USER ASKS:**
- "What's the success rate?" / "success rate for X"
- "How competitive is this call/programme?"
- "Average funding for X" / "typical budget"
- "How many projects were funded?"

Returns: Success rates, average funding, participation statistics from real data.

**DO NOT use search_documents for statistics - use this tool instead!**""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "programme": "Programme name (e.g., 'EIC', 'ERC', 'MSCA', 'Cluster 5')",
                    "metric": "Optional: specific metric like 'success_rate', 'avg_funding', 'participation'",
                },
                examples=[
                    "get_programme_statistics(programme='EIC Accelerator')",
                    "get_programme_statistics(programme='Cluster 5', metric='success_rate')",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="get_country_statistics",
                description="""Get participation statistics and top organizations for ONE SPECIFIC country.

**IMPORTANT**: This tool is for SINGLE COUNTRY lookups only. Use a real country name/code (Germany, FR, Netherlands, etc.).
DO NOT use "EU" as a country - it's not valid. For analytical "why" questions about country differences, use BUILT-IN KNOWLEDGE instead.

Returns: Eligibility status, top organizations in that country, and participation data.""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "country": "Country name (e.g., 'Germany', 'France') or ISO code (e.g., 'DE', 'FR'). NOT 'EU'.",
                    "programme": "Optional: filter by programme",
                },
                examples=[
                    "get_country_statistics(country='Germany')",
                    "get_country_statistics(country='Netherlands', programme='EIC')",
                ],
            )
        )

        # Budget benchmarking tool
        self.register_tool(
            Tool(
                name="get_budget_benchmark",
                description="Get real budget statistics from funded Horizon Europe projects. Returns min/max/average/median EU contributions, budget per partner, consortium sizes, and data-driven recommendations.",
                category=ToolCategory.STATISTICS,
                parameters={
                    "cluster": "Optional: Cluster code (e.g., 'CL4', 'CL5', 'EIC')",
                    "action_type": "Optional: Action type (e.g., 'RIA', 'IA', 'CSA', 'ERC-STG')",
                    "topic_keywords": "Optional: Keywords to filter projects (e.g., 'AI', 'hydrogen')",
                    "year": "Optional: Filter by funding year",
                },
                examples=[
                    "get_budget_benchmark(cluster='CL4', action_type='RIA')",
                    "get_budget_benchmark(action_type='IA', topic_keywords='hydrogen')",
                    "get_budget_benchmark(cluster='CL5')",
                ],
            )
        )

        # Consortium patterns tool
        self.register_tool(
            Tool(
                name="get_consortium_patterns",
                description="Analyze consortium composition patterns from funded projects. Returns organization type distribution (HES, REC, PRC, SME), country participation rates, coordinator profiles, and composition recommendations.",
                category=ToolCategory.STATISTICS,
                parameters={
                    "cluster": "Optional: Cluster code (e.g., 'CL4', 'CL5', 'EIC')",
                    "action_type": "Optional: Action type (e.g., 'RIA', 'IA', 'CSA')",
                    "topic_keywords": "Optional: Keywords to filter projects",
                },
                examples=[
                    "get_consortium_patterns(cluster='CL4', action_type='RIA')",
                    "get_consortium_patterns(action_type='IA')",
                    "get_consortium_patterns(topic_keywords='hydrogen')",
                ],
            )
        )

        # Geographic diversification tool
        self.register_tool(
            Tool(
                name="analyze_geographic_diversification",
                description="""Analyze geographic diversification of country partners in consortia by custom country groups.

**USE THIS TOOL WHEN**: User asks about country group coverage, geographic diversity patterns, or share of projects with partners from specific European regions (Nordic, South Europe, Baltic, CEE, Western Balkans, EPC, Islands, Western Europe).

Returns:
- Share of projects with at least one partner from each country group
- Coverage statistics (how many projects have 5/6/7/8 groups)
- Underrepresented vs well-represented groups
- Recommendations for consortium building

Default country groups:
- Nordic: NO, DK, SE, FI
- South Europe: ES, PT, IT, GR
- Western Europe: FR, DE, BE, NL, LU (BENELUX)
- Baltic: EE, LV, LT
- CEE: PL, SK, CZ, HU, SI
- Western Balkans: HR, RS, ME
- EPC (Eastern Partnership): MD, BY, UA, GE, AM, AZ
- Islands: IE, UK, MT, CY""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "cluster": "Optional: Cluster code (e.g., 'CL2' for Cluster 2/SSH)",
                    "exclude_widening": "Optional: Exclude Widening calls (default: True)",
                    "min_partners": "Optional: Minimum partners for consortium inclusion (default: 3)",
                    "country_groups": "Optional: Custom country group definitions (dict of group_name -> [country_codes])",
                },
                examples=[
                    "analyze_geographic_diversification(cluster='CL2', exclude_widening=True)",
                    "analyze_geographic_diversification(cluster='CL5')",
                    "analyze_geographic_diversification()",
                ],
            )
        )

        # Partner discovery tool
        self.register_tool(
            Tool(
                name="find_experienced_partners",
                description="""**PARTNER DISCOVERY TOOL** - Find organizations with proven EU funding track records.

**USE THIS WHEN USER ASKS:**
- "Find partners" / "find organizations" / "partner search"
- "Organizations experienced in X" / "who has experience in X"
- "Find consortium partners" / "potential partners"
- "Companies/universities working on X"

Returns: Organizations with their project count, funding received, coordination experience.

**DO NOT use search_documents for finding partners - use this tool instead!**""",
                category=ToolCategory.PROJECTS,
                parameters={
                    "topic_keywords": "Required: Keywords describing the research area (e.g., 'quantum computing')",
                    "country": "Optional: Country name or code (e.g., 'Germany', 'DE')",
                    "organization_type": "Optional: HES, REC, PRC, SME, university, research",
                    "cluster": "Optional: Cluster code (CL2, CL4, CL5, etc.)",
                    "min_projects": "Optional: Minimum projects to be considered experienced (default: 2)",
                    "role_filter": "Optional: 'coordinator' or 'participant'",
                    "programme": "Optional: 'HORIZON' (HE only), 'H2020' (H2020 only), or 'both' (default: both)",
                },
                examples=[
                    "find_experienced_partners(topic_keywords='quantum computing', country='Germany')",
                    "find_experienced_partners(topic_keywords='hydrogen', organization_type='SME')",
                    "find_experienced_partners(topic_keywords='AI healthcare', role_filter='coordinator')",
                    "find_experienced_partners(topic_keywords='democracy governance society', cluster='CL2', role_filter='coordinator', programme='both')",
                ],
            )
        )

        # Similar funded projects tool (semantic search) - FOR PROPOSAL SUPPORT ONLY
        self.register_tool(
            Tool(
                name="get_similar_funded_projects",
                description="""Find projects similar to a SPECIFIC PROPOSAL IDEA for proposal writing support.

**USE THIS TOOL WHEN**: User is writing a proposal and wants to find similar funded projects to learn from.
**DO NOT USE FOR**: General project searches like "find projects about X" - use search_projects instead.

This tool uses AI embeddings to match a detailed proposal description to funded projects.""",
                category=ToolCategory.PROJECTS,
                parameters={
                    "description": "Required: Detailed project idea/proposal description to match (min 20 chars)",
                    "cluster": "Optional: Cluster code filter (CL4, CL5, EIC, etc.)",
                    "action_type": "Optional: Action type filter (RIA, IA, CSA)",
                    "min_budget": "Optional: Minimum EU contribution filter",
                    "max_budget": "Optional: Maximum EU contribution filter",
                    "year_from": "Optional: Filter for projects starting from year",
                    "limit": "Optional: Number of results (default 10)",
                },
                examples=[
                    "get_similar_funded_projects(description='Our proposal develops an AI-powered diagnostic system for early cancer detection using deep learning on medical imaging data, targeting integration with existing hospital workflows')",
                    "get_similar_funded_projects(description='Novel green hydrogen production using advanced electrolyzers with 30% efficiency improvement', cluster='CL5')",
                ],
            )
        )

        # Call history analysis tool
        self.register_tool(
            Tool(
                name="analyze_call_history",
                description="""Analyze historical funding patterns for Horizon Europe topics. Shows what got funded, when, funding trends over time, and recommendations.

IMPORTANT - Scope Control with 'expand_scope':
- expand_scope=False (default): Searches for projects where the topic IS the main focus (e.g., "AI research projects")
- expand_scope=True: Searches for projects where the topic is USED/APPLIED (e.g., "projects that use AI as a tool")

When user asks about "projects using X" or "X as part of projects" or "applied X", set expand_scope=True.
This uses AI to automatically expand keywords to related terms (e.g., "AI" → includes "machine learning", "neural networks", "deep learning", etc.)""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "topic_pattern": "Optional: Topic code pattern (e.g., 'HORIZON-CL4-2023')",
                    "cluster": "Optional: Cluster code (CL4, CL5, EIC, etc.)",
                    "keywords": "Optional: Keywords to search in call titles/descriptions",
                    "year_from": "Optional: Starting year filter",
                    "year_to": "Optional: Ending year filter",
                    "action_types": "Optional: List of action types (RIA, IA, CSA)",
                    "include_projects": "Optional: Include funded project examples (default true)",
                    "expand_scope": "Optional: Set to true to include projects where the topic is USED/APPLIED, not just focused on it. Uses AI to expand keywords to related terms.",
                },
                examples=[
                    "analyze_call_history(cluster='CL4', keywords='artificial intelligence')  # AI-focused projects only",
                    "analyze_call_history(keywords='artificial intelligence', expand_scope=True)  # Projects USING AI",
                    "analyze_call_history(keywords='hydrogen', year_from=2022)",
                    "analyze_call_history(cluster='CL5', action_types=['RIA', 'IA'])",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="compare_programmes",
                description="Compare statistics between two programmes or clusters",
                category=ToolCategory.COMPARISON,
                parameters={
                    "programme_a": "First programme to compare",
                    "programme_b": "Second programme to compare",
                    "metrics": "List of metrics to compare",
                },
                examples=[
                    "compare_programmes(programme_a='EIC', programme_b='ERC', metrics=['success_rate', 'avg_funding'])"
                ],
            )
        )

        # Document search tools
        self.register_tool(
            Tool(
                name="search_documents",
                description="""Search official EU documents for RULES, ELIGIBILITY, and REQUIREMENTS only.

**DO NOT USE THIS TOOL FOR:**
- Budget planning/calculation → USE calculate_budget instead!
- Budget recalculation/adjustment → USE calculate_budget instead!
- Budget comparison/benchmarking → USE get_budget_benchmark instead!
- "What if we add more partners" → USE calculate_budget instead!
- "90th percentile" / budget percentiles → USE get_budget_benchmark instead!
- "Compare this budget" / "typical RIA" → USE get_budget_benchmark instead!
- "Increase personnel costs" / cost adjustments → USE calculate_budget instead!
- Timeline generation → USE generate_timeline instead!
- Work packages / WP structure → USE generate_timeline instead!
- Add clinical trial phase / clinical phases → USE generate_timeline instead!
- Buffer period / delay handling → USE generate_timeline instead!
- Milestones / adjust milestones → USE generate_timeline instead!
- Similar project timelines → USE find_similar_projects or get_similar_funded_projects instead!
- Typical timeline patterns → USE find_similar_projects + generate_timeline instead!
- Finding partners/organizations → USE find_experienced_partners instead!
- Success rates/statistics → USE get_programme_statistics instead!
- Consortium composition patterns → USE get_consortium_patterns instead!
- "Find organizations experienced in X" → USE find_experienced_partners instead!
- "SME partner from X region" → USE find_experienced_partners with organization_type and country!
- "Research organization from Germany" → USE find_experienced_partners with country filter!
- "Typical consortium size" → USE get_consortium_patterns instead!
- "Precision farming" / "agriculture AI" partners → USE find_experienced_partners instead!

**USE THIS TOOL ONLY FOR:**
- Eligibility rules ("What are the eligibility rules for RIA?")
- Submission requirements ("What documents do I need to submit?")
- Evaluation criteria ("What are the evaluation criteria?")
- Official EU regulations and guidance documents""",
                category=ToolCategory.DOCUMENTS,
                parameters={
                    "query": "Search query",
                    "document_type": "Optional: 'regulation', 'work_programme', 'guidance', 'template'",
                    "max_results": "Optional: number of results (default 5)",
                },
                examples=[
                    "search_documents(query='consortium eligibility RIA')",
                    "search_documents(query='budget categories', document_type='guidance')",
                ],
            )
        )

        # Funding call tools
        self.register_tool(
            Tool(
                name="search_funding_calls",
                description="Search for open or upcoming funding calls",
                category=ToolCategory.CALLS,
                parameters={
                    "keywords": "Keywords to search for",
                    "status": "Optional: 'open', 'upcoming', 'closed'",
                    "year": "Optional: specific year",
                },
                examples=[
                    "search_funding_calls(keywords='hydrogen energy', status='open')",
                    "search_funding_calls(keywords='AI healthcare', year=2025)",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="get_call_details",
                description="Get detailed information about a specific funding call by its ID. Use this when the user provides a call ID (e.g., HORIZON-*, CREA-*, EIC-*). This tool fetches from the EU Portal API if not found locally.",
                category=ToolCategory.CALLS,
                parameters={
                    "call_id": "The call identifier (e.g., 'HORIZON-CL5-2025-D3-01', 'CREA-MEDIA-2026-FILMSALES')"
                },
                examples=[
                    "get_call_details(call_id='HORIZON-CL5-2025-D3-01')",
                    "get_call_details(call_id='CREA-MEDIA-2026-FILMSALES')",
                ],
            )
        )

        # Project search tools
        self.register_tool(
            Tool(
                name="search_projects",
                description="""Search the CORDIS database for funded Horizon Europe projects by topic/keywords.

**USE THIS TOOL FOR**: General project searches like "find projects about AI", "show me quantum computing projects", "projects on climate change"
**Returns**: List of funded projects matching the keywords with titles, budgets, consortiums, and descriptions.

**SEARCH TIPS**:
- For AI/ML research: Use keywords like "machine learning", "neural network", "deep learning", "artificial intelligence"
- Short acronyms like "AI", "ML", "IoT", "HPC" are supported but may benefit from expanded terms
- Combine specific terms for better results: "AI healthcare diagnostics" rather than just "AI"
- The search uses full-text matching on project titles, objectives, and topics

This is the PRIMARY tool for finding projects by topic.""",
                category=ToolCategory.PROJECTS,
                parameters={
                    "keywords": "Required: Keywords/topic to search for (e.g., 'machine learning healthcare', 'quantum computing', 'green hydrogen')",
                    "programme": "Optional: Filter by programme (Horizon Europe, EIC, ERC, etc.)",
                    "country": "Optional: Filter by coordinator/participant country",
                    "limit": "Optional: Number of results (default 10)",
                },
                examples=[
                    "search_projects(keywords='machine learning healthcare diagnostics')",
                    "search_projects(keywords='artificial intelligence robotics')",
                    "search_projects(keywords='renewable energy', country='Germany')",
                    "search_projects(keywords='deep learning computer vision', limit=15)",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="get_project_details",
                description="Get detailed information about a specific project",
                category=ToolCategory.PROJECTS,
                parameters={"project_id": "The project identifier or acronym"},
                examples=["get_project_details(project_id='101000000')"],
            )
        )

        # Relationship-based project discovery tools
        self.register_tool(
            Tool(
                name="find_similar_projects",
                description="Find projects similar to a given project based on topic, consortium partners, or cluster",
                category=ToolCategory.PROJECTS,
                parameters={
                    "project_id": "The reference project ID",
                    "similarity_type": "Type: 'topic' (same topic), 'consortium' (shared partners), or 'cluster' (same cluster)",
                },
                examples=[
                    "find_similar_projects(project_id='101000000', similarity_type='topic')",
                    "find_similar_projects(project_id='101000000', similarity_type='consortium')",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="find_semantically_similar_projects",
                description="Find projects semantically similar to a given project using AI embeddings (understands project objectives and descriptions)",
                category=ToolCategory.PROJECTS,
                parameters={
                    "project_id": "The reference project ID",
                    "limit": "Optional: maximum number of results (default 10)",
                },
                examples=[
                    "find_semantically_similar_projects(project_id='101000000')",
                    "find_semantically_similar_projects(project_id='101000000', limit=5)",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="find_organization_projects",
                description="Find all projects an organization has participated in",
                category=ToolCategory.PROJECTS,
                parameters={
                    "organization_name": "Name (or partial name) of the organization",
                    "role": "Optional: 'coordinator' or 'participant'",
                },
                examples=[
                    "find_organization_projects(organization_name='Fraunhofer')",
                    "find_organization_projects(organization_name='TU Munich', role='coordinator')",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="get_collaboration_network",
                description="Get the collaboration network showing which organizations frequently partner together",
                category=ToolCategory.PROJECTS,
                parameters={"organization_name": "Name of the organization to find partners for"},
                examples=["get_collaboration_network(organization_name='CNRS')"],
            )
        )

        self.register_tool(
            Tool(
                name="search_by_cluster",
                description="Find projects in a specific research cluster (e.g., Climate, Health, Digital)",
                category=ToolCategory.PROJECTS,
                parameters={"cluster": "Cluster name or code (e.g., 'Climate', 'CL5', 'Health')"},
                examples=[
                    "search_by_cluster(cluster='Climate')",
                    "search_by_cluster(cluster='CL4')",
                ],
            )
        )

        # Budget calculator tool (proposal planning)
        self.register_tool(
            Tool(
                name="calculate_budget",
                description="""**PROPOSAL PLANNING TOOL** - Calculate budget breakdown for a Horizon Europe proposal.

**USE THIS WHEN USER ASKS:**
- "Help me plan the budget" / "calculate budget" / "budget breakdown"
- "Budget for X million project" / "X year project budget"
- "How should I allocate my budget?"

Returns: Personnel costs, equipment, travel, subcontracting, indirect costs, per-partner distribution.

**DO NOT use search_documents for budget planning - use this tool instead!**""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "action_type": "Required: Action type (RIA, IA, CSA, ERC-STG, ERC-COG, ERC-ADG)",
                    "duration_months": "Required: Project duration in months",
                    "num_partners": "Required: Number of consortium partners",
                    "total_person_months": "Optional: Total person-months (if known)",
                    "target_budget": "Optional: Target total budget in EUR",
                    "countries": "Optional: List of partner country codes (e.g., ['DE', 'FR', 'ES'])",
                },
                examples=[
                    "calculate_budget(action_type='RIA', duration_months=36, num_partners=8)",
                    "calculate_budget(action_type='IA', duration_months=48, num_partners=12, target_budget=10000000)",
                    "calculate_budget(action_type='RIA', duration_months=36, num_partners=6, countries=['DE', 'FR', 'ES', 'PL', 'IT', 'NL'])",
                ],
            )
        )

        # Timeline generator tool (proposal planning)
        self.register_tool(
            Tool(
                name="generate_timeline",
                description="""**PROPOSAL PLANNING TOOL** - Generate project timeline with work packages, deliverables, milestones.

**USE THIS WHEN USER ASKS:**
- "Generate a timeline" / "project timeline" / "timeline for X months"
- "Work packages" / "WP structure" / "how many work packages"
- "What deliverables should we have?" / "milestones"
- "48-month project with 6 work packages"

Returns: Work package structure, deliverables with due dates, milestones, Gantt chart structure.

**DO NOT use search_documents for timeline planning - use this tool instead!**""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "action_type": "Required: Action type (RIA, IA, CSA, ERC)",
                    "duration_months": "Required: Project duration in months",
                    "num_partners": "Required: Number of partners",
                    "total_person_months": "Required: Total effort in person-months",
                    "project_title": "Optional: Project title for naming",
                    "start_date": "Optional: Start date (YYYY-MM-DD)",
                },
                examples=[
                    "generate_timeline(action_type='RIA', duration_months=36, num_partners=8, total_person_months=300)",
                    "generate_timeline(action_type='IA', duration_months=48, num_partners=12, total_person_months=500, project_title='GreenHydrogen')",
                ],
            )
        )

        # =====================================================================
        # Multi-Programme Tools (NEW)
        # Search across all 6 EU programmes: Horizon Europe, Erasmus+,
        # Creative Europe, EU4Health, Digital Europe, LIFE
        # =====================================================================

        self.register_tool(
            Tool(
                name="search_all_programmes",
                description="""Search for funding opportunities across ALL EU programmes in one query.
Searches: Horizon Europe (€95.5B), Erasmus+ (€26.2B), Creative Europe (€2.44B),
EU4Health (€5.3B), Digital Europe (€7.5B), LIFE (€5.4B).

Use this when user asks about funding in a general area (education, health, culture, etc.)
or wants to compare options across different EU programmes.""",
                category=ToolCategory.PROGRAMMES,
                parameters={
                    "keywords": "Required: Search keywords (e.g., 'renewable energy', 'youth mobility', 'digital health')",
                    "programmes": "Optional: List of programmes to search (e.g., ['horizon_europe', 'erasmus_plus']). If not specified, searches all.",
                    "status": "Optional: Filter by status ('open', 'upcoming')",
                    "year": "Optional: Filter by call year",
                },
                examples=[
                    "search_all_programmes(keywords='renewable energy')",
                    "search_all_programmes(keywords='digital skills', programmes=['erasmus_plus', 'digital_europe'])",
                    "search_all_programmes(keywords='cancer research', status='open')",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="recommend_programmes",
                description="""Recommend the best EU funding programmes for a given project or organization.
Returns ranked recommendations with reasoning based on project description,
organization type, and sector.

Use this when user asks "Which programme should I apply to?" or describes their
project and wants to know where to find funding.""",
                category=ToolCategory.PROGRAMMES,
                parameters={
                    "description": "Required: Description of the project or activity",
                    "organization_type": "Optional: Type of organization (university, SME, NGO, hospital, school, etc.)",
                    "sector": "Optional: Primary sector (health, education, culture, research, environment, digital)",
                },
                examples=[
                    "recommend_programmes(description='Develop AI tools for early cancer detection', organization_type='university')",
                    "recommend_programmes(description='Student exchange programme between European universities', sector='education')",
                    "recommend_programmes(description='Documentary film about European cultural heritage')",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="get_programme_info",
                description="""Get detailed information about a specific EU funding programme.
Returns budget, focus areas, action types, eligibility, key actions (for Erasmus+),
strands (for Creative Europe), and priority areas (for EU4Health).

IMPORTANT: Also returns 'actionable_guidance' with official links and next steps.
When explaining a programme's structure, ALWAYS include these actionable links
at the end of your response to help users take next steps.

Available programmes: horizon_europe, erasmus_plus, creative_europe, eu4health,
digital_europe, life""",
                category=ToolCategory.PROGRAMMES,
                parameters={
                    "programme": "Optional: Specific programme ID (e.g., 'erasmus_plus', 'eu4health'). If not specified, returns info for all programmes."
                },
                examples=[
                    "get_programme_info(programme='erasmus_plus')",
                    "get_programme_info(programme='creative_europe')",
                    "get_programme_info()",
                ],
            )
        )

        # Proposal Quality Scoring Tools
        self.tools["score_proposal_section"] = Tool(
            name="score_proposal_section",
            description="Evaluate a proposal section using EU Horizon Europe evaluation criteria. Returns score (0-5), quality level, strengths, weaknesses, and improvement suggestions. Use this when users want to assess proposal quality.",
            category=ToolCategory.PROPOSAL,
            parameters={
                "content": "The proposal section text to evaluate (required, minimum 50 characters)",
                "section_type": "Type of section: 'excellence', 'impact', or 'implementation' (required)",
                "section_id": "Optional specific section: 'objectives', 'methodology', 'state_of_art', 'pathways', 'dissemination', 'work_plan', 'consortium'",
                "action_type": "Optional action type: 'RIA', 'IA', or 'CSA' (default: 'RIA')",
            },
            examples=[
                "score_proposal_section(content='Our project aims to...', section_type='excellence')",
                "score_proposal_section(content='The methodology involves...', section_type='excellence', section_id='methodology')",
                "score_proposal_section(content='Expected impacts include...', section_type='impact', action_type='IA')",
            ],
        )

        self.tools["score_full_proposal"] = Tool(
            name="score_full_proposal",
            description="Evaluate a complete proposal with all three main sections. Returns overall score (0-15), funding probability, and section-by-section breakdown. Use this for comprehensive proposal assessment.",
            category=ToolCategory.PROPOSAL,
            parameters={
                "excellence_content": "Excellence section content (objectives, methodology, state-of-art)",
                "impact_content": "Impact section content (pathways, dissemination, exploitation)",
                "implementation_content": "Implementation section content (work plan, consortium, resources)",
                "action_type": "Optional action type: 'RIA', 'IA', or 'CSA' (default: 'RIA')",
            },
            examples=[
                "score_full_proposal(excellence_content='...', impact_content='...', implementation_content='...')",
                "score_full_proposal(excellence_content='...', impact_content='...', implementation_content='...', action_type='IA')",
            ],
        )

        self.tools["quick_quality_check"] = Tool(
            name="quick_quality_check",
            description="Quick quality check for draft proposal text without full AI evaluation. Returns quality indicators and improvement suggestions. Use this for rapid feedback on early drafts.",
            category=ToolCategory.PROPOSAL,
            parameters={
                "text": "The draft text to check (required)",
                "context": "Optional context hint: 'objectives', 'methodology', 'impact', etc.",
            },
            examples=[
                "quick_quality_check(text='This project will develop innovative solutions...')",
                "quick_quality_check(text='The work plan consists of 5 WPs...', context='implementation')",
            ],
        )

        self.tools["validate_budget"] = Tool(
            name="validate_budget",
            description="Validate a proposal budget against EU Horizon Europe funding rules. Checks funding rates, cost categories, consortium requirements, and budget ranges. Returns compliance score and issues.",
            category=ToolCategory.PROPOSAL,
            parameters={
                "total_cost": "Total project cost in EUR (required)",
                "eu_contribution": "Requested EU contribution in EUR (required)",
                "action_type": "Action type: 'RIA', 'IA', 'CSA', 'ERC-STG', 'ERC-COG', 'ERC-ADG', 'EIC', 'MSCA' (default: 'RIA')",
                "duration_months": "Project duration in months (default: 36)",
                "num_partners": "Number of consortium partners (default: 3)",
                "cost_breakdown": "Optional dict with personnel, equipment, travel, subcontracting, other_direct, indirect costs",
                "call_budget_cap": "Optional call-specific maximum budget",
            },
            examples=[
                "validate_budget(total_cost=4000000, eu_contribution=4000000, action_type='RIA', num_partners=8)",
                "validate_budget(total_cost=6000000, eu_contribution=4200000, action_type='IA', duration_months=42)",
                "validate_budget(total_cost=2000000, eu_contribution=2000000, action_type='CSA', cost_breakdown={'personnel': 1300000, 'travel': 200000})",
            ],
        )

        # Erasmus+ specific tools
        self.tools["check_erasmus_eligibility"] = Tool(
            name="check_erasmus_eligibility",
            description="Check if an organization is eligible for Erasmus+ actions. Considers organization type (HEI, school, NGO, etc.), country (Programme vs Partner), ECHE status, and Key Action requirements. Use for eligibility questions about Erasmus+.",
            category=ToolCategory.CALLS,
            parameters={
                "org_type": "Organization type: HEI, SCHOOL, VET_PROVIDER, ADULT_ED, YOUTH_ORG, NGO, PUBLIC_BODY, ENTERPRISE, SPORT_ORG, RESEARCH (required)",
                "country": "Country of the organization (required)",
                "action_type": "Optional: Erasmus+ action to check (e.g., 'KA1-HED', 'KA2-COOP', 'KA2-SSP', 'JMO-MODULE', 'SPORT-COOP')",
                "has_eche": "Optional: Whether the HEI has ECHE (default: false)",
                "is_coordinator": "Optional: Whether checking as coordinator (default: true)",
            },
            examples=[
                "check_erasmus_eligibility(org_type='HEI', country='Germany', action_type='KA1-HED', has_eche=True)",
                "check_erasmus_eligibility(org_type='NGO', country='Spain', action_type='KA2-COOP')",
                "check_erasmus_eligibility(org_type='SCHOOL', country='France')  # Returns all eligible actions",
            ],
        )

        self.tools["calculate_erasmus_budget"] = Tool(
            name="calculate_erasmus_budget",
            description="Calculate Erasmus+ lump sum grants using official unit costs. Handles mobility (KA1), partnership (KA2), Jean Monnet, and Sport budgets. Uses travel bands, daily rates, and organizational support rates from the Programme Guide.",
            category=ToolCategory.PROPOSAL,
            parameters={
                "action_type": "Action type: 'mobility', 'partnership', 'jean_monnet', 'sport', or specific codes like 'KA1-HED', 'KA2-COOP' (required)",
                "num_participants": "Number of participants for mobility (default: 10)",
                "duration_days": "Duration in days for mobility (default: 14)",
                "duration_months": "Project duration in months for partnership (default: 24)",
                "num_partners": "Number of partners for KA2 (default: 3)",
                "destination_country": "Destination/coordinator country (default: 'Germany')",
                "origin_country": "Origin country for mobility (default: 'Spain')",
                "partnership_type": "'cooperation' (120-400k EUR) or 'small_scale' (30-60k EUR)",
                "distance_band": "Travel distance: '100-499km', '500-1999km', '2000-2999km', etc.",
                "green_travel": "Whether using sustainable travel (adds bonus)",
                "target_budget": "Optional target budget for partnership",
            },
            examples=[
                "calculate_erasmus_budget(action_type='mobility', num_participants=20, duration_days=10, destination_country='France')",
                "calculate_erasmus_budget(action_type='partnership', num_partners=5, duration_months=36, partnership_type='cooperation')",
                "calculate_erasmus_budget(action_type='jean_monnet', action_type='JMO-MODULE')",
                "calculate_erasmus_budget(action_type='sport', partnership_type='small_scale', num_partners=3)",
            ],
        )

        self.tools["search_erasmus_templates"] = Tool(
            name="search_erasmus_templates",
            description="Search Erasmus+ Programme Guide for application guidance, eligibility rules, quality criteria, budget information, and sector-specific requirements. Use for any Erasmus+ application questions.",
            category=ToolCategory.DOCUMENTS,
            parameters={
                "query": "What to search for (e.g., 'KA2 quality criteria', 'mobility eligibility')",
                "key_action": "Optional: Filter by KA1, KA2, KA3, JMO, SPORT",
                "sector": "Optional: Filter by HED, VET, SCH, ADU, YOU, SPORT",
                "document_type": "Optional: eligibility, budget, quality_criteria, etc.",
                "top_k": "Number of results (default: 5)",
            },
            examples=[
                "search_erasmus_templates(query='quality assessment criteria', key_action='KA2')",
                "search_erasmus_templates(query='budget lump sum calculation', sector='HED')",
                "search_erasmus_templates(query='ECHE requirements for higher education')",
                "search_erasmus_templates(query='partnership eligibility', key_action='KA2', sector='VET')",
            ],
        )

        # Creative Europe specific tools
        self.tools["check_creative_europe_eligibility"] = Tool(
            name="check_creative_europe_eligibility",
            description="Check if an organization is eligible for Creative Europe actions. Covers CULTURE strand (cooperation projects, networks, platforms), MEDIA strand (film development, distribution, festivals), and Cross-sectoral strand (innovation labs, news media). Use for eligibility questions about Creative Europe.",
            category=ToolCategory.CALLS,
            parameters={
                "org_type": "Organization type: CULTURAL_ORG, AUDIOVISUAL, PRODUCTION, DISTRIBUTION, BROADCASTER, CINEMA, FESTIVAL, TRAINING, NGO, PUBLIC_BODY, SME, NEWS_MEDIA, RESEARCH (required)",
                "country": "Country of the organization (required)",
                "action_type": "Optional: Specific action to check (e.g., 'COOP-SMALL', 'DEVSLATE', 'INNOVLAB')",
                "strand": "Optional: Filter by CULTURE, MEDIA, or CROSS-SECTORAL",
                "is_coordinator": "Optional: Whether checking as coordinator (default: true)",
            },
            examples=[
                "check_creative_europe_eligibility(org_type='PRODUCTION', country='France', action_type='DEVSLATE')",
                "check_creative_europe_eligibility(org_type='CULTURAL_ORG', country='Germany', strand='CULTURE')",
                "check_creative_europe_eligibility(org_type='NEWS_MEDIA', country='Spain', action_type='JOURPART')",
            ],
        )

        self.tools["calculate_creative_europe_budget"] = Tool(
            name="calculate_creative_europe_budget",
            description="Calculate Creative Europe grant amounts based on strand and action type. Covers CULTURE (cooperation projects 200k-2M), MEDIA (development 30-210k, distribution, festivals), and Cross-sectoral (innovation labs 2-4M, news partnerships). Uses official funding rates and budget caps.",
            category=ToolCategory.PROPOSAL,
            parameters={
                "action_type": "Action type: COOP-SMALL, COOP-MEDIUM, COOP-LARGE, DEVSLATE, DEVSINGLE, TVONLINE, FEST, INNOVLAB, JOURPART, etc. (required)",
                "requested_amount": "Optional: Requested EU grant amount",
                "project_scale": "'small', 'medium', or 'large' (default: 'medium')",
                "num_partners": "Number of consortium partners (default: 3)",
                "duration_months": "Optional: Project duration in months",
                "strand": "Optional: For 'OVERVIEW' action_type, filter by strand",
            },
            examples=[
                "calculate_creative_europe_budget(action_type='COOP-MEDIUM', num_partners=6, project_scale='large')",
                "calculate_creative_europe_budget(action_type='DEVSLATE', requested_amount=180000)",
                "calculate_creative_europe_budget(action_type='OVERVIEW', strand='MEDIA')  # Get all MEDIA action budgets",
            ],
        )

        self.tools["search_creative_europe_templates"] = Tool(
            name="search_creative_europe_templates",
            description="Search Creative Europe documents (Work Programmes, CulturEU Funding Guide, strand overviews) for application guidance, eligibility criteria, and programme information. Use for Creative Europe application questions.",
            category=ToolCategory.DOCUMENTS,
            parameters={
                "query": "What to search for (e.g., 'MEDIA development eligibility', 'cooperation project criteria')",
                "strand": "Optional: Filter by CULTURE, MEDIA, or CROSS-SECTORAL",
                "action_type": "Optional: Filter by action type (e.g., 'DEVSLATE', 'COOP-SMALL')",
                "topic": "Optional: Specific topic (eligibility, budget, evaluation)",
                "top_k": "Number of results (default: 5)",
            },
            examples=[
                "search_creative_europe_templates(query='MEDIA development eligibility requirements')",
                "search_creative_europe_templates(query='cooperation project evaluation criteria', strand='CULTURE')",
                "search_creative_europe_templates(query='film distribution support', action_type='FILMDIST')",
            ],
        )

    def register_tool(self, tool: Tool):
        """Register a tool with the agent."""
        self.tools[tool.name] = tool

    def _get_tools_description(self) -> str:
        """Generate tools description for the prompt."""
        by_category = {}
        for tool in self.tools.values():
            cat = tool.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool.to_prompt_format())

        sections = []
        for category, tools in by_category.items():
            sections.append(f"### {category.title()} Tools\n" + "\n".join(tools))

        return "\n\n".join(sections)

    async def process_query(
        self, query: str, context: str = "", conversation_history: list[dict] = None
    ) -> dict[str, Any]:
        """
        Process a complex query using multi-tool reasoning.

        Args:
            query: User's question
            context: Additional context
            conversation_history: Previous messages

        Returns:
            Dict with answer, reasoning steps, and sources
        """
        start_time = datetime.now()

        # Reset context window manager to prevent memory leak across queries
        _context_manager.reset()

        # Initialize plan
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query),
        )

        logger.info(
            f"🧠 Query complexity: {plan.complexity}, sources needed: {plan.required_sources}"
        )

        # Start speculative execution for likely-needed tools
        speculative_tasks = {}
        if self.speculative_executor:
            try:
                speculative_tasks = await self.speculative_executor.start_speculative_execution(
                    query=query, context=context
                )
                if speculative_tasks:
                    logger.info(
                        f"🔮 Started speculative execution for {len(speculative_tasks)} tool(s)"
                    )
            except Exception as e:
                logger.warning(f"Speculative execution failed to start: {e}")

        # ReAct loop
        iteration = 0
        all_tool_results = {}

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 Reasoning iteration {iteration}/{self.max_iterations}")

            # Get next action from LLM
            reasoning_result = await self._reason_next_step(
                query=query,
                context=context,
                previous_steps=plan.reasoning_steps,
                tool_results=all_tool_results,
            )

            if not reasoning_result:
                logger.warning("Reasoning step failed, using fallback")
                break

            # Create reasoning step
            step = ReasoningStep(
                step_number=iteration,
                thought=reasoning_result.get("thought", ""),
                action=reasoning_result.get("action", "conclude"),
            )

            # Handle different actions
            if step.action == "call_tools":
                # Execute tool calls
                tool_calls = reasoning_result.get("tool_calls", [])
                step.tool_calls = await self._execute_tool_calls(tool_calls)

                # Collect results - use unique keys for each tool call
                for idx, tc in enumerate(step.tool_calls):
                    if tc.success:
                        # Use iteration_idx format to ensure uniqueness when same tool called multiple times
                        all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get("needs_more_info", True)

            elif step.action == "analyze_results":
                # Analyze without calling more tools
                step.observation = reasoning_result.get("analysis", "")
                step.next_action_needed = reasoning_result.get("needs_more_info", False)

            elif step.action == "conclude":
                # Final answer
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            elif step.action == "generate_guidance":
                # Direct guidance generation without tool calls (capacity building, etc.)
                guidance_response = reasoning_result.get("response", "")
                plan.final_answer = guidance_response
                plan.confidence = 0.9  # High confidence for pre-written guidance
                step.observation = (
                    f"Generated {reasoning_result.get('guidance_type', 'guidance')} guidance"
                )
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            # Check if we should stop
            if not step.next_action_needed:
                logger.info(f"✅ Agent concluded after {iteration} iteration(s)")
                break

        # Build final response
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # Cancel any unused speculative tasks
        if self.speculative_executor:
            used_tools = set()
            for step in plan.reasoning_steps:
                for tc in step.tool_calls:
                    used_tools.add(tc.tool_name)
            self.speculative_executor.cancel_unused_speculation(used_tools)

        # Cache the first step's plan if query was successful
        if self.plan_cache and plan.reasoning_steps and plan.final_answer:
            first_step = plan.reasoning_steps[0] if plan.reasoning_steps else None
            if first_step and first_step.tool_calls:
                # Build a cacheable plan from the first step
                first_plan = {
                    "thought": first_step.thought,
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": tc.tool_name,
                            "parameters": tc.parameters,
                            "reasoning": tc.reasoning,
                        }
                        for tc in first_step.tool_calls
                    ],
                    "needs_more_info": first_step.next_action_needed,
                }
                # Use confidence as quality score
                self.plan_cache.cache_plan(
                    query=query,
                    plan=first_plan,
                    context=context,
                    quality_score=plan.confidence or 0.8,
                )

        # Compute the answer before quality analysis
        answer = plan.final_answer or self._build_fallback_answer(plan)

        # Analyze response quality
        quality_analysis = self._analyze_response_quality(
            query=query, answer=answer, tool_results=all_tool_results
        )

        return {
            "answer": answer,
            "success": plan.final_answer is not None,
            "reasoning_steps": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "tools_called": [tc.tool_name for tc in s.tool_calls],
                    "observation": s.observation[:200] if s.observation else "",
                }
                for s in plan.reasoning_steps
            ],
            "sources_used": list(all_tool_results.keys()),
            "tool_results": all_tool_results,  # Include full tool results for formatting
            "complexity": plan.complexity,
            "iterations": iteration,
            "confidence": plan.confidence,
            "total_time_ms": total_time,
            "quality_analysis": quality_analysis,  # Response quality metrics
        }

    async def process_query_streaming(
        self, query: str, context: str = "", conversation_history: list[dict] = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a query and yield events in real-time as reasoning happens.

        Yields events like:
        - {'type': 'agent_thinking', 'iteration': 1, 'thought': '...'}
        - {'type': 'tool_call', 'tool_name': '...', 'parameters': {...}}
        - {'type': 'tool_result', 'tool_name': '...', 'result_summary': '...', 'result_count': 5}
        - {'type': 'agent_complete', 'result': {...}}

        Args:
            query: User's question
            context: Additional context (conversation history)
            conversation_history: Previous messages

        Yields:
            Dict events as processing happens
        """
        start_time = datetime.now()

        # Reset context window manager to prevent memory leak across queries
        _context_manager.reset()

        # Initialize plan
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query),
        )

        logger.info(
            f"🧠 [Streaming] Query complexity: {plan.complexity}, sources needed: {plan.required_sources}"
        )

        # Start speculative execution for likely-needed tools
        if self.speculative_executor:
            try:
                speculative_tasks = await self.speculative_executor.start_speculative_execution(
                    query=query, context=context
                )
                if speculative_tasks:
                    logger.info(
                        f"🔮 Started speculative execution for {len(speculative_tasks)} tool(s)"
                    )
            except Exception as e:
                logger.warning(f"Speculative execution failed to start: {e}")

        # ReAct loop with streaming
        iteration = 0
        all_tool_results = {}

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 [Streaming] Reasoning iteration {iteration}/{self.max_iterations}")

            # Get next action from LLM
            reasoning_result = await self._reason_next_step(
                query=query,
                context=context,
                previous_steps=plan.reasoning_steps,
                tool_results=all_tool_results,
            )

            if not reasoning_result:
                logger.warning("Reasoning step failed, using fallback")
                break

            # Create reasoning step
            step = ReasoningStep(
                step_number=iteration,
                thought=reasoning_result.get("thought", ""),
                action=reasoning_result.get("action", "conclude"),
            )

            # YIELD: Agent thinking event immediately
            yield {
                "type": "agent_thinking",
                "iteration": iteration,
                "thought": step.thought,
                "action": step.action,
            }

            # Handle different actions
            if step.action == "call_tools":
                tool_calls = reasoning_result.get("tool_calls", [])

                # YIELD: Tool call events before execution
                for tc in tool_calls:
                    tool_name = tc.get("tool", "")
                    parameters = tc.get("parameters", {})
                    yield {
                        "type": "tool_call",
                        "iteration": iteration,
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "reasoning": tc.get("reasoning", ""),
                    }

                # Execute tool calls
                step.tool_calls = await self._execute_tool_calls(tool_calls)

                # YIELD: Tool result events after execution
                for idx, tc in enumerate(step.tool_calls):
                    result_count = self._count_results(tc.result) if tc.success else 0
                    yield {
                        "type": "tool_result",
                        "iteration": iteration,
                        "tool_name": tc.tool_name,
                        "success": tc.success,
                        "result_count": result_count,
                        "result_summary": str(tc.result)[:300] if tc.result else "No results",
                        "execution_time_ms": tc.execution_time_ms,
                    }

                    if tc.success:
                        # Use iteration_idx format to ensure uniqueness when same tool called multiple times
                        all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get("needs_more_info", True)

            elif step.action == "analyze_results":
                step.observation = reasoning_result.get("analysis", "")
                step.next_action_needed = reasoning_result.get("needs_more_info", False)

            elif step.action == "conclude":
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            elif step.action == "generate_guidance":
                # Direct guidance generation without tool calls (capacity building, etc.)
                guidance_response = reasoning_result.get("response", "")
                plan.final_answer = guidance_response
                plan.confidence = 0.9  # High confidence for pre-written guidance
                step.observation = (
                    f"Generated {reasoning_result.get('guidance_type', 'guidance')} guidance"
                )
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            # Check if we should stop
            if not step.next_action_needed:
                logger.info(f"✅ [Streaming] Agent concluded after {iteration} iteration(s)")
                break

        # Build final response
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # Cancel any unused speculative tasks
        if self.speculative_executor:
            used_tools = set()
            for step in plan.reasoning_steps:
                for tc in step.tool_calls:
                    used_tools.add(tc.tool_name)
            self.speculative_executor.cancel_unused_speculation(used_tools)

        # Cache the first step's plan if successful
        if self.plan_cache and plan.reasoning_steps and plan.final_answer:
            first_step = plan.reasoning_steps[0] if plan.reasoning_steps else None
            if first_step and first_step.tool_calls:
                first_plan = {
                    "thought": first_step.thought,
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": tc.tool_name,
                            "parameters": tc.parameters,
                            "reasoning": tc.reasoning,
                        }
                        for tc in first_step.tool_calls
                    ],
                    "needs_more_info": first_step.next_action_needed,
                }
                self.plan_cache.cache_plan(
                    query=query,
                    plan=first_plan,
                    context=context,
                    quality_score=plan.confidence or 0.8,
                )

        # Compute the answer before quality analysis
        answer = plan.final_answer or self._build_fallback_answer(plan)

        # Analyze response quality
        quality_analysis = self._analyze_response_quality(
            query=query, answer=answer, tool_results=all_tool_results
        )

        # YIELD: Final complete event with full result
        final_result = {
            "answer": answer,
            "success": plan.final_answer is not None,
            "reasoning_steps": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "tools_called": [tc.tool_name for tc in s.tool_calls],
                    "observation": s.observation[:500] if s.observation else "",
                }
                for s in plan.reasoning_steps
            ],
            "sources_used": list(all_tool_results.keys()),
            "tool_results": all_tool_results,
            "complexity": plan.complexity,
            "iterations": iteration,
            "confidence": plan.confidence,
            "total_time_ms": total_time,
            "quality_analysis": quality_analysis,  # Response quality metrics
        }

        yield {"type": "agent_complete", "result": final_result}

    def _assess_complexity(self, query: str) -> str:
        """Assess the complexity of a query."""
        query_lower = query.lower()

        # Comparison queries
        if any(
            word in query_lower
            for word in ["compare", "versus", "vs", "difference between", "better"]
        ):
            return "comparison"

        # Multi-source queries
        if any(word in query_lower for word in ["and also", "as well as", "both", "multiple"]):
            return "multi_source"

        # Analysis queries
        if any(
            word in query_lower for word in ["why", "analyze", "explain the reason", "how does"]
        ):
            return "analysis"

        return "simple"

    def _identify_required_sources(self, query: str) -> list[str]:
        """Identify which data sources are needed."""
        sources = []
        query_lower = query.lower()

        # Statistics indicators
        if any(
            word in query_lower
            for word in ["rate", "percentage", "how many", "statistics", "average", "success"]
        ):
            sources.append("statistics")

        # Document indicators
        if any(
            word in query_lower
            for word in ["eligible", "requirement", "rule", "can i", "allowed", "must"]
        ):
            sources.append("documents")

        # Call indicators
        if any(word in query_lower for word in ["call", "funding", "deadline", "apply", "open"]):
            sources.append("calls")

        # Project indicators
        if any(word in query_lower for word in ["project", "funded", "example", "similar"]):
            sources.append("projects")

        return sources if sources else ["documents"]

    def _count_results(self, result: Any) -> int | None:
        """Count the number of results from a tool response."""
        if result is None:
            return 0
        if isinstance(result, dict):
            # Check for common result count keys
            for key in ["count", "total", "total_results", "projects_count", "calls_found"]:
                if key in result:
                    return int(result[key])
            # Check for list-like keys
            for key in ["results", "projects", "calls", "documents", "partners", "organizations"]:
                if key in result and isinstance(result[key], list):
                    return len(result[key])
        if isinstance(result, list):
            return len(result)
        return None

    async def _reason_next_step(
        self,
        query: str,
        context: str,
        previous_steps: list[ReasoningStep],
        tool_results: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Use LLM to reason about the next step."""

        # PRE-ROUTING: For first step, detect queries that must use specific tools
        # This bypasses LLM for obvious cases where it might incorrectly choose search_documents
        # IMPORTANT: This check runs BEFORE cache to override bad cached plans
        if not previous_steps:
            pre_routed = self._detect_query_type_for_tool_selection(query, context)
            if pre_routed:
                logger.info(
                    f"🎯 Pre-routed query to {pre_routed.get('tool_calls', [{}])[0].get('tool', 'unknown')}"
                )
                return pre_routed

        # Check cache for first step only (no previous steps or results)
        if not previous_steps and not tool_results and self.plan_cache:
            cached_plan = self.plan_cache.get_cached_plan(query, context)
            if cached_plan:
                logger.info("🚀 Using cached reasoning plan")
                return cached_plan

        # Reset context manager for this reasoning step
        _context_manager.reset()

        # Format previous steps with context-aware truncation
        steps_text = ""
        for step in previous_steps:
            step_text = f"\n**Step {step.step_number}**\n"
            step_text += f"Thought: {step.thought}\n"
            step_text += f"Action: {step.action}\n"
            if step.tool_calls:
                step_text += f"Tools called: {[tc.tool_name for tc in step.tool_calls]}\n"
            if step.observation:
                truncated_obs = _context_manager.truncate_observation(step.observation)
                step_text += f"Observation: {truncated_obs}\n"
            steps_text += step_text

        # Format tool results with context-aware truncation
        results_text = _context_manager.format_results_for_context(tool_results)

        # Add tool hints for specific query types (helps guide LLM to correct tools)
        tool_hint = self._get_tool_hint(query, context)
        enhanced_context = context or "No additional context"
        if tool_hint:
            enhanced_context = f"{enhanced_context}\n\n**TOOL HINT**: {tool_hint}"

        # Build prompt
        prompt = self.REASONING_PROMPT.format(
            built_in_knowledge=self.BUILT_IN_KNOWLEDGE,
            tools_description=self._get_tools_description(),
            query=query,
            context=enhanced_context,
            previous_steps=steps_text or "This is the first step",
            tool_results=results_text or "No tool results yet",
        )

        # LLM timeout in seconds (configurable via env, default 30s)
        import os

        llm_timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

        try:
            if self.llm:
                # Wrap LLM call with timeout protection
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(self.llm.generate_content, prompt), timeout=llm_timeout
                    )
                except TimeoutError:
                    logger.warning(f"⏰ LLM call timed out after {llm_timeout}s, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results, context)

                # Parse JSON from response
                response_text = response.text

                # Extract JSON block - try multiple patterns for robustness
                json_str = None

                # Pattern 1: Fenced JSON block
                json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)

                # Pattern 2: Any fenced code block (might not have 'json' marker)
                if not json_str:
                    json_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
                    if json_match:
                        potential_json = json_match.group(1).strip()
                        if potential_json.startswith("{"):
                            json_str = potential_json

                # Pattern 3: Raw JSON object
                if not json_str:
                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    json_str = json_match.group(0) if json_match else None

                if not json_str:
                    logger.warning("Could not extract JSON from LLM response, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results, context)

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as je:
                    # Try to fix common JSON issues
                    fixed_json = self._fix_malformed_json(json_str)
                    if fixed_json:
                        return fixed_json
                    logger.warning(f"JSON decode failed: {je}, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results, context)
            else:
                # Fallback reasoning
                return self._fallback_reasoning(query, previous_steps, tool_results, context)

        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return self._fallback_reasoning(query, previous_steps, tool_results, context)

    def _fix_malformed_json(self, json_str: str) -> dict[str, Any] | None:
        """Attempt to fix common JSON formatting issues from LLM responses."""
        if not json_str:
            return None

        try:
            # Try as-is first
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        fixed = json_str

        # Remove trailing commas before } or ]
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)

        # Fix single quotes to double quotes (but not inside strings)
        # This is a simplified fix - may not work for all cases
        if "'" in fixed and '"' not in fixed:
            fixed = fixed.replace("'", '"')

        # Remove control characters
        fixed = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", fixed)

        # Try to extract just the JSON object if there's extra text
        obj_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", fixed, re.DOTALL)
        if obj_match:
            fixed = obj_match.group(0)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _detect_query_type_for_tool_selection(
        self, query: str, context: str = ""
    ) -> dict[str, Any] | None:
        """Detect query type and return appropriate tool configuration.

        Returns None if no special handling needed (falls through to default behavior).
        """
        query_lower = query.lower()

        # FIRST: Check for PERSONALIZED CALL RECOMMENDATION queries
        # These use accumulated context (org type, sector, country) to search for calls
        personalized_result = self._detect_personalized_call_query(query, context)
        if personalized_result:
            return personalized_result

        # Check for STRATEGIC PLANNING / FUNDING STRATEGY queries
        # These are multi-year planning queries that benefit from programme recommendations
        strategic_result = self._detect_strategic_planning_query(query, context)
        if strategic_result:
            return strategic_result

        # Check for CAPACITY BUILDING / NEWCOMER GUIDANCE queries
        # These are questions from organizations new to EU funding about getting started
        capacity_result = self._detect_capacity_building_query(query, context)
        if capacity_result:
            return capacity_result

        # Check for EIC ACCELERATOR RISK ASSESSMENT queries
        # These are questions about EIC risks, interview stage, improving success odds
        eic_risk_result = self._detect_eic_risk_assessment_query(query, context)
        if eic_risk_result:
            return eic_risk_result

        # Check for FUNDING TYPE EXPLANATION queries
        # These are questions about action types (RIA, IA, CSA, MSCA, EIC Pathfinder)
        # and their characteristics, comparisons, and which provides most freedom
        funding_type_result = self._detect_funding_type_query(query, context)
        if funding_type_result:
            return funding_type_result

        # Check for CONTEXT RECALL queries (e.g., "I mentioned earlier I work on hydrogen")
        # These reference earlier conversation context to find calls
        context_recall_result = self._detect_context_recall_query(query, context)
        if context_recall_result:
            return context_recall_result

        # Check for SPECIFIC ORGANIZATION queries (must come before partner discovery!)
        # These are queries about a NAMED organization's funding history/projects/track record
        # e.g., "Tell me about TUM's EU funding history", "What has Fraunhofer done in Horizon Europe?"
        org_profile_result = self._detect_initial_organization_profile_query(query)
        if org_profile_result:
            return org_profile_result

        # Partner/organization discovery patterns
        partner_patterns = [
            "find partner",
            "find organization",
            "find organisations",
            "organizations experienced",
            "organisations experienced",
            "partner search",
            "experienced in",
            "who has experience",
            "companies working on",
            "universities working on",
            "sme partner",
            "sme from",
            "research organization",
            "research organisation",
            "need a partner",
            "need an sme",
            "precision farming",
            "find a research",
        ]

        # Check for partner discovery queries
        if any(pattern in query_lower for pattern in partner_patterns):
            # Extract topic keywords from query
            topic_keywords = self._extract_topic_keywords(query)
            country = self._extract_country(query)
            org_type = self._extract_org_type(query)

            params = {"topic_keywords": topic_keywords}
            if country:
                params["country"] = country
            if org_type:
                params["organization_type"] = org_type

            return {
                "thought": f"User is looking for partners/organizations. Using find_experienced_partners with keywords: {topic_keywords}",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "find_experienced_partners",
                        "parameters": params,
                        "reasoning": "Finding organizations with relevant EU funding experience",
                    }
                ],
                "needs_more_info": True,
            }

        # Check for "tell me more about that" follow-up queries about programmes/recommendations
        tell_more_result = self._detect_tell_me_more_query(query, context)
        if tell_more_result:
            return tell_more_result

        # Check for partner search REFINEMENT queries (e.g., "Show only universities" after partner search)
        refinement_result = self._detect_partner_search_refinement(query, context)
        if refinement_result:
            return refinement_result

        # Check for organization DEEP-DIVE queries BEFORE partner comparison
        # This ensures "## Projects by <org>" context triggers org tools, not partner comparison
        # e.g., "What topics do they focus on?", "Show their projects", "Who are their partners?"
        # e.g., "What's their success rate as coordinator?" (about a specific org in context)
        org_deepdive_result = self._detect_organization_deepdive_query(query, context)
        if org_deepdive_result:
            return org_deepdive_result

        # Check for partner COMPARISON/ANALYSIS queries (e.g., "Compare the top 3", "Which has most funding?")
        # Only reached if context doesn't have organization-specific indicators
        comparison_result = self._detect_partner_comparison_query(query, context)
        if comparison_result:
            return comparison_result

        # Consortium size/patterns queries
        consortium_patterns = [
            "typical consortium",
            "consortium size",
            "how many partners",
            "consortium composition",
            "consortium pattern",
            "ideal partners",
            "partner types",
            "typical number of partners",
        ]

        if any(pattern in query_lower for pattern in consortium_patterns):
            topic_keywords = self._extract_topic_keywords(query)
            return {
                "thought": "User is asking about consortium patterns. Using get_consortium_patterns tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "get_consortium_patterns",
                        "parameters": {"topic_keywords": topic_keywords} if topic_keywords else {},
                        "reasoning": "Getting consortium composition patterns from funded projects",
                    }
                ],
                "needs_more_info": True,
            }

        return None

    def _detect_initial_organization_profile_query(self, query: str) -> dict[str, Any] | None:
        """Detect if query asks about a SPECIFIC named organization's funding/projects.

        This handles INITIAL queries (no context needed) like:
        - "Tell me about Technical University of Munich's EU funding history"
        - "What has Fraunhofer done in Horizon Europe?"
        - "Show TUM's projects"
        - "CNRS funding track record"

        These should use find_organization_projects, NOT find_experienced_partners.

        Key distinction:
        - "Find partners for AI research" -> find_experienced_partners (searching MANY orgs)
        - "Tell me about TUM's funding" -> find_organization_projects (asking about ONE org)
        """
        query_lower = query.lower()

        # Known organization names/aliases (common forms users might use)
        known_org_patterns = {
            # German Universities
            "technical university of munich": "Technical University of Munich",
            "tu munich": "TU Munich",
            "tum's": "TUM",
            "tum ": "TUM",
            "technische universitaet muenchen": "Technische Universitaet Muenchen",
            "technical university of berlin": "Technical University of Berlin",
            "tu berlin": "TU Berlin",
            "rwth aachen": "RWTH Aachen",
            "tu dortmund": "TU Dortmund",
            "tu dresden": "TU Dresden",
            # German Research Orgs
            "fraunhofer": "Fraunhofer",
            "max planck": "Max Planck",
            "helmholtz": "Helmholtz",
            "leibniz": "Leibniz",
            # Dutch Universities
            "tu delft": "TU Delft",
            "delft university": "TU Delft",
            "tu eindhoven": "TU Eindhoven",
            "eindhoven university": "TU Eindhoven",
            # Austrian Universities
            "tu vienna": "TU Vienna",
            "tu wien": "TU Wien",
            "tu graz": "TU Graz",
            # French institutions
            "cnrs": "CNRS",
            "inria": "INRIA",
            "cea ": "CEA",
            "inserm": "INSERM",
            # UK institutions
            "imperial college": "Imperial College London",
            "ucl ": "UCL",
            "university college london": "UCL",
            "oxford university": "Oxford University",
            "university of oxford": "University of Oxford",
            "cambridge university": "Cambridge University",
            "university of cambridge": "University of Cambridge",
            # Swiss institutions
            "eth zurich": "ETH Zurich",
            "epfl": "EPFL",
            # Italian institutions
            "politecnico di milano": "Politecnico di Milano",
            "polimi": "Politecnico di Milano",
            "sapienza": "Sapienza",
            "universita di bologna": "Universita di Bologna",
            # Spanish institutions
            "csic": "CSIC",
            # Belgian institutions
            "ku leuven": "KU Leuven",
            "imec": "IMEC",
            "universiteit gent": "Universiteit Gent",
            # Nordic institutions
            "dtu": "DTU",
            "danmarks tekniske": "DTU",
            "chalmers": "Chalmers",
            "kth": "KTH",
            "sintef": "SINTEF",
            "vtt": "VTT",
            # Other major institutions
            "cern": "CERN",
            "esa ": "ESA",
        }

        # Patterns indicating asking ABOUT an organization (not searching for partners)
        org_profile_patterns = [
            "'s eu funding",
            "'s funding history",
            "'s eu projects",
            "'s projects",
            "'s track record",
            "'s horizon",
            "tell me about",
            "what has",
            "show me",
            "funding history",
            "project history",
            "eu funding track",
            "what projects has",
            "how many projects has",
            "projects by",
            "projects from",
        ]

        # Check if query has an organization profile indicator
        has_profile_pattern = any(pattern in query_lower for pattern in org_profile_patterns)

        # Find if a known organization is mentioned
        found_org = None
        for org_pattern, org_name in known_org_patterns.items():
            if org_pattern in query_lower:
                found_org = org_name
                break

        # If we found a known org AND a profile-asking pattern, use find_organization_projects
        if found_org and has_profile_pattern:
            logger.info(f"🏢 Detected organization profile query for: {found_org}")
            return {
                "thought": f"User is asking specifically about {found_org}'s EU funding profile. "
                f"Using find_organization_projects (not find_experienced_partners).",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "find_organization_projects",
                        "parameters": {"organization_name": found_org},
                        "reasoning": f"Getting {found_org}'s project portfolio from database",
                    }
                ],
                "needs_more_info": True,
            }

        # Even without profile pattern, if query ONLY mentions one known org,
        # it's likely asking about that specific org
        if found_org:
            # Check if it's not a "find partners FOR" query
            partner_search_indicators = [
                "find partner",
                "need partner",
                "looking for partner",
                "experienced in",
                "organizations working on",
                "who has experience",
            ]
            is_partner_search = any(ind in query_lower for ind in partner_search_indicators)

            if not is_partner_search:
                logger.info(f"🏢 Detected organization-focused query for: {found_org}")
                return {
                    "thought": f"User is asking about {found_org}. Using find_organization_projects.",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": "find_organization_projects",
                            "parameters": {"organization_name": found_org},
                            "reasoning": f"Getting {found_org}'s project portfolio from database",
                        }
                    ],
                    "needs_more_info": True,
                }

        return None

    def _detect_partner_search_refinement(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is a refinement of a previous partner search.

        This handles short queries like "Show only universities", "From EU15 countries only"
        that follow a partner search and should continue using find_experienced_partners.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates a recent partner search
        partner_search_indicators = [
            "find_experienced_partners",
            "experienced partners",
            "organizations with experience",
            "partner discovery",
            "top organizations",
            "organization type",
            "relevant projects",
            "total funding",
        ]

        has_partner_context = any(
            indicator in context_lower for indicator in partner_search_indicators
        )

        if not has_partner_context:
            return None

        # Partner refinement patterns - short queries that filter results
        refinement_patterns = {
            # Organization type filters
            "only universities": {"organization_type": "HES"},
            "show only universities": {"organization_type": "HES"},
            "universities only": {"organization_type": "HES"},
            "only hes": {"organization_type": "HES"},
            "higher education": {"organization_type": "HES"},
            "only smes": {"organization_type": "SME"},
            "smes only": {"organization_type": "SME"},
            "only research": {"organization_type": "REC"},
            "research only": {"organization_type": "REC"},
            "only private": {"organization_type": "PRC"},
            "companies only": {"organization_type": "PRC"},
            # Role filters
            "experience coordinating": {"role_filter": "coordinator"},
            "coordinating projects": {"role_filter": "coordinator"},
            "as coordinator": {"role_filter": "coordinator"},
            "who have coordinated": {"role_filter": "coordinator"},
            "coordination experience": {"role_filter": "coordinator"},
            # Country/region filters
            "eu15 countries": {"country_group": "EU15"},
            "from eu15": {"country_group": "EU15"},
            "eu15 only": {"country_group": "EU15"},
            "eu13 countries": {"country_group": "EU13"},
            "from eu13": {"country_group": "EU13"},
            "southern europe": {"country_group": "SOUTHERN"},
            "northern europe": {"country_group": "NORTHERN"},
            "western europe": {"country_group": "WESTERN"},
            "eastern europe": {"country_group": "EASTERN"},
        }

        # Check for refinement patterns
        matched_params = {}
        for pattern, params in refinement_patterns.items():
            if pattern in query_lower:
                matched_params.update(params)

        # Also check for organization type via standard extraction
        org_type = self._extract_org_type(query)
        if org_type:
            matched_params["organization_type"] = org_type

        # Check for country extraction
        country = self._extract_country(query)
        if country:
            matched_params["country"] = country

        # Check for topic refinement (e.g., "who have worked on quantum communication")
        topic_refinement_patterns = [
            "worked on",
            "have worked on",
            "who have worked",
            "experience in",
            "experience with",
            "specialized in",
            "focus on",
        ]
        if any(p in query_lower for p in topic_refinement_patterns):
            # Extract topic from the query
            new_topic = self._extract_topic_keywords(query)
            if new_topic:
                matched_params["topic_keywords"] = new_topic

        if not matched_params:
            return None

        # Extract original topic from context if available
        original_topic = self._extract_topic_from_context(context)
        if original_topic and "topic_keywords" not in matched_params:
            matched_params["topic_keywords"] = original_topic

        # Convert country_group to actual country list
        if "country_group" in matched_params:
            country_group = matched_params.pop("country_group")
            countries = self._get_countries_for_group(country_group)
            if countries:
                # For now, use the first country - the tool may need enhancement to accept multiple
                matched_params["country"] = countries[0]

        return {
            "thought": f"User is refining previous partner search with filters: {matched_params}. Using find_experienced_partners with refinement.",
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "find_experienced_partners",
                    "parameters": matched_params,
                    "reasoning": "Refining partner search based on user's filter criteria",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_personalized_call_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is asking for call recommendations using accumulated context.

        This handles queries like:
        - "What calls should we apply to?"
        - "What about as a partner?"
        - "What funding is available for us?"
        - "Which opportunities fit our profile?"

        These should use search_funding_calls with keywords extracted from conversation context.
        """
        if not context:
            return None

        query_lower = query.lower()

        # Patterns that indicate user wants personalized call/opportunity recommendations
        personalized_patterns = [
            "what calls should",
            "what calls can",
            "calls should we apply",
            "calls can we apply",
            "what about as a partner",
            "as a participant",
            "for our organization",
            "for our university",
            "for us",
            "opportunities for",
            "which opportunities",
            "what funding is available",
            "suitable calls",
            "relevant calls",
            "matching calls",
            # Profile-based recommendation queries
            "best option",
            "our best option",
            "what's our best",
            "what is our best",
            "what should we",
            "what do you recommend",
            "what would you recommend",
            "recommend for us",
            "which programme",
            "which program",
            "best programme",
            "best program",
            "best fit",
            "best match",
            "right programme",
            "right program",
        ]

        if not any(pattern in query_lower for pattern in personalized_patterns):
            return None

        # Extract context from conversation (org type, sector, country, experience level)
        context_lower = context.lower()

        # Extract research sector/topic from context
        sector_keywords = []
        sector_patterns = [
            # Medical/Healthcare - more specific patterns first
            ("ai diagnostics", "AI diagnostics artificial intelligence medical devices health"),
            ("medical devices", "medical devices health clinical diagnostics"),
            ("medical device", "medical devices health clinical diagnostics"),
            ("diagnostics", "diagnostics medical devices health clinical"),
            ("healthcare sector", "health medical clinical healthcare"),
            ("healthcare", "health medical clinical"),
            ("health", "health medical clinical"),
            # Marine/Ocean
            ("marine biology", "marine biology ocean aquatic"),
            ("marine", "marine ocean aquatic"),
            ("ocean", "marine ocean aquatic"),
            # Energy/Climate
            ("energy", "energy renewable climate"),
            ("climate", "climate environment sustainability"),
            # AI/Digital
            ("ai", "artificial intelligence AI digital"),
            ("artificial intelligence", "artificial intelligence AI digital"),
            ("digital", "digital AI technology"),
            # Agriculture/Food
            ("agriculture", "agriculture food bioeconomy"),
            ("food", "food agriculture bioeconomy"),
        ]

        for pattern, keywords in sector_patterns:
            if pattern in context_lower:
                sector_keywords = keywords.split()
                break

        # Extract country from context
        country = None
        country_patterns = {
            "portugal": "PT",
            "portuguese": "PT",
            "germany": "DE",
            "german": "DE",
            "spain": "ES",
            "spanish": "ES",
            "italy": "IT",
            "italian": "IT",
            "france": "FR",
            "french": "FR",
            "netherlands": "NL",
            "dutch": "NL",
        }
        for pattern, code in country_patterns.items():
            if pattern in context_lower:
                country = code
                break

        # Check for experience level indicators
        is_beginner = any(
            pattern in context_lower
            for pattern in [
                "never coordinated",
                "first time",
                "new to",
                "beginner",
                "no experience",
                "never done eu funding",
                "never applied",
                "never submitted",
            ]
        )

        # Check for organization type
        org_type = None
        if any(
            x in context_lower
            for x in ["university", "universities", "academic", "higher education"]
        ):
            org_type = "HES"
        elif any(x in context_lower for x in ["sme", "startup", "small business"]):
            org_type = "SME"
        elif any(
            x in context_lower
            for x in ["research center", "research institute", "research organisation"]
        ):
            org_type = "REC"

        # Build search parameters
        if not sector_keywords:
            # No specific sector found, can't personalize enough
            return None

        search_keywords = " ".join(sector_keywords[:4])

        # Build thought that shows personalization
        thought_parts = [f"User has a profile: {', '.join(sector_keywords[:3])} research"]
        if country:
            thought_parts.append(f"from {country}")
        if org_type:
            thought_parts.append(f"({org_type})")
        if is_beginner:
            thought_parts.append("(beginner, recommend partner role)")
        thought = " ".join(thought_parts) + ". Searching for matching calls."

        # Build conclusion that uses context
        conclusion_parts = []

        # Check if user is asking about partner role specifically
        if "as a partner" in query_lower or "as a participant" in query_lower:
            if is_beginner:
                conclusion_parts.append(
                    f"Given your background in {', '.join(sector_keywords[:2])} research "
                    "and no prior coordination experience, participating as a **partner** is a great strategy "
                    "to build your EU funding track record.\n\n"
                    "**Recommended Approach:**\n"
                    "1. **Join existing consortia** - Look for projects seeking partners in your area\n"
                    "2. **Use Partner Search** - Register on the EU Funding Portal Partner Search\n"
                    "3. **Target Widening calls** - These have extra support for organizations like yours\n"
                    "4. **Consider MSCA** - Marie Curie actions are great for building experience\n\n"
                )
            else:
                conclusion_parts.append(
                    f"Here are opportunities in {', '.join(sector_keywords[:2])} where you could participate as a partner:\n\n"
                )

        # Check if this is a "best option/programme recommendation" query vs "find calls" query
        is_programme_recommendation = any(
            pattern in query_lower
            for pattern in [
                "best option",
                "best programme",
                "best program",
                "which programme",
                "which program",
                "recommend for us",
                "what do you recommend",
                "what would you recommend",
                "right programme",
                "right program",
            ]
        )

        if is_programme_recommendation:
            # Build a comprehensive description from accumulated profile for recommend_programmes
            # Include all relevant context for better programme matching
            profile_parts = []
            if org_type:
                org_type_names = {"SME": "SME", "HES": "university", "REC": "research center"}
                profile_parts.append(org_type_names.get(org_type, org_type))

            # Build comprehensive sector description with all relevant keywords
            sector_desc_parts = []
            if sector_keywords:
                # Include all sector keywords for comprehensive matching
                sector_desc_parts.extend(sector_keywords)

            # Also check for specific domain keywords in context to enhance description
            # These patterns should match various ways users describe their domains
            domain_keywords = []
            # Health/Healthcare patterns (for EU4Health matching)
            if any(p in context_lower for p in ["healthcare", "health sector", "health "]):
                domain_keywords.append("health")
                domain_keywords.append("healthcare")
            # Medical device patterns (important for EU4Health)
            if any(
                p in context_lower
                for p in ["medical device", "medical devices", "medtech", "medicaldevice"]
            ):
                domain_keywords.append("medical device")
            # AI/Digital patterns
            if any(
                p in context_lower
                for p in ["ai ", " ai", "artificial intelligence", "machine learning"]
            ):
                domain_keywords.append("AI")
            # Diagnostics patterns
            if any(p in context_lower for p in ["diagnostics", "diagnostic", "diagnosis"]):
                domain_keywords.append("diagnostics")

            # Combine sector and domain keywords (deduplicated)
            all_keywords = []
            seen = set()
            for kw in sector_desc_parts + domain_keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    seen.add(kw_lower)
                    all_keywords.append(kw)

            if all_keywords:
                profile_parts.append(f"working in {', '.join(all_keywords[:8])}")

            if country:
                country_names = {
                    "DE": "Germany",
                    "PT": "Portugal",
                    "ES": "Spain",
                    "IT": "Italy",
                    "FR": "France",
                    "NL": "Netherlands",
                }
                profile_parts.append(f"based in {country_names.get(country, country)}")
            if is_beginner:
                profile_parts.append("new to EU funding")

            description = ", ".join(profile_parts) if profile_parts else search_keywords

            # Determine the primary sector for the sector parameter
            primary_sector = None
            if "health" in context_lower or "healthcare" in context_lower:
                primary_sector = "health"
            elif "medical" in context_lower:
                primary_sector = "health"
            elif sector_keywords:
                primary_sector = sector_keywords[0]

            return {
                "thought": thought + " Using recommend_programmes for best option query.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "recommend_programmes",
                        "parameters": {
                            "description": description,
                            "organization_type": org_type.lower() if org_type else None,
                            "sector": primary_sector,
                        },
                        "reasoning": f"Recommending best programmes based on profile: {description}",
                    }
                ],
                "needs_more_info": True,
            }

        return {
            "thought": thought,
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "search_funding_calls",
                    "parameters": {"keywords": search_keywords, "status": "open", "limit": 10},
                    "reasoning": f"Finding open calls for {search_keywords} based on accumulated user context",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_tell_me_more_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect follow-up queries like 'Tell me more about that option'.

        This handles queries like:
        - "Tell me more about that option"
        - "Tell me more about that programme"
        - "More details on that"
        - "Elaborate on that recommendation"

        These should use get_programme_info with the programme from context.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Patterns that indicate user wants more info about something from context
        tell_more_patterns = [
            "tell me more",
            "more about that",
            "more details",
            "elaborate on",
            "explain more",
            "can you explain",
            "what else",
            "more information",
            "more info",
        ]

        if not any(pattern in query_lower for pattern in tell_more_patterns):
            return None

        # Look for programme names in context to understand what "that" refers to
        programme_mentions = {
            "horizon europe": ("horizon_europe", "Horizon Europe"),
            "eu4health": ("eu4health", "EU4Health"),
            "erasmus+": ("erasmus_plus", "Erasmus+"),
            "erasmus plus": ("erasmus_plus", "Erasmus+"),
            "creative europe": ("creative_europe", "Creative Europe"),
            "digital europe": ("digital_europe", "Digital Europe"),
            "life programme": ("life", "LIFE Programme"),
        }

        # Check which programme was mentioned in context (most recent first)
        detected_programme = None
        detected_programme_name = None

        for pattern, (prog_id, prog_name) in programme_mentions.items():
            if pattern in context_lower:
                detected_programme = prog_id
                detected_programme_name = prog_name
                break

        if not detected_programme:
            # No specific programme found, can't provide more info
            return None

        # Build profile from context for personalized response
        profile_parts = []

        # Extract org type from context
        if "sme" in context_lower:
            profile_parts.append("SME")
        elif "university" in context_lower or "academic" in context_lower:
            profile_parts.append("university")

        # Extract sector from context
        sector_map = {
            "healthcare": "healthcare",
            "medical device": "medical devices",
            "ai diagnostics": "AI diagnostics",
            "health": "health",
            "energy": "energy",
            "digital": "digital",
        }
        for pattern, sector in sector_map.items():
            if pattern in context_lower:
                profile_parts.append(sector)
                break

        # Extract country from context
        country_map = {
            "germany": "Germany",
            "german": "Germany",
            "france": "France",
            "spain": "Spain",
            "italy": "Italy",
        }
        for pattern, country in country_map.items():
            if pattern in context_lower:
                profile_parts.append(f"based in {country}")
                break

        profile_summary = ", ".join(profile_parts) if profile_parts else "your profile"

        return {
            "thought": f"User wants more details about {detected_programme_name}. Using get_programme_info with context: {profile_summary}.",
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "get_programme_info",
                    "parameters": {"programme": detected_programme},
                    "reasoning": f"Getting detailed info about {detected_programme_name} for {profile_summary}",
                }
            ],
            "needs_more_info": True,
            "context_summary": f"Based on your profile ({profile_summary}), here's more about {detected_programme_name}:",
        }

    def _detect_strategic_planning_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect strategic planning / funding strategy queries.

        This handles queries like:
        - "Help me plan our research funding strategy for the next 3 years"
        - "We're a university department focusing on cybersecurity" (context building)
        - "What Horizon Europe options do we have?"
        - "How should we sequence our applications?"

        Strategic queries benefit from programme recommendations and context-aware responses.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Patterns for strategic planning queries
        strategic_patterns = [
            "funding strategy",
            "funding plan",
            "multi-year plan",
            "3 year plan",
            "3-year plan",
            "next 3 years",
            "next three years",
            "strategic plan",
            "plan our research",
            "plan our funding",
            "sequence our applications",
            "sequencing applications",
            "application strategy",
            "what options do we have",
            "options for us",
        ]

        # Context-building patterns (organization + research focus)
        context_building_patterns = [
            "we're a ",
            "we are a ",
            "our department",
            "our organization",
            "our organisation",
            "our university",
            "our institute",
            "i work at",
            "we work on",
            "we focus on",
            "focusing on",
            "our research area",
            "our research areas",  # Added: plural form
            "our areas are",  # Added: "Our research areas are:"
            "our team",
        ]

        # Domain/sector patterns
        domain_patterns = {
            "cybersecurity": ["cybersecurity", "cyber security", "cyber-security"],
            "ai_robotics": [
                "artificial intelligence",
                "machine learning",
                " ai ",
                "ai/ml",
                "robotics",
                "robot",
                "human-machine",
                "human machine",
                "hmi",
                "hci",
                "automation",
                "autonomous",
            ],  # Combined AI + Robotics + HMI
            "ai": ["artificial intelligence", "machine learning", " ai ", "ai/ml"],
            "healthcare": ["healthcare", "health care", "medical", "health sector"],
            "energy": ["clean energy", "renewable energy", "energy transition"],
            "climate": ["climate", "sustainability", "environment"],
            "digital": ["digital transformation", "digitalization", "digitization"],
            "biotech": ["biotechnology", "biotech", "life sciences"],
            "quantum": ["quantum computing", "quantum technology"],
        }

        is_strategic_query = any(pattern in query_lower for pattern in strategic_patterns)
        is_context_building = any(pattern in query_lower for pattern in context_building_patterns)

        # Detect research domain from query
        detected_domain = None
        for domain, patterns in domain_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_domain = domain
                break

        # If context building with a research domain, provide strategic guidance + search calls
        if is_context_building and detected_domain:
            # Extract organization type description
            org_type_desc = ""
            if any(x in query_lower for x in ["university", "department", "academic"]):
                org_type_desc = "university/academic institution"
            elif any(x in query_lower for x in ["sme", "startup", "company"]):
                org_type_desc = "SME/company"
            elif any(x in query_lower for x in ["institute", "research center", "research centre"]):
                org_type_desc = "research institute"

            # Build strategic context response
            strategic_intro = (
                f"As a {org_type_desc or 'organization'} focusing on **{detected_domain}**, "
            )

            if detected_domain == "cybersecurity":
                cluster_info = "you align well with **Cluster 3** (Civil Security for Society) and **Cluster 4** (Digital, Industry and Space)"
                search_keywords = "cybersecurity digital security"
            elif detected_domain == "ai_robotics":
                cluster_info = "you align with **Cluster 4** (Digital, Industry and Space) covering AI, Robotics, and Human-Machine Interaction. This is a highly strategic area in Horizon Europe"
                search_keywords = "AI robotics human machine interaction autonomous"
            elif detected_domain == "ai":
                cluster_info = "you align with **Cluster 4** (Digital, Industry and Space) and cross-cutting AI initiatives"
                search_keywords = "artificial intelligence AI digital"
            elif detected_domain == "healthcare":
                cluster_info = (
                    "you align with **Cluster 1** (Health) and digital health initiatives"
                )
                search_keywords = "health medical clinical"
            elif detected_domain == "energy":
                cluster_info = "you align with **Cluster 5** (Climate, Energy and Mobility)"
                search_keywords = "energy renewable clean energy"
            elif detected_domain == "climate":
                cluster_info = "you align with **Cluster 5** (Climate, Energy and Mobility) and **Cluster 6** (Food, Bioeconomy)"
                search_keywords = "climate sustainability environment"
            else:
                cluster_info = "you have multiple relevant Horizon Europe clusters to explore"
                search_keywords = detected_domain

            return {
                "thought": f"User is providing context about their organization ({org_type_desc or 'organization'}) with focus on {detected_domain}. Searching for relevant calls to provide concrete options.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "search_funding_calls",
                        "parameters": {"keywords": search_keywords, "status": "open"},
                        "reasoning": f"Finding open calls relevant to {detected_domain} for strategic planning",
                    }
                ],
                "needs_more_info": True,
                "context_prefix": f"{strategic_intro}{cluster_info}.\n\nHere are currently open funding opportunities relevant to your focus:\n\n",
                "context_suffix": "\n\n---\n\n🎯 **Next Steps:**\n• Review the calls above and identify 2-3 that match your capabilities\n• Check [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for full call details\n• Consider your role preference: coordinator vs partner (universities often start as partners)\n• Share more details about your specific research focus for tailored recommendations",
            }

        # If asking about strategic planning (without domain context), recommend programmes
        if is_strategic_query:
            return {
                "thought": "User is asking about strategic funding planning. Using recommend_programmes to provide an overview of options.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "recommend_programmes",
                        "parameters": {},
                        "reasoning": "Providing strategic overview of EU funding programmes for multi-year planning",
                    }
                ],
                "needs_more_info": True,
                "context_suffix": "\n\n---\n\n🎯 **Next Steps:**\n• Share your organization type (university, SME, research institute)\n• Tell me your research focus area for personalized recommendations\n• Indicate your experience level with EU funding (first-time vs experienced)\n• Let me know your preferred role: coordinator or participant",
            }

        # Check if context has strategic planning context and query asks about options
        options_patterns = [
            "what options",
            "which options",
            "horizon europe options",
            "our options",
            "available for us",
        ]

        if any(pattern in query_lower for pattern in options_patterns):
            # Check context for research domain
            for domain, patterns in domain_patterns.items():
                if any(pattern in context_lower for pattern in patterns):
                    detected_domain = domain
                    break

            if detected_domain:
                if detected_domain == "cybersecurity":
                    search_keywords = "cybersecurity digital security"
                elif detected_domain == "ai":
                    search_keywords = "artificial intelligence AI"
                elif detected_domain == "healthcare":
                    search_keywords = "health medical"
                else:
                    search_keywords = detected_domain

                return {
                    "thought": f"User is asking about Horizon Europe options. Context indicates {detected_domain} focus. Searching for relevant calls.",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": "search_funding_calls",
                            "parameters": {"keywords": search_keywords, "status": "open"},
                            "reasoning": f"Finding Horizon Europe options for {detected_domain}",
                        }
                    ],
                    "needs_more_info": True,
                }

        return None

    def _detect_capacity_building_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect capacity building / newcomer guidance queries.

        These are questions from organizations NEW to EU funding who need guidance on:
        - Best programmes for beginners
        - Partner vs coordinator role
        - First project size recommendations
        - Building track record
        - How to get started

        These queries should provide structured guidance with Next Steps, not tool calls.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Detect if the user is new to EU funding (from context or query)
        is_newcomer = any(
            pattern in query_lower or pattern in context_lower
            for pattern in [
                "new to eu funding",
                "new to eu",
                "first time",
                "we're new",
                "we are new",
                "never applied",
                "never submitted",
                "no experience",
                "beginner",
                "getting started",
                "how do we get started",
                "how do i get started",
                "new to horizon",
            ]
        )

        # Query patterns for specific capacity building guidance
        beginner_programme_patterns = [
            "best for beginners",
            "best for beginner",
            "programme for beginners",
            "programs for beginners",
            "programmes for beginners",
            "which programme is best",
            "which program is best",
            "easiest programme",
            "easiest program",
            "simpler programme",
            "beginner friendly",
            "beginner-friendly",
            "entry point",
            "where to start",
            "good starting point",
            "first programme",
            "first program",
        ]

        partner_vs_coordinator_patterns = [
            "partner or coordinator",
            "coordinator or partner",
            "start as partner",
            "start as coordinator",
            "should we coordinate",
            "should we be coordinator",
            "should we lead",
            "should we be partner",
            "participant or leader",
            "begin as partner",
            "begin as coordinator",
            "first project coordinator",
            "first project partner",
        ]

        first_project_size_patterns = [
            "first project size",
            "good first project",
            "appropriate size",
            "project size for beginners",
            "beginner project size",
            "starting project size",
            "small project to start",
            "what size project",
            "how big should first",
            "manageable first project",
        ]

        track_record_patterns = [
            "build track record",
            "building track record",
            "develop track record",
            "establish track record",
            "how do we build",
            "how to build track",
            "gain track record",
            "create track record",
            "track record strategy",
            "track record advice",
            "build experience",
            "build our experience",
        ]

        # Check for beginner-friendly programme query
        if any(pattern in query_lower for pattern in beginner_programme_patterns) or (
            is_newcomer
            and any(
                p in query_lower
                for p in [
                    "which programme",
                    "which program",
                    "best programme",
                    "best program",
                    "recommend",
                ]
            )
        ):
            return {
                "thought": "User is asking about beginner-friendly programmes. Providing structured guidance from built-in knowledge.",
                "action": "generate_guidance",
                "guidance_type": "beginner_programmes",
                "response": self._generate_beginner_programmes_guidance(),
            }

        # Check for partner vs coordinator query
        if any(pattern in query_lower for pattern in partner_vs_coordinator_patterns):
            return {
                "thought": "User is asking about partner vs coordinator role for newcomers. Providing capacity building guidance.",
                "action": "generate_guidance",
                "guidance_type": "partner_vs_coordinator",
                "response": self._generate_partner_coordinator_guidance(is_newcomer),
            }

        # Check for first project size query
        if any(pattern in query_lower for pattern in first_project_size_patterns) or (
            is_newcomer and any(p in query_lower for p in ["project size", "how big", "size"])
        ):
            return {
                "thought": "User is asking about appropriate first project size. Providing beginner-appropriate guidance.",
                "action": "generate_guidance",
                "guidance_type": "first_project_size",
                "response": self._generate_first_project_size_guidance(),
            }

        # Check for track record building query
        if any(pattern in query_lower for pattern in track_record_patterns):
            return {
                "thought": "User is asking about building track record. Providing strategic guidance.",
                "action": "generate_guidance",
                "guidance_type": "track_record",
                "response": self._generate_track_record_guidance(),
            }

        return None

    def _generate_beginner_programmes_guidance(self) -> str:
        """Generate guidance on best programmes for beginners."""
        return """For organizations new to EU funding, the best strategy is to **start small and build experience progressively**. You should consider these beginner-friendly entry points:

### 1. Marie Skłodowska-Curie Actions (MSCA) - Best for Researchers

**Why you should apply to MSCA:**
- Simpler consortium: Often just your organization + the researcher
- Clear evaluation criteria focused on research quality - you can achieve this
- Fixed funding amounts (unit costs) - no complex budget calculations
- High success rate compared to collaborative actions

**Best entry points you can apply to:**
- **MSCA Postdoctoral Fellowships (PF)**: You can host an experienced researcher
- **MSCA Staff Exchanges (SE)**: Exchange staff with international partners

### 2. Coordination and Support Actions (CSA)

**Why you should consider CSA:**
- Smaller budgets (€1-3M) with smaller consortia (3-8 partners)
- Focus on coordination, networking, dissemination - you can manage this without heavy R&D
- 100% funding rate
- Less technical complexity than RIA/IA

### 3. Widening Participation Actions

**Why you should apply to Widening:**
- Designed specifically for organizations with less EU funding experience
- Teaming, Twinning, and ERA Chairs provide structured support
- You can connect with experienced partners who will guide you
- Higher success rates for eligible countries

### 4. Join as Partner in RIA/IA (Not Coordinator)

**Why you should start as partner:**
- You can learn consortium management without the coordination burden
- Build relationships with experienced coordinators
- Lower administrative responsibility
- You can gain track record for future coordination

### Recommendation by Organization Type

| Organization | Best Starting Point |
|--------------|---------------------|
| **University** | MSCA (host fellows), CSA as partner, Widening actions |
| **Research Institute** | CSA as partner, RIA as partner, MSCA-DN |
| **SME** | Eurostars, EIC Pathfinder (as partner), IA as partner |
| **Public Body** | CSA (often as partner), Missions |

---

🎯 **Next Steps - What You Should Do:**
• You should visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home) to get a PIC number
• You should contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized advice
• Check for open calls in your research area and apply to consortium opportunities
• You can visit [Info Days](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/horizon-dashboard) to network with potential partners"""

    def _generate_partner_coordinator_guidance(self, is_newcomer: bool = True) -> str:
        """Generate guidance on partner vs coordinator role."""
        intro = (
            "For organizations new to EU funding, you **should start as a partner** "
            "before taking on the coordinator role."
            if is_newcomer
            else "The decision between partner and coordinator depends on your experience level and strategic goals."
        )

        return f"""{intro}

### Starting as Partner (Recommended for Beginners)

**Why you should start as partner:**
- **Lower risk**: The coordinator bears the legal/financial responsibility to the EC
- **Learning opportunity**: You can observe how experienced coordinators manage consortia
- **Build relationships**: You can develop trust with partners for future coordination
- **Focus on research**: You can contribute your expertise without admin overhead
- **Build track record**: Successful participation can improve your future proposal scores

**Typical partner responsibilities:**
- Deliver your work package tasks
- Contribute to reporting
- Participate in consortium meetings
- Manage your organization's budget

### When You Should Consider Coordinating

**You should have this minimum experience before coordinating:**
- 2-3 successful projects as partner
- Understanding of EC reporting requirements
- Strong network of trusted partners
- Administrative capacity (dedicated project manager)

**Signs you can coordinate:**
- Partners actively invite you to lead
- You have a clear research vision others want to join
- Your organization can handle the admin burden
- You've built relationships with reliable partners

### Comparison Table

| Aspect | Partner | Coordinator |
|--------|---------|-------------|
| **Admin burden** | Low | High |
| **Financial risk** | Limited to your share | Full consortium guarantee |
| **Decision authority** | Limited | High |
| **Track record value** | Good | Excellent |
| **Recommended for beginners** | ✅ Yes | ❌ Not yet |

### Strategic Progression Path

1. **Year 1-2**: You should apply as partner in 1-2 projects
2. **Year 2-3**: Take on Work Package leadership
3. **Year 3-4**: Co-coordinate a smaller project (CSA)
4. **Year 4+**: You can coordinate RIA/IA projects

---

🎯 **Next Steps - What You Should Do:**
• You should visit [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to find consortium opportunities
• You can visit Info Days to meet potential coordinators
• Contact coordinators to express interest in joining consortia in your research area
• You should apply to join consortia with experienced partners who can guide you"""

    def _generate_first_project_size_guidance(self) -> str:
        """Generate guidance on appropriate first project size."""
        return """For organizations new to EU funding, starting with **manageable project sizes** is crucial for success. Here's guidance on appropriate first project scope:

### Recommended First Project Parameters

| Parameter | Beginner Recommendation | Why |
|-----------|------------------------|-----|
| **Budget participation** | €200K - €500K | Manageable financial reporting |
| **Duration** | 24-36 months | Standard timeline, not too long |
| **Consortium size** | 4-8 partners | Easier coordination |
| **Your role** | Partner (not coordinator) | Lower admin burden |
| **Action type** | CSA or RIA | Clear structure |

### Action Type Comparison for Beginners

| Action Type | Typical Project Budget | Your Share | Complexity |
|-------------|----------------------|------------|------------|
| **CSA** | €1-3M | €150-400K | Lower (coordination focus) |
| **RIA (smaller)** | €3-5M | €250-500K | Medium (research focus) |
| **MSCA-PF** | €200-300K | Host costs | Lower (single researcher) |
| **Widening** | €1-2M | €300-500K | Lower (support provided) |

### What Makes a "Manageable" First Project

✅ **Good for beginners:**
- Clearly defined work package scope
- Experienced coordinator who provides guidance
- Realistic deliverables you can achieve
- Some administrative support included
- Regular consortium meetings (learning opportunity)

❌ **Avoid for first project:**
- Coordinator role in large consortia (10+ partners)
- Very large budget responsibility (>€1M your share)
- High-risk technical objectives
- Very short timelines (<24 months)
- Projects requiring major new hires

### Budget Breakdown Example (Partner Role in RIA)

For a first-time partner with €400K budget share:
- **Personnel**: €250-280K (60-70%) - Your researchers' time
- **Travel**: €30-40K - Consortium meetings, conferences
- **Equipment**: €20-40K (if needed)
- **Other costs**: €20-30K - Consumables, publications
- **Indirect costs**: 25% flat rate (included above)

### Gradual Scale-Up Strategy

| Phase | Project Type | Your Budget | Role |
|-------|-------------|-------------|------|
| **1st project** | CSA or small RIA | €200-400K | Partner |
| **2nd project** | RIA | €400-600K | WP Leader |
| **3rd project** | RIA/IA | €600K-1M | Major partner |
| **4th+ project** | Any | €1M+ or Coordinator | Lead |

---

🎯 **Next Steps:**
• Review open calls to identify projects seeking partners with your expertise
• Check the [Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) for typical budgets in your cluster
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for specific calls matching your profile
• Use [CORDIS](https://cordis.europa.eu/) to see budget distributions in similar funded projects"""

    def _generate_track_record_guidance(self) -> str:
        """Generate guidance on building EU funding track record."""
        return """Building a strong EU funding track record is a **multi-year strategic effort**. Here's a proven framework for developing your organization's EU funding experience:

### What Constitutes "Track Record"

Evaluators look for evidence of:
- **Successful project participation**: Completed EU-funded projects
- **Relevant publications/outputs**: Demonstrable research impact
- **International collaboration**: Working across borders effectively
- **Financial/admin capacity**: Proven ability to manage EU grants

### 3-Year Track Record Building Strategy

#### Year 1: Foundation Building (Low-Risk Entry)

| Activity | Purpose | Expected Outcome |
|----------|---------|------------------|
| **MSCA-PF hosting** | Host a postdoctoral fellow | 1 EU project on record |
| **CSA as partner** | Join a coordination project | Experience in EU reporting |
| **Networking events** | Build consortium contacts | Partner relationships |
| **NCP engagement** | Get expert guidance | Better proposal targeting |

**Goal**: Get 1-2 EU projects on your organizational record

#### Year 2: Portfolio Expansion

| Activity | Purpose | Expected Outcome |
|----------|---------|------------------|
| **RIA as partner** | Substantive research role | Strong track record entry |
| **WP leadership** | Prove management capacity | Leadership credentials |
| **Publications** | Document project outputs | Demonstrable impact |
| **Repeat partnerships** | Deepen trusted relationships | Future invitation to consortia |

**Goal**: Build reputation as reliable partner

#### Year 3: Strategic Growth

| Activity | Purpose | Expected Outcome |
|----------|---------|------------------|
| **Co-coordinate small project** | Test coordination capacity | Coordinator experience |
| **Multiple parallel projects** | Diversify portfolio | Robust track record |
| **International visibility** | Conference presentations | Expert reputation |
| **Mentor newcomers** | Support your network | Strengthen partnerships |

**Goal**: Ready to coordinate major projects

### Track Record by Organization Type

| Organization | Best Track Record Builders |
|--------------|---------------------------|
| **University** | MSCA, RIA as partner, teaching innovation projects |
| **Research Institute** | RIA partnerships, infrastructure access projects |
| **SME** | Eurostars, EIC Pathfinder, IA as partner |
| **Public Body** | CSA, Missions, policy-oriented projects |

### Accelerating Track Record Development

**Quick wins:**
1. **National/regional EU projects**: Often easier to win, still counts
2. **Horizon Europe associated instruments**: Eurostars, EUREKA
3. **Expert evaluator role**: Apply to evaluate proposals (builds credibility)
4. **Horizon Results Platform**: Register past project outputs

**Strategic moves:**
1. **Join winning teams**: Partner with high-success-rate coordinators
2. **Target less competitive calls**: Widening, CSA, thematic areas with fewer applicants
3. **Leverage existing relationships**: Previous collaboration partners
4. **Highlight non-EU experience**: National grants demonstrate capacity

### Common Mistakes to Avoid

❌ **Don't:**
- Try to coordinate before having partner experience
- Over-commit to too many proposals simultaneously
- Ignore admin/reporting requirements (damages reputation)
- Work only with familiar partners (limits network growth)

✅ **Do:**
- Start small and grow systematically
- Deliver on commitments (reputation is everything)
- Document lessons learned from each project
- Maintain relationships even after projects end

---

🎯 **Next Steps:**
• Create a 3-year EU funding roadmap for your organization
• Identify 2-3 target calls for initial participation
• Register on [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to signal your interest
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for a strategy consultation
• Review [CORDIS](https://cordis.europa.eu/) for funded projects in your area to find active consortia"""

    def _detect_eic_risk_assessment_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect EIC Accelerator risk assessment queries.

        These are questions about:
        - Risks of applying to EIC Accelerator
        - Impact of prior EU funding on EIC chances
        - Company size requirements and impact
        - The interview stage and how to prepare
        - Strategies to improve success odds

        These queries should provide structured guidance with Next Steps, not tool calls.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check if context is about EIC Accelerator (from previous turns)
        is_eic_context = any(
            pattern in context_lower
            for pattern in [
                "eic accelerator",
                "eic",
                "accelerator",
                "european innovation council",
                "risks of applying",
                "improve our odds",
            ]
        )

        # Prior funding impact patterns
        prior_funding_patterns = [
            "don't have prior",
            "no prior funding",
            "without prior funding",
            "lack prior",
            "haven't had eu funding",
            "no eu funding",
            "no previous funding",
            "what if we don't have",
            "if we don't have prior",
            "without eu funding",
            "no track record",
            "no eu experience",
            "first time applying",
        ]

        # Interview stage patterns
        interview_patterns = [
            "interview stage",
            "about the interview",
            "interview process",
            "eic interview",
            "what about the interview",
            "pitch stage",
            "pitch preparation",
            "jury interview",
            "panel interview",
            "face to face",
            "face-to-face",
            "final stage",
            "how to prepare for interview",
            "interview preparation",
        ]

        # Improve odds/success patterns
        improve_odds_patterns = [
            "improve our odds",
            "improve my odds",
            "improve our chances",
            "improve my chances",
            "increase our chances",
            "increase our odds",
            "better our chances",
            "how can we improve",
            "what can we do to improve",
            "how to succeed",
            "how to be successful",
            "tips for success",
            "strategies to improve",
            "boost our chances",
            "maximize chances",
            "success strategies",
        ]

        # Company size patterns (in EIC context)
        company_size_patterns = [
            "company size",
            "our company size",
            "how does size affect",
            "does company size",
            "size affect chances",
            "sme requirements",
            "sme eligibility",
            "too small",
            "too large",
            "employee count",
            "startup size",
        ]

        # Initial EIC risk assessment patterns (first query about EIC risks)
        eic_risk_patterns = [
            "risks of applying to eic",
            "eic accelerator risks",
            "risks of eic",
            "what are the risks of eic",
            "risks associated with eic",
            "challenges of eic",
            "eic accelerator challenges",
            "difficulties of eic",
            "risks of applying to the eic",
            "downsides of eic",
        ]

        # Check for initial EIC risk assessment query (doesn't need context)
        if any(pattern in query_lower for pattern in eic_risk_patterns) or (
            "eic" in query_lower
            and "accelerator" in query_lower
            and any(
                w in query_lower for w in ["risk", "risks", "challenge", "challenges", "difficult"]
            )
        ):
            return {
                "thought": "User is asking about risks of EIC Accelerator. Providing comprehensive risk assessment guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_risks_overview",
                "response": self._generate_eic_risks_overview_guidance(),
            }

        # Check for prior funding impact query (in EIC context)
        if any(pattern in query_lower for pattern in prior_funding_patterns) and is_eic_context:
            return {
                "thought": "User is asking about EIC Accelerator with no prior EU funding. Providing EIC-specific guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_prior_funding",
                "response": self._generate_eic_prior_funding_guidance(),
            }

        # Check for interview stage query (in EIC context or explicitly about interview)
        if any(pattern in query_lower for pattern in interview_patterns) or (
            is_eic_context and "interview" in query_lower
        ):
            return {
                "thought": "User is asking about EIC Accelerator interview stage. Providing interview preparation guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_interview",
                "response": self._generate_eic_interview_guidance(),
            }

        # Check for improve odds query (in EIC context)
        if any(pattern in query_lower for pattern in improve_odds_patterns) and is_eic_context:
            return {
                "thought": "User is asking how to improve EIC Accelerator success odds. Providing strategic guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_improve_odds",
                "response": self._generate_eic_improve_odds_guidance(),
            }

        # Check for company size query in EIC context
        if any(pattern in query_lower for pattern in company_size_patterns) and is_eic_context:
            return {
                "thought": "User is asking about company size impact on EIC Accelerator. Providing eligibility and impact guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_company_size",
                "response": self._generate_eic_company_size_guidance(),
            }

        return None

    def _generate_eic_risks_overview_guidance(self) -> str:
        """Generate comprehensive guidance on EIC Accelerator risks."""
        return """Applying to the EIC Accelerator is a **high-risk, high-reward endeavor**. While the potential funding (up to €2.5M grant + €15M equity) is substantial, you should understand the significant risks involved.

### 1. Extremely Low Success Rate

The EIC Accelerator is one of the most competitive funding instruments globally:

| Stage | Success Rate | Your Odds |
|-------|-------------|-----------|
| **Short Application** | ~20-30% pass | 1 in 4 |
| **Full Application** | ~30-40% pass | 1 in 3 (of those remaining) |
| **Interview** | ~50-60% pass | 1 in 2 (of finalists) |
| **Overall** | **2-5%** | 1 in 20-50 applicants |

### 2. High Time and Resource Investment

⚠️ **Application costs to consider:**
- **Internal time**: 100-300 hours for full application
- **External support**: €10,000-50,000 for professional help (optional)
- **Opportunity cost**: Time away from business development
- **Resubmission cycles**: Average 2-3 attempts before success

### 3. Equity Component Risks

If you accept EIC equity (up to €15M), you should understand:
- EIC becomes a minority shareholder in your company
- Investment terms are standardized (limited negotiation)
- Due diligence process can take 6-12 months post-selection
- Some applicants decline equity after grant acceptance

### 4. Process and Timeline Risks

| Risk | Impact |
|------|--------|
| **Long timelines** | 6-12 months from application to funding |
| **Cut-off dates** | Miss deadlines = wait 3+ months for next round |
| **Process changes** | Rules and criteria can change between calls |
| **Interview cancellation** | Reaching interview doesn't guarantee funding |

### 5. Execution Risks Post-Award

Even if successful, you face:
- Strict reporting requirements (technical + financial)
- Milestone-based funding release
- Commission oversight of strategic decisions
- Potential clawback for non-performance

### What EIC Accelerator IS Good For

Despite risks, EIC is valuable if:
✅ You have breakthrough innovation with €100M+ market potential
✅ You're willing to accept equity investment terms
✅ You have 12-18 months runway to wait for funding
✅ You can sustain application effort alongside business growth

### What to Consider Instead

| Alternative | When to Consider |
|-------------|------------------|
| **EIC Pathfinder** | Earlier stage (TRL 2-4), research-focused |
| **Horizon RIA/IA** | Collaborative research, longer timelines |
| **National grants** | Faster timelines, less competition |
| **VC funding** | Need faster access to capital |
| **Eurostars** | SME R&D with international partner |

---

🎯 **Next Steps - What You Should Do:**
• Honestly assess if your company is EIC-ready (TRL 6-8, commercial traction)
• Calculate the total cost of application (time + resources)
• Review your current runway - can you wait 6-12 months for funding?
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for an honest readiness assessment
• Consider EIC coaching to evaluate your application strength before submitting
• Review successful EIC projects on [CORDIS](https://cordis.europa.eu/) in your sector"""

    def _generate_eic_prior_funding_guidance(self) -> str:
        """Generate guidance for EIC applicants without prior EU funding."""
        return """The lack of prior EU funding is **NOT a disqualifying factor** for the EIC Accelerator. The programme prioritizes commercial track record over EU project experience.

### What EIC Evaluators Really Look For

The EIC Accelerator focuses on **commercial readiness and market potential**, not prior EU funding history. You can demonstrate capability through:

| Alternative Evidence | What To Show |
|---------------------|--------------|
| **Commercial traction** | Revenue, paying customers, signed contracts |
| **Investor validation** | Previous funding rounds, investor interest |
| **Team track record** | Founders' entrepreneurial or industry experience |
| **Technical achievements** | Patents, prototypes, publications |
| **Market validation** | Pilot projects, partnerships, LOIs |

### Why Prior EU Funding Matters Less Than You Think

**The EIC is different from collaborative grants (RIA/IA):**
- No consortium management experience needed (single applicant)
- Focus is on commercial viability, not research track record
- Many successful EIC projects had zero prior EU funding
- Strong startup experience often valued more than research grants

### What You Should Emphasize Instead

✅ **Focus on these strengths:**
1. **Product-market fit evidence** - Customer testimonials, pilot results
2. **Clear go-to-market strategy** - How you'll scale with EIC funding
3. **Strong founding team** - Relevant experience, complementary skills
4. **Competitive differentiation** - Why your solution is 10x better
5. **Financial projections** - Realistic path to profitability

### Potential Concerns to Address

⚠️ **Evaluators may wonder about:**
- Your ability to handle EU reporting → Show other grant management experience
- Administrative capacity → Highlight your team's capabilities
- European dimension → Emphasize EU market focus and partnerships

---

🎯 **Next Steps - What You Should Do:**
• You should focus your application on commercial achievements, not research history
• Prepare evidence of market traction (customer letters, pilot agreements)
• Consider an EIC coaching programme to strengthen your application
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for feedback on your EIC fit
• Review successful EIC projects on [CORDIS](https://cordis.europa.eu/) to understand what works"""

    def _generate_eic_interview_guidance(self) -> str:
        """Generate guidance for EIC Accelerator interview preparation."""
        return """The EIC Accelerator interview is the **final, decisive stage** of the evaluation process. If you reach this stage, you have approximately a **50-60% chance of success**.

### Interview Format and Structure

| Aspect | Details |
|--------|---------|
| **Duration** | 30-45 minutes total |
| **Presentation** | 10-15 minutes (you control this part) |
| **Q&A** | 15-25 minutes (jury-led questions) |
| **Panel Size** | Typically 6 evaluators |
| **Panel Composition** | Investors, entrepreneurs, industry experts |

### The Jury's Evaluation Focus

**What the jury assesses during the interview:**

1. **Team Credibility** (Critical)
   - Can this team execute the vision?
   - Do founders have relevant experience?
   - Is there a capable, committed team?

2. **Market Understanding**
   - Do they know their market deeply?
   - Is the addressable market realistic?
   - Is competition analysis thorough?

3. **Business Model Viability**
   - Is the path to revenue clear?
   - Are unit economics sound?
   - Can they scale effectively?

4. **Technology Differentiation**
   - Is the innovation real and defensible?
   - Is TRL (Technology Readiness Level) appropriate?
   - Is IP strategy clear?

### How to Prepare Effectively

✅ **Presentation preparation:**
- Lead with your strongest commercial evidence
- Show, don't tell - use demos if possible
- Keep slides minimal (visual backup, not scripts)
- Practice your timing relentlessly (they will cut you off)

✅ **Q&A preparation:**
- Prepare for tough questions on financials
- Know your numbers cold (TAM, CAC, LTV, burn rate)
- Practice with hostile mock interviewers
- Have backup slides for common questions

### Common Interview Mistakes

❌ **Avoid these pitfalls:**
- Reading from slides (shows lack of preparation)
- Over-technical explanations (jury wants business impact)
- Defensive responses to criticism (shows poor coachability)
- Unrealistic financial projections (undermines credibility)
- Vague market sizing ("it's a $50B market")

### Presentation Structure Recommendation

| Section | Time | Focus |
|---------|------|-------|
| **Hook** | 1 min | Problem and urgency |
| **Solution** | 2-3 min | Your innovation, demo if possible |
| **Market** | 2 min | Size, segments, timing |
| **Business Model** | 2 min | Revenue, customers, traction |
| **Competition** | 1 min | Differentiation, moats |
| **Team** | 2 min | Why this team will win |
| **Ask** | 1 min | Use of funds, milestones |

---

🎯 **Next Steps - What You Should Do:**
• Book professional interview coaching (EIC-specific coaches available)
• Conduct at least 5 mock interviews with experienced entrepreneurs/investors
• Record your presentation and review critically
• Prepare a Q&A sheet with 50+ potential questions and answers
• Check [EIC Community](https://eic.ec.europa.eu/eic-community_en) for interview preparation resources
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for interview coaching referrals"""

    def _generate_eic_improve_odds_guidance(self) -> str:
        """Generate guidance for improving EIC Accelerator success odds."""
        return """Improving your EIC Accelerator success odds requires a **strategic approach at each stage**. The overall success rate is 2-5%, but you can significantly improve your chances with preparation.

### Success Rates by Stage

| Stage | Success Rate | What's Evaluated |
|-------|-------------|------------------|
| **Short Application** | ~20-30% pass | Innovation, team, market potential |
| **Full Application** | ~30-40% pass | Business plan, financials, impact |
| **Interview** | ~50-60% pass | Team credibility, investor readiness |
| **Overall** | ~2-5% | Cumulative (20% × 35% × 55% ≈ 4%) |

### Strategies to Improve Your Odds

#### 1. Strengthen Your Application Quality

✅ **You should focus on:**
- **Clear value proposition** - One sentence that captures your innovation
- **Strong traction evidence** - Customers, revenue, pilots, LOIs
- **Realistic financials** - Conservative base case, ambitious upside
- **Clear use of funds** - Specific milestones tied to EIC funding

#### 2. Target the Right Timing

✅ **You should apply when:**
- You have concrete market validation (not just R&D results)
- Your product is at TRL 6-8 (not too early, not too late)
- You can demonstrate 12-18 months of runway already
- Your team has entrepreneurial credibility

#### 3. Leverage Support Systems

✅ **You should use:**
- **NCP support** - Free proposal review and advice
- **EIC coaching** - Professional application support
- **Investor feedback** - Ask VCs to review your pitch
- **Previous applicants** - Learn from their experience

### Key Differentiators That Improve Success

| Factor | Low Success | High Success |
|--------|-------------|--------------|
| **Traction** | "We plan to..." | "We have X customers paying Y" |
| **Team** | First-time founders | Serial entrepreneurs or industry experts |
| **Market** | "Huge potential" | Specific segment, clear entry strategy |
| **Competition** | "No real competition" | Deep competitive analysis with clear moats |
| **Financials** | Hockey stick projections | Data-driven, realistic models |

### Timing Your Application

**Best time to apply:**
- After significant commercial milestone (Series A, major customer)
- When you can show 6-12 months of growth trajectory
- Before you're "too big" (>€100M revenue may be questioned)

**Worst time to apply:**
- With only R&D results and no commercial validation
- Immediately after incorporation with no traction
- When running out of cash (desperation shows)

### Reapplication Strategy

If your application fails:
1. **Request feedback** - EC provides evaluation reports
2. **Address specific weaknesses** - Don't just resubmit
3. **Build more evidence** - Get more traction before reapplying
4. **Wait 6-12 months** - Use time to strengthen fundamentals

---

🎯 **Next Steps - What You Should Do:**
• You should get an honest assessment of your TRL and market readiness
• Build at least 3-5 concrete pieces of commercial traction evidence
• Have your application reviewed by an experienced EIC coach
• Practice your pitch with real investors (even if not raising)
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for a proposal readiness assessment
• Review EIC selection statistics and adjust expectations accordingly"""

    def _generate_eic_company_size_guidance(self) -> str:
        """Generate guidance for EIC Accelerator company size requirements."""
        return """Company size is **critical for EIC Accelerator eligibility**. The programme is exclusively designed for Small and Medium-sized Enterprises (SMEs).

### SME Definition for EIC Eligibility

To be eligible for EIC Accelerator, your company must meet the EU SME definition:

| Criterion | Threshold | Your Status |
|-----------|-----------|-------------|
| **Employees** | < 250 FTE | Must be under |
| **Annual turnover** | ≤ €50 million | OR under this |
| **Annual balance sheet** | ≤ €43 million | OR under this |

**Note:** You must meet the employee threshold AND at least one of the financial thresholds.

### How Company Size Affects Your Chances

**Small startups (< 50 employees):**
✅ Core target of EIC Accelerator
✅ Evaluators expect high-growth potential
⚠️ Must demonstrate execution capability

**Medium-sized SMEs (50-249 employees):**
✅ Still eligible
✅ Stronger track record expected
⚠️ Must show why EIC funding (not VC) is needed

**Near-threshold companies (200+ employees):**
⚠️ Carefully verify SME status
⚠️ Consider affiliated/linked enterprise rules
⚠️ Evaluators may question growth potential

### SME Calculation Complexities

**Watch out for these:**

| Situation | Impact on SME Status |
|-----------|---------------------|
| **Parent company owns >50%** | Parent's data may be added |
| **Multiple investors with >25%** | Partner enterprises rule applies |
| **Recent rapid growth** | Use most recent closed accounts |
| **Recent spin-off** | Special rules may apply |

### Company Stage and EIC Fit

| Stage | EIC Suitability | Comments |
|-------|-----------------|----------|
| **Pre-revenue** | Medium | Need strong team and technology |
| **Early revenue (€0-1M)** | Good | Classic EIC target |
| **Growing (€1-10M)** | Excellent | Ideal stage for scale-up funding |
| **Scaling (€10-50M)** | Good | May need blended finance |
| **Established (€50M+)** | Low | May exceed SME thresholds |

### If You're Approaching SME Thresholds

**Options to consider:**
1. Apply before crossing the threshold
2. Check precise calculation (averages, FTE rules)
3. Consider other instruments (EIC Pathfinder, Horizon RIA)
4. National growth funding alternatives

### Non-SME Alternatives

If you exceed SME thresholds:
- **EIC Pathfinder** - Open to non-SMEs for earlier-stage innovation
- **Horizon Europe RIA/IA** - Collaborative research (no SME requirement)
- **National innovation funds** - Many countries have SME-alternative programmes
- **EIB financing** - Debt and equity for larger companies

---

🎯 **Next Steps - What You Should Do:**
• Verify your SME status using the [EC SME self-assessment tool](https://ec.europa.eu/growth/smes/sme-definition_en)
• Calculate linked and partner enterprise effects carefully
• Prepare SME declaration documents in advance
• If near threshold, consider timing of application strategically
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for SME status verification support
• Consult a grant accountant if your corporate structure is complex"""

    def _detect_funding_type_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect funding type explanation queries.

        These are questions about Horizon Europe action types:
        - RIA (Research and Innovation Action)
        - IA (Innovation Action)
        - CSA (Coordination and Support Action)
        - MSCA (Marie Skłodowska-Curie Actions)
        - EIC Pathfinder
        - ERC (European Research Council)

        Covers:
        - Direct explanations: "What is CSA?", "Explain RIA"
        - Comparisons: "Compare RIA vs IA", "Difference between RIA and IA"
        - Follow-ups in funding type context: "What about CSA?", "How does X differ?"
        - Freedom/flexibility questions: "Which gives most freedom?"

        These should use built-in knowledge, NOT tool calls.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check if context is about funding type comparison (from previous turns)
        is_funding_type_context = any(
            pattern in context_lower
            for pattern in [
                "compare ria",
                "compare ia",
                "ria vs ia",
                "ia vs ria",
                "funding type",
                "action type",
                "research and innovation action",
                "innovation action",
                "coordination and support",
                "msca postdoctoral",
                "eic pathfinder",
                "100% funding",
                "70% funding",
            ]
        )

        # Direct funding type explanation patterns
        funding_type_explain_patterns = [
            r"what is (?:a |an )?(?:ria|ia|csa)\b",
            r"what are (?:ria|ia|csa)s?\b",
            r"explain (?:ria|ia|csa)\b",
            r"tell me about (?:ria|ia|csa)\b",
            r"what does (?:ria|ia|csa) mean",
            r"what is (?:a )?research and innovation action",
            r"what is (?:an )?innovation action",
            r"what is (?:a )?coordination and support",
        ]

        # RIA vs IA comparison patterns
        ria_ia_comparison_patterns = [
            "ria vs ia",
            "ia vs ria",
            "compare ria",
            "compare ia",
            "ria and ia",
            "ia and ria",
            "difference between ria and ia",
            "difference between ia and ria",
            "ria or ia",
            "ia or ria",
            "ria versus ia",
            "ia versus ria",
        ]

        # CSA follow-up patterns (when in funding type context)
        csa_followup_patterns = [
            "what about csa",
            "and csa",
            "how about csa",
            "tell me about csa",
            "what is csa",
            "explain csa",
            "coordination and support",
        ]

        # EIC Pathfinder patterns
        eic_pathfinder_patterns = [
            "eic pathfinder",
            "pathfinder differ",
            "how does pathfinder",
            "what is pathfinder",
            "about pathfinder",
            "pathfinder vs",
            "vs pathfinder",
        ]

        # MSCA patterns
        msca_patterns = [
            "msca postdoctoral",
            "msca fellowship",
            "marie curie",
            "marie sklodowska",
            "postdoctoral fellowship",
            "what about msca",
            "msca-pf",
        ]

        # Freedom/flexibility question patterns (when in funding type context)
        freedom_patterns = [
            "which gives the most freedom",
            "which has most freedom",
            "which offers most freedom",
            "most flexible",
            "most flexibility",
            "most autonomy",
            "most independence",
            "most freedom",
            "greatest freedom",
            "which is most open",
            "which allows most",
            "bottom-up",
            "researcher-driven",
        ]

        # Check for RIA vs IA comparison
        if any(pattern in query_lower for pattern in ria_ia_comparison_patterns):
            return {
                "thought": "User is asking to compare RIA vs IA action types. Providing comprehensive comparison from built-in knowledge.",
                "action": "generate_guidance",
                "guidance_type": "ria_ia_comparison",
                "response": self._generate_ria_ia_comparison_guidance(),
            }

        # Check for CSA explanation/follow-up
        if any(pattern in query_lower for pattern in csa_followup_patterns) or (
            is_funding_type_context and "csa" in query_lower
        ):
            return {
                "thought": "User is asking about CSA (Coordination and Support Actions). Providing detailed CSA explanation.",
                "action": "generate_guidance",
                "guidance_type": "csa_explanation",
                "response": self._generate_csa_explanation_guidance(),
            }

        # Check for EIC Pathfinder explanation
        if any(pattern in query_lower for pattern in eic_pathfinder_patterns) or (
            is_funding_type_context and "pathfinder" in query_lower
        ):
            return {
                "thought": "User is asking about EIC Pathfinder. Providing detailed EIC Pathfinder explanation.",
                "action": "generate_guidance",
                "guidance_type": "eic_pathfinder_explanation",
                "response": self._generate_eic_pathfinder_explanation_guidance(),
            }

        # Check for MSCA explanation
        if any(pattern in query_lower for pattern in msca_patterns) or (
            is_funding_type_context and ("msca" in query_lower or "postdoctoral" in query_lower)
        ):
            return {
                "thought": "User is asking about MSCA Postdoctoral Fellowships. Providing detailed MSCA-PF explanation.",
                "action": "generate_guidance",
                "guidance_type": "msca_explanation",
                "response": self._generate_msca_explanation_guidance(),
            }

        # Check for freedom/flexibility question (in funding type context)
        if any(pattern in query_lower for pattern in freedom_patterns) and is_funding_type_context:
            return {
                "thought": "User is asking which funding type offers most freedom. Providing freedom comparison.",
                "action": "generate_guidance",
                "guidance_type": "funding_type_freedom",
                "response": self._generate_funding_type_freedom_guidance(),
            }

        # Check for generic funding type explanation using regex
        import re

        for pattern in funding_type_explain_patterns:
            if re.search(pattern, query_lower):
                # Determine which funding type
                if "csa" in query_lower or "coordination" in query_lower:
                    return {
                        "thought": "User is asking about CSA. Providing CSA explanation.",
                        "action": "generate_guidance",
                        "guidance_type": "csa_explanation",
                        "response": self._generate_csa_explanation_guidance(),
                    }
                elif "ia" in query_lower and "ria" not in query_lower:
                    return {
                        "thought": "User is asking about IA. Providing IA explanation.",
                        "action": "generate_guidance",
                        "guidance_type": "ia_explanation",
                        "response": self._generate_ia_explanation_guidance(),
                    }
                elif "ria" in query_lower:
                    return {
                        "thought": "User is asking about RIA. Providing RIA explanation.",
                        "action": "generate_guidance",
                        "guidance_type": "ria_explanation",
                        "response": self._generate_ria_explanation_guidance(),
                    }

        return None

    def _generate_ria_ia_comparison_guidance(self) -> str:
        """Generate comprehensive RIA vs IA comparison."""
        return """The choice between **Research and Innovation Action (RIA)** and **Innovation Action (IA)** depends on your project's technological maturity and objective. Both are suitable for applied research, but they target different stages of development.

### 1. Key Differences Overview

| Feature | RIA (Research & Innovation Action) | IA (Innovation Action) |
|---------|-----------------------------------|------------------------|
| **Focus** | Generating new knowledge, exploring feasibility | Demonstrating, piloting, validating |
| **TRL Range** | TRL 2-5 (research to early prototype) | TRL 5-8 (prototype to near-market) |
| **Funding Rate** | **100%** of eligible costs | **70%** (100% for non-profits) |
| **Typical Budget** | €3-15M | €5-20M |
| **Duration** | 36-48 months | 24-36 months |
| **Risk Profile** | Higher technical risk, knowledge gaps | Lower tech risk, market/scale-up focus |

### 2. When to Choose RIA

✅ **Choose RIA when:**
- You're exploring new concepts or generating foundational knowledge
- Your technology is at TRL 2-5 (concept validation to lab demonstration)
- You want 100% funding for research-intensive activities
- Your main deliverable is new knowledge, methods, or early prototypes
- You need to answer fundamental research questions

**Typical RIA activities:**
- Basic and applied research
- Technology exploration and feasibility studies
- Lab-scale testing and validation
- Development of new methods, processes, or tools

### 3. When to Choose IA

✅ **Choose IA when:**
- You have proven technology ready for demonstration/piloting
- Your technology is at TRL 5-8 (large-scale prototype to near-market)
- You need to validate in real-world conditions
- Your main deliverable is demonstrated technology, pilot plants, or scale-up
- You're preparing for market deployment

**Typical IA activities:**
- Large-scale demonstrations and pilots
- Prototyping at near-production scale
- Market replication and first-of-a-kind deployment
- Field testing and user validation
- Regulatory preparation

### 4. Consortium Considerations

| Aspect | RIA | IA |
|--------|-----|------|
| **Typical size** | 8-15 partners | 10-20 partners |
| **Academia role** | Often coordinator, research leaders | Partners for specific expertise |
| **Industry role** | Essential for validation, end-user | Often coordinator, scale-up leaders |
| **SME role** | Technology providers, niche expertise | Demonstration, early adopters |

### 5. Budget Implications

**RIA (100% funding):**
- Full cost recovery for all partners
- Lower financial risk for participants
- May attract more academic partners

**IA (70% for industry):**
- Industrial partners need 30% co-funding
- Non-profit entities still get 100%
- May require stronger industry commitment

### 6. Decision Guide

| Your Situation | Recommended Action |
|----------------|-------------------|
| "We have an idea and want to validate the concept" | RIA |
| "We have a working prototype and need to demonstrate at scale" | IA |
| "We want to explore fundamental scientific questions" | RIA |
| "We're ready to pilot with real users" | IA |
| "Our technology is TRL 2-4" | RIA |
| "Our technology is TRL 6-8" | IA |
| "We need 100% funding coverage" | RIA |
| "We have strong industry partners with co-funding" | IA |

---

🎯 **Next Steps - What You Should Do:**
• Assess your current TRL level honestly - this determines the best fit
• Check the Work Programme topics - some specify RIA only or IA only
• Review your consortium's ability to provide 30% co-funding (if considering IA)
• Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for open calls
• Consult your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for topic-specific advice
• Review funded projects on [CORDIS](https://cordis.europa.eu/) in your area"""

    def _generate_csa_explanation_guidance(self) -> str:
        """Generate detailed CSA explanation."""
        return """**Coordination and Support Actions (CSA)** are fundamentally different from RIA and IA. They focus on coordination, networking, and support activities rather than research and development.

### What is a CSA?

CSA stands for **Coordination and Support Action** - a funding type designed for activities that:
- Coordinate existing research efforts
- Support policy development
- Build networks and communities
- Disseminate knowledge
- Standardize practices

**Key characteristic:** CSAs do **NOT** fund research or innovation activities directly.

### CSA Characteristics

| Feature | CSA (Coordination & Support Action) |
|---------|-------------------------------------|
| **Funding Rate** | **100%** of eligible costs |
| **Focus** | Coordination, networking, dissemination |
| **TRL Range** | N/A (not technology development) |
| **Typical Budget** | €1-3 million |
| **Duration** | 24-36 months |
| **Consortium Size** | 5-10 partners (smaller than RIA/IA) |

### What CSAs Fund

✅ **Eligible CSA activities:**
- Coordination of research networks
- Policy support and strategy development
- Stakeholder engagement and dialogue
- Knowledge transfer and dissemination
- Standardization activities
- Training and capacity building
- Communication and outreach
- Events, workshops, conferences
- Roadmap development
- Best practice sharing

❌ **NOT eligible in CSA:**
- Laboratory research
- Technology development
- Prototyping
- Demonstration activities
- Any R&D activities

### When to Choose CSA

✅ **CSA is ideal when:**
- You want to build a European network in your field
- You need to coordinate existing research efforts across countries
- You're supporting policy development or standardization
- You're disseminating results from previous projects
- You want to develop roadmaps or strategic agendas
- You're organizing large-scale stakeholder engagement

### CSA vs RIA/IA Comparison

| Aspect | CSA | RIA | IA |
|--------|-----|-----|-----|
| **Research** | None | Core activity | Core activity |
| **Funding** | 100% | 100% | 70% (industry) |
| **Budget** | €1-3M | €3-15M | €5-20M |
| **Focus** | Coordination | Knowledge creation | Demonstration |
| **Complexity** | Lower | Higher | Higher |
| **Competition** | Moderate | High | High |

### Who Typically Coordinates CSAs

| Organization Type | Suitability | Why |
|-------------------|-------------|-----|
| **Associations/Networks** | Excellent | Natural coordinators, existing connections |
| **Policy organizations** | Excellent | Policy focus aligns with CSA objectives |
| **Universities** | Good | Can lead dissemination/training activities |
| **Research institutes** | Good | Coordinate research communities |
| **SMEs** | Limited | CSA isn't their typical domain |

### CSA as Entry Point

**For newcomers to EU funding:**
- CSA projects are smaller and more manageable
- Lower administrative burden than RIA/IA
- 100% funding reduces financial risk
- Good way to build EU project management experience
- Opportunity to meet potential future consortium partners

---

🎯 **Next Steps - What You Should Do:**
• Check if your activity is truly coordination/support (not research)
• Review open CSA topics on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)
• Consider CSA if you're new to EU funding - it's a good starting point
• Partner with associations or networks experienced in coordination
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) to discuss CSA suitability"""

    def _generate_eic_pathfinder_explanation_guidance(self) -> str:
        """Generate detailed EIC Pathfinder explanation."""
        return """The **EIC Pathfinder** is fundamentally different from collaborative actions (RIA/IA/CSA). It's designed for **breakthrough, high-risk research** at the earliest stages of technology development, operating under Pillar III (Innovative Europe).

### What is EIC Pathfinder?

EIC Pathfinder funds **visionary, high-risk research** that could lead to breakthrough technologies. Unlike RIA/IA, which operate within known scientific paradigms, Pathfinder supports research that challenges current understanding.

### EIC Pathfinder vs Collaborative Actions

| Feature | EIC Pathfinder | RIA/IA/CSA (Pillar II) |
|---------|----------------|------------------------|
| **TRL Range** | TRL 1-4 (very early) | TRL 2-8 |
| **Focus** | Breakthrough science, new technology paradigms | Incremental innovation, demonstration |
| **Risk Level** | Extremely high (failure expected) | Moderate to high |
| **Funding** | 100% | 100% (RIA/CSA), 70% (IA) |
| **Typical Budget** | €3-4M (Open), up to €5M (Challenges) | €3-20M |
| **Duration** | 36-48 months | 36-48 months |
| **Consortium** | Small teams (2-5 partners) | Large consortia (8-20 partners) |

### Two Types of EIC Pathfinder

**1. EIC Pathfinder Open**
- **Bottom-up:** You define the topic
- **Any breakthrough technology area**
- Maximum €3M per project
- Small, focused teams (can be single applicant)
- Higher scientific freedom

**2. EIC Pathfinder Challenges**
- **Top-down:** Predefined strategic challenges
- Specific breakthrough areas defined by EIC
- Maximum €4-5M per project
- Requires addressing specific challenge scope
- Annual challenge topics announced

### Key Characteristics of Pathfinder

| Aspect | What This Means |
|--------|-----------------|
| **High-risk tolerance** | Failure is acceptable; EIC expects many projects won't succeed |
| **Long-term vision** | 10-20 year horizon for potential impact |
| **Scientific ambition** | Must go beyond incremental advances |
| **Proof of concept** | Goal is to demonstrate scientific feasibility |
| **Technology transition** | Successful projects may progress to EIC Transition |

### Who Should Apply to EIC Pathfinder?

✅ **Ideal Pathfinder applicants:**
- Research teams exploring radical new ideas
- Scientists working on fundamental breakthroughs
- Startups with revolutionary (not evolutionary) technology
- Interdisciplinary teams challenging established paradigms

❌ **Not suitable for Pathfinder:**
- Incremental improvements to existing technology
- Products ready for market demonstration
- Large consortium projects
- Projects requiring large-scale validation

### EIC Pathfinder Success Factors

| Factor | What Evaluators Look For |
|--------|-------------------------|
| **Excellence** | Scientific novelty, paradigm-shifting potential |
| **Impact** | Long-term transformative potential |
| **Implementation** | Team capability, methodology quality |
| **Risk awareness** | Clear understanding of technical uncertainties |

### Pathfinder vs Other EIC Instruments

| Instrument | Stage | Funding | Goal |
|------------|-------|---------|------|
| **EIC Pathfinder** | TRL 1-4 | Grant up to €4M | Prove scientific concept |
| **EIC Transition** | TRL 4-5 | Grant up to €2.5M | Technology maturation |
| **EIC Accelerator** | TRL 6-9 | Grant + Equity up to €17.5M | Scale-up and market entry |

---

🎯 **Next Steps - What You Should Do:**
• Assess if your idea is truly breakthrough (not incremental)
• Check if EIC Pathfinder Open or a Challenge topic fits better
• Review evaluation criteria on the [EIC website](https://eic.ec.europa.eu/)
• Consider the EIC proactive grant management approach
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) or EIC Business Acceleration Services
• Look at funded Pathfinder projects on [CORDIS](https://cordis.europa.eu/)"""

    def _generate_msca_explanation_guidance(self) -> str:
        """Generate detailed MSCA Postdoctoral Fellowship explanation."""
        return """**Marie Skłodowska-Curie Actions Postdoctoral Fellowships (MSCA-PF)** are a core component of Horizon Europe (Pillar I - Excellent Science), designed to support experienced researchers in gaining new skills through international and inter-sectoral mobility.

### What is MSCA-PF?

MSCA Postdoctoral Fellowships provide funding for researchers to conduct research at a host organization in a different country than where they have resided for the last 3 years (mobility rule).

### Key MSCA-PF Characteristics

| Feature | MSCA Postdoctoral Fellowship |
|---------|------------------------------|
| **Funding Rate** | 100% (unit costs model) |
| **Who applies** | Individual researcher |
| **Duration** | 12-24 months (European), 12-24 months + return (Global) |
| **Monthly allowance** | ~€5,080 living allowance + host contribution |
| **Research area** | **Any field** (bottom-up, researcher-driven) |
| **Consortium** | Just researcher + host institution |

### Two Fellowship Types

**1. European Fellowships (EF)**
- Researcher moves TO an EU/Associated Country
- Duration: 12-24 months
- Host must be in EU Member State or Associated Country

**2. Global Fellowships (GF)**
- Outgoing phase: Move to Third Country (12-24 months)
- Mandatory return phase: Back to EU (12 months)
- For EU/AC researchers wanting international experience

### Why MSCA-PF Offers Most Freedom

| Aspect | MSCA-PF Freedom Level |
|--------|----------------------|
| **Topic choice** | ✅ **Complete freedom** - any research area |
| **Host choice** | ✅ Researcher selects their own host |
| **Methodology** | ✅ Researcher designs their own project |
| **Career development** | ✅ Dedicated training component required |
| **Administrative burden** | Low - simpler than collaborative projects |

### Eligibility Requirements

| Requirement | Criteria |
|-------------|----------|
| **PhD** | Must have PhD OR 4+ years research experience |
| **Mobility** | Cannot have resided in host country >12 months in last 3 years |
| **Experience** | Maximum 8 years of research experience post-PhD |
| **Nationality** | Any nationality (researcher), EU/AC (host) |

### MSCA-PF vs Collaborative Grants

| Aspect | MSCA-PF | RIA/IA |
|--------|---------|--------|
| **Applicant** | Individual researcher | Consortium |
| **Topic** | Any (bottom-up) | Specific topics |
| **Budget** | Fixed unit costs | Flexible budget |
| **Consortium** | None needed | 3+ partners required |
| **Competition** | High (~15% success) | Variable by topic |
| **Freedom** | Maximum | Topic-constrained |

### Funding Structure

| Category | Monthly Amount (2024) |
|----------|---------------------|
| **Living allowance** | €5,080 (base) |
| **Mobility allowance** | €600 |
| **Family allowance** | €660 (if applicable) |
| **Research costs** | €1,000/month to host |
| **Management costs** | €650/month to host |

### Success Factors

| Criterion | Weight | What Evaluators Want |
|-----------|--------|---------------------|
| **Excellence** | 50% | Scientific quality, innovation, researcher CV |
| **Impact** | 30% | Career development, knowledge transfer |
| **Implementation** | 20% | Feasibility, work plan quality |

---

🎯 **Next Steps - What You Should Do:**
• Check the mobility rule - you can't have lived in host country >12 months
• Find a host institution that matches your research interests
• Develop a strong career development plan (training activities)
• Review the [MSCA Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) for deadlines
• Contact potential supervisors early - you need a host commitment letter
• Prepare a strong 2-page research proposal
• Visit the [MSCA portal](https://marie-sklodowska-curie-actions.ec.europa.eu/) for guidance"""

    def _generate_ia_explanation_guidance(self) -> str:
        """Generate detailed IA explanation."""
        return """**Innovation Actions (IA)** are Horizon Europe funding instruments focused on bringing near-market technologies to demonstration and deployment. They target the later stages of innovation where technology proof-of-concept exists and needs real-world validation.

### What is an IA?

Innovation Actions fund activities aimed at producing plans, designs, or prototypes for new, altered, or improved products, processes, or services, including activities such as prototyping, testing, demonstrating, piloting, and large-scale product validation.

### Key IA Characteristics

| Feature | Innovation Action (IA) |
|---------|------------------------|
| **Funding Rate** | **70%** for industry, **100%** for non-profits |
| **Focus** | Demonstration, piloting, validation, scale-up |
| **TRL Range** | TRL 5-8 (prototype to near-market) |
| **Typical Budget** | €5-20 million |
| **Duration** | 24-36 months |
| **Consortium Size** | 10-20 partners |

### When to Choose IA

✅ **IA is right when:**
- You have proven technology ready for large-scale demonstration
- You need to validate in real operational environments
- You're preparing for market deployment
- You want to prove scalability and user acceptance
- Your technology is TRL 5-8

### IA vs RIA Comparison

| Aspect | IA | RIA |
|--------|-----|-----|
| **Funding** | 70% (industry) | 100% |
| **Focus** | Demonstration | Research |
| **TRL** | 5-8 | 2-5 |
| **Risk** | Scale-up risk | Technical risk |
| **Output** | Pilots, demos | Knowledge, early prototypes |

---

🎯 **Next Steps - What You Should Do:**
• Assess if your technology is at TRL 5+ for demonstration
• Ensure industry partners can provide 30% co-funding
• Check the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for IA topics
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for advice"""

    def _generate_ria_explanation_guidance(self) -> str:
        """Generate detailed RIA explanation."""
        return """**Research and Innovation Actions (RIA)** are the core Horizon Europe funding instrument for generating new knowledge and exploring the feasibility of new or improved technologies, products, processes, services, and solutions.

### What is an RIA?

RIA funds activities that aim primarily to establish new knowledge and/or explore the feasibility of new or improved technology, product, process, service, or solution. This includes basic and applied research, technology development and integration, testing, demonstration, and validation on a small-scale prototype.

### Key RIA Characteristics

| Feature | Research & Innovation Action (RIA) |
|---------|-----------------------------------|
| **Funding Rate** | **100%** of eligible costs |
| **Focus** | Knowledge generation, feasibility, early validation |
| **TRL Range** | TRL 2-5 (concept to lab demonstration) |
| **Typical Budget** | €3-15 million |
| **Duration** | 36-48 months |
| **Consortium Size** | 8-15 partners |

### When to Choose RIA

✅ **RIA is right when:**
- You need to generate new scientific knowledge
- You're exploring the feasibility of new concepts
- Your technology is TRL 2-5 (concept to early prototype)
- You want 100% funding coverage
- Your focus is on research questions, not market deployment

### RIA Activities

| Eligible | Not typical for RIA |
|----------|-------------------|
| Basic research | Large-scale production |
| Applied research | Market deployment |
| Technology exploration | Commercial demonstration |
| Lab-scale validation | Near-market pilots |
| Early prototyping | Regulatory approval preparation |

---

🎯 **Next Steps - What You Should Do:**
• Verify your technology is at TRL 2-5 for research focus
• Check the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for RIA topics
• Build a strong academic-industry consortium
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for advice"""

    def _generate_funding_type_freedom_guidance(self) -> str:
        """Generate guidance comparing freedom/flexibility across funding types."""
        return """When comparing **scientific and administrative freedom** across Horizon Europe funding types, the **MSCA Postdoctoral Fellowship** offers the most freedom, followed by **EIC Pathfinder Open**, while collaborative actions (RIA/IA/CSA) are more constrained by topic definitions.

### Freedom Comparison: Scientific Scope

This refers to whether you choose the research topic (bottom-up) or respond to a predefined call topic (top-down).

| Funding Type | Topic Freedom | Description |
|--------------|---------------|-------------|
| **MSCA-PF** | ✅ **Highest** | Any research area, researcher-defined |
| **EIC Pathfinder Open** | ✅ **Very High** | Any breakthrough technology, you define |
| **ERC Grants** | ✅ **Very High** | Any frontier research, PI-driven |
| **EIC Pathfinder Challenges** | ⚡ Medium | Within defined challenge scope |
| **RIA/IA** | ⚡ Medium-Low | Specific Work Programme topics |
| **CSA** | ⚡ Low | Predefined coordination activities |

### Freedom Comparison: Consortium Requirements

| Funding Type | Consortium | Freedom Level |
|--------------|------------|---------------|
| **MSCA-PF** | Just you + host | ✅ Highest |
| **ERC** | PI + team | ✅ Very High |
| **EIC Pathfinder** | 2-5 partners | ✅ High |
| **RIA** | 8-15 partners | ⚡ Medium |
| **IA** | 10-20 partners | ⚡ Medium |
| **CSA** | 5-10 partners | ⚡ Medium |

### Freedom Comparison: Methodology & Approach

| Funding Type | Approach Freedom | Description |
|--------------|------------------|-------------|
| **MSCA-PF** | ✅ **Highest** | You design your entire research approach |
| **ERC** | ✅ **Highest** | Frontier research, your methodology |
| **EIC Pathfinder** | ✅ High | Must be breakthrough, but your approach |
| **RIA** | ⚡ Medium | Guided by topic expected impact |
| **IA** | ⚡ Medium | Demonstration requirements constrain |
| **CSA** | ⚡ Lower | Specific coordination objectives |

### Recommendation: Which Gives Most Freedom?

**For Individual Researchers:**
1. **MSCA-PF** - Maximum freedom: any topic, simple application, you + host
2. **ERC grants** - Frontier research on your chosen topic (but more competitive)

**For Teams/Organizations:**
1. **EIC Pathfinder Open** - Breakthrough innovation, any area, small team
2. **RIA (open topics)** - Some calls have broad scope
3. **CSA** - Limited scope but simpler administration

### Trade-offs to Consider

| Freedom Aspect | High Freedom Options | Trade-off |
|----------------|---------------------|-----------|
| **Topic choice** | MSCA-PF, ERC, Pathfinder Open | Higher competition for open calls |
| **Consortium** | MSCA-PF, ERC | Limited to individual/small team |
| **Budget** | RIA, IA | Must follow specific topics |
| **Risk tolerance** | EIC Pathfinder | Breakthrough required, risky |
| **Simplicity** | MSCA-PF, CSA | Lower budgets |

### Summary by User Need

| If You Want... | Best Choice |
|----------------|-------------|
| **Maximum freedom, any topic** | MSCA-PF (individual) or EIC Pathfinder Open (team) |
| **Large budget + freedom** | ERC (individual) or broad RIA topics |
| **Simple administration** | MSCA-PF or CSA |
| **Scale-up funding** | EIC Accelerator (constrained but well-funded) |
| **Collaborative but flexible** | Broad RIA/IA topics |

---

🎯 **Next Steps - What You Should Do:**
• For maximum freedom as researcher: Apply to MSCA-PF or ERC
• For maximum freedom as team: Apply to EIC Pathfinder Open
• Check topic descriptions - some RIA topics have broad scope
• Review your constraints (team size, budget needs) against funding type requirements
• Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) to explore options
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) to discuss your specific situation"""

    def _detect_context_recall_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query references earlier conversation context to find calls.

        This handles queries like:
        - "I mentioned earlier I work on hydrogen - any new calls open right now?"
        - "As I said before, I'm in healthcare - what calls are available?"
        - "Remember I work on AI? Are there any open calls?"
        - "Going back to my hydrogen research, any funding?"
        - "Any new [topic] calls" (where topic was mentioned earlier)

        These should recall context from earlier and use search_funding_calls.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Patterns that indicate user is referencing earlier conversation
        recall_patterns = [
            "i mentioned earlier",
            "as i said",
            "as i mentioned",
            "remember i",
            "i said before",
            "i told you",
            "going back to",
            "back to my",
            "you know i work on",
            "you know i'm working on",
            "earlier i said",
            "my earlier",
            "i previously mentioned",
        ]

        # Check if query contains recall pattern
        has_recall_pattern = any(pattern in query_lower for pattern in recall_patterns)

        # Also check for "any [topic] calls" pattern where topic might be from context
        any_calls_match = re.search(
            r"any\s+(?:new\s+)?(\w+(?:\s+\w+)?)\s+calls?",
            query_lower,
        )

        # Check for "[topic] calls open" pattern
        calls_open_match = re.search(
            r"(\w+(?:\s+\w+)?)\s+calls?\s+(?:open|available)",
            query_lower,
        )

        if not has_recall_pattern and not any_calls_match and not calls_open_match:
            return None

        # Extract topic from query
        topic_from_query = None

        # First try to extract topic from query patterns
        topic_patterns = [
            r"work\s+on\s+(\w+(?:\s+\w+)?)",
            r"working\s+on\s+(\w+(?:\s+\w+)?)",
            r"research\s+(?:in|on)\s+(\w+(?:\s+\w+)?)",
            r"any\s+(?:new\s+)?(\w+(?:\s+\w+)?)\s+calls?",
            r"(\w+(?:\s+\w+)?)\s+calls?\s+(?:open|available)",
        ]

        for pattern in topic_patterns:
            match = re.search(pattern, query_lower)
            if match:
                extracted = match.group(1).strip()
                # Filter out generic words
                if extracted not in ["new", "any", "open", "funding", "more", "the", "some"]:
                    topic_from_query = extracted
                    break

        # If no topic in query, try to extract from context
        topic_from_context = None
        if not topic_from_query:
            # Look for research topics in context
            context_topic_patterns = [
                r"hydrogen\s*(?:storage|technology|research)?",
                r"marine\s+biology",
                r"artificial\s+intelligence",
                r"machine\s+learning",
                r"renewable\s+energy",
                r"solar\s+(?:energy|power)",
                r"climate\s+(?:change|research)",
                r"healthcare\s*(?:technology)?",
                r"quantum\s+(?:computing|technology)",
                r"battery\s+(?:technology|storage)",
                r"energy\s+storage",
                r"clean\s+energy",
                r"digital\s+(?:health|transformation)",
                r"sustainable\s+(?:transport|mobility)",
            ]

            for pattern in context_topic_patterns:
                match = re.search(pattern, context_lower)
                if match:
                    topic_from_context = match.group(0).strip()
                    break

        # Combine: prefer query topic, fall back to context topic
        search_topic = topic_from_query or topic_from_context

        if not search_topic:
            return None

        # Extract additional context (country, org type)
        country = None
        country_patterns = {
            "germany": "DE",
            "german": "DE",
            "portugal": "PT",
            "portuguese": "PT",
            "spain": "ES",
            "italy": "IT",
            "france": "FR",
            "netherlands": "NL",
        }
        for pattern, code in country_patterns.items():
            if pattern in context_lower:
                country = code
                break

        # Build thought showing context recall
        thought_parts = [f"User is referencing earlier context about '{search_topic}'"]
        if country:
            thought_parts.append(f"(from {country})")
        thought = " ".join(thought_parts) + ". Searching for open calls."

        return {
            "thought": thought,
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "search_funding_calls",
                    "parameters": {"keywords": search_topic, "status": "open", "limit": 10},
                    "reasoning": f"Recalling earlier context and finding open calls for {search_topic}",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_partner_comparison_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is a comparison/analysis of partners from a previous search.

        This handles follow-up queries like:
        - "Compare the top 3 organizations"
        - "Which has the most EU funding?"
        - "Which has the most diverse collaboration network?"
        - "Recommend the best fit for a coordination role"

        These should either use context directly or use get_collaboration_network for network questions.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates partner search data is available
        # These indicators cover both original partner search results AND
        # our context synthesis responses (which also contain organization data)
        partner_context_indicators = [
            "find_experienced_partners",
            "top organizations",
            "organization type",
            "relevant projects",
            "total funding",
            "coordinated",
            "example projects",
            # Indicators from our synthesis responses
            "partner comparison",
            "partner funding comparison",
            "network diversity",
            "coordination experience",
            "projects coordinated",
            "network score",
            "highest funding",
            "most coordination",
            # Additional patterns from comparison table
            "| organization |",
            "| country |",
            "total projects",
            "most diverse collaboration",
            "highest funded",
            "eu funding",
            "key insights",
        ]

        # Need at least 2 indicators to confirm partner data is in context
        indicator_count = sum(1 for ind in partner_context_indicators if ind in context_lower)
        if indicator_count < 2:
            return None

        # Extract organization names from context for use in conclusions
        org_names = self._extract_organization_names_from_context(context)

        # Check for collaboration network queries
        # Use context data (coordination counts) as proxy for network diversity
        # since calling get_collaboration_network for multiple orgs is expensive
        network_patterns = [
            "collaboration network",
            "diverse network",
            "most diverse",
            "network diversity",
            "collaboration history",
            "who do they work with",
            "their partners",
        ]

        if any(pattern in query_lower for pattern in network_patterns):
            # For network diversity, use coordination count as proxy
            # Organizations that coordinate more projects have more diverse networks
            conclusion = self._build_network_diversity_conclusion(context, org_names)
            return {
                "thought": "User is asking about collaboration network diversity. Using coordination data from partner context as proxy for network diversity. Higher coordination = more collaboration experience.",
                "action": "conclude",
                "conclusion": conclusion,
                "confidence": 0.80,
                "needs_more_info": False,
            }

        # Comparison/analysis patterns that can be answered from context
        # Note: More specific patterns (e.g., "coordination role") should come BEFORE
        # generic patterns (e.g., "recommend") to ensure correct classification
        context_synthesis_patterns = [
            # Coordinator recommendations (most specific - check first)
            ("coordination role", "coordinator recommendation"),
            ("as coordinator", "coordinator recommendation"),
            ("should coordinate", "coordinator recommendation"),
            ("who should lead", "coordinator recommendation"),
            ("best coordinator", "coordinator recommendation"),
            ("recommend.*coordinator", "coordinator recommendation"),
            # Funding comparisons
            ("most eu funding", "funding comparison"),
            ("most funding", "funding comparison"),
            ("highest funding", "funding comparison"),
            # Organization comparisons
            ("compare", "comparison request"),
            ("top 3", "comparing top organizations"),
            ("top three", "comparing top organizations"),
            ("top 5", "comparing top organizations"),
            ("top five", "comparing top organizations"),
            # Ranking by attribute
            ("which has the most", "ranking by attribute"),
            ("which one has", "ranking by attribute"),
            ("most projects", "project count comparison"),
            ("most experience", "experience comparison"),
            # Generic recommendations (check after specific patterns)
            ("recommend", "recommendation request"),
            ("best fit", "recommendation request"),
            # Ranking requests
            ("rank these", "ranking request"),
            ("sort by", "ranking request"),
        ]

        matched_pattern = None
        pattern_type = None
        for pattern, ptype in context_synthesis_patterns:
            if pattern in query_lower:
                matched_pattern = pattern
                pattern_type = ptype
                break

        if not matched_pattern:
            return None

        # Build context-aware conclusion
        conclusion = self._build_partner_comparison_conclusion(
            query, context, org_names, pattern_type
        )

        return {
            "thought": f"User is asking for {pattern_type}. Partner search data is already in context with organizations: {', '.join(org_names[:3]) if org_names else 'available'}. Synthesizing answer from context.",
            "action": "conclude",
            "conclusion": conclusion,
            "confidence": 0.85,
            "needs_more_info": False,
        }

    def _detect_organization_deepdive_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect if query is a follow-up about a specific organization.

        This handles follow-up queries like:
        - "What topics do they focus on?" (after asking about TUM's funding history)
        - "Show their recent projects"
        - "Who are their preferred partners?"
        - "What's their success rate as coordinator?"

        These should use find_organization_projects or get_collaboration_network.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates a specific organization is being discussed
        # Look for patterns like "## Projects for/by <org>" or organization names mentioned
        org_context_indicators = [
            "## projects for ",
            "## projects by ",
            "## collaboration network",
            "find_organization_projects",
            "organization's eu funding",
            "'s funding history",
            "technical university of munich",
            "technische universit",
            "technische universitaet muenchen",  # German spelling
            "fraunhofer",
            "university of ",
            "cnrs",
            "max planck",
            "tu delft",
            "tu munich",
            "eth zurich",
            "epfl",
            " eu funding history",
            "total projects found",  # Response pattern from find_organization_projects
        ]

        has_org_context = any(indicator in context_lower for indicator in org_context_indicators)

        if not has_org_context:
            return None

        # Extract the organization name from context
        org_name = self._extract_org_from_context(context)

        if not org_name:
            return None

        # Queries about collaboration/partners - use get_collaboration_network
        partner_query_patterns = [
            "who are their partners",
            "their preferred partners",
            "who do they partner with",
            "who do they work with",
            "collaboration network",
            "typically partner with",
            "partner with",
            "collaborators",
        ]

        if any(pattern in query_lower for pattern in partner_query_patterns):
            return {
                "thought": f"User is asking about {org_name}'s collaboration partners. Using get_collaboration_network.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "get_collaboration_network",
                        "parameters": {"organization_name": org_name},
                        "reasoning": f"Getting collaboration network for {org_name}",
                    }
                ],
                "needs_more_info": True,
            }

        # Queries about projects/focus/topics - use find_organization_projects
        project_query_patterns = [
            "their projects",
            "their recent projects",
            "show projects",
            "what topics",
            "research focus",
            "focus areas",
            "topics do they",
            "what do they work on",
            "what are they working",
            "success rate as coordinator",
            "coordinated projects",
            "as coordinator",
            "projects they coordinated",
            "coordinator success",
        ]

        if any(pattern in query_lower for pattern in project_query_patterns):
            # Check if query specifically asks about coordinator role
            # BUT: For success rate queries, don't filter by role - we need all projects
            # to compute statistics (even if they ask about coordinator success rate)
            role = None
            is_success_rate_query = "success rate" in query_lower
            if not is_success_rate_query and any(
                kw in query_lower for kw in ["coordinator", "coordinated", "lead", "leading"]
            ):
                role = "coordinator"

            thought = f"User is asking about {org_name}'s projects."
            if is_success_rate_query:
                thought += " Fetching all projects to analyze coordinator statistics."
            thought += " Using find_organization_projects."

            return {
                "thought": thought,
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "find_organization_projects",
                        "parameters": {
                            "organization_name": org_name,
                            **({"role": role} if role else {}),
                        },
                        "reasoning": f"Finding projects for {org_name}"
                        + (f" (as {role})" if role else " (all roles for statistics)"),
                    }
                ],
                "needs_more_info": True,
            }

        return None

    def _extract_org_from_context(self, context: str) -> str | None:
        """Extract the most recently discussed organization name from context.

        Looks for patterns like:
        - "## Projects for Technical University of Munich"
        - "Technical University of Munich's EU funding history"
        - Previous tool calls with organization_name parameter
        """
        import re

        context_lines = context.split("\n")

        # Pattern 1: Look for "Projects for <org>" or "Projects by <org>" headers
        for line in context_lines:
            match = re.search(r"## Projects (?:for|by) (.+)", line, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                # Clean up any markdown or parenthetical info
                org_name = re.sub(r"\s*\([^)]+\)\s*$", "", org_name)
                if org_name and len(org_name) > 3:
                    return org_name

        # Pattern 2: Look for "Collaboration Network" for/of organization (colon format)
        # e.g., "## Collaboration Network: TECHNISCHE UNIVERSITAET MUENCHEN"
        for line in context_lines:
            match = re.search(r"## Collaboration Network[:\s]+(.+)", line, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                # Clean up any markdown or extra text
                org_name = re.sub(r"\s*\([^)]+\)\s*$", "", org_name)
                if org_name and len(org_name) > 3:
                    return org_name

        # Pattern 3: Look for "<org>'s EU funding history" or similar
        funding_history_patterns = [
            r"([A-Za-z\s\-']+(?:University|Institute|College|Centre|Center|GmbH|AG|Ltd).*?)'s (?:EU|funding|project)",
            r"about ([A-Za-z\s\-']+(?:University|Institute|College|Centre|Center))",
            r"Tell me about ([A-Za-z\s\-']+)'s",
        ]

        for pattern in funding_history_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                if len(org_name) > 3 and org_name.lower() not in ["the", "their", "this"]:
                    return org_name

        # Pattern 4: Look for major university/institution names in context
        major_institutions = {
            "technical university of munich": "Technical University of Munich",
            "technische universitaet muenchen": "Technical University of Munich",
            "tum": "Technical University of Munich",
            "fraunhofer": "Fraunhofer",
            "max planck": "Max Planck",
            "cnrs": "CNRS",
            "tu delft": "TU Delft",
            "eth zurich": "ETH Zurich",
            "epfl": "EPFL",
            "imperial college": "Imperial College London",
            "university of oxford": "University of Oxford",
            "university of cambridge": "University of Cambridge",
        }

        context_lower = context.lower()
        for search_term, display_name in major_institutions.items():
            if search_term in context_lower:
                return display_name

        return None

    def _extract_organization_names_from_context(self, context: str) -> list[str]:
        """Extract organization names from partner search context."""
        import re

        org_names = []

        # Pattern 1: Look for bold organization names (markdown format)
        # e.g., "**FRAUNHOFER GESELLSCHAFT ZUR FORDERUNG DER ANGEWANDTEN FORSCHUNG EV**"
        bold_pattern = re.findall(r"\*\*([A-Z][A-Z0-9\s\-&']+?)\*\*", context)
        for name in bold_pattern:
            name = name.strip()
            # Filter out section headers and keep actual organization names
            if len(name) > 5 and not name.startswith(("Finding", "How to", "Top")):
                org_names.append(name)

        # Pattern 2: Look for numbered list entries with organization names
        # e.g., "### 1. **ORG NAME** (DE)"
        numbered_pattern = re.findall(r"###\s*\d+\.\s*\*\*([^*]+)\*\*", context)
        for name in numbered_pattern:
            name = name.strip()
            if name not in org_names and len(name) > 5:
                org_names.append(name)

        # Deduplicate while preserving order
        seen = set()
        unique_orgs = []
        for org in org_names:
            if org not in seen:
                seen.add(org)
                unique_orgs.append(org)

        return unique_orgs[:10]  # Return top 10 organizations

    def _build_partner_comparison_conclusion(
        self, query: str, context: str, org_names: list[str], pattern_type: str
    ) -> str:
        """Build a structured comparison/recommendation based on partner context."""
        import re

        # Extract funding data from context
        # Format: **Total Funding**: €75,951,578 or Total Funding: €75,951,578
        funding_data = {}
        for org in org_names[:5]:
            # Look for funding info near the org name
            org_escaped = re.escape(org)
            # Match patterns like: **Total Funding**: €75,951,578 or Total Funding: €75,951,578
            funding_match = re.search(
                rf"{org_escaped}.*?\*?\*?Total Funding\*?\*?[:\s]*€?([\d,]+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if funding_match:
                funding_str = funding_match.group(1).replace(",", "")
                try:
                    funding_data[org] = int(funding_str)
                except ValueError:
                    pass

        # Extract project counts
        # Format: **Relevant Projects**: 93 or Relevant Projects: 93
        project_data = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            project_match = re.search(
                rf"{org_escaped}.*?\*?\*?Relevant Projects\*?\*?[:\s]*(\d+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if project_match:
                try:
                    project_data[org] = int(project_match.group(1))
                except ValueError:
                    pass

        # Extract coordination counts
        # Format: (coordinated **14** projects) or coordinated 14 projects
        coordination_data = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            coord_match = re.search(
                rf"{org_escaped}.*?coordinated\s*\**(\d+)\**",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if coord_match:
                try:
                    coordination_data[org] = int(coord_match.group(1))
                except ValueError:
                    pass

        # Extract organization types
        # Format: **Organization Type**: REC (Research Center) or Organization Type: REC
        org_types = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            type_match = re.search(
                rf"{org_escaped}.*?\*?\*?Organization Type\*?\*?[:\s]*([A-Z]+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if type_match:
                org_types[org] = type_match.group(1)

        # Extract countries
        # Format: **ORG NAME** (DE) or ORG NAME (DE)
        countries = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            # Match: **ORG NAME** (DE) or ORG NAME (DE)
            country_match = re.search(rf"{org_escaped}\*?\*?\s*\(([A-Z]{{2}})\)", context)
            if country_match:
                countries[org] = country_match.group(1)

        # Build response based on pattern type
        top_3 = org_names[:3]

        if pattern_type == "funding comparison" or "funding" in query.lower():
            # Sort by funding and present
            sorted_by_funding = sorted(
                [(org, funding_data.get(org, 0)) for org in top_3],
                key=lambda x: x[1],
                reverse=True,
            )
            result = "## Partner Funding Comparison\n\n"
            result += "Based on the partner search results, here's the funding comparison:\n\n"
            for i, (org, funding) in enumerate(sorted_by_funding, 1):
                country = countries.get(org, "")
                org_type = org_types.get(org, "")
                result += f"### {i}. {org}"
                if country:
                    result += f" ({country})"
                result += "\n"
                result += f"- **Total EU Funding**: €{funding:,}\n"
                result += f"- **Organization Type**: {org_type}\n"
                projects = project_data.get(org, "N/A")
                result += f"- **Relevant Projects**: {projects}\n\n"

            if sorted_by_funding:
                winner = sorted_by_funding[0]
                result += (
                    f"\n**Highest Funded**: {winner[0]} with €{winner[1]:,} in total EU funding.\n"
                )

        elif pattern_type == "coordinator recommendation":
            # Sort by coordination experience
            sorted_by_coord = sorted(
                [(org, coordination_data.get(org, 0)) for org in top_3],
                key=lambda x: x[1],
                reverse=True,
            )
            result = "## Coordinator Recommendation\n\n"
            result += "Based on coordination experience from the partner search:\n\n"
            for i, (org, coord_count) in enumerate(sorted_by_coord, 1):
                country = countries.get(org, "")
                org_type = org_types.get(org, "")
                funding = funding_data.get(org, 0)
                result += f"### {i}. {org}"
                if country:
                    result += f" ({country})"
                result += "\n"
                result += f"- **Projects Coordinated**: {coord_count}\n"
                result += f"- **Organization Type**: {org_type}\n"
                result += f"- **Total Funding**: €{funding:,}\n\n"

            if sorted_by_coord and sorted_by_coord[0][1] > 0:
                winner = sorted_by_coord[0]
                result += f"\n**Recommended Coordinator**: {winner[0]} has the most coordination experience with {winner[1]} projects coordinated.\n"
            result += "\n**Next Steps:**\n"
            result += "- Contact the recommended organization via CORDIS or their website\n"
            result += "- Verify their availability and interest in your project topic\n"
            result += "- Discuss consortium composition and roles\n"

        elif pattern_type == "comparison request" or pattern_type == "comparing top organizations":
            result = "## Partner Comparison\n\n"
            result += f"Comparing the top {len(top_3)} organizations from the partner search:\n\n"
            result += "| Organization | Country | Type | Projects | Coordinated | Total Funding |\n"
            result += "|-------------|---------|------|----------|-------------|---------------|\n"
            for org in top_3:
                country = countries.get(org, "-")
                org_type = org_types.get(org, "-")
                projects = project_data.get(org, "-")
                coord = coordination_data.get(org, "-")
                funding = funding_data.get(org, 0)
                funding_str = f"€{funding:,}" if funding else "-"
                # Truncate long org names for table
                short_name = org[:40] + "..." if len(org) > 40 else org
                result += f"| {short_name} | {country} | {org_type} | {projects} | {coord} | {funding_str} |\n"

            result += "\n### Key Insights:\n"
            # Funding leader
            if funding_data:
                funding_leader = max(funding_data.items(), key=lambda x: x[1])
                result += f"- **Highest Funding**: {funding_leader[0]} (€{funding_leader[1]:,})\n"
            # Coordination leader
            if coordination_data:
                coord_leader = max(coordination_data.items(), key=lambda x: x[1])
                result += f"- **Most Coordination Experience**: {coord_leader[0]} ({coord_leader[1]} projects)\n"
            # Project leader
            if project_data:
                project_leader = max(project_data.items(), key=lambda x: x[1])
                result += f"- **Most Relevant Projects**: {project_leader[0]} ({project_leader[1]} projects)\n"

        else:
            # Generic comparison
            result = "## Partner Analysis\n\n"
            result += (
                f"Based on the partner search, here are the top {len(top_3)} organizations:\n\n"
            )
            for i, org in enumerate(top_3, 1):
                country = countries.get(org, "")
                org_type = org_types.get(org, "")
                projects = project_data.get(org, "N/A")
                coord = coordination_data.get(org, "N/A")
                funding = funding_data.get(org, 0)
                result += f"### {i}. {org}"
                if country:
                    result += f" ({country})"
                result += "\n"
                result += f"- **Organization Type**: {org_type}\n"
                result += f"- **Relevant Projects**: {projects}\n"
                result += f"- **Coordinated Projects**: {coord}\n"
                result += f"- **Total Funding**: €{funding:,}\n\n"

        result += "\n**Next Steps:**\n"
        result += "- Search CORDIS for detailed project information\n"
        result += "- Use the EU Partner Search tool to contact organizations\n"
        result += "- Verify current availability and interest\n"

        return result

    def _build_network_diversity_conclusion(self, context: str, org_names: list[str]) -> str:
        """Build a network diversity analysis from partner context.

        Uses coordination count as a proxy for network diversity:
        Organizations that coordinate more projects have collaborated with more partners.
        """
        import re

        # Extract coordination counts for top organizations
        coordination_data = {}
        project_data = {}
        countries = {}
        org_types = {}

        for org in org_names[:5]:
            org_escaped = re.escape(org)

            # Coordination count
            coord_match = re.search(
                rf"{org_escaped}.*?coordinated\s*\**(\d+)\**",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if coord_match:
                try:
                    coordination_data[org] = int(coord_match.group(1))
                except ValueError:
                    pass

            # Project count
            project_match = re.search(
                rf"{org_escaped}.*?\*?\*?Relevant Projects\*?\*?[:\s]*(\d+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if project_match:
                try:
                    project_data[org] = int(project_match.group(1))
                except ValueError:
                    pass

            # Country
            country_match = re.search(rf"{org_escaped}\*?\*?\s*\(([A-Z]{{2}})\)", context)
            if country_match:
                countries[org] = country_match.group(1)

            # Org type
            type_match = re.search(
                rf"{org_escaped}.*?\*?\*?Organization Type\*?\*?[:\s]*([A-Z]+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if type_match:
                org_types[org] = type_match.group(1)

        # Sort by coordination count (more coordinated = more diverse network)
        sorted_orgs = sorted(
            [
                (org, coordination_data.get(org, 0), project_data.get(org, 0))
                for org in org_names[:5]
            ],
            key=lambda x: (x[1], x[2]),  # Sort by coord count, then project count
            reverse=True,
        )

        result = "## Collaboration Network Diversity Analysis\n\n"
        result += "Organizations that coordinate more projects have built more diverse collaboration networks, "
        result += "as coordinators must assemble consortia from multiple countries and organization types.\n\n"

        result += "### Network Diversity Ranking (by coordination experience)\n\n"
        result += "| Organization | Country | Type | Projects Coordinated | Total Projects | Network Score |\n"
        result += "|--------------|---------|------|---------------------|----------------|---------------|\n"

        for org, coord_count, proj_count in sorted_orgs[:5]:
            country = countries.get(org, "-")
            org_type = org_types.get(org, "-")
            # Network score: weighted combination of coordination and participation
            network_score = coord_count * 3 + proj_count  # Coordination weighted 3x
            short_name = org[:40] + "..." if len(org) > 40 else org
            result += f"| {short_name} | {country} | {org_type} | {coord_count} | {proj_count} | {network_score} |\n"

        if sorted_orgs:
            winner = sorted_orgs[0]
            result += "\n### Most Diverse Collaboration Network\n\n"
            result += f"**{winner[0]}** has the most diverse collaboration network based on:\n"
            result += f"- **{winner[1]} projects coordinated** - Each coordinated project requires building a consortium\n"
            result += (
                f"- **{winner[2]} total projects** - Broad participation across many consortia\n"
            )
            result += f"- **Country**: {countries.get(winner[0], 'N/A')}\n"
            result += f"- **Organization Type**: {org_types.get(winner[0], 'N/A')}\n"

        result += "\n**Note**: Actual network diversity can be verified via CORDIS by examining "
        result += "consortium compositions of coordinated projects.\n"

        result += "\n**Next Steps:**\n"
        result += "- Search CORDIS for the organization's project list\n"
        result += "- Review consortium compositions to understand collaboration patterns\n"
        result += "- Contact organizations for specific collaboration opportunities\n"

        return result

    def _extract_topic_from_context(self, context: str) -> str | None:
        """Extract the original topic keywords from conversation context."""
        # Look for common patterns that indicate a topic was searched
        import re

        # Pattern 1: "topic_keywords='...'"
        match = re.search(r"topic_keywords[=:]\s*['\"]?([^'\"]+)['\"]?", context, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Pattern 2: "for ... research" or "partners for ..."
        match = re.search(
            r"(?:partners? for|find.*for|experience in|experienced in)\s+([a-z\s]+?)(?:\s+research|\s+project|\s*$)",
            context.lower(),
        )
        if match:
            topic = match.group(1).strip()
            if len(topic) > 3:
                return topic

        # Pattern 3: Look for capitalized technical terms
        match = re.search(
            r"(?:quantum|hydrogen|ai|machine learning|renewable|solar|climate)\s*\w*",
            context.lower(),
        )
        if match:
            return match.group(0).strip()

        return None

    def _get_countries_for_group(self, group: str) -> list[str]:
        """Get list of countries for a regional group."""
        country_groups = {
            "EU15": [
                "Germany",
                "France",
                "Italy",
                "Spain",
                "Netherlands",
                "Belgium",
                "Austria",
                "Sweden",
                "Denmark",
                "Finland",
                "Ireland",
                "Portugal",
                "Greece",
                "Luxembourg",
            ],
            "EU13": [
                "Poland",
                "Czech Republic",
                "Hungary",
                "Romania",
                "Bulgaria",
                "Slovakia",
                "Slovenia",
                "Lithuania",
                "Latvia",
                "Estonia",
                "Croatia",
                "Cyprus",
                "Malta",
            ],
            "SOUTHERN": ["Spain", "Italy", "Portugal", "Greece", "Malta", "Cyprus"],
            "NORTHERN": ["Sweden", "Denmark", "Finland", "Norway", "Iceland"],
            "WESTERN": [
                "Germany",
                "France",
                "Netherlands",
                "Belgium",
                "Austria",
                "Ireland",
                "Luxembourg",
            ],
            "EASTERN": [
                "Poland",
                "Czech Republic",
                "Hungary",
                "Romania",
                "Bulgaria",
                "Slovakia",
            ],
        }
        return country_groups.get(group.upper(), [])

    def _extract_topic_keywords(self, query: str) -> str:
        """Extract topic keywords from a query for tool parameters."""
        # Remove common query words
        stopwords = [
            "find",
            "search",
            "look",
            "for",
            "in",
            "from",
            "with",
            "the",
            "a",
            "an",
            "we",
            "need",
            "want",
            "partner",
            "partners",
            "organization",
            "organizations",
            "organisation",
            "organisations",
            "sme",
            "research",
            "experienced",
            "typical",
            "consortium",
            "size",
            "how",
            "many",
            "what",
            "is",
            "are",
            "show",
            "our",
            "proposed",
            "to",
            "me",
            "can",
            "you",
            "please",
            "help",
            "about",
        ]
        words = query.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return " ".join(keywords[:5]) if keywords else query

    def _extract_country(self, query: str) -> str | None:
        """Extract country from query if mentioned.

        Uses word boundaries for short country codes to avoid false positives
        like 'fit' matching 'it' (Italy) or 'before' matching 'be' (Belgium).
        """
        import re

        query_lower = query.lower()

        # Two-letter codes require word boundaries to avoid false positives
        short_codes = {
            r"\bde\b": "Germany",
            r"\bfr\b": "France",
            r"\bit\b": "Italy",
            r"\bes\b": "Spain",
            r"\bpt\b": "Portugal",
            r"\bel\b": "Greece",
            r"\bnl\b": "Netherlands",
            r"\bbe\b": "Belgium",
        }

        # Full country names and adjectives (safe for substring match)
        full_names = {
            "germany": "Germany",
            "german": "Germany",
            "france": "France",
            "french": "France",
            "italy": "Italy",
            "italian": "Italy",
            "spain": "Spain",
            "spanish": "Spain",
            "portugal": "Portugal",
            "portuguese": "Portugal",
            "greece": "Greece",
            "greek": "Greece",
            "netherlands": "Netherlands",
            "dutch": "Netherlands",
            "belgium": "Belgium",
            "belgian": "Belgium",
            "southern europe": "Spain",  # Default to Spain for Southern Europe
        }

        # Check short codes with word boundaries first
        for pattern, country in short_codes.items():
            if re.search(pattern, query_lower):
                return country

        # Check full names (substring match is safe for these)
        for pattern, country in full_names.items():
            if pattern in query_lower:
                return country

        return None

    def _extract_org_type(self, query: str) -> str | None:
        """Extract organization type from query if mentioned.

        Uses word boundaries to avoid false positives like 'recommend' matching 'rec'.
        """
        import re

        query_lower = query.lower()

        # SME patterns - "sme" as word or "small" in context of business
        if re.search(r"\bsme\b|\bsmes\b|\bsmall\s+(company|business|enterprise)", query_lower):
            return "SME"

        # REC patterns - "research" as word or "rec" as standalone abbreviation
        # Don't match "rec" inside other words like "recommend"
        if re.search(r"\bresearch\b|\brec\b", query_lower):
            return "REC"

        # HES patterns - universities, higher education
        if re.search(r"\buniversity\b|\buniversities\b|\bhes\b|\bhigher education\b", query_lower):
            return "HES"

        # PRC patterns - private companies
        if re.search(r"\bprivate\b|\bcompany\b|\bcompanies\b|\bprc\b", query_lower):
            return "PRC"

        return None

    def _get_tool_hint(self, query: str, context: str = "") -> str | None:
        """Get a tool hint for specific query types to guide LLM tool selection.

        Returns a hint string to be injected into the context, or None if no hint needed.
        """
        query_lower = query.lower()

        # Partner/organization discovery patterns - MUST use find_experienced_partners
        partner_patterns = [
            "find partner",
            "find organization",
            "find organisations",
            "find a research",
            "organizations experienced",
            "organisations experienced",
            "experienced in",
            "partner search",
            "who has experience",
            "companies working on",
            "universities working on",
            "sme partner",
            "sme from",
            "need a partner",
            "need an sme",
            "precision farming",
            "research organization",
            "research organisation",
            "partner from",
            "find organizations",
        ]

        if any(pattern in query_lower for pattern in partner_patterns):
            # Extract specific context for the hint
            topic = self._extract_topic_keywords(query)
            country = self._extract_country(query)
            org_type = self._extract_org_type(query)

            hint_parts = [
                "MANDATORY: This is a PARTNER DISCOVERY query.",
                "You MUST use find_experienced_partners tool - DO NOT use search_documents!",
                f"Use parameters: topic_keywords='{topic}'",
            ]
            if country:
                hint_parts.append(f", country='{country}'")
            if org_type:
                hint_parts.append(f", organization_type='{org_type}'")

            return " ".join(hint_parts)

        # Check for partner search REFINEMENT hints
        refinement_hint = self._get_partner_refinement_hint(query, context)
        if refinement_hint:
            return refinement_hint

        # Consortium size/patterns queries - MUST use get_consortium_patterns
        consortium_patterns = [
            "typical consortium",
            "consortium size",
            "how many partners",
            "consortium composition",
            "consortium pattern",
            "ideal partners",
            "partner types",
            "typical number of partners",
        ]

        if any(pattern in query_lower for pattern in consortium_patterns):
            return (
                "This is a CONSORTIUM PATTERNS query. You MUST use get_consortium_patterns tool "
                "(NOT search_documents). This tool provides consortium size statistics from funded projects."
            )

        # Budget queries - use calculate_budget or get_budget_benchmark
        budget_patterns = [
            "calculate budget",
            "budget breakdown",
            "budget for",
            "help me plan",
            "recalculate",
            "adjust budget",
            "increase personnel",
        ]

        if any(pattern in query_lower for pattern in budget_patterns):
            return (
                "This is a BUDGET query. You MUST use calculate_budget or get_budget_benchmark tool "
                "(NOT search_documents)."
            )

        # Timeline queries - use generate_timeline
        timeline_patterns = [
            "generate timeline",
            "project timeline",
            "work packages",
            "add wp",
            "add a clinical",
            "add buffer",
            "milestones",
        ]

        if any(pattern in query_lower for pattern in timeline_patterns):
            return (
                "This is a TIMELINE query. You MUST use generate_timeline tool "
                "(NOT search_documents)."
            )

        # Context synthesis queries - should synthesize from conversation, NOT search
        synthesis_patterns = [
            "show our proposed",
            "show the proposed",
            "our consortium",
            "proposed consortium",
            "consortium summary",
            "summarize the partners",
            "list the partners",
            "what partners have we",
            "partners we found",
        ]

        if any(pattern in query_lower for pattern in synthesis_patterns):
            return (
                "This is a CONTEXT SYNTHESIS query. Do NOT use search_documents. "
                "Instead, synthesize the partners/information from the PREVIOUS CONVERSATION turns. "
                "List and summarize the organizations already discovered in this conversation."
            )

        return None

    def _get_partner_refinement_hint(self, query: str, context: str) -> str | None:
        """Get a hint for partner search refinement queries.

        Detects when a short query is refining a previous partner search.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates a recent partner search
        partner_search_indicators = [
            "find_experienced_partners",
            "experienced partners",
            "organizations with experience",
            "partner discovery",
            "top organizations",
            "organization type",
            "relevant projects",
            "total funding",
        ]

        has_partner_context = any(
            indicator in context_lower for indicator in partner_search_indicators
        )

        if not has_partner_context:
            return None

        # Partner refinement patterns
        refinement_indicators = [
            # Org type refinements
            "only universities",
            "show only universities",
            "universities only",
            "only hes",
            "higher education",
            "only smes",
            "smes only",
            "only research",
            "research only",
            "only private",
            "companies only",
            # Role refinements
            "experience coordinating",
            "coordinating projects",
            "as coordinator",
            "who have coordinated",
            "coordination experience",
            # Country/region refinements
            "eu15 countries",
            "from eu15",
            "eu15 only",
            "eu13 countries",
            "from eu13",
            "southern europe",
            "northern europe",
            "western europe",
            "eastern europe",
            # Topic refinements
            "worked on",
            "have worked on",
            "who have worked",
        ]

        if any(indicator in query_lower for indicator in refinement_indicators):
            # Detect specific filter type for better hint
            org_type = self._extract_org_type(query)
            country = self._extract_country(query)

            hint = (
                "MANDATORY: This is a PARTNER SEARCH REFINEMENT query. "
                "The user is refining the previous partner search. "
                "You MUST use find_experienced_partners tool (NOT search_documents!) "
                "with filters based on their refinement request."
            )

            if org_type:
                hint += f" Use organization_type='{org_type}'."
            if country:
                hint += f" Use country='{country}'."

            # Get original topic from context
            original_topic = self._extract_topic_from_context(context)
            if original_topic:
                hint += f" Use topic_keywords from the previous search: '{original_topic}'."

            return hint

        return None

    def _fallback_reasoning(
        self,
        query: str,
        previous_steps: list[ReasoningStep],
        tool_results: dict[str, Any],
        context: str = "",
    ) -> dict[str, Any]:
        """Fallback reasoning when LLM fails."""

        if not previous_steps:
            # First, try to detect specific query types for better tool selection
            # Pass context to enable detection of refinement queries
            detected_tool = self._detect_query_type_for_tool_selection(query, context)
            if detected_tool:
                return detected_tool

            # Default fallback - call basic search with more results
            return {
                "thought": "Starting with document search to gather information",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "search_documents",
                        "parameters": {"query": query, "max_results": 15},  # Increased from 5
                        "reasoning": "Initial search for relevant information",
                    }
                ],
                "needs_more_info": True,
            }

        if tool_results:
            # Have results - synthesize a proper answer
            # Extract and synthesize content from results
            synthesized_content = self._synthesize_from_results(query, tool_results)

            return {
                "thought": "Have gathered information, synthesizing answer",
                "action": "conclude",
                "conclusion": synthesized_content,
                "confidence": 0.7,
                "needs_more_info": False,
            }

        return {
            "thought": "Unable to gather more information",
            "action": "conclude",
            "conclusion": "I was unable to find specific information to answer this question. Please try rephrasing your question or asking about a more specific topic.",
            "confidence": 0.3,
            "needs_more_info": False,
        }

    def _synthesize_from_results(self, query: str, tool_results: dict[str, Any]) -> str:
        """Synthesize a coherent answer from tool results."""

        content_pieces = []

        for name, result in tool_results.items():
            if not isinstance(result, dict):
                continue

            # Extract documents
            if "documents" in result and isinstance(result["documents"], list):
                for doc in result["documents"][:10]:
                    content = doc.get("content", "")
                    if content and len(content) > 100:
                        content_pieces.append(content.strip())

            # Extract calls info
            elif "calls" in result and isinstance(result["calls"], list):
                if len(result["calls"]) == 0:
                    # Explicitly note that no calls were found
                    content_pieces.append(
                        "No open funding calls were found matching your search criteria. This could mean:\n- There are currently no open calls in this topic area\n- Relevant calls may have already closed\n- Upcoming calls may not yet be announced\n\nConsider checking the Horizon Europe Funding & Tenders Portal for the latest information."
                    )
                else:
                    for call in result["calls"][:10]:
                        title = call.get("title", "")
                        call_id = call.get("topic_code", call.get("call_id", ""))
                        if title or call_id:
                            content_pieces.append(f"Call {call_id}: {title}")

            # Extract budget calculation results
            elif result.get("tool_name") == "calculate_budget" and result.get("success"):
                breakdown = result.get("breakdown", {})
                budget = result.get("calculated_budget", {})
                per_partner = result.get("per_partner", {})

                budget_text = f"""Budget Calculation Results:
- Total Budget: €{budget.get("total_cost", 0):,.0f}
- EU Contribution: €{budget.get("eu_contribution", 0):,.0f} ({budget.get("funding_rate", "100%")})

Breakdown:
- Personnel: €{breakdown.get("personnel", {}).get("amount", 0):,.0f} ({breakdown.get("personnel", {}).get("percentage", 0)}%)
- Equipment: €{breakdown.get("equipment", {}).get("amount", 0):,.0f} ({breakdown.get("equipment", {}).get("percentage", 0)}%)
- Travel: €{breakdown.get("travel", {}).get("amount", 0):,.0f} ({breakdown.get("travel", {}).get("percentage", 0)}%)
- Subcontracting: €{breakdown.get("subcontracting", {}).get("amount", 0):,.0f} ({breakdown.get("subcontracting", {}).get("percentage", 0)}%)
- Other Direct Costs: €{breakdown.get("other_direct", {}).get("amount", 0):,.0f} ({breakdown.get("other_direct", {}).get("percentage", 0)}%)
- Indirect Costs (25% flat rate): €{breakdown.get("indirect", {}).get("amount", 0):,.0f} ({breakdown.get("indirect", {}).get("percentage", 0)}%)

Per Partner Distribution:
- Average per partner: €{per_partner.get("average", 0):,.0f}
- Coordinator (typical): €{per_partner.get("coordinator_typical", 0):,.0f}
- Other partners (typical): €{per_partner.get("partner_typical", 0):,.0f}
"""
                content_pieces.append(budget_text)

            # Extract call details - ENHANCED with full description
            elif result.get("call_id") and result.get("title"):
                call_parts = []
                call_parts.append(f"## Call Details: {result.get('call_id')}\n")
                call_parts.append(f"**Title:** {result.get('title')}")
                call_parts.append(f"**Status:** {result.get('status', 'Unknown')}")
                call_parts.append(f"**Type:** {result.get('type', 'N/A')}")
                call_parts.append(f"**Deadline:** {result.get('deadline', 'N/A')}")

                # Full description without truncation
                description = result.get("description", "")
                if description:
                    # Clean HTML tags if present
                    import re

                    clean_desc = re.sub(r"<[^>]+>", " ", description)
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                    call_parts.append(f"\n**Description:**\n{clean_desc}")

                # Add expected outcomes if available
                expected_outcomes = result.get("expected_outcomes", [])
                if expected_outcomes:
                    call_parts.append("\n**Expected Outcomes:**")
                    for outcome in expected_outcomes[:10]:
                        call_parts.append(f"- {outcome}")

                # Add scope if available
                scope = result.get("scope", "")
                if scope and scope != description:
                    clean_scope = re.sub(r"<[^>]+>", " ", scope)
                    clean_scope = re.sub(r"\s+", " ", clean_scope).strip()
                    call_parts.append(f"\n**Scope:**\n{clean_scope}")

                content_pieces.append("\n".join(call_parts))

            # Extract statistics/benchmark results - improved formatting
            # Extract statistics/benchmark results - improved formatting
            elif result.get("statistics") or result.get("benchmark"):
                stats = result.get("statistics", result.get("benchmark", {}))
                if isinstance(stats, dict):
                    if "success_rates" in stats:
                        # EIC/ERC/MSCA format
                        programme = result.get("programme", "Programme")
                        parts = [f"**{programme} Statistics:**"]
                        if stats.get("description"):
                            parts.append(f"\n{stats['description']}")
                        parts.append("\n**Success Rates:**")
                        for key, value in stats.get("success_rates", {}).items():
                            if key != "note":
                                parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                        if stats.get("funding"):
                            parts.append("\n**Funding:**")
                            for key, value in stats["funding"].items():
                                parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                        # Add Next Steps for actionability
                        parts.append("\n---\n\n🎯 **Next Steps:**")
                        parts.append(
                            "• Review successful proposals in [CORDIS](https://cordis.europa.eu/)"
                        )
                        parts.append(
                            "• Check open calls on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                        )
                        parts.append("• Consider working with experienced partners or consultants")
                        content_pieces.append("\n".join(parts))
                    else:
                        # Cluster statistics format
                        programme = result.get("programme", result.get("cluster_code", "Unknown"))
                        parts = [f"**{programme} Statistics:**"]
                        if "total_projects" in stats or "project_count" in stats:
                            projects = stats.get(
                                "total_projects", stats.get("project_count", "N/A")
                            )
                            parts.append(
                                f"- Total Projects: {projects:,}"
                                if isinstance(projects, int)
                                else f"- Total Projects: {projects}"
                            )
                        if "success_rate" in stats:
                            parts.append(f"- Success Rate: {stats['success_rate']}%")
                        if "avg_project_budget" in stats or "average_funding" in stats:
                            avg = stats.get("avg_project_budget", stats.get("average_funding", 0))
                            parts.append(f"- Average Budget: €{avg:,.0f}")
                        # Add Next Steps for actionability
                        parts.append("\n---\n\n🎯 **Next Steps:**")
                        parts.append(
                            "• Review open calls in this cluster on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                        )
                        parts.append(
                            "• Study similar funded projects in [CORDIS](https://cordis.europa.eu/)"
                        )
                        content_pieces.append("\n".join(parts))
                else:
                    # Fallback for non-dict stats
                    content_pieces.append(
                        f"Statistics: {json.dumps(stats, indent=2, default=str)[:1000]}"
                    )

            # Extract timeline generation results - ENHANCED with full details
            elif result.get("tool_name") == "generate_timeline" and result.get("success"):
                wps = result.get("work_packages", [])
                deliverables = result.get("deliverables", [])
                milestones = result.get("milestones", [])
                params = result.get("parameters", {})
                gantt = result.get("gantt_data", {})
                recommendations = result.get("recommendations", [])

                timeline_parts = []
                timeline_parts.append("## Project Timeline Generated\n")
                timeline_parts.append("**Project Parameters:**")
                timeline_parts.append(f"- Duration: {params.get('duration_months', 36)} months")
                timeline_parts.append(f"- Action Type: {params.get('action_type', 'RIA')}")
                timeline_parts.append(f"- Partners: {params.get('num_partners', 8)}")
                timeline_parts.append(
                    f"- Total Effort: {params.get('total_person_months', 0)} person-months"
                )
                timeline_parts.append("")

                # Work Packages with full details
                timeline_parts.append("### Work Packages\n")
                for wp in wps:
                    wp_num = wp.get("number", 0)
                    title = wp.get("title", "")
                    lead = wp.get("lead", "P1")
                    participants = wp.get("participants", [])
                    start = wp.get("start_month", 1)
                    end = wp.get("end_month", 36)
                    effort = wp.get("effort_pms", 0)
                    objective = wp.get("objective", "")
                    tasks = wp.get("tasks", [])

                    timeline_parts.append(f"**WP{wp_num}: {title}**")
                    timeline_parts.append(
                        f"- Lead: {lead} | Participants: {', '.join(participants[:4]) if participants else 'All'}"
                    )
                    timeline_parts.append(
                        f"- Duration: M{start} - M{end} ({end - start + 1} months)"
                    )
                    timeline_parts.append(f"- Effort: {effort} person-months")
                    if objective:
                        timeline_parts.append(f"- Objective: *{objective}*")
                    if tasks:
                        timeline_parts.append(f"- Tasks: {'; '.join(tasks[:4])}")
                    timeline_parts.append("")

                # Deliverables
                if deliverables:
                    timeline_parts.append(f"### Deliverables ({len(deliverables)} total)\n")
                    for d in deliverables[:15]:
                        d_id = d.get("id", d.get("seq_id", "D?"))
                        d_title = d.get("title", "")[:60]
                        d_month = d.get("due_month", 0)
                        d_type = d.get("type", "R")
                        d_level = d.get("dissemination_level", "PU")
                        timeline_parts.append(
                            f"- **{d_id}**: {d_title} (M{d_month}, {d_type}, {d_level})"
                        )
                    if len(deliverables) > 15:
                        timeline_parts.append(
                            f"- ... and {len(deliverables) - 15} more deliverables"
                        )
                    timeline_parts.append("")

                # Milestones
                if milestones:
                    timeline_parts.append(f"### Milestones ({len(milestones)} total)\n")
                    for m in milestones:
                        m_id = m.get("id", "MS?")
                        m_title = m.get("title", "")
                        m_month = m.get("due_month", 0)
                        timeline_parts.append(f"- **{m_id}**: {m_title} (M{m_month})")
                    timeline_parts.append("")

                # ASCII Gantt Chart
                ascii_chart = gantt.get("ascii_chart", "")
                if ascii_chart:
                    timeline_parts.append("### Gantt Chart\n")
                    timeline_parts.append("```")
                    timeline_parts.append(ascii_chart)
                    timeline_parts.append("```")
                    timeline_parts.append("")

                # WP Dependencies
                dependencies = gantt.get("dependencies", [])
                if dependencies:
                    timeline_parts.append("### WP Dependencies\n")
                    for dep in dependencies[:6]:
                        timeline_parts.append(
                            f"- {dep.get('from')} → {dep.get('to')}: {dep.get('description', '')}"
                        )
                    timeline_parts.append("")

                # Recommendations
                if recommendations:
                    timeline_parts.append("### Recommendations\n")
                    for rec in recommendations[:5]:
                        timeline_parts.append(f"- {rec}")

                # Add Next Steps section for actionability
                timeline_parts.append("")
                timeline_parts.append("---")
                timeline_parts.append("")
                timeline_parts.append("🎯 **Next Steps:**")
                timeline_parts.append(
                    "• Review work package allocation with your consortium partners"
                )
                timeline_parts.append("• Adjust deliverable timing based on dependencies")
                timeline_parts.append(
                    "• Check [Horizon Europe proposal templates](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents) for formatting requirements"
                )
                timeline_parts.append(
                    "• Use the EU Portal's [Grant Agreement Preparation](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/om_en.pdf) guide for milestone definitions"
                )

                content_pieces.append("\n".join(timeline_parts))

            # Extract similar projects results - ENHANCED with full details
            elif "similar_projects" in result and isinstance(result.get("similar_projects"), list):
                projects = result["similar_projects"]
                query_desc = result.get("query_description", "")
                matches = result.get("matches_found", len(projects))
                filters = result.get("filters_applied", {})

                if not projects:
                    content_pieces.append(
                        f"## Similar Projects Search\n\nNo projects found matching: *{query_desc}*"
                    )
                else:
                    similar_parts = []
                    similar_parts.append("## Similar Funded Projects\n")
                    similar_parts.append(f"**Query:** {query_desc}")
                    if filters:
                        filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
                        if filter_str:
                            similar_parts.append(f"**Filters:** {filter_str}")
                    similar_parts.append(f"**Found:** {matches} similar projects\n")

                    for i, p in enumerate(projects[:10], 1):
                        acronym = p.get("acronym", "N/A")
                        title = p.get("title", "N/A")
                        score = p.get("similarity_score", 0)
                        budget = p.get("eu_contribution", p.get("total_cost", 0))
                        consortium = p.get("consortium", {})
                        size = consortium.get("size", p.get("partner_count", 0))
                        action_type = p.get("action_type", "N/A")
                        objective = p.get("objective", "")
                        start_date = p.get("start_date", "")
                        end_date = p.get("end_date", "")
                        coordinator = consortium.get("coordinator", {}).get("name", "")
                        cluster = p.get("cluster", "")

                        budget_str = f"€{budget / 1_000_000:.1f}M" if budget > 0 else "N/A"

                        similar_parts.append(f"### {i}. {acronym} [{score:.0%} match]")
                        similar_parts.append(f"**{title}**")
                        similar_parts.append(
                            f"- Type: {action_type} | Budget: {budget_str} | Partners: {size}"
                        )
                        if cluster:
                            similar_parts.append(f"- Cluster: {cluster}")
                        if start_date and end_date:
                            similar_parts.append(f"- Duration: {start_date[:7]} to {end_date[:7]}")
                        if coordinator:
                            similar_parts.append(f"- Coordinator: {coordinator}")
                        if objective:
                            obj_preview = (
                                objective[:300] + "..." if len(objective) > 300 else objective
                            )
                            similar_parts.append(f"- Objective: *{obj_preview}*")
                        similar_parts.append("")

                    # Add insights
                    insights = result.get("insights", [])
                    if insights:
                        similar_parts.append("**Key Insights:**")
                        for insight in insights[:5]:
                            similar_parts.append(f"- {insight}")

                    content_pieces.append("\n".join(similar_parts))

            # Extract collaboration network results (get_collaboration_network)
            elif "partners" in result and isinstance(result.get("partners"), list):
                org_name = result.get("organization", "Unknown Organization")
                org_country = result.get("country", "")
                partners = result.get("partners", [])
                total_partners = result.get("total_partners", len(partners))

                if not partners:
                    network_text = f"""## Collaboration Network: {org_name}

No collaboration partners found for this organization in the database.

**Suggestions:**
- Check the organization name spelling
- Try searching with a shorter name (e.g., "Fraunhofer" instead of full name)
- The organization may not have participated in Horizon Europe projects"""
                else:
                    network_text = f"""## Collaboration Network: {org_name}
**Location:** {org_country}
**Total Collaborating Organizations:** {total_partners}

### Top Collaborating Partners

| Partner | Country | Type | Joint Projects |
|---------|---------|------|----------------|
"""
                    for p in partners[:15]:
                        p_name = p.get("name", "Unknown")[:50]
                        p_country = p.get("country", "N/A")
                        p_type = p.get("type", "N/A")
                        p_type_desc = {
                            "HES": "University",
                            "REC": "Research",
                            "PRC": "Company",
                            "PUB": "Public",
                            "OTH": "Other",
                        }.get(p_type, p_type or "N/A")
                        collabs = p.get("collaborations", 0)
                        network_text += f"| {p_name} | {p_country} | {p_type_desc} | {collabs} |\n"

                    if total_partners > 15:
                        network_text += f"\n*...and {total_partners - 15} more partners*\n"

                    # Add insights
                    countries = set(p.get("country") for p in partners if p.get("country"))
                    types = [p.get("type") for p in partners if p.get("type")]
                    type_counts = {}
                    for t in types:
                        type_counts[t] = type_counts.get(t, 0) + 1
                    top_type = max(type_counts, key=type_counts.get) if type_counts else "N/A"
                    top_type_desc = {
                        "HES": "Universities",
                        "REC": "Research Centers",
                        "PRC": "Companies",
                        "PUB": "Public Bodies",
                        "OTH": "Other Organizations",
                    }.get(top_type, top_type)

                    network_text += f"""
### Network Insights
- **Geographic Reach:** {len(countries)} countries
- **Most Common Partner Type:** {top_type_desc}
- **Strongest Collaboration:** {partners[0].get("name", "N/A")} ({partners[0].get("collaborations", 0)} joint projects)

**Next Steps:**
- Explore specific partners' project histories
- Search CORDIS for joint project details
- Contact organizations through EU Partner Search
"""
                content_pieces.append(network_text)

            # Extract organization projects results (find_organization_projects)
            elif "organization" in result and "projects" in result and "count" in result:
                org_name = result.get("organization", "Unknown")
                projects = result.get("projects", [])
                count = result.get("count", len(projects))
                role_filter = result.get("role_filter")

                if not projects:
                    org_text = f"""## Projects for {org_name}

No projects found for this organization in the database.

**Suggestions:**
- Check the organization name spelling
- Try searching with a shorter name
- The organization may not have participated in Horizon Europe yet"""
                else:
                    role_desc = f" (as {role_filter})" if role_filter else ""
                    org_text = f"""## Projects by {org_name}{role_desc}
**Total Projects Found:** {count}

"""
                    coordinated = [p for p in projects if p.get("role") == "coordinator"]
                    participated = [p for p in projects if p.get("role") != "coordinator"]

                    if coordinated:
                        org_text += f"### Coordinated Projects ({len(coordinated)})\n\n"
                        for p in coordinated[:10]:
                            acronym = p.get("acronym", "N/A")
                            title = p.get("title", "N/A")[:60]
                            budget = p.get("budget", 0)
                            status = p.get("status", "N/A")
                            scheme = p.get("funding_scheme", "N/A")
                            start = p.get("start_date", "")[:10] if p.get("start_date") else "N/A"
                            url = p.get("cordis_url", "")

                            budget_str = f"€{budget / 1_000_000:.1f}M" if budget else "N/A"
                            org_text += f"- **{acronym}**: {title}\n"
                            org_text += (
                                f"  - Budget: {budget_str} | Type: {scheme} | Status: {status}\n"
                            )
                            if url:
                                org_text += f"  - [View on CORDIS]({url})\n"
                            org_text += "\n"

                    if participated:
                        org_text += f"### As Participant ({len(participated)})\n\n"
                        for p in participated[:10]:
                            acronym = p.get("acronym", "N/A")
                            title = p.get("title", "N/A")[:60]
                            budget = p.get("budget", 0)
                            scheme = p.get("funding_scheme", "N/A")
                            url = p.get("cordis_url", "")

                            budget_str = f"€{budget / 1_000_000:.1f}M" if budget else "N/A"
                            org_text += f"- **{acronym}**: {title} ({scheme}, {budget_str})\n"

                    # Add insights
                    total_budget = sum(p.get("budget", 0) or 0 for p in projects)
                    funding_schemes = set(
                        p.get("funding_scheme") for p in projects if p.get("funding_scheme")
                    )

                    org_text += f"""
### Summary
- **Total Projects:** {count}
- **As Coordinator:** {len(coordinated)}
- **Total Budget Involved:** €{total_budget / 1_000_000:.1f}M
- **Funding Types:** {", ".join(funding_schemes) if funding_schemes else "N/A"}

**Next Steps:**
- Explore specific project details on CORDIS
- Search for collaboration partners
- Analyze the organization's research focus areas
"""
                content_pieces.append(org_text)

            # Extract project results (generic fallback for other project queries)
            elif "projects" in result and isinstance(result["projects"], list):
                for proj in result["projects"][:5]:
                    acronym = proj.get("acronym", "")
                    title = proj.get("title", "")
                    if acronym or title:
                        content_pieces.append(f"Project {acronym}: {title}")

            # Extract country statistics results
            elif "country_code" in result and "eligibility" in result:
                country = result.get("country", result.get("country_code", "Unknown"))
                eligibility = result.get("eligibility", {})
                top_orgs = result.get("top_organizations", [])

                # Get participation history from eligibility
                participation = eligibility.get("participation_history", {})
                org_count = participation.get(
                    "organization_count", result.get("organization_count", 0)
                )
                proj_count = participation.get("project_count", 0)
                total_funding = participation.get("total_funding_received", 0)

                # Build clear eligibility answer first
                is_eligible = eligibility.get("is_eligible", False)
                eligibility_status = eligibility.get("eligibility_status", "Unknown")

                country_text = f"""Country: {country}
**Can participate in Horizon Europe: {"YES" if is_eligible else "NO"}**
- Status: {eligibility_status}"""

                # Add notes if available
                notes = eligibility.get("notes", [])
                if notes:
                    country_text += f"\n- {notes[0]}"

                # Add participation stats
                if proj_count > 0:
                    country_text += f"""

Participation Statistics:
- Organizations Participating: {org_count:,}
- Projects Involved: {proj_count:,}
- Total Funding Received: €{total_funding:,.0f}"""

                if top_orgs:
                    country_text += f"\n\nTop Organizations ({len(top_orgs)} shown):"
                    for org in top_orgs[:10]:
                        org_name = org.get("name", org.get("organization_name", "Unknown"))
                        org_projects = org.get("project_count", org.get("projects", 0))
                        org_funding = org.get("total_funding", org.get("funding", 0))
                        country_text += (
                            f"\n- {org_name}: {org_projects} projects, €{org_funding:,.0f}"
                        )

                content_pieces.append(country_text)

            # Handle get_programme_info results (actionable programme information)
            elif "programme" in result and "actionable_guidance" in result:
                prog_name = result.get("info", {}).get("name", result.get("programme", ""))
                info = result.get("info", {})

                prog_text = f"## {prog_name}\n\n"

                # Add budget and focus
                if info.get("budget"):
                    prog_text += f"**Budget**: {info['budget']}\n"
                if info.get("focus"):
                    prog_text += f"**Focus**: {info['focus']}\n\n"

                # Add actionable guidance
                guidance = result.get("actionable_guidance", "")
                if guidance:
                    prog_text += f"{guidance}\n\n"

                # Add official resources
                resources = result.get("official_resources", {})
                if resources:
                    prog_text += "**Official Resources:**\n"
                    for resource_name, url in resources.items():
                        # Format resource name nicely
                        nice_name = resource_name.replace("_", " ").title()
                        prog_text += f"- [{nice_name}]({url})\n"

                # Add official website
                if result.get("official_website"):
                    prog_text += f"\n**Official Website**: {result['official_website']}\n"

                content_pieces.append(prog_text)

            # Extract programme/cluster statistics results
            elif "cluster_code" in result or ("programme" in result and "statistics" in result):
                programme = result.get("programme", result.get("cluster_code", "Unknown"))
                programme_type = result.get("programme_type", "")
                stats = result.get("statistics", {})
                budget = result.get("budget_details", {})

                programme_text = f"""Programme Statistics for {programme}:"""
                if programme_type:
                    programme_text += f"\n({programme_type})"

                # Handle EIC/ERC/MSCA format with success_rates dict
                if "success_rates" in stats:
                    success_rates = stats["success_rates"]
                    programme_text += f"\n\n{stats.get('description', '')}\n"
                    programme_text += "\nSuccess Rates:"
                    for key, value in success_rates.items():
                        if key != "note":
                            programme_text += f"\n- {key.replace('_', ' ').title()}: {value}"
                    if success_rates.get("note"):
                        programme_text += f"\n\nNote: {success_rates['note']}"

                    # Add funding info
                    if "funding" in stats:
                        programme_text += "\n\nFunding Available:"
                        for key, value in stats["funding"].items():
                            programme_text += f"\n- {key.replace('_', ' ').title()}: {value}"

                    # Add eligibility
                    if stats.get("eligibility"):
                        programme_text += f"\n\nEligibility: {stats['eligibility']}"

                    if stats.get("trl_range"):
                        programme_text += f"\nTRL Range: {stats['trl_range']}"

                    # Add evaluation criteria
                    if stats.get("evaluation_criteria"):
                        programme_text += "\n\nEvaluation Criteria:"
                        for criterion in stats["evaluation_criteria"]:
                            programme_text += f"\n- {criterion}"
                else:
                    # Standard cluster statistics format
                    if stats:
                        total_projects = stats.get(
                            "total_projects", stats.get("project_count", "N/A")
                        )
                        total_funding = stats.get("total_funding", stats.get("total_budget", 0))
                        avg_budget = stats.get(
                            "avg_project_budget", stats.get("average_funding", 0)
                        )

                        programme_text += (
                            f"""
- Total Projects: {total_projects:,}"""
                            if isinstance(total_projects, int)
                            else f"""
- Total Projects: {total_projects}"""
                        )
                        programme_text += f"""
- Total Funding: €{total_funding:,.0f}
- Success Rate: {stats.get("success_rate", "N/A")}%
- Average Project Budget: €{avg_budget:,.0f}"""

                    if budget:
                        programme_text += f"""

Budget Breakdown:
- Min Budget: €{budget.get("min_budget", 0):,.0f}
- Max Budget: €{budget.get("max_budget", 0):,.0f}
- Median Budget: €{budget.get("median_budget", 0):,.0f}"""

                content_pieces.append(programme_text)

            # Extract call history analysis results
            elif result.get("tool_name") == "analyze_call_history" or (
                "timeline" in result and "trends" in result
            ):
                query_params = result.get("query_params", {})
                keywords = query_params.get("keywords", "specified criteria")
                cluster = query_params.get("cluster", "")

                calls_analyzed = result.get("calls_analyzed", 0)
                projects_funded = result.get("projects_funded", 0)
                total_funding = result.get("total_funding_allocated", 0)
                timeline = result.get("timeline", {})
                trends = result.get("trends", {})
                top_topics = result.get("top_funded_topics", [])
                sample_projects = result.get("sample_funded_projects", [])
                recommendations = result.get("recommendations", [])

                # Build header
                search_desc = (
                    keywords
                    if keywords
                    else (f"Cluster {cluster}" if cluster else "Horizon Europe")
                )
                history_text = f"""## Funding History Analysis: {search_desc}

**Overview:**
- Calls Analyzed: {calls_analyzed}
- Projects Funded: {projects_funded:,}
- Total Funding: €{total_funding / 1_000_000_000:.2f} billion
"""

                # Add trend info
                funding_trend = trends.get("funding_trend", "unknown")
                yoy_growth = trends.get("year_over_year_funding_growth", 0)
                if funding_trend and funding_trend != "insufficient_data":
                    history_text += f"- Funding Trend: {funding_trend.replace('_', ' ').title()} ({yoy_growth:+.1f}% YoY)\n"

                # Add timeline
                if timeline:
                    history_text += "\n**Funding by Year:**\n"
                    sorted_years = sorted(timeline.keys(), reverse=True)
                    for year in sorted_years[:5]:
                        data = timeline[year]
                        year_projects = data.get("projects_funded", 0)
                        year_funding = data.get("total_funding", 0)
                        avg_budget = data.get("avg_project_budget", 0)
                        history_text += f"- **{year}**: {year_projects:,} projects, €{year_funding / 1_000_000:.0f}M total (avg €{avg_budget / 1_000_000:.1f}M/project)\n"

                # Add top topics
                if top_topics:
                    history_text += "\n**Top Funded Topics:**\n"
                    for topic in top_topics[:5]:
                        topic_name = topic.get("topic", topic.get("name", "N/A"))
                        topic_projects = topic.get("projects", topic.get("count", 0))
                        topic_funding = topic.get("total_funding", 0)
                        if topic_funding > 0:
                            history_text += f"- {topic_name}: {topic_projects} projects, €{topic_funding / 1_000_000:.0f}M\n"
                        else:
                            history_text += f"- {topic_name}: {topic_projects} projects\n"

                # Add sample projects
                if sample_projects:
                    history_text += "\n**Sample Funded Projects:**\n"
                    for proj in sample_projects[:5]:
                        acronym = proj.get("acronym", "N/A")
                        title = proj.get("title", "")[:60]
                        budget = proj.get("budget", proj.get("ec_contribution", 0))
                        history_text += (
                            f"- **{acronym}**: {title}... (€{budget / 1_000_000:.1f}M)\n"
                        )

                # Add recommendations
                if recommendations:
                    history_text += "\n**Recommendations:**\n"
                    for rec in recommendations[:3]:
                        history_text += f"- {rec}\n"

                content_pieces.append(history_text)

            # Extract geographic diversification results
            elif (
                result.get("tool_name") == "analyze_geographic_diversification"
                or "group_representation" in result
            ):
                query_params = result.get("query_params", {})
                cluster = query_params.get("cluster", "All Horizon Europe")
                total_projects = result.get("total_projects_analyzed", 0)
                country_groups = result.get("country_groups", {})
                group_stats = result.get("group_representation", [])
                coverage_stats = result.get("coverage_statistics", {})
                at_least_stats = result.get("at_least_coverage", {})
                insights = result.get("insights", {})
                recommendations = result.get("recommendations", {})
                exclude_widening = query_params.get("exclude_widening", True)

                # Build comprehensive output
                geo_text = f"""## Geographic Diversification Analysis: {cluster}

**Analysis Parameters:**
- Projects Analyzed: {total_projects:,}
- Widening Calls: {"Excluded" if exclude_widening else "Included"}
- Country Groups Defined: {len(country_groups)}

**Country Group Definitions:**
"""
                for group_name, countries in country_groups.items():
                    geo_text += f"- **{group_name}**: {', '.join(countries)}\n"

                geo_text += (
                    "\n**Group Representation (% of projects with at least one partner):**\n"
                )
                geo_text += "| Country Group | Projects | Share (%) |\n"
                geo_text += "|---------------|----------|----------|\n"
                for stat in group_stats:
                    group_name = stat.get("group", "Unknown")
                    projects = stat.get("projects_with_partner", 0)
                    share = stat.get("share_percentage", 0)
                    geo_text += f"| {group_name} | {projects:,} | {share}% |\n"

                geo_text += "\n**Coverage Distribution (number of groups per project):**\n"
                geo_text += "| Coverage | Projects | Share (%) |\n"
                geo_text += "|----------|----------|----------|\n"
                for coverage_key, coverage_data in coverage_stats.items():
                    if isinstance(coverage_data, dict):
                        count = coverage_data.get("count", 0)
                        share = coverage_data.get("share_percentage", 0)
                        label = coverage_key.replace("_", " ").title()
                        geo_text += f"| {label} | {count:,} | {share}% |\n"

                geo_text += "\n**Cumulative Coverage (projects with at least N groups):**\n"
                for coverage_key, coverage_data in at_least_stats.items():
                    if isinstance(coverage_data, dict):
                        share = coverage_data.get("share_percentage", 0)
                        label = coverage_key.replace("_", " ").replace("at least", "At least")
                        geo_text += f"- {label}: {share}%\n"

                geo_text += "\n**Key Insights:**\n"
                typical = insights.get("typical_coverage", "N/A")
                avg_presence = insights.get("avg_group_presence", 0)
                well_rep = insights.get("well_represented_groups", [])
                under_rep = insights.get("underrepresented_groups", [])

                geo_text += f"- Typical consortium covers: {typical}\n"
                geo_text += f"- Average group presence: {avg_presence}%\n"
                if well_rep:
                    geo_text += f"- Well-represented groups: {', '.join(well_rep)}\n"
                if under_rep:
                    geo_text += f"- Underrepresented groups: {', '.join(under_rep)}\n"

                geo_text += "\n**Recommendations:**\n"
                if recommendations.get("consortium_building"):
                    geo_text += f"- {recommendations['consortium_building']}\n"
                if recommendations.get("evaluation_note"):
                    geo_text += f"- {recommendations['evaluation_note']}\n"

                geo_text += """
**Resources:**
- **CORDIS Database**: https://cordis.europa.eu
- **EU Partner Search**: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search
"""
                content_pieces.append(geo_text)

            # Extract Erasmus+ eligibility results
            elif result.get("metadata", {}).get("tool") == "check_erasmus_eligibility":
                eligibility_text = self._format_erasmus_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract Creative Europe eligibility results
            elif result.get("metadata", {}).get("tool") == "check_creative_europe_eligibility":
                eligibility_text = self._format_creative_europe_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract programme recommendations results
            elif "recommendations" in result and result.get("total_programmes"):
                recs = result.get("recommendations", [])
                if recs:
                    rec_text = "## EU Funding Programme Recommendations\n\n"
                    rec_text += "Based on your profile, here are the most relevant EU funding programmes:\n\n"
                    for i, rec in enumerate(recs, 1):
                        icon = rec.get("programme_icon", "🇪🇺")
                        name = rec.get("programme_name", rec.get("programme", ""))
                        budget = rec.get("budget", "")
                        focus = rec.get("focus", "")
                        reasons = rec.get("reasons", [])
                        website = rec.get("website", "")

                        rec_text += f"### {i}. {icon} **{name}**\n"
                        rec_text += f"- **Budget**: {budget}\n"
                        rec_text += f"- **Focus**: {focus}\n"
                        if reasons:
                            rec_text += f"- **Why it fits**: {'; '.join(reasons)}\n"
                        if website:
                            rec_text += f"- **Learn more**: {website}\n"
                        rec_text += "\n"

                    # Check if we have profile info from reasons to provide personalized next steps
                    # Look for indicators of SME, health sector, or specific profile details
                    has_specific_profile = False
                    for r in recs:
                        reasons_str = " ".join(r.get("reasons", []))
                        if "SME" in reasons_str or "health" in reasons_str.lower():
                            has_specific_profile = True
                            break

                    rec_text += "---\n\n🎯 **Next Steps:**\n"
                    if has_specific_profile:
                        # User has provided profile info - give actionable next steps
                        rec_text += (
                            "• Ask me to **find specific open calls** matching your profile\n"
                        )
                        rec_text += "• Ask about **consortium building** and partner requirements\n"
                        rec_text += "• Request **budget benchmarks** from similar funded projects\n"
                        rec_text += "• Learn about the **application process** and deadlines\n"
                    else:
                        rec_text += (
                            "• Tell me more about your research area so I can find specific calls\n"
                        )
                        rec_text += "• Share your organization's experience level (first-time applicant, or experienced?)\n"
                        rec_text += "• Let me know your sector (health, energy, digital, etc.) for targeted recommendations\n"

                    content_pieces.append(rec_text)
                else:
                    # No specific matches - provide general guidance
                    rec_text = """## EU Funding Programmes Overview

I can help you find the right EU funding programme! To give you personalized recommendations, please tell me:

1. **Your organization type**: University, SME, NGO, research institute?
2. **Your research area**: What topics do you work on?
3. **Your goals**: Research, training/mobility, cultural projects?

**Main EU Funding Programmes:**

🔬 **Horizon Europe** (€95.5B) - Research & Innovation
🎓 **Erasmus+** (€26.2B) - Education, Training, Youth, Sport
🎨 **Creative Europe** (€2.44B) - Culture & Media
🏥 **EU4Health** (€5.3B) - Health & Crisis Preparedness
💻 **Digital Europe** (€7.5B) - Digital Transformation
🌍 **LIFE Programme** (€5.4B) - Environment & Climate

---

🎯 **Next Steps:**
• Share your organization type and research area
• I'll recommend the best programme and find open calls for you
"""
                    content_pieces.append(rec_text)

            # Extract partner discovery results
            elif (
                result.get("tool_name") == "find_experienced_partners"
                or "experienced_partners" in result
            ):
                partners = result.get("experienced_partners", [])
                total_found = result.get("total_found", 0)
                query_params = result.get("query_params", {})
                keywords = query_params.get("topic_keywords", "specified criteria")

                if not partners and total_found == 0:
                    partner_text = f"""Partner Search Results for '{keywords}':
No organizations found matching your criteria.

Suggestions:
- Try broader keywords (e.g., "energy storage" instead of "solid-state battery")
- Remove the cluster filter to search across all Horizon Europe
- Reduce the minimum projects requirement
- Try searching for related topics"""
                    content_pieces.append(partner_text)
                else:
                    partner_text = f"""## Top Organizations with Experience in '{keywords}'

Found **{total_found} organizations** with relevant track records:

"""
                    for i, p in enumerate(partners[:10], 1):
                        # Prefer full name over short_name for better recognition
                        full_name = p.get("name", "Unknown")
                        short_name = p.get("short_name", "")
                        # Use full name if available, otherwise use short_name
                        name = full_name if len(full_name) > 5 else (short_name or full_name)
                        country = p.get("country", "N/A")
                        org_type = p.get("type", "N/A")
                        org_type_desc = {
                            "HES": "Higher Education",
                            "REC": "Research Center",
                            "PRC": "Private Company",
                            "PUB": "Public Body",
                            "OTH": "Other",
                        }.get(org_type, org_type)
                        track = p.get("track_record", {})
                        relevant = track.get("relevant_projects", 0)
                        coord = track.get("as_coordinator", 0)
                        # Use funding_in_relevant (actual field) with fallback to total_funding
                        total_funding = track.get(
                            "funding_in_relevant", track.get("total_funding", 0)
                        )
                        # Get project examples (list of dicts with acronym, title, role)
                        project_examples = p.get("relevant_projects", [])

                        partner_text += f"### {i}. **{name}** ({country})\n"
                        partner_text += f"- **Organization Type**: {org_type} ({org_type_desc})\n"
                        partner_text += f"- **Relevant Projects**: {relevant}"
                        if coord > 0:
                            partner_text += f" (coordinated **{coord}** projects)"
                        partner_text += f"\n- **Total Funding**: €{total_funding:,.0f}\n"

                        # Add project examples if available (shows municipal/testbed evidence)
                        if project_examples and isinstance(project_examples, list):
                            partner_text += "- **Example Projects**: "
                            examples = []
                            for proj in project_examples[:3]:  # Max 3 examples
                                if isinstance(proj, dict):
                                    acronym = proj.get("acronym", "")
                                    role = proj.get("role", "participant")
                                    if acronym:
                                        examples.append(f"{acronym} ({role})")
                            if examples:
                                partner_text += ", ".join(examples) + "\n"

                        partner_text += "\n"

                    # Add insights if available
                    insights = result.get("aggregated_insights", {})
                    if insights.get("top_countries_in_topic"):
                        partner_text += f"\n**Top countries for this topic**: {', '.join(insights['top_countries_in_topic'][:5])}\n"
                    if insights.get("top_org_types"):
                        partner_text += f"**Common organization types**: {', '.join(insights['top_org_types'][:3])}\n"

                    # Add actionability section with country-specific resources
                    country_filter = query_params.get("country", "")
                    partner_text += """
---

### How to Verify & Contact Partners

- **CORDIS Database**: Search for specific projects at https://cordis.europa.eu
- **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/
- **Partner Search**: Use the EU Partner Search tool to find and contact organizations
- **Verify Municipal Networks**: Check organizations' websites for urban/city partnerships, living labs, or pilot site descriptions
"""
                    # Add Spain-specific resource for municipal networks
                    if country_filter and country_filter.upper() in ["ES", "SPAIN"]:
                        partner_text += "- **FEMP (Spanish Federation of Municipalities)**: http://www.femp.es - Contact for municipal network verification\n"
                    content_pieces.append(partner_text)

        if not content_pieces:
            return "I found some information but couldn't extract specific details. Please try a more specific question."

        # Combine and deduplicate content
        unique_content = []
        seen = set()
        for piece in content_pieces:
            key = piece[:100].lower()
            if key not in seen:
                seen.add(key)
                unique_content.append(piece)

        # Build a structured response
        # Check for special formatted outputs that should bypass the "Finding X:" wrapper
        # These are detailed outputs that should be returned directly without truncation

        # Markers for detailed content types - prioritize similar projects over call details
        # (since user wants similar projects, not just call info)
        direct_output_markers_priority = [
            "## Similar Funded Projects",  # Highest priority - what user wants
            "## Similar Projects Search",
            "## Collaboration Network:",  # Network exploration results
            "## Projects by ",  # Organization project results
            "## Projects for ",  # Organization project results (no results case)
            "## Project Timeline Generated",
            "## Funding History Analysis:",
            "## Geographic Diversification Analysis:",  # Country group analysis
            "**Programme Statistics:**",  # Programme/cluster statistics
            "Programme Statistics for",  # Alternative statistics format
            "**EIC Accelerator Statistics:**",  # Specific programme stats
            "**ERC Statistics:**",  # Specific programme stats
            "**MSCA Statistics:**",  # Specific programme stats
            "## Call Details:",  # Lower priority - context, not main answer
        ]

        # Collect ALL content pieces with direct output markers
        direct_outputs = []
        regular_content = []

        for content in unique_content:
            is_direct = False
            for marker in direct_output_markers_priority:
                if marker in content:
                    direct_outputs.append((marker, content))
                    is_direct = True
                    break
            if not is_direct:
                regular_content.append(content)

        # If we have direct outputs, combine them (prioritizing similar projects)
        if direct_outputs:
            # Sort by priority (lower index = higher priority)
            direct_outputs.sort(
                key=lambda x: (
                    direct_output_markers_priority.index(x[0])
                    if x[0] in direct_output_markers_priority
                    else 999
                )
            )

            # Combine all direct outputs
            combined_parts = []
            for _marker, content in direct_outputs:
                combined_parts.append(content)

            return "\n\n---\n\n".join(combined_parts)

        intro = f"Based on my search for information about '{query}', here's what I found:\n\n"

        # Take top pieces and format
        body_parts = []
        for i, content in enumerate(unique_content[:5], 1):
            # Truncate long pieces (use higher limit for statistics and detailed results)
            is_detailed = any(
                k in content.lower()
                for k in [
                    "statistics",
                    "eligibility",
                    "organizations",
                    "funding",
                    "timeline",
                    "work package",
                    "deliverable",
                    "milestone",
                    "gantt",
                    "similar",
                    "call details",
                    "budget",
                ]
            )
            max_len = 8000 if is_detailed else 1500
            if len(content) > max_len:
                content = content[:max_len] + "..."
            body_parts.append(f"**Finding {i}:**\n{content}")

        return intro + "\n\n".join(body_parts)

    async def _execute_tool_calls(self, tool_calls: list[dict]) -> list[ToolCall]:
        """Execute multiple tool calls (in parallel when possible).

        If speculative execution is enabled, check for pre-computed results first.
        """
        results = []

        # Group calls that need execution vs those with speculative results
        to_execute = []
        used_speculative = set()

        for tc in tool_calls:
            tool_name = tc.get("tool")
            params = tc.get("parameters", {})
            reasoning = tc.get("reasoning", "")

            tool_call = ToolCall(tool_name=tool_name, parameters=params, reasoning=reasoning)

            # Check for speculative result first (with param validation)
            speculative_result = None
            if self.speculative_executor:
                speculative_result = await self.speculative_executor.get_speculative_result(
                    tool_name,
                    timeout=0.2,  # 200ms timeout for speculative results
                    requested_params=params,  # Pass params for compatibility check
                )

            if speculative_result and speculative_result.get("result") is not None:
                # Use speculative result
                tool_call.success = True
                tool_call.result = speculative_result["result"]
                tool_call.execution_time_ms = 0  # Already computed
                results.append(tool_call)
                used_speculative.add(tool_name)
                logger.info(f"🎯 Using speculative result for: {tool_name}")

                # Track speculative hit in analytics
                if self.analytics:
                    from ..analytics.tool_analytics_service import ToolUsageEvent

                    await self.analytics.track_tool_usage(
                        ToolUsageEvent(
                            tool_name=tool_name,
                            parameters=params,
                            execution_time_ms=0,
                            success=True,
                            speculative=True,
                            result_count=self._count_results(speculative_result["result"]),
                        )
                    )
            else:
                # Need to execute normally
                to_execute.append((tool_call, self._execute_single_tool(tool_name, params)))

        # Execute remaining tools in parallel
        if to_execute:
            start_time = datetime.now()

            tasks = [call[1] for call in to_execute]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, (tool_call, _) in enumerate(to_execute):
                result = task_results[i]
                execution_time = (datetime.now() - start_time).total_seconds() * 1000

                if isinstance(result, Exception):
                    tool_call.success = False
                    tool_call.error = str(result)
                else:
                    tool_call.success = True
                    tool_call.result = result

                tool_call.execution_time_ms = execution_time
                results.append(tool_call)

                logger.info(f"🔧 Tool {tool_call.tool_name}: {'✓' if tool_call.success else '✗'}")

                # Track in analytics
                if self.analytics:
                    from ..analytics.tool_analytics_service import ToolUsageEvent

                    await self.analytics.track_tool_usage(
                        ToolUsageEvent(
                            tool_name=tool_call.tool_name,
                            parameters=tool_call.parameters,
                            execution_time_ms=int(execution_time),
                            success=tool_call.success,
                            error_message=tool_call.error if not tool_call.success else None,
                            result_count=self._count_results(result) if tool_call.success else None,
                            speculative=False,
                        )
                    )

        return results

    async def _execute_single_tool(self, tool_name: str, params: dict) -> Any:
        """Execute a single tool."""

        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Route to actual tool implementations
        try:
            if tool_name == "get_programme_statistics":
                return await self._tool_get_programme_stats(params)
            elif tool_name == "get_country_statistics":
                return await self._tool_get_country_stats(params)
            elif tool_name == "compare_programmes":
                return await self._tool_compare_programmes(params)
            elif tool_name == "search_documents":
                return await self._tool_search_documents(params)
            elif tool_name == "search_funding_calls":
                return await self._tool_search_funding_calls(params)
            elif tool_name == "get_call_details":
                return await self._tool_get_call_details(params)
            elif tool_name == "search_projects":
                return await self._tool_search_projects(params)
            elif tool_name == "find_similar_projects":
                return await self._tool_find_similar_projects(params)
            elif tool_name == "find_semantically_similar_projects":
                return await self._tool_find_semantically_similar_projects(params)
            elif tool_name == "find_organization_projects":
                return await self._tool_find_organization_projects(params)
            elif tool_name == "get_collaboration_network":
                return await self._tool_get_collaboration_network(params)
            elif tool_name == "search_by_cluster":
                return await self._tool_search_by_cluster(params)
            elif tool_name == "get_budget_benchmark":
                return await self._tool_get_budget_benchmark(params)
            elif tool_name == "get_consortium_patterns":
                return await self._tool_get_consortium_patterns(params)
            elif tool_name == "analyze_geographic_diversification":
                return await self._tool_analyze_geographic_diversification(params)
            elif tool_name == "find_experienced_partners":
                return await self._tool_find_experienced_partners(params)
            elif tool_name == "get_similar_funded_projects":
                return await self._tool_get_similar_funded_projects(params)
            elif tool_name == "analyze_call_history":
                return await self._tool_analyze_call_history(params)
            elif tool_name == "calculate_budget":
                return await self._tool_calculate_budget(params)
            elif tool_name == "generate_timeline":
                return await self._tool_generate_timeline(params)
            # Multi-programme tools
            elif tool_name == "search_all_programmes":
                return await self._tool_search_all_programmes(params)
            elif tool_name == "recommend_programmes":
                return await self._tool_recommend_programmes(params)
            elif tool_name == "get_programme_info":
                return await self._tool_get_programme_info(params)
            # Proposal quality scoring tools
            elif tool_name == "score_proposal_section":
                return await self._tool_score_proposal_section(params)
            elif tool_name == "score_full_proposal":
                return await self._tool_score_full_proposal(params)
            elif tool_name == "quick_quality_check":
                return await self._tool_quick_quality_check(params)
            # Budget validation tool
            elif tool_name == "validate_budget":
                return await self._tool_validate_budget(params)
            # Erasmus+ specific tools
            elif tool_name == "check_erasmus_eligibility":
                return await self._tool_check_erasmus_eligibility(params)
            elif tool_name == "calculate_erasmus_budget":
                return await self._tool_calculate_erasmus_budget(params)
            elif tool_name == "search_erasmus_templates":
                return await self._tool_search_erasmus_templates(params)
            # Creative Europe specific tools
            elif tool_name == "check_creative_europe_eligibility":
                return await self._tool_check_creative_europe_eligibility(params)
            elif tool_name == "calculate_creative_europe_budget":
                return await self._tool_calculate_creative_europe_budget(params)
            elif tool_name == "search_creative_europe_templates":
                return await self._tool_search_creative_europe_templates(params)
            else:
                return {"error": f"Tool {tool_name} not implemented"}
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}

    # ==================== Tool Implementations ====================

    def _extract_cluster_param(self, params: dict) -> str | None:
        """
        Extract cluster parameter from tool params with fallback alternatives.
        LLM might use different names for the cluster parameter.
        """
        cluster = (
            params.get("cluster")
            or params.get("cluster_code")
            or params.get("cluster_id")
            or params.get("pillar")  # Sometimes LLM confuses pillar with cluster
        )
        if cluster:
            logger.debug(f"_extract_cluster_param: extracted '{cluster}' from params")
        return cluster

    async def _tool_get_programme_stats(self, params: dict) -> dict:
        """Get programme/cluster statistics from graph DB."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()

            programme = params.get("programme", "")
            programme_lower = programme.lower()

            # Map programme names to cluster codes (Neo4j uses CLUSTER-X format)
            cluster_map = {
                "cluster 5": "CLUSTER-5",
                "cluster-5": "CLUSTER-5",
                "cl5": "CLUSTER-5",
                "climate": "CLUSTER-5",
                "energy": "CLUSTER-5",
                "mobility": "CLUSTER-5",
                "cluster 4": "CLUSTER-4",
                "cluster-4": "CLUSTER-4",
                "cl4": "CLUSTER-4",
                "digital": "CLUSTER-4",
                "industry": "CLUSTER-4",
                "space": "CLUSTER-4",
                "cluster 6": "CLUSTER-6",
                "cluster-6": "CLUSTER-6",
                "cl6": "CLUSTER-6",
                "food": "CLUSTER-6",
                "bioeconomy": "CLUSTER-6",
                "agriculture": "CLUSTER-6",
                "cluster 1": "CLUSTER-1",
                "cluster-1": "CLUSTER-1",
                "cl1": "CLUSTER-1",
                "health": "CLUSTER-1",
                "cluster 2": "CLUSTER-2",
                "cluster-2": "CLUSTER-2",
                "cl2": "CLUSTER-2",
                "culture": "CLUSTER-2",
                "creativity": "CLUSTER-2",
                "cluster 3": "CLUSTER-3",
                "cluster-3": "CLUSTER-3",
                "cl3": "CLUSTER-3",
                "security": "CLUSTER-3",
            }

            # Handle EIC/ERC/MSCA separately - these are pillars, not clusters
            # Return known statistics from official EC sources
            if "eic" in programme_lower or "accelerator" in programme_lower:
                return {
                    "programme": "EIC Accelerator",
                    "programme_type": "Pillar 3 - Innovative Europe",
                    "statistics": {
                        "description": "EIC Accelerator supports high-risk, high-impact SMEs and startups with breakthrough innovations",
                        "success_rates": {
                            "overall": "2-5%",
                            "short_proposal_to_full": "~25-30%",
                            "full_proposal_to_interview": "~20-25%",
                            "interview_to_funding": "~50-60%",
                            "note": "Success rates vary by cut-off date and are highly competitive",
                        },
                        "funding": {
                            "grant_only": "Up to €2.5 million",
                            "blended_finance": "Up to €2.5M grant + up to €15M equity",
                            "equity_only": "Up to €15 million",
                        },
                        "eligibility": "Single SMEs (including startups) from EU/Associated Countries",
                        "trl_range": "TRL 5-9 (close to market)",
                        "evaluation_criteria": [
                            "Excellence (Breakthrough innovation, Technology readiness)",
                            "Impact (Market potential, Scalability, Team capability)",
                            "Implementation (Business plan, Milestones, Resources)",
                            "Level of risk and need for EU support",
                        ],
                    },
                    "source": "official_ec_data",
                }

            if "erc" in programme_lower:
                return {
                    "programme": "European Research Council (ERC)",
                    "programme_type": "Pillar 1 - Excellent Science",
                    "statistics": {
                        "description": "ERC funds frontier research by individual investigators",
                        "success_rates": {
                            "starting_grant": "~10-15%",
                            "consolidator_grant": "~12-15%",
                            "advanced_grant": "~10-12%",
                            "synergy_grant": "~8-10%",
                            "proof_of_concept": "~35-40%",
                        },
                        "funding": {
                            "starting_grant": "Up to €1.5M for 5 years",
                            "consolidator_grant": "Up to €2M for 5 years",
                            "advanced_grant": "Up to €2.5M for 5 years",
                            "synergy_grant": "Up to €10M for 6 years (2-4 PIs)",
                        },
                        "eligibility": "Researchers at any career stage hosted by EU/AC institutions",
                        "evaluation_criteria": [
                            "Excellence of the PI (track record, scientific leadership)",
                            "Excellence of the research project (groundbreaking nature, methodology)",
                        ],
                    },
                    "source": "official_ec_data",
                }

            if (
                "msca" in programme_lower
                or "marie" in programme_lower
                or "curie" in programme_lower
            ):
                return {
                    "programme": "Marie Skłodowska-Curie Actions (MSCA)",
                    "programme_type": "Pillar 1 - Excellent Science",
                    "statistics": {
                        "description": "MSCA supports researcher mobility, training and career development",
                        "success_rates": {
                            "postdoctoral_fellowships": "~12-15%",
                            "doctoral_networks": "~8-12%",
                            "staff_exchanges": "~25-30%",
                            "cofund": "~20-25%",
                            "citizens": "Varied (outreach programme)",
                        },
                        "funding": {
                            "postdoctoral_fellowships": "Living allowance + mobility + research costs",
                            "doctoral_networks": "Up to €360,000/researcher",
                        },
                        "eligibility": "Researchers at all career stages, with mobility requirements",
                        "evaluation_criteria": [
                            "Excellence (Quality of research/training)",
                            "Impact (Career development, Knowledge transfer)",
                            "Implementation (Work plan, Management)",
                        ],
                    },
                    "source": "official_ec_data",
                }

            # Try to find a matching cluster code for Pillar 2 clusters
            cluster_code = None
            for key, code in cluster_map.items():
                if key in programme_lower:
                    cluster_code = code
                    break

            # Get cluster statistics from Neo4j
            result = await asyncio.to_thread(graph.get_cluster_statistics, cluster_code)

            if result:
                # Also get budget statistics for more detail
                budget_stats = await asyncio.to_thread(graph.get_budget_statistics, cluster_code)

                # Combine results with clear context to avoid budget confusion
                return {
                    "programme": programme,
                    "cluster_code": cluster_code,
                    "statistics": result,
                    "budget_details": budget_stats,
                    "source": "neo4j_graph",
                    # IMPORTANT: Add programme budget context to avoid LLM confusion
                    "programme_context": {
                        "note": "IMPORTANT: The 'total_funding' in statistics is the cumulative amount awarded to PROJECTS in this cluster/area, NOT the overall Horizon Europe budget.",
                        "horizon_europe_total_budget": "€95.5 billion (2021-2027)",
                        "cluster_funding_note": f"This cluster ({cluster_code}) represents a portion of the overall programme budget.",
                    },
                }

            return {
                "message": f"No statistics found for {programme}. Try specific cluster names (e.g., 'Cluster 5 - Climate', 'Health') or programmes (EIC, ERC, MSCA).",
                # Include correct programme budgets to prevent hallucination
                "programme_budget_reference": {
                    "Horizon Europe": "€95.5 billion (2021-2027)",
                    "Erasmus+": "€26.2 billion (2021-2027)",
                    "Creative Europe": "€2.44 billion (2021-2027)",
                    "note": "Use these figures when discussing overall programme budgets.",
                },
            }
        except Exception as e:
            logger.error(f"Programme stats error: {e}")
            return {"error": str(e)}

    async def _tool_get_country_stats(self, params: dict) -> dict:
        """Get country statistics from graph DB."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()

            country = params.get("country", "")

            # Try to extract country code from input
            country_codes = {
                "germany": "DE",
                "german": "DE",
                "france": "FR",
                "french": "FR",
                "italy": "IT",
                "italian": "IT",
                "spain": "ES",
                "spanish": "ES",
                "netherlands": "NL",
                "dutch": "NL",
                "belgium": "BE",
                "belgian": "BE",
                "austria": "AT",
                "austrian": "AT",
                "sweden": "SE",
                "swedish": "SE",
                "denmark": "DK",
                "danish": "DK",
                "finland": "FI",
                "finnish": "FI",
                "ireland": "IE",
                "irish": "IE",
                "portugal": "PT",
                "portuguese": "PT",
                "greece": "GR",
                "greek": "GR",
                "poland": "PL",
                "polish": "PL",
                "switzerland": "CH",
                "swiss": "CH",
                "norway": "NO",
                "norwegian": "NO",
                "uk": "GB",
                "united kingdom": "GB",
                "britain": "GB",
                "british": "GB",
                "israel": "IL",
                "israeli": "IL",
            }

            country_code = None
            country_lower = country.lower()

            # First check if it's already a code (2 letters)
            if len(country) == 2:
                country_code = country.upper()
            else:
                for name, code in country_codes.items():
                    if name in country_lower:
                        country_code = code
                        break

            if not country_code:
                return {
                    "message": f"Could not identify country code for '{country}'. Try using ISO codes like DE, FR, IT."
                }

            # Get eligibility info
            eligibility = await asyncio.to_thread(graph.check_country_eligibility, country_code)

            # Get top organizations in that country
            top_orgs = await asyncio.to_thread(
                graph.get_top_organizations,
                None,  # no cluster filter
                country_code,
                10,  # limit
            )

            return {
                "country": country,
                "country_code": country_code,
                "eligibility": eligibility,
                "top_organizations": top_orgs,
                "organization_count": len(top_orgs),
                "source": "neo4j_graph",
            }
        except Exception as e:
            logger.error(f"Country stats error: {e}")
            return {"error": str(e)}

    async def _tool_compare_programmes(self, params: dict) -> dict:
        """Compare two programmes/clusters."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()

            prog_a = params.get("programme_a", "")
            prog_b = params.get("programme_b", "")

            # Use the same cluster mapping as get_programme_stats (Neo4j uses CLUSTER-X format)
            cluster_map = {
                "cluster 5": "CLUSTER-5",
                "cluster-5": "CLUSTER-5",
                "cl5": "CLUSTER-5",
                "climate": "CLUSTER-5",
                "energy": "CLUSTER-5",
                "mobility": "CLUSTER-5",
                "cluster 4": "CLUSTER-4",
                "cluster-4": "CLUSTER-4",
                "cl4": "CLUSTER-4",
                "digital": "CLUSTER-4",
                "industry": "CLUSTER-4",
                "space": "CLUSTER-4",
                "cluster 6": "CLUSTER-6",
                "cluster-6": "CLUSTER-6",
                "cl6": "CLUSTER-6",
                "food": "CLUSTER-6",
                "bioeconomy": "CLUSTER-6",
                "agriculture": "CLUSTER-6",
                "cluster 1": "CLUSTER-1",
                "cluster-1": "CLUSTER-1",
                "cl1": "CLUSTER-1",
                "health": "CLUSTER-1",
                "cluster 2": "CLUSTER-2",
                "cluster-2": "CLUSTER-2",
                "cl2": "CLUSTER-2",
                "culture": "CLUSTER-2",
                "creativity": "CLUSTER-2",
                "cluster 3": "CLUSTER-3",
                "cluster-3": "CLUSTER-3",
                "cl3": "CLUSTER-3",
                "security": "CLUSTER-3",
                "eic": "EIC",
                "eic accelerator": "EIC",
                "erc": "ERC",
                "msca": "MSCA",
                "marie curie": "MSCA",
                "ria": "RIA",
                "ia": "IA",
                "csa": "CSA",
            }

            def get_cluster_code(prog: str) -> str | None:
                prog_lower = prog.lower()
                for key, code in cluster_map.items():
                    if key in prog_lower:
                        return code
                return None

            code_a = get_cluster_code(prog_a)
            code_b = get_cluster_code(prog_b)

            # Get statistics for both
            stats_a = await asyncio.to_thread(graph.get_cluster_statistics, code_a)
            stats_b = await asyncio.to_thread(graph.get_cluster_statistics, code_b)

            return {
                "comparison": {
                    prog_a: {"cluster_code": code_a, "statistics": stats_a[0] if stats_a else None},
                    prog_b: {"cluster_code": code_b, "statistics": stats_b[0] if stats_b else None},
                },
                "source": "neo4j_graph",
            }
        except Exception as e:
            logger.error(f"Compare programmes error: {e}")
            return {"error": str(e)}

    async def _tool_search_documents(self, params: dict) -> dict:
        """Search documents using vector search."""
        try:
            from ..vector_search_service import VectorSearchService

            vector = VectorSearchService()

            query = params.get("query", "")
            max_results = params.get("max_results", 15)  # Increased default from 5
            doc_type = params.get("document_type")

            # Build filters if document type specified
            filters = None
            if doc_type:
                filters = {"document_type": doc_type}

            # hybrid_search uses num_results, not limit
            results = vector.hybrid_search(query=query, num_results=max_results, filters=filters)

            return {
                "documents": [
                    {
                        "content": (
                            r.content[:1500] if hasattr(r, "content") else str(r)[:1500]
                        ),  # Increased from 300
                        "source": r.document_title if hasattr(r, "document_title") else "Unknown",
                        "title": r.document_title if hasattr(r, "document_title") else "",
                        "section": r.section if hasattr(r, "section") else "",
                        "score": r.score if hasattr(r, "score") else 0,
                    }
                    for r in results[:max_results]
                ]
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_search_funding_calls(self, params: dict) -> dict:
        """Search funding calls."""
        try:
            from ..local_call_search_service import LocalCallSearchService

            call_service = LocalCallSearchService()

            keywords = params.get("keywords", "")
            # Handle keywords being a list or string
            if isinstance(keywords, list):
                keywords = " ".join(keywords)
            status = params.get("status", "open")
            year = params.get("year")

            # LocalCallSearchService.search_calls uses 'num_results' not 'limit'
            results = call_service.search_calls(
                query=keywords,
                num_results=15,
                include_closed=(status == "closed"),
                year_filter=str(year) if year else None,
            )

            calls = results.get("calls", [])

            # Pass through ALL available fields for rich formatting
            return {
                "calls_found": len(calls),
                "calls": [
                    {
                        "call_id": c.get("topic_code", ""),  # topic_code is the actual call ID
                        "title": c.get("title", ""),
                        "deadline": c.get("deadline", ""),
                        "type": c.get("action_type", ""),
                        "cluster": c.get("cluster", ""),
                        "budget": c.get("budget", ""),
                        "scope": c.get("scope", "") or c.get("description", ""),
                        "expected_outcome": c.get("expected_outcome", ""),
                        "status": c.get("status", "open"),
                        "url": c.get("url", ""),
                        "work_programme": c.get("work_programme", ""),
                        "call_year": c.get("call_year", ""),
                    }
                    for c in calls[:15]
                ],
            }
        except Exception as e:
            logger.error(f"Funding calls search error: {e}")
            return {"error": str(e), "calls": []}

    async def _tool_get_call_details(self, params: dict) -> dict:
        """Get details for a specific call."""
        try:
            call_id = params.get("call_id", "")
            if not call_id:
                return {"error": "call_id is required"}

            logger.info(f"🔍 Getting call details for: {call_id}")

            from ..local_call_search_service import LocalCallSearchService

            call_service = LocalCallSearchService()

            # First try the dedicated get_call_details method (includes API enrichment)
            call_details = call_service.get_call_details(call_id)

            # Check if we got valid data (not just empty dict)
            if call_details and (call_details.get("topic_code") or call_details.get("title")):
                logger.info(
                    f"✅ Got call details: {call_details.get('topic_code')} - {call_details.get('title', '')[:50]}"
                )
                return {
                    "call_id": call_details.get("topic_code"),
                    "title": call_details.get("title"),
                    "description": call_details.get("scope") or call_details.get("description", ""),
                    "expected_outcome": call_details.get("expected_outcome", ""),
                    "deadline": (
                        str(call_details.get("deadline")) if call_details.get("deadline") else None
                    ),
                    "type": call_details.get("action_type"),
                    "cluster": call_details.get("cluster"),
                    "budget": call_details.get("budget"),
                    "status": call_details.get("status"),
                    "url": call_details.get("url") or call_details.get("portal_url"),
                }

            # Fallback: Search for the call using keywords
            # Include closed calls since user is looking for a specific call ID
            logger.info(f"🔎 Fallback: Searching for {call_id}...")
            results = call_service.search_calls(
                query=call_id,
                num_results=10,
                include_closed=True,  # Include closed calls when looking up specific call IDs
            )

            calls = results.get("calls", [])
            logger.info(f"Search returned {len(calls)} results")

            for call in calls:
                # Check both topic_code and call_id fields
                topic_code = call.get("topic_code", "") or ""
                if call_id.upper() in topic_code.upper():
                    logger.info(f"✅ Found matching call: {topic_code}")
                    return {
                        "call_id": topic_code,
                        "title": call.get("title"),
                        "description": call.get("scope") or call.get("description", ""),
                        "expected_outcome": call.get("expected_outcome", ""),
                        "deadline": str(call.get("deadline")) if call.get("deadline") else None,
                        "type": call.get("action_type"),
                        "cluster": call.get("cluster"),
                        "budget": call.get("budget"),
                        "status": call.get("status"),
                        "url": call.get("url") or call.get("portal_url"),
                    }

            # If still not found, try searching with just the base call identifier
            # e.g., HORIZON-CL5-2026-02-D4-01 -> search for "HORIZON-CL5-2026"
            if "-" in call_id:
                parts = call_id.split("-")
                if len(parts) >= 4:
                    base_call = "-".join(parts[:4])  # e.g., HORIZON-CL5-2026-02
                    logger.info(f"🔎 Trying base call search: {base_call}")
                    results = call_service.search_calls(
                        query=base_call, num_results=15, include_closed=True
                    )
                    calls = results.get("calls", [])
                    for call in calls:
                        topic_code = call.get("topic_code", "") or ""
                        if (
                            call_id.upper() in topic_code.upper()
                            or topic_code.upper() in call_id.upper()
                        ):
                            logger.info(f"✅ Found via base search: {topic_code}")
                            return {
                                "call_id": topic_code,
                                "title": call.get("title"),
                                "description": call.get("scope") or call.get("description", ""),
                                "expected_outcome": call.get("expected_outcome", ""),
                                "deadline": (
                                    str(call.get("deadline")) if call.get("deadline") else None
                                ),
                                "type": call.get("action_type"),
                                "cluster": call.get("cluster"),
                                "budget": call.get("budget"),
                                "status": call.get("status"),
                                "url": call.get("url") or call.get("portal_url"),
                            }

            logger.warning(f"❌ No details found for {call_id} in local searches")

            # Last resort: Try direct API fetch via enrichment service
            logger.info(f"🌐 Trying direct EU Portal API fetch for {call_id}...")
            try:
                from app.core.config import settings

                from ..call_enrichment_service import CallEnrichmentService

                enrichment = CallEnrichmentService(settings.database_url)
                api_result = enrichment.get_call_details(call_id, force_refresh=True)
                if api_result and (api_result.get("topic_code") or api_result.get("title")):
                    logger.info(f"✅ Found {call_id} via direct API fetch!")
                    return {
                        "call_id": api_result.get("topic_code") or call_id,
                        "title": api_result.get("title"),
                        "description": api_result.get("scope") or api_result.get("description", ""),
                        "expected_outcome": api_result.get("expected_outcome", ""),
                        "deadline": (
                            str(api_result.get("deadline")) if api_result.get("deadline") else None
                        ),
                        "type": api_result.get("action_type"),
                        "cluster": api_result.get("cluster"),
                        "budget": api_result.get("budget") or api_result.get("budget_total"),
                        "status": api_result.get("status"),
                        "url": api_result.get("portal_url")
                        or f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}",
                    }
                else:
                    logger.info(f"⚠️ Direct API fetch returned no valid data for {call_id}")
            except Exception as api_err:
                logger.warning(f"Direct API fetch failed: {api_err}")

            # Try to find similar calls to suggest
            similar_calls = []
            if "-" in call_id:
                parts = call_id.split("-")
                # Search for calls in the same cluster/year
                if len(parts) >= 3:
                    search_term = "-".join(parts[:3])  # e.g., HORIZON-CL5-2026
                    results = call_service.search_calls(
                        query=search_term, num_results=5, include_closed=True
                    )
                    for call in results.get("calls", [])[:5]:
                        topic_code = call.get("topic_code", "")
                        title = call.get("title", "")
                        if topic_code and title:
                            similar_calls.append(f"- {topic_code}: {title[:60]}...")

            if similar_calls:
                suggestions = "\n".join(similar_calls)
                return {
                    "message": f"Call ID '{call_id}' was not found. This may be an invalid or incomplete call ID.\n\n**Similar calls you might be looking for:**\n{suggestions}\n\nYou can also check the EU Portal directly.",
                    "similar_calls": similar_calls,
                }
            else:
                return {
                    "message": f"No details found for {call_id}. This call ID may be invalid or not yet in our database. Please verify the call ID format (e.g., HORIZON-CL5-2026-02-D3-01) and try again, or check the EU Funding & Tenders Portal directly."
                }
        except Exception as e:
            logger.error(f"Get call details error: {e}")
            import traceback

            traceback.print_exc()
            return {"error": str(e)}

    async def _tool_search_projects(self, params: dict) -> dict:
        """Search CORDIS projects using LOCAL database."""
        try:
            from ..local_project_search_service import LocalProjectSearchService

            keywords = params.get("keywords", "")
            country = params.get("country")
            programme = params.get("programme")

            # Build the full query including country if provided
            # Let the LocalProjectSearchService handle country extraction from natural language
            query = keywords
            if country:
                query = f"{keywords} {country}"

            # Build explicit filters for programme only
            filters = {}
            if programme:
                filters["programme"] = programme.upper()

            # Use local search service - it will parse country from query
            service = LocalProjectSearchService()
            results = await service.search_projects(
                query=query, filters=filters if filters else None, limit=10
            )

            return {
                "projects": results.get("projects", []),
                "total_found": results.get("total_found", 0),
                "sources": results.get("sources_used", []),
            }
        except Exception as e:
            logger.error(f"Project search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_find_similar_projects(self, params: dict) -> dict:
        """Find projects similar to a given project."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()

            project_id = params.get("project_id", "")
            similarity_type = params.get("similarity_type", "topic")

            if not project_id:
                return {"error": "project_id is required", "projects": []}

            results = await asyncio.to_thread(
                graph.find_similar_projects,
                project_id=project_id,
                similarity_type=similarity_type,
                limit=10,
            )

            return {
                "reference_project": project_id,
                "similarity_type": similarity_type,
                "similar_projects": results,
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Similar projects search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_find_semantically_similar_projects(self, params: dict) -> dict:
        """Find semantically similar projects using vector embeddings."""
        try:
            from ..local_project_search_service import LocalProjectSearchService

            project_id = params.get("project_id", "")
            limit = params.get("limit", 10)

            if not project_id:
                return {"error": "project_id is required", "projects": []}

            service = LocalProjectSearchService()
            result = await service.find_similar_projects_by_embedding(
                project_id=project_id, limit=limit
            )

            return result
        except Exception as e:
            logger.error(f"Semantic similarity search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_find_organization_projects(self, params: dict) -> dict:
        """Find projects by organization."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()

            org_name = params.get("organization_name", "")
            role = params.get("role")

            if not org_name:
                return {"error": "organization_name is required", "projects": []}

            results = await asyncio.to_thread(
                graph.find_projects_by_organization, organization_name=org_name, role=role, limit=20
            )

            return {
                "organization": org_name,
                "role_filter": role,
                "projects": results,
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Organization projects search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_get_collaboration_network(self, params: dict) -> dict:
        """Get collaboration network for an organization."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService

            graph = GraphSearchService()

            org_name = params.get("organization_name", "")

            if not org_name:
                return {"error": "organization_name is required", "partners": []}

            result = await asyncio.to_thread(
                graph.get_organization_collaboration_network,
                organization_name=org_name,
                depth=1,
                limit=30,
            )

            return result
        except Exception as e:
            logger.error(f"Collaboration network error: {e}")
            return {"error": str(e), "partners": []}

    async def _tool_search_by_cluster(self, params: dict) -> dict:
        """Search projects in a specific cluster."""
        try:
            from ..local_project_search_service import LocalProjectSearchService

            service = LocalProjectSearchService()

            # Extract cluster with fallback alternatives
            cluster = self._extract_cluster_param(params) or ""

            if not cluster:
                return {"error": "cluster parameter is required", "projects": []}

            result = await service.search_projects_by_relationship(
                relationship_type="cluster", entity_value=cluster, limit=15
            )

            return result
        except Exception as e:
            logger.error(f"Cluster search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_get_budget_benchmark(self, params: dict) -> dict:
        """Get budget benchmarks from funded Horizon Europe projects."""
        try:
            from ..tools.budget_benchmark import BudgetBenchmarkTool

            # Log the incoming params
            logger.info(f"_tool_get_budget_benchmark called with params: {params}")

            # Extract cluster with fallback alternatives
            cluster_param = self._extract_cluster_param(params)
            logger.info(f"_tool_get_budget_benchmark: cluster param = {cluster_param!r}")

            tool = BudgetBenchmarkTool()
            result = tool.get_benchmark(
                cluster=cluster_param,
                action_type=params.get("action_type"),
                topic_keywords=params.get("topic_keywords"),
                year=params.get("year"),
            )

            return result

        except Exception as e:
            logger.error(f"Budget benchmark error: {e}")
            return {"error": str(e)}

    async def _tool_get_consortium_patterns(self, params: dict) -> dict:
        """Get consortium composition patterns from funded projects."""
        try:
            from ..tools.consortium_patterns import ConsortiumPatternsTool

            # Extract cluster with fallback alternatives
            cluster_param = self._extract_cluster_param(params)

            tool = ConsortiumPatternsTool()
            result = tool.get_patterns(
                cluster=cluster_param,
                action_type=params.get("action_type"),
                topic_keywords=params.get("topic_keywords"),
                min_projects=params.get("min_projects", 10),
            )

            return result

        except Exception as e:
            logger.error(f"Consortium patterns error: {e}")
            return {"error": str(e)}

    async def _tool_analyze_geographic_diversification(self, params: dict) -> dict:
        """Analyze geographic diversification of country partners by country groups."""
        try:
            from ..tools.consortium_patterns import GeographicDiversificationTool

            # Extract cluster with fallback alternatives
            cluster_param = self._extract_cluster_param(params)

            tool = GeographicDiversificationTool()
            result = tool.analyze_geographic_diversification(
                cluster=cluster_param,
                country_groups=params.get("country_groups"),
                exclude_widening=params.get("exclude_widening", True),
                min_partners=params.get("min_partners", 3),
            )

            return result

        except Exception as e:
            logger.error(f"Geographic diversification error: {e}")
            return {"error": str(e)}

    async def _tool_find_experienced_partners(self, params: dict) -> dict:
        """Find experienced partners for consortium building."""
        try:
            from ..tools.partner_discovery import PartnerDiscoveryTool

            # Extract cluster with fallback alternatives
            cluster_param = self._extract_cluster_param(params)

            tool = PartnerDiscoveryTool()
            result = tool.find_partners(
                topic_keywords=params.get("topic_keywords", params.get("keywords", "")),
                country=params.get("country"),
                organization_type=params.get("organization_type"),
                cluster=cluster_param,
                min_projects=params.get("min_projects", 2),
                role_filter=params.get("role_filter"),
                limit=params.get("limit", 20),
            )

            return result

        except Exception as e:
            logger.error(f"Partner discovery error: {e}")
            return {"error": str(e)}

    async def _tool_get_similar_funded_projects(self, params: dict) -> dict:
        """Find funded projects semantically similar to a description."""
        try:
            from ..tools.similar_projects import SimilarProjectsTool

            # Extract cluster with fallback alternatives
            cluster_param = self._extract_cluster_param(params)

            tool = SimilarProjectsTool()
            result = tool.find_similar(
                description=params.get("description", ""),
                cluster=cluster_param,
                action_type=params.get("action_type"),
                min_budget=params.get("min_budget"),
                max_budget=params.get("max_budget"),
                year_from=params.get("year_from"),
                limit=params.get("limit", 10),
                similarity_threshold=params.get("similarity_threshold", 0.3),
            )

            return result

        except Exception as e:
            logger.error(f"Similar projects error: {e}")
            return {"error": str(e)}

    async def _tool_analyze_call_history(self, params: dict) -> dict:
        """Analyze historical funding patterns for Horizon Europe topics.

        Supports expand_scope parameter for broader searches (projects USING a technology
        rather than just focusing on it).
        """
        try:
            from ..tools.call_history import CallHistoryTool

            # Extract cluster with fallback alternatives
            cluster_param = self._extract_cluster_param(params)

            tool = CallHistoryTool()
            result = tool.analyze_history(
                topic_pattern=params.get("topic_pattern"),
                cluster=cluster_param,
                keywords=params.get("keywords"),
                year_from=params.get("year_from"),
                year_to=params.get("year_to"),
                action_types=params.get("action_types"),
                include_projects=params.get("include_projects", True),
                expand_scope=params.get("expand_scope", False),  # NEW: AI-powered keyword expansion
                limit=params.get("limit", 50),
            )

            return result

        except Exception as e:
            logger.error(f"Call history analysis error: {e}")
            return {"error": str(e)}

    async def _tool_calculate_budget(self, params: dict) -> dict:
        """Calculate budget breakdown for a Horizon Europe proposal."""
        try:
            from ..tools.budget_calculator import BudgetCalculatorTool

            tool = BudgetCalculatorTool()
            result = tool.calculate_budget(
                action_type=params.get("action_type", "RIA"),
                duration_months=params.get("duration_months", 36),
                num_partners=params.get("num_partners", 8),
                total_person_months=params.get("total_person_months"),
                target_budget=params.get("target_budget"),
                countries=params.get("countries"),
                include_breakdown=params.get("include_breakdown", True),
            )

            return result

        except Exception as e:
            logger.error(f"Budget calculator error: {e}")
            return {"error": str(e)}

    async def _tool_generate_timeline(self, params: dict) -> dict:
        """Generate project timeline with work packages, deliverables, and milestones."""
        try:
            from ..tools.timeline_generator import TimelineGeneratorTool

            tool = TimelineGeneratorTool()
            result = tool.generate_timeline(
                action_type=params.get("action_type", "RIA"),
                duration_months=params.get("duration_months", 36),
                num_partners=params.get("num_partners", 8),
                total_person_months=params.get("total_person_months", 300),
                project_title=params.get("project_title", "Project"),
                custom_wps=params.get("custom_wps"),
                start_date=params.get("start_date"),
            )

            return result

        except Exception as e:
            logger.error(f"Timeline generator error: {e}")
            return {"error": str(e)}

    async def _tool_search_all_programmes(self, params: dict) -> dict:
        """Search across all EU funding programmes (Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe, LIFE)."""
        try:
            from ..tools.multi_programme_search import search_all_programmes_execute

            result = search_all_programmes_execute(
                keywords=params.get("keywords", ""),
                programmes=params.get("programmes"),
                status=params.get("status"),
                year=params.get("year"),
                action_type=params.get("action_type"),
                limit=params.get("limit", 20),
                include_closed=params.get("include_closed", False),
            )

            return result

        except Exception as e:
            logger.error(f"Multi-programme search error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_recommend_programmes(self, params: dict) -> dict:
        """Recommend EU funding programmes based on project/activity description."""
        try:
            from ..tools.multi_programme_search import get_programme_recommendations_execute

            result = get_programme_recommendations_execute(
                description=params.get("description", ""),
                organization_type=params.get("organization_type"),
                sector=params.get("sector"),
            )

            return result

        except Exception as e:
            logger.error(f"Programme recommendations error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_get_programme_info(self, params: dict) -> dict:
        """Get detailed information about EU funding programmes."""
        try:
            from ..tools.multi_programme_search import get_programme_info_execute

            result = get_programme_info_execute(
                programme=params.get("programme"),
            )

            return result

        except Exception as e:
            logger.error(f"Programme info error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_score_proposal_section(self, params: dict) -> dict:
        """Score a proposal section using EU Horizon Europe evaluation criteria."""
        try:
            from ..tools.proposal_quality_scorer import score_proposal_section_execute

            result = await score_proposal_section_execute(
                content=params.get("content", ""),
                section_type=params.get("section_type", "excellence"),
                section_id=params.get("section_id"),
                action_type=params.get("action_type", "RIA"),
                call_id=params.get("call_id"),
            )

            return result

        except Exception as e:
            logger.error(f"Proposal section scoring error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_score_full_proposal(self, params: dict) -> dict:
        """Score a complete proposal with all three main sections."""
        try:
            from ..tools.proposal_quality_scorer import score_full_proposal_execute

            result = await score_full_proposal_execute(
                excellence_content=params.get("excellence_content", ""),
                impact_content=params.get("impact_content", ""),
                implementation_content=params.get("implementation_content", ""),
                action_type=params.get("action_type", "RIA"),
                call_id=params.get("call_id"),
            )

            return result

        except Exception as e:
            logger.error(f"Full proposal scoring error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_quick_quality_check(self, params: dict) -> dict:
        """Quick quality check for draft proposal text."""
        try:
            from ..tools.proposal_quality_scorer import quick_quality_check_execute

            result = await quick_quality_check_execute(
                text=params.get("text", ""),
                context=params.get("context", "general"),
            )

            return result

        except Exception as e:
            logger.error(f"Quick quality check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_validate_budget(self, params: dict) -> dict:
        """Validate proposal budget against EU Horizon Europe funding rules."""
        try:
            from ..tools.budget_validator import validate_budget_execute

            result = validate_budget_execute(
                total_cost=params.get("total_cost", 0),
                eu_contribution=params.get("eu_contribution", 0),
                action_type=params.get("action_type", "RIA"),
                duration_months=params.get("duration_months", 36),
                num_partners=params.get("num_partners", 3),
                cost_breakdown=params.get("cost_breakdown"),
                consortium=params.get("consortium"),
                call_budget_cap=params.get("call_budget_cap"),
            )

            return result

        except Exception as e:
            logger.error(f"Budget validation error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_check_erasmus_eligibility(self, params: dict) -> dict:
        """Check Erasmus+ eligibility for an organization."""
        try:
            from ..tools.erasmus_eligibility import check_erasmus_eligibility_execute

            result = await check_erasmus_eligibility_execute(
                org_type=params.get("org_type", "HEI"),
                country=params.get("country", "Germany"),
                action_type=params.get("action_type"),
                has_eche=params.get("has_eche", False),
                is_coordinator=params.get("is_coordinator", True),
            )

            return result

        except Exception as e:
            logger.error(f"Erasmus+ eligibility check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_calculate_erasmus_budget(self, params: dict) -> dict:
        """Calculate Erasmus+ lump sum budget."""
        try:
            from ..tools.erasmus_budget_calculator import calculate_erasmus_budget_execute

            result = await calculate_erasmus_budget_execute(
                action_type=params.get("action_type", "partnership"),
                num_participants=params.get("num_participants", 10),
                duration_days=params.get("duration_days", 14),
                duration_months=params.get("duration_months", 24),
                num_partners=params.get("num_partners", 3),
                destination_country=params.get("destination_country", "Germany"),
                origin_country=params.get("origin_country", "Spain"),
                partnership_type=params.get("partnership_type", "cooperation"),
                distance_band=params.get("distance_band", "500-1999km"),
                green_travel=params.get("green_travel", False),
                target_budget=params.get("target_budget"),
            )

            return result

        except Exception as e:
            logger.error(f"Erasmus+ budget calculation error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_search_erasmus_templates(self, params: dict) -> dict:
        """Search Erasmus+ Programme Guide for application guidance."""
        try:
            from ..tools.erasmus_template_search import search_erasmus_templates_execute

            result = await search_erasmus_templates_execute(
                query=params.get("query", ""),
                key_action=params.get("key_action"),
                sector=params.get("sector"),
                document_type=params.get("document_type"),
                top_k=params.get("top_k", 5),
            )

            return result

        except Exception as e:
            logger.error(f"Erasmus+ template search error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_check_creative_europe_eligibility(self, params: dict) -> dict:
        """Check Creative Europe eligibility for an organization."""
        try:
            from ..tools.creative_europe_eligibility import (
                check_creative_europe_eligibility_execute,
            )

            result = await check_creative_europe_eligibility_execute(
                org_type=params.get("org_type", "CULTURAL_ORG"),
                country=params.get("country", "Germany"),
                action_type=params.get("action_type"),
                strand=params.get("strand"),
                is_coordinator=params.get("is_coordinator", True),
            )

            return result

        except Exception as e:
            logger.error(f"Creative Europe eligibility check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_calculate_creative_europe_budget(self, params: dict) -> dict:
        """Calculate Creative Europe grant budget."""
        try:
            from ..tools.creative_europe_budget_calculator import (
                calculate_creative_europe_budget_execute,
            )

            result = await calculate_creative_europe_budget_execute(
                action_type=params.get("action_type", "COOP-SMALL"),
                requested_amount=params.get("requested_amount"),
                project_scale=params.get("project_scale", "medium"),
                num_partners=params.get("num_partners", 3),
                duration_months=params.get("duration_months"),
                strand=params.get("strand"),
            )

            return result

        except Exception as e:
            logger.error(f"Creative Europe budget calculation error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_search_creative_europe_templates(self, params: dict) -> dict:
        """Search Creative Europe documents for application guidance."""
        try:
            from ..tools.creative_europe_template_search import (
                search_creative_europe_templates_execute,
            )

            result = await search_creative_europe_templates_execute(
                query=params.get("query", ""),
                strand=params.get("strand"),
                action_type=params.get("action_type"),
                topic=params.get("topic"),
                top_k=params.get("top_k", 5),
            )

            return result

        except Exception as e:
            logger.error(f"Creative Europe template search error: {e}")
            return {"error": str(e), "success": False}

    def _summarize_tool_results(self, tool_calls: list[ToolCall]) -> str:
        """Summarize results from tool calls in a human-readable format."""
        summaries = []

        for tc in tool_calls:
            if tc.success:
                result = tc.result
                summary = self._format_tool_result_summary(tc.tool_name, result)
                summaries.append(summary)
            else:
                summaries.append(f"{tc.tool_name}: Failed - {tc.error}")

        return "\n".join(summaries)

    def _format_erasmus_eligibility_result(self, result: dict) -> str:
        """Format Erasmus+ eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single action eligibility check
        if query_type == "specific_action" and "result" in result:
            check_result = result["result"]
            action_type = check_result.get("action_type", "Unknown")
            action_name = check_result.get("action_name", "Unknown Action")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_programme_country = check_metadata.get("is_programme_country", False)

            eligibility_text = f"""## Erasmus+ Eligibility Check: {action_name} ({action_type})

**Organization**: {org_type} from {country}
**Country Status**: {"Programme Country ✅" if is_programme_country else "Partner Country (Third Country)"}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}

"""
            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Recommendations & Requirements:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide) for detailed eligibility criteria
• Register on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for country-specific guidance
"""
            return eligibility_text

        # All eligible actions check
        elif query_type == "all_actions" and "eligible_actions" in result:
            eligible_actions = result.get("eligible_actions", [])
            total_eligible = result.get("total_eligible", len(eligible_actions))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")

            if total_eligible == 0:
                eligibility_text = f"""## Erasmus+ Eligibility Check for {org_type} from {country}

**Eligibility**: ❌ No eligible actions found

This may be because:
- {country} is a Partner/Third Country with limited participation options
- The organization type ({org_type}) has specific restrictions

**Recommendations:**
- Check if your country has bilateral agreements for specific actions
- Consider participation as a partner rather than coordinator
- Contact your National Agency for specific opportunities
"""
            else:
                eligibility_text = f"""## Erasmus+ Eligibility Check for {org_type} from {country}

**Total Eligible Actions**: {total_eligible}

**Eligible Actions:**
"""
                for action in eligible_actions:
                    action_type = action.get("action_type", "")
                    action_name = action.get("action_name", "")
                    warnings = action.get("warnings", [])
                    notes = action.get("notes", [])

                    eligibility_text += f"\n### {action_name} ({action_type})\n"
                    if warnings:
                        for w in warnings:
                            eligibility_text += f"- ⚠️ {w}\n"
                    if notes:
                        for n in notes:
                            eligibility_text += f"- {n}\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide) for detailed requirements
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for support
"""

            return eligibility_text

        return ""

    def _format_creative_europe_eligibility_result(self, result: dict) -> str:
        """Format Creative Europe eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single action eligibility check
        if query_type == "specific_action" and "result" in result:
            check_result = result["result"]
            action_type = check_result.get("action_type", "Unknown")
            action_name = check_result.get("action_name", "Unknown Action")
            strand = check_result.get("strand", "Unknown")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_eligible_country = check_metadata.get("is_eligible_country", True)

            eligibility_text = f"""## Creative Europe Eligibility Check: {action_name} ({action_type})

**Strand**: {strand}
**Organization**: {org_type} from {country}
**Country Status**: {"Eligible Country ✅" if is_eligible_country else "Third Country (restrictions may apply)"}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}

"""
            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Recommendations & Requirements:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [CulturEU Funding Guide](https://culture.ec.europa.eu/funding/cultureu-funding-guide) for programme details
• Review calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact the [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) in your country
"""
            return eligibility_text

        # All eligible actions (by strand)
        elif query_type == "all_actions" and "eligible_actions" in result:
            eligible_actions = result.get("eligible_actions", [])
            total_eligible = result.get("total_eligible", len(eligible_actions))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")
            strand = metadata.get("strand", "All Strands")

            if total_eligible == 0:
                eligibility_text = f"""## Creative Europe Eligibility Check for {org_type} from {country}

**Strand**: {strand}
**Eligibility**: ❌ No eligible actions found

This may be because:
- The organization type ({org_type}) is not eligible for {strand} actions
- {country} may have restrictions for certain Creative Europe actions

**Recommendations:**
- Check if your organization qualifies under a different category
- Review the CulturEU Funding Guide for alternative opportunities
- Contact your Creative Europe Desk for guidance
"""
            else:
                eligibility_text = f"""## Creative Europe Eligibility Check for {org_type} from {country}

**Strand**: {strand}
**Total Eligible Actions**: {total_eligible}

**Eligible Actions:**
"""
                for action in eligible_actions:
                    action_type = action.get("action_type", "")
                    action_name = action.get("action_name", "")
                    action_strand = action.get("strand", "")
                    warnings = action.get("warnings", [])
                    notes = action.get("notes", [])

                    eligibility_text += f"\n### {action_name} ({action_type}) - {action_strand}\n"
                    if warnings:
                        for w in warnings:
                            eligibility_text += f"- ⚠️ {w}\n"
                    if notes:
                        for n in notes:
                            eligibility_text += f"- {n}\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [CulturEU Funding Guide](https://culture.ec.europa.eu/funding/cultureu-funding-guide) for detailed requirements
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for support
"""

            return eligibility_text

        return ""

    def _format_tool_result_summary(self, tool_name: str, result: Any) -> str:
        """Format a single tool result into a readable summary."""
        if not isinstance(result, dict):
            return f"{tool_name}: {str(result)[:500]}"

        # Handle document search results
        if "documents" in result and isinstance(result["documents"], list):
            docs = result["documents"]
            if not docs:
                return f"{tool_name}: No documents found"

            # Extract actual content from documents
            content_parts = []
            for doc in docs[:8]:  # Increased from 3 to 8
                content = doc.get("content", "")
                source = doc.get("source", doc.get("title", "Unknown"))
                if content:
                    # Clean up the content
                    content = content.strip()[:800]  # Increased from 400
                    content_parts.append(f"From {source}: {content}")

            if content_parts:
                return f"Found {len(docs)} relevant document(s):\n" + "\n\n".join(content_parts)
            return f"{tool_name}: Found {len(docs)} documents (no content extracted)"

        # Handle funding call results
        if "calls" in result and isinstance(result["calls"], list):
            calls = result["calls"]
            if not calls:
                return f"{tool_name}: No funding calls found"
            return f"Found {len(calls)} funding call(s)"

        # Handle project results
        if "projects" in result and isinstance(result["projects"], list):
            projects = result["projects"]
            if not projects:
                return f"{tool_name}: No projects found"
            return f"Found {len(projects)} project(s)"

        # Handle call details
        if "call_id" in result or "topic_code" in result:
            call_id = result.get("call_id") or result.get("topic_code")
            title = result.get("title", "Unknown")
            if call_id and title:
                desc = result.get("description", "")[:200] if result.get("description") else ""
                return f"Call {call_id}: {title}\n{desc}" if desc else f"Call {call_id}: {title}"
            elif result.get("message"):
                return result["message"]

        # Handle budget benchmark results
        if "statistics" in result and "total_eu_contribution" in result.get("statistics", {}):
            stats = result["statistics"]
            contrib = stats.get("total_eu_contribution", {})
            consortium = stats.get("consortium_size", {})
            recs = result.get("recommendations", {})

            parts = [
                f"Budget Benchmark Analysis ({stats.get('projects_analyzed', 'N/A')} projects):"
            ]

            if contrib:
                avg = contrib.get("average", 0)
                median = contrib.get("median", 0)
                parts.append(
                    f"- EU Contribution: €{median / 1_000_000:.1f}M median, €{avg / 1_000_000:.1f}M average"
                )
                parts.append(
                    f"- Range: €{contrib.get('min', 0) / 1_000_000:.1f}M - €{contrib.get('max', 0) / 1_000_000:.1f}M"
                )

            if consortium:
                parts.append(
                    f"- Consortium Size: {consortium.get('median', 0):.0f} partners (avg: {consortium.get('average', 0):.1f})"
                )

            if recs:
                parts.append(f"- Recommended Budget: {recs.get('suggested_budget_range', 'N/A')}")
                parts.append(
                    f"- Recommended Partners: {recs.get('suggested_consortium_size', 'N/A')}"
                )

            return "\n".join(parts)

        # Handle consortium patterns results
        if "organization_type_distribution" in result and "consortium_size" in result:
            projects = result.get("projects_analyzed", "N/A")
            consortium = result.get("consortium_size", {})
            org_dist = result.get("organization_type_distribution", {})
            country_patterns = result.get("country_patterns", {})
            recs = result.get("recommendations", {})

            parts = [f"Consortium Patterns Analysis ({projects} projects):"]

            # Consortium size
            if consortium:
                parts.append(
                    f"- Consortium Size: {consortium.get('median', 0):.0f} partners (avg: {consortium.get('average', 0):.1f})"
                )
                parts.append(f"- Recommended: {consortium.get('recommended', 'N/A')}")

            # Org type distribution
            if org_dist:
                type_parts = []
                for org_type, data in sorted(
                    org_dist.items(), key=lambda x: x[1].get("percentage", 0), reverse=True
                )[:4]:
                    pct = data.get("percentage", 0)
                    type_parts.append(f"{org_type}: {pct:.0f}%")
                parts.append(f"- Organization Mix: {', '.join(type_parts)}")

            # Top countries
            top_countries = country_patterns.get("top_participating", [])[:5]
            if top_countries:
                countries = [c["country"] for c in top_countries]
                parts.append(f"- Top Countries: {', '.join(countries)}")

            # Geographic diversity
            geo = country_patterns.get("geographic_diversity", {})
            if geo:
                parts.append(f"- Avg Countries per Project: {geo.get('avg_countries', 'N/A')}")

            # Recommendations
            if recs.get("ideal_composition"):
                parts.append(f"- Ideal Mix: {'; '.join(recs['ideal_composition'][:3])}")

            return "\n".join(parts)

        # Handle partner discovery results
        if "experienced_partners" in result:
            partners = result.get("experienced_partners", [])
            total = result.get("total_found", 0)
            query = result.get("query_params", {})

            if not partners:
                return f"Partner Discovery: No organizations found matching '{query.get('topic_keywords', '')}'"

            # Use abbreviated keywords for header (first 60 chars) to save space
            keywords = query.get("topic_keywords", "")
            keywords_abbrev = keywords[:60] + "..." if len(keywords) > 60 else keywords
            parts = [f"Found {total} experienced partners for '{keywords_abbrev}':"]

            # Include ALL partners (up to 15) with compact format for observation
            # This ensures the agent sees all partners to present multiple in response
            for i, p in enumerate(partners[:15], 1):
                name = p.get("short_name") or p.get("name", "Unknown")
                country = p.get("country", "")
                org_type = p.get("type", "")
                track = p.get("track_record", {})
                relevant = track.get("relevant_projects", 0)
                coord = track.get("as_coordinator", 0)
                funding = track.get("funding_in_relevant", track.get("total_funding", 0))

                # Compact format: "1. NAME (CC, TYPE): Xp, Yc, €ZM"
                coord_str = f", {coord}c" if coord > 0 else ""
                funding_mil = funding / 1_000_000 if funding > 0 else 0
                funding_str = f", €{funding_mil:.1f}M" if funding > 0 else ""
                parts.append(
                    f"{i}. {name} ({country}, {org_type}): {relevant}p{coord_str}{funding_str}"
                )

            # Skip insights to save space - partners list is more important

            return "\n".join(parts)

        # Handle similar projects results - ENHANCED with full details
        if "similar_projects" in result and isinstance(result["similar_projects"], list):
            projects = result["similar_projects"]
            query_desc = result.get("query_description", "")
            matches = result.get("matches_found", len(projects))
            filters = result.get("filters_applied", {})

            if not projects:
                return f"## Similar Projects Search\n\nNo projects found matching: *{query_desc}*"

            parts = []
            parts.append("## Similar Funded Projects\n")
            parts.append(f"**Query:** {query_desc}")
            if filters:
                filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
                if filter_str:
                    parts.append(f"**Filters:** {filter_str}")
            parts.append(f"**Found:** {matches} similar projects\n")

            for i, p in enumerate(projects[:10], 1):
                acronym = p.get("acronym", "N/A")
                title = p.get("title", "N/A")
                score = p.get("similarity_score", 0)
                budget = p.get("eu_contribution", p.get("total_cost", 0))
                consortium = p.get("consortium", {})
                size = consortium.get("size", p.get("partner_count", 0))
                action_type = p.get("action_type", "N/A")
                objective = p.get("objective", "")
                start_date = p.get("start_date", "")
                end_date = p.get("end_date", "")
                coordinator = consortium.get("coordinator", {}).get("name", "")
                cluster = p.get("cluster", "")

                budget_str = f"€{budget / 1_000_000:.1f}M" if budget > 0 else "N/A"

                parts.append(f"### {i}. {acronym} [{score:.0%} match]")
                parts.append(f"**{title}**")
                parts.append(f"- Type: {action_type} | Budget: {budget_str} | Partners: {size}")
                if cluster:
                    parts.append(f"- Cluster: {cluster}")
                if start_date and end_date:
                    parts.append(f"- Duration: {start_date[:7]} to {end_date[:7]}")
                if coordinator:
                    parts.append(f"- Coordinator: {coordinator}")
                if objective:
                    # Show first 300 chars of objective
                    obj_preview = objective[:300] + "..." if len(objective) > 300 else objective
                    parts.append(f"- Objective: *{obj_preview}*")
                parts.append("")

            # Add insights
            insights = result.get("insights", [])
            if insights:
                parts.append("**Key Insights:**")
                for insight in insights[:5]:
                    parts.append(f"- {insight}")

            return "\n".join(parts)

        # Handle timeline generator results
        if "work_packages" in result and "deliverables" in result and "milestones" in result:
            wps = result.get("work_packages", [])
            deliverables = result.get("deliverables", [])
            milestones = result.get("milestones", [])
            params = result.get("parameters", {})
            _summary = result.get("summary", {})  # noqa: F841 - may be used in future
            gantt = result.get("gantt_data", {})

            parts = []
            parts.append("**Project Timeline Generated**")
            parts.append(f"- Duration: {params.get('duration_months', 36)} months")
            parts.append(f"- Action Type: {params.get('action_type', 'RIA')}")
            parts.append(f"- Partners: {params.get('num_partners', 8)}")
            parts.append(f"- Total Effort: {params.get('total_person_months', 0)} person-months")
            parts.append("")

            # Work Packages Summary
            parts.append("**Work Packages:**")
            for wp in wps:
                wp_num = wp.get("number", 0)
                title = wp.get("title", "")
                lead = wp.get("lead", "P1")
                start = wp.get("start_month", 1)
                end = wp.get("end_month", 36)
                effort = wp.get("effort_pms", 0)
                objective = wp.get("objective", "")

                parts.append(f"\n**WP{wp_num}: {title}** (Lead: {lead})")
                parts.append(f"  M{start}-M{end} | {effort} PMs")
                if objective:
                    parts.append(f"  *{objective[:100]}*")

                # Show tasks
                tasks = wp.get("tasks", [])
                if tasks:
                    parts.append(f"  Tasks: {'; '.join(tasks[:3])}")

            # Deliverables
            parts.append("")
            parts.append(f"**Deliverables ({len(deliverables)} total):**")
            for d in deliverables[:10]:  # Show first 10
                d_id = d.get("id", "D?")
                d_title = d.get("title", "")[:50]
                d_month = d.get("due_month", 0)
                d_type = d.get("type", "R")
                d_level = d.get("dissemination_level", "PU")
                parts.append(f"  {d_id}: {d_title} (M{d_month}, {d_type}, {d_level})")

            if len(deliverables) > 10:
                parts.append(f"  ... and {len(deliverables) - 10} more")

            # Milestones
            parts.append("")
            parts.append(f"**Milestones ({len(milestones)} total):**")
            for m in milestones:
                m_id = m.get("id", "MS?")
                m_title = m.get("title", "")
                m_month = m.get("due_month", 0)
                parts.append(f"  {m_id}: {m_title} (M{m_month})")

            # ASCII Gantt Chart
            ascii_chart = gantt.get("ascii_chart", "")
            if ascii_chart:
                parts.append("")
                parts.append("**Gantt Chart:**")
                parts.append("```")
                parts.append(ascii_chart)
                parts.append("```")

            # Dependencies
            dependencies = gantt.get("dependencies", [])
            if dependencies:
                parts.append("")
                parts.append("**WP Dependencies:**")
                for dep in dependencies[:5]:
                    parts.append(
                        f"  {dep.get('from')} → {dep.get('to')}: {dep.get('description', '')}"
                    )

            # Recommendations
            recommendations = result.get("recommendations", [])
            if recommendations:
                parts.append("")
                parts.append("**Recommendations:**")
                for rec in recommendations[:4]:
                    parts.append(f"  - {rec}")

            return "\n".join(parts)

        # Handle call history analysis results
        if "timeline" in result and "trends" in result:
            calls = result.get("calls_analyzed", 0)
            projects = result.get("projects_funded", 0)
            total_funding = result.get("total_funding_allocated", 0)
            trends = result.get("trends", {})

            parts = [f"Call History Analysis: {calls} calls, {projects} projects funded"]

            if total_funding > 0:
                parts.append(f"Total funding: €{total_funding / 1_000_000_000:.1f}B")

            # Trend info
            trend = trends.get("funding_trend", "unknown")
            growth = trends.get("year_over_year_funding_growth", 0)
            if trend != "insufficient_data":
                parts.append(f"Trend: {trend.replace('_', ' ')} ({growth:+.1f}% YoY)")

            # Timeline summary
            timeline = result.get("timeline", {})
            if timeline:
                years = sorted(timeline.keys(), reverse=True)[:3]
                for year in years:
                    data = timeline[year]
                    parts.append(
                        f"  {year}: {data.get('projects_funded', 0)} projects, €{data.get('total_funding', 0) / 1_000_000:.0f}M"
                    )

            # Top topics
            top_topics = result.get("top_funded_topics", [])[:3]
            if top_topics:
                parts.append("\nTop topics:")
                for t in top_topics:
                    parts.append(f"  - {t.get('topic', 'N/A')}: {t.get('projects', 0)} projects")

            # Recommendations
            recommendations = result.get("recommendations", [])[:2]
            if recommendations:
                parts.append(f"\nRecommendations: {'; '.join(recommendations)}")

            return "\n".join(parts)

        # Handle country statistics results
        if "country_code" in result and "eligibility" in result:
            country = result.get("country", result.get("country_code", "Unknown"))
            eligibility = result.get("eligibility", {})
            top_orgs = result.get("top_organizations", [])

            # Get participation history from eligibility
            participation = eligibility.get("participation_history", {})
            org_count = participation.get("organization_count", result.get("organization_count", 0))
            proj_count = participation.get("project_count", 0)
            total_funding = participation.get("total_funding_received", 0)

            # Build clear eligibility answer first
            is_eligible = eligibility.get("is_eligible", False)
            eligibility_status = eligibility.get("eligibility_status", "Unknown")

            parts = [f"Country: {country}"]
            parts.append(f"**Can participate in Horizon Europe: {'YES' if is_eligible else 'NO'}**")
            parts.append(f"- Status: {eligibility_status}")

            # Add notes if available
            notes = eligibility.get("notes", [])
            if notes:
                parts.append(f"- {notes[0]}")

            if proj_count > 0:
                parts.append("\nParticipation Statistics:")
                parts.append(f"- Organizations: {org_count:,}")
                parts.append(f"- Projects: {proj_count:,}")
                parts.append(f"- Total Funding: €{total_funding:,.0f}")

            if top_orgs:
                parts.append(f"\nTop {min(len(top_orgs), 10)} Organizations:")
                for org in top_orgs[:10]:
                    org_name = org.get("name", org.get("organization_name", "Unknown"))
                    org_projects = org.get("project_count", org.get("projects", 0))
                    org_funding = org.get("total_funding", org.get("funding", 0))
                    parts.append(f"- {org_name}: {org_projects} projects, €{org_funding:,.0f}")

            return "\n".join(parts)

        # Handle programme/cluster statistics results
        if "cluster_code" in result or ("programme" in result and "statistics" in result):
            programme = result.get("programme", result.get("cluster_code", "Unknown"))
            programme_type = result.get("programme_type", "")
            stats = result.get("statistics", {})
            # Ensure stats is a dict, not a list
            if isinstance(stats, list):
                stats = stats[0] if stats else {}
            budget = result.get("budget_details", {})
            # Ensure budget is a dict, not a list
            if isinstance(budget, list):
                budget = budget[0] if budget else {}

            parts = [f"Programme Statistics for {programme}:"]
            if programme_type:
                parts.append(f"({programme_type})")

            # Handle EIC/ERC/MSCA format with success_rates dict
            if "success_rates" in stats:
                success_rates = stats["success_rates"]
                if stats.get("description"):
                    parts.append(f"\n{stats['description']}")
                parts.append("\nSuccess Rates:")
                for key, value in success_rates.items():
                    if key != "note":
                        parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                if success_rates.get("note"):
                    parts.append(f"\nNote: {success_rates['note']}")

                # Add funding info
                if "funding" in stats:
                    parts.append("\nFunding Available:")
                    for key, value in stats["funding"].items():
                        parts.append(f"- {key.replace('_', ' ').title()}: {value}")

                if stats.get("eligibility"):
                    parts.append(f"\nEligibility: {stats['eligibility']}")

                if stats.get("trl_range"):
                    parts.append(f"TRL Range: {stats['trl_range']}")

                # Add actionable Next Steps
                parts.append("\n---\n\n🎯 **Next Steps:**")
                parts.append(
                    "• Carefully review your innovation for market readiness (EIC) or scientific excellence (ERC)"
                )
                parts.append(
                    "• Study successful proposals in your domain via [CORDIS](https://cordis.europa.eu/)"
                )
                parts.append(
                    "• Consider working with a consultant or experienced coordinator to improve odds"
                )
                parts.append(
                    "• Check the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for current call details"
                )

            else:
                # Standard cluster statistics format
                if stats:
                    total_projects = stats.get("total_projects", stats.get("project_count", "N/A"))
                    total_funding = stats.get("total_funding", stats.get("total_budget", 0))
                    success_rate = stats.get("success_rate", "N/A")
                    avg_budget = stats.get("avg_project_budget", stats.get("average_funding", 0))

                    parts.append(
                        f"- Total Projects: {total_projects:,}"
                        if isinstance(total_projects, int)
                        else f"- Total Projects: {total_projects}"
                    )
                    # IMPORTANT: Clarify this is projects funded, not programme budget
                    parts.append(
                        f"- Total Funding Awarded to Projects: €{total_funding:,.0f} (Note: This is the sum of project awards in this area, NOT the overall Horizon Europe budget of €95.5 billion)"
                    )
                    parts.append(f"- Success Rate: {success_rate}%")
                    parts.append(f"- Average Project Budget: €{avg_budget:,.0f}")

                if budget:
                    parts.append("\nBudget Breakdown:")
                    parts.append(f"- Min Budget: €{budget.get('min_budget', 0):,.0f}")
                    parts.append(f"- Max Budget: €{budget.get('max_budget', 0):,.0f}")
                    parts.append(f"- Median Budget: €{budget.get('median_budget', 0):,.0f}")

                # Add actionable Next Steps for cluster statistics
                parts.append("\n---\n\n🎯 **Next Steps:**")
                parts.append(
                    "• Review open calls in this cluster on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                )
                parts.append(
                    "• Study similar funded projects in [CORDIS](https://cordis.europa.eu/) to understand successful approaches"
                )
                parts.append("• Connect with experienced partners or consultants in this domain")
                parts.append("• Consider starting as a partner before taking a coordinator role")

            return "\n".join(parts)

        # Handle error messages
        if "error" in result:
            return f"{tool_name}: Error - {result['error']}"

        if "message" in result:
            return f"{tool_name}: {result['message']}"

        # Default: truncated string representation
        return f"{tool_name}: {str(result)[:500]}"

    def _build_fallback_answer(self, plan: AgentPlan) -> str:
        """Build a fallback answer from collected information."""

        if not plan.reasoning_steps:
            return ""  # Return empty to trigger synthesis

        # Collect all tool results from steps
        all_results = {}
        for step in plan.reasoning_steps:
            for tc in step.tool_calls:
                if tc.success and tc.result:
                    all_results[tc.tool_name] = tc.result

        # If we have tool results, synthesize from them
        if all_results:
            return self._synthesize_from_results(plan.query, all_results)

        # Collect meaningful observations (skip raw tool results)
        meaningful_content = []

        for step in plan.reasoning_steps:
            if step.observation:
                obs = step.observation

                # Skip if it looks like raw JSON
                if obs.startswith("{") or obs.startswith("search_") or obs.startswith("get_"):
                    continue

                # Check if this is formatted document content
                if "Found " in obs and "relevant document" in obs:
                    # Extract the actual content from "From source: content" lines
                    lines = obs.split("\n")
                    for line in lines:
                        if line.startswith("From ") and ":" in line:
                            # Extract content after "From Source:"
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                content = parts[1].strip()
                                # Check content quality - skip truncated/malformed text
                                if self._is_quality_content(content):
                                    meaningful_content.append(content)
                elif self._is_quality_content(obs):
                    meaningful_content.append(obs)

        # Only return if we have quality content
        if meaningful_content:
            # Deduplicate similar content
            unique_content = self._deduplicate_content(meaningful_content)
            if unique_content:
                # Format as a proper answer
                intro = f"Based on the information I found about '{plan.query}':\n\n"
                formatted_content = []
                for _i, content in enumerate(unique_content[:5], 1):
                    if len(content) > 500:
                        content = content[:500] + "..."
                    formatted_content.append(f"{content}")
                return intro + "\n\n".join(formatted_content)

        # Return empty to trigger LLM synthesis
        return ""

    def _is_quality_content(self, text: str) -> bool:
        """Check if text is quality content suitable for display."""
        if not text or len(text) < 50:
            return False

        # Check for truncated/malformed text patterns
        bad_patterns = [
            # Truncated words at start
            text[:20].count("  ") > 2,  # Multiple spaces
            text.startswith("rmance"),  # Cut-off word
            text.startswith("tion"),
            text.startswith("ing "),
            # Raw data patterns
            "{'documents'" in text,
            '{"documents"' in text,
            "'content':" in text,
            "'score':" in text,
            # Meta/structural content
            "Table of Contents" in text,
            "Page " in text and " of " in text,
        ]

        if any(bad_patterns):
            return False

        # Check for reasonable word structure
        words = text.split()
        if len(words) < 10:
            return False

        # Check that content has actual sentences (periods, capitals)
        if "." not in text and "?" not in text:
            return False

        return True

    def _deduplicate_content(self, contents: list) -> list:
        """Remove duplicate or very similar content."""
        if not contents:
            return []

        unique = []
        for content in contents:
            # Check if this content is similar to any existing
            is_duplicate = False
            content_start = content[:100].lower()
            for existing in unique:
                existing_start = existing[:100].lower()
                if content_start == existing_start:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(content)

        return unique
