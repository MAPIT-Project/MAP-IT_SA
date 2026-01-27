"""
Streaming Response Optimizer

Optimizes Server-Sent Events (SSE) streaming by:
- Batching small token updates to reduce overhead
- Immediately flushing important events
- Managing stream lifecycle and cleanup

Key Features:
- Configurable flush interval and buffer size
- Priority-based event handling
- Memory-efficient buffering
- Async-friendly design
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority levels for SSE events."""
    IMMEDIATE = "immediate"  # Flush immediately (errors, complete, tool_result)
    HIGH = "high"           # Flush soon (status, tool_call, agent_thinking)
    NORMAL = "normal"       # Buffer if possible (tokens)


# Event type to priority mapping
EVENT_PRIORITIES: dict[str, EventPriority] = {
    # Immediate flush events
    "error": EventPriority.IMMEDIATE,
    "complete": EventPriority.IMMEDIATE,
    "tool_result": EventPriority.IMMEDIATE,

    # High priority events
    "status": EventPriority.HIGH,
    "progress": EventPriority.HIGH,
    "tool_call": EventPriority.HIGH,
    "agent_thinking": EventPriority.HIGH,
    "conversation_name": EventPriority.HIGH,

    # Normal priority (can be buffered)
    "token": EventPriority.NORMAL,
}


