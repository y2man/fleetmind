from fastapi import APIRouter

from app.api.v1 import ai, analytics, auth, dashboard, documents, fleet, health, integrations, notifications, org, routes, search, tracking

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(ai.router)
api_router.include_router(auth.router)
api_router.include_router(org.router)
api_router.include_router(fleet.router)
api_router.include_router(documents.router)
api_router.include_router(integrations.router)
api_router.include_router(dashboard.router)
api_router.include_router(routes.router)
api_router.include_router(tracking.router)
api_router.include_router(analytics.router)
api_router.include_router(notifications.router)
api_router.include_router(search.router)
