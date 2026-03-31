"""Tests for PaymentAttempt API endpoints using TestClient with a test database."""

from fastapi.testclient import TestClient


def _create_order(
    client: TestClient, api_headers: dict[str, str], **overrides: object
) -> dict[str, object]:
    defaults: dict[str, object] = {
        "external_user_id": "user_001",
        "type": "one_time",
        "amount": 3000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/orders/", json=defaults, headers=api_headers)
    assert resp.status_code == 201
    return resp.json()


def _create_attempt(
    client: TestClient,
    api_headers: dict[str, str],
    order_id: int,
    **overrides: object,
) -> dict[str, object]:
    defaults: dict[str, object] = {
        "order_id": order_id,
        "channel": "alipay",
        "amount": 3000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/payment-attempts/", json=defaults, headers=api_headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateAttempt:
    def test_create_success(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        data = _create_attempt(client, api_client_token_headers, order["id"])

        assert data["order_id"] == order["id"]
        assert data["channel"] == "alipay"
        assert data["amount"] == 3000
        assert data["status"] == "pending"
        assert data["channel_transaction_id"] is None

    def test_create_order_not_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/payment-attempts/",
            json={"order_id": 99999, "channel": "alipay", "amount": 3000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_idempotent(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        first = _create_attempt(client, api_client_token_headers, order["id"])

        # Create again, should return same attempt
        resp = client.post(
            "/api/v1/payment-attempts/",
            json={"order_id": order["id"], "channel": "alipay", "amount": 3000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == first["id"]

    def test_create_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/payment-attempts/",
            json={"order_id": 1, "channel": "alipay", "amount": 3000},
        )
        assert resp.status_code == 401

    def test_create_rejects_invalid_channel(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        resp = client.post(
            "/api/v1/payment-attempts/",
            json={"order_id": order["id"], "channel": "invalid", "amount": 3000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422


class TestGetAttempt:
    def test_get_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        resp = client.get(
            f"/api/v1/payment-attempts/{attempt['id']}", headers=api_client_token_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == attempt["id"]

    def test_get_not_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/payment-attempts/99999", headers=api_client_token_headers
        )
        assert resp.status_code == 404


class TestListByOrder:
    def test_returns_attempts(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        first = _create_attempt(client, api_client_token_headers, order["id"])

        # Mark as failed so we can create another
        client.post(
            f"/api/v1/payment-attempts/{first['id']}/fail",
            headers=api_client_token_headers,
        )

        # Now can create a second attempt
        _create_attempt(client, api_client_token_headers, order["id"])

        resp = client.get(
            f"/api/v1/payment-attempts/by-order/{order['id']}",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_empty(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get(
            "/api/v1/payment-attempts/by-order/99999", headers=api_client_token_headers
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestMarkAsSuccess:
    def test_success_from_pending(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        resp = client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/success",
            json={"channel_transaction_id": "txn_123"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert resp.json()["channel_transaction_id"] == "txn_123"

    def test_idempotent(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        # Mark success twice
        client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/success",
            json={"channel_transaction_id": "txn_123"},
            headers=api_client_token_headers,
        )
        resp = client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/success",
            json={"channel_transaction_id": "txn_456"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_not_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/payment-attempts/99999/success",
            json={"channel_transaction_id": "txn_123"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 404


class TestMarkAsFailed:
    def test_fail_from_pending(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        resp = client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/fail",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_idempotent(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        # Mark failed twice
        client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/fail",
            headers=api_client_token_headers,
        )
        resp = client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/fail",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_not_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/payment-attempts/99999/fail",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 404

    def test_fail_then_create_new(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        first = _create_attempt(client, api_client_token_headers, order["id"])

        # Mark as failed
        client.post(
            f"/api/v1/payment-attempts/{first['id']}/fail",
            headers=api_client_token_headers,
        )

        # Can create new attempt
        resp = client.post(
            "/api/v1/payment-attempts/",
            json={"order_id": order["id"], "channel": "alipay", "amount": 3000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 201
        # New attempt should have different id
        assert resp.json()["id"] != first["id"]


class TestAdminListAll:
    def test_list_all(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        _create_attempt(client, api_client_token_headers, order["id"])

        resp = client.get("/api/v1/payment-attempts/admin/all", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_with_channel_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        _create_attempt(client, api_client_token_headers, order["id"], channel="alipay")
        _create_attempt(client, api_client_token_headers, order["id"], channel="wechat")

        resp = client.get(
            "/api/v1/payment-attempts/admin/all?channel=alipay",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["channel"] == "alipay"

    def test_list_with_status_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        client.post(
            f"/api/v1/payment-attempts/{attempt['id']}/success",
            json={"channel_transaction_id": "txn_123"},
            headers=api_client_token_headers,
        )

        resp = client.get(
            "/api/v1/payment-attempts/admin/all?status=success",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_requires_admin_auth(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        resp = client.get(
            "/api/v1/payment-attempts/admin/all", headers=api_client_token_headers
        )
        assert resp.status_code == 401


class TestAdminGetAttempt:
    def test_get_found(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])

        resp = client.get(
            f"/api/v1/payment-attempts/admin/{attempt['id']}", headers=admin_token_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == attempt["id"]

    def test_get_not_found(
        self, client: TestClient, admin_token_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/payment-attempts/admin/99999", headers=admin_token_headers
        )
        assert resp.status_code == 404
