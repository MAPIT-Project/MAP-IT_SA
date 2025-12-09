# Horizon Europe AI Assistant - Question Categories & Capabilities

## Overview
This document categorizes all types of questions that the enhanced RAG system can answer, providing a comprehensive reference for testing and utilizing the AI tool's full capabilities. The system uses a **V3 Simplified Architecture** with a single agentic loop (ToolAwareAgent) that autonomously selects from 20 specialized tools to answer queries.

**Key Architecture Features:**
- **Single Agentic Loop**: No intent classification - the agent decides which tools to use
- **20 Specialized Tools**: Covering statistics, comparisons, documents, calls, projects, and proposal support
- **Hybrid Graph+SQL Tools**: 7 tools use combined Neo4j + PostgreSQL for comprehensive results
- **Semantic Search**: 768-dim embeddings (Google text-embedding-004) for meaning-based matching
- **Multi-Source Fusion**: Results combined using RRF, weighted averaging, and combined scoring

---

## Part 1: Query Categories

### 1. Call-Specific Questions
**Description**: Questions targeting specific Horizon Europe call or topic identifiers. Uses local call database with on-demand API enrichment for missing details.

**Examples**:
- "What are the eligibility criteria for HORIZON-CL4-2024-DATA-01-01?"
- "Tell me about the budget and deadlines for HORIZON-CL5-2024-CLIMATE-01"
- "What are the evaluation criteria for HORIZON-HLTH-2024-DISEASE-03-02?"
- "Explain the submission process for HORIZON-EIC-2024-ACCELERATOR-01"
- "What are the specific requirements for HORIZON-ERC-2024-SYG-01?"

**Data Sources**: Local funding_calls table, EU Funding & Tenders Portal API (enrichment)
**Tools Used**: `search_funding_calls`, `get_call_details`
**Handled By**: ToolAwareAgent with CallEnrichmentService

### 2. Cluster-Specific Questions
**Description**: Questions about specific Horizon Europe clusters (CLUSTER-1 through CLUSTER-6) or programmes. Automatic cluster inference from keywords.

**Examples**:
- "What health cluster calls are available for 2024?"
- "Show me digital transformation topics in Horizon Europe"
- "What climate and energy calls are open now?"
- "Tell me about the European Innovation Council (EIC) opportunities"
- "What are the ERC grants available for frontier research?"

**Cluster Mapping**:
| Cluster | Focus Area | Keywords |
|---------|------------|----------|
| CLUSTER-1 | Health | cancer, disease, clinical, pharma, medical |
| CLUSTER-2 | Culture & Society | culture, heritage, democracy, social |
| CLUSTER-4 | Digital | AI, digital, cyber, quantum, data, computing |
| CLUSTER-5 | Climate & Energy | hydrogen, solar, wind, battery, climate, energy |
| CLUSTER-6 | Food & Bio | agriculture, food, biodiversity, bioeconomy |

**Data Sources**: Work Programme cluster sections, Neo4j graph (cluster relationships)
**Tools Used**: `search_funding_calls`, `search_by_cluster`, `analyze_call_history`
**Handled By**: ToolAwareAgent with automatic cluster inference

### 3. General Funding Opportunity Questions
**Description**: Broad queries about open calls and funding opportunities. Local-first search with API enrichment.

**Examples**:
- "What are some open calls for AI research?"
- "Find funding opportunities for renewable energy projects"
- "Are there any grants for sustainable agriculture?"
- "What calls are available for cybersecurity research?"
- "Show me open proposals for quantum technology"

**Data Sources**: Local PostgreSQL (funding_calls), EU Funding & Tenders Portal API
**Tools Used**: `search_funding_calls`
**Handled By**: ToolAwareAgent with LocalCallSearchService

### 4. General Eligibility & Programme Questions (FAQ)
**Description**: Questions about Horizon Europe programme rules, eligibility criteria, and general procedures. Uses semantic search across 500+ indexed documents.

**Examples**:
- "What are the eligibility criteria for Horizon Europe?"
- "How do I form a consortium for Horizon Europe projects?"
- "What is the evaluation process for Horizon Europe proposals?"
- "What are the different funding rates in Horizon Europe?"
- "Explain the difference between RIA, IA, and CSA actions"
- "Can Switzerland participate in Horizon Europe?"

