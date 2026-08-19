#!/bin/sh
# 单容器启动脚本：初始化 PostgreSQL（首次）→ supervisord 管理全部进程
set -e

# 确保数据目录存在（挂载卷首次为空时）
mkdir -p /data/postgres /data/redis /data/uploads
chown postgres:postgres /data/postgres
chown redis:redis /data/redis 2>/dev/null || true
chown forum:forum /data/uploads

# 首次初始化 PostgreSQL（幂等）
/pg_init.sh

# supervisord 前台运行（postgres/redis/nginx/uvicorn/celery）
exec supervisord -c /etc/supervisor/supervisord.conf
