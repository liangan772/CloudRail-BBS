"""认证：账号密码注册 / 登录 / 刷新 / 登出。

TODO（按文档 6.2）：
- POST /auth/register    注册（含图形验证码）
- POST /auth/login       登录，返回双 Token
- POST /auth/refresh     刷新 Access Token（Refresh Token 轮换）
- POST /auth/logout      登出（吊销 Refresh Token）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["认证"])
