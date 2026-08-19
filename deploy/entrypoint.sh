#!/bin/sh
# 合并镜像启动脚本：同时启动 Nginx（前端 + /api 反代）与 FastAPI 后端
set -e

# 确保数据目录存在（挂载卷首次为空时；卷权限由镜像内 /data 属主继承）
mkdir -p /data/uploads

# Nginx 前台运行
nginx -g 'daemon off;' &

# FastAPI 后端（Nginx 已配置将 /api/* 反代到本机 8000）
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
