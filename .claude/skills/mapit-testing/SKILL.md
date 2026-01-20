# MAPIT Testing Patterns Skill

This skill documents testing patterns for the MAPIT AI project, including async testing, mocking strategies, and test organization.

## Test Configuration

### pyproject.toml

```ini
[tool.pytest.ini_options]
addopts = "-ra -q"
testpaths = ["tests", "."]
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
]
```

### Running Tests

```bash
# All tests
make test
pytest

# Specific file
pytest tests/test_tool_aware_agent.py

# With coverage
pytest --cov=app tests/

# Verbose output
pytest -v tests/

# Only integration tests
pytest -m integration
```

---

## Test File Structure

### Organization Pattern

```python
"""
Tests for [feature/module name].

Tests cover:
- [Behavior 1]
- [Behavior 2]
- [Error handling]
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.module import ClassUnderTest


class TestFeatureName:
    """Test [feature description]."""

    @pytest.fixture
    def setup_fixture(self):
        """Setup common test data."""
        return {"key": "value"}

    def test_specific_behavior(self, setup_fixture):
        """Test [specific behavior]."""
        # Arrange
        data = setup_fixture

        # Act
        result = function_under_test(data)

        # Assert
        assert result is not None
```

### Naming Conventions

- **Files**: `test_[module_name].py`
- **Classes**: `Test[FeatureName]`
- **Methods**: `test_[behavior]_[scenario]` or `test_[method]_[expected_result]`

Examples:
- `test_empty_query`
- `test_handles_llm_error`
- `test_ria_cost_ratios_sum_to_one`

---

## Async Testing Patterns

### Using asyncio.run() (Preferred)

```python
def test_async_function_returns_result(self):
    """Test async function in sync test method."""
    result = asyncio.run(async_function_under_test(
        param1="value1",
        param2="value2"
    ))

    assert result is not None
    assert isinstance(result, dict)
```

### Using @pytest.mark.asyncio

```python
import pytest

class TestAsyncFeature:
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test async tool execution."""
        agent = ToolAwareAgent()

        result = await agent.process_query(
            query="Find hydrogen calls",
            context="",
            conversation_history=[]
        )

        assert result is not None
        assert 'answer' in result or 'response' in result
```

### Async Generator Testing

```python
@pytest.fixture
def mock_stream_generator(self):
    """Create a mock async generator for streaming."""
    async def generator():
        yield {"type": "status", "stage": "processing"}
        yield {"type": "token", "content": "Hello"}
        yield {"type": "complete", "metadata": {}}
    return generator

@pytest.mark.asyncio
async def test_streaming_response(self, mock_stream_generator):
    """Test streaming response handling."""
    events = []
    async for event in mock_stream_generator():
        events.append(event)

    assert len(events) == 3
    assert events[-1]['type'] == 'complete'
```

---

## Mocking Patterns

### Mock LLM Responses

```python
@pytest.fixture
def mock_agent(self):
    """Create mock agent with mocked LLM."""
    agent = ToolAwareAgent()

    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.text = """
    Thought: I need to search for funding calls.
    Action: search_funding_calls
    Action Input: {"keywords": "hydrogen", "status": "open"}
    """

    # Mock the llm attribute
    agent.llm = MagicMock()
    agent.llm.generate_content = MagicMock(return_value=mock_response)

    return agent


def test_agent_uses_correct_tool(self, mock_agent):
    """Test agent selects correct tool."""
    result = asyncio.run(mock_agent.process_query(
        query="Find hydrogen funding calls",
        context="",
        conversation_history=[]
    ))

    assert mock_agent.llm.generate_content.called
```

### Mock External Libraries (google.generativeai)

```python
def create_mock_genai():
    """Create a mock for google.generativeai."""
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Final Answer: Test response."
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model
    return mock_genai


@pytest.fixture(autouse=True)
def mock_genai_fixture():
    """Auto-use fixture to mock google.generativeai for all tests."""
    mock_genai = create_mock_genai()
    with patch.dict('sys.modules', {'google.generativeai': mock_genai}):
        yield mock_genai
```

