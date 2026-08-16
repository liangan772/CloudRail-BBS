"""FastAPI 依赖注入：当前用户解析等。"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """骨架阶段的当前用户对象；接入数据库模型后替换为 ORM 实体。"""

    id: int
    role: int = 0
    device_id: str | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效") from None
    return CurrentUser(id=user_id, role=int(payload.get("role", 0)), device_id=payload.get("device_id"))


def require_role(min_role: int):
    """角色校验：0 普通 / 1 版主 / 2 管理员。"""

    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role < min_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
        return user

    return checker
