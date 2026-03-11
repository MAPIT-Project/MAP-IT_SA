# isort: skip_file
"""
Tool registry and routing for ToolAwareAgent.
Extracted from tool_aware_agent.py for maintainability.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


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


class ToolRegistryMixin:
    """Mixin providing tool registration and routing for ToolAwareAgent."""

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

        # Similar funded projects tool (semantic search) - FOR SEMANTIC SIMILARITY
        self.register_tool(
            Tool(
                name="get_similar_funded_projects",
                description="""Find projects semantically similar to a concept, description, or proposal idea using AI embeddings.

**USE THIS TOOL WHEN**:
- User asks for projects "similar to" a concept/topic (e.g., "projects similar to developing sustainable aviation fuels")
- User describes a project idea and wants semantically related projects
- User wants to find projects that conceptually relate to their idea (finds biofuels, green aviation when searching for "sustainable aviation fuels")
- User is writing a proposal and wants similar funded projects to learn from
- User asks about TRENDS or THEMES in a broad research area (e.g., "trends in trustworthy AI", "what projects illustrate responsible AI")
- User asks about a BROAD CONCEPT where keyword matching would miss relevant projects (e.g., "trustworthy AI", "sustainable mobility", "digital health innovations")
- The query topic is abstract or multi-faceted (e.g., "trustworthy AI" encompasses fairness, explainability, robustness, privacy — keyword search only finds exact matches)

**DO NOT USE FOR**: Simple keyword searches with SPECIFIC technical terms like "find projects about graphene" or "show me quantum computing projects" - use search_projects instead.

**PREFER THIS OVER search_projects WHEN**: The topic is conceptual, thematic, or trend-related. Semantic search understands meaning and finds conceptually related projects even without exact keyword matches.""",
                category=ToolCategory.PROJECTS,
                parameters={
                    "description": "Required: Concept, topic description, or proposal idea to find similar projects for (min 20 chars)",
                    "cluster": "Optional: Cluster code filter (CL4, CL5, EIC, etc.)",
                    "action_type": "Optional: Action type filter (RIA, IA, CSA)",
                    "min_budget": "Optional: Minimum EU contribution filter",
                    "max_budget": "Optional: Maximum EU contribution filter",
                    "year_from": "Optional: Filter for projects starting from year",
                    "limit": "Optional: Number of results (default 10)",
                },
                examples=[
                    "get_similar_funded_projects(description='developing sustainable aviation fuels')",
                    "get_similar_funded_projects(description='AI-powered diagnostic system for early cancer detection using deep learning on medical imaging data')",
                    "get_similar_funded_projects(description='Novel green hydrogen production using advanced electrolyzers', cluster='CL5')",
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
                description="""Search the CORDIS database for funded Horizon Europe projects by topic/keywords. Supports sorting by EC contribution, relevance, or date.

**USE THIS TOOL FOR**: Keyword-based project searches with SPECIFIC technical terms like "find projects about graphene", "show me quantum computing projects", "wind energy operations and maintenance"
**DO NOT USE FOR**:
- Queries asking for "similar to [concept]" or semantic similarity → use get_similar_funded_projects
- Queries about BROAD CONCEPTS, THEMES, or TRENDS (e.g., "trustworthy AI", "responsible AI", "sustainable mobility") → use get_similar_funded_projects (semantic search)
- Queries like "trends in X" or "what projects illustrate X" → use get_similar_funded_projects
**Returns**: List of funded projects matching the keywords with titles, budgets, consortiums, descriptions, and DOI links.

**SEARCH TIPS**:
- Works best with SPECIFIC technical keywords: "machine learning", "neural network", "graphene", "quantum computing"
- Short acronyms like "AI", "ML", "IoT", "HPC" are supported but may benefit from expanded terms
- Combine specific terms for better results: "AI healthcare diagnostics" rather than just "AI"
- The search uses full-text matching on project titles, objectives, and topics
- Use sort_by='ec_contribution' to find projects with the largest EU funding
- **To get partner/consortium details**: After finding projects, call get_project_partners(project_id=<id>) for each project

