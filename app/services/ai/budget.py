"""Optional, process-local generation limits for bounded evaluation runs.

Counts application generation invocations, including failed/cancelled attempts.
Provider-internal HTTP retries are not observable here. Reported token limits
stop subsequent invocations; they cannot stop unknown tokens already in flight.
No prompts, answers, credentials or tool arguments are retained.
"""

import asyncio
import inspect
from collections import Counter
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Any

_budget = ContextVar("mapit_inference_budget", default=None)
_attempt = ContextVar("mapit_inference_attempt", default=None)


class InferenceBudgetError(RuntimeError):
    """Stop an evaluation without selecting another model or provider."""


class InferenceBudgetExceeded(InferenceBudgetError):
    pass


class InferenceProviderBlocked(InferenceBudgetError):
    pass


def _nonnegative_integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _usage(response):
    usage = getattr(response, "usage", None)
    if not usage:
        usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None
    if not isinstance(usage, Mapping):
        if hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        else:
            usage = {
                name: getattr(usage, name, None)
                for name in (
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "prompt_tokens",
                    "completion_tokens",
                    "prompt_token_count",
                    "candidates_token_count",
                    "total_token_count",
                    "thoughts_token_count",
                )
            }
    input_tokens = _nonnegative_integer(
        usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("prompt_token_count")
    )
    output_tokens = _nonnegative_integer(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("candidates_token_count")
    )
    total = usage.get("total_tokens") or usage.get("total_token_count")
    if total is None:
        total = (
            input_tokens + output_tokens + _nonnegative_integer(usage.get("thoughts_token_count"))
        )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": _nonnegative_integer(total),
    }


@dataclass
class _Attempt:
    budget: Any
    number: int
    provider: str
    model: str | None
    step: str | None
    status: str = "pending"
    usage: dict[str, int] | None = None
    error_type: str | None = None

    def record(self, response):
        usage = _usage(response)
        actual_model = getattr(response, "model_name", None) or getattr(response, "model", None)
        with self.budget._lock:
            if isinstance(actual_model, str) and actual_model:
                self.model = actual_model
            if usage is not None:
                # Facade, framework and transport may all see this same response.
                # Streaming usage is often cumulative; never sum duplicates.
                self.usage = {
                    key: max(value, (self.usage or {}).get(key, 0)) for key, value in usage.items()
                }


