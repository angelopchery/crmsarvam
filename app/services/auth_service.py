"""
Authentication service for user management and JWT handling.
"""
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserWithToken, UserLogin

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize AuthService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user response

        Raises:
            ValueError: If username already exists
        """
        # Check if username exists
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise ValueError("Username already exists")

        # Create new user
        user = User(
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role,
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"User created: {user.username}")
        return UserResponse.model_validate(user)

    async def authenticate_user(self, login_data: UserLogin) -> UserWithToken:
        """
        Authenticate user with username and password.

        Args:
            login_data: User login credentials

        Returns:
            User response with access token

        Raises:
            ValueError: If credentials are invalid
        """
        # Get user by username
        result = await self.db.execute(
            select(User).where(User.username == login_data.username)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Invalid username or password")

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise ValueError("Invalid username or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is inactive")

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role}
        )

        logger.info(f"User authenticated: {user.username}")

        return UserWithToken(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            access_token=access_token,
        )

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def is_admin(self, user_id: int) -> bool:
        """
        Check if user is an admin.

        Args:
            user_id: User ID

        Returns:
            True if user is admin, False otherwise
        """
        user = await self.get_user_by_id(user_id)
        return user is not None and user.role == "admin"