This is the PRIMARY tool for finding projects by SPECIFIC keyword matching. For broad/conceptual topics, use get_similar_funded_projects instead.""",
                category=ToolCategory.PROJECTS,
                parameters={
                    "keywords": "Required: Keywords/topic to search for (e.g., 'machine learning healthcare', 'quantum computing', 'green hydrogen')",
                    "programme": "Optional: Filter by programme (Horizon Europe, EIC, ERC, etc.)",
                    "country": "Optional: Filter by coordinator/participant country",
                    "limit": "Optional: Number of results (default 10)",
                    "sort_by": "Optional: Sort results by 'relevance' (default), 'ec_contribution' (largest EU funding first), 'total_cost' (largest budget first), or 'start_date' (newest first)",
                },
                examples=[
                    "search_projects(keywords='machine learning healthcare diagnostics')",
                    "search_projects(keywords='artificial intelligence robotics')",
                    "search_projects(keywords='renewable energy', country='Germany')",
                    "search_projects(keywords='deep learning computer vision', limit=15)",
                    "search_projects(keywords='quantum computing', sort_by='ec_contribution', limit=3)",
                ],
            )
        )

        self.register_tool(
            Tool(
                name="get_project_details",
                description="Get detailed information about a specific project including full partner list with names, countries, and roles. USE THIS when you need complete project info or partner/consortium details for a known project.",
                category=ToolCategory.PROJECTS,
                parameters={"project_id": "The project identifier or acronym"},
                examples=[
                    "get_project_details(project_id='101000000')",
                    "get_project_details(project_id='MAPIT')",
                ],
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
                description="Find and LIST all projects an organization has participated in. Shows project details (title, budget, status, role). USE THIS when the user wants to SEE/LIST the actual projects. For counting or statistics (how many projects, coordinator count, total funding), use get_organization_stats instead — it is faster and more accurate.",
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

        # Project partners tool
        self.register_tool(
            Tool(
                name="get_project_partners",
                description="""Get the full list of partner organizations in a specific project.

**USE THIS WHEN USER ASKS:**
- "Who are the partners of project X?" / "List consortium members of X"
- "Which organizations participate in X?"
- "Show me the partners of MAPIT and UDENE"
- "Do projects X and Y share any common partners?"

Returns: Full partner list with names, countries, roles (coordinator/participant), activity type, SME status, and EC contribution per partner.""",
                category=ToolCategory.PROJECTS,
                parameters={
                    "project_id": "Project ID, RCN, or acronym (e.g., 'MAPIT', '101158945')",
                },
                examples=[
                    "get_project_partners(project_id='MAPIT')",
                    "get_project_partners(project_id='101158945')",
                    "get_project_partners(project_id='UDENE')",
                ],
            )
        )

        # Organization statistics tool
        self.register_tool(
            Tool(
                name="get_organization_stats",
                description="""Get aggregate statistics for an organization: total project count, coordinator count, total funding, active research clusters.

**USE THIS WHEN USER ASKS:**
- "How many projects does X have?" / "How many projects has TU Munich participated in?"
- "Is X a coordinator?" / "How often does X coordinate?"
- "What is X's total funding?" / "How much EU funding has X received?"
- "What clusters does X work in?"

