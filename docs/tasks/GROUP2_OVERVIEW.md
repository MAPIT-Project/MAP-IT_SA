# Group 2: Proposal Quality & Success Enhancement - Implementation Overview

## Context

This document outlines the implementation plan for **Group 2** of the EU Programme Call Assessment system. Group 2 focuses on helping users improve their proposal quality and consortium composition based on **real data from funded projects**.

### What We Have (Data Assets)
- **13,865+ funded CORDIS projects** with objectives, budgets, consortium compositions
- **Neo4j graph database** with organization relationships, project-topic-cluster mappings
- **Project embeddings** (768-dim vectors) for semantic similarity
- **Full organization data** including countries, types, and participation history

### What We DON'T Have (Constraints)
- ❌ Rejected proposals (EU doesn't publish these)
- ❌ Success/failure rates per topic
- ❌ Evaluation scores or feedback
- ❌ Submission counts

### Design Philosophy
All tools will be **honest and data-backed**. We will NOT create fake "AI scores" or pretend to predict success. Instead, we provide real benchmarks and patterns from funded projects.

---

## Task Files

| Task | File | Tool Name | Status |
|------|------|-----------|--------|
| 1 | `task_01_budget_benchmarking.md` | `get_budget_benchmark` | ✅ Implemented |
| 2 | `task_02_consortium_patterns.md` | `get_consortium_patterns` | ✅ Implemented |
| 3 | `task_03_partner_discovery.md` | `find_experienced_partners` | 📋 Defined |
| 4 | `task_04_similar_projects.md` | `get_similar_funded_projects` | 📋 Defined |
| 5 | `task_05_call_history.md` | `analyze_call_history` | 📋 Defined |
| 6 | `task_06_future_proposals.md` | Future enhancements | 📋 Defined |

---

## Implementation Order (Recommended)

1. **Task 1: Budget Benchmarking** - Simplest, uses existing Neo4j queries
2. **Task 2: Consortium Patterns** - Builds on existing graph relationships
3. **Task 4: Similar Projects** - Uses existing embeddings
4. **Task 3: Partner Discovery** - Combines multiple data sources
5. **Task 5: Call History** - Most complex, requires pattern analysis

---

## User Questions Each Tool Answers

### Budget Benchmarking
- "What's a typical budget for a Climate RIA?"
- "How much should I request for an AI-focused IA project?"
- "What's the average consortium size for Cluster 4 projects?"

### Consortium Patterns
- "What's the typical consortium composition for Health projects?"
- "How many SMEs are usually in an IA project?"
- "Which countries lead in Digital projects?"

### Partner Discovery
- "Who are experienced partners for quantum computing projects?"
- "Which German organizations work on renewable energy?"
- "Find SMEs with hydrogen project experience"

### Similar Projects
- "Show me funded projects similar to my AI in healthcare idea"
- "What projects were funded about sustainable agriculture?"
- "Find examples of successful quantum computing projects"

### Call History
- "What topics got funded under HORIZON-CL4 in 2023?"
- "Which clusters fund the most AI projects?"
- "What are the funding trends in Cluster 5?"

---

## Integration with Existing System

All new tools will be:
1. Registered in `app/services/tools/__init__.py`
2. Added to `ToolAwareAgent` in `tool_aware_agent.py`
3. Documented in the agent's tool descriptions
4. Tested with integration tests

---

## Future Extensions (When Proposal Data Available)

If the user obtains past successful/failed proposals, we can add:
- Proposal structure analysis
- Common writing patterns in successful proposals
- Weakness detection (comparing to successful examples)
- More accurate success indicators

See `task_06_future_proposals.md` for details.
