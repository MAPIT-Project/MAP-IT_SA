"""Evaluation settings. Optional embedding configuration never enables API generation."""

import json
import os
from contextlib import ExitStack, contextmanager
from unittest.mock import patch


@contextmanager
def isolated_settings(model="gpt-6.1-sol", effort="high", embedding_env_file=None):
    names = ("HOME", "PATH", "CODEX_HOME", "LANG", "LC_ALL")
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment.update(
        PYTHON_DOTENV_DISABLED="1",
        DEFAULT_AI_PROVIDER="codex",
        CODEX_ENABLED="true",
        CODEX_MODEL=model,
        CODEX_REASONING_EFFORT=effort,
        AGENT_FRAMEWORK="pydantic",
        DATABASE_URL="postgresql://dummy:dummy@invalid/scenario_readonly",
        SUPABASE_URL="http://127.0.0.1:1",
        SUPABASE_SERVICE_KEY="dummy-scenario-key",
        REDIS_URL="redis://127.0.0.1:1",
        VECTOR_SEARCH_ENABLED="false",
    )
    if embedding_env_file is not None:
        from dotenv import load_dotenv

        # Normal application configuration loading, with no file inspection or
        # credential output. Retain only embedding settings in the evaluation.
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(embedding_env_file, override=False)
            embedding = {
                name: os.environ[name]
                for name in (
                    "GOOGLE_EMBEDDING_API_KEY",
                    "EMBEDDING_MODEL",
                    "EMBEDDING_DIMENSION",
                )
                if name in os.environ
            }
        if not embedding.get("GOOGLE_EMBEDDING_API_KEY"):
            raise ValueError(
                "Dedicated GOOGLE_EMBEDDING_API_KEY is required for live embedding checks"
            )
        environment.update(embedding, VECTOR_SEARCH_ENABLED="true")
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, environment, clear=True))
        stack.enter_context(patch("dotenv.load_dotenv", return_value=False))
        stack.enter_context(patch("dotenv.dotenv_values", return_value={}))
        stack.enter_context(
            patch("pydantic_settings.sources.DotEnvSettingsSource._read_env_files", return_value={})
        )
        yield


class ScenarioCache:
    """Disposable cache state used by the real pagination tool; never external Redis."""

    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        return True


class ScenarioSessionManager:
    """Actual proposal state with evaluation-local persistence only."""

    def __init__(self):
        from app.services.proposal_session.session_state import (
            ConversationState,
            ProposalDocument,
            ProposalSessionState,
            SectionState,
            SectionStatus,
        )

        from .catalog import PROPOSAL_TEXT

        content = PROPOSAL_TEXT
        document = ProposalDocument(
            proposal_id=-1,
            call_id="SYNTHETIC-EVALUATION",
            title="Synthetic hydrogen pilot",
            sections={
                "excellence.objectives": SectionState(
                    "excellence.objectives",
                    "Objectives",
                    content=content,
                    word_count=len(content.split()),
                    status=SectionStatus.DRAFT,
                )
            },
        )
        self.session = ProposalSessionState(
            session_id="synthetic-evaluation",
            user_id=-1,
            document=document,
            conversation=ConversationState(conversation_id=-1),
            active_section_id="excellence.objectives",
        )
        self.db_pool = None

    async def get_session(self, session_id):
        return self.session if session_id == self.session.session_id else None

    async def set_active_section(self, session_id, section_id):
        if (
            not await self.get_session(session_id)
            or section_id not in self.session.document.sections
        ):
            raise ValueError("Unknown evaluation section")
        self.session.active_section_id = section_id

    async def update_section_status(self, session_id, section_id, status):
        if not await self.get_session(session_id):
            return False
        section = self.session.document.get_section(section_id)
        if section is None:
            return False
        section.status = status
        return True


def make_agent(proposal=False, facts=None):
    """Run actual registry, models and dispatch without storage/analytics side effects."""
    from app.services.agents.proposal_aware_agent import ProposalAwareAgent
    from app.services.agents.tool_aware_agent import ToolAwareAgent

    cls = ProposalAwareAgent if proposal else ToolAwareAgent
    owner = cls.__new__(cls)
    owner.tools = {}
    owner.max_iterations = 4
    owner.enable_quality_analysis = False
    owner.quality_analyzer = None
    owner.plan_cache = None
    owner.analytics = None
    owner.speculative_executor = None
    owner._redis_client = ScenarioCache()
    owner._conversation_id = "synthetic-evaluation"
    owner._current_query = ""
    owner._init_tools()
    owner._init_llm()
    owner._reset_generation_metadata()
    if facts and facts.get("reference_project"):
        project = dict(facts["reference_project"][0])
        project["id"] = project["project_id"]
        project["cordis_url"] = f"https://cordis.europa.eu/project/id/{project['project_id']}"
        for name in ("eu_contribution", "total_cost"):
            if project.get(name) is not None:
                project[name] = float(project[name])
        owner._redis_client.setex(
            "merged_projects:synthetic-evaluation",
            60,
            json.dumps(
                {
                    "merged_projects": [project],
                    "total_found": 1,
                    "display_limit": 1,
                    "query_description": "source-verified reference project",
                },
                default=str,
            ),
        )
        owner._redis_client.setex("project_page:synthetic-evaluation", 60, "0")
    if proposal:
        owner.session_manager = ScenarioSessionManager()
        owner._init_proposal_tools()
        owner._current_session_id = owner.session_manager.session.session_id
        owner._current_proposal_context = owner.session_manager.session.get_context_for_agent()
    else:
        owner._current_session_id = None
    return owner
