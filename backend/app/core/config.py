"""应用配置（pydantic-settings，读取环境变量 / .env）。"""

from functools import lru_cache
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # 安全（v0.1.0 加固）
    # 首个注册用户自动成为管理员（生产环境请设为 false，用引导脚本创建管理员）
    admin_bootstrap: bool = True
    # 通用 API 限流（每分钟每 IP 请求上限）
    api_rate_limit: int = 120
    # 登录/注册/验证码接口限流
    auth_rate_limit: int = 5
    auth_rate_window: int = 60

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

    # AI 自动审核（OpenAI 兼容协议：DeepSeek / 通义千问 / 智谱等）
    ai_enabled: bool = False
    ai_mode: str = "llm"  # llm=真实调用 / mock=确定性模拟（本地演示与自动化测试，无需 API Key）
    ai_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"
    ai_vision_model: str = ""  # 图片审核视觉模型（如 qwen-vl-max / gpt-4o-mini）；留空则回退用 ai_model
    ai_audit_mode: str = "async"  # sync / async / off
    ai_audit_threshold: float = 0.6  # score >= 阈值判定违规
    ai_timeout: float = 30.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_security(self) -> None:
        """启动安全校验：生产环境下 SECRET_KEY 必须是强密钥。"""
        is_weak = len(self.secret_key) < 32 or self.secret_key in (
            "change-me",
            "change-me-to-a-random-64-byte-secret",
        )
        if is_weak:
            if not self.debug:
                raise RuntimeError(
                    "生产环境 SECRET_KEY 过弱：请配置至少 32 字符的随机密钥"
                    "（python -c \"import secrets; print(secrets.token_urlsafe(48))\"）"
                )
            logger.warning("[SECURITY] 当前处于 Debug/开发环境，正在使用弱密钥，生产环境请务必更换！")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
