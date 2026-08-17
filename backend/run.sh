#!/usr/bin/env bash
# CloudRail Forum 后端开发启动脚本（Git Bash / Linux / macOS）
# 用法：./run.sh [额外 uvicorn 参数，如 --host 0.0.0.0]
set -euo pipefail
cd "$(dirname "$0")"

# 首次运行提示
if [ ! -f .env ]; then
  echo "[run.sh] 未找到 .env，正在从 .env.example 复制..."
  cp .env.example .env
  echo "[run.sh] 请编辑 .env 填写数据库/Redis/密钥配置后重新运行。"
  exit 1
fi

# 选择 Python：优先 venv，缺失时给出指引而不是静默回退
if [ -x ".venv/Scripts/python" ]; then
  PY=".venv/Scripts/python"
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  echo "[run.sh] 未找到虚拟环境 .venv，请先执行："
  echo "    python -m venv .venv"
  echo "    ./.venv/Scripts/python -m pip install -e \".[dev]\"   # Windows"
  echo "    ./.venv/bin/python -m pip install -e \".[dev]\"       # Linux/macOS"
  exit 1
fi

echo "[run.sh] 加载 .env 并启动 uvicorn..."
# 加载 .env 到进程环境（UVICORN_* 变量对 uvicorn 生效）
set -a
# shellcheck disable=SC1091
source .env
set +a

exec "$PY" -m uvicorn app.main:app "$@"
