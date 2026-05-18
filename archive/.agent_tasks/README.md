# MAPIT Data Intelligence Upgrade - Agent Task Files

## Project Overview

This directory contains structured task files for upgrading NEWMAPIT with advanced data intelligence capabilities inspired by OTHERMAPIT's architecture.

**Goal**: Integrate Neo4j graph database with existing PostgreSQL/Supabase vector search to enable:
- Relationship-aware queries (organizations, projects, collaborations)
- Intelligent query planning (Planner LLM)
- Multi-source result fusion
- Neural reranking (Cross-Encoder)

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Query                                   │
│                             │                                        │
│                             ▼                                        │
│                    ┌─────────────────┐                              │
│                    │  QueryPlanner   │  (LLM-based planning)        │
│                    │  (TASK_06)      │                              │
│                    └────────┬────────┘                              │
│                             │                                        │
│              ┌──────────────┼──────────────┐                        │
│              ▼              ▼              ▼                        │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│     │   Neo4j     │ │  pgvector   │ │  Postgres   │                │
│     │   Graph     │ │  Semantic   │ │  Keyword    │                │
│     │  (TASK_04)  │ │  (existing) │ │  (existing) │                │
│     └─────────────┘ └─────────────┘ └─────────────┘                │
│              │              │              │                        │
│              └──────────────┼──────────────┘                        │
│                             ▼                                        │
│                    ┌─────────────────┐                              │
│                    │ DataIntelligence│  (Facade service)            │
│                    │    Service      │                              │
│                    │   (TASK_07)     │                              │
│                    └────────┬────────┘                              │
│                             │                                        │
│                             ▼                                        │
│                    ┌─────────────────┐                              │
│                    │ CrossEncoder    │  (Week 2: TASK_10)           │
│                    │   Reranker      │                              │
│                    └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Execution Order

### Week 1: Foundation (Days 1-7)

| Order | Task ID | Name | Dependencies | Est. Time |
|-------|---------|------|--------------|-----------|
| 1 | TASK_01 | Neo4j Container Setup | None | 1 hour |
| 2 | TASK_02 | CORDIS Dataset Download | None | 30 min |
| 3 | TASK_03 | CORDIS Data Ingestion | TASK_01, TASK_02 | 2 hours |
| 4 | TASK_04 | Graph Search Service | TASK_01, TASK_03 | 3 hours |
| 5 | TASK_05 | Planner System Prompt | None | 1 hour |
| 6 | TASK_06 | Query Planner | TASK_05 | 2 hours |
| 7 | TASK_07 | Data Intelligence Service | TASK_04, TASK_06 | 2 hours |
| 8 | TASK_08 | Tool Registration | TASK_07 | 1 hour |
| 9 | TASK_09 | Integration Testing | All above | 2 hours |

### Week 2: Intelligence + Quality (Days 8-14)

| Order | Task ID | Name | Dependencies | Est. Time |
|-------|---------|------|--------------|-----------|
| 10 | TASK_10 | Cross-Encoder Reranker | TASK_07 | 2 hours |
| 11 | TASK_11 | Result Fusion | TASK_10 | 2 hours |
| 12 | TASK_12 | Advanced Queries (F-H) | TASK_04 | 3 hours |
| 13 | TASK_13 | Consortium Builder Tool | TASK_04 | 2 hours |
| 14 | TASK_14 | Compliance Checker Tool | TASK_04 | 2 hours |
| 15 | TASK_15 | Final Testing & Docs | All above | 3 hours |

## Task File Format

Each task file contains:

1. **Metadata**: ID, dependencies, estimated time
2. **Objective**: Clear goal statement
3. **Context**: Background information needed
4. **Files to Create/Modify**: Exact file paths
5. **Implementation Steps**: Numbered instructions
6. **Code**: Complete implementation or templates
7. **Acceptance Criteria**: Checkboxes for completion
8. **Verification Commands**: How to test

## For AI Agents

When executing a task:

1. **Read the entire task file first** before starting
2. **Check dependencies** are complete (run verification commands from prior tasks)
3. **Follow implementation steps** in order
4. **Run verification commands** after completion
5. **Mark acceptance criteria** as complete
6. **Report any blockers** or deviations

## Project Paths

```
NEWMAPIT/MAP-IT_SA/
├── app/
│   ├── core/
│   │   ├── config.py              # Existing config
│   │   └── neo4j_config.py        # NEW (TASK_01)
│   ├── services/
│   │   ├── data_intelligence/     # NEW directory
│   │   │   ├── __init__.py
│   │   │   ├── graph_service.py   # NEW (TASK_04)
│   │   │   ├── query_planner.py   # NEW (TASK_06)
│   │   │   ├── cross_encoder_reranker.py  # NEW (TASK_10)
│   │   │   └── planner_system_prompt.txt  # NEW (TASK_05)
│   │   ├── data_intelligence_service.py   # NEW (TASK_07)
│   │   └── tools/
│   │       └── tool_orchestrator.py       # MODIFY (TASK_08)
├── scripts/
│   └── ingest_cordis_to_neo4j.py  # NEW (TASK_03)
├── data/
│   └── cordis/                     # NEW (TASK_02)
├── docker-compose.yml              # MODIFY (TASK_01)
├── requirements.txt                # MODIFY (multiple tasks)
└── .agent_tasks/                   # This directory
```

## Key Technologies

- **Neo4j 5.x**: Graph database with APOC and GDS plugins
- **Python 3.10+**: Backend language
- **sentence-transformers**: For Cross-Encoder reranking
- **Google Gemini**: For Planner LLM
- **Existing**: Supabase/PostgreSQL with pgvector

## Success Metrics (End of Week 1)

The following queries should work:

```python
# Query A: Call Lookup
"What is the deadline for HORIZON-CL4-2025-DATA-01?"

# Query B: Eligibility Check
"Can an SME from Switzerland participate in Cluster 4 calls?"

# Query C: Budget Questions
"What is the maximum budget for RIA actions in Cluster 5?"

# Query D: Consortium Rules
"What is the minimum number of countries required for a CSA?"

# Query E: Similar Calls
"Find calls similar to HORIZON-CL4-2024-HUMAN-01"
```

## Contact

Project: MAPIT (101158945)
Organisation: Stichting Hogeschool Utrecht
