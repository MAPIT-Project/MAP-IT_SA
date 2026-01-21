"""
Shared pytest fixtures and utilities for MAPIT tests.

This conftest.py consolidates fixtures that were previously scattered
across multiple test files, providing:
- Mock conversation managers
- Mock streaming generators
- Mock LLM clients (Gemini)
- Mock database connections
- Mock Redis clients
- Test data factories
- Common assertion helpers
"""

import pytest
import asyncio
import json
import os
import sys
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Optional
from dataclasses import dataclass, field
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# DATA CLASSES FOR TEST DATA
# =============================================================================

@dataclass
class MockCallResult:
    """Mock funding call result."""
    call_id: str = "HORIZON-CL5-2024-D3-01"
    title: str = "Clean Hydrogen Research"
    status: str = "open"
    deadline: str = "2024-06-15"
    budget: float = 10000000.0
    type: str = "RIA"
    programme: str = "Horizon Europe"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "title": self.title,
            "status": self.status,
            "deadline": self.deadline,
            "budget": self.budget,
            "type": self.type,
            "programme": self.programme,
        }


@dataclass
class MockProjectResult:
    """Mock project result."""
    project_id: str = "101000001"
    acronym: str = "HYDSTOR"
    title: str = "Hydrogen Storage Solutions"
    status: str = "SIGNED"
    total_cost: float = 5000000.0
    ec_contribution: float = 5000000.0
    start_date: str = "2023-01-01"
    end_date: str = "2026-12-31"
    coordinator_country: str = "DE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.project_id,
            "acronym": self.acronym,
            "title": self.title,
            "status": self.status,
            "totalCost": self.total_cost,
            "ecMaxContribution": self.ec_contribution,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "coordinatorCountry": self.coordinator_country,
        }


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    user_message: str
    response_text: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    @property
    def references_previous_result(self) -> bool:
        """Check if this turn references a previous result."""
        reference_patterns = [
            "the first", "the second", "the third", "the 1st", "the 2nd",
            "that one", "this call", "this project", "mentioned above",
            "tell me more", "more details", "elaborate",
        ]
        lower_msg = self.user_message.lower()
        return any(pattern in lower_msg for pattern in reference_patterns)


@dataclass
class ScenarioStep:
    """A single step in a conversation scenario."""
    message: str
    validations: List[Dict[str, Any]] = field(default_factory=list)
    expected_tools: List[str] = field(default_factory=list)
    expected_patterns: List[str] = field(default_factory=list)


