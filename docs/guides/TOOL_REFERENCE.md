# MAP-IT SA Tool Reference Guide

This document provides a comprehensive overview of the 42 specialized tools available in the MAP-IT SA ecosystem. These tools are used by the `ToolAwareAgent` (V3) and `ProposalAwareAgent` (V4) to provide data-driven insights.

## Tool Categories

### 1. Statistics & Analytics
These tools query the Neo4j graph and PostgreSQL to provide aggregate data.

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `get_programme_statistics` | Success rates, funding amounts, and participation data for specific programmes. | `programme`, `metric` |
| `get_country_statistics` | Deep dive into a single country's participation (orgs, funding, eligibility). | `country`, `programme` |
| `analyze_geographic_diversification` | Analyzes consortium diversity across regions (Nordic, CEE, etc.). | - |
| `get_organization_stats` | Aggregate stats for an organization (projects, funding, roles). | `org_id` / `org_name` |
| `analyze_call_history` | Historical funding patterns for topics or research clusters. | `cluster`, `topic_keywords` |

### 2. Project Search & Discovery (CORDIS)
Local-first tools for searching the 13,850+ funded project database.

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `search_projects` | Multi-source search (Keywords + Graph + Vector). | `keywords`, `country`, `sort_by` |
| `get_project_details` | Full metadata for a project, including objectives and partners. | `project_id` |
| `get_project_partners` | Lists all organizations in a consortium with their roles and funding. | `project_id` |
| `find_similar_projects` | Find projects similar by consortium structure or research cluster. | `project_id` |
| `find_semantically_similar_projects` | Uses AI embeddings to find projects with similar objectives. | `description` |
| `find_organization_projects` | Lists all projects associated with a specific organization. | `org_name` |

### 3. Funding Call Search
Finds open, closed, and upcoming funding opportunities.

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `search_funding_calls` | Search for calls across programmes. Enriched by EU Portal API. | `keywords`, `status`, `year` |
| `get_call_details` | Detailed requirements, deadlines, and budget for a specific call. | `call_id` |
| `search_all_programmes` | One-shot search across all 6 supported EU programmes. | `query` |
| `recommend_programmes` | AI recommendation of the best programme for a specific project idea. | `description` |

### 4. Proposal Support & Planning
Tools designed to help with the drafting and planning of EU proposals.

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `get_budget_benchmark` | Provides real budget statistics from similar funded projects. | `cluster`, `action_type` |
| `get_consortium_patterns` | Analyzes successful consortium sizes and compositions. | `cluster`, `topic_keywords` |
| `find_experienced_partners` | Identifies organizations with high success rates in specific topics. | `keywords`, `cluster` |
| `calculate_budget` | Generates a detailed budget breakdown based on real cost ratios. | `total_budget`, `cluster` |
| `generate_timeline` | Creates a project timeline (WPs, Milestones) grounded in real examples. | `duration_months`, `cluster` |

### 5. Quality & Validation
Evaluator-level tools for assessing draft content.

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `score_proposal_section` | Scores a section (0-5) based on official EU criteria. | `section_text`, `criteria` |
| `score_full_proposal` | Evaluates an entire proposal (Excellence, Impact, Implementation). | `full_text` |
| `validate_budget` | Checks a draft budget for compliance with programme rules. | `budget_data` |

### 6. Programme-Specific Eligibility
Dedicated logic for the unique rules of different funding streams.

- **Erasmus+**: `check_erasmus_eligibility`, `calculate_erasmus_budget`, `search_erasmus_templates`.
- **Creative Europe**: `check_creative_europe_eligibility`, `calculate_creative_europe_budget`.
- **EU4Health**: `check_eu4health_eligibility`.
- **Digital Europe**: `check_digital_europe_eligibility`.
- **LIFE**: `check_life_eligibility`.

---

## Technical Details: Hybrid Search
Most tools categorized as "Project Search" or "Proposal Support" use a **Hybrid Search** pattern:
1. **Graph Traversal (Neo4j)**: For relationship-based discovery (e.g., partners of partners).
2. **Keyword Search (PostgreSQL)**: For exact term matching in project titles.
3. **Vector Search (pgvector)**: For semantic similarity (understanding meaning).
4. **RRF (Reciprocal Rank Fusion)**: Combines results from all three sources into a single ranked list.