**Data Sources**: Horizon Europe Programme Guide, General Annexes, Work Programmes, FAQs (pgvector)
**Tools Used**: `search_documents`
**Handled By**: ToolAwareAgent with VectorSearchService

### 5. Project Search Questions
**Description**: Queries about existing funded Horizon Europe projects. Uses multi-source search combining PostgreSQL full-text, Neo4j graph traversal, and vector embeddings.

**Examples**:
- "Show me successful AI healthcare projects funded by EU"
- "What renewable energy projects have been funded recently?"
- "Find me projects about digital transformation in manufacturing"
- "What climate change adaptation projects exist?"
- "Show me ERC-funded projects in quantum physics"
- "Find projects similar to my hydrogen fuel cell idea"

**Data Sources**:
- PostgreSQL: 13,865+ projects with full metadata
- Neo4j: Project-organization-topic relationships
- pgvector: 13,850 project embeddings for semantic search

**Tools Used**: `search_projects`, `get_project_details`, `find_similar_projects`, `find_semantically_similar_projects`, `search_by_cluster`
**Handled By**: ToolAwareAgent with LocalProjectSearchService (100% local, no API calls)

### 6. Statistics & Analysis Questions
**Description**: Questions about success rates, funding amounts, participation data, and historical trends. Uses Neo4j for pre-aggregated statistics.

**Examples**:
- "What is the success rate for EIC Accelerator?"
- "How much funding has Germany received from Horizon Europe?"
- "Compare success rates of RIA vs IA grants"
- "What's the average budget for Climate cluster projects?"
- "Show me funding trends for digital topics over the years"

**Data Sources**: Neo4j (pre-aggregated statistics), PostgreSQL (detailed calculations)
**Tools Used**: `get_programme_statistics`, `get_country_statistics`, `compare_programmes`, `analyze_call_history`
**Handled By**: ToolAwareAgent with GraphSearchService

### 7. Partner & Consortium Questions
**Description**: Questions about finding partners, consortium composition, and collaboration networks. Uses **hybrid Graph+SQL architecture** with RRF fusion.

**Examples**:
- "Find German SMEs with hydrogen experience"
- "Who are the top coordinators in health research?"
- "What's the typical consortium makeup for Climate RIA projects?"
- "Find universities that collaborate with Fraunhofer"
- "Show me the collaboration network for AI research"

**Data Sources**:
- Neo4j: Organization relationships, 2-hop partner discovery, cluster expertise
- PostgreSQL: Full project details, keyword filtering

**Tools Used**:
- `find_experienced_partners` (HYBRID: Graph+SQL with RRF fusion)
- `get_consortium_patterns` (HYBRID: Graph+SQL with parallel queries)
- `get_collaboration_network`
- `find_organization_projects`

**Handled By**: ToolAwareAgent with hybrid architecture

### 8. Budget & Financial Questions
**Description**: Questions about typical budgets, funding benchmarks, and financial planning. Uses **hybrid Graph+SQL architecture** with weighted fusion.

**Examples**:
- "What's typical budget for a Climate RIA project?"
- "How much should I budget for a 3-year IA in digital?"
- "What's the average EU contribution for Health cluster projects?"
- "Show me budget distribution by organization type"
- "What percentage of budget typically goes to SMEs?"

**Data Sources**:
- Neo4j: Pre-aggregated cluster statistics, consortium patterns
- PostgreSQL: Detailed budget breakdowns, org type analysis

**Tools Used**:
- `get_budget_benchmark` (HYBRID: Graph+SQL with weighted fusion)
- `calculate_budget` (HYBRID: Graph+SQL for budget planning)

**Response Includes**: Statistics, org type breakdown, country breakdown, recommendations

**Handled By**: ToolAwareAgent with hybrid architecture

### 9. Proposal Support Questions
**Description**: Questions to help users prepare competitive proposals. Combines multiple tools for comprehensive support.

**Examples**:
- "Help me find similar funded projects for my AI healthcare proposal"
- "What budget should I plan for a 36-month RIA in Cluster 5?"
- "Generate a timeline for my 4-year Innovation Action"
- "What consortium composition works best for Climate projects?"
- "Find experienced partners for my quantum computing proposal"

**Data Sources**: All sources combined - graph, SQL, vector, documents