Returns: Organization name, country, project count, coordinator count, total funding, active clusters, and sample recent projects.""",
                category=ToolCategory.STATISTICS,
                parameters={
                    "organization_name": "Full or partial name of the organization (e.g., 'TECHNISCHE UNIVERSITAET MUENCHEN', 'TU Munich', 'Fraunhofer')",
                },
                examples=[
                    "get_organization_stats(organization_name='TECHNISCHE UNIVERSITAET MUENCHEN')",
                    "get_organization_stats(organization_name='Fraunhofer')",
                    "get_organization_stats(organization_name='CNRS')",
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

        # EU4Health specific tools
        self.tools["check_eu4health_eligibility"] = Tool(
            name="check_eu4health_eligibility",
            description="Check if an organization is eligible for EU4Health actions. Covers Action Grants (AG), Joint Actions (JA), Operating Grants (OG), and Procurement. Considers organization type (hospital, research, NGO, public authority), country eligibility, and action-specific requirements. Use for eligibility questions about EU4Health.",
            category=ToolCategory.CALLS,
            parameters={
                "org_type": "Organization type: HEALTHCARE_PROVIDER, RESEARCH, UNIVERSITY, PUBLIC_AUTHORITY, NGO, PATIENT_ORG, PROFESSIONAL_ORG, ENTERPRISE, SME, INTERNATIONAL_ORG",
                "country": "Country of the organization (e.g., 'Germany', 'France', 'Poland')",
                "action_type": "Optional: Specific action type (AG, PJ, JA, DG, OG, FPA, PROC). If not provided, returns all eligible actions.",
                "strand": "Optional: EU4Health strand (CRISIS, PREVENTION, HEALTH_SYSTEMS, DIGITAL)",
            },
            examples=[
                "check_eu4health_eligibility(org_type='HEALTHCARE_PROVIDER', country='Germany', action_type='AG')",
                "check_eu4health_eligibility(org_type='PUBLIC_AUTHORITY', country='France', action_type='JA')",
                "check_eu4health_eligibility(org_type='NGO', country='Spain')  # Returns all eligible actions",
            ],
        )

        self.tools["search_eu4health_templates"] = Tool(
            name="search_eu4health_templates",
            description="Search EU4Health documents (Annual Work Programmes, Regulation) for application guidance, eligibility criteria, and programme information. Use for EU4Health application questions.",
            category=ToolCategory.DOCUMENTS,
            parameters={
                "query": "What to search for (e.g., 'joint action eligibility', 'cancer prevention funding')",
                "strand": "Optional: Filter by CRISIS, PREVENTION, HEALTH_SYSTEMS, or DIGITAL",
                "action_type": "Optional: Filter by action type (AG, JA, OG, etc.)",
                "topic": "Optional: Specific topic (eligibility, budget, evaluation)",
                "top_k": "Number of results (default: 5)",
            },
            examples=[
                "search_eu4health_templates(query='joint action requirements for Member States')",
                "search_eu4health_templates(query='cancer prevention funding opportunities', strand='PREVENTION')",
                "search_eu4health_templates(query='digital health EHDS', strand='DIGITAL')",
            ],
        )

        # Digital Europe specific tools
        self.tools["check_digital_europe_eligibility"] = Tool(
            name="check_digital_europe_eligibility",
            description="Check if an organization is eligible for Digital Europe Programme funding. Covers 6 Specific Objectives: HPC (High Performance Computing), AI (Artificial Intelligence), Cybersecurity, Skills (Advanced Digital Skills), Deployment (EDIHs), and Semiconductors (Chips Act). Considers organization type (SME, startup, research, EDIH, HPC center, public authority), country eligibility (EU + EEA + associated countries), and objective-specific requirements. Use for eligibility questions about Digital Europe.",
            category=ToolCategory.CALLS,
            parameters={
                "org_type": "Organization type: SME, STARTUP, LARGE_ENTERPRISE, RESEARCH, UNIVERSITY, PUBLIC_AUTHORITY, EDIH, HPC_CENTER, NGO, COMPETENCE_CENTER, HEALTHCARE, EDUCATION_PROVIDER",
                "country": "Country of the organization (e.g., 'Germany', 'France', 'Poland')",
                "objective": "Optional: Specific objective (HPC, AI, CYBERSECURITY, SKILLS, DEPLOYMENT, SEMICONDUCTORS). If not provided, returns all eligible objectives.",
                "action_type": "Optional: Action type filter (grant, procurement)",
            },
            examples=[
                "check_digital_europe_eligibility(org_type='SME', country='Germany', objective='AI')",
                "check_digital_europe_eligibility(org_type='STARTUP', country='France', objective='CYBERSECURITY')",
                "check_digital_europe_eligibility(org_type='EDIH', country='Spain')  # Returns all eligible objectives",
                "check_digital_europe_eligibility(org_type='RESEARCH', country='Switzerland', objective='HPC')",
            ],
        )

        # LIFE Programme specific tools
        self.tools["check_life_eligibility"] = Tool(
            name="check_life_eligibility",
            description="Check if an organization is eligible for LIFE Programme funding. Covers 4 sub-programmes: NAT (Nature and Biodiversity), ENV (Circular Economy and Quality of Life), CCA (Climate Change Mitigation and Adaptation), and CET (Clean Energy Transition). Considers organization type (public authority, NGO, SME, research), country eligibility (EU + EEA + associated countries), and sub-programme specific requirements. Use for eligibility questions about LIFE Programme, biodiversity conservation, environmental protection, climate action, and clean energy projects.",
            category=ToolCategory.CALLS,
            parameters={
                "org_type": "Organization type: PUBLIC_AUTHORITY, LOCAL_AUTHORITY, NGO, ENVIRONMENTAL_NGO, RESEARCH, UNIVERSITY, SME, LARGE_ENTERPRISE, INTERNATIONAL_ORG, ASSOCIATION, FOUNDATION, PARK_AUTHORITY",
                "country": "Country of the organization (e.g., 'Germany', 'France', 'Poland')",
                "subprogramme": "Optional: Specific sub-programme (NAT, ENV, CCA, CET). If not provided, returns all eligible sub-programmes.",
                "project_type": "Optional: Project type filter (SAP, SIP, SNAP, TA, OG)",
            },
            examples=[
                "check_life_eligibility(org_type='NGO', country='Germany', subprogramme='NAT')",
                "check_life_eligibility(org_type='PUBLIC_AUTHORITY', country='France', subprogramme='CCA')",
                "check_life_eligibility(org_type='ENVIRONMENTAL_NGO', country='Italy')  # Returns all eligible sub-programmes",
                "check_life_eligibility(org_type='SME', country='Spain', subprogramme='CET', project_type='SAP')",
            ],
        )

        self.tools["search_life_templates"] = Tool(
            name="search_life_templates",
            description="Search LIFE Programme documents (Multi-Annual Work Programme, regulations, guidance) for application guidance, eligibility criteria, and programme information. Use for LIFE application questions, sub-programme details, project types, and funding rules.",
            category=ToolCategory.DOCUMENTS,
            parameters={
                "query": "What to search for (e.g., 'nature conservation eligibility', 'climate adaptation funding')",
                "subprogramme": "Optional: Filter by NAT, ENV, CCA, or CET",
                "section": "Optional: Specific section (nature, circular_economy, climate, energy, eligibility, budget, evaluation)",
                "top_k": "Number of results (default: 5)",
            },
            examples=[
                "search_life_templates(query='Natura 2000 conservation project requirements')",
                "search_life_templates(query='climate adaptation funding criteria', subprogramme='CCA')",
                "search_life_templates(query='clean energy transition co-financing rates', subprogramme='CET')",
            ],
        )

        # Pagination tool for cached project results
        self.tools["show_cached_projects"] = Tool(
            name="show_cached_projects",
            description=(
                "Show the NEXT batch of projects from a previous project search. "
                "Use this when the user asks to 'show more', 'next page', 'see more projects', "
                "'keep going', etc. after a project search. This tool retrieves the next page "
                "from cached results — do NOT re-run the search tools."
            ),
            category=ToolCategory.PROJECTS,
            parameters={},
            examples=[
                "show_cached_projects()",
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
            elif tool_name == "get_project_details":
                return await self._tool_get_project_details(params)
            elif tool_name == "find_similar_projects":
                return await self._tool_find_similar_projects(params)
            elif tool_name == "find_semantically_similar_projects":
                return await self._tool_find_semantically_similar_projects(params)
            elif tool_name == "find_organization_projects":
                return await self._tool_find_organization_projects(params)
            elif tool_name == "get_project_partners":
                return await self._tool_get_project_partners(params)
            elif tool_name == "get_organization_stats":
                return await self._tool_get_organization_stats(params)
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
            # EU4Health specific tools
            elif tool_name == "check_eu4health_eligibility":
                return await self._tool_check_eu4health_eligibility(params)
            elif tool_name == "search_eu4health_templates":
                return await self._tool_search_eu4health_templates(params)
            # Digital Europe specific tools
            elif tool_name == "check_digital_europe_eligibility":
                return await self._tool_check_digital_europe_eligibility(params)
            # LIFE Programme specific tools
            elif tool_name == "check_life_eligibility":
                return await self._tool_check_life_eligibility(params)
            elif tool_name == "search_life_templates":
                return await self._tool_search_life_templates(params)
            elif tool_name == "show_cached_projects":
                return self._tool_show_cached_projects()
            else:
                return {"error": f"Tool {tool_name} not implemented"}
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}

    # ==================== Tool Implementations ====================
    # _extract_cluster_param is provided by ToolExecutorsMixin.
