"""APP 端专项：bootstrap / 版本管理 / 推送 Token。

TODO（按文档 6.5）：
- GET    /app/bootstrap        启动配置（公告/banner/功能开关/分享文案）
- GET    /app/versions/latest  最新版本
- POST   /app/push-token       注册推送 Token
- DELETE /app/push-token       注销推送 Token
- POST   /uploads/image        图片上传（multipart + 缩略图）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/app", tags=["APP 端"])
