from collections.abc import AsyncIterator

import psycopg
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from core.config import Config
from core.drivers.db.base import Base
from core.drivers.db.models import OutboxModel, PaymentModel  # noqa: F401

TEST_DB = 'paymaster_test'


@pytest.fixture(scope='session')
def test_dsn() -> str:
    url = make_url(Config().postgres_dsn)
    admin = f'host={url.host} port={url.port} user={url.username} password={url.password} dbname={url.database}'
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)')
        conn.execute(f'CREATE DATABASE {TEST_DB}')
    return url.set(database=TEST_DB).render_as_string(hide_password=False)


@pytest.fixture(scope='session')
async def engine(test_dsn: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(test_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as conn:
        trans = await conn.begin()
        yield conn
        await trans.rollback()


@pytest.fixture
async def db_session(db_conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(db_conn, join_transaction_mode='create_savepoint', expire_on_commit=False) as session:
        yield session
