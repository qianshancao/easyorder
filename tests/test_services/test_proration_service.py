"""ProrationService 差价计算测试。"""

from app.services.proration import ProrationService


class TestCalculateProration:
    """ProrationService.calculate_proration 测试。"""

    def test_upgrade_proration_positive(self) -> None:
        """升级：月付 3000 -> 月付 5000，剩余 15 天，应产生正差价。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=3000,
            old_cycle="monthly",
            new_base_price=5000,
            new_cycle="monthly",
            remaining_days=15,
        )
        assert result == 1000  # (5000/30 - 3000/30) * 15 = 1000

    def test_downgrade_proration_negative(self) -> None:
        """降级：月付 5000 -> 月付 3000，剩余 15 天，应产生负差价。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=5000,
            old_cycle="monthly",
            new_base_price=3000,
            new_cycle="monthly",
            remaining_days=15,
        )
        assert result == -1000

    def test_same_price_zero(self) -> None:
        """同价：差价为 0。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=3000,
            old_cycle="monthly",
            new_base_price=3000,
            new_cycle="monthly",
            remaining_days=15,
        )
        assert result == 0

    def test_remaining_zero(self) -> None:
        """剩余 0 天：差价为 0。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=3000,
            old_cycle="monthly",
            new_base_price=5000,
            new_cycle="monthly",
            remaining_days=0,
        )
        assert result == 0

    def test_different_cycles_monthly_to_yearly(self) -> None:
        """不同周期：月付 3000 -> 年付 36000，剩余 15 天。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=3000,
            old_cycle="monthly",
            new_base_price=36000,
            new_cycle="yearly",
            remaining_days=15,
        )
        # (36000/365 - 3000/30) * 15 = (98.63 - 100) * 15 = -20.5 -> -21
        assert result < 0  # 年付日均更便宜

    def test_different_cycles_yearly_to_monthly(self) -> None:
        """不同周期：年付 36000 -> 月付 5000，剩余 15 天。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=36000,
            old_cycle="yearly",
            new_base_price=5000,
            new_cycle="monthly",
            remaining_days=15,
        )
        # (5000/30 - 36000/365) * 15 = (166.67 - 98.63) * 15 = 1020
        assert result > 0  # 升级

    def test_rounding(self) -> None:
        """验证四舍五入到整数。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=1000,
            old_cycle="monthly",
            new_base_price=2000,
            new_cycle="monthly",
            remaining_days=7,
        )
        # (2000/30 - 1000/30) * 7 = 33.33... * 7 / 30 -> 233.33 -> 233
        assert isinstance(result, int)
        assert result == 233

    def test_quarterly_cycle(self) -> None:
        """季度周期计算。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=9000,
            old_cycle="quarterly",
            new_base_price=18000,
            new_cycle="quarterly",
            remaining_days=30,
        )
        # (18000/90 - 9000/90) * 30 = (200 - 100) * 30 = 3000
        assert result == 3000

    def test_unknown_cycle_defaults_to_30_days(self) -> None:
        """未知周期默认 30 天。"""
        svc = ProrationService()
        result = svc.calculate_proration(
            old_base_price=3000,
            old_cycle="unknown",
            new_base_price=6000,
            new_cycle="unknown",
            remaining_days=15,
        )
        # (6000/30 - 3000/30) * 15 = 1500
        assert result == 1500
