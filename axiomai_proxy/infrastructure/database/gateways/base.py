from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine


class BaseGateway:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
