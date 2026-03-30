# EasyOrder

自托管订阅管理系统，FastAPI 三层架构，Python 3.12+，使用 uv 管理依赖。
业务需求见 @docs/requirements.md。

## 规范

根据当前任务读取对应规范文件：

- 涉及 service/repo/api 层划分、依赖注入、schema 设计 → 读取 [架构规范](docs/conventions/architecture.md)
- 添加或修改 logger 调用 → 读取 [日志规范](docs/conventions/logging.md)
- 启动 Docker 可观测性栈、查看日志/指标 → 读取 [可观测性栈](docs/conventions/observability.md)

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

## 开发流程

1. **先设计后开发** — 实现前先出方案，确认思路再动手
2. **TDD 驱动** — 先写测试（失败），再写实现（通过），最后重构
3. **小步迭代，快速验证** — 每完成一个小步骤就运行测试确认，不要攒一大堆再验证
4. **可观测性验证** — 实现完成后启动 victoria-observe 栈，调用 API 验证 traces 和 logs 符合日志规范

## IMPORTANT

- 修改代码后运行 ruff check 和 pyright 确认无报错
- 数据库模型变更需要同步更新对应的 schema 和 repository
- 可观测性栈用完后必须 `docker compose down -v` 清理
- 提交信息使用中文，Co-Authored-By: GLM 5.1 <noreply@z.ai>
- 分支命名：feature/xxx（新功能）、fix/xxx（修复）
