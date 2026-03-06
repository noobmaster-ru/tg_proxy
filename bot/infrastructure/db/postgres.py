from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from bot.infrastructure.db.schema import SCHEMA_SQL


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return dsn


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    for raw_statement in sql_text.split(";"):
        statement = raw_statement.strip()
        if statement:
            statements.append(statement)
    return statements


class PostgresDatabase:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._engine: AsyncEngine | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Database engine is not initialized")
        return self._engine

    async def connect(self) -> None:
        self._engine = create_async_engine(
            _normalize_dsn(self._dsn),
            pool_pre_ping=True,
        )

        async with self.engine.begin() as connection:
            for statement in _split_sql_statements(SCHEMA_SQL):
                await connection.execute(text(statement))

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
