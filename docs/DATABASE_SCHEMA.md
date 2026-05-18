# MAP-IT Database Schema & Data Architecture

This document provides a comprehensive overview of the MAP-IT data ecosystem, detailing the structure of our PostgreSQL (Supabase), Neo4j, and Vector databases.

## 📊 Database Ecosystem Overview

MAP-IT utilizes a **Three-Tier Storage Architecture** to handle different types of data efficiently:

1.  **PostgreSQL (Supabase)**: Primary relational store for metadata, conversations, and analytics.
2.  **pgvector (Supabase Extension)**: Vector store for high-dimensional embeddings enabling semantic search.
3.  **Neo4j**: Graph database for relationship-heavy queries (consortium patterns, organization statistics).

---

## 🐘 PostgreSQL / pgvector (Supabase)

The PostgreSQL instance contains **50+ tables** organized into functional domains.

### 1. Document & RAG Domain
Used for the Retrieval-Augmented Generation pipeline.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `horizon_documents` | Registry for official EU documents (Work Programmes, Guides). | ~150 docs |
| `document_chunks` | Shredded document text with **768-dim vectors** and `tsvector`. | ~40,000 chunks |
| `shared_documents` | Documents shared across multiple programmes. | ~50 docs |
| `shared_document_chunks`| Chunks for shared documents. | ~13,000 chunks |
| `embedding_cache` | Cache for text embeddings to reduce API costs. | ~12,000 entries |

### 2. Projects & Organizations Domain
Historical data from CORDIS for Horizon Europe.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `projects` | Core project metadata (acronym, title, cost, framework). | ~14,000 projects |
| `project_embeddings`| **3072-dim vectors** (Gemini) for project titles/objectives. | ~14,000 vectors |
| `organizations` | Detailed participation data (roles, EC contributions, SME status).| ~90,000 entries |

### 3. Funding Calls Domain
Current and future funding opportunities.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `funding_calls` | Metadata for calls across all 6 programmes. Includes embeddings. | ~2,800 calls |
| `call_metadata` | Programme-specific attributes and rules. | - |

### 4. Conversations & Analytics Domain
Persistence for the agentic chat system.

| Table | Description | Data Scale |
|-------|-------------|------------|
| `conversation` | Session-level metadata. | ~3,300 sessions |
| `message` | Individual chat messages with role and content. | ~12,000 messages |
| `conversation_analytics`| Detailed logs of tool usage and response quality. | ~4,800 logs |
| `tool_usage_analytics` | Tracking which tools are called and their outcomes. | ~5,200 entries |

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
- Uses `ivfflat` index for efficient vector retrieval.

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
- **Total Tables**: 51
- **Total Views**: 18
