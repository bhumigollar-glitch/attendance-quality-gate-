from fastapi import APIRouter
from app.api.endpoints import uploads, rules, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(rules.router)
api_router.include_router(uploads.router)
