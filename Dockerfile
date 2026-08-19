# CloudRail Forum 单容器全栈镜像：Nginx + FastAPI + PostgreSQL + Redis + Celery Worker
# 构建：docker build -t forum:latest .   （context = 仓库根目录）
# 运行：一个容器内由 supervisord 管理全部进程（v1.6）
#   - nginx :8080（前端静态 + /api 反代）
#   - uvicorn :8000（FastAPI）
#   - postgres :5432（数据 /data/postgres，仅监听容器内 127.0.0.1）
#   - redis :6379（数据 /data/redis，仅监听容器内 127.0.0.1）
#   - celery worker（AI 审核异步任务，broker/backend = 容器内 Redis）
# 安全说明：supervisord 以 root 启动以拉起 postgres（必须 setuid postgres）；
#   nginx/uvicorn/celery 均以非 root 用户运行；PG/Redis 不对外暴露端口。

# ---------- 阶段 1：构建前端静态资源 ----------
FROM node:22-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：运行镜像（Python + Nginx + PostgreSQL + Redis + Supervisor） ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 安装 Nginx / PostgreSQL / Redis / Supervisor / procps（pg_ctl 需要）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx postgresql redis-server supervisor procps \
    && rm -rf /var/lib/apt/lists/*

# 清理发行版默认数据目录（首次启动由 pg_init.sh 初始化到 /data/postgres）
RUN rm -rf /var/lib/postgresql/15/main /var/lib/redis/* \
    && mkdir -p /run/postgresql && chown postgres:postgres /run/postgresql

WORKDIR /app

# 后端：依赖 + 代码
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
RUN pip install --no-cache-dir .

# 前端静态资源 + Nginx 配置 + 进程编排与初始化脚本
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY deploy/nginx/forum.conf /etc/nginx/conf.d/default.conf
COPY deploy/supervisord.conf /etc/supervisor/conf.d/forum.conf
COPY deploy/redis.conf /etc/forum-redis.conf
COPY deploy/pg_init.sh /pg_init.sh
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /pg_init.sh

# 非 root 应用用户（uvicorn / nginx / celery 使用）——必须先创建，后续 chown 才能引用
RUN useradd --create-home --uid 1000 forum

# 数据目录（挂载卷 /data）：postgres / redis / uploads
RUN mkdir -p /data/postgres /data/redis /data/uploads \
    && chown -R postgres:postgres /data/postgres \
    && chown -R redis:redis /data/redis \
    && chown -R forum:forum /data/uploads \
    && chown -R forum:forum /app /usr/share/nginx/html

EXPOSE 8080

CMD ["/entrypoint.sh"]
