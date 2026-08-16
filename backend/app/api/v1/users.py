"""用户。

TODO（按文档 6.2）：
- GET  /users/me            当前用户信息
- PUT  /users/me            修改资料
- PUT  /users/me/password   修改密码
- POST /users/me/avatar     上传头像
- PUT  /users/me/phone      绑定/换绑手机号
- PUT  /users/me/email      绑定/换绑邮箱
- GET  /users/{id}          用户主页
- POST /users/{id}/follow   关注/取关
- GET  /users/{id}/followers 粉丝列表
"""

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["用户"])
