"""Password verification and role-based access for operator actions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import get_settings
from app.db.enums import UserRole
from app.errors import AuthenticationError, AuthorizationError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash suitable for the users.password_hash column."""
    if len(password) < 12:
        raise ValueError("Operator passwords must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return "$".join(
        (
            PASSWORD_HASH_SCHEME,
            str(PASSWORD_HASH_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify only supported PBKDF2 hashes; reject legacy/plaintext placeholders."""
    try:
        scheme, iterations_text, salt_text, digest_text = encoded_hash.split("$", 3)
        iterations = int(iterations_text)
        if scheme != PASSWORD_HASH_SCHEME or not 100_000 <= iterations <= 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def _signing_secret() -> tuple[str, str, int]:
    settings = get_settings()
    secret = settings.jwt_secret
    if not secret or len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operator authentication is unavailable until JWT_SECRET is configured with at least 32 characters.",
        )
    return secret, settings.jwt_algorithm, settings.jwt_expiry_minutes


def create_token(subject: str, role: str) -> str:
    secret, algorithm, expiry_minutes = _signing_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "exp": now + timedelta(minutes=expiry_minutes),
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str) -> dict:
    secret, algorithm, _ = _signing_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise AuthenticationError("Invalid token subject")
        if payload.get("role") not in {role.value for role in UserRole}:
            raise AuthenticationError("Invalid token role")
        return payload
    except jwt.ExpiredSignatureError as error:
        raise AuthenticationError("Token has expired") from error
    except jwt.PyJWTError as error:
        raise AuthenticationError("Invalid token") from error


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)


def require_role(allowed_roles: list[UserRole]) -> Callable:
    allowed_values = {role.value for role in allowed_roles}

    def role_dependency(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_values:
            raise AuthorizationError("Insufficient permissions")
        return user

    return role_dependency


OPERATOR_ROLES = [UserRole.EMERGENCY_COORDINATOR, UserRole.ADMINISTRATOR]
