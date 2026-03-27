from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.database import engine
from app.models.base import Base

app = FastAPI(title="EasyOrder", version="0.1.0")
app.include_router(v1_router, prefix="/api")

Base.metadata.create_all(bind=engine)
