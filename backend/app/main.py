"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudRail Forum API",
        version=__version__,
        description="中文论坛后端 API（开发文档见 docs/开发文档.md）",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"name": "CloudRail Forum API", "version": __version__, "docs": "/docs"}

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        # 骨架阶段：仅返回进程状态；数据库连通性检查待接入 DB 后补充
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
