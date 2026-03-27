# 测试违规代码（验证 semgrep 规则有效性）
# 这些代码故意违反架构规则，不应该通过 semgrep scan
#
# 验证方法：
#   1. 将违规代码复制到对应的 app/ 目录
#   2. 运行 uv run semgrep scan --config .semgrep.yml app/
#   3. 确认 semgrep 报错
#   4. 删除违规代码
#
# 以下为各规则的违规示例：


# --- 规则: api-no-direct-data-access ---
# 放到 app/api/v1/test_violation.py 中应报错
# from app.models.plan import Plan
# from app.repositories.plan import PlanRepository


# --- 规则: service-no-api-import ---
# 放到 app/services/test_violation.py 中应报错
# from app.api.v1.plans import router


# --- 规则: repo-no-upper-layer-import ---
# 放到 app/repositories/test_violation.py 中应报错
# from app.services.plan import PlanService


# --- 规则: sqlalchemy-no-declarative-base ---
# 任何文件中应报错
# from sqlalchemy.orm import declarative_base
# Base = declarative_base()


# --- 规则: sqlalchemy-no-column ---
# 任何文件中应报错
# from sqlalchemy import Column, Integer
# id = Column(Integer, primary_key=True)


# --- 规则: sqlalchemy-no-legacy-query ---
# 任何文件中应报错
# session.query(Plan)


# --- 规则: api-no-direct-service-instantiation ---
# 放到 app/api/v1/test_violation.py 中应报错
# from app.services.plan import PlanService
# service = PlanService(repo=...)  # 应使用 Depends() 注入


# --- 规则: service-no-direct-repo-instantiation ---
# 放到 app/services/test_violation.py 中应报错
# from app.repositories.plan import PlanRepository
# repo = PlanRepository(db=...)  # 应通过构造函数依赖注入
