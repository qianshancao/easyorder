"""Shared API test helpers."""

from fastapi.testclient import TestClient


def _build_plan_payload(**overrides: object) -> dict[str, object]:
    """Helper to create a plan creation payload with sensible defaults."""
    defaults: dict[str, object] = {
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
    }
    defaults.update(overrides)
    return defaults


def _create_plan(client: TestClient, headers: dict[str, str], **overrides: object) -> dict[str, object]:
    """Helper to create a plan with auth and return its JSON data."""
    resp = client.post("/api/v1/plans/", json=_build_plan_payload(**overrides), headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _create_subscription(client: TestClient, plan_id: int, api_headers: dict[str, str]) -> dict[str, object]:
    """Helper to create a subscription and return its JSON data."""
    resp = client.post(
        "/api/v1/subscriptions/",
        json={"external_user_id": "user_001", "plan_id": plan_id},
        headers=api_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_order(client: TestClient, api_headers: dict[str, str], **overrides: object) -> dict[str, object]:
    """Helper to create a one-time order and return its JSON data."""
    defaults: dict[str, object] = {
        "external_user_id": "user_001",
        "type": "one_time",
        "amount": 3000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/orders/", json=defaults, headers=api_headers)
    assert resp.status_code == 201
    return resp.json()
