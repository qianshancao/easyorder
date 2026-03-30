from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentAdmin, SuperAdmin, get_admin_service
from app.schemas.admin import AdminCreate, AdminResponse, AdminUpdate, PasswordChange
from app.services.admin import AdminService

router = APIRouter(prefix="/admins", tags=["管理员"])


@router.post("/", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def create_admin(
    data: AdminCreate,
    _admin: SuperAdmin,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    return AdminResponse.model_validate(admin_service.create_admin(data))


@router.get("/", response_model=list[AdminResponse])
def list_admins(
    _admin: CurrentAdmin,
    admin_service: AdminService = Depends(get_admin_service),
) -> list[AdminResponse]:
    return [AdminResponse.model_validate(a) for a in admin_service.list_all()]


@router.get("/{admin_id}", response_model=AdminResponse)
def get_admin(
    admin_id: int,
    _admin: CurrentAdmin,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    admin = admin_service.get(admin_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return AdminResponse.model_validate(admin)


@router.put("/{admin_id}", response_model=AdminResponse)
def update_admin(
    admin_id: int,
    data: AdminUpdate,
    _admin: SuperAdmin,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminResponse:
    admin = admin_service.update_admin(admin_id, data)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return AdminResponse.model_validate(admin)


@router.put("/{admin_id}/password", response_model=dict)
def change_password(
    admin_id: int,
    data: PasswordChange,
    current_admin: CurrentAdmin,
    admin_service: AdminService = Depends(get_admin_service),
) -> dict[str, str]:
    if current_admin.role != "super_admin" and current_admin.id != admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改他人密码")
    if not admin_service.change_password(admin_id, data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码修改失败")
    return {"message": "密码已修改"}