**Tools Used**:
- `get_similar_funded_projects` (HYBRID: Vector+Graph with combined scoring)
- `get_budget_benchmark` (HYBRID: Graph+SQL)
- `calculate_budget` (HYBRID: Graph+SQL)
- `generate_timeline` (HYBRID: Graph+SQL with cluster-specific WPs)
- `get_consortium_patterns` (HYBRID: Graph+SQL)
- `find_experienced_partners` (HYBRID: Graph+SQL with RRF)
- `analyze_call_history` (HYBRID: Graph+SQL with topic evolution)

**Handled By**: ToolAwareAgent with multi-tool orchestration

### 10. Comparison & Complex Queries
**Description**: Complex questions that compare programmes, countries, or require multi-step reasoning across multiple data sources.

**Examples**:
- "Compare EIC Accelerator success rates with regular RIA grants"
- "How does German participation compare to France in Climate topics?"
- "What are the differences between Cluster 4 and Cluster 5 project characteristics?"
- "Explain the evaluation criteria for EIC Accelerator and show me past successful projects"
- "What consortium size works best for different action types?"

**Data Sources**: Multiple sources combined with intelligent fusion
**Tools Used**: `compare_programmes`, `get_programme_statistics`, `get_country_statistics`, plus context-specific tools
**Handled By**: ToolAwareAgent with ReAct pattern (up to 5 reasoning iterations)

---

## Part 2: Proposal Writer Conversation Scenarios

This section outlines conversation scenarios for the AI Proposal Writer feature, covering the full user journey from initial proposal creation through submission readiness.

### 11. Getting Started Scenarios

#### 11.1 New User Onboarding
```
User: "I want to write a proposal for Horizon Europe. Where do I start?"

Expected: AI explains the proposal structure, asks about the call/topic,
and guides user through initial setup.
```

#### 11.2 Call Selection
```
User: "I found a call about AI in healthcare. The ID is HORIZON-HLTH-2025-01-CARE-01."

Expected: AI fetches call details, explains requirements, and suggests
which sections to prioritize.
```

#### 11.3 Topic Understanding
```
User: "What exactly is this call looking for? I don't understand the technical scope."

Expected: AI analyzes the call text, extracts key requirements, and explains
in plain language what evaluators expect.
```

#### 11.4 Proposal Initialization
```
User: "Let's start a new proposal for this call. Our project is about using
machine learning to predict drug interactions."

Expected: AI creates proposal structure, suggests title options, and
identifies relevant funded projects for reference.
```

#### 11.5 Returning User
```
User: "I was working on my proposal yesterday. Can we continue?"

Expected: AI retrieves saved progress, shows current status, and suggests
next actions based on where user left off.
```

### 12. Section Writing Scenarios

#### 12.1 Generate First Draft - Excellence
```
User: "Write the Excellence section for my proposal about quantum computing
for drug discovery."

Expected: AI generates domain-specific content using call requirements
and similar funded projects as reference.
```

#### 12.2 Generate First Draft - Impact
```
User: "Now write the Impact section. Our main stakeholders are pharmaceutical
companies and hospitals."

Expected: AI creates impact pathways, identifies target groups, and
suggests dissemination channels.
```

#### 12.3 Generate First Draft - Implementation
```
User: "Generate the Implementation section. We have 5 partners from
Germany, France, Spain, Netherlands, and Italy."

Expected: AI creates work package structure, suggests timeline, and
distributes responsibilities across partners.
```

#### 12.4 Partial Section Writing
```
User: "I've written the first paragraph of my objectives. Can you continue
from here?"

Expected: AI reads existing content, maintains style/tone, and continues
writing coherently.
```

#### 12.5 Bullet Points to Prose
```
User: "Here are my key points:
- Novel AI algorithm
- 50% faster than state of art
- Validated on 3 datasets
Turn this into a proper paragraph."

Expected: AI expands bullets into well-structured academic prose.
```

#### 12.6 Section-Specific Guidance
```
User: "What should go in the 'Methodology' subsection?"

Expected: AI explains expected content, common mistakes to avoid,
and shows examples from funded projects.
```

### 13. Quality Improvement Scenarios

#### 13.1 General Improvement Request
```
User: "This section feels weak. How can I make it stronger?"

Expected: AI analyzes content, identifies specific weaknesses, and
provides actionable improvement suggestions.
```