### Mock Database Connections

```python
@pytest.fixture
def mock_db_connection(self):
    """Mock PostgreSQL connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'name': 'Test Project', 'budget': 5000000}
    ]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def test_query_returns_results(self, mock_db_connection):
    """Test database query returns results."""
    with patch('psycopg2.connect', return_value=mock_db_connection):
        tool = BudgetBenchmarkTool()
        result = tool._query_sql("hydrogen", "RIA", 10)

        assert len(result) == 1
        assert result[0]['name'] == 'Test Project'
```

### Mock Redis Client

```python
@pytest.fixture
def mock_conversation_manager(self):
    """Create a mock conversation manager with Redis."""
    mock = MagicMock()
    mock.memory_service = MagicMock()
    mock.memory_service.redis_client = MagicMock()
    mock.memory_service.redis_client.ping.return_value = True
    mock.memory_service.ltm = MagicMock()
    return mock
```

### Mock Neo4j Graph Service

```python
@pytest.fixture
def mock_graph_service(self):
    """Mock Neo4j graph service."""
    mock_graph = MagicMock()
    mock_graph.execute_query.return_value = [
        {'name': 'Org A', 'projectCount': 10},
        {'name': 'Org B', 'projectCount': 8}
    ]
    return mock_graph


def test_graph_query(self, mock_graph_service):
    """Test graph-based query."""
    with patch.object(PartnerDiscoveryTool, '_graph_service', mock_graph_service):
        tool = PartnerDiscoveryTool()
        result = tool._query_graph("hydrogen", "CLUSTER-5", 10)

        assert len(result) == 2
```

---

## Fixture Patterns

### Class-Level Fixtures

```python
class TestBudgetBenchmark:
    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            return BudgetBenchmarkTool()

    def test_normalize_cluster(self, tool):
        """Test cluster normalization."""
        assert tool._normalize_cluster_code('CL5') == 'CLUSTER-5'
```

### Generator Fixtures (Setup/Teardown)

```python
@pytest.fixture
def temp_data(self):
    """Setup temporary data with cleanup."""
    # Setup
    data = create_test_data()
    yield data
    # Teardown
    cleanup_test_data(data)
```

### Auto-use Fixtures

```python
@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    ServiceClass._instance = None
    yield
    ServiceClass._instance = None
```

### Parameterized Fixtures

```python
@pytest.fixture(params=['RIA', 'IA', 'CSA'])
def action_type(self, request):
    """Parameterized fixture for action types."""
    return request.param


def test_budget_for_action_type(self, action_type):
    """Test budget calculation for different action types."""
    tool = BudgetCalculatorTool()
    result = tool.calculate_budget(action_type=action_type, budget=5000000)
    assert result['success'] is True
```

---

## Response Validation Patterns

### Structure Validation

```python
def test_response_structure(self):
    """Test response has required structure."""
    result = asyncio.run(tool_execute({'keywords': 'test'}, {}))

    assert 'success' in result
    assert 'tool_name' in result

    if result['success']:
        assert 'results' in result or 'data' in result
        assert 'metadata' in result
```

### Metadata Validation

```python
def test_metadata_completeness(self):
    """Test metadata has required fields."""
    result = asyncio.run(tool_execute({'keywords': 'test'}, {}))

    metadata = result.get('metadata', {})

    assert 'search_type' in metadata
    assert 'timestamp' in metadata
    assert metadata['search_type'] in ['hybrid', 'sql_only', 'graph_only']
```

### Pydantic Model Testing

```python
from app.api.conversation_routes_v3 import MessageRequest, MessageResponse


def test_message_request_validation(self):
    """Test Pydantic model validation."""
    # Valid request
    req = MessageRequest(message="Test question")
    assert req.message == "Test question"
    assert req.include_context is True  # Default

    # With explicit values
    req = MessageRequest(message="Test", include_context=False)
    assert req.include_context is False
```

