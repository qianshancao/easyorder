"""Tests for Plan API endpoints using TestClient with a test database."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError


def _build_plan_payload(**overrides: object) -> dict[str, object]:
    """Helper to create a plan creation payload with sensible defaults."""
    defaults: dict[str, object] = {
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
    }
    defaults.update(overrides)
    return defaults


class TestCreatePlan:
    """Tests for POST /api/v1/plans/."""

    def test_create_plan_success(self, client: TestClient) -> None:
        response = client.post("/api/v1/plans/", json=_build_plan_payload())

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Basic Plan"
        assert data["cycle"] == "monthly"
        assert data["base_price"] == 3000
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data

    def test_create_plan_with_all_fields(self, client: TestClient) -> None:
        payload = _build_plan_payload(
            introductory_price=1000,
            trial_price=0,
            trial_duration=7,
            features={"projects": 5, "storage": "10GB"},
            renewal_rules={"grace_period_days": 3},
        )
        response = client.post("/api/v1/plans/", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["introductory_price"] == 1000
        assert data["trial_price"] == 0
        assert data["trial_duration"] == 7
        assert data["features"] == {"projects": 5, "storage": "10GB"}
        assert data["renewal_rules"] == {"grace_period_days": 3}

    def test_create_plan_missing_required_field(self, client: TestClient) -> None:
        response = client.post("/api/v1/plans/", json={"name": "Incomplete"})

        assert response.status_code == 422


class TestListPlans:
    """Tests for GET /api/v1/plans/."""

    def test_list_plans_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/plans/")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_plans_with_data(self, client: TestClient) -> None:
        client.post("/api/v1/plans/", json=_build_plan_payload(name="Plan A"))
        client.post("/api/v1/plans/", json=_build_plan_payload(name="Plan B"))

        response = client.get("/api/v1/plans/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Plan A"
        assert data[1]["name"] == "Plan B"


class TestGetPlan:
    """Tests for GET /api/v1/plans/{plan_id}."""

    def test_get_plan_found(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/plans/", json=_build_plan_payload())
        plan_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/plans/{plan_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == plan_id
        assert data["name"] == "Basic Plan"

    def test_get_plan_not_found(self, client: TestClient) -> None:
        # Endpoint does not handle None — raises ValidationError.
        # Should be updated to return 404 once error handling is added.
        with pytest.raises(ValidationError):
            client.get("/api/v1/plans/99999")
