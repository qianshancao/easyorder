from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.config import settings
from app.database import SessionLocal, engine
from app.repositories.admin import AdminRepository
from app.services.admin import AdminService
from app.telemetry import setup_telemetry, shutdown_telemetry


def _ensure_super_admin() -> None:
    db = SessionLocal()
    try:
        service = AdminService(AdminRepository(db))
        service.ensure_super_admin(settings.super_admin_username, settings.super_admin_password)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _ensure_super_admin()
    setup_telemetry(app, engine)
    yield
    shutdown_telemetry()


app = FastAPI(title="EasyOrder", version="0.1.0", lifespan=lifespan)
app.include_router(v1_router, prefix="/api")
