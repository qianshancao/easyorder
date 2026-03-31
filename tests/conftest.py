"""Shared test fixtures for all test layers."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test database URL before importing app modules,
# so app.database creates an in-memory engine instead of touching the filesystem.
os.environ.setdefault("EASYORDER_DATABASE_URL", "sqlite:///:memory:")

import app.models  # pyright: ignore[reportUnusedImport] — 注册所有模型到 Base.metadata
from app.database import get_db
from app.main import app
from app.models.admin import Admin
from app.models.base import Base
from app.models.oauth_client import OAuthClient
from app.repositories.admin import AdminRepository
from app.repositories.oauth_client import OAuthClientRepository
from app.repositories.order import OrderRepository
from app.repositories.payment_attempt import PaymentAttemptRepository
from app.repositories.plan import PlanRepository
from app.repositories.refund import RefundRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.system_config import SystemConfigRepository
from app.services.auth import AuthService


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Session-scoped in-memory SQLite engine.

    StaticPool ensures all connections share the same underlying sqlite3 connection,
    which is essential for :memory: databases.
    """
    engine_instance = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign key constraints for SQLite
    from sqlalchemy import event

    @event.listens_for(engine_instance, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine_instance


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


# ── Repository fixtures (real SQLite) ──


@pytest.fixture()
def plan_repository(db_session: Session) -> PlanRepository:
    """PlanRepository backed by the test database."""
    return PlanRepository(db_session)


@pytest.fixture()
def admin_repository(db_session: Session) -> AdminRepository:
    """AdminRepository backed by the test database."""
    return AdminRepository(db_session)


@pytest.fixture()
def oauth_client_repository(db_session: Session) -> OAuthClientRepository:
    """OAuthClientRepository backed by the test database."""
    return OAuthClientRepository(db_session)


@pytest.fixture()
def system_config_repository(db_session: Session) -> SystemConfigRepository:
    """SystemConfigRepository backed by the test database."""
    return SystemConfigRepository(db_session)


@pytest.fixture()
def subscription_repository(db_session: Session) -> SubscriptionRepository:
    """SubscriptionRepository backed by the test database."""
    return SubscriptionRepository(db_session)


@pytest.fixture()
def order_repository(db_session: Session) -> OrderRepository:
    """OrderRepository backed by the test database."""
    return OrderRepository(db_session)


@pytest.fixture()
def payment_attempt_repository(db_session: Session) -> PaymentAttemptRepository:
    """PaymentAttemptRepository backed by the test database."""
    return PaymentAttemptRepository(db_session)


@pytest.fixture()
def refund_repository(db_session: Session) -> RefundRepository:
    """RefundRepository backed by the test database."""
    return RefundRepository(db_session)


# ── Mock repository fixtures (service layer) ──


@pytest.fixture()
def mock_plan_repository() -> MagicMock:
    """Mocked PlanRepository for service layer tests."""
    return MagicMock(spec=PlanRepository)


@pytest.fixture()
def mock_admin_repository() -> MagicMock:
    """Mocked AdminRepository for service layer tests."""
    return MagicMock(spec=AdminRepository)


@pytest.fixture()
def mock_oauth_client_repository() -> MagicMock:
    """Mocked OAuthClientRepository for service layer tests."""
    return MagicMock(spec=OAuthClientRepository)


@pytest.fixture()
def mock_system_config_repository() -> MagicMock:
    """Mocked SystemConfigRepository for service layer tests."""
    return MagicMock(spec=SystemConfigRepository)


@pytest.fixture()
def mock_subscription_repository() -> MagicMock:
    """Mocked SubscriptionRepository for service layer tests."""
    return MagicMock(spec=SubscriptionRepository)


@pytest.fixture()
def mock_order_repository() -> MagicMock:
    """Mocked OrderRepository for service layer tests."""
    return MagicMock(spec=OrderRepository)


@pytest.fixture()
def mock_payment_attempt_repository() -> MagicMock:
    """Mocked PaymentAttemptRepository for service layer tests."""
    return MagicMock(spec=PaymentAttemptRepository)


@pytest.fixture()
def mock_refund_repository() -> MagicMock:
    """Mocked RefundRepository for service layer tests."""
    return MagicMock(spec=RefundRepository)


# ── Auth token header fixtures (API layer) ──


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@pytest.fixture()
def super_admin_token_headers(db_session: Session) -> dict[str, str]:
    """Super admin JWT auth headers for API tests."""
    admin = Admin(
        username="test_super_admin",
        password_hash=_hash_password("testpass123"),
        role="super_admin",
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    auth_service = AuthService(AdminRepository(db_session), OAuthClientRepository(db_session))
    token = auth_service.create_admin_token(admin)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_token_headers(db_session: Session) -> dict[str, str]:
    """Regular admin JWT auth headers for API tests."""
    admin = Admin(
        username="test_admin",
        password_hash=_hash_password("testpass123"),
        role="admin",
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    auth_service = AuthService(AdminRepository(db_session), OAuthClientRepository(db_session))
    token = auth_service.create_admin_token(admin)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def api_client_token_headers(db_session: Session) -> dict[str, str]:
    """OAuth API client JWT auth headers for API tests."""
    raw_secret = "test_client_secret"
    client = OAuthClient(
        client_id="test_api_client_id",
        client_secret=_hash_password(raw_secret),
        name="Test API Client",
        status="active",
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)

    auth_service = AuthService(AdminRepository(db_session), OAuthClientRepository(db_session))
    token, _ = auth_service.create_api_token(client)
    return {"Authorization": f"Bearer {token}"}


# ── TestClient fixture ──


@pytest.fixture()
def client(db_session: Session, engine: Engine) -> Generator[TestClient, None, None]:
    """TestClient with get_db overridden to use the test database.

    Patches both FastAPI dependency_overrides and the get_db reference
    in app.api.deps so that direct next(get_db()) calls in auth guards
    also use the test session.
    """
    import app.api.deps as _deps_module

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    original_deps_get_db = _deps_module.get_db
    _deps_module.get_db = _override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()
    _deps_module.get_db = original_deps_get_db
