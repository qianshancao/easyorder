from fastapi import APIRouter, Depends

from app.api.deps import get_plan_service
from app.schemas.plan import PlanCreate, PlanResponse
from app.services.plan import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/", response_model=PlanResponse)
def create_plan(data: PlanCreate, service: PlanService = Depends(get_plan_service)) -> PlanResponse:
    plan = service.create_plan(data)
    return PlanResponse.model_validate(plan)


@router.get("/", response_model=list[PlanResponse])
def list_plans(service: PlanService = Depends(get_plan_service)) -> list[PlanResponse]:
    plans = service.list_plans()
    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, service: PlanService = Depends(get_plan_service)) -> PlanResponse:
    plan = service.get_plan(plan_id)
    return PlanResponse.model_validate(plan)
