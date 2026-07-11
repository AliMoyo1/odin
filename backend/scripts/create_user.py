"""
Seed the single ODIN user. No public registration endpoint exists.
Usage: python scripts/create_user.py --email you@example.com --password SECRET
"""
import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import User
from app.security.passwords import hash_password


async def main(email: str, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"User {email} already exists.")
            return

        user = User(email=email, password_hash=hash_password(password))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Created user {email} (id={user.id})")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.email, args.password))
