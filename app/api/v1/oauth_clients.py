from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SuperAdmin, get_oauth_client_service
from app.schemas.oauth_client import OAuthClientCreate, OAuthClientResponse, OAuthClientSecretResponse
from app.services.oauth_client import OAuthClientService

router = APIRouter(prefix="/oauth-clients", tags=["OAuth 客户端"])


@router.post("/", response_model=OAuthClientSecretResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    data: OAuthClientCreate,
    _admin: SuperAdmin,
    client_service: OAuthClientService = Depends(get_oauth_client_service),
) -> OAuthClientSecretResponse:
    client, raw_secret = client_service.create_client(data)
    return OAuthClientSecretResponse(client_id=client.client_id, client_secret=raw_secret)


@router.get("/", response_model=list[OAuthClientResponse])
def list_clients(
    _admin: SuperAdmin,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client_service: OAuthClientService = Depends(get_oauth_client_service),
) -> list[OAuthClientResponse]:
    return [OAuthClientResponse.model_validate(c) for c in client_service.list_all(limit=limit, offset=offset)]


@router.put("/{client_id}/status", response_model=OAuthClientResponse)
def update_status(
    client_id: int,
    new_status: str,
    _admin: SuperAdmin,
    client_service: OAuthClientService = Depends(get_oauth_client_service),
) -> OAuthClientResponse:
    client = client_service.update_status(client_id, new_status)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户端不存在")
    return OAuthClientResponse.model_validate(client)


@router.post("/{client_id}/regenerate", response_model=OAuthClientSecretResponse)
def regenerate_secret(
    client_id: int,
    _admin: SuperAdmin,
    client_service: OAuthClientService = Depends(get_oauth_client_service),
) -> OAuthClientSecretResponse:
    client, raw_secret = client_service.regenerate_secret(client_id)
    if client is None or raw_secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户端不存在")
    return OAuthClientSecretResponse(client_id=client.client_id, client_secret=raw_secret)
