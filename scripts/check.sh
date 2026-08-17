#!/usr/bin/env bash
# 检查后端代码：编译 + ruff 规范检查
set -euo pipefail
cd "$(dirname "$0")/.."

PY=backend/.venv/Scripts/python
if [ ! -x "$PY" ]; then
  PY=python
fi

echo "==> 语法检查"
"$PY" -m compileall -q backend/app backend/tests

echo "==> pytest"
(cd backend && "$PY" -m pytest -q)

echo "==> ruff"
(cd backend && "$PY" -m ruff check app tests || true)