#### 13.2 Evaluator Perspective
```
User: "What would an evaluator think of this paragraph?"

Expected: AI simulates evaluator assessment, highlights potential
concerns, and suggests how to address them.
```

#### 13.3 Strengthen Specific Aspect
```
User: "The innovation part isn't convincing enough. Help me strengthen it."

Expected: AI identifies why innovation is weak and suggests specific
additions or rewrites.
```

#### 13.4 Add Technical Depth
```
User: "Reviewers might think this is too superficial. Add more technical detail."

Expected: AI adds domain-appropriate technical content without
making it inaccessible.
```

#### 13.5 Improve Clarity
```
User: "This paragraph is confusing. Make it clearer."

Expected: AI restructures sentences, breaks down complex ideas,
and improves readability.
```

#### 13.6 Make More Concise
```
User: "This is too long. Cut it down by 30% without losing key points."

Expected: AI identifies redundancies, tightens prose, and maintains
essential information.
```

### 14. Score & Feedback Scenarios

#### 14.1 Quick Score Check
```
User: "What's my current score for this section?"

Expected: AI provides quick heuristic score with brief explanation.
```

#### 14.2 Detailed Evaluation
```
User: "Give me a detailed evaluation of my Excellence section."

Expected: AI provides criterion-by-criterion breakdown with scores,
confidence levels, and specific feedback.
```

#### 14.3 Score Comparison
```
User: "How does my score compare to the funding threshold?"

Expected: AI shows current score vs. threshold (3.0), explains gap,
and prioritizes improvements needed.
```

#### 14.4 Track Improvement
```
User: "Has my score improved since the last version?"

Expected: AI shows score history, highlights improvements, and
identifies remaining issues.
```

#### 14.5 Predict Final Score
```
User: "If I submit now, what score would I likely get?"

Expected: AI provides predicted overall score with confidence interval
and key factors affecting it.
```

#### 14.6 Score Explanation
```
User: "Why did I only get 3.2? I thought this was good."

Expected: AI explains specific scoring criteria, shows where points
were lost, and provides examples of 4.0+ content.
```

### 15. Gap Analysis Scenarios

#### 15.1 Identify All Gaps
```
User: "What's missing from my proposal?"

Expected: AI analyzes against call requirements and evaluation criteria,
lists all gaps with severity ratings.
```

#### 15.2 Critical Gaps Only
```
User: "What are the most critical things I need to fix?"

Expected: AI prioritizes gaps by impact on score, shows blocking
issues first.
```

#### 15.3 Gap in Specific Area
```
User: "Is there anything missing in my methodology description?"

Expected: AI checks methodology against expected content and
identifies specific gaps.
```

#### 15.4 Compare to Requirements
```
User: "Does my proposal address all the call requirements?"

Expected: AI maps proposal content to call requirements, shows
coverage percentage and missing items.
```

#### 15.5 Gap Resolution Guidance
```
User: "How do I fix the gap about 'clear KPIs'?"

Expected: AI explains what KPIs are expected, provides examples,
and suggests specific additions.
```

#### 15.6 Verify Gap Closure
```
User: "I added the risk assessment. Is the gap closed now?"

Expected: AI re-evaluates content, confirms if gap is addressed,
or explains what's still missing.
```

### 16. Rewriting & Suggestions Scenarios

#### 16.1 Full Section Rewrite
```
User: "Rewrite this entire section to be more compelling."

Expected: AI provides complete rewrite with tracked changes or
side-by-side comparison.
```

#### 16.2 Paragraph Rewrite Options
```
User: "Give me 3 different ways to rewrite this paragraph."

Expected: AI provides multiple rewrite options with different
approaches (concise, detailed, persuasive).
```

#### 16.3 Inline Suggestions
```
User: "Show me suggestions for improving this text inline."

Expected: AI provides Grammarly-style suggestions - insertions,
deletions, replacements with explanations.
```

#### 16.4 Accept/Reject Suggestions
```
User: "Apply suggestion 2 but not the others."

Expected: AI applies selected suggestion and updates content.
```

#### 16.5 Style Matching
```
User: "Rewrite this to match the style of my other sections."

Expected: AI analyzes existing sections and rewrites to match
tone, formality, and structure.
```

