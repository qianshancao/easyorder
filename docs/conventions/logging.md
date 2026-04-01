# 日志规范

## Logger 获取

- **service 层**：继承 `BaseService`，通过 `self.logger` 使用，logger 名为 `app.services.{domain_name}`
- **其他模块**（telemetry 等）：模块顶部 `logger = logging.getLogger(__name__)`
- **api / repository 层**：不要获取 logger，这些层的日志由 instrumentation 自动追踪

## 事件名格式

使用 `{领域}.{动作}` 点分格式，**不含空格，不用 f-string**：

```python
# 正确
logger.info("plan.created", extra={"plan_id": plan.id, "name": plan.name})
logger.warning("plan.not_found", extra={"plan_id": plan_id})

# 错误
logger.info("plan created")           # 包含空格
logger.info(f"plan.created.{plan.id}")  # f-string
logger.info("Plan Created")           # 大写
```

常见动作词：`created`, `updated`, `deleted`, `listed`, `not_found`, `failed`, `paid`, `canceled`, `idempotent`

## extra 字段

业务数据**必须**通过 `extra` 传递，用于结构化查询：

- 实体 ID 用 `{domain}_id` 命名（如 `plan_id`, `order_id`, `admin_id`）
- 数量用 `count`
- 状态用 `status`
- 不要放完整对象，只放可序列化的标量值

```python
# 正确
logger.info("plan.created", extra={"plan_id": plan.id, "name": plan.name})

# 错误
logger.info("plan.created", extra={"plan": plan})  # 不要放 ORM 对象
```

## Severity 选用

| 级别 | 场景 | 示例 |
|------|------|------|
| DEBUG | 复杂逻辑的中间状态，生产环境通常关闭 | 条件分支路径、跳过原因 |
| INFO | 正常业务操作 | created, listed, updated, paid |
| WARNING | 预期内的异常情况 | not_found, idempotent 重复操作 |
| ERROR | 需要关注的失败 | 支付失败、外部服务不可用 |

## 各层记录规则

- **service** — 业务日志的唯一合法位置。记录业务事件（创建、状态变更、异常）
- **repository** — 禁止。数据库操作由 SQLAlchemy instrumentation 自动追踪
- **api** — 禁止。请求由 FastAPI instrumentation 自动追踪
- **telemetry** — 仅记录初始化和关闭（`telemetry.enabled`, `telemetry.disabled`）

## 新模块 checklist

添加新 service 模块时，确保日志覆盖以下场景：

1. **创建** → `{domain}.created` + 实体 ID
2. **查询列表** → `{domain}.listed` + count
3. **查不到** → `{domain}.not_found` + ID（WARNING）
4. **状态变更** → `{domain}.{action}` + 实体 ID + 新状态（如有）
5. **幂等跳过** → `{domain}.{action}_idempotent` + 实体 ID（INFO）
