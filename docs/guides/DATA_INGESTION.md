# Data Ingestion & Setup Guide

This guide explains how to populate the MAP-IT SA system with the necessary data to enable its RAG and analytical capabilities.

## Data Ecosystem Overview

The system relies on four primary data stores:
1. **Neo4j**: Graph data for statistics and relationships.
2. **Supabase (pgvector)**: Vector embeddings for document chunks.
3. **PostgreSQL**: Structured metadata for projects and organizations.
4. **Local File System**: Source PDFs and JSON files for ingestion.

---

## 1. CORDIS Research Projects (Horizon Europe)

The system is pre-configured to handle 13,850+ projects.

### Step A: PostgreSQL Restoration
The structured project metadata (the `projects` and `organizations` tables) is restored directly from the pre-packaged PostgreSQL dump, as no public ingestion script is provided for importing raw CSV/JSON CORDIS datasets to SQL:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"
pg_restore --clean --no-acl --no-owner -d "$DATABASE_URL" neo4j_backup/project_embeddings.dump
```

### Step B: Neo4j Ingestion
Once the PostgreSQL database is restored, you can run the Neo4j ingestion script to populate project nodes, organisation nodes, and their relationships inside the graph database:
```bash
python scripts/ingest_cordis_to_neo4j.py
```

### Step C: Embedding Generation
Generate 3072-dim embeddings for all project descriptions using Google's embedding model:
```bash
python scripts/generate_project_embeddings.py
```
*Note: This requires a valid `GOOGLE_EMBEDDING_API_KEY`.*


---

## 2. EU Funding Documents (RAG)

The system supports 6 major programmes. Ingestion involves processing PDFs/Docs, chunking them, and uploading them to Supabase.

### Comprehensive Document Ingestion
To ingest official work programmes and regulations:
```bash
python scripts/ingest_comprehensive_docs.py
```

### Programme-Specific Ingestion
Specific scripts exist for different funding streams:
- **Erasmus+**: `python scripts/ingest_erasmus_documents.py`
- **Creative Europe**: `python scripts/ingest_creative_europe_documents.py`
- **EU4Health**: `python scripts/ingest_eu4health_documents.py`
- **Digital Europe**: `python scripts/ingest_digital_europe_documents.py`
- **LIFE**: `python scripts/ingest_life_documents.py`

---

## 3. Funding Calls (Live Data)

While most data is local, funding calls are synced from the EU Portal API to ensure deadlines are accurate.

### Syncing Calls
```bash
python scripts/sync_topics_from_projects.py  # Syncs Horizon Europe topics
# Specific sync scripts for other programmes:
python scripts/sync_erasmus_calls_from_api.py
python scripts/sync_creative_europe_calls.py
```

---

## 4. Neo4j Graph Setup

The graph must be populated with programme and country nodes to enable the statistics tools.

### Initializing the Graph
```bash
python scripts/ingest_erasmus_to_neo4j.py
python scripts/ingest_creative_europe_to_neo4j.py
# etc.
```

---

## 5. Verification
After ingestion, you can verify the data coverage using the following commands:
```bash
# Check embedding coverage
python scripts/quality_gate.py --check-embeddings

# Check call sync status
python scripts/quality_gate.py --check-calls
```

## System Limits
- **Vector Search**: Current limit is ~2000 dimensions for HNSW indexes. Since we use 3072-dim vectors, the system uses **Exact Search**, which is slower (~300ms) than indexed search but highly accurate.
- **Neo4j**: Large graph traversals (beyond 3 hops) are capped to prevent timeout.
- **API Enrichment**: If the EU Portal API is down, the system falls back to cached local call data (which may be slightly outdated).
