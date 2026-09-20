import os
import re
import urllib.parse
import logging
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from web.backend.database import get_users_collection
from web.backend.auth_utils import create_access_token

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path, override=True)

logger = logging.getLogger("uvicorn")
router = APIRouter()


def get_google_credentials():
    load_dotenv(_env_path, override=True)
    return os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")


def get_github_credentials():
    return os.getenv("GITHUB_CLIENT_ID"), os.getenv("GITHUB_CLIENT_SECRET")


def get_google_redirect_uri(request: Request) -> str:
    """
    Determine the Google OAuth redirect URI dynamically.
    Priority 1: Explicit GOOGLE_REDIRECT_URI environment variable.
    Priority 2: Auto-detected from incoming request host (supports localhost & deployed cloud reverse proxies).
    """
    env_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if env_uri and env_uri.strip():
        return env_uri.strip()

    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:5000"))
    return f"{proto}://{host}/auth/google/callback"


def get_github_redirect_uri(request: Request) -> str:
    """Determine the GitHub OAuth redirect URI dynamically."""
    env_uri = os.getenv("GITHUB_REDIRECT_URI")
    if env_uri and env_uri.strip():
        return env_uri.strip()

    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:5000"))
    return f"{proto}://{host}/auth/github/callback"


def get_frontend_url(request: Request, state: Optional[str] = None) -> str:
    """
    Determine where to return the user after OAuth flow.
    Supports localhost, Vercel production, or custom FRONTEND_URL.
    """
    # 1. State parameter if valid http/https origin
    if state:
        try:
            parsed = urllib.parse.urlparse(urllib.parse.unquote(state))
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        except Exception:
            pass

    # 2. Environment variable
    env_frontend = os.getenv("FRONTEND_URL")
    if env_frontend and env_frontend.strip():
        return env_frontend.strip().rstrip("/")

    # 3. Request origin / referer header
    origin = request.headers.get("origin") or request.headers.get("referer", "")
    if "quantum-learning-workspace.vercel.app" in origin:
        return "https://quantum-learning-workspace.vercel.app"

    return "http://localhost:5173"


async def generate_unique_username(users_col, base_name: str, email: str) -> str:
    """Generate a clean, valid, and unique username for OAuth accounts."""
    clean_base = re.sub(r"[^a-z0-9_.-]", "", (base_name or email.split("@")[0]).lower())[:20]
    if len(clean_base) < 3:
        clean_base = f"user_{clean_base}"[:20]

    candidate = clean_base
    counter = 1
    while await users_col.find_one({"username": candidate, "email": {"$ne": email}}):
        candidate = f"{clean_base}_{counter}"
        counter += 1
    return candidate


# ─── Google OAuth ────────────────────────────────────────────────

