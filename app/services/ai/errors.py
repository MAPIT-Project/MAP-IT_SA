"""Content-free diagnostics for generation failures; never return SDK payloads."""


def generation_error_message(error: Exception, provider: str | None = None) -> str:
    """Recognize common SDK status codes without exposing prompts or credentials."""
    label = {
        "gemini": "Gemini",
        "openai": "OpenAI",
        "openrouter": "OpenRouter",
        "codex": "Codex",
        "antigravity": "Antigravity",
    }.get(provider, "AI provider")
    code = getattr(error, "status_code", None) or getattr(error, "code", None)
    if callable(code):
        code = code()
    code = getattr(code, "value", code)
    # Some Google SDK errors expose the reason only inside their error message.
    # Inspect it locally; never include the raw message in logs or API responses.
    detail = str(error).upper()
    if code in (401, 403) or any(
        reason in detail
        for reason in (
            "API_KEY_INVALID",
            "API_KEY_EXPIRED",
            "API KEY NOT VALID",
            "API KEY EXPIRED",
            "UNAUTHENTICATED",
            "PERMISSION_DENIED",
        )
    ):
        return f"{label} generation authentication failed. Check the selected provider's credentials and permissions."
    if code == 429 or "RESOURCE_EXHAUSTED" in detail:
        return (
            f"{label} generation quota or rate limit reached. Check the selected provider's quota."
        )
    if isinstance(error, TimeoutError):
        return f"{label} generation timed out."
    return f"{type(error).__name__}: agent execution failed"
