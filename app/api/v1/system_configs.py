from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SuperAdmin, get_system_config_service
from app.schemas.system_config import SystemConfigCreate, SystemConfigResponse, SystemConfigUpdate
from app.services.system_config import SystemConfigService

router = APIRouter(prefix="/system-configs", tags=["系统配置"])


@router.post("/", response_model=SystemConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(
    data: SystemConfigCreate,
    _admin: SuperAdmin,
    config_service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigResponse:
    return SystemConfigResponse.model_validate(config_service.create_config(data))


@router.get("/", response_model=list[SystemConfigResponse])
def list_configs(
    _admin: SuperAdmin,
    config_service: SystemConfigService = Depends(get_system_config_service),
) -> list[SystemConfigResponse]:
    return [SystemConfigResponse.model_validate(c) for c in config_service.list_all()]


@router.get("/{config_id}", response_model=SystemConfigResponse)
def get_config(
    config_id: int,
    _admin: SuperAdmin,
    config_service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigResponse:
    config = config_service.get(config_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return SystemConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=SystemConfigResponse)
def update_config(
    config_id: int,
    data: SystemConfigUpdate,
    _admin: SuperAdmin,
    config_service: SystemConfigService = Depends(get_system_config_service),
) -> SystemConfigResponse:
    config = config_service.update_config(config_id, data)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return SystemConfigResponse.model_validate(config)
