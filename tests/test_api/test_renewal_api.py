"""Tests for Renewal API endpoints."""

from datetime import UTC, datetime, timedelta

from app.models.subscription import Subscription


class TestRenewalAdminAPI:
    """测试管理员续费 API。"""

    def test_process_renewals_as_super_admin(
        self, client, db_session, super_admin_token_headers, subscription_repository
    ) -> None:
        """超级管理员可以批量处理续费。"""
        # 创建即将到期的订阅
        from app.models.plan import Plan
        from app.repositories.base import BaseRepository

        plan_repo = BaseRepository(Plan, db_session)
        plan = plan_repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))

        now = datetime.now(tz=UTC)
        sub = subscription_repository.create(
            Subscription(
                external_user_id="user_001",
                plan_id=plan.id,
                plan_snapshot={"cycle": "monthly", "base_price": 3000},
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=2),
            )
        )

        response = client.post(
            "/api/v1/renewals/admin/process",
            json={"grace_period_days": 7},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["processed_count"] == 1
        assert data["success_count"] == 1
        assert data["failure_count"] == 0
        assert len(data["attempts"]) == 1
        assert data["attempts"][0]["subscription_id"] == sub.id
        assert data["attempts"][0]["success"] is True

    def test_process_renewals_forbidden_as_regular_admin(self, client, admin_token_headers) -> None:
        """普通管理员不能批量处理续费。"""
        response = client.post(
            "/api/v1/renewals/admin/process",
            json={"grace_period_days": 7},
            headers=admin_token_headers,
        )

        assert response.status_code == 403

    def test_process_renewals_unauthorized_without_token(self, client) -> None:
        """没有 token 不能批量处理续费。"""
        response = client.post(
            "/api/v1/renewals/admin/process",
            json={"grace_period_days": 7},
        )

        assert response.status_code == 401

    def test_mark_renewal_success_as_super_admin(
        self, client, db_session, super_admin_token_headers, subscription_repository
    ) -> None:
        """超级管理员可以标记续费成功。"""
        from app.models.plan import Plan
        from app.repositories.base import BaseRepository

        plan_repo = BaseRepository(Plan, db_session)
        plan = plan_repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))

        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=5)
        sub = subscription_repository.create(
            Subscription(
                external_user_id="user_001",
                plan_id=plan.id,
                plan_snapshot={"cycle": "monthly", "base_price": 3000},
                status="active",
                current_period_start=now,
                current_period_end=original_end,
            )
        )

        response = client.post(
            f"/api/v1/renewals/admin/{sub.id}/success",
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # 验证订阅状态仍为 active
        assert data["status"] == "active"
        # 验证周期延长约 30 天（月付 cycle）
        from datetime import datetime as dt

        end = dt.fromisoformat(data["current_period_end"])
        diff = (end.replace(tzinfo=None) if end.tzinfo else end) - (
            original_end.replace(tzinfo=None) if original_end.tzinfo else original_end
        )
        assert abs(diff.total_seconds() - timedelta(days=30).total_seconds()) < 5

    def test_mark_renewal_success_forbidden_as_regular_admin(self, client, admin_token_headers) -> None:
        """普通管理员不能标记续费成功。"""
        response = client.post(
            "/api/v1/renewals/admin/1/success",
            headers=admin_token_headers,
        )

        assert response.status_code == 403

    def test_mark_renewal_failure_as_super_admin(
        self, client, db_session, super_admin_token_headers, subscription_repository
    ) -> None:
        """超级管理员可以标记续费失败。"""
        from app.models.plan import Plan
        from app.repositories.base import BaseRepository

        plan_repo = BaseRepository(Plan, db_session)
        plan = plan_repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))

        now = datetime.now(tz=UTC)
        sub = subscription_repository.create(
            Subscription(
                external_user_id="user_001",
                plan_id=plan.id,
                plan_snapshot={"cycle": "monthly", "base_price": 3000},
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=5),
            )
        )

        response = client.post(
            f"/api/v1/renewals/admin/{sub.id}/fail",
            json={"grace_period_days": 7},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "past_due"

    def test_mark_renewal_failure_forbidden_as_regular_admin(self, client, admin_token_headers) -> None:
        """普通管理员不能标记续费失败。"""
        response = client.post(
            "/api/v1/renewals/admin/1/fail",
            json={"grace_period_days": 7},
            headers=admin_token_headers,
        )

        assert response.status_code == 403

    def test_process_expired_as_super_admin(
        self, client, db_session, super_admin_token_headers, subscription_repository
    ) -> None:
        """超级管理员可以处理过期订阅。"""
        from app.models.plan import Plan
        from app.repositories.base import BaseRepository

        plan_repo = BaseRepository(Plan, db_session)
        plan = plan_repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))

        now = datetime.now(tz=UTC)
        sub = subscription_repository.create(
            Subscription(
                external_user_id="user_001",
                plan_id=plan.id,
                plan_snapshot={"cycle": "monthly", "base_price": 3000},
                status="past_due",
                current_period_start=now - timedelta(days=40),
                current_period_end=now - timedelta(days=10),
            )
        )

        response = client.post(
            "/api/v1/renewals/admin/process-expired",
            json={"grace_period_days": 7},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expired_count"] == 1

    def test_process_expired_forbidden_as_regular_admin(self, client, admin_token_headers) -> None:
        """普通管理员不能处理过期订阅。"""
        response = client.post(
            "/api/v1/renewals/admin/process-expired",
            json={"grace_period_days": 7},
            headers=admin_token_headers,
        )

        assert response.status_code == 403

    def test_mark_renewal_success_with_past_due_subscription(
        self, client, db_session, super_admin_token_headers, subscription_repository
    ) -> None:
        """past_due 订阅标记续费成功后应回到 active。"""
        from app.models.plan import Plan
        from app.repositories.base import BaseRepository

        plan_repo = BaseRepository(Plan, db_session)
        plan = plan_repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))

        now = datetime.now(tz=UTC)
        sub = subscription_repository.create(
            Subscription(
                external_user_id="user_001",
                plan_id=plan.id,
                plan_snapshot={"cycle": "monthly", "base_price": 3000},
                status="past_due",
                current_period_start=now - timedelta(days=35),
                current_period_end=now - timedelta(days=5),
            )
        )

        response = client.post(
            f"/api/v1/renewals/admin/{sub.id}/success",
            headers=super_admin_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_mark_renewal_success_not_found(self, client, super_admin_token_headers) -> None:
        """标记不存在的订阅续费成功应返回 404。"""
        response = client.post(
            "/api/v1/renewals/admin/99999/success",
            headers=super_admin_token_headers,
        )

        assert response.status_code == 404

    def test_mark_renewal_failure_not_found(self, client, super_admin_token_headers) -> None:
        """标记不存在的订阅续费失败应返回 404。"""
        response = client.post(
            "/api/v1/renewals/admin/99999/fail",
            json={"grace_period_days": 7},
            headers=super_admin_token_headers,
        )

        assert response.status_code == 404


class TestRenewalClientAPI:
    """测试客户端续费 API。"""

    def test_renew_single_subscription_as_client(
        self, client, db_session, api_client_token_headers, subscription_repository
    ) -> None:
        """OAuth 客户端可以续费单个订阅。"""
        from app.models.plan import Plan
        from app.repositories.base import BaseRepository

        plan_repo = BaseRepository(Plan, db_session)
        plan = plan_repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))

        now = datetime.now(tz=UTC)
        sub = subscription_repository.create(
            Subscription(
                external_user_id="user_001",
                plan_id=plan.id,
                plan_snapshot={"cycle": "monthly", "base_price": 3000},
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=5),
            )
        )

        response = client.post(
            f"/api/v1/renewals/{sub.id}/renew",
            headers=api_client_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["subscription_id"] == sub.id
        assert data["success"] is True
        assert data["order_id"] is not None

    def test_renew_subscription_not_found(self, client, api_client_token_headers) -> None:
        """续费不存在的订阅返回错误。"""
        response = client.post(
            "/api/v1/renewals/999/renew",
            headers=api_client_token_headers,
        )

        assert response.status_code == 404

    def test_renew_subscription_unauthorized_without_token(self, client) -> None:
        """没有 token 不能续费订阅。"""
        response = client.post("/api/v1/renewals/1/renew")

        assert response.status_code == 401

    def test_admin_endpoints_rejected_with_api_token(self, client, api_client_token_headers) -> None:
        """API token 不能调用管理员续费端点。"""
        response = client.post(
            "/api/v1/renewals/admin/process",
            json={"grace_period_days": 7},
            headers=api_client_token_headers,
        )

        assert response.status_code == 401
