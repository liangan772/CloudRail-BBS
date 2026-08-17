# CloudRail Forum 合并镜像：Nginx（前端静态 + 反代 /api）+ FastAPI 后端
# 构建：docker build -t forum:latest .   （context = 仓库根目录）
# 运行：一个容器同时提供 http://<host>/（前端）与 http://<host>/api/（后端 API）

# ---------- 阶段 1：构建前端静态资源 ----------
FROM node:22-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：运行镜像（Python + Nginx） ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 安装 Nginx（用于托管前端静态资源并反向代理 /api）
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 后端：依赖 + 代码 + 迁移
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
RUN pip install --no-cache-dir .

# 前端静态资源 + Nginx 配置 + 启动脚本
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY deploy/nginx/forum.conf /etc/nginx/conf.d/default.conf
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

CMD ["/entrypoint.sh"]
