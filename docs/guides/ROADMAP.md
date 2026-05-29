# Project Status & Roadmap

This document outlines the current implementation status, known limitations, and the future roadmap for the MAP-IT SA project.

## Currently Implemented (Production-Ready)

### ✅ V3 Agentic Architecture
- **Tool-Aware Agent**: Single ReAct loop handling all query types.
- **V3 Response Formatter**: Rich, emoji-enhanced formatting for calls and projects.
- **Parallel Tool Execution**: Reducing latency for multi-tool queries.
- **Plan Caching**: Redis-based caching for frequent query patterns.

### ✅ Multi-Programme Coverage
- **Core Support**: Fully implemented tools for Horizon Europe, Erasmus+, Creative Europe, EU4Health, Digital Europe, and LIFE.
- **Cross-Programme Logic**: The `search_all_programmes` and `recommend_programmes` tools work across the entire ecosystem.

### ✅ Proposal Session (V4)
- **State Management**: Robust session handling for iterative proposal writing.
- **Section Locking**: Preventing race conditions during AI content generation.
- **Quality Feedback**: Real-time evaluator-style feedback on draft sections.

### ✅ Data Intelligence Layer
- **Neo4j + PostgreSQL + pgvector**: A sophisticated hybrid search system.
- **RRF (Reciprocal Rank Fusion)**: Mathematical merging of ranked results from multiple sources.

---

## Partially Implemented / Experimental

### ⚠️ Automated Testing Coverage
- While basic scenarios are covered, edge cases for **concurrent sessions** and **long-term memory summarization** require more comprehensive stress testing.
- Current tests focus heavily on Horizon Europe; more scenarios are needed for the newer programmes (LIFE, EU4Health).

### ⚠️ Data Freshness
- The CORDIS project database is based on a snapshot (13,850+ projects). An automated periodic sync from the EU Open Data Portal is planned but currently manual.

---

## Not Fully Finished / Planned

### ❌ Advanced Collaboration Features
- While API routes exist (`collaboration_routes.py`), the backend logic for multi-user real-time editing of the same proposal is in an early stage.

### ❌ Offline Mode
- The system heavily relies on LLM providers (Gemini/OpenAI). A path for fully local LLM execution (e.g., via Ollama/Llama-3) is not yet implemented.

### ❌ Mobile-Optimized Response Formatting
- The current formatter produces rich Markdown designed for web/desktop. A simplified, text-only or mobile-responsive format is on the roadmap.

---

## System Limits & Technical Debt

- **Vector Dimensions**: Using 3072-dim vectors (Google) prevents us from using standard HNSW indexes in pgvector 0.7.0. This leads to **Exact Search**, which adds ~200-300ms to retrieval time.
- **Context Window**: Long conversations (20+ turns) can approach the context limit of the reasoning model. Memory summarization is active but can occasionally lose subtle details from early in the chat.
- **Service Size**: `ConversationManager` was recently pruned, but remains the primary orchestrator. Further decomposition into smaller specialized managers is recommended for long-term scalability.
