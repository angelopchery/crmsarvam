"""
Script to create an initial admin user.

Run this after setting up the database to create the first admin account.
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User


async def create_admin_user(username: str, password: str):
    """Create an admin user."""
    async with async_session_maker() as db:
        # Check if user already exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User '{username}' already exists!")
            return False

        # Create admin user
        admin = User(
            username=username,
            hashed_password=get_password_hash(password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()

        print(f"Admin user '{username}' created successfully!")
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--username", "-u", default="admin", help="Username for admin")
    parser.add_argument("--password", "-p", default="admin123", help="Password for admin")

    args = parser.parse_args()

    print(f"Creating admin user: {args.username}")
    asyncio.run(create_admin_user(args.username, args.password))
