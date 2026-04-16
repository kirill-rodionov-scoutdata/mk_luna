"""
Shared FastAPI dependencies.

- verify_api_key: validates the X-API-Key header on every request.
"""

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """
    Dependency that enforces static API key authentication.

    Raise 401 if the key is missing or incorrect.
    Add to any router with:
        router = APIRouter(dependencies=[Depends(verify_api_key)])
    """
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
