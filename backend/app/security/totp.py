import pyotp

from app.services.crypto import decrypt, encrypt


def encrypt_secret(plaintext: str) -> str:
    return encrypt(plaintext)


def decrypt_secret(blob: str) -> str:
    return decrypt(blob)


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="ODIN")


def verify_code(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)
