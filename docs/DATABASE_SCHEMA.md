# MAP-IT Database Schema & Data Architecture

This document provides a comprehensive overview of the MAP-IT data ecosystem, detailing the structure of our PostgreSQL (Supabase), Neo4j, and Vector databases.

---

## 📊 Database Ecosystem Overview

MAP-IT utilizes a **Three-Tier Storage Architecture** to handle different types of data efficiently:

1. **PostgreSQL (Supabase)**: Primary relational store for metadata, conversations, and analytics.
2. **pgvector (Supabase Extension)**: Vector store for high-dimensional embeddings enabling semantic search.
3. **Neo4j**: Graph database for relationship-heavy queries (consortium patterns, organization statistics).

---

## 🐘 PostgreSQL / pgvector (Supabase)

The PostgreSQL instance contains **35 active tables** (including system tables, excluding views) and **15 views** organized into functional domains:

### 1. Document & RAG Domain
Used for the Retrieval-Augmented Generation pipeline.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `horizon_documents` | Registry for official EU documents (Work Programmes, Guides). | ~144 docs |
| `document_chunks` | Shredded document text with **768-dim vectors** and `tsvector`. | ~38,697 chunks |
| `shared_documents` | Documents shared across multiple programmes. | ~54 docs |
| `shared_document_chunks`| Chunks for shared documents. | ~13,147 chunks |
| `embedding_cache` | Cache for text embeddings to reduce API costs. | ~11,817 entries |
| `call_metadata` | Programme-specific attributes and rules. | 4 entries |
| `call_document_mappings`| Mappings between calls and call documents. | 51 entries |
| `citations` | Registry of citations generated in answers. | 12 entries |

### 2. Projects & Organizations Domain
Historical data from CORDIS for Horizon Europe.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `projects` | Core project metadata (acronym, title, cost, framework). | ~13,865 projects |
| `project_embeddings`| **3072-dim vectors** (Gemini) for project titles/objectives. | ~13,850 vectors |
| `organizations` | Detailed participation data (roles, Net EC contributions, SME status).| ~89,348 entries |

### 3. Funding Calls Domain
Current and future funding opportunities.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `funding_calls` | Metadata for calls across all 6 programmes. Includes embeddings. | ~2,756 calls |

### 4. Conversations & Analytics Domain
Persistence for the agentic chat system.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `conversation` | Session-level metadata. | ~3,296 sessions |
| `message` | Individual chat messages with role and content. | ~12,239 messages |
| `conversation_analytics`| Detailed logs of tool usage and response quality. | ~4,821 logs |
| `tool_usage_analytics` | Tracking which tools are called and their outcomes. | ~5,223 entries |
| `tool_combination_analytics`| Co-occurrence tracking of tools used in the same session. | 1 entry |
| `conversation_facts` | Key facts extracted from conversations. | 112 entries |
| `conversation_memory` | Long-term memory store for context injection. | 43 entries |
| `entity_cards` | Cached profiles of partners and organizations. | ~1,696 cards |
| `response_feedback` | User rating feedback (thumbs up/down) and comments. | 2 entries |

### 5. Proposal Writer Domain (V4)
Supports drafting, grading, and improving proposals.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `proposals` | Core draft proposals metadata. | 11 entries |
| `proposal_sessions` | Proposal generation sessions. | 13 entries |
| `proposal_sections` | Draft content for specific sections. | 7 entries |
| `proposal_activity_log` | Logs of actions taken on a proposal session. | 6 entries |
| `proposal_budgets` | Draft budget tables. | 0 entries |
| `proposal_consortium` | Consortium drafts. | 0 entries |
| `proposal_examples` | Stored good-practice section examples. | 0 entries |
| `section_criteria_mapping` | Evaluation criteria mapped to proposal sections. | 0 entries |
| `compliance_checks` | Compliance evaluation results. | 0 entries |
| `improvement_suggestions` | Gap analysis and quality improvement suggestions. | 0 entries |

### 6. SvelteKit User & Collaboration Domain
Frontend authentication and collaborative workspace management.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `client` | User accounts linked to Supabase auth. | 2 entries |
| `collaboration` | Shared workspace collaborations. | 1 entry |
| `client_collaboration` | Join table for user-collaboration roles. | 1 entry |

---

## 👁️ Database Views

We use custom database views to aggregate analytics, monitor performance, and structure proposal data:

1. `active_funding_calls`: View for filtering open/forthcoming calls.
2. `call_document_chunks_view`: Unified view of chunks for search.
3. `horizon_europe_calls`: Horizon programme filter view.
4. `proposal_overview`: Completion status overview of draft proposals.
5. `section_quality_summary`: Quality scores for proposal sections.
6. `session_activity_summary`: Action stats for proposal sessions.
7. `v_conversation_analytics_24h`: Last 24 hours of chat session metrics.
8. `v_embedding_coverage`: Completeness statistics of project embeddings.
9. `v_embedding_stats`: Vector counts and details.
10. `v_feedback_metrics_7d`: Feedback and rating metrics for the last 7 days.
11. `v_popular_tool_combos`: Co-occurrence analytics for multi-tool execution.
12. `v_question_patterns`: Analysis of patterns in queries.
13. `v_tool_feedback`: Analytics correlating rating feedback to specific tools used.
14. `v_tool_performance_24h`: Latency and error rates for tools used in the last 24 hours.
15. `v_tool_usage_analytics`: Overall statistics on tool execution counts.

---

## 🔍 Search Logic & RPC Functions

We use custom PL/pgSQL functions for efficient server-side processing.

### `hybrid_search`
Combines Vector Similarity and Full-Text Search (Keyword) using a weighted scoring model.
- **Vector Score**: Calculated using cosine distance (`1 - (embedding <=> query_embedding)`).
- **Text Score**: Calculated using PostgreSQL `ts_rank` on `tsvector` columns.
- **Combined Score**: `(vector_score * vector_weight) + (text_score * (1 - vector_weight))`.

### `search_documents`
Pure semantic search with metadata filtering (document type, programme year).
- Uses `ivfflat` or flat search for efficient vector retrieval.

---

## 🕸️ Neo4j Graph Schema

The graph enables complex relationship queries that are inefficient in SQL.

- **Nodes**: `Project`, `Organization`, `Topic`, `Programme`, `Country`, `Cluster`.
- **Relationships**:
  - `(Organization)-[:PARTICIPATED_IN {role, contribution}]->(Project)`
  - `(Project)-[:BELONGS_TO]->(Topic)`
  - `(Topic)-[:PART_OF]->(Programme)`

---

## 📈 Data Scale Summary

- **Total Organizations**: 89,348
- **Total Projects**: 13,865
- **RAG Chunks**: 38,697
- **Funding Calls**: 2,756
- **Chat Messages**: 12,239
- **Total Active Tables**: 34 (+1 system table)
- **Total Views**: 15
