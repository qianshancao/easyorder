# EasyOrder

自托管订阅管理系统，FastAPI 三层架构，Python 3.12+，使用 uv 管理依赖。
业务需求见 @docs/requirements.md。

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
uv sync                          # 安装依赖
uv run fastapi dev app/main.py   # 启动开发服务器
uv run pytest                    # 运行测试
uv run pyright                   # 类型检查
uv run ruff check .              # Lint
uv run ruff format .             # 格式化
uv run semgrep scan --config .semgrep.yml .  # 安全扫描
```

## 开发规范

### 架构

- 三层架构：api → services → repositories → models
- 严禁反向依赖和跨层调用
- 必须使用依赖注入：api 通过 Depends() 注入 service，service 通过构造函数注入 repository
- Pydantic schema 与 ORM model 分离

### Git

- 分支命名：`feature/xxx`、`fix/xxx`
- 提交信息使用中文
- Co-Authored-By: GLM 5.1 <noreply@z.ai>

## IMPORTANT

- 修改代码后运行 ruff check 和 pyright 确认无报错
- 数据库模型变更需要同步更新对应的 schema 和 repository
