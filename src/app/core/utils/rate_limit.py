from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logger import logging
from ...schemas.rate_limit import sanitize_path

logger = logging.getLogger(__name__)


class RateLimiter:
    _instance: Optional["RateLimiter"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, redis_url: str) -> None:
        instance = cls()
        # No-op since Redis is removed

    async def is_rate_limited(self, db: AsyncSession, user_id: int, path: str, limit: int, period: int) -> bool:
        # Always return False since rate limiting is disabled without Redis
        return False

rate_limiter = RateLimiter()
