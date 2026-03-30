# EasyOrder

自托管订阅管理系统，FastAPI 三层架构，Python 3.12+，使用 uv 管理依赖。
业务需求见 @docs/requirements.md。

## 规范

- [架构规范](docs/conventions/architecture.md) — 三层架构、依赖注入、schema 分离
- [Git 规范](docs/conventions/git.md) — 分支命名、提交信息
- [日志规范](docs/conventions/logging.md) — 结构化日志写法、severity 选用、各层记录要求
- [可观测性栈](docs/conventions/observability.md) — Docker 栈启动/查询/清理

## 常用命令

```bash
uv sync                          # 安装依赖
uv run fastapi dev app/main.py   # 启动开发服务器
uv run pytest                    # 运行测试
uv run pyright                   # 类型检查
uv run ruff check .              # Lint
uv run ruff format .             # 格式化
uv run semgrep scan --config .semgrep.yml .  # 架构与兼容性扫描
uv run semgrep scan --config auto .          # 安全扫描（外部规则集）
```

## IMPORTANT

- 修改代码后运行 ruff check 和 pyright 确认无报错
- 数据库模型变更需要同步更新对应的 schema 和 repository
- 可观测性栈用完后必须 `docker compose down -v` 清理
