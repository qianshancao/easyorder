# EasyOrder 需求文档

## 1. 产品定位

自托管、单租户的订阅管理系统，帮助商户快速搭建订阅付费能力。

- **自托管**：商户部署在自己的服务器上，数据完全自主可控
- **单租户**：一套系统只服务一个商户，无多租户隔离需求

### 核心价值

- 商户自行部署，管理自己的订阅用户和订单
- 不碰资金池，通过对接支付渠道（支付宝/微信支付/Stripe）完成收单，资金直接进入商户账户
- 开箱即用的订阅生命周期管理

### 目标用户

需要订阅付费能力的商户（SaaS、工具、内容平台等）。

### 术语

- **商户（Merchant）**：部署本系统的运营者，售卖订阅服务
- **外部用户（External User）**：商户系统的用户，通过 external_user_id 关联订阅和订单

### 系统角色与认证

**角色：**

| 角色 | 说明 |
|---|---|
| 超级管理员 | 系统初始化时创建，拥有所有权限 |
| 管理员 | 超级管理员分配，管理套餐、订单 |

**认证方案：**

- 管理后台：系统自带认证，管理员直接登录
- 业务 API：采用 OAuth2.0，商户系统作为客户端携带 token 调用 API
- 系统通过 external_user_id 映射商户系统的用户，不管理用户身份和认证

## 2. 非功能性需求

- **幂等性**：支付回调可能重复推送，同一笔订单必须幂等处理，不能重复扣款或重复开通
- **数据权限**：管理员可访问所有数据；API 调用时通过 external_user_id 限定只返回该用户的数据

## 3. 核心业务模型

> 核心原则：系统只关心"怎么卖"（价格、周期、续费规则），不关心"卖什么"。产品定义由商户系统负责。

### 3.1 实体关系

```
Plan（套餐）
  ↓ 订阅时快照
Subscription（订阅）
  ↓ 产生
Order（订单/业务应收）
  ↓ 触发
PaymentAttempt（支付尝试）→ PaymentTransaction（支付流水）
  ↓ 如需退款
Refund（退款记录）
```

### 3.2 套餐（Plan）

定义"怎么卖"，包含周期、定价、续费规则、功能配额。

**定价结构：**

| 字段 | 说明 | 示例 |
|---|---|---|
| base_price | 标准续费价格 | ¥30/月 |
| introductory_price | 首期价格（可选） | ¥1（首月） |
| trial_price | 试用价格（可选） | ¥0 |
| trial_duration | 试用时长（可选） | 7天 |

**周期类型：** 月、季、年

**续费规则：** 商户可配置，如续费失败宽限期、升降级差价计算策略等

**功能配额：** JSON 结构，由商户自定义，系统不定义具体字段

```json
{
  "projects": 20,
  "storage": "10GB",
  "members": 5
}
```

### 3.3 订阅（Subscription）

用户与套餐的绑定关系，核心实体。

**关键设计：创建时快照整个 Plan。**

订阅时将 Plan 的完整信息（定价策略 + 功能配额）序列化存入订阅记录。之后 Plan 的变更（调价、调整配额）不影响已有订阅。

```
Subscription
├── external_user_id
├── plan_id            → 关联 Plan（引用）
├── plan_snapshot      → 订阅时 Plan 完整快照（JSON）
│   ├── base_price
│   ├── introductory_price
│   ├── trial_price / trial_duration
│   ├── features: { ... }
│   └── cycle: monthly / quarterly / yearly
├── status             → active / trial / past_due / canceled / expired
├── current_period_start
├── current_period_end
└── canceled_at
```

**订阅状态流转：**

```
trial → active → past_due → active（续费成功）
                 → expired（超时未续费）
                 → canceled（用户主动取消）
```

### 3.4 订单（Order）

业务应收记录，描述"应该收多少钱"，不涉及具体支付细节。

```
Order
├── external_user_id
├── subscription_id     → 可选，一次性购买时为空
├── type                → opening / renewal / upgrade / downgrade / one_time
├── amount              → 应收金额
├── currency
├── status              → pending / paid / canceled
├── created_at
├── paid_at
└── canceled_at
```

**订单类型：**

| 类型 | 说明 |
|---|---|
| opening | 首次开通订阅 |
| renewal | 周期性续费 |
| upgrade | 升级补差 |
| downgrade | 降级调整 |
| one_time | 一次性购买 |

### 3.5 支付尝试（PaymentAttempt）

一次向支付渠道发起的支付请求。一个 Order 可能有多次 PaymentAttempt（重试、换渠道）。

```
PaymentAttempt
├── order_id
├── channel             → alipay / wechat / stripe
├── amount
├── status              → pending / success / failed
└── created_at
```

### 3.6 退款（Refund）

独立记录，与 Order 关联，不混入订单类型。

```
Refund
├── order_id
├── amount              → 退款金额（支持部分退款）
├── reason
├── status              → pending / success / failed
├── channel
├── channel_refund_id   → 渠道方退款号
├── created_at
└── completed_at
```

## 3. 功能模块

### 3.1 商户管理

- 管理员账号管理（超级管理员创建/分配管理员）
- 管理后台登录认证
- 系统配置

### 3.2 套餐管理

- 套餐 CRUD（定价、周期、功能配额、续费规则）
- 套餐上下架
- 定价策略配置（首期价/试用/标准价）

### 3.3 订阅管理

- 开通订阅（快照 Plan）
- 自动续费调度
- 订阅状态变更（暂停/恢复/取消）
- 套餐升降级（差价计算策略由商户配置）
- 过期处理（续费失败宽限期由商户配置）

### 3.4 订单管理

- 订单记录查询
- 订单状态追踪
- 订单导出

### 3.5 支付管理

- 支付渠道配置
- 支付尝试记录查询
- 支付回调处理（幂等）

### 3.6 退款管理

- 退款申请与处理
- 支持部分退款
- 退款记录查询

### 3.7 支付集成

- 对接支付宝、微信支付、Stripe
- 统一支付接口封装
- 支付结果回调处理
- 不做资金池，资金直接进入商户账户

### 3.8 一次性购买

- 支持无订阅的独立订单（买断/一次性付费）
- 订单 subscription_id 为空，直接记录 Order → PaymentAttempt

## 4. 系统架构

```
FastAPI 三层架构
├── api/             表现层：路由、请求/响应
├── services/        业务层：核心业务逻辑
├── repositories/    数据层：数据库 CRUD
└── models/          数据层：ORM 模型

依赖方向：api → services → repositories → models
```

## 5. 技术选型

| 项目 | 选型 |
|---|---|
| 语言 | Python 3.12+ |
| 框架 | FastAPI |
| 包管理 | uv |
| 数据库 | MySQL（生产）/ SQLite（开发） |
| ORM | SQLAlchemy |
| 迁移 | Alembic |
| 缓存 | Redis |
| 代码质量 | ruff + pyright + semgrep |
| 测试 | pytest |
