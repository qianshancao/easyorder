"""Shared mock helpers for service tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.models.admin import Admin
from app.models.oauth_client import OAuthClient
from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.models.payment_transaction import PaymentTransaction
from app.models.plan import Plan
from app.models.refund import Refund
from app.models.subscription import Subscription
from app.models.system_config import SystemConfig
from app.services.admin import _hash_password
from app.services.oauth_client import _hash_secret


def _make_admin_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "username": "testadmin",
        "password_hash": _hash_password("password123"),
        "role": "admin",
        "status": "active",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Admin)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_order_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "external_user_id": "user_001",
        "subscription_id": None,
        "type": "one_time",
        "amount": 3000,
        "currency": "CNY",
        "status": "pending",
        "paid_at": None,
        "canceled_at": None,
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Order)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_subscription_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "external_user_id": "user_001",
        "plan_id": 1,
        "plan_snapshot": {"name": "Basic Plan", "cycle": "monthly", "base_price": 3000},
        "status": "trial",
        "current_period_start": datetime.now(tz=UTC),
        "current_period_end": datetime.now(tz=UTC) + timedelta(days=7),
        "canceled_at": None,
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Subscription)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_plan_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
        "introductory_price": None,
        "trial_price": None,
        "trial_duration": None,
        "features": {"projects": 20},
        "renewal_rules": None,
        "status": "active",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Plan)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_refund_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "order_id": 1,
        "amount": 3000,
        "reason": "用户申请退款",
        "status": "pending",
        "channel": "alipay",
        "channel_refund_id": None,
        "completed_at": None,
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Refund)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_oauth_client_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "client_id": "test_client_id",
        "client_secret": _hash_secret("test_secret"),
        "name": "Test Client",
        "status": "active",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=OAuthClient)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_config_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "key": "site.name",
        "value": {"title": "EasyOrder"},
        "description": "Site title",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=SystemConfig)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_attempt_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "order_id": 1,
        "channel": "alipay",
        "amount": 3000,
        "status": "pending",
        "channel_transaction_id": None,
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    mock = MagicMock(spec=PaymentAttempt)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_payment_transaction_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "payment_attempt_id": 1,
        "order_id": 1,
        "channel": "alipay",
        "amount": 3000,
        "currency": "CNY",
        "channel_transaction_id": "txn_001",
        "raw_callback_data": None,
        "status": "confirmed",
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    mock = MagicMock(spec=PaymentTransaction)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


@pytest.fixture()
def subscription_service(mock_subscription_repository, mock_plan_repository, mock_order_repository):
    """SubscriptionService wired to mock repositories + fresh ProrationService."""
    from app.services.proration import ProrationService
    from app.services.subscription import SubscriptionService

    return SubscriptionService(
        mock_subscription_repository,
        mock_plan_repository,
        ProrationService(),
        mock_order_repository,
    )
