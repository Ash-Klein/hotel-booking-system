"""Password hashing helpers.

Passwords are never stored in plain text. A per-user random salt plus
PBKDF2-HMAC-SHA256 with 120,000 iterations is sufficient for a course project
and avoids adding a third-party crypto dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ITERATIONS = 120_000
SALT_BYTES = 16


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return ``(hash_hex, salt_hex)`` for a password."""
    if not password:
        raise ValueError("密码不能为空")
    salt_hex = salt or secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS
    )
    return digest.hex(), salt_hex


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Constant-time password verification."""
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def new_token(prefix: str = "") -> str:
    """Short, URL-safe identifier used by orders and payments."""
    raw = secrets.token_hex(4).upper()
    return f"{prefix}{raw}"