#### 16.6 Targeted Rewrite
```
User: "Rewrite just the innovation claims to be more specific."

Expected: AI identifies innovation claims and rewrites only those
portions with concrete details.
```

### 17. Learning from Examples Scenarios

#### 17.1 Find Similar Projects
```
User: "Show me funded projects similar to mine."

Expected: AI finds semantically similar CORDIS projects, shows
relevance scores and key similarities.
```

#### 17.2 Learn from Successful Proposal
```
User: "What can I learn from how project EXAMPLE-123 wrote their Excellence section?"

Expected: AI analyzes successful project's approach and suggests
applicable techniques.
```

#### 17.3 Benchmark Against Funded Projects
```
User: "How does my proposal compare to funded projects in this area?"

Expected: AI compares content, structure, and approach to successful
projects, highlights differences.
```

#### 17.4 Copy Successful Patterns
```
User: "Use a similar structure to what worked for funded AI projects."

Expected: AI identifies common structural patterns in successful
proposals and applies them.
```

#### 17.5 Topic-Specific Examples
```
User: "Show me how other proposals described their consortium for digital health."

Expected: AI retrieves relevant consortium descriptions from
similar funded projects.
```

#### 17.6 Budget Benchmarking
```
User: "Is my budget realistic compared to similar funded projects?"

Expected: AI compares budget breakdown to projects with similar
scope, action type, and consortium size.
```

### 18. Budget & Timeline Scenarios

#### 18.1 Generate Budget
```
User: "Create a budget for a 4-year RIA project with 8 partners
requesting €5M total."

Expected: AI generates detailed budget breakdown following HE rules,
distributed appropriately across partners.
```

#### 18.2 Budget Validation
```
User: "Is my budget compliant with Horizon Europe rules?"

Expected: AI checks against HE financial rules, flags issues
(overhead rates, equipment limits, etc.).
```

#### 18.3 Budget Optimization
```
User: "How can I optimize the budget distribution?"

Expected: AI suggests reallocation based on work package activities
and partner capabilities.
```

#### 18.4 Generate Timeline
```
User: "Create a project timeline with work packages and milestones."

Expected: AI generates Gantt chart data, WP descriptions,
deliverables, and milestone schedule.
```

#### 18.5 Timeline Validation
```
User: "Is my timeline realistic for the proposed activities?"

Expected: AI checks task dependencies, duration reasonability,
and resource allocation.
```

#### 18.6 Partner-Specific Budget
```
User: "What should Partner 3's budget look like? They're a university
doing WP2 and WP4."

Expected: AI generates partner-specific budget based on their
role and activities.
```

### 19. Compliance & Requirements Scenarios

#### 19.1 Check Overall Compliance
```
User: "Is my proposal compliant with all requirements?"

Expected: AI runs full compliance check against call requirements,
eligibility, and format rules.
```

#### 19.2 Consortium Eligibility
```
User: "Is our consortium eligible? We have partners from Germany,
Switzerland, and UK."

Expected: AI checks country eligibility, minimum partner requirements,
and associated country rules.
```

#### 19.3 Format Compliance
```
User: "Does my proposal meet the page limits and formatting requirements?"

Expected: AI checks page counts, font sizes, section lengths against
template requirements.
```

#### 19.4 Missing Mandatory Elements
```
User: "What mandatory elements am I missing?"

Expected: AI lists all required elements (ethics, gender, open science)
and their status.
```

#### 19.5 Fix Compliance Issue
```
User: "Help me fix the ethics section to be compliant."

Expected: AI explains requirements and helps write compliant
ethics self-assessment.
```

#### 19.6 Pre-Submission Checklist
```
User: "Give me a final checklist before submission."

Expected: AI provides comprehensive pre-submission checklist
with pass/fail status for each item.
```

### 20. Progress & Dashboard Scenarios

#### 20.1 Check Progress
```
User: "How far along is my proposal?"

Expected: AI shows completion percentage, sections status,
and estimated work remaining.
```

#### 20.2 Full Dashboard
```
User: "Show me my proposal dashboard."

Expected: AI displays comprehensive dashboard with all sections,
scores, actions, and readiness status.
```

#### 20.3 Next Actions
```
User: "What should I work on next?"

Expected: AI prioritizes next actions based on impact,
showing estimated time and benefit.
```

