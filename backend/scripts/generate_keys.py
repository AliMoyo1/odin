"""
Generate RS256 keypair + print ENCRYPTION_KEY and SECRET_KEY for .env.
Usage: python scripts/generate_keys.py /keys
"""
import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main():
    key_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/keys")
    private_path = key_dir / "jwt_private.pem"
    public_path = key_dir / "jwt_public.pem"

    if private_path.exists() or public_path.exists():
        print("Keys already exist. Delete them first if you want to regenerate.")
        sys.exit(1)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Keys written to {key_dir}")

    encryption_key = base64.b64encode(os.urandom(32)).decode()
    secret_key = os.urandom(32).hex()

    print("\nAdd these to your .env file:")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print(f"SECRET_KEY={secret_key}")


if __name__ == "__main__":
    main()
