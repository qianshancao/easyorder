"""Tests for Subscription API endpoints using TestClient with a test database."""


from fastapi.testclient import TestClient

from .conftest import _create_plan


class TestCreateSubscription:
    """Tests for POST /api/v1/subscriptions/ (OAuth client auth)."""

    def test_create_with_trial(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers, trial_duration=7)
        payload = {"external_user_id": "user_001", "plan_id": plan["id"]}

        resp = client.post("/api/v1/subscriptions/", json=payload, headers=api_client_token_headers)

        assert resp.status_code == 201
        data = resp.json()
        assert data["subscription"]["status"] == "trial"
        assert data["subscription"]["external_user_id"] == "user_001"
        assert data["subscription"]["plan_id"] == plan["id"]
        assert data["subscription"]["plan_snapshot"]["name"] == "Basic Plan"
        assert data["order"]["type"] == "opening"
        assert data["order"]["status"] == "pending"

    def test_create_without_trial(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        payload = {"external_user_id": "user_002", "plan_id": plan["id"]}

        resp = client.post("/api/v1/subscriptions/", json=payload, headers=api_client_token_headers)

        assert resp.status_code == 201
        data = resp.json()
        assert data["subscription"]["status"] == "active"
        assert data["order"]["type"] == "opening"
        assert data["order"]["amount"] == 3000

    def test_create_plan_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        payload = {"external_user_id": "user_003", "plan_id": 99999}

        resp = client.post("/api/v1/subscriptions/", json=payload, headers=api_client_token_headers)

        assert resp.status_code == 422

    def test_create_requires_auth(self, client: TestClient, super_admin_token_headers: dict[str, str]) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        payload = {"external_user_id": "user_004", "plan_id": plan["id"]}

        resp = client.post("/api/v1/subscriptions/", json=payload)

        assert resp.status_code == 401


class TestGetSubscription:
    """Tests for GET /api/v1/subscriptions/{id}."""

    def test_get_found(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.get(f"/api/v1/subscriptions/{sub_id}", headers=api_client_token_headers)

        assert resp.status_code == 200
        assert resp.json()["id"] == sub_id

    def test_get_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/subscriptions/99999", headers=api_client_token_headers)

        assert resp.status_code == 404


class TestListByUser:
    """Tests for GET /api/v1/subscriptions/by-user/{external_user_id}."""

    def test_returns_subscriptions(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )

        resp = client.get("/api/v1/subscriptions/by-user/user_001", headers=api_client_token_headers)

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_empty(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/subscriptions/by-user/nobody", headers=api_client_token_headers)

        assert resp.status_code == 200
        assert resp.json() == []


class TestCancelSubscription:
    """Tests for POST /api/v1/subscriptions/{id}/cancel."""

    def test_cancel_success(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(f"/api/v1/subscriptions/{sub_id}/cancel", headers=api_client_token_headers)

        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_not_found(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/subscriptions/99999/cancel", headers=api_client_token_headers)

        assert resp.status_code == 404


class TestAdminListAll:
    """Tests for GET /api/v1/subscriptions/admin/all."""

    def test_list_all(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )

        resp = client.get("/api/v1/subscriptions/admin/all", headers=admin_token_headers)

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_requires_admin_auth(self, client: TestClient, api_client_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/subscriptions/admin/all", headers=api_client_token_headers)

        assert resp.status_code == 401


class TestAdminGetSubscription:
    """Tests for GET /api/v1/subscriptions/admin/{id}."""

    def test_get_found(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.get(f"/api/v1/subscriptions/admin/{sub_id}", headers=admin_token_headers)

        assert resp.status_code == 200
        assert resp.json()["id"] == sub_id

    def test_get_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.get("/api/v1/subscriptions/admin/99999", headers=admin_token_headers)

        assert resp.status_code == 404


class TestAdminCancelSubscription:
    """Tests for POST /api/v1/subscriptions/admin/{id}/cancel."""

    def test_cancel_success(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(f"/api/v1/subscriptions/admin/{sub_id}/cancel", headers=admin_token_headers)

        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/subscriptions/admin/99999/cancel", headers=admin_token_headers)

        assert resp.status_code == 404


class TestAdminReactivateSubscription:
    """Tests for POST /api/v1/subscriptions/admin/{id}/reactivate."""

    def test_reactivate_invalid_from_active(
        self,
        client: TestClient,
        admin_token_headers: dict[str, str],
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(f"/api/v1/subscriptions/admin/{sub_id}/reactivate", headers=admin_token_headers)

        assert resp.status_code == 422
        assert "Invalid status transition" in resp.json()["detail"]

    def test_reactivate_not_found(self, client: TestClient, admin_token_headers: dict[str, str]) -> None:
        resp = client.post("/api/v1/subscriptions/admin/99999/reactivate", headers=admin_token_headers)

        assert resp.status_code == 404


class TestUpgradeSubscription:
    """Tests for POST /api/v1/subscriptions/{id}/upgrade."""

    def test_upgrade_success(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        """测试升级订阅 API。"""
        # 创建两个套餐
        plan_basic = _create_plan(client, super_admin_token_headers, name="Basic", base_price=3000)
        plan_pro = _create_plan(client, super_admin_token_headers, name="Pro", base_price=5000)

        # 创建活跃订阅（剩余 15 天）
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan_basic["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(
            f"/api/v1/subscriptions/{sub_id}/upgrade",
            json={"new_plan_id": plan_pro["id"]},
            headers=api_client_token_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription"]["id"] == sub_id
        assert data["subscription"]["plan_id"] == plan_pro["id"]
        assert data["order"]["type"] == "upgrade"
        assert data["proration_amount"] > 0

    def test_upgrade_subscription_not_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        """升级不存在的订阅。"""
        resp = client.post(
            "/api/v1/subscriptions/99999/upgrade",
            json={"new_plan_id": 1},
            headers=api_client_token_headers,
        )

        assert resp.status_code == 422
        assert "not found" in resp.json()["detail"]

    def test_upgrade_plan_not_found(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        """升级到不存在的套餐。"""
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(
            f"/api/v1/subscriptions/{sub_id}/upgrade",
            json={"new_plan_id": 99999},
            headers=api_client_token_headers,
        )

        assert resp.status_code == 422

    def test_upgrade_requires_auth(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        """升级需要认证。"""
        plan = _create_plan(client, super_admin_token_headers)
        resp = client.post(
            "/api/v1/subscriptions/1/upgrade",
            json={"new_plan_id": plan["id"]},
        )

        assert resp.status_code == 401


class TestDowngradeSubscription:
    """Tests for POST /api/v1/subscriptions/{id}/downgrade."""

    def test_downgrade_success(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        """测试降级订阅 API。"""
        # 创建两个套餐
        plan_basic = _create_plan(client, super_admin_token_headers, name="Basic", base_price=3000)
        plan_pro = _create_plan(client, super_admin_token_headers, name="Pro", base_price=5000)

        # 创建 Pro 订阅
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan_pro["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(
            f"/api/v1/subscriptions/{sub_id}/downgrade",
            json={"new_plan_id": plan_basic["id"]},
            headers=api_client_token_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription"]["id"] == sub_id
        assert data["subscription"]["plan_id"] == plan_basic["id"]
        assert data["order"]["type"] == "downgrade"
        # 降级不收钱
        assert data["proration_amount"] == 0

    def test_downgrade_subscription_not_found(
        self, client: TestClient, api_client_token_headers: dict[str, str]
    ) -> None:
        """降级不存在的订阅。"""
        resp = client.post(
            "/api/v1/subscriptions/99999/downgrade",
            json={"new_plan_id": 1},
            headers=api_client_token_headers,
        )

        assert resp.status_code == 422
        assert "not found" in resp.json()["detail"]

    def test_downgrade_plan_not_found(
        self,
        client: TestClient,
        api_client_token_headers: dict[str, str],
        super_admin_token_headers: dict[str, str],
    ) -> None:
        """降级到不存在的套餐。"""
        plan = _create_plan(client, super_admin_token_headers)
        create_resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": plan["id"]},
            headers=api_client_token_headers,
        )
        sub_id = create_resp.json()["subscription"]["id"]

        resp = client.post(
            f"/api/v1/subscriptions/{sub_id}/downgrade",
            json={"new_plan_id": 99999},
            headers=api_client_token_headers,
        )

        assert resp.status_code == 422

    def test_downgrade_requires_auth(
        self, client: TestClient, super_admin_token_headers: dict[str, str]
    ) -> None:
        """降级需要认证。"""
        plan = _create_plan(client, super_admin_token_headers)
        resp = client.post(
            "/api/v1/subscriptions/1/downgrade",
            json={"new_plan_id": plan["id"]},
        )

        assert resp.status_code == 401
