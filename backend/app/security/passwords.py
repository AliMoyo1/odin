from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or fewer")
    return _ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode("utf-8")) > 72:
        return False
    return _ctx.verify(plain, hashed)
