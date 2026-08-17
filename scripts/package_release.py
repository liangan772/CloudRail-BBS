#!/usr/bin/env python3
"""CloudRail Forum 发布打包脚本（跨平台，供本地与 CI Release 使用）。

生成发布压缩包（zip + tar.gz）到 release/ 目录，内容为开箱即用的部署包：
    - 前端构建产物 frontend/dist（默认自动执行 npm run build）
    - 后端完整代码（app / alembic / pyproject.toml / run.sh / .env.example）
    - 部署配置（Dockerfile / deploy/ / docs/ / README.md / scripts/）

用法（项目根目录）：
    python scripts/package_release.py            # 打包为 zip + tar.gz
    python scripts/package_release.py --no-build # 跳过前端构建（使用现有 dist）
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
RELEASE_DIR = ROOT / "release"

# 需要打进的顶层内容（相对根目录）
TOP_LEVEL_ITEMS = [
    "README.md",
    "Dockerfile",
    "deploy",
    "docs",
    "backend",
    "frontend",
    "scripts",
]

# 拷贝时忽略的目录/文件（递归）；frontend/dist 需要保留（构建产物）
IGNORE_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", "release", ".idea", ".vscode"}
IGNORE_FILES = {".env", "*.db", "*.pyc", ".DS_Store", "Thumbs.db"}


def get_version() -> str:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (BACKEND / "app" / "__init__.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "0.1.0"


def _should_ignore(name: str, is_dir: bool) -> bool:
    if is_dir and name in IGNORE_DIRS:
        return True
    if not is_dir:
        for pat in IGNORE_FILES:
            if pat.startswith("*") and name.endswith(pat[1:]):
                return True
            if name == pat:
                return True
    return False


def build_frontend() -> None:
    """构建前端产物（dist）。"""
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    print("==> 构建前端（npm run build）")
    code = subprocess.call([npm, "run", "build"], cwd=FRONTEND)
    if code != 0:
        print("前端构建失败，请先手动修复后重试（或使用 --no-build）", file=sys.stderr)
        sys.exit(1)


def stage_release(staging: Path, include_dist: bool) -> None:
    """拷贝发布内容到 staging 目录。"""
    for item in TOP_LEVEL_ITEMS:
        src = ROOT / item
        dst = staging / item
        if src.is_dir():
            shutil.copytree(
                src, dst,
                ignore=lambda d, names: [n for n in names if _should_ignore(n, (Path(d) / n).is_dir())],
            )
            # 前端构建产物（dist）默认包含在发布包中；--no-build 且无产物时跳过
            if item == "frontend" and not include_dist and (dst / "dist").exists():
                shutil.rmtree(dst / "dist")
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser(description="打包 CloudRail Forum 发布压缩包")
    parser.add_argument("--no-build", action="store_true", help="跳过前端构建（使用现有 dist）")
    args = parser.parse_args()

    if not args.no_build:
        build_frontend()
    elif not (FRONTEND / "dist").exists():
        print("警告：frontend/dist 不存在，且使用了 --no-build，发布包将不含前端产物", file=sys.stderr)

    version = get_version()
    base_name = f"forum-v{version}"
    staging = RELEASE_DIR / f".staging-{base_name}"

    print(f"==> 收集发布文件（版本 {version}）")
    if staging.exists():
        shutil.rmtree(staging)
    stage_release(staging, include_dist=(FRONTEND / "dist").exists())

    RELEASE_DIR.mkdir(exist_ok=True)
    print("==> 生成压缩包")
    for fmt in ("zip", "gztar"):
        archive = shutil.make_archive(str(RELEASE_DIR / base_name), fmt, root_dir=RELEASE_DIR, base_dir=staging.name)
        size_mb = Path(archive).stat().st_size / 1024 / 1024
        print(f"    {Path(archive).name} ({size_mb:.1f} MB)")

    shutil.rmtree(staging)
    print(f"\n发布包已生成：{RELEASE_DIR}/  （解压后按 README「手动部署」运行，或用 Docker 部署）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