---

## SSE Event Testing

### Event Type Validation

```python
def test_sse_event_types(self):
    """Test that all SSE event types are valid."""
    allowed_types = [
        'status', 'progress', 'conversation_name', 'agent_thinking',
        'tool_call', 'tool_result', 'token', 'complete', 'error'
    ]

    for event_type in allowed_types:
        chunk = {'type': event_type}
        assert chunk['type'] in allowed_types
```

### Event Sequence Validation

```python
def test_event_sequence(self):
    """Test events follow correct sequence."""
    events = [
        {'type': 'status', 'stage': 'processing'},
        {'type': 'agent_thinking', 'thought': '...'},
        {'type': 'tool_call', 'tool_name': 'search'},
        {'type': 'tool_result', 'success': True},
        {'type': 'token', 'content': 'Response...'},
        {'type': 'complete', 'metadata': {}}
    ]

    # Verify sequence
    assert events[0]['type'] == 'status'
    assert events[-1]['type'] == 'complete'

    # Tokens must come before complete
    token_indices = [i for i, e in enumerate(events) if e['type'] == 'token']
    complete_index = next(i for i, e in enumerate(events) if e['type'] == 'complete')
    assert all(i < complete_index for i in token_indices)
```

### SSE Format Validation

```python
def test_sse_format(self):
    """Test SSE wire format."""
    import json

    chunk = {"type": "token", "content": "Hello"}
    sse_output = f"data: {json.dumps(chunk)}\n\n"

    # Must have "data: " prefix
    assert sse_output.startswith("data: ")
    # Must end with double newline
    assert sse_output.endswith("\n\n")
    # Must be valid JSON after prefix
    json_part = sse_output.replace("data: ", "").strip()
    assert json.loads(json_part) == chunk
```

---

## Error Handling Testing

### Exception Handling

```python
def test_handles_exception_gracefully(self):
    """Test error handling returns valid response."""
    agent = ToolAwareAgent()
    agent.llm = MagicMock()
    agent.llm.generate_content.side_effect = Exception("API Error")

    result = asyncio.run(agent.process_query(
        query="Test",
        context="",
        conversation_history=[]
    ))

    # Should return error response, not crash
    assert result is not None
    # May have 'error' key or still have 'response'
```

### Error Response Structure

```python
def test_error_response_structure(self):
    """Test error response has required fields."""
    error_event = {
        "type": "error",
        "error": "Database connection failed",
        "stage": "error"
    }

    assert error_event["type"] == "error"
    assert "error" in error_event
    assert isinstance(error_event["error"], str)
```

---

## Edge Case Testing

### Empty/Null Inputs

```python
def test_empty_query(self):
    """Test handling empty query."""
    result = asyncio.run(tool_execute({'keywords': ''}, {}))

    # Should handle gracefully
    assert result is not None
    # May fail with error message or succeed with empty results


def test_none_parameters(self):
    """Test handling None parameters."""
    result = asyncio.run(tool_execute({'keywords': None}, {}))

    assert result is not None
```

### Large Inputs

```python
def test_very_long_query(self):
    """Test handling very long input."""
    long_query = "Find hydrogen " * 1000

    result = asyncio.run(tool_execute({'keywords': long_query}, {}))

    # Should not crash
    assert result is not None
```

### Boundary Values

```python
def test_rating_boundary_values(self):
    """Test rating at boundaries."""
    # Valid boundaries
    assert validate_rating(1) is True
    assert validate_rating(5) is True

    # Invalid
    assert validate_rating(0) is False
    assert validate_rating(6) is False
```

---

## Configuration Validation Testing

### Cost Ratios Sum Check

