"""应用配置（pydantic-settings，读取环境变量 / .env）。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 基础
    app_name: str = "CloudRail Forum API"
    debug: bool = False

    # 数据层
    database_url: str = "postgresql+asyncpg://forum:forum@localhost:5432/forum"
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # CORS（逗号分隔）
    cors_origins: str = "http://localhost:5173"

    # 上传
    upload_dir: str = "./uploads"

    # 外部服务（骨架阶段可选）
    sms_provider: str | None = None
    sms_access_key: str | None = None
    sms_secret: str | None = None
    sms_sign_name: str | None = None
    push_provider: str | None = None
    push_app_key: str | None = None
    oauth_wechat_client_id: str | None = None
    oauth_wechat_client_secret: str | None = None
    oauth_qq_client_id: str | None = None
    oauth_qq_client_secret: str | None = None
    oauth_github_client_id: str | None = None
    oauth_github_client_secret: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
