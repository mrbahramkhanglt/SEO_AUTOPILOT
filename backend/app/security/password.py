"""Password hashing utilities (bcrypt direct – no passlib)."""
from __future__ import annotations

import re

import bcrypt

# bcrypt truncates at 72 bytes
_MAX_PASSWORD_BYTES = 72
_MIN_PASSWORD_LEN = 8


def validate_password_strength(password: str) -> None:
    """Raise ValueError if password is too weak."""
    if not password or len(password) < _MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {_MIN_PASSWORD_LEN} characters")
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long")
    # Require mixed character classes for production-grade accounts
    classes = sum(
        [
            bool(re.search(r"[a-z]", password)),
            bool(re.search(r"[A-Z]", password)),
            bool(re.search(r"\d", password)),
            bool(re.search(r"[^A-Za-z0-9]", password)),
        ]
    )
    if classes < 2:
        raise ValueError(
            "Password must include at least two of: lowercase, uppercase, digit, symbol"
        )


def hash_password(password: str) -> str:
    validate_password_strength(password)
    raw = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        raw = plain.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        return bcrypt.checkpw(raw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
