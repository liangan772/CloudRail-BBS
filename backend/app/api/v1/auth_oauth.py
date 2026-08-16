"""认证增强：第三方登录（OAuth2）。

TODO（按文档 6.2 / 9.9）：
- GET  /auth/oauth/{provider}   跳转授权
- POST /auth/oauth/{provider}   授权回调（校验 state 防 CSRF）
- POST /auth/oauth/bind         绑定第三方账号
- DELETE /auth/oauth/{provider} 解绑
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["认证-第三方登录"])
