"""
[Contract v1, Section 10 — Quiz Security] JWT authentication for
quiz endpoints.

Matches the scheme documented in docs/api-contracts.md for Mu's
/ask: HS256, JWT_SECRET_KEY env var, "Authorization: Bearer <jwt>",
identity read from the token's `sub` claim (the user's login email,
per Contract v1 Section 2). No user_id is ever trusted from a
request body or header directly — only from a verified token.

Requires PyJWT (`pip install pyjwt`) — add it to requirements.txt
if it isn't already there (Mu's service already depends on it for
the same purpose, so it's likely already in the root/shared
requirements somewhere; worth checking before assuming it needs
adding here too).
"""

import os
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"


def get_current_user_id(authorization: str = Header(default=None)) -> str:
    """
    FastAPI dependency. Verifies the Authorization header and returns
    the authenticated user's identity from the JWT's `sub` claim.

    Failure modes match Contract v1 / Mu's documented /ask behavior
    exactly, so error handling is consistent across services:
      - missing header            -> 403 "Not authenticated"
      - invalid/expired token     -> 401 "Could not validate credentials."
      - server missing the secret -> 500 "Server is not configured with a JWT secret."
    """
    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured with a JWT secret.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

    return user_id