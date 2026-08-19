"""FastAPI 应用入口（完整修复版）。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
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
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """通用 API 限流：放行 OPTIONS 预检请求，防止破坏跨域规范。"""

    async def dispatch(self, request: Request, call_next):
        # 放行 OPTIONS 预检请求与免限流路径
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if path not in _RATE_LIMIT_FREE and path.startswith("/api/"):
            if not await api_limiter.allow(f"api:{_client_ip(request)}"):
                origin = request.headers.get("origin", "")
                headers = {}
                # 确保 429 响应带上 CORS 头，避免前端抛出跨域错误
                if origin and (origin in settings.cors_origin_list or "*" in settings.cors_origin_list):
                    headers["Access-Control-Allow-Origin"] = origin
                    headers["Access-Control-Allow-Credentials"] = "true"
                return JSONResponse(
                    status_code=429,
                    content={"code": 42900, "message": "请求过于频繁，请稍后重试", "data": None},
                    headers=headers,
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_security()
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudRail Forum API",
        version=__version__,
        description="中文论坛后端 API",
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
    async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            return await http_exception_handler(request, exc)
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        logger.exception("未处理内部异常: %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"code": 50000, "message": "服务器内部错误", "data": None},
        )

    return app


app = create_app()