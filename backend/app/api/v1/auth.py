"""认证：图形验证码 / 注册 / 登录 / 刷新 / 登出。

按文档 6.2 实现；验证码覆盖注册、登录（发帖/评论见 posts 模块）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from app.services import auth as auth_service
from app.services import captcha as captcha_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/captcha", summary="获取图形验证码", response_model=dict)
async def get_captcha() -> dict:
    """生成验证码（SVG base64 + captcha_id），注册/登录/发帖/评论前调用。"""
    return captcha_service.create_captcha()


@router.post("/register", summary="注册（含验证码）", response_model=dict)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)) -> dict:
    if not captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    data = await auth_service.register(session, payload.username, payload.password, payload.email)
    return {"code": 0, "message": "注册成功", "data": data}


@router.post("/login", summary="登录（含验证码）", response_model=dict)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> dict:
    if not captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    data = await auth_service.login(session, payload.username, payload.password)
    return {"code": 0, "message": "登录成功", "data": data}


@router.post("/refresh", summary="刷新 Access Token", response_model=dict)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db)) -> dict:
    data = await auth_service.refresh(session, payload.refresh_token)
    return {"code": 0, "message": "ok", "data": data}


@router.post("/logout", summary="登出")
async def logout(_user: CurrentUser = Depends(get_current_user)) -> dict:
    # 骨架：JWT 无状态，前端清除本地凭证即可；生产可吊销 Refresh Token（见文档 9.1）
    return {"code": 0, "message": "已登出", "data": None}