```python
class TestBudgetCalculatorConfig:
    def test_ria_cost_ratios_sum_to_one(self):
        """Test RIA cost ratios sum to ~1.0."""
        tool = BudgetCalculatorTool()
        ratios = tool.COST_RATIOS['RIA']

        total = sum(ratios.values())
        assert abs(total - 1.0) < 0.01, f"RIA ratios sum to {total}"


    def test_all_action_types_have_required_categories(self):
        """Test all action types have all cost categories."""
        tool = BudgetCalculatorTool()
        required = ['personnel', 'equipment', 'travel', 'subcontracting', 'other_direct', 'indirect']

        for action_type, ratios in tool.COST_RATIOS.items():
            for category in required:
                assert category in ratios, f"{action_type} missing {category}"
```

---

## Singleton Testing

```python
def test_singleton_returns_same_instance(self):
    """Test singleton pattern."""
    # Reset singleton
    ServiceClass._instance = None

    service1 = ServiceClass()
    service2 = ServiceClass()

    assert service1 is service2


def test_service_disabled_without_config(self):
    """Test service disabled when config missing."""
    ServiceClass._instance = None

    with patch.dict('os.environ', {'DATABASE_URL': ''}, clear=False):
        service = ServiceClass()
        assert service.enabled is False
```

---

## Real Integration Tests (Conditional)

```python
# Skip if DATABASE_URL not set
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set"
)


class TestRealToolExecution:
    """Real tests against actual database."""

    @pytest.mark.asyncio
    async def test_budget_benchmark_real(self):
        """Test budget benchmark with real data."""
        from app.services.tools.budget_benchmark import get_budget_benchmark_execute

        result = await get_budget_benchmark_execute(
            {"action_type": "RIA", "cluster": "CLUSTER-5"},
            {}
        )

        assert result["success"] is True
        assert "statistics" in result
        assert result["statistics"]["projects_analyzed"] > 0
```

---

## Assertion Patterns

```python
# Type checking
assert isinstance(result, dict)
assert isinstance(result['data'], list)

# Value equality
assert result['success'] is True
assert result['tool_name'] == "my_tool"

# Presence checking
assert 'answer' in result or 'response' in result
assert 'metadata' in result

# Range checking
assert 0 <= metadata['confidence'] <= 1
assert result['count'] > 0

# List operations
assert 'search_funding_calls' in tools
assert len(results) >= 1
assert all(r.get('id') for r in results)

# Approximate equality (floats)
assert abs(total - 1.0) < 0.01

# String matching
assert 'hydrogen' in result['query'].lower()
assert result['status'] in ['success', 'partial', 'error']

# None checking
assert result.get('error') is None
```

---

## Test Template

```python
"""
Tests for [module name].
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tools.my_tool import MyTool, my_tool_execute


class TestMyTool:
    """Tests for MyTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance with mocked dependencies."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            tool = MyTool()
            tool._graph_service = None  # Disable graph for unit tests
            return tool

    def test_initialization(self, tool):
        """Test tool initializes correctly."""
        assert tool is not None
        assert tool.db_url is not None

    def test_normalize_input(self, tool):
        """Test input normalization."""
        result = tool._normalize_input('TEST')
        assert result == 'test'

    def test_query_returns_results(self, tool):
        """Test query returns expected structure."""
        with patch.object(tool, '_get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [{'id': 1}]
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._query_sql('test', 10)

            assert len(result) == 1

    def test_handles_empty_results(self, tool):
        """Test handling of empty results."""
        with patch.object(tool, '_get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value = mock_cursor

            result = tool._query_sql('nonexistent', 10)

            assert result == []


@pytest.mark.asyncio
async def test_execute_function():
    """Test the async execute function."""
    with patch('app.services.tools.my_tool.MyTool') as MockTool:
        mock_instance = MockTool.return_value
        mock_instance.main_method.return_value = {
            'success': True,
            'results': [{'id': 1}]
        }

        result = await my_tool_execute({'keywords': 'test'}, {})

        assert result['success'] is True


@pytest.mark.asyncio
async def test_execute_missing_required_param():
    """Test execute with missing required parameter."""
    result = await my_tool_execute({}, {})

    assert result['success'] is False
    assert 'error' in result
```
