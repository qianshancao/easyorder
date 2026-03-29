from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.database import engine
from app.models.base import Base
from app.telemetry import setup_telemetry, shutdown_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    setup_telemetry(app, engine)
    yield
    shutdown_telemetry()


app = FastAPI(title="EasyOrder", version="0.1.0", lifespan=lifespan)
app.include_router(v1_router, prefix="/api")
