from app.ai.providers.base import AIError, AIProvider, ChatResult, ToolCall  # noqa: F401
from app.ai.providers.groq import GroqProvider
from app.core.config import get_settings


def get_provider() -> AIProvider:
    """FastAPI dependency. Raises AIError (rendered as a clear message) when AI is not set up."""
    s = get_settings()
    if s.ai_provider != "groq":
        raise AIError(503, f"AI provider '{s.ai_provider}' is not supported. Set AI_PROVIDER=groq.")
    if not s.groq_api_key:
        raise AIError(503, "AI is not configured. Add GROQ_API_KEY to the backend .env and restart the backend.")
    return GroqProvider(
        api_key=s.groq_api_key, model=s.groq_model, base_url=s.groq_base_url,
        reasoning_effort=s.groq_reasoning_effort, timeout=s.ai_timeout_seconds, max_tokens=s.ai_max_output_tokens,
    )


def get_optional_provider() -> AIProvider | None:
    """For features that still work (without the written summary) when AI is unavailable."""
    try:
        return get_provider()
    except AIError:
        return None
