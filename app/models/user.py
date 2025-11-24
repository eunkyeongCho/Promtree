from beanie import Document
from pydantic import EmailStr, Field
from typing import Optional


class User(Document):
    email: EmailStr = Field(..., unique=True)
    username: str
    hashed_password: str
    theme: str = "light"  # "light" or "dark"
    language: str = "ko"  # "ko" or "en"

    class Settings:
        name = "users"
        indexes = [
            "email",
        ]
