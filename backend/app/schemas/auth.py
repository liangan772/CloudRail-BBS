"""认证请求 / 响应 Schema。"""

from pydantic import BaseModel, Field


class CaptchaField(BaseModel):
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_code: str = Field(min_length=1, max_length=8)


class RegisterRequest(CaptchaField):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    email: str | None = Field(default=None, max_length=128)


class LoginRequest(CaptchaField):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=1024)


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    avatar_url: str | None = None
    role: int = 0
    points: int = 0
    level: int = 1
    created_at: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair
