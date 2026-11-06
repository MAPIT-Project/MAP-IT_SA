"""Budget contracts with synthetic responses; no real CLI, network or inference."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.ai.budget import (
    InferenceBudget,
    InferenceBudgetExceeded,
    InferenceProviderBlocked,
    budgeted_inference,
)
from app.services.ai.types import TextResponse


class SyntheticModel:
    def __init__(self, provider="codex"):
        self.provider = provider
        self.model_name = "synthetic-configured"
        self.calls = 0

    def response(self):
        return TextResponse(
            "Synthetic answer",
            self.provider,
            "synthetic-actual",
            {"input_tokens": 7, "output_tokens": 3},
        )

    @budgeted_inference
    def generate_content(self, prompt, stream=False):
        self.calls += 1
        return iter([self.response()]) if stream else self.response()

    @budgeted_inference
    async def generate_content_async(self, prompt, stream=False):
        self.calls += 1
        await asyncio.sleep(0)
        if stream:

            async def chunks():
                yield self.response()

            return chunks()
        return self.response()


def test_sync_limit_blocks_before_an_extra_dispatch():
    model = SyntheticModel()
    budget = InferenceBudget(max_requests=1)
    with pytest.raises(InferenceBudgetExceeded, match="request limit"):
        with budget:
            model.generate_content("first")
            model.generate_content("second")
    assert model.calls == 1
    assert budget.snapshot()["attempted"] == 1
    assert budget.snapshot()["reported_tokens"] == 10
    assert budget.snapshot()["models"] == {"synthetic-actual": 1}


@pytest.mark.asyncio
async def test_limit_is_shared_by_concurrent_tasks():
    model = SyntheticModel()
    budget = InferenceBudget(max_requests=3)
    with pytest.raises(InferenceBudgetExceeded):
        with budget:
            results = await asyncio.gather(
                *[model.generate_content_async(f"request {index}") for index in range(10)],
                return_exceptions=True,
            )
            assert sum(isinstance(result, TextResponse) for result in results) == 3
            assert sum(isinstance(result, InferenceBudgetExceeded) for result in results) == 7
    assert model.calls == 3
    assert budget.snapshot()["completed"] == 3


@pytest.mark.asyncio
async def test_sync_helpers_in_threads_share_the_run_limit():
    model = SyntheticModel()
    budget = InferenceBudget(max_requests=2)
    with pytest.raises(InferenceBudgetExceeded):
        with budget:
            await asyncio.to_thread(model.generate_content, "sync helper one")
            await asyncio.to_thread(model.generate_content, "sync helper two")
            await model.generate_content_async("async helper three")
    assert model.calls == 2


@pytest.mark.asyncio
async def test_text_facade_and_transport_are_charged_once(monkeypatch):
    from app.core.config import settings
    from app.services.ai.factory import create_text_model

    monkeypatch.setattr(settings, "codex_enabled", True)
    model = create_text_model("chat_reasoning", provider="codex")
    transport = SyntheticModel()
    monkeypatch.setattr(model, "_get_model", lambda: ("codex", transport))
    with InferenceBudget(max_requests=1) as budget:
        result = await model.generate_content_async("one job through two wrappers")
    assert result.text == "Synthetic answer"
    assert transport.calls == 1
    assert budget.snapshot()["attempted"] == 1
    assert budget.snapshot()["reported_tokens"] == 10
    assert budget.snapshot()["attempts"][0]["step"] == "chat_reasoning"


@pytest.mark.parametrize("provider", ["gemini", "openai", "openrouter"])
def test_other_providers_cannot_receive_prompts(provider):
    model = SyntheticModel(provider)
    budget = InferenceBudget(max_requests=30, allowed_providers={"codex"})
    with pytest.raises(InferenceProviderBlocked):
        with budget:
            model.generate_content("must not reach another provider")
    assert model.calls == 0
    assert budget.snapshot()["attempted"] == 0


def test_swallowed_stop_is_re_raised_when_scope_exits():
    model = SyntheticModel()
    budget = InferenceBudget(max_requests=0)
    with pytest.raises(InferenceBudgetExceeded):
        with budget:
            try:
                model.generate_content("no allowance")
            except Exception:
                pass  # Simulate a legacy helper returning a fallback.
    assert model.calls == 0


def test_reported_token_limit_blocks_subsequent_requests():
    model = SyntheticModel()
    budget = InferenceBudget(max_requests=20, max_reported_tokens=5)
    with pytest.raises(InferenceBudgetExceeded, match="token limit"):
        with budget:
            model.generate_content("response reports ten tokens")
            model.generate_content("would exceed measured limit")
    # The first in-flight response cannot be cut off at an unknown token count.
    assert model.calls == 1
    assert budget.snapshot()["reported_tokens"] == 10


def test_failed_attempt_spends_allowance_without_logging_contents():
    class Broken(SyntheticModel):
        @budgeted_inference
        def generate_content(self, prompt):
            self.calls += 1
            raise RuntimeError("Sensitive synthetic provider diagnostics")

    model = Broken()
    with InferenceBudget(max_requests=1) as budget:
        with pytest.raises(RuntimeError):
            model.generate_content("Sensitive synthetic prompt")
    snapshot = budget.snapshot()
    assert snapshot["failed"] == 1
    assert snapshot["unknown_usage_requests"] == 1
    assert snapshot["attempts"][0]["error_type"] == "RuntimeError"
    assert "Sensitive" not in str(snapshot)


@pytest.mark.asyncio
async def test_cancelled_attempt_spends_allowance():
    started = asyncio.Event()

    class Waiting(SyntheticModel):
        @budgeted_inference
        async def generate_content_async(self, prompt):
            self.calls += 1
            started.set()
            await asyncio.Future()

    model = Waiting()
    with InferenceBudget(max_requests=1) as budget:
        task = asyncio.create_task(model.generate_content_async("synthetic wait"))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert model.calls == 1
    assert budget.snapshot()["cancelled"] == 1


def test_sync_stream_counts_on_consumption_and_does_not_leak_scope():
    model = SyntheticModel()
    budget = InferenceBudget(max_requests=2)
    with pytest.raises(InferenceBudgetExceeded):
        with budget:
            stream = model.generate_content("lazy", True)
            assert model.calls == 0
            assert next(stream).text == "Synthetic answer"
            # Caller code executes while the stream is suspended at a yield.
            model.generate_content("a separate invocation")
            assert list(stream) == []
            model.generate_content("blocked third invocation")
    assert model.calls == 2
    assert budget.snapshot()["attempted"] == 2


@pytest.mark.asyncio
async def test_async_stream_reports_usage_once():
    model = SyntheticModel()
    with InferenceBudget(max_requests=1) as budget:
        stream = await model.generate_content_async("synthetic stream", stream=True)
        assert model.calls == 0
        chunks = [chunk async for chunk in stream]
        assert len(chunks) == 1
    assert model.calls == 1
    assert budget.snapshot()["completed"] == 1
    assert budget.snapshot()["reported_tokens"] == 10


@pytest.mark.asyncio
async def test_framework_budget_stop_propagates(monkeypatch):
    from pydantic_ai.models.function import FunctionModel

    from app.services.agents.framework import runtime
    from app.services.agents.tool_registry import AgentPlan

    def forbidden_response(messages, info):
        pytest.fail("The model was called despite a zero-request budget")

    @asynccontextmanager
    async def selected(step, model_hint=None):
        yield FunctionModel(forbidden_response), "codex"

    monkeypatch.setattr(runtime, "model_for_step", selected)
    owner = SimpleNamespace(
        llm=SimpleNamespace(model_name="synthetic"),
        tools={},
        max_iterations=5,
        plan_cache=None,
        _finalize_plan=Mock(),
        _record_generation=Mock(),
        _select_knowledge_sections=Mock(return_value="Synthetic knowledge"),
    )
    plan = AgentPlan("Synthetic query", "simple", [])
    with pytest.raises(InferenceBudgetExceeded):
        with InferenceBudget(max_requests=0):
            await runtime.run_agent_loop(owner, plan.query, "", plan)
    assert plan.final_answer is None
    owner._finalize_plan.assert_called_once_with(plan)


def test_native_usage_objects_are_recorded():
    @dataclass
    class Usage:
        input_tokens: int = 11
        output_tokens: int = 4

    class Native(SyntheticModel):
        @budgeted_inference
        def generate_content(self, prompt):
            return SimpleNamespace(model_name="actual-native", usage=Usage())

    with InferenceBudget(max_requests=1) as budget:
        Native().generate_content("synthetic")
    assert budget.snapshot()["reported_tokens"] == 15


def test_no_scope_keeps_existing_behavior_and_scope_cannot_be_reused():
    model = SyntheticModel()
    assert model.generate_content("outside scope").text == "Synthetic answer"
    budget = InferenceBudget(max_requests=1)
    with budget:
        model.generate_content("inside scope")
        with pytest.raises(ValueError, match="nested"):
            with InferenceBudget():
                pass
    with pytest.raises(ValueError, match="reused"):
        with budget:
            pass


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["gemini", "openai"])
@pytest.mark.parametrize("method", ["generate_text", "generate_structured", "generate_stream"])
async def test_legacy_proposal_providers_are_blocked_before_sdk_dispatch(provider_name, method):
    from app.services.proposal_writing.ai_providers.base import BaseAIProvider, ProviderConfig
    from app.services.proposal_writing.ai_providers.gemini_provider import GeminiProvider
    from app.services.proposal_writing.ai_providers.openai_provider import OpenAIProvider

    cls = GeminiProvider if provider_name == "gemini" else OpenAIProvider
    provider = cls.__new__(cls)
    BaseAIProvider.__init__(provider, ProviderConfig(provider_name, "dummy", "synthetic-model"))
    # Budget checks execute before either SDK accessor is touched.
    with pytest.raises(InferenceProviderBlocked):
        with InferenceBudget(max_requests=30, allowed_providers={"codex"}) as budget:
            if method == "generate_stream":
                async for _ in provider.generate_stream("must stay local"):
                    pytest.fail("Blocked provider produced a chunk")
            elif method == "generate_structured":
                await provider.generate_structured("must stay local", {"type": "object"})
            else:
                await provider.generate_text("must stay local")
    assert budget.snapshot()["attempted"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["generate_text", "generate_structured", "generate_stream"])
async def test_multi_provider_service_does_not_retry_or_fallback_after_budget_stop(method):
    from app.services.proposal_writing.ai_providers.multi_provider_service import (
        MultiProviderAIService,
    )

    class Legacy:
        config = SimpleNamespace(name="gemini", model="synthetic-model")
        name = "gemini"
        calls = 0

        def is_available(self):
            return True

        @budgeted_inference
        async def generate_text(self, **kwargs):
            self.calls += 1
            pytest.fail("SDK dispatch must be blocked")

        @budgeted_inference
        async def generate_structured(self, **kwargs):
            self.calls += 1
            pytest.fail("SDK dispatch must be blocked")

        @budgeted_inference
        async def generate_stream(self, **kwargs):
            self.calls += 1
            pytest.fail("SDK dispatch must be blocked")
            yield "unreachable"

    class Fallback(Legacy):
        config = SimpleNamespace(name="codex", model="synthetic-model")
        name = "codex"

    primary, fallback = Legacy(), Fallback()
    service = MultiProviderAIService.__new__(MultiProviderAIService)
    service.providers = [primary, fallback]
    with pytest.raises(InferenceProviderBlocked):
        with InferenceBudget(max_requests=30, allowed_providers={"codex"}):
            if method == "generate_stream":
                async for _ in service.generate_stream("synthetic prompt"):
                    pytest.fail("A blocked run produced output")
            elif method == "generate_structured":
                await service.generate_structured("synthetic prompt", {"type": "object"})
            else:
                await service.generate_text("synthetic prompt")
    assert primary.calls == 0
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_structured_sdk_usage_survives_response_conversion():
    from unittest.mock import AsyncMock

    from app.services.proposal_writing.ai_providers.base import BaseAIProvider, ProviderConfig
    from app.services.proposal_writing.ai_providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider.__new__(OpenAIProvider)
    BaseAIProvider.__init__(provider, ProviderConfig("openai", "dummy", "synthetic-configured"))
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"valid": true}'))],
        model="synthetic-actual",
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=6, total_tokens=18),
    )
    sdk_call = AsyncMock(return_value=response)
    provider._available = True
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=sdk_call))
    )
    with InferenceBudget(max_requests=1, allowed_providers={"openai"}) as budget:
        assert await provider.generate_structured("synthetic", {"type": "object"}) == {
            "valid": True
        }
    sdk_call.assert_awaited_once()
    assert budget.snapshot()["reported_tokens"] == 18
    assert budget.snapshot()["models"] == {"synthetic-actual": 1}


@pytest.mark.asyncio
async def test_async_generator_charges_on_consumption_and_cleans_up():
    closed = False

    class Streaming(SyntheticModel):
        @budgeted_inference
        async def generate_stream(self, prompt):
            nonlocal closed
            self.calls += 1
            try:
                yield self.response()
                await asyncio.Future()
            finally:
                closed = True

    model = Streaming()
    with InferenceBudget(max_requests=1) as budget:
        stream = model.generate_stream("synthetic stream")
        assert model.calls == 0
        assert (await anext(stream)).text == "Synthetic answer"
        await stream.aclose()
    assert closed
    assert budget.snapshot()["cancelled"] == 1
    assert budget.snapshot()["reported_tokens"] == 10
