"""Shared test fixtures for all test layers."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test database URL before importing app modules,
# so app.database creates an in-memory engine instead of touching the filesystem.
os.environ.setdefault("EASYORDER_DATABASE_URL", "sqlite:///:memory:")

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.plan import Plan  # noqa: F401 # pyright: ignore[reportUnusedImport]
from app.repositories.plan import PlanRepository


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Session-scoped in-memory SQLite engine.

    StaticPool ensures all connections share the same underlying sqlite3 connection,
    which is essential for :memory: databases.
    """
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(autouse=True)
def _setup_tables(engine: Engine) -> Generator[None, None, None]:  # pyright: ignore[reportUnusedFunction]
    """Create all tables before each test and drop them after.

    Provides full isolation: every test starts with a clean schema.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped database session for repository tests."""
    test_session_factory = sessionmaker(bind=engine)
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def plan_repository(db_session: Session) -> PlanRepository:
    """PlanRepository backed by the test database."""
    return PlanRepository(db_session)


@pytest.fixture()
def mock_plan_repository() -> MagicMock:
    """Mocked PlanRepository for service layer tests."""
    return MagicMock(spec=PlanRepository)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with get_db overridden to use the test database."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
