# 日志规范

## Logger 获取

```python
import logging
logger = logging.getLogger(__name__)
```

每个模块顶部获取，使用 `__name__` 自动生成 `scope.name`（如 `app.services.plan`）。

## 事件名格式

`_msg` 使用 `{领域}.{动作}` 点分格式：

```python
logger.info("plan.created", extra={...})
logger.info("plan.listed", extra={...})
logger.warning("plan.not_found", extra={...})
logger.error("payment.failed", extra={...})
```

## 结构化字段

业务数据通过 `extra` 传递，禁止拼接到消息文本中：

```python
# 正确
logger.info("plan.created", extra={"plan_id": plan.id, "name": plan.name})

# 错误
logger.info(f"plan created: {plan.name}")
```

`extra` 中的字段在 VictoriaLogs 中可直接按字段名查询。

## Severity 选用

| 级别 | 场景 | 示例 |
|------|------|------|
| INFO | 正常业务操作 | 创建、列表、更新 |
| WARNING | 预期内的异常情况 | 查不到记录、降级处理 |
| ERROR | 需要关注的失败 | 支付失败、外部服务不可用 |

## 各层记录要求

- **service** — 必须记录业务事件（创建、状态变更、异常）
- **repository** — 不记录业务日志，数据库操作由 SQLAlchemy instrumentation 自动追踪
- **api** — 不记录业务日志，请求由 FastAPI instrumentation 自动追踪
- **telemetry** — 仅记录初始化和关闭
