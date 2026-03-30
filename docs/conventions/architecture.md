# 架构规范

## 三层架构

```
api/         → 表现层：路由、请求/响应
services/    → 业务逻辑层
repositories/ → 数据访问层：查询封装
models/      → ORM 模型
schemas/     → Pydantic 请求/响应模型
```

## 依赖方向

```
api → services → repositories → models
```

- 严禁反向依赖和跨层调用
- api 不得直接调用 repository
- service 不得直接返回 HTTP 响应

## 依赖注入

- api 通过 `Depends()` 注入 service
- service 通过构造函数注入 repository
- 禁止在层内部 `import` 具体实现

## Schema 与 Model 分离

- `schemas/` 中的 Pydantic 模型用于 API 请求/响应
- `models/` 中的 ORM 模型用于数据库操作
- 两者不得混用，service 层负责转换

## 项目结构

```
app/
├── api/             # 表现层
│   └── v1/          # API v1 版本
├── schemas/         # Pydantic 模型
├── services/        # 业务逻辑层
├── models/          # ORM 模型
├── repositories/    # 数据访问层
├── config.py        # 配置管理
├── database.py      # 数据库连接
├── telemetry.py     # 可观测性
└── main.py          # 应用入口
```

## 数据库模型变更

数据库模型变更需要同步更新对应的 schema 和 repository。
