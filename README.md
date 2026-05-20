# MAP-IT: Multi-Programme EU Funding Research Assistant

A production-grade Retrieval-Augmented Generation (RAG) system for querying European Union funding programmes. MAP-IT implements sophisticated multi-source intelligent search, agentic AI capabilities, and comprehensive tooling for **6 EU funding programmes**.

> [!WARNING]
> **Project Disclaimer & Review Notice:**
> - **Horizon Europe Focus**: This system was primarily designed and optimized for **Horizon Europe**. The other 5 programmes (Erasmus+, Creative Europe, EU4Health, Digital Europe, and LIFE) are supported but are not as advanced or as thoroughly tested.
> - **AI-Assisted Single-Dev Build**: This large codebase was built by a **single developer** leveraging AI extensively to execute the work of a full development team.
> - **Manual Review Required**: Due to the massive scale of this project, a complete manual review of all code has not been feasible. There may be duplicate logic, redundant code, or potential security vulnerabilities. **Please perform a thorough security audit and code review before deploying this system to production or making it public.**

---

## 🚀 Overview

MAP-IT is designed to help researchers, consultants, and organizations navigate the complex landscape of EU funding. It provides a conversational interface that can find calls, analyze projects, check eligibility, and assist in proposal writing.

### Supported Programmes
1. **Horizon Europe**: Research & Innovation
2. **Erasmus+**: Education, Training, Youth & Sport
3. **Creative Europe**: Culture & Media
4. **EU4Health**: Public Health
5. **Digital Europe**: Strategic Digital Technologies
6. **LIFE**: Environment & Climate Action

---

## 🛠️ Quick Start

### Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose** (for Neo4j, Redis, and API)
- **Supabase Account** (for pgvector document storage)
- **Google Gemini API Key** (Primary AI reasoning and embeddings)

### Installation & Setup

1. **Clone & Enter**
   ```bash
   git clone <repo-url>
   cd MAP-IT_SA
   ```

2. **Environment & Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   make install-dev
   ```

3. **Configuration**
   ```bash
   cp .env.example .env
   # Update .env with your keys (Gemini, Database, Neo4j, etc.)
   ```

4. **Launch Infrastructure**
   ```bash
   make docker-up
   ```

5. **Initialize Data**
   See the [Data Ingestion Guide](docs/guides/DATA_INGESTION.md) for detailed steps on populating the databases.

6. **Run API**
   ```bash
   make run-reload  # Accessible at http://localhost:8000
   ```

---

## 📚 Documentation Suite

To keep things organized, the documentation is divided into specialized guides:

| Guide | Description |
|-------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | **Recommended Start Point**: Deep dive into developer rules, system architecture overview, command references, and agentic tool designs. |
| **[Tool Reference](docs/guides/TOOL_REFERENCE.md)** | Detailed explanation of all 42+ agentic tools. |
| **[Data Ingestion](docs/guides/DATA_INGESTION.md)** | How to get the data, run ingestion scripts, and setup the graph. |
| **[Database Schema](docs/DATABASE_SCHEMA.md)** | Deep dive into the 35 active PostgreSQL tables and vector search logic. |
| **[Roadmap & Status](docs/guides/ROADMAP.md)** | Current implementation status, system limits, and future plans. |
| **[System Architecture](docs_tracked/SYSTEM_ARCHITECTURE.md)** | Deep dive into the V3/V4 architectures and service layer. |
| **[API Specification](docs_tracked/FRONTEND_STREAMING_V3_SPEC.md)** | Details on SSE streaming and V3 endpoint formats. |

---

## 🧠 Key Architecture: V3 Simplified

The project has transitioned to a **Simplified Agentic Architecture**:
- **No Manual Intent Routing**: The `ToolAwareAgent` analyzes the query and decides which tools to call dynamically.
- **ReAct Pattern**: The agent follows a Reasoning + Acting loop to solve complex queries.
- **Hybrid Data Flow**: Tools automatically merge results from Neo4j (Graph), PostgreSQL (Structured), and pgvector (Unstructured) using **RRF (Reciprocal Rank Fusion)**.

---

## 🧪 Development & Testing

We use `make` for common tasks:
```bash
make test    # Run all pytest scenarios
make lint    # Run ruff check (Excludes .claude templates)
make format  # Auto-format with black, isort, and ruff
```

**Testing Tip**: Scenario-based tests are located in `tests/scenarios/`. Use these to verify complex multi-turn conversation flows.

---

## 🛑 Limits to Keep in Mind
- **Vector Search**: Uses exact search for high-dimensional vectors (3072-dim).
- **Data Snapshots**: CORDIS data is local; live call data is synced via API.
- **Programme Maturity**: Only **Horizon Europe** is fully mature and comprehensively tested. Other programmes (Erasmus+, Creative Europe, EU4Health, Digital Europe, LIFE) are integrated but have simpler implementations and less coverage.
- **AI Code & Security**: Built by a single developer leveraging AI to handle multiple engineering domains. Unreviewed/duplicate code may exist, and security audits have not been manually conducted. Thorough review is required before going public.

---

## ❤️ Credits & Support
Developed and maintained by **Anmar Ram** ([anmar.noah@gmail.com](mailto:anmar.noah@gmail.com)) for the MAP-IT platform. For technical inquiries, refer to the [System Architecture](docs_tracked/SYSTEM_ARCHITECTURE.md).
