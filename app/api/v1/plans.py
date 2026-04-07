from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentApiClient, SuperAdmin, get_plan_service
from app.schemas.plan import PlanCreate, PlanResponse, PlanStatusToggle, PlanUpdate
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
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: PlanService = Depends(get_plan_service),
) -> list[PlanResponse]:
    plans = service.list_plans(limit=limit, offset=offset)
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


@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    _admin: SuperAdmin,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.update_plan(plan_id, data)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan不存在")
    return PlanResponse.model_validate(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    _admin: SuperAdmin,
    service: PlanService = Depends(get_plan_service),
) -> None:
    try:
        deleted = service.delete_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan不存在")


@router.patch("/{plan_id}/status", response_model=PlanResponse)
def toggle_plan_status(
    plan_id: int,
    data: PlanStatusToggle,
    _admin: SuperAdmin,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.toggle_plan_status(plan_id, data.status)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan不存在")
    return PlanResponse.model_validate(plan)
