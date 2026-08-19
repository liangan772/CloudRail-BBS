#!/bin/sh
# PostgreSQL 首次初始化（幂等）：数据目录 /data/postgres + 应用库 forum
# 仅首次（/data/postgres/PG_VERSION 不存在）执行；失败即退出（由 supervisord 启动流程暴露）。
set -e

PGBIN=/usr/lib/postgresql/15/bin

if [ -f /data/postgres/PG_VERSION ]; then
    echo "[pg_init] 数据目录已初始化，跳过"
    exit 0
fi

echo "[pg_init] 首次初始化 PostgreSQL 数据目录..."
mkdir -p /data/postgres
chown -R postgres:postgres /data/postgres

# initdb：超级用户 forum，本地 trust 认证（仅容器内 127.0.0.1 可访问）
su postgres -c "$PGBIN/initdb -D /data/postgres -U forum --auth=trust -E UTF8"

# 临时启动，创建应用库后关闭
su postgres -c "$PGBIN/pg_ctl -D /data/postgres -o '-c listen_addresses=127.0.0.1 -p 5432 -c unix_socket_directories=/run/postgresql' -l /tmp/pg_init.log -w start"
su postgres -c "$PGBIN/psql -h 127.0.0.1 -U forum -d postgres -c 'CREATE DATABASE forum OWNER forum;'"
su postgres -c "$PGBIN/pg_ctl -D /data/postgres -m fast stop"

echo "[pg_init] PostgreSQL 初始化完成（库 forum，用户 forum）"
