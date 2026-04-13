"""
Pydantic schemas for User model.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base schema for User."""

    username: str = Field(..., min_length=3, max_length=50)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    password: Optional[str] = Field(None, min_length=8, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserWithToken(UserResponse):
    """Schema for user response with authentication token."""

    access_token: str
    token_type: str = "bearer"


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
