"""Tests for Order API endpoints using TestClient with a test database."""

from fastapi.testclient import TestClient

from .conftest import _create_order, _create_plan, _create_subscription


class TestCreateOrder:
    def test_create_one_time(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        data = _create_order(client, api_client_token_headers)

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
        order = _create_order(client, api_client_token_headers)

        resp = client.get(f"/api/v1/orders/{order['id']}", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == order["id"]

    def test_get_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/orders/99999", headers=api_client_token_headers)
        assert resp.status_code == 404


class TestListByUser:
    def test_returns_orders(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        _create_order(client, api_client_token_headers)

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
        assert len(resp.json()) == 1
        assert resp.json()[0]["type"] == "opening"


class TestMarkAsPaid:
    def test_pay_success(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_order(client, api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        assert resp.json()["paid_at"] is not None

    def test_pay_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_order(client, api_client_token_headers)

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
        order = _create_order(client, api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/orders/99999/cancel", headers=api_client_token_headers)
        assert resp.status_code == 404

    def test_cancel_paid_order_fails(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_order(client, api_client_token_headers)
        client.post(f"/api/v1/orders/{order['id']}/pay", headers=api_client_token_headers)

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=api_client_token_headers)
        assert resp.status_code == 422

    def test_cancel_idempotent(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        order = _create_order(client, api_client_token_headers)
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
        _create_order(client, api_client_token_headers)

        resp = client.get("/api/v1/orders/admin/all", headers=admin_token_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_with_status_filter(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)
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
        _create_order(client, api_client_token_headers)

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
        _create_order(client, api_client_token_headers, external_user_id="user_filter")

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
        assert len(resp.json()) == 1
        assert resp.json()[0]["type"] == "opening"

    def test_get_found(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
    ) -> None:
        order = _create_order(client, api_client_token_headers)

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
        order = _create_order(client, api_client_token_headers)

        resp = client.post(f"/api/v1/orders/admin/{order['id']}/cancel", headers=admin_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/orders/admin/99999/cancel", headers=admin_token_headers)
        assert resp.status_code == 404


def _one_time_pay(
    client: TestClient,
    api_headers: dict[str, str],
    **overrides: object,
) -> dict[str, object]:
    """调用 POST /api/v1/orders/one-time-pay 一体化端点。"""
    defaults: dict[str, object] = {
        "external_user_id": "user_001",
        "channel": "alipay",
        "amount": 3000,
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/orders/one-time-pay", json=defaults, headers=api_headers)
    return resp.json()


class TestOneTimePurchase:
    """POST /api/v1/orders/one-time-pay 一体化购买端点。"""

    def test_one_time_purchase_returns_order(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_001",
                "channel": "alipay",
                "amount": 3000,
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # 验证 order 部分
        assert data["order"]["type"] == "one_time"
        assert data["order"]["status"] == "pending"
        assert data["order"]["amount"] == 3000
        assert data["order"]["subscription_id"] is None

        # 验证 payment_attempt 部分
        assert data["payment_attempt"]["status"] == "pending"
        assert data["payment_attempt"]["channel"] == "alipay"
        assert data["payment_attempt"]["amount"] == 3000
        assert data["payment_attempt"]["order_id"] == data["order"]["id"]

    def test_order_type_is_one_time(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        data = _one_time_pay(client, api_client_token_headers)
        assert data["order"]["type"] == "one_time"

    def test_payment_attempt_status_pending(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        data = _one_time_pay(client, api_client_token_headers)
        assert data["payment_attempt"]["status"] == "pending"

    def test_subscription_id_is_none(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        data = _one_time_pay(client, api_client_token_headers)
        assert data["order"]["subscription_id"] is None

    def test_invalid_channel(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_001",
                "channel": "invalid_channel",
                "amount": 3000,
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_invalid_amount(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_001",
                "channel": "alipay",
                "amount": -100,
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_001",
                "channel": "alipay",
                "amount": 3000,
            },
        )
        assert resp.status_code == 401

    def test_missing_external_user_id(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={"channel": "alipay", "amount": 3000},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422

    def test_zero_amount(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={"external_user_id": "user_001", "channel": "alipay", "amount": 0},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 422


class TestOneTimePurchaseE2E:
    """one-time-pay 端到端流程测试。"""

    def test_pay_then_mark_success_order_becomes_paid(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        """one-time-pay -> 标记支付成功 -> 验证订单状态为 paid。"""
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_e2e_1",
                "channel": "alipay",
                "amount": 5000,
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        order_id = data["order"]["id"]
        attempt_id = data["payment_attempt"]["id"]

        # 标记支付成功
        resp = client.post(
            f"/api/v1/payment-attempts/{attempt_id}/success",
            json={"channel_transaction_id": "txn_e2e_001"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # 验证订单状态已变为 paid
        resp = client.get(f"/api/v1/orders/{order_id}", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        assert resp.json()["paid_at"] is not None

    def test_pay_then_cancel(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        """one-time-pay -> 取消订单。"""
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_e2e_2",
                "channel": "wechat",
                "amount": 2000,
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        order_id = data["order"]["id"]

        # 取消订单
        resp = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

        # 验证订单已取消
        resp = client.get(f"/api/v1/orders/{order_id}", headers=api_client_token_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_pay_mark_success_then_refund(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        """one-time-pay -> 标记支付成功 -> 申请退款。"""
        resp = client.post(
            "/api/v1/orders/one-time-pay",
            json={
                "external_user_id": "user_e2e_3",
                "channel": "alipay",
                "amount": 8000,
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        order_id = data["order"]["id"]
        attempt_id = data["payment_attempt"]["id"]

        # 标记支付成功
        resp = client.post(
            f"/api/v1/payment-attempts/{attempt_id}/success",
            json={"channel_transaction_id": "txn_refund_001"},
            headers=api_client_token_headers,
        )
        assert resp.status_code == 200

        # 验证订单已 paid
        resp = client.get(f"/api/v1/orders/{order_id}", headers=api_client_token_headers)
        assert resp.json()["status"] == "paid"

        # 申请退款
        resp = client.post(
            "/api/v1/refunds/",
            json={
                "order_id": order_id,
                "amount": 8000,
                "reason": "用户申请退款",
                "channel": "alipay",
            },
            headers=api_client_token_headers,
        )
        assert resp.status_code == 201
        refund_data = resp.json()
        assert refund_data["status"] == "pending"
        assert refund_data["order_id"] == order_id
