from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from app.ai.providers import AIError
from app.api.v1 import api_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="FleetMind API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],  # lets the browser read the export file name
)
app.include_router(api_router)


@app.exception_handler(AIError)
async def ai_error_handler(_: Request, exc: AIError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
