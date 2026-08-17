"""安全工具：JWT 签发/校验、密码哈希（bcrypt）。"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, expires_delta: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": extra.pop("type", "access") if extra else "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: int, role: int = 0, device_id: str | None = None) -> str:
    extra: dict[str, Any] = {"role": role}
    if device_id:
        extra["device_id"] = device_id
    return _create_token(str(user_id), timedelta(minutes=settings.access_token_expire_minutes), extra)


def create_refresh_token(
    user_id: int, device_id: str | None = None, jti: str | None = None
) -> str:
    """签发 Refresh Token（携带 jti，供服务端吊销与轮换，见文档 9.1）。"""
    extra: dict[str, Any] = {"type": "refresh", "jti": jti or uuid.uuid4().hex}
    if device_id:
        extra["device_id"] = device_id
    return _create_token(str(user_id), timedelta(days=settings.refresh_token_expire_days), extra)


def decode_token(token: str) -> dict[str, Any] | None:
    """解析 JWT；无效或过期返回 None。"""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
