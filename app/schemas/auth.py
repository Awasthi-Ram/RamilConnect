"""Auth schemas — registration, login, and token responses."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    dob: str = Field(description="Date of birth in ISO format (YYYY-MM-DD)")
    gender: str = Field(description="Gender: male, female, non-binary, other")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserBasic
    tokens: TokenResponse


class UserBasic(BaseModel):
    id: int
    email: str
    name: str
    onboarding_complete: bool
    companion_persona: str
    companion_name: str | None = None

    class Config:
        from_attributes = True