@dataclass
class ConversationScenario:
    """A complete conversation scenario for testing."""
    name: str
    description: str
    steps: List[ScenarioStep]
    tags: List[str] = field(default_factory=list)
    stop_on_error: bool = True


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    name: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    """Result of running a conversation scenario."""
    scenario_name: str
    validations: List[ValidationResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    turns: List[ConversationTurn] = field(default_factory=list)

    @property
    def all_validations_passed(self) -> bool:
        return all(v.passed for v in self.validations)

    @property
    def failed_validations(self) -> List[ValidationResult]:
        return [v for v in self.validations if not v.passed]

    def add_validation(self, name: str, passed: bool, message: str = ""):
        self.validations.append(ValidationResult(passed=passed, name=name, message=message))

    def add_error(self, step_message: str, error: str):
        self.errors.append({"step": step_message, "error": error})


# =============================================================================
# MOCK GENAI (GOOGLE GENERATIVE AI)
# =============================================================================

def create_mock_genai():
    """Create a mock for google.generativeai that simulates the real module."""
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Final Answer: Test response based on the search results."
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model
    return mock_genai


@pytest.fixture
def mock_genai():
    """Fixture to create mock google.generativeai."""
    return create_mock_genai()


@pytest.fixture
def mock_genai_patched(mock_genai):
    """Auto-use fixture to mock google.generativeai in sys.modules."""
    with patch.dict('sys.modules', {'google.generativeai': mock_genai}):
        yield mock_genai


# =============================================================================
# MOCK CONVERSATION MANAGER
# =============================================================================

def create_mock_conversation_manager():
    """Create a fully mocked conversation manager."""
    mock = MagicMock()

    # Memory service
    mock.memory_service = MagicMock()
    mock.memory_service.redis_client = MagicMock()
    mock.memory_service.redis_client.ping.return_value = True
    mock.memory_service.ltm = MagicMock()
    mock.memory_service.get_conversation_context.return_value = {
        "short_term": [],
        "long_term_summary": "",
        "entities": {},
    }
    mock.memory_service.add_conversation_turn = MagicMock()

    # Response generator
    mock.response_generator = MagicMock()
    mock.response_generator.model = MagicMock()

    # Tool orchestrator
    mock.tool_orchestrator = MagicMock()
    mock.tool_orchestrator.execute_plan = AsyncMock(return_value=[])

    # Data intelligence
    mock.data_intelligence = MagicMock()
    mock.data_intelligence.search = AsyncMock(return_value=[])

    return mock


@pytest.fixture
def mock_conversation_manager():
    """Create a mock conversation manager fixture."""
    return create_mock_conversation_manager()


@pytest.fixture
def mock_conversation_manager_with_tools(mock_conversation_manager):
    """Conversation manager with mocked tool execution."""
    async def mock_tool_execution(tool_calls):
        results = []
        for call in tool_calls:
            tool_name = call.tool_name if hasattr(call, 'tool_name') else call.get('tool_name', '')
            if tool_name == 'search_funding_calls':
                results.append({
                    "tool": tool_name,
                    "result": {
                        "calls": [MockCallResult().to_dict()],
                        "count": 1,
                    }
                })
            elif tool_name == 'search_projects':
                results.append({
                    "tool": tool_name,
                    "result": {
                        "projects": [MockProjectResult().to_dict()],
                        "count": 1,
                    }
                })
            else:
                results.append({
                    "tool": tool_name,
                    "result": {"success": True}
                })
        return results

    mock_conversation_manager.tool_orchestrator.execute_plan = AsyncMock(side_effect=mock_tool_execution)
    return mock_conversation_manager


# =============================================================================
# MOCK STREAMING GENERATORS
# =============================================================================

async def create_mock_stream_generator(
    include_name_event: bool = True,
    include_tool_events: bool = True,
    response_text: str = "Here are the results based on your query.",
    tools_used: List[str] = None,
    error: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Create a mock async generator for streaming responses."""
    conversation_id = str(uuid.uuid4())[:8]

    if error:
        yield {"type": "error", "message": error}
        return

    yield {"type": "status", "stage": "processing", "message": "Processing your query..."}

    if include_name_event:
        yield {
            "type": "conversation_name",
            "name": "Test Conversation",
            "conversation_id": conversation_id
        }

    yield {"type": "status", "stage": "context_loaded", "message": "Context loaded"}
    yield {"type": "agent_thinking", "content": "Analyzing query and planning tools..."}

    if include_tool_events:
        tools = tools_used or ["search_funding_calls"]
        for tool in tools:
            yield {"type": "tool_call", "tool": tool, "args": {"keywords": "test"}}
            yield {"type": "tool_result", "tool": tool, "result": {"count": 5}}

    # Stream response tokens
    words = response_text.split()
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i:i+3])
        yield {"type": "token", "content": chunk + " "}

    yield {
        "type": "complete",
        "metadata": {
            "architecture": "simplified_v3",
            "tools_used": tools_used or ["search_funding_calls"],
            "iterations": 1,
            "processing_time_ms": 1500,
        }
    }


@pytest.fixture
def mock_stream_generator():
    """Fixture for mock stream generator factory."""
    return create_mock_stream_generator


# =============================================================================
# MOCK REDIS
# =============================================================================

def create_mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = 0
    mock.expire.return_value = True
    mock.rpush.return_value = 1
    mock.lrange.return_value = []
    mock.ltrim.return_value = True
    mock.llen.return_value = 0

    # Store for testing
    mock._store = {}

    def mock_set_impl(key, value, *args, **kwargs):
        mock._store[key] = value
        return True

    def mock_get_impl(key):
        return mock._store.get(key)

    mock.set.side_effect = mock_set_impl
    mock.get.side_effect = mock_get_impl

    return mock


@pytest.fixture
def mock_redis():
    """Fixture for mock Redis client."""
    return create_mock_redis()


# =============================================================================
# MOCK DATABASE
# =============================================================================

def create_mock_db_connection():
    """Create a mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None

    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchmany.return_value = []
    mock_cursor.rowcount = 0

    return mock_conn


@pytest.fixture
def mock_db_connection():
    """Fixture for mock database connection."""
    return create_mock_db_connection()


def create_mock_db_pool():
    """Create a mock database connection pool."""
    mock_pool = MagicMock()
    mock_conn = create_mock_db_connection()

    mock_pool.getconn.return_value = mock_conn
    mock_pool.putconn.return_value = None
    mock_pool.closeall.return_value = None

    return mock_pool


@pytest.fixture
def mock_db_pool():
    """Fixture for mock database pool."""
    return create_mock_db_pool()


# =============================================================================
# MOCK TOOL AWARE AGENT
# =============================================================================

@pytest.fixture
def mock_tool_aware_agent(mock_genai_patched):
    """Create a mocked ToolAwareAgent."""
    from app.services.agents.tool_aware_agent import ToolAwareAgent

    agent = ToolAwareAgent()

    # Mock the LLM response for tool selection
    mock_response = MagicMock()
    mock_response.text = """
    Thought: I need to search for funding calls related to the query.
    Action: search_funding_calls
    Action Input: {"keywords": "hydrogen", "status": "open"}

    Observation: Found 5 funding calls.

    Final Answer: I found 5 open funding calls for hydrogen research.
    """

    if hasattr(agent, 'llm') and agent.llm:
        agent.llm.generate_content = MagicMock(return_value=mock_response)

    return agent


# =============================================================================
# FASTAPI TEST CLIENT FIXTURES
# =============================================================================

@pytest.fixture
def app_with_mocked_manager(mock_conversation_manager):
    """Create FastAPI app with mocked conversation manager."""
    from app.api.conversation_routes_v3 import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with patch('app.api.conversation_routes_v3.conversation_manager', mock_conversation_manager):
        yield app, mock_conversation_manager


# =============================================================================
# TEST DATA FACTORIES
# =============================================================================

class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_calls(count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple mock funding calls."""
        calls = []
        for i in range(count):
            call = MockCallResult(
                call_id=f"HORIZON-CL5-2024-D3-{i+1:02d}",
                title=f"Test Call {i+1}",
                deadline=f"2024-{(i % 12) + 1:02d}-15"
            )
            calls.append(call.to_dict())
        return calls

    @staticmethod
    def create_projects(count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple mock projects."""
        projects = []
        for i in range(count):
            project = MockProjectResult(
                project_id=str(101000001 + i),
                acronym=f"PROJ{i+1}",
                title=f"Test Project {i+1}"
            )
            projects.append(project.to_dict())
        return projects

    @staticmethod
    def create_conversation_scenario(
        name: str,
        steps: List[Dict[str, Any]]
    ) -> ConversationScenario:
        """Create a conversation scenario from dict config."""
        scenario_steps = []
        for step in steps:
            scenario_steps.append(ScenarioStep(
                message=step.get("message", ""),
                validations=step.get("validations", []),
                expected_tools=step.get("expected_tools", []),
                expected_patterns=step.get("expected_patterns", []),
            ))

        return ConversationScenario(
            name=name,
            description=f"Test scenario: {name}",
            steps=scenario_steps,
        )


@pytest.fixture
def test_data_factory():
    """Fixture for test data factory."""
    return TestDataFactory()


# =============================================================================
# ASSERTION HELPERS
# =============================================================================

class AssertionHelpers:
    """Helper methods for common assertions."""

    @staticmethod
    def assert_sse_event_valid(event: Dict[str, Any]):
        """Assert that an SSE event has valid structure."""
        assert "type" in event, "SSE event must have 'type' field"
        valid_types = [
            'status', 'progress', 'conversation_name', 'agent_thinking',
            'tool_call', 'tool_result', 'token', 'complete', 'error'
        ]
        assert event["type"] in valid_types, f"Invalid event type: {event['type']}"

    @staticmethod
    def assert_response_has_required_fields(response: Dict[str, Any]):
        """Assert that a response has required fields."""
        assert "response" in response or "answer" in response, "Response must have content"
        if "metadata" in response:
            assert isinstance(response["metadata"], dict)

    @staticmethod
    def assert_tool_result_valid(result: Dict[str, Any], tool_name: str):
        """Assert that a tool result is valid."""
        assert "result" in result or "error" in result, "Tool result must have result or error"

    @staticmethod
    def assert_conversation_context_valid(context: Dict[str, Any]):
        """Assert that conversation context has expected structure."""
        expected_keys = ["short_term", "long_term_summary"]
        for key in expected_keys:
            assert key in context, f"Context missing key: {key}"


@pytest.fixture
def assertion_helpers():
    """Fixture for assertion helpers."""
    return AssertionHelpers()


# =============================================================================
# ENVIRONMENT FIXTURES
# =============================================================================

@pytest.fixture
def api_base_url():
    """Get API base URL from environment or default."""
    return os.environ.get("TEST_API_URL", "http://localhost:8000")


@pytest.fixture
def skip_if_no_database():
    """Skip test if DATABASE_URL is not set."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set - skipping database test")


@pytest.fixture
def skip_if_no_redis():
    """Skip test if REDIS_URL is not set."""
    if not os.environ.get("REDIS_URL"):
        pytest.skip("REDIS_URL not set - skipping Redis test")


@pytest.fixture
def skip_if_no_neo4j():
    """Skip test if NEO4J_URI is not set."""
    if not os.environ.get("NEO4J_URI"):
        pytest.skip("NEO4J_URI not set - skipping Neo4j test")


# =============================================================================
# ASYNC UTILITIES
# =============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def collect_stream_events(
    stream_generator: AsyncGenerator[Dict[str, Any], None]
) -> List[Dict[str, Any]]:
    """Collect all events from a stream generator."""
    events = []
    async for event in stream_generator:
        events.append(event)
    return events


@pytest.fixture
def collect_stream():
    """Fixture for collecting stream events."""
    return collect_stream_events


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    yield

    # Reset known singletons
    singleton_classes = [
        ('app.services.analytics.tool_analytics_service', 'ToolAnalyticsService'),
        ('app.services.feedback.feedback_service', 'FeedbackService'),
    ]

    for module_path, class_name in singleton_classes:
        try:
            module = sys.modules.get(module_path)
            if module:
                cls = getattr(module, class_name, None)
                if cls and hasattr(cls, '_instance'):
                    cls._instance = None
        except Exception:
            pass
