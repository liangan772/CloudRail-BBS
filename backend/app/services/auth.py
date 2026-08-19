"""认证服务：注册 / 登录 / 刷新（吊销+轮换）/ 登出。

安全加固（v0.1.0）：
- 密码策略：6-64 位且同时包含字母与数字
- 注册错误收敛：不区分「用户名已存在 / 邮箱已被注册」，返回统一提示
- 管理员引导：仅 ADMIN_BOOTSTRAP=true（默认）时首用户为管理员
- Refresh Token：服务端登记 jti（Redis/内存），登出吊销；刷新时轮换（旧 token 作废）
"""

import logging
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis, memory_store
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User

logger = logging.getLogger(__name__)

_REFRESH_PREFIX = "refresh:"


# ---------- Refresh Token 服务端登记（吊销 / 轮换） ----------

async def _save_refresh(jti: str, user_id: int) -> None:
    ttl = settings.refresh_token_expire_days * 86400
    redis = await get_redis()
    if redis is not None:
        try:
            await redis.setex(f"{_REFRESH_PREFIX}{jti}", ttl, str(user_id))
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 登记 Refresh Token 失败，降级内存: %s", exc)
    memory_store.set(f"{_REFRESH_PREFIX}{jti}", user_id, ttl=ttl)


async def _check_refresh(jti: str, user_id: int) -> bool:
    redis = await get_redis()
    if redis is not None:
        try:
            raw = await redis.get(f"{_REFRESH_PREFIX}{jti}")
            return raw is not None and int(raw) == user_id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 校验 Refresh Token 失败，降级内存: %s", exc)
    return memory_store.get(f"{_REFRESH_PREFIX}{jti}") == user_id


async def _revoke_refresh(jti: str) -> None:
    redis = await get_redis()
    if redis is not None:
        try:
            await redis.delete(f"{_REFRESH_PREFIX}{jti}")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 吊销 Refresh Token 失败，降级内存: %s", exc)
    memory_store.delete(f"{_REFRESH_PREFIX}{jti}")


async def revoke_user_refresh_tokens(user_id: int) -> None:
    """吊销用户全部 Refresh Token（同时清理 Redis 与进程内内存存储）。"""
    # 1. 清理 Redis
    redis = await get_redis()
    if redis is not None:
        try:
            keys = []
            async for key in redis.scan_iter(f"{_REFRESH_PREFIX}*"):
                raw = await redis.get(key)
                if raw is not None and int(raw) == user_id:
                    keys.append(key)
            if keys:
                await redis.delete(*keys)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 批量吊销 Refresh Token 失败: %s", exc)

    # 2. 清理内存降级存储（确保单机/测试模式下也能被彻底注销）
    with memory_store._lock:
        keys_to_del = [
            k for k, (_, uid) in memory_store._data.items()
            if k.startswith(_REFRESH_PREFIX) and uid == user_id
        ]
        for k in keys_to_del:
            memory_store._data.pop(k, None)


# ---------- 注册 / 登录 / 刷新 ----------


def _validate_password(password: str) -> None:
    if len(password) < 6 or len(password) > 64:
        raise HTTPException(status_code=400, detail="密码长度需为 6-64 位")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="密码需同时包含字母和数字")


def _tokens_for(user: User, jti: str | None = None) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id, jti=jti),
    }


async def register(
    session: AsyncSession, username: str, password: str, email: str | None = None
) -> dict:
    username = username.strip()
    if len(username) < 2 or len(username) > 32:
        raise HTTPException(status_code=400, detail="用户名长度需为 2-32 位")
    _validate_password(password)
    email = (email or "").strip() or None

    exists = await session.scalar(select(func.count()).select_from(User).where(User.username == username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名或邮箱不可用")
    if email:
        exists_email = await session.scalar(select(func.count()).select_from(User).where(User.email == email))
        if exists_email:
            raise HTTPException(status_code=400, detail="用户名或邮箱不可用")

    # 管理员引导：仅配置开启时，首个注册用户为管理员（生产请关闭，见 config.admin_bootstrap）
    user_count = await session.scalar(select(func.count()).select_from(User))
    role = 2 if settings.admin_bootstrap and user_count == 0 else 0

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    jti = uuid.uuid4().hex
    await _save_refresh(jti, user.id)
    logger.info("新用户注册: id=%s username=%s role=%s", user.id, user.username, user.role)
    return {"user": _user_out(user), "tokens": _tokens_for(user, jti=jti)}


async def login(session: AsyncSession, username: str, password: str) -> dict:
    user = await session.scalar(select(User).where(User.username == username.strip()))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.status == 2:
        raise HTTPException(status_code=403, detail="账号已被封禁")
    if user.status == 1:
        raise HTTPException(status_code=403, detail="账号已被禁言")

    user.last_login_at = func.now()
    await session.commit()

    jti = uuid.uuid4().hex
    await _save_refresh(jti, user.id)
    return {"user": _user_out(user), "tokens": _tokens_for(user, jti=jti)}


async def refresh(session: AsyncSession, refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh Token 无效或已过期")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh Token 无效") from None
    jti = payload.get("jti")

    # 服务端登记校验（登出/吊销后不可再用）
    if not jti or not await _check_refresh(str(jti), user_id):
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.status == 2:
        raise HTTPException(status_code=403, detail="账号已被封禁")

    # 轮换：旧 Refresh Token 立即作废，签发新 Token
    await _revoke_refresh(str(jti))
    new_jti = uuid.uuid4().hex
    await _save_refresh(new_jti, user.id)
    return {"user": _user_out(user), "tokens": _tokens_for(user, jti=new_jti)}


async def logout(refresh_token: str | None = None) -> None:
    """登出：吊销 Refresh Token（无 token 时仅前端清理凭证）。"""
    if not refresh_token:
        return
    payload = decode_token(refresh_token)
    if payload and payload.get("type") == "refresh" and payload.get("jti"):
        await _revoke_refresh(str(payload["jti"]))


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "points": user.points,
        "level": user.level,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
