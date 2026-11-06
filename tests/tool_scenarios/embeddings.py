"""Explicit, separately bounded embedding access for the read-only evaluator."""

from threading import Lock

import numpy as np

from .oracles import OraclePrerequisiteError


class EmbeddingLimitExceeded(OraclePrerequisiteError):
    pass


class EmbeddingAllowance:
    def __init__(self, max_requests=0):
        if (
            not isinstance(max_requests, int)
            or isinstance(max_requests, bool)
            or not 0 <= max_requests <= 100
        ):
            raise ValueError("Embedding request limit must be between 0 and 100")
        self.max_requests = max_requests
        self.attempted = 0
        self.failed = 0
        self.cache_hits = 0
        self.stopped = False
        self.endpoint_failed = False
        self.cache = {}
        self.lock = Lock()

    def raise_if_stopped(self):
        if self.stopped:
            raise EmbeddingLimitExceeded(
                "Embedding request limit reached; no further request attempted"
            )

    def query(self, owner, text, generate, sdk_call):
        key = (owner.model_name, owner.embedding_dimension, text)
        with self.lock:
            self.raise_if_stopped()
            if self.endpoint_failed:
                raise OraclePrerequisiteError(
                    "Embedding endpoint previously failed; no automatic retry attempted"
                )
            if key in self.cache:
                self.cache_hits += 1
                return self.cache[key].copy()
            if self.attempted >= self.max_requests:
                self.stopped = True
                self.raise_if_stopped()
            error_type = None

            def bounded_call(**kwargs):
                nonlocal error_type
                if self.attempted >= self.max_requests:
                    self.stopped = True
                    self.raise_if_stopped()
                self.attempted += 1
                try:
                    return sdk_call(**kwargs, request_options={"timeout": 20, "retry": None})
                except Exception as exc:
                    error_type = type(exc).__name__
                    raise OraclePrerequisiteError(
                        f"Embedding endpoint failed ({error_type})"
                    ) from None

            from unittest.mock import patch

            with patch("google.generativeai.embed_content", bounded_call):
                result = generate(owner, text)
            if result.shape != (3072,) or not np.isfinite(result).all() or not np.any(result != 0):
                self.failed += 1
                self.endpoint_failed = True
                raise OraclePrerequisiteError(
                    f"Embedding request produced no valid vector ({error_type or 'invalid_output'})"
                )
            self.cache[key] = result.copy()
            return result

    def snapshot(self):
        return {
            "max_requests": self.max_requests,
            "attempted": self.attempted,
            "failed": self.failed,
            "cache_hits": self.cache_hits,
            "stopped": self.stopped,
            "endpoint_failed": self.endpoint_failed,
            "usage_tokens": None,
            "cache_scope": "evaluation process only",
        }
