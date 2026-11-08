# Local Antigravity CLI Text Provider

MAPIT can route text generation and agent reasoning jobs to the authenticated local Antigravity CLI (`agy`).
This integration is designed for local development, leveraging local Google authentication sessions and Gemini 3.8 models (such as `gemini-3.8-flash-high`) with configurable reasoning effort without requiring paid API keys.

---

## 1. Overview & Architecture

The Antigravity adapter (`app/services/ai/antigravity.py`) executes `agy` non-interactively using `-p` (prompt mode). The CLI manages authentication, model communication, and session tokens via the local environment.

### Host vs. Docker Isolation Requirement

> [!IMPORTANT]
> **Antigravity CLI runs on the host machine, NOT inside Docker.**
> `agy` relies on the host's Linux D-Bus/secret-service keyring (`github.com/zalando/go-keyring`) to access your authenticated Google session.
>
> If you start the API container via `docker compose up --build`, the containerised API will fail with:
> ```text
> Antigravity CLI not found at 'agy'. Install it or set ANTIGRAVITY_CLI_PATH
> ```
>
> **Correct Hybrid Development Workflow:**
> 1. Run backing data services in Docker:
>    ```bash
>    docker compose up -d redis neo4j
>    ```
> 2. Run the FastAPI backend directly on the host using the local API launcher:
>    ```bash
>    .venv/pydantic-agent/bin/python scripts/run_local_api.py --provider antigravity --local-services --port 18000
>    ```
>    This automatically points to the host-mapped ports (`16379` for Redis, `17687` for Neo4j, `54322` for PostgreSQL).

---

## 2. Prerequisites & Authentication

Install the Antigravity CLI on the host machine and ensure it is authenticated:

```bash
# Verify CLI is in your PATH
agy --version

# Log in interactively if not already authenticated
agy auth login
```

The adapter checks for executable accessibility of the binary at `ANTIGRAVITY_CLI_PATH` (defaults to `agy`).

---

## 3. Configuration

Enable Antigravity in your `.env` or process environment:

```bash
# Global provider selection
DEFAULT_AI_PROVIDER=antigravity

# Antigravity CLI settings
ANTIGRAVITY_ENABLED=true
ANTIGRAVITY_CLI_PATH=agy
ANTIGRAVITY_MODEL=gemini-3.8-flash-high
ANTIGRAVITY_REASONING_EFFORT=high
ANTIGRAVITY_TIMEOUT_SECONDS=300
```

### Environment Variables Reference

| Variable | Type | Default | Description |
|---|---|---|---|
| `ANTIGRAVITY_ENABLED` | bool | `false` | Master toggle. Must be `true` to use Antigravity. |
| `DEFAULT_AI_PROVIDER` | string | `gemini` | Set to `antigravity` to use as primary provider. |
| `ANTIGRAVITY_CLI_PATH` | string | `agy` | Path to the `agy` binary on the host system. |
| `ANTIGRAVITY_MODEL` | string | `gemini-3.8-flash-high` | Model name passed via `--model`. |
| `ANTIGRAVITY_REASONING_EFFORT` | string | `high` | Reasoning effort level (`low`, `medium`, `high`, `xhigh`, `max`). |
| `ANTIGRAVITY_TIMEOUT_SECONDS` | float | `300.0` | Timeout per CLI invocation in seconds. |

### Why 300 Seconds Timeout?

When using `gemini-3.8-flash-high` with `ANTIGRAVITY_REASONING_EFFORT=high`, the model generates 8,000–13,000 thinking tokens to reason through complex queries. A single inference step typically takes 30–60 seconds. In an agentic loop (e.g., query analysis → tool invocation → synthesis), multiple turns are executed. Setting `ANTIGRAVITY_TIMEOUT_SECONDS=300` ensures that multi-turn reasoning queries do not time out prematurely.

### Named-Step Routing

You can use Antigravity selectively for specific pipeline steps while leaving other tasks to API providers:

