"""Tests for PaymentTransaction API endpoints using TestClient with a test database."""

from fastapi.testclient import TestClient

from .conftest import _create_order


def _create_attempt(
    client: TestClient,
    api_headers: dict[str, str],
    order_id: int,
) -> dict[str, object]:
    resp = client.post(
        "/api/v1/payment-attempts/",
        json={"order_id": order_id, "channel": "alipay", "amount": 3000},
        headers=api_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _mark_success(
    client: TestClient,
    api_headers: dict[str, str],
    attempt_id: int,
    channel_transaction_id: str = "txn_001",
) -> dict[str, object]:
    resp = client.post(
        f"/api/v1/payment-attempts/{attempt_id}/success",
        json={"channel_transaction_id": channel_transaction_id},
        headers=api_headers,
    )
    assert resp.status_code == 200
    return resp.json()


class TestTransactionCreatedOnMarkSuccess:
    """Verify that marking an attempt as success creates a PaymentTransaction."""

    def test_transaction_visible_by_attempt(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        resp = client.get(
            f"/api/v1/payment-transactions/by-attempt/{attempt['id']}",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["payment_attempt_id"] == attempt["id"]
        assert data[0]["order_id"] == order["id"]
        assert data[0]["channel"] == "alipay"
        assert data[0]["amount"] == 3000
        assert data[0]["channel_transaction_id"] == "txn_001"
        assert data[0]["status"] == "confirmed"

    def test_transaction_visible_by_order(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        resp = client.get(
            f"/api/v1/payment-transactions/by-order/{order['id']}",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["order_id"] == order["id"]

    def test_transaction_get_by_id(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        # Get the transaction ID from the by-attempt list
        list_resp = client.get(
            f"/api/v1/payment-transactions/by-attempt/{attempt['id']}",
            headers=api_client_token_headers,
        )
        txn_id = list_resp.json()[0]["id"]

        resp = client.get(
            f"/api/v1/payment-transactions/{txn_id}",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == txn_id

    def test_no_transaction_before_success(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        # Don't mark as success

        resp = client.get(
            f"/api/v1/payment-transactions/by-attempt/{attempt['id']}",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_idempotent_mark_success_creates_one_transaction(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"], "txn_unique")
        _mark_success(client, api_client_token_headers, attempt["id"], "txn_unique")

        resp = client.get(
            f"/api/v1/payment-transactions/by-attempt/{attempt['id']}",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestGetTransaction:
    def test_not_found(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/v1/payment-transactions/99999", headers=api_client_token_headers)
        assert resp.status_code == 404


class TestAdminListAll:
    def test_list_all(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        resp = client.get(
            "/api/v1/payment-transactions/admin/all",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_channel(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        resp = client.get(
            "/api/v1/payment-transactions/admin/all?channel=alipay",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_status(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        resp = client.get(
            "/api/v1/payment-transactions/admin/all?status=confirmed",
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
            "/api/v1/payment-transactions/admin/all",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 401


class TestAdminGetTransaction:
    def test_get_found(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
        attempt = _create_attempt(client, api_client_token_headers, order["id"])
        _mark_success(client, api_client_token_headers, attempt["id"])

        list_resp = client.get(
            f"/api/v1/payment-transactions/by-attempt/{attempt['id']}",
            headers=api_client_token_headers,
        )
        txn_id = list_resp.json()[0]["id"]

        resp = client.get(
            f"/api/v1/payment-transactions/admin/{txn_id}",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == txn_id

    def test_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.get(
            "/api/v1/payment-transactions/admin/99999",
            headers=admin_token_headers,
        )
        assert resp.status_code == 404
