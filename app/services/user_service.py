"""
User management service for CRUD operations.
"""
import logging
from typing import Optional, List

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """Service for handling user CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize UserService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_user(self, user_id: int) -> Optional[UserResponse]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User response or None
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return UserResponse.model_validate(user) if user else None

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[str] = None,
    ) -> UserListResponse:
        """
        Get paginated list of users.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            role: Optional role filter

        Returns:
            Paginated user list response
        """
        # Build query
        query = select(User)
        if role:
            query = query.where(User.role == role)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get users with pagination
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.db.execute(query)
        users = result.scalars().all()

        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

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

    async def update_user(
        self, user_id: int, user_data: UserUpdate
    ) -> Optional[UserResponse]:
        """
        Update an existing user.

        Args:
            user_id: User ID
            user_data: User update data

        Returns:
            Updated user response or None

        Raises:
            ValueError: If user not found
        """
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Update fields
        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)
        if user_data.role:
            user.role = user_data.role
        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"User updated: {user.username}")
        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            delete(User).where(User.id == user_id)
        )
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"User deleted: {user_id}")

        return deleted

    async def count_users(self) -> int:
        """
        Count total users in the database.

        Returns:
            Number of users
        """
        result = await self.db.execute(select(func.count()).select_from(User))
        return result.scalar() or 0
