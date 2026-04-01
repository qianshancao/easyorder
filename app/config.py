from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{Path(__file__).parent.parent / 'data' / 'easyorder.db'}"

    otel_enabled: bool = True

    secret_key: str = "change-me-in-production"  # noqa: S105
    admin_jwt_expire_minutes: int = 60
    api_token_expire_seconds: int = 3600

    super_admin_username: str = "admin"
    super_admin_password: str = "admin123"  # noqa: S105

    model_config = {"env_prefix": "EASYORDER_"}


settings = Settings()