```bash
DEFAULT_AI_PROVIDER=gemini
ANTIGRAVITY_ENABLED=true
AI_STEP_PROVIDERS='{"chat_reasoning":"antigravity","proposal_generation":"gemini"}'
```

---

## 4. Security & Sandbox Controls

When executing `agy`, the adapter enforces strict containment to ensure the model functions purely as an inference engine without touching host resources:

1. **CLI Sandbox Flags**:
   - `--sandbox`: Runs in an isolated sandbox.
   - `--disable-slash-commands`: Prevents interactive command triggers.
   - `--settings`: Passes strict permissions configuration:
     ```json
     {
       "toolPermission": "strict",
       "permissions": {
         "deny": ["command(*)", "read_file(*)", "write_file(*)", "read_url(*)", "mcp(*)"]
       }
     }
     ```
2. **Ephemeral Workspace Isolation**:
   - Each CLI invocation runs in an isolated temporary directory outside the codebase.
   - A `GEMINI.md` file is automatically placed in the temporary directory instructing the model:
     - To act as an application inference engine.
     - Never to explore files, run shell commands, or invoke autonomous subagents.
     - To conclude the turn immediately on Turn 1 via `finish`.
   - This optimization reduces unnecessary latency from autonomous exploratory tool loops.
3. **Process Clean-up**:
   - CLI processes are executed in separate POSIX process groups (`start_new_session=True`).
   - If a request is cancelled or times out, the entire process group is terminated cleanly (`SIGTERM` followed by `SIGKILL`).

---

## 5. Pydantic AI Agent Framework Integration

MAPIT uses Pydantic AI for V3 chat and V4 proposal sessions:

- **`AntigravityAgentModel`** (`app/services/agents/framework/models.py`):
  Subclasses `CodexAgentModel` and wraps `AntigravityTextModel`.
- **Tool Protocol**:
  Pydantic AI translates registered Python tools (all 42 V3 tools) into the schema expected by the adapter. The model outputs structured tool calls via JSON schema.
- **Python-Side Tool Execution**:
  Tools execute strictly inside the MAPIT Python application environment (accessing PostgreSQL, Neo4j, etc.). No tools are executed inside the CLI sandbox.
- **Streaming Compatibility**:
  Yields completed message chunks compatible with SSE events (`agent_thinking`, `tool_call`, `tool_result`, `token`, `complete`).

---

## 6. Embeddings Note

`EmbeddingService` continues to use Google `gemini-embedding-001` (3072-dimensional vectors) via `GOOGLE_EMBEDDING_API_KEY` (or `GEMINI_API_KEY`). The Antigravity CLI does not provide embedding endpoints. Vector search and pgvector schemas remain unchanged.

---

## 7. Verification & Testing

### 1. Configuration & CLI Check
Run the launcher check to verify that `agy` is discovered and authenticated:
```bash
python scripts/run_local_api.py --check
```
Output:
```json
{
  "api_port": 18000,
  "antigravity_cli_available": true,
  "antigravity_cli_path": "agy",
  "antigravity_configured_model": "gemini-3.8-flash-high",
  "antigravity_reasoning_effort": "high",
  "antigravity_timeout_seconds": 300.0,
  "default_ai_provider": "antigravity"
}
```

### 2. Mocked Offline Tests
Verify adapter parsing, process lifecycle, and launcher arguments without calling external services:
```bash
pytest tests/test_antigravity_adapter.py tests/test_local_api_launcher.py tests/test_pydantic_agent_models.py -v
```

### 3. Live End-to-End Chat Test
Start the local server and verify query execution:
```bash
# 1. Start backing data containers
docker compose up -d redis neo4j

# 2. Start API on host
.venv/pydantic-agent/bin/python scripts/run_local_api.py --env-file .env --provider antigravity --local-services --port 18000

# 3. Test in another terminal
curl -X POST http://127.0.0.1:18000/api/v3/conversation/100/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what EU funding programmes do you cover?"}'
```
