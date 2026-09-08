import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from app.core.config import settings

_ALGORITHM = "sha256"
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _ALGORITHM,
        password.encode("utf-8"),
        salt,
        settings.PASSWORD_HASH_ITERATIONS,
    )
    return f"pbkdf2_{_ALGORITHM}${settings.PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = password_hash.split("$")
        digest = hashlib.pbkdf2_hmac(
            _ALGORITHM,
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(digest.hex(), digest_hex)


def create_access_token(
    *,
    user_id: UUID,
    email: str,
    role: str,
    organization_id: UUID | None = None,
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expires_at,
    }
    if organization_id is not None:
        payload["org"] = str(organization_id)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def generate_otp(*, length: int = 6) -> str:
    """Generate a numeric one-time password (default 6 digits)."""
    if length < 4 or length > 12:
        raise ValueError("OTP length must be between 4 and 12")
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_otp(otp: str) -> str:
    """Normalize and hash an OTP for storage lookup."""
    return hash_password_reset_token(otp.strip())
