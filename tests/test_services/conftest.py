"""Shared mock helpers for service tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.models.admin import Admin
from app.models.order import Order
from app.models.refund import Refund
from app.models.subscription import Subscription
from app.services.admin import _hash_password


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
