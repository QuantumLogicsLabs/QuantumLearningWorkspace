import os
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from database import get_users_collection
from auth_utils import create_access_token

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# ─── Google OAuth ────────────────────────────────────────────────

@router.get("/auth/google/login")
def google_login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid email profile"
        "&access_type=offline"
    )
    return RedirectResponse(google_auth_url)


@router.get("/auth/google/callback")
async def google_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Google token")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Google user info")

        user_info = userinfo_response.json()
        email = user_info.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="No email returned from Google")

    users = get_users_collection()
    existing_user = await users.find_one({"email": email})

    if not existing_user:
        await users.insert_one({
            "email": email,
            "hashed_password": None,
            "auth_provider": "google",
            "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        })

    jwt_token = create_access_token(email=email)

    return RedirectResponse(f"{FRONTEND_URL}/oauth-success?token={jwt_token}")


# ─── GitHub OAuth ────────────────────────────────────────────────

@router.get("/auth/github/login")
def github_login():
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        "&scope=user:email"
    )
    return RedirectResponse(github_auth_url)


@router.get("/auth/github/callback")
async def github_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get GitHub token")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token from GitHub")

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
        email = primary["email"] if primary else (emails[0]["email"] if emails else None)

    if not email:
        raise HTTPException(status_code=400, detail="No email returned from GitHub")

    users = get_users_collection()
    existing_user = await users.find_one({"email": email})

    if not existing_user:
        await users.insert_one({
            "email": email,
            "hashed_password": None,
            "auth_provider": "github",
            "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        })

    jwt_token = create_access_token(email=email)

    return RedirectResponse(f"{FRONTEND_URL}/oauth-success?token={jwt_token}")