import logging

logger = logging.getLogger(__name__)

CYCLE_DURATION_DAYS: dict[str, int] = {
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365,
}


class ProrationService:
    """差价计算服务。计算升降级时的差价。"""

    def calculate_proration(
        self,
        old_base_price: int,
        old_cycle: str,
        new_base_price: int,
        new_cycle: str,
        remaining_days: int,
    ) -> int:
        """计算升降级差价。

        Args:
            old_base_price: 旧套餐标准价格 (分)
            old_cycle: 旧套餐周期
            new_base_price: 新套餐标准价格 (分)
            new_cycle: 新套餐周期
            remaining_days: 当前周期剩余天数

        Returns:
            差价 (分). 正数=需补差价 (升级), 负数=应退差价 (降级).
        """
        old_daily = old_base_price / CYCLE_DURATION_DAYS.get(old_cycle, 30)
        new_daily = new_base_price / CYCLE_DURATION_DAYS.get(new_cycle, 30)
        proration = (new_daily - old_daily) * remaining_days
        result = round(proration)
        logger.info(
            "proration.calculated",
            extra={
                "old_base_price": old_base_price,
                "old_cycle": old_cycle,
                "new_base_price": new_base_price,
                "new_cycle": new_cycle,
                "remaining_days": remaining_days,
                "proration_amount": result,
            },
        )
        return result
