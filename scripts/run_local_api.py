"""Run this checkout on the host with private runtime configuration loaded normally.

Provider and local-service overrides apply only to this process. No .env or CLI
authentication file is copied, inspected, printed or modified by this launcher.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def local_database_url(value, port):
    """Keep the configured database/authentication; use the published local port."""
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise ValueError("DATABASE_URL must be a PostgreSQL URL for local-service overrides")
    userinfo = parsed.netloc.rsplit("@", 1)[0] + "@" if "@" in parsed.netloc else ""
    return urlunsplit(parsed._replace(netloc=f"{userinfo}127.0.0.1:{port}"))


def configure(args):
    from dotenv import load_dotenv

    # The application consumes its private configuration through the standard
    # loader. The agent never reads or displays file contents or secret values.
    load_dotenv(dotenv_path=args.env_file, override=False)
    if args.provider:
        os.environ["DEFAULT_AI_PROVIDER"] = args.provider
    if args.provider == "codex":
        os.environ["CODEX_ENABLED"] = "true"
    if args.provider == "antigravity":
        os.environ["ANTIGRAVITY_ENABLED"] = "true"
    if args.model:
        os.environ[f"{args.provider.upper()}_MODEL"] = args.model
    if args.reasoning_effort:
        if args.provider == "codex":
            os.environ["CODEX_REASONING_EFFORT"] = args.reasoning_effort
        elif args.provider == "antigravity":
            os.environ["ANTIGRAVITY_REASONING_EFFORT"] = args.reasoning_effort
    os.environ["AGENT_FRAMEWORK"] = "pydantic"
    if args.local_services:
        os.environ["DATABASE_URL"] = local_database_url(
            os.environ.get("DATABASE_URL", ""), args.database_port
        )
        os.environ.update(
            SUPABASE_URL=f"http://127.0.0.1:{args.supabase_port}",
            NEO4J_URI=f"bolt://127.0.0.1:{args.neo4j_port}",
            REDIS_URL=f"redis://127.0.0.1:{args.redis_port}/0",
            REDIS_HOST="127.0.0.1",
            REDIS_PORT=str(args.redis_port),
            CELERY_BROKER_URL=f"redis://127.0.0.1:{args.redis_port}/0",
            CELERY_RESULT_BACKEND=f"redis://127.0.0.1:{args.redis_port}/0",
            DOCKER_ENV="false",
        )
    os.environ["PGCONNECT_TIMEOUT"] = "5"


async def check_runtime():
    from app.core.ai_routing import TEXT_STEPS
    from app.core.config import settings
    from app.services.ai.codex import CodexTextModel
    from app.services.ai.factory import resolve_provider

    selected = {step: resolve_provider(step) for step in sorted(TEXT_STEPS)}
    report = {
        "source_root": str(ROOT),
        "agent_framework": settings.agent_framework,
        "default_ai_provider": settings.default_ai_provider,
        "text_steps": selected,
        "codex_model": settings.codex_model,
        "codex_reasoning_effort": settings.codex_reasoning_effort,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimension,
        "embedding_key_configured": bool(settings.effective_embedding_api_key),
    }
    if "codex" in selected.values():
        await CodexTextModel(settings).check_available()
        report["codex_cli_authenticated"] = True
    if "antigravity" in selected.values():
        from app.services.ai.antigravity import AntigravityTextModel

        await AntigravityTextModel(settings).check_available()
        report["antigravity_cli_available"] = True
    import psycopg2
    import redis

    # Verify the known funding dataset without touching conversations or profiles.
    connection = psycopg2.connect(settings.database_url, connect_timeout=5)
    try:
        connection.set_session(readonly=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM projects WHERE id = %s)", ("101137586",))
            report["reference_funding_project_available"] = bool(cursor.fetchone()[0])
        connection.rollback()
    finally:
        connection.close()
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=5, socket_timeout=5)
    try:
        report["redis_available"] = bool(client.ping())
    finally:
        client.close()
    print(json.dumps(report))
    return 0 if report["reference_funding_project_available"] and report["redis_available"] else 1


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument(
        "--provider", choices=("gemini", "openai", "openrouter", "codex", "antigravity")
    )
    parser.add_argument("--model")
    parser.add_argument(
        "--reasoning-effort",
        choices=("minimal", "low", "medium", "high", "xhigh", "max", "ultra"),
    )
    parser.add_argument("--local-services", action="store_true")
    parser.add_argument("--database-port", type=int, default=54322)
    parser.add_argument("--supabase-port", type=int, default=54321)
    parser.add_argument("--neo4j-port", type=int, default=17687)
    parser.add_argument("--redis-port", type=int, default=16379)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--check", action="store_true", help="Read-only checks, no model inference")
    args = parser.parse_args(argv)
    if args.model and not args.provider:
        parser.error("--model requires --provider")
    if args.reasoning_effort and args.provider not in ("codex", "antigravity"):
        parser.error("--reasoning-effort requires --provider codex or antigravity")
    return args


def main():
    args = arguments()
    os.chdir(ROOT)
    try:
        configure(args)
        if args.check:
            logging.disable(logging.CRITICAL)
            return asyncio.run(check_runtime())
        import uvicorn

        uvicorn.run("main:app", host=args.host, port=args.port, log_level="info")
        return 0
    except Exception as error:
        # SDK exceptions and validation errors may contain secret field values.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
