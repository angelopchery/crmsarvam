"""
Authentication router for login and token management.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.schemas.user import UserCreate, UserLogin, UserWithToken, UserResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Dependency to get current authenticated user from token.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        Current user response

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Get user ID from payload
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return UserResponse.model_validate(user)


async def get_current_admin_user(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Dependency to get current authenticated admin user.

    Args:
        current_user: Current user from get_current_user
        db: Database session

    Returns:
        Current admin user response

    Raises:
        HTTPException: If user is not an admin
    """
    auth_service = AuthService(db)
    is_admin = await auth_service.is_admin(current_user.id)

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user.

    Anyone can register. New users are created with 'user' role by default.
    Admin users must be created by an existing admin.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user response

    Raises:
        HTTPException: If registration fails
    """
    auth_service = AuthService(db)

    try:
        user = await auth_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=UserWithToken)
async def login(
    login_data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate user and return access token.

    Args:
        login_data: User login credentials
        db: Database session

    Returns:
        User response with access token
    """
    auth_service = AuthService(db)

    try:
        user_with_token = await auth_service.authenticate_user(login_data)
        return user_with_token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user response
    """
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout user (client-side token invalidation).

    Note: This is a placeholder. JWT tokens are stateless and cannot be
    invalidated on the server side without a blacklist. In production,
    implement token blacklisting or use refresh tokens.
    """
    return {"message": "Successfully logged out"}