@dataclass
class StreamBuffer:
    """
    Buffer for batching streaming updates.

    Accumulates small events and flushes them based on:
    - Buffer size threshold
    - Time interval threshold
    - Event priority
    """
    max_buffer_size: int = 10          # Max events to buffer
    flush_interval_ms: float = 100.0   # Flush interval in milliseconds
    max_token_batch: int = 5           # Max tokens to batch together

    # Internal state
    buffer: list[dict[str, Any]] = field(default_factory=list)
    token_buffer: list[str] = field(default_factory=list)
    last_flush_time: float = field(default_factory=time.time)

    def reset(self):
        """Reset buffer state."""
        self.buffer.clear()
        self.token_buffer.clear()
        self.last_flush_time = time.time()

    def _should_flush(self) -> bool:
        """Check if buffer should be flushed based on size or time."""
        if len(self.buffer) >= self.max_buffer_size:
            return True

        elapsed_ms = (time.time() - self.last_flush_time) * 1000
        if elapsed_ms >= self.flush_interval_ms and self.buffer:
            return True

        return False

    def _get_priority(self, event: dict[str, Any]) -> EventPriority:
        """Get priority for an event."""
        event_type = event.get("type", "")
        return EVENT_PRIORITIES.get(event_type, EventPriority.NORMAL)

    def add(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Add event to buffer, return events to flush.

        Args:
            event: SSE event dict

        Returns:
            List of events to send (may be empty)
        """
        priority = self._get_priority(event)
        event_type = event.get("type", "")

        # Immediate priority - flush buffer first, then return this event
        if priority == EventPriority.IMMEDIATE:
            events_to_flush = self.flush()
            events_to_flush.append(event)
            return events_to_flush

        # Token events - batch them together
        if event_type == "token":
            content = event.get("content", "")
            self.token_buffer.append(content)

            # Batch tokens if we have enough
            if len(self.token_buffer) >= self.max_token_batch:
                batched_content = "".join(self.token_buffer)
                self.token_buffer.clear()
                batched_event = {"type": "token", "content": batched_content}
                self.buffer.append(batched_event)
        else:
            # Non-token events
            self.buffer.append(event)

        # Check if we should flush
        if self._should_flush() or priority == EventPriority.HIGH:
            return self.flush()

        return []

    def flush(self) -> list[dict[str, Any]]:
        """
        Flush all buffered events.

        Returns:
            List of all buffered events
        """
        events = list(self.buffer)

        # Add any remaining tokens
        if self.token_buffer:
            batched_content = "".join(self.token_buffer)
            events.append({"type": "token", "content": batched_content})
            self.token_buffer.clear()

        self.buffer.clear()
        self.last_flush_time = time.time()

        return events

    def has_pending(self) -> bool:
        """Check if there are pending events to flush."""
        return bool(self.buffer) or bool(self.token_buffer)


class StreamingOptimizer:
    """
    Optimizer for SSE streaming responses.

    Wraps an async event generator to provide optimized streaming
    with buffering and batching.
    """

    def __init__(
        self,
        max_buffer_size: int = 10,
        flush_interval_ms: float = 100.0,
        max_token_batch: int = 5
    ):
        """
        Initialize streaming optimizer.

        Args:
            max_buffer_size: Maximum events to buffer
            flush_interval_ms: Time threshold for flushing
            max_token_batch: Maximum tokens to batch together
        """
        self.buffer = StreamBuffer(
            max_buffer_size=max_buffer_size,
            flush_interval_ms=flush_interval_ms,
            max_token_batch=max_token_batch
        )

    async def optimize_stream(
        self,
        event_source: AsyncIterator[dict[str, Any]]
    ) -> AsyncIterator[str]:
        """
        Optimize an event stream for SSE delivery.

        Args:
            event_source: Async iterator yielding event dicts

        Yields:
            Formatted SSE strings
        """
        try:
            async for event in event_source:
                events_to_send = self.buffer.add(event)

                for evt in events_to_send:
                    yield self._format_sse(evt)

            # Flush any remaining events at end of stream
            final_events = self.buffer.flush()
            for evt in final_events:
                yield self._format_sse(evt)

        except Exception as e:
            logger.error(f"Error in optimized stream: {e}")
            # Send error event
            error_event = {"type": "error", "error": str(e)}
            yield self._format_sse(error_event)

        finally:
            self.buffer.reset()

    def _format_sse(self, event: dict[str, Any]) -> str:
        """Format event as SSE string."""
        return f"data: {json.dumps(event)}\n\n"


def create_optimized_stream_response(
    event_source: AsyncIterator[dict[str, Any]],
    max_buffer_size: int = 10,
    flush_interval_ms: float = 100.0,
    max_token_batch: int = 5
) -> AsyncIterator[str]:
    """
    Create an optimized streaming response from an event source.

    Convenience function for creating optimized streams.

    Args:
        event_source: Async iterator yielding event dicts
        max_buffer_size: Maximum events to buffer
        flush_interval_ms: Time threshold for flushing
        max_token_batch: Maximum tokens to batch together

    Returns:
        Optimized async iterator of SSE strings
    """
    optimizer = StreamingOptimizer(
        max_buffer_size=max_buffer_size,
        flush_interval_ms=flush_interval_ms,
        max_token_batch=max_token_batch
    )
    return optimizer.optimize_stream(event_source)


async def wrap_dict_result_as_stream(
    result: dict[str, Any]
) -> AsyncIterator[dict[str, Any]]:
    """
    Wrap a dict result as a single-event async stream.

    Useful for error cases where we have a dict instead of a generator.

    Args:
        result: Dict result to wrap

    Yields:
        Single event from the dict
    """
    if "error" in result:
        yield {"type": "error", "error": result.get("error", "Unknown error")}
    else:
        yield {"type": "complete", "data": result}


class StreamingMetrics:
    """Track streaming performance metrics."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics."""
        self.events_sent = 0
        self.bytes_sent = 0
        self.batches_sent = 0
        self.tokens_batched = 0
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self):
        """Start tracking."""
        self.start_time = time.time()

    def record_event(self, event_data: str):
        """Record a sent event."""
        self.events_sent += 1
        self.bytes_sent += len(event_data.encode('utf-8'))

    def record_batch(self, batch_size: int):
        """Record a batch of events."""
        self.batches_sent += 1
        self.tokens_batched += batch_size

    def stop(self):
        """Stop tracking."""
        self.end_time = time.time()

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        duration = 0.0
        if self.start_time:
            end = self.end_time or time.time()
            duration = end - self.start_time

        return {
            "events_sent": self.events_sent,
            "bytes_sent": self.bytes_sent,
            "batches_sent": self.batches_sent,
            "tokens_batched": self.tokens_batched,
            "duration_seconds": round(duration, 3),
            "events_per_second": round(self.events_sent / duration, 2) if duration > 0 else 0,
            "bytes_per_second": round(self.bytes_sent / duration, 2) if duration > 0 else 0,
        }


class InstrumentedStreamingOptimizer(StreamingOptimizer):
    """Streaming optimizer with performance instrumentation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = StreamingMetrics()

    async def optimize_stream(
        self,
        event_source: AsyncIterator[dict[str, Any]]
    ) -> AsyncIterator[str]:
        """Optimize stream with metrics tracking."""
        self.metrics.reset()
        self.metrics.start()

        try:
            async for sse_string in super().optimize_stream(event_source):
                self.metrics.record_event(sse_string)
                yield sse_string

        finally:
            self.metrics.stop()
            logger.debug(f"Stream metrics: {self.metrics.get_stats()}")

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        return self.metrics.get_stats()