#### 20.4 Submission Readiness
```
User: "Am I ready to submit?"

Expected: AI runs readiness checks, shows blocking vs.
non-blocking issues, and funding probability.
```

#### 20.5 Section Comparison
```
User: "Which section needs the most work?"

Expected: AI compares all sections by score, gaps, and
improvement potential.
```

#### 20.6 Time to Deadline
```
User: "How much time do I have left?"

Expected: AI shows time until deadline, estimated work
remaining, and feasibility assessment.
```

### 21. Export & Submission Scenarios

#### 21.1 Export to Word
```
User: "Export my proposal to Word format."

Expected: AI generates properly formatted Word document
following HE template.
```

#### 21.2 Export Budget to Excel
```
User: "Export my budget to Excel."

Expected: AI generates Excel spreadsheet with proper
formatting and formulas.
```

#### 21.3 Export Full Package
```
User: "Create a complete submission package."

Expected: AI generates ZIP with all required documents
(Part A, Part B, annexes).
```

#### 21.4 Final Review Mode
```
User: "Enter final review mode before submission."

Expected: AI performs comprehensive final check and
highlights any last-minute issues.
```

#### 21.5 Version Comparison
```
User: "Compare my current version to last week's version."

Expected: AI shows tracked changes, score improvements,
and modifications summary.
```

### 22. Multi-Turn Conversation Scenarios

#### 22.1 Iterative Refinement
```
Turn 1 - User: "Write an objectives section."
Turn 2 - User: "Make the first objective more specific."
Turn 3 - User: "Add a fourth objective about sustainability."
Turn 4 - User: "Now score this section."

Expected: AI maintains context across turns, applies
incremental changes correctly.
```

#### 22.2 Topic Switching
```
Turn 1 - User: "Help with Excellence section."
Turn 2 - User: "Actually, let's work on the budget first."
Turn 3 - User: "OK back to Excellence now."

Expected: AI handles topic switches, maintains state
for both topics.
```

#### 22.3 Reference Previous Content
```
User: "Use the same style as the paragraph I wrote yesterday
about consortium composition."

Expected: AI retrieves previous content, analyzes style,
and applies it.
```

#### 22.4 Comparison Across Versions
```
Turn 1 - User: "Score my methodology."
Turn 2 - User: "Rewrite it."
Turn 3 - User: "Score it again. Did it improve?"

Expected: AI tracks before/after scores and explains changes.
```

#### 22.5 Building on Feedback
```
Turn 1 - AI: "Your innovation claims are too vague."
Turn 2 - User: "I added more detail. Check again."
Turn 3 - AI: "Better, but still missing quantitative evidence."
Turn 4 - User: "Added numbers. How about now?"

Expected: AI provides consistent, progressive feedback.
```

### 23. Error Recovery & Edge Cases

#### 23.1 Unclear Request
```
User: "Make it better."

Expected: AI asks clarifying questions - which section?
what aspect? what's the goal?
```

#### 23.2 Missing Context
```
User: "Continue writing."

Expected: AI asks which section, or retrieves last active
section from context.
```

#### 23.3 Conflicting Instructions
```
User: "Make it shorter but add more detail about the methodology."

Expected: AI addresses conflict, suggests prioritization,
or asks which is more important.
```

#### 23.4 Out of Scope Request
```
User: "Write my PhD thesis introduction."

Expected: AI politely explains scope limitation and
redirects to proposal-related tasks.
```

#### 23.5 Empty Section
```
User: "Score my Impact section." [Section is empty]

Expected: AI handles gracefully, explains section needs
content before scoring.
```

#### 23.6 Very Long Content
```
User: [Pastes 10,000 words] "Evaluate this."

Expected: AI handles large content, possibly processes
in chunks, provides complete feedback.
```

#### 23.7 Last-Minute Panic
```
User: "Deadline is in 2 hours! What are the most critical
things to fix?"

Expected: AI immediately prioritizes critical blocking
issues, provides rapid fixes, skips nice-to-haves.
```

#### 23.8 Multiple Proposals
```
User: "I'm working on two proposals. Switch to the climate one."

Expected: AI switches context to correct proposal,
confirms switch with user.
```

---

## Part 3: Available Tools (20 Total)

