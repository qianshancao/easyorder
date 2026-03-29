from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{Path(__file__).parent.parent / 'data' / 'easyorder.db'}"

    otel_enabled: bool = False

    model_config = {"env_prefix": "EASYORDER_"}


settings = Settings()
