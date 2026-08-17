"""FastAPI 应用入口。

安全加固（v0.1.0）：
- 启动时校验 SECRET_KEY 强度（过弱拒绝启动）
- 全局异常收敛（对外统一 500，详情入日志）
- 通用 API 限流（按 IP，每分钟 N 次；认证类接口另有更严限流）
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import init_db
from app.core.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

api_limiter = RateLimiter(limit=settings.api_rate_limit, window=60)

# 放行限流的元信息路径（避免探活/文档被误伤）
_RATE_LIMIT_FREE = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """通用 API 限流：按 IP 每分钟 api_rate_limit 次。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path not in _RATE_LIMIT_FREE and path.startswith("/api/"):
            if not await api_limiter.allow(f"api:{_client_ip(request)}"):
                return JSONResponse(
                    status_code=429,
                    content={"code": 42900, "message": "请求过于频繁，请稍后重试", "data": None},
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 安全启动校验：弱 SECRET_KEY 直接拒绝启动（防 JWT 伪造）
    settings.validate_security()
    # 启动时建表（数据库不可用时自动降级，不阻塞启动）
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudRail Forum API",
        version=__version__,
        description="中文论坛后端 API（开发文档见 docs/开发文档.md）",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"name": "CloudRail Forum API", "version": __version__, "docs": "/docs"}

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """全局异常收敛：对外统一 500，详情记录日志（不泄露内部信息）。"""
        logger.exception("未处理异常: %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"code": 50000, "message": "服务器内部错误", "data": None},
        )

    return app


app = create_app()
