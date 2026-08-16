"""认证增强：短信验证码。

TODO（按文档 6.2 / 9.8）：
- POST /auth/sms-code       发送验证码（图形验证码前置 + 多级限频）
- POST /auth/login/sms      手机号 + 验证码登录（未注册自动注册）
- POST /auth/password/forgot-code  发送找回密码验证码
- PUT  /auth/password/reset 验证码重置密码
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["认证-短信"])
