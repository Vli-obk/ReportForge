import asyncio
import os

from sqlalchemy import select

from app.core.security import get_password_hash
from app.database.session import AsyncSessionLocal
from app.models.user import User


async def seed_admin() -> None:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    full_name = os.getenv("ADMIN_FULL_NAME", "Admin User").strip() or "Admin User"

    if not email or not password:
        print("Admin seed skipped: ADMIN_EMAIL or ADMIN_PASSWORD not set.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        admin = result.scalars().first()

        if admin:
            changed = False
            if not admin.is_superuser:
                admin.is_superuser = True
                changed = True
            if not admin.is_active:
                admin.is_active = True
                changed = True
            if changed:
                await session.commit()
                print(f"Admin user updated: {email}")
            else:
                print(f"Admin user already configured: {email}")
            return

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
            ocr_enabled=True,
            max_upload_size=50,
            auto_process=True,
        )
        session.add(user)
        await session.commit()
        print(f"Admin user created: {email}")


if __name__ == "__main__":
    asyncio.run(seed_admin())

