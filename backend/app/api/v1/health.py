from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "environment": s.environment,
        "ai_provider": s.ai_provider,
        "ai_model": s.groq_model,
        "ai_configured": bool(s.groq_api_key),  # never return the key itself
    }
