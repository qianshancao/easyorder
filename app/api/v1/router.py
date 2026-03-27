from fastapi import APIRouter

from app.api.v1.plans import router as plans_router

router = APIRouter(prefix="/v1")
router.include_router(plans_router)
