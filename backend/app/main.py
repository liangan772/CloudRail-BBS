"""FastAPI 应用入口（已修复异常拦截与安全启动逻辑）。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import init_db
from app.core.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

api_limiter = RateLimiter(limit=settings.api_rate_limit, window=60)

_RATE_LIMIT_FREE = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


def _client_ip(request: Request) -> str:
    """安全获取客户端 IP（默认取真实直连 IP，防止通过自定义请求头伪造 XFF 绕过限流）。"""
    # 如果系统明确部署在反向代理（如 Nginx）后，可从 header 中取最右侧代理提供的 IP；
    # 在未配置受信代理前，最安全的方式是直接使用 socket 直连 IP：
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


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
    # 安全启动校验：生产环境强制，开发环境警告
    settings.validate_security()
    # 启动时建表
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
        """全局非预期异常收敛：放行标准 HTTP 异常与校验异常，其余统一 500。"""
        if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
            raise exc
        logger.exception("未处理内部异常: %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"code": 50000, "message": "服务器内部错误", "data": None},
        )

    return app


app = create_app()