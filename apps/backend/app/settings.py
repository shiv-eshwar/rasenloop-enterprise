from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rasen_api_base: str = "https://api.rasen.ai/v1"
    rasen_api_key: str = ""
    rasen_transport: str = "fake"  # fake | live
    database_url: str = "sqlite:///./rasenloop.db"
    public_base_url: str = "http://localhost:8000"
    webhook_signing_secret: str = "whsec_dev_replace_me"
    mcp_auth_token: str = "mcp-dev-token"
    war_room_password: str = "dev"
    control_plane_auto_eval: bool = True
    chaos_mode: bool = False
    refund_secret_id: str = ""
    refund_secret_version: int = 1
    agent_id: str = ""
    pre_call_deadline_ms: int = 800


@lru_cache
def get_settings() -> Settings:
    return Settings()