class InferenceBudget:
    """Share one limit across an evaluation's async tasks and to_thread calls.

    Use ``raise_if_stopped()`` after each scenario: some legacy application
    helpers catch Exception and return a fallback. Context exit also re-raises
    a swallowed stop signal. A budget is deliberately single-use.
    """

    def __init__(self, max_requests=30, allowed_providers=None, max_reported_tokens=None):
        if not isinstance(max_requests, int) or isinstance(max_requests, bool) or max_requests < 0:
            raise ValueError("max_requests must be a nonnegative integer")
        if max_reported_tokens is not None and (
            not isinstance(max_reported_tokens, int)
            or isinstance(max_reported_tokens, bool)
            or max_reported_tokens < 0
        ):
            raise ValueError("max_reported_tokens must be a nonnegative integer or None")
        self.max_requests = max_requests
        self.allowed_providers = (
            frozenset(allowed_providers) if allowed_providers is not None else frozenset({"codex"})
        )
        if not self.allowed_providers or any(
            provider not in {"codex", "gemini", "openai", "openrouter"}
            for provider in self.allowed_providers
        ):
            raise ValueError("allowed_providers must name supported providers")
        self.max_reported_tokens = max_reported_tokens
        self._attempts = []
        self._lock = Lock()
        self._stop = None
        self._token = None
        self._closed = False

    def __enter__(self):
        if _budget.get() is not None or self._token is not None or self._closed:
            raise ValueError("Inference budgets cannot be nested or reused")
        self._token = _budget.set(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        _budget.reset(self._token)
        self._token = None
        self._closed = True
        if exc_type is None:
            self.raise_if_stopped()
        return False

    def raise_if_stopped(self):
        with self._lock:
            stopped = self._stop
        if stopped is not None:
            exception, message = stopped
            raise exception(message)

    def _reserve(self, provider, model, step):
        with self._lock:
            if self._stop is None:
                if self._closed:
                    self._stop = (InferenceBudgetExceeded, "Inference budget scope is closed")
                elif provider not in self.allowed_providers:
                    self._stop = (
                        InferenceProviderBlocked,
                        f"Inference provider '{provider}' is not allowed by this run",
                    )
                elif len(self._attempts) >= self.max_requests:
                    self._stop = (
                        InferenceBudgetExceeded,
                        f"Inference request limit reached ({self.max_requests})",
                    )
                elif (
                    self.max_reported_tokens is not None
                    and sum(
                        (attempt.usage or {}).get("total_tokens", 0) for attempt in self._attempts
                    )
                    >= self.max_reported_tokens
                ):
                    self._stop = (
                        InferenceBudgetExceeded,
                        f"Reported inference token limit reached ({self.max_reported_tokens})",
                    )
            if self._stop is not None:
                exception, message = self._stop
                raise exception(message)
            attempt = _Attempt(self, len(self._attempts) + 1, provider, model, step)
            self._attempts.append(attempt)
            return attempt

    def snapshot(self):
        with self._lock:
            attempts = [
                {
                    "number": attempt.number,
                    "provider": attempt.provider,
                    "model": attempt.model,
                    "step": attempt.step,
                    "status": attempt.status,
                    "usage": dict(attempt.usage) if attempt.usage is not None else None,
                    "error_type": attempt.error_type,
                }
                for attempt in self._attempts
            ]
            return {
                "max_requests": self.max_requests,
                "allowed_providers": sorted(self.allowed_providers),
                "max_reported_tokens": self.max_reported_tokens,
                "attempted": len(attempts),
                "completed": sum(a["status"] == "completed" for a in attempts),
                "failed": sum(a["status"] == "failed" for a in attempts),
                "cancelled": sum(a["status"] == "cancelled" for a in attempts),
                "pending": sum(a["status"] == "pending" for a in attempts),
                "unknown_usage_requests": sum(a["usage"] is None for a in attempts),
                "reported_tokens": sum((a["usage"] or {}).get("total_tokens", 0) for a in attempts),
                "providers": dict(Counter(a["provider"] for a in attempts)),
                "models": dict(Counter(a["model"] or "unknown" for a in attempts)),
                "stopped": self._stop is not None,
                "stop_reason": self._stop[1] if self._stop is not None else None,
                "counting_unit": "application generation invocations; provider-internal retries excluded",
                "attempts": attempts,
            }


@contextmanager
def inference_request(provider, model=None, step=None):
    budget = _budget.get()
    if budget is None:
        yield None
        return
    parent = _attempt.get()
    if (
        parent is not None
        and parent.budget is budget
        and parent.provider == provider
        and parent.status == "pending"
        and not budget._closed
    ):
        budget.raise_if_stopped()
        yield parent
        return
    attempt = budget._reserve(provider, model, step)
    token = _attempt.set(attempt)
    try:
        yield attempt
    except (asyncio.CancelledError, GeneratorExit):
        with budget._lock:
            attempt.status = "cancelled"
        raise
    except BaseException as exc:
        with budget._lock:
            attempt.status = "failed"
            attempt.error_type = type(exc).__name__
        raise
    else:
        with budget._lock:
            attempt.status = "completed"
    finally:
        _attempt.reset(token)


@contextmanager
def _suspend_attempt():
    # A yielded streaming chunk returns control to caller code. A separate model
    # call made by that caller must not inherit this stream's nested-call exemption.
    token = _attempt.set(None)
    try:
        yield
    finally:
        _attempt.reset(token)


def record_inference_response(response):
    """Record raw SDK usage before a provider converts it to JSON or text chunks."""
    attempt = _attempt.get()
    if attempt is not None:
        attempt.record(response)
    return _usage(response)


def budgeted_inference(function=None, *, step=None):
    """Account for native sync/async calls and lazy streaming without content logs."""
    if function is None:
        return lambda wrapped: budgeted_inference(wrapped, step=step)
    signature = inspect.signature(function)

    def is_stream(owner, args, kwargs):
        if "stream" in kwargs:
            return kwargs["stream"]
        return signature.bind_partial(owner, *args, **kwargs).arguments.get("stream", False)

    def metadata(owner):
        config = getattr(owner, "config", None)
        provider = (
            getattr(owner, "mapit_provider", None)
            or getattr(owner, "provider", None)
            or getattr(config, "name", None)
        )
        model = getattr(owner, "model_name", None) or getattr(config, "model", None)
        return provider, model, step or getattr(owner, "step", None)

    if inspect.isasyncgenfunction(function):

        @wraps(function)
        async def async_generator_wrapped(owner, *args, **kwargs):
            if _budget.get() is None:
                async for chunk in function(owner, *args, **kwargs):
                    yield chunk
                return
            provider, model, selected_step = metadata(owner)
            with inference_request(provider, model, selected_step) as attempt:
                stream = function(owner, *args, **kwargs)
                try:
                    async for chunk in stream:
                        attempt.record(chunk)
                        with _suspend_attempt():
                            yield chunk
                finally:
                    await stream.aclose()

        return async_generator_wrapped

    if inspect.iscoroutinefunction(function):

        @wraps(function)
        async def async_wrapped(owner, *args, **kwargs):
            if _budget.get() is None:
                return await function(owner, *args, **kwargs)
            provider, model, selected_step = metadata(owner)
            if is_stream(owner, args, kwargs):

                async def chunks():
                    with inference_request(provider, model, selected_step) as attempt:
                        result = await function(owner, *args, **kwargs)
                        async for chunk in result:
                            attempt.record(chunk)
                            with _suspend_attempt():
                                yield chunk

                return chunks()
            with inference_request(provider, model, selected_step) as attempt:
                response = await function(owner, *args, **kwargs)
                attempt.record(response)
                return response

        return async_wrapped

    @wraps(function)
    def sync_wrapped(owner, *args, **kwargs):
        if _budget.get() is None:
            return function(owner, *args, **kwargs)
        provider, model, selected_step = metadata(owner)
        if is_stream(owner, args, kwargs):

            def chunks():
                with inference_request(provider, model, selected_step) as attempt:
                    for chunk in function(owner, *args, **kwargs):
                        attempt.record(chunk)
                        with _suspend_attempt():
                            yield chunk

            return chunks()
        with inference_request(provider, model, selected_step) as attempt:
            response = function(owner, *args, **kwargs)
            attempt.record(response)
            return response

    return sync_wrapped
