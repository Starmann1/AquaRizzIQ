from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.config import get_settings
from app.errors import AuthenticationError, AuthorizationError
from app.db.enums import UserRole

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def create_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)

def require_role(allowed_roles: List[UserRole]):
    def role_dependency(user: dict = Depends(get_current_user)):
        user_role = user.get("role")
        if not user_role or user_role not in [r.value for r in allowed_roles]:
            raise AuthorizationError("Insufficient permissions")
        return user
    return role_dependency
