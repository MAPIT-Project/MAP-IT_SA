"""Public activity traces use actual execution, with mocked models and business tools."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic_ai.messages import ModelResponse, ThinkingPart, ToolCallPart

from app.services.agents.framework import runtime
from app.services.agents.framework.progress import tool_activity, tool_outcome
from app.services.agents.tool_registry import ToolCall
from tests.test_pydantic_agent_runtime import (
    final,
    owner_with_tool,
    plan,
    tool_returns,
    use_model,
)


@pytest.mark.parametrize(
    "name,params,expected",
    [
        (
            "get_project_details",
            {"project_id": "IMAGHyNE"},
            "Looking up project details (project id: IMAGHyNE).",
        ),
        (
            "search_documents",
            {"query": "minimum consortium requirements"},
            "Searching official documents (query: minimum consortium requirements).",
        ),
        (
            "get_country_statistics",
            {"country": "DE"},
            "Checking country participation and funding (country: DE).",
        ),
        (
            "generate_section_draft",
            {"section_id": "excellence.objectives", "call_id": "HORIZON-TEST"},
            "Drafting the proposal section (section id: excellence.objectives; call id: HORIZON-TEST).",
        ),
    ],
)
def test_activity_identifies_actual_tool_scope(name, params, expected):
    assert tool_activity(name, params, "Display") == expected


def test_activity_does_not_echo_uploaded_text_or_unbounded_markup():
    thought = tool_activity(
        "generate_section_draft",
        {
            "section_id": "excellence.objectives",
            "content": "PRIVATE UPLOADED BODY",
            "guidance": "SECRET INSTRUCTIONS",
        },
        "Draft",
    )
    assert "PRIVATE" not in thought
    assert "SECRET" not in thought
    thought = tool_activity(
        "search_documents", {"query": "[click](https://example.invalid)\n" + "x" * 5000}, "Search"
    )
    assert len(thought) < 160
    assert "\n" not in thought
    assert "[" not in thought


@pytest.mark.parametrize(
    "result,success,expected",
    [
        ({"partners": [{}] * 42}, True, "Partners returned 42 partners."),
        ({"documents": []}, True, "Partners returned 0 document excerpts."),
        ({"project": None}, True, "Partners returned no matching project record."),
        (None, True, "Partners returned no usable output."),
        (
            {"error": "SECRET diagnostic"},
            False,
            "Partners failed; no verified result is available from this call.",
        ),
    ],
)
def test_outcomes_report_actual_counts_and_empty_or_failed_results(result, success, expected):
    assert tool_outcome("Partners", result, success) == expected


@pytest.mark.asyncio
async def test_stream_reports_tool_action_result_review_and_final_answer_without_extra_inference(
    monkeypatch,
):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall(
                "synthetic_search",
                {"limit": 2},
                result={"projects": [{"id": "one"}, {"id": "two"}]},
                success=True,
            )
        ]
    )
    requests = []

    def respond(messages, info):
        requests.append(messages)
        if tool_returns(messages):
            return final(info)
        return ModelResponse(
            [
                ThinkingPart("PRIVATE MODEL REASONING"),
                ToolCallPart("synthetic_search", {"limit": 2}),
            ]
        )

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    current = plan()
    count, _ = await runtime.run_agent_loop(owner, "Synthetic query", "", current, emit)
    assert count == len(requests) == 2
    assert current.error is None
    thought_events = [event for event in events if event["type"] == "agent_thinking"]
    assert [event["stage"] for event in thought_events] == [
        "reviewing",
        "tool_started",
        "reviewing",
        "answer_ready",
    ]
    assert not any(event.get("action") == "observe" for event in events)
    call = next(event for event in events if event["type"] == "tool_call")
    result = next(event for event in events if event["type"] == "tool_result")
    assert thought_events[1]["thought"] == call["reasoning"]
    assert thought_events[1]["call_id"] == call["call_id"] == result["call_id"]
    assert "2 projects" in result["activity_summary"]
    assert "2 projects" in thought_events[2]["thought"]
    assert "2 projects" in current.reasoning_steps[-1].thought
    assert "PRIVATE MODEL REASONING" not in str(events)


@pytest.mark.asyncio
async def test_failed_tool_is_visible_and_never_claims_verified_evidence(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall("synthetic_search", {"limit": 2}, result={"success": False}, success=True)
        ]
    )

    def respond(messages, info):
        return (
            final(info, "The source is unavailable.")
            if tool_returns(messages)
            else ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})])
        )

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    current = plan()
    _, results = await runtime.run_agent_loop(owner, "Synthetic query", "", current, emit)
    assert results == {}
    result = next(event for event in events if event["type"] == "tool_result")
    assert result["success"] is False
    assert "failed" in result["activity_summary"]
    assert "no verified result" in current.reasoning_steps[-1].thought


@pytest.mark.asyncio
async def test_parallel_calls_keep_outcomes_attached_to_their_call_ids(monkeypatch):
    owner = owner_with_tool()
    both_started = asyncio.Event()
    arrivals = []

    async def execute(specs):
        limit = specs[0]["parameters"]["limit"]
        arrivals.append(limit)
        if len(arrivals) == 2:
            both_started.set()
        await both_started.wait()
        if limit == 1:
            await asyncio.sleep(0)
        return [
            ToolCall(
                "synthetic_search",
                {"limit": limit},
                result={"projects": [{}] * limit},
                success=True,
            )
        ]

    owner._execute_tool_calls = execute

    def respond(messages, info):
        if tool_returns(messages):
            return final(info)
        return ModelResponse(
            [ToolCallPart("synthetic_search", {"limit": number}) for number in (1, 2)]
        )

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    await runtime.run_agent_loop(owner, "Synthetic query", "", plan(), emit)
    calls = {event["call_id"]: event for event in events if event["type"] == "tool_call"}
    results = [event for event in events if event["type"] == "tool_result"]
    assert len(calls) == len(results) == 2
    for event in results:
        count = calls[event["call_id"]]["parameters"]["limit"]
        assert event["activity_summary"].endswith(
            f"{count} {'project' if count == 1 else 'projects'}."
        )


@pytest.mark.asyncio
async def test_generation_failure_emits_failed_activity_without_answer_ready(monkeypatch):
    owner = owner_with_tool()

    def respond(messages, info):
        raise RuntimeError("PRIVATE SDK PAYLOAD")

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    await runtime.run_agent_loop(owner, "Synthetic query", "", plan(), emit)
    assert events[-1]["stage"] == "failed"
    assert not any(event.get("stage") == "answer_ready" for event in events)
    assert "PRIVATE" not in str(events)


@pytest.mark.asyncio
async def test_direct_answer_does_not_claim_a_lookup_or_add_an_inference_call(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock()
    use_model(monkeypatch, lambda messages, info: final(info, "Ready to help."))
    events = []

    async def emit(event):
        events.append(event)

    count, _ = await runtime.run_agent_loop(owner, "Test", "", plan(), emit)
    assert count == 1
    assert [event["stage"] for event in events] == ["reviewing", "answer_ready"]
    assert "No tool results were used" in events[-1]["thought"]
    owner._execute_tool_calls.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_arguments_produce_validation_activity_before_a_real_tool_starts(monkeypatch):
    owner = owner_with_tool()
    owner._execute_tool_calls = AsyncMock(
        return_value=[
            ToolCall("synthetic_search", {"limit": 2}, result={"projects": [{}]}, success=True)
        ]
    )
    requests = []

    def respond(messages, info):
        requests.append(messages)
        if len(requests) == 1:
            return ModelResponse([ToolCallPart("synthetic_search", {"limit": "invalid"})])
        if len(requests) == 2:
            return ModelResponse([ToolCallPart("synthetic_search", {"limit": 2})])
        return final(info)

    use_model(monkeypatch, respond)
    events = []

    async def emit(event):
        events.append(event)

    current = plan()
    await runtime.run_agent_loop(owner, "Synthetic query", "", current, emit)
    assert current.error is None
    retry = next(event for event in events if event.get("stage") == "retrying")
    started = next(event for event in events if event.get("stage") == "tool_started")
    assert "Checking tool arguments" in retry["thought"]
    assert events.index(retry) < events.index(started)
    owner._execute_tool_calls.assert_awaited_once()
