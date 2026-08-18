"""认证：图形验证码 / 注册 / 登录 / 刷新 / 登出。

安全加固（v0.1.0）：
- 登录/注册/验证码接口按 IP 限流（Redis/内存，见 core.rate_limit）
- 登出吊销服务端 Refresh Token（见 services.auth）
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.rate_limit import RateLimiter
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from app.services import auth as auth_service
from app.services import captcha as captcha_service

router = APIRouter(prefix="/auth", tags=["认证"])

_login_limiter = RateLimiter(limit=settings.auth_rate_limit, window=settings.auth_rate_window)
_register_limiter = RateLimiter(limit=settings.auth_rate_limit, window=settings.auth_rate_window)
_captcha_limiter = RateLimiter(limit=30, window=60)


def _client_ip(request: Request) -> str:
    """安全获取客户端 IP（默认取真实直连 IP，防止通过自定义请求头伪造 XFF 绕过限流）。"""
    # 如果系统明确部署在反向代理（如 Nginx）后，可从 header 中取最右侧代理提供的 IP；
    # 在未配置受信代理前，最安全的方式是直接使用 socket 直连 IP：
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.get("/captcha", summary="获取图形验证码", response_model=dict)
async def get_captcha(request: Request) -> dict:
    """生成验证码（SVG base64 + captcha_id），注册/登录/发帖/评论前调用。"""
    if not await _captcha_limiter.allow(f"captcha:{_client_ip(request)}"):
        raise HTTPException(status_code=429, detail="验证码获取过于频繁，请稍后再试")
    return await captcha_service.create_captcha()


@router.post("/register", summary="注册（含验证码）", response_model=dict)
async def register(payload: RegisterRequest, request: Request, session: AsyncSession = Depends(get_db)) -> dict:
    if not await _register_limiter.allow(f"register:{_client_ip(request)}"):
        raise HTTPException(status_code=429, detail="注册过于频繁，请稍后再试")
    if not await captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    data = await auth_service.register(session, payload.username, payload.password, payload.email)
    return {"code": 0, "message": "注册成功", "data": data}


@router.post("/login", summary="登录（含验证码）", response_model=dict)
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_db)) -> dict:
    if not await _login_limiter.allow(f"login:{_client_ip(request)}"):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请 60 秒后再试")
    if not await captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    data = await auth_service.login(session, payload.username, payload.password)
    return {"code": 0, "message": "登录成功", "data": data}


@router.post("/refresh", summary="刷新 Access Token（Refresh 轮换）", response_model=dict)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db)) -> dict:
    data = await auth_service.refresh(session, payload.refresh_token)
    return {"code": 0, "message": "ok", "data": data}


@router.post("/logout", summary="登出（吊销 Refresh Token）")
async def logout(
    payload: RefreshRequest | None = Body(None),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    await auth_service.logout(payload.refresh_token if payload else None)
    return {"code": 0, "message": "已登出", "data": None}
