# 可观测性栈

用于验证运行行为、复现 bug。**用完必须清理。**

## 启动与清理

```bash
docker compose up -d                   # 启动
docker compose down -v                 # 清理（含数据卷）
```

## 数据流

```
App (OTEL SDK) → OTEL Collector (localhost:4317/4318) → VictoriaMetrics (指标, :8428)
                                                        → VictoriaTraces  (链路, :9428)
                                                        → VictoriaLogs    (日志, :9429)
```

## 查询 API

### Metrics

```bash
curl 'localhost:8428/api/v1/query?query=...'
```

### Traces

```bash
curl 'localhost:9428/api/traces...'
```

### Logs

```bash
# 查看所有日志
curl 'localhost:9429/select/logsql/query?query=*'

# 按级别
curl 'localhost:9429/select/logsql/query?query=severity:WARN'

# 按事件名
curl 'localhost:9429/select/logsql/query?query=_msg:plan.not_found'

# 按 extra 字段
curl 'localhost:9429/select/logsql/query?query=plan_id:999'
```

## 启用方式

启动应用时设置环境变量：

```bash
EASYORDER_OTEL_ENABLED=true uv run uvicorn app.main:app
```

默认关闭（`EASYORDER_OTEL_ENABLED=false`），开发时无需启动栈。