### Discovery Tools
| Tool | Description | Architecture |
|------|-------------|--------------|
| `search_funding_calls` | Find open/upcoming calls | Local + API enrichment |
| `get_call_details` | Get details for specific call | Local + API enrichment |
| `search_projects` | Search CORDIS projects | Local (PostgreSQL + Neo4j + Vector) |
| `get_project_details` | Get project details | Local |
| `search_documents` | Search EU regulations/guides | Vector (pgvector) |

### Statistics Tools
| Tool | Description | Architecture |
|------|-------------|--------------|
| `get_programme_statistics` | Success rates, funding for programme | Neo4j |
| `get_country_statistics` | Participation stats for country | Neo4j |
| `compare_programmes` | Side-by-side programme comparison | Neo4j |

### Project Discovery Tools
| Tool | Description | Architecture |
|------|-------------|--------------|
| `find_similar_projects` | Find projects by topic/consortium/cluster | Local |
| `find_semantically_similar_projects` | Find projects by semantic meaning | Vector (pgvector) |
| `get_similar_funded_projects` | Find similar funded projects | **HYBRID: Vector+Graph** |
| `find_organization_projects` | All projects for an organization | Neo4j + SQL |
| `get_collaboration_network` | Organization partnership network | Neo4j |
| `search_by_cluster` | Projects in research cluster | Neo4j |

### Proposal Support Tools (Hybrid Architecture)
| Tool | Description | Architecture |
|------|-------------|--------------|
| `get_budget_benchmark` | Budget statistics from similar projects | **HYBRID: Graph+SQL** |
| `get_consortium_patterns` | Consortium composition patterns | **HYBRID: Graph+SQL** |
| `find_experienced_partners` | Organizations with track record | **HYBRID: Graph+SQL (RRF)** |
| `analyze_call_history` | Historical funding patterns | **HYBRID: Graph+SQL** |
| `calculate_budget` | Generate detailed budget breakdown | **HYBRID: Graph+SQL** |
| `generate_timeline` | Create project timeline with WPs | **HYBRID: Graph+SQL** |

---

## Part 4: Hybrid Architecture Details

Seven tools use a **hybrid Graph+SQL architecture** for comprehensive results:

### Result Fusion Methods
| Tool | Fusion Method | Description |
|------|---------------|-------------|
| `find_experienced_partners` | RRF (k=60) | Reciprocal Rank Fusion with score boosts |
| `get_budget_benchmark` | Weighted Average | By project count from each source |
| `get_consortium_patterns` | Parallel Merge | Templates from SQL, patterns from graph |
| `analyze_call_history` | Timeline Merge | Evolution from graph, details from SQL |
| `get_similar_funded_projects` | Combined Scoring | 75% embedding + 25% graph signals |
| `calculate_budget` | Reference Merge | Patterns from graph, examples from SQL |
| `generate_timeline` | Template Merge | Duration patterns from graph, examples from SQL |

### Cluster Inference
All hybrid tools automatically infer Horizon Europe clusters from keywords:
```
hydrogen, solar, wind → CLUSTER-5 (Climate, Energy, Mobility)
cancer, clinical, pharma → CLUSTER-1 (Health)
AI, quantum, cyber → CLUSTER-4 (Digital, Industry, Space)
agriculture, food, bio → CLUSTER-6 (Food, Bioeconomy)
```

---

## Part 5: API Endpoints

### V3 Simplified Architecture (Recommended)
```
POST /api/v3/conversation/{id}/message/stream  - Streaming responses
POST /api/v3/conversation/{id}/message         - Non-streaming responses
GET  /api/v3/conversation/{id}/context         - Get conversation history
DELETE /api/v3/conversation/{id}/context       - Clear memory
GET  /api/v3/conversation/health               - Health check
```

### Legacy V2 Endpoints
```
POST /api/query          - Synchronous query
POST /api/query/stream   - SSE streaming
POST /api/query/async    - Async with task ID
GET  /api/query/status/{task_id}  - Check async status
```

### Feedback API
```
POST /api/feedback                    - Submit feedback
GET  /api/feedback/summary            - Aggregated metrics
GET  /api/feedback/conversation/{id}  - Conversation feedback
GET  /api/feedback/suggestions        - AI improvement suggestions
```

---

## Part 6: Testing Methods

