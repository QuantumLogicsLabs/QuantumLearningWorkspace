import os
from typing import Optional
from datetime import datetime, timedelta, timezone
import bcrypt

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is missing! Server halting.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY")
if not INTERNAL_SERVICE_KEY:
    raise RuntimeError("INTERNAL_SERVICE_KEY environment variable is missing! Server halting.")

bearer_scheme = HTTPBearer()


def hash_password(plain_password: str) -> str:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT token and return payload dictionary or None if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Verify the JWT token and return the email it belongs to."""
    credentials_error = HTTPException(
        status_code=401,
        detail="Could not validate credentials.",
    )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None or not isinstance(email, str):
            raise credentials_error
        return email
    except JWTError:
        raise credentials_error


def verify_internal_service_key(x_internal_key: Optional[str] = None) -> bool:
    """Verify the internal service key for backend-to-backend communication."""
    if not x_internal_key:
        raise HTTPException(
            status_code=401,
            detail="Missing internal service key.",
        )
    if x_internal_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid internal service key.",
        )
    return True
