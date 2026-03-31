from fastapi import APIRouter

from app.api.v1.admins import router as admins_router
from app.api.v1.auth import router as auth_router
from app.api.v1.oauth_clients import router as oauth_clients_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payment_attempts import router as payment_attempts_router
from app.api.v1.plans import router as plans_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.system_configs import router as system_configs_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(admins_router)
router.include_router(plans_router)
router.include_router(system_configs_router)
router.include_router(oauth_clients_router)
router.include_router(subscriptions_router)
router.include_router(orders_router)
router.include_router(payment_attempts_router)
