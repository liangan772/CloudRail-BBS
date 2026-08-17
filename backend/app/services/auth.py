"""认证服务：注册 / 登录 / 刷新 / 登出。"""

import logging

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User

logger = logging.getLogger(__name__)


def _tokens_for(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
    }


async def register(
    session: AsyncSession, username: str, password: str, email: str | None = None
) -> dict:
    username = username.strip()
    if len(username) < 2 or len(username) > 32:
        raise HTTPException(status_code=400, detail="用户名长度需为 2-32 位")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    exists = await session.scalar(select(func.count()).select_from(User).where(User.username == username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if email:
        exists_email = await session.scalar(select(func.count()).select_from(User).where(User.email == email))
        if exists_email:
            raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 首个注册用户自动成为管理员（演示/初始化用；生产可通过后台手动授权）
    user_count = await session.scalar(select(func.count()).select_from(User))
    role = 2 if user_count == 0 else 0

    user = User(
        username=username,
        email=email or None,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("新用户注册: id=%s username=%s role=%s", user.id, user.username, user.role)

    return {"user": _user_out(user), "tokens": _tokens_for(user)}


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
    return {"user": _user_out(user), "tokens": _tokens_for(user)}


async def refresh(session: AsyncSession, refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh Token 无效或已过期")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh Token 无效") from None
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"user": _user_out(user), "tokens": _tokens_for(user)}


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
