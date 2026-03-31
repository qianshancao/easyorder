from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentApiClient, SuperAdmin, get_plan_service
from app.schemas.plan import PlanCreate, PlanResponse
from app.services.plan import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: PlanCreate,
    _admin: SuperAdmin,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.create_plan(data)
    return PlanResponse.model_validate(plan)


@router.get("/", response_model=list[PlanResponse])
def list_plans(
    _client: CurrentApiClient,
    service: PlanService = Depends(get_plan_service),
) -> list[PlanResponse]:
    plans = service.list_plans()
    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    _client: CurrentApiClient,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan不存在")
    return PlanResponse.model_validate(plan)
