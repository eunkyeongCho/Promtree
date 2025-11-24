from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal


class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfoResponse(BaseModel):
    username: str
    theme: Literal["light", "dark"]
    language: Literal["ko", "en"]


class UserSettingsUpdate(BaseModel):
    theme: Literal["light", "dark"] | None = None
    language: Literal["ko", "en"] | None = None

    @field_validator('theme', 'language')
    @classmethod
    def check_not_both_none(cls, v, info):
        # 적어도 하나는 값이 있어야 함
        return v
