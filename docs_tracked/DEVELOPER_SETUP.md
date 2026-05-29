# Developer Setup & Database Restore Guide

Welcome to the MAP-IT SA development setup. This guide covers how to initialize the database structures, restore bulk CORDIS and Neo4j data, and resolve network constraints for a clean developer onboarding experience.

---

## 🛠️ Step-by-Step Local Setup

### 1. Environment & Packages Setup
First, run the virtual environment creator and install dependencies:
```bash
./scripts/setup.sh
source .venv/bin/activate
```
*Note: `setup.sh` copies `.env.example` to `.env` in the root. Fill out the necessary API keys (`GOOGLE_EMBEDDING_API_KEY`, etc.) in `.env` before running services.*

### 2. Resolving Supabase / Docker Compose Network
By default, the `docker-compose.yml` links the api container to an external docker network: `supabase_network_supabase_cli` (which runs the Supabase CLI services).

If you are running the Supabase CLI:
1. Make sure you have installed Supabase CLI: [Supabase CLI Guide](https://supabase.com/docs/guides/cli)
2. Initialize and start Supabase:
   ```bash
   supabase init
   supabase start
   ```
3. Run docker compose to start the API:
   ```bash
   make run
   ```

#### Standalone Dev Workaround (No Supabase CLI)
If you prefer running a direct PostgreSQL image without the Supabase CLI, modify `docker-compose.yml` to spin up a local database container:

```yaml
# Add this service to docker-compose.yml:
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: mapit-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_secure_password
      POSTGRES_DB: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - mapit_network

volumes:
  postgres_data:
```
Then, remove the `external: true` network declaration for `supabase_network` at the bottom of the compose file, and point your `.env` `DATABASE_URL` to `postgresql://postgres:postgres_secure_password@postgres:5432/postgres`.

---

## 🗄️ Database Initialization & Restoration

The project is packaged with a unified schema script inside the `migration/` directory and database dumps in `neo4j_backup/`. You can set up the database using either a clean schema initialization or by restoring a bulk data dump.

### Option A: Clean Schema Initialization (Recommended)
To set up all the database tables, views, indexes, triggers, and RPC functions (such as `hybrid_search` and `reload_schema`) without loading large datasets, use the unified `schema.sql` script located inside the `migration/` directory:

```bash
# Point to your local database endpoint
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Execute schema.sql
psql "$DATABASE_URL" -f migration/schema.sql
```

This sets up the 34 active tables and ensures that your PostgreSQL instance matches the exact SvelteKit Drizzle models and python backend requirements.

### Option B: PostgreSQL Dump Restoration
To restore the projects, organizations, embeddings, and analytics schemas with the pre-populated CORDIS bulk dataset (~14,000 projects):
```bash
# Set your DATABASE_URL (using your database endpoint)
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Execute pg_restore
pg_restore --clean --no-acl --no-owner -d "$DATABASE_URL" neo4j_backup/project_embeddings.dump
```

### Neo4j Graph Restoration
To load the consortium networks and partner relationships into Neo4j:

1. Copy the database dump to the Neo4j import volume:
   ```bash
   cp neo4j_backup/neo4j.dump neo4j/import/
   ```
2. Stop the Neo4j database container to release file locks:
   ```bash
   docker compose stop neo4j
   ```
3. Load the dump into the Neo4j database:
   ```bash
   docker compose run --entrypoint neo4j-admin --rm neo4j database load \
     --from-path=/var/lib/neo4j/import/ \
     neo4j \
     --overwrite-destination=true
   ```
4. Restart the Neo4j container:
   ```bash
   docker compose start neo4j
   ```

---

## 🗂️ SQL Schema Migrations & Types

The core schemas are maintained under SvelteKit Drizzle or raw SQL files inside the backend `migration/` directory.

> [!IMPORTANT]
> **Data Type Alignment**: The original migration file `migration/001_init_schema.sql` defines `projects.id` and `organizations.projectID` as `VARCHAR(50)`. However, the running database and frontend Drizzle schema (`schema.ts`) define them as `integer`.
>
> When creating or altering tables manually, ensure they use `integer` types to avoid foreign key and serialization mismatches between the SvelteKit API and python backend. The `migration/schema.sql` script incorporates this alignment correctly.

---

## 🗺️ Code Execution Architecture

Queries flow through different pipelines depending on the requested functionality.

### V3 Flow: Tool-Aware Chat
Answering user questions dynamically using ReAct loop and DataIntelligence tools:

```mermaid
sequenceDiagram
    participant User
    participant Route as conversation_routes_v3.py
    participant Agent as ToolAwareAgent
    participant DIS as DataIntelligenceService
    participant Neo4j as Neo4j Graph
    participant SQL as PostgreSQL/pgvector
    participant Formatter as V3ResponseFormatter

    User->>Route: POST /api/v3/conversation/{id}/message/stream
    Route->>Agent: generate_response(query, context)
    loop ReAct Loop
        Agent->>Agent: Think (Decide which tool to use)
        Agent->>DIS: Execute Tool (e.g. find_experienced_partners)
        DIS->>Neo4j: Query partner relations
        DIS->>SQL: Query organisation stats
        DIS-->>Agent: Return tool results
    end
    Agent->>Formatter: Format response markdown
    Formatter-->>Route: Rich formatted text + tools log
    Route-->>User: Server-Sent Events (SSE) stream
```

### V4 Flow: Proposal Writer Session
Used for proposal generation and quality grading:

```mermaid
sequenceDiagram
    participant User
    participant Route as proposal_session_routes.py
    participant PSM as ProposalSessionManager
    participant Agent as ProposalAwareAgent
    participant Evaluator as QualityEvaluatorAgent

    User->>Route: POST /api/v4/proposals/sessions
    Route->>PSM: create_session(call_id, template_id)
    Route-->>User: Return session details (ID)

    User->>Route: POST /api/v4/proposals/sessions/{id}/generate
    Route->>Agent: generate_section(section_name, context)
    Agent-->>Route: Return draft proposal text

    User->>Route: POST /api/v4/proposals/sessions/{id}/evaluate
    Route->>Evaluator: score_proposal_section(draft_text, criteria)
    Evaluator-->>User: Return scores (0-5) + gap analysis suggestions
```
