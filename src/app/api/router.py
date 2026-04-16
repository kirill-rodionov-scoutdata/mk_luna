"""
Top-level API router.

Aggregates all versioned routers and mounts them under /api/v1 (prefix set in main.py).
"""

from fastapi import APIRouter

from app.api.v1.payments import router as payments_router

api_router = APIRouter()
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