@router.get("/auth/google/login")
def google_login(request: Request, redirect_to: Optional[str] = None):
    client_id, _ = get_google_credentials()
    target_frontend = redirect_to or get_frontend_url(request)

    if not client_id:
        logger.warning("GOOGLE_CLIENT_ID is not configured in environment.")
        return RedirectResponse(f"{target_frontend}/?error=google_oauth_not_configured")

    redirect_uri = get_google_redirect_uri(request)
    state = urllib.parse.quote(target_frontend, safe="")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(google_auth_url)


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    target_frontend = get_frontend_url(request, state)

    if error:
        logger.warning(f"Google OAuth error received from Google: {error}")
        return RedirectResponse(f"{target_frontend}/?error=google_access_denied")

    if not code:
        return RedirectResponse(f"{target_frontend}/?error=google_no_code")

    client_id, client_secret = get_google_credentials()
    if not client_id or not client_secret:
        return RedirectResponse(f"{target_frontend}/?error=google_oauth_not_configured")

    redirect_uri = get_google_redirect_uri(request)

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            logger.warning(f"Google token exchange failed ({token_response.status_code}): {token_response.text}")
            return RedirectResponse(f"{target_frontend}/?error=google_token_failed")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            logger.warning(f"Failed to fetch Google userinfo ({userinfo_response.status_code}): {userinfo_response.text}")
            return RedirectResponse(f"{target_frontend}/?error=google_userinfo_failed")

        user_info = userinfo_response.json()
        email = (user_info.get("email") or "").strip().lower()

    if not email:
        return RedirectResponse(f"{target_frontend}/?error=google_no_email")

    users = get_users_collection()
    existing_user = await users.find_one({"email": email})

    full_name = user_info.get("name") or email.split("@")[0].capitalize()

    if not existing_user:
        new_username = await generate_unique_username(users, user_info.get("name") or "", email)
        await users.insert_one({
            "name": full_name,
            "username": new_username,
            "email": email,
            "hashed_password": None,
            "auth_provider": "google",
            "is_verified": True,
            "picture": user_info.get("picture"),
            "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        })
    else:
        # Keep existing user profile fresh and ensure verified
        update_fields = {"is_verified": True}
        if not existing_user.get("name"):
            update_fields["name"] = full_name
        if not existing_user.get("username"):
            update_fields["username"] = await generate_unique_username(users, full_name, email)
        if not existing_user.get("auth_provider"):
            update_fields["auth_provider"] = "google"
        if user_info.get("picture") and not existing_user.get("picture"):
            update_fields["picture"] = user_info.get("picture")

        await users.update_one({"email": email}, {"$set": update_fields})

    jwt_token = create_access_token(email=email)
    return RedirectResponse(f"{target_frontend}/oauth-success?token={jwt_token}")


# ─── GitHub OAuth ────────────────────────────────────────────────

@router.get("/auth/github/login")
def github_login(request: Request, redirect_to: Optional[str] = None):
    client_id, _ = get_github_credentials()
    target_frontend = redirect_to or get_frontend_url(request)

    if not client_id:
        return RedirectResponse(f"{target_frontend}/?error=github_oauth_not_configured")

    redirect_uri = get_github_redirect_uri(request)
    state = urllib.parse.quote(target_frontend, safe="")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email",
        "state": state,
    }
    github_auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(github_auth_url)


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    target_frontend = get_frontend_url(request, state)

    if error:
        return RedirectResponse(f"{target_frontend}/?error=github_access_denied")

    if not code:
        return RedirectResponse(f"{target_frontend}/?error=github_no_code")

    client_id, client_secret = get_github_credentials()
    if not client_id or not client_secret:
        return RedirectResponse(f"{target_frontend}/?error=github_oauth_not_configured")

    redirect_uri = get_github_redirect_uri(request)

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            return RedirectResponse(f"{target_frontend}/?error=github_token_failed")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            return RedirectResponse(f"{target_frontend}/?error=github_token_failed")

        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        emails_response = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    email = None
    if emails_response.status_code == 200:
        emails = emails_response.json()
        primary = next((e for e in emails if e.get("primary")), None)
        email = (primary["email"] if primary else (emails[0]["email"] if emails else None))

    if email:
        email = email.strip().lower()

    if not email:
        return RedirectResponse(f"{target_frontend}/?error=github_no_email")

    users = get_users_collection()
    existing_user = await users.find_one({"email": email})

    gh_user_data = user_response.json() if user_response.status_code == 200 else {}
    full_name = gh_user_data.get("name") or gh_user_data.get("login") or email.split("@")[0].capitalize()

    if not existing_user:
        new_username = await generate_unique_username(users, gh_user_data.get("login") or full_name, email)
        await users.insert_one({
            "name": full_name,
            "username": new_username,
            "email": email,
            "hashed_password": None,
            "auth_provider": "github",
            "is_verified": True,
            "picture": gh_user_data.get("avatar_url"),
            "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        })
    else:
        update_fields = {"is_verified": True}
        if not existing_user.get("name"):
            update_fields["name"] = full_name
        if not existing_user.get("username"):
            update_fields["username"] = await generate_unique_username(users, full_name, email)
        if not existing_user.get("auth_provider"):
            update_fields["auth_provider"] = "github"
        await users.update_one({"email": email}, {"$set": update_fields})

    jwt_token = create_access_token(email=email)
    return RedirectResponse(f"{target_frontend}/oauth-success?token={jwt_token}")

