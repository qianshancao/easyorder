"""Tests for Order API endpoints using TestClient with a test database."""

from fastapi.testclient import TestClient


def _create_plan(client: TestClient, headers: dict[str, str], **overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/plans/", json=defaults, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _create_subscription(client: TestClient, plan_id: int, api_headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        "/api/v1/subscriptions/",
        json={"external_user_id": "user_001", "plan_id": plan_id},
        headers=api_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_one_time_order(client: TestClient, api_headers: dict[str, str], **overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "external_user_id": "user_001",
        "type": "one_time",
        "amount": 3000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/orders/", json=defaults, headers=api_headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateOrder:
    def test_create_one_time(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        data = _create_one_time_order(client, api_client_token_headers)

        assert data["type"] == "one_time"
        assert data["status"] == "pending"
        assert data["amount"] == 3000
        assert data["currency"] == "CNY"
        assert data["subscription_id"] is None

    def test_create_rejects_non_one_time(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/orders/",
            json={"external_user_id": "user_001", "subscription_id": 1, "type": "opening", "amount": 3000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/orders/",
            json={"external_user_id": "user_001", "type": "one_time", "amount": 3000},
        )
        assert resp.status_code == 401


class TestGetOrder:
    def test_get_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_one_time_order(client, api_client_token_headers)

        resp = client.get(f"/api/v1/orders/{order['id']}", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == order["id"]

    def test_get_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/orders/99999", headers=api_client_token_headers)
        assert resp.status_code == 404


class TestListByUser:
    def test_returns_orders(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        _create_one_time_order(client, api_client_token_headers)

        resp = client.get("/api/v1/orders/by-user/user_001", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_empty(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/orders/by-user/nobody", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestListBySubscription:
    def test_returns_orders(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        sub = _create_subscription(client, plan["id"], api_client_token_headers)

        resp = client.get(f"/api/v1/orders/by-subscription/{sub['id']}", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestMarkAsPaid:
    def test_pay_success(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_one_time_order(client, api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        assert resp.json()["paid_at"] is not None

    def test_pay_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_one_time_order(client, api_client_token_headers)

        # Pay twice
        client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)
        resp = client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        first_paid_at = resp.json()["paid_at"]

        # second pay should return same paid_at
        resp = client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        assert resp.json()["paid_at"] == first_paid_at

    def test_pay_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/orders/99999/pay", headers=api_client_token_headers)
        assert resp.status_code == 404


class TestCancelOrder:
    def test_cancel_success(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_one_time_order(client, api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/orders/99999/cancel", headers=api_client_token_headers)
        assert resp.status_code == 404

    def test_cancel_paid_order_fails(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_one_time_order(client, api_client_token_headers)
        client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=api_client_token_headers)
        assert resp.status_code == 422

    def test_cancel_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_one_time_order(client, api_client_token_headers)
        client.post(f"/api/v1/orders/{order['id']}/cancel", headers=api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"


class TestAdminListAll:
    def test_list_all(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        _create_one_time_order(client, api_client_token_headers)

        resp = client.get("/api/v1/orders/admin/all", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_with_status_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_one_time_order(client, api_client_token_headers)
        client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)

        resp = client.get("/api/v1/orders/admin/all?status=paid", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_with_type_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        _create_one_time_order(client, api_client_token_headers)

        resp = client.get("/api/v1/orders/admin/all?type=one_time", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["type"] == "one_time"

    def test_list_with_external_user_id_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        _create_one_time_order(client, api_client_token_headers, external_user_id="user_filter")

        resp = client.get("/api/v1/orders/admin/all?external_user_id=user_filter", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["external_user_id"] == "user_filter"

    def test_requires_admin_auth(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/v1/orders/admin/all", headers=api_client_token_headers)
        assert resp.status_code == 401


class TestAdminListAllFilters:
    """Additional filter tests for GET /api/v1/orders/admin/all."""

    def test_list_with_subscription_id_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        sub = _create_subscription(client, plan["id"], api_client_token_headers)

        resp = client.get(
            f"/api/v1/orders/admin/all?subscription_id={sub['id']}",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_found(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_one_time_order(client, api_client_token_headers)

        resp = client.get(f"/api/v1/orders/admin/{order['id']}", headers=admin_token_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == order["id"]

    def test_get_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/orders/admin/99999", headers=admin_token_headers)
        assert resp.status_code == 404


class TestAdminCancelOrder:
    def test_cancel_success(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_one_time_order(client, api_client_token_headers)

        resp = client.post(f"/api/v1/orders/admin/{order['id']}/cancel", headers=admin_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/orders/admin/99999/cancel", headers=admin_token_headers)
        assert resp.status_code == 404
