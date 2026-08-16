"""认证增强：设备 / 多端会话管理。

TODO（按文档 6.2 / 9.1）：
- GET    /auth/devices        设备列表
- DELETE /auth/devices/{id}   踢下线（递增 session:dev:{device_id} 版本号）
- POST   /auth/scan/qrcode    扫码登录二维码
- GET    /auth/scan/status    轮询扫码状态
- POST   /auth/scan/confirm   App 端确认扫码
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["认证-设备会话"])
