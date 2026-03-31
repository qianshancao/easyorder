"""Tests for Refund API endpoints using TestClient with a test database."""

from fastapi.testclient import TestClient


def _create_paid_order(client: TestClient, api_headers: dict[str, str], **overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "external_user_id": "user_001",
        "type": "one_time",
        "amount": 5000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/orders/", json=defaults, headers=api_headers)
    assert resp.status_code == 201
    order = resp.json()
    # Mark as paid
    client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_headers)
    # Refresh order
    resp = client.get(f"/api/v1/orders/{order['id']}", headers=api_headers)
    return resp.json()


def _create_refund(
    client: TestClient,
    api_headers: dict[str, str],
    order_id: int,
    **overrides: object,
) -> dict[str, object]:
    defaults: dict[str, object] = {
        "order_id": order_id,
        "amount": 3000,
        "reason": "用户申请退款",
        "channel": "alipay",
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/refunds/", json=defaults, headers=api_headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateRefund:
    def test_create_success(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        data = _create_refund(client, api_client_token_headers, order["id"])

        assert data["order_id"] == order["id"]
        assert data["amount"] == 3000
        assert data["reason"] == "用户申请退款"
        assert data["channel"] == "alipay"
        assert data["status"] == "pending"
        assert data["channel_refund_id"] is None
        assert data["completed_at"] is None
        assert "created_at" in data

    def test_create_order_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": 99999, "amount": 3000, "reason": "test", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_order_not_paid(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        # Create order but don't pay it
        resp = client.post(
            "/api/v1/orders/",
            json={"external_user_id": "user_001", "type": "one_time", "amount": 5000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 201
        order = resp.json()

        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 3000, "reason": "test", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_amount_exceeds_order(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers, amount=3000)
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 5000, "reason": "test", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_cumulative_refund_exceeds_order(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        # Order amount is 5000, create first refund of 3000
        order = _create_paid_order(client, api_client_token_headers)
        _create_refund(client, api_client_token_headers, order["id"], amount=3000)

        # Try to create second refund of 3000 (total would be 6000 > 5000)
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 3000, "reason": "超额退款", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422
        assert "plus existing refunds" in resp.json()["detail"]

    def test_create_cumulative_refund_exact_order_amount_allowed(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        # Order amount is 5000, create first refund of 2000
        order = _create_paid_order(client, api_client_token_headers)
        _create_refund(client, api_client_token_headers, order["id"], amount=2000)

        # Create second refund of 3000 (total = 5000 = order amount, should succeed)
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 3000, "reason": "剩余退款", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 201

    def test_create_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        first = _create_refund(client, api_client_token_headers, order["id"], amount=2000)

        # Create again with same amount, should return same refund
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 2000, "reason": "用户申请退款", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == first["id"]

    def test_create_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": 1, "amount": 3000, "reason": "test", "channel": "alipay"},
        )
        assert resp.status_code == 401

    def test_create_rejects_invalid_channel(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 3000, "reason": "test", "channel": "invalid"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_rejects_empty_reason(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        resp = client.post(
            "/api/v1/refunds/",
            json={"order_id": order["id"], "amount": 3000, "reason": "", "channel": "alipay"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_create_with_all_channels(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        for channel in ("alipay", "wechat", "stripe"):
            order = _create_paid_order(client, api_client_token_headers)
            resp = client.post(
                "/api/v1/refunds/",
                json={"order_id": order["id"], "amount": 1000, "reason": "test", "channel": channel},
                headers=api_client_token_headers,
            )
            assert resp.status_code == 201
            assert resp.json()["channel"] == channel


class TestGetRefund:
    def test_get_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        resp = client.get(f"/api/v1/refunds/{refund['id']}", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == refund["id"]

    def test_get_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/refunds/99999", headers=api_client_token_headers)
        assert resp.status_code == 404

    def test_get_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/refunds/1")
        assert resp.status_code == 401


class TestMarkAsSuccess:
    def test_success_from_pending(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        resp = client.post(
            f"/api/v1/refunds/{refund['id']}/success",
            json={"channel_refund_id": "refund_12345"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["channel_refund_id"] == "refund_12345"
        assert data["completed_at"] is not None

    def test_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        # Mark success twice
        client.post(
            f"/api/v1/refunds/{refund['id']}/success",
            json={"channel_refund_id": "refund_123"},
            headers=api_client_token_headers,
        )
        resp = client.post(
            f"/api/v1/refunds/{refund['id']}/success",
            json={"channel_refund_id": "refund_456"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/refunds/99999/success",
            json={"channel_refund_id": "refund_123"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 404

    def test_invalid_from_failed(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        # Mark as failed
        client.post(f"/api/v1/refunds/{refund['id']}/fail", headers=api_client_token_headers)

        # Try to mark as success
        resp = client.post(
            f"/api/v1/refunds/{refund['id']}/success",
            json={"channel_refund_id": "refund_123"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422


class TestMarkAsFailed:
    def test_fail_from_pending(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        resp = client.post(
            f"/api/v1/refunds/{refund['id']}/fail",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        # Mark failed twice
        client.post(f"/api/v1/refunds/{refund['id']}/fail", headers=api_client_token_headers)
        resp = client.post(f"/api/v1/refunds/{refund['id']}/fail", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/refunds/99999/fail",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 404

    def test_invalid_from_success(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        # Mark as success
        client.post(
            f"/api/v1/refunds/{refund['id']}/success",
            json={"channel_refund_id": "refund_123"},
            headers=api_client_token_headers,
        )

        # Try to mark as failed
        resp = client.post(f"/api/v1/refunds/{refund['id']}/fail", headers=api_client_token_headers)
        assert resp.status_code == 422


class TestAdminListAll:
    def test_list_all(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        _create_refund(client, api_client_token_headers, order["id"])

        resp = client.get("/api/v1/refunds/admin/all", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_with_order_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order1 = _create_paid_order(client, api_client_token_headers)
        order2 = _create_paid_order(client, api_client_token_headers)
        _create_refund(client, api_client_token_headers, order1["id"])
        _create_refund(client, api_client_token_headers, order2["id"])

        resp = client.get(
            f"/api/v1/refunds/admin/all?order_id={order1['id']}",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["order_id"] == order1["id"]

    def test_list_with_status_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        client.post(
            f"/api/v1/refunds/{refund['id']}/success",
            json={"channel_refund_id": "refund_123"},
            headers=api_client_token_headers,
        )

        resp = client.get(
            "/api/v1/refunds/admin/all?status=success",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_with_channel_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        _create_refund(client, api_client_token_headers, order["id"], amount=1000, channel="alipay")
        _create_refund(client, api_client_token_headers, order["id"], amount=1000, channel="wechat")

        resp = client.get(
            "/api/v1/refunds/admin/all?channel=alipay",
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["channel"] == "alipay"

    def test_requires_admin_auth(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/v1/refunds/admin/all", headers=api_client_token_headers)
        assert resp.status_code == 401


class TestAdminGetRefund:
    def test_get_found(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_paid_order(client, api_client_token_headers)
        refund = _create_refund(client, api_client_token_headers, order["id"])

        resp = client.get(f"/api/v1/refunds/admin/{refund['id']}", headers=admin_token_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == refund["id"]

    def test_get_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/refunds/admin/99999", headers=admin_token_headers)
        assert resp.status_code == 404
