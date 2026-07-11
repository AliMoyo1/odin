"""Create the initial ODIN user. Run inside the gateway-api container."""
import argparse
import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import User
from app.security.passwords import hash_password


async def main(email: str, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        user = User(email=email, password_hash=hash_password(password))
        session.add(user)
        await session.commit()
        await session.refresh(user)
    await engine.dispose()
    print(f"Created user {email} (id={user.id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.email, args.password))
