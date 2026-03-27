# EasyOrder

白标订阅支付中台（Subscription-as-a-Service），为开发者提供开箱即用的会员订阅、计费和订单管理能力。FastAPI 三层架构，Python 3.12+，使用 uv 管理依赖。

## 核心领域

- **多租户**：每个接入方（tenant）独立隔离，支持 OEM 白标
- **订阅计划**：包年/包月/按量计费，支持升降级
- **订单与支付**：统一订单管理，对接支付渠道
- **会员状态**：续费、过期、暂停、取消生命周期管理

## 项目结构

```
app/
├── api/             # 表现层：路由、请求/响应
│   └── v1/          # API v1 版本
├── schemas/         # Pydantic 请求/响应模型
├── services/        # 业务逻辑层
├── models/          # 数据访问层：ORM 模型
├── repositories/    # 数据访问层：查询封装
├── config.py        # 配置管理
├── database.py      # 数据库连接
└── main.py          # FastAPI 应用入口
```

## 常用命令

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run fastapi dev app/main.py

# 运行测试
uv run pytest

# 类型检查
uv run pyright

# Lint & 格式化
uv run ruff check .
uv run ruff format .

# 安全扫描
uv run semgrep scan --config auto .
```

## 开发规范

### 架构分层

- 表现层（`api/`）：只处理 HTTP 请求/响应，不包含业务逻辑
- 业务层（`services/`）：核心业务逻辑，通过 repository 操作数据
- 数据层（`models/` + `repositories/`）：ORM 定义和数据库 CRUD

### 依赖方向

api → services → repositories → models

严禁反向依赖，禁止跨层调用（如 api 直接调用 repository）。

### 代码风格

- 使用 ruff 格式化和 lint
- 使用 pyright 进行类型检查
- Pydantic schema 与 ORM model 分离，不要混用

### Git 规范

- 分支命名：`feature/xxx`、`fix/xxx`
- 提交信息使用中文

## IMPORTANT

- 修改代码后运行 `uv run ruff check .` 和 `uv run pyright` 确认无报错
- 新增 API 端点必须在对应的 router 中注册
- 数据库模型变更需要同步更新对应的 schema