### Script-Based Testing
```bash
# Integration tests
pytest tests/test_integration_v2.py

# Intent detection
pytest tests/test_intent_detection_only.py

# Data source verification
pytest tests/test_data_source_verification.py

# All tests with coverage
pytest --cov=app tests/
```

### Direct Tool Testing
```python
# Test hybrid partner discovery
from app.services.tools.partner_discovery import PartnerDiscoveryTool
tool = PartnerDiscoveryTool()
result = await tool.find_partners(keywords='hydrogen', country='Germany')

# Test hybrid budget benchmark
from app.services.tools.budget_benchmark import BudgetBenchmarkTool
tool = BudgetBenchmarkTool()
result = tool.get_benchmark(action_type='RIA', cluster='CL5')

# Test hybrid similar projects
from app.services.tools.similar_projects import SimilarProjectsTool
tool = SimilarProjectsTool()
result = tool.find_similar(description='AI healthcare diagnostics', rerank_with_graph=True)
```

### Proposal Writer Scenario Testing
Each scenario should be tested for:
1. **Accuracy** - Does the AI provide correct information?
2. **Relevance** - Is the response relevant to the request?
3. **Completeness** - Does it fully address the user's need?
4. **Tone** - Is the response appropriately professional?
5. **Actionability** - Can the user act on the response?
6. **Context Awareness** - Does it use available context?
7. **Error Handling** - Does it fail gracefully?
8. **Performance** - Does it respond in reasonable time?

---

## Part 7: Data Sources Overview

### Primary Databases
| Database | Content | Records |
|----------|---------|---------|
| PostgreSQL | Projects, calls, organizations | 13,865+ projects |
| Neo4j | Relationships, statistics, patterns | Full graph of HE data |
| pgvector | Document chunks, project embeddings | 13,850 embeddings |

### Document Collections
- **Horizon Europe Work Programme 2023-2027**: Call descriptions, budgets, topics
- **Programme Guide**: Eligibility rules, procedures, funding rates
- **General Annexes**: Detailed rules and requirements
- **Call Texts**: Topic-specific requirements
- **FAQs**: Common questions and answers

### External APIs
- **EU Funding & Tenders Portal**: Real-time call enrichment (used sparingly)

---

## Part 8: System Capabilities Summary

### Core Capabilities
- Single agentic loop with autonomous tool selection
- 20 specialized tools covering all query types
- Hybrid Graph+SQL architecture for 7 proposal support tools
- Semantic search with 768-dim embeddings
- Multi-source result fusion (RRF, weighted average, combined scoring)

### Advanced Features
- Automatic cluster inference from keywords
- Graph-based reranking with combined scoring
- Parallel query execution for performance
- SQL enrichment for graph-only results
- 2-hop partner discovery in collaboration networks

### Performance Features
- Query plan caching in Redis
- Speculative tool execution
- Tool analytics and performance tracking
- User feedback collection and analysis

### Proposal Writer Capabilities
- Section drafting (Excellence, Impact, Implementation)
- Score prediction and gap analysis
- Budget and timeline generation
- Compliance checking
- Multi-turn conversation support
- Learning from funded projects

---

## Implementation Priority (Proposal Writer)

### High Priority (Core Functionality)
- Section writing (12.1-12.4)
- Quality scoring (14.1-14.3)
- Gap analysis (15.1-15.3)
- Basic rewriting (16.1-16.3)
- Compliance checking (19.1-19.4)

### Medium Priority (Enhanced Experience)
- Learning from examples (17.1-17.4)
- Budget/timeline generation (18.1-18.5)
- Progress tracking (20.1-20.3)
- Dashboard (20.2-20.5)
- Multi-turn conversations (22.1-22.4)

### Lower Priority (Polish)
- Advanced export (21.3-21.5)
- Edge cases (23.1-23.8)
- Error recovery refinement

---

## Version Information
- **Architecture Version**: V3 Simplified (Single Agentic Loop)
- **Tools**: 20 tools (7 with hybrid Graph+SQL architecture)
- **Last Updated**: December 2024
- **Project Coverage**: 13,865+ Horizon Europe projects
- **Embedding Coverage**: 13,850 project embeddings (768-dim)
- **Documentation Coverage**: Full Horizon Europe 2021-2027 programme

This document serves as a living reference for all question types and conversation scenarios the system can handle. Update it as new capabilities are added or new tools are implemented.
