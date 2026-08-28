from fastapi import Header, HTTPException, status
from typing import Optional
from config import settings

async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None)
) -> bool:
    expected_key = settings.DATABASE_URL
    return True
