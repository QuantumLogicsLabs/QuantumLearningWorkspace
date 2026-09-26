import os
import sys

# Ensure repository root is on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import uuid
import re
import shutil
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from bson import ObjectId

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
import httpx

from web.backend.models import (
    SignupRequest,
    LoginRequest,
    VerifyOtpRequest,
    ResendOtpRequest,
    Upload,
    ChatMessage,
    ChangePasswordRequest,
    UpdateProfileRequest,
    QuizResult,
    QuizResultRequest,
)
from web.backend.email_service import send_otp_email
import random
import secrets
from web.backend.database import (
    get_users_collection,
    get_uploads_collection,
    get_chat_history_collection,
    get_quiz_results_collection,
    get_quiz_sessions_collection,
    get_flashcard_reviews_collection,
    get_flashcards_collection,
    init_db_indexes,
)
from web.backend.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_email,
    verify_internal_service_key,
)
from web.backend.routes.chat import router as chat_router
from web.backend.routes.oauth import router as oauth_router
from web.backend.routes.quiz import router as quiz_router
from web.backend.routes.flashcards import router as flashcards_router
from web.backend.routes.roadmap import router as roadmap_router

logger = logging.getLogger("uvicorn")

app = FastAPI(title="StudyMind AI Backend")


@app.on_event("startup")
async def on_startup():
    await init_db_indexes()

origins = [
    "https://quantum-learning-workspace.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(oauth_router)
app.include_router(quiz_router)
app.include_router(flashcards_router)
app.include_router(roadmap_router)


UPLOAD_DIRECTORY = os.getenv(
    "UPLOAD_DIRECTORY",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploaded_files"),
)
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001")
print(f"DEBUG: INGESTION_SERVICE_URL = {repr(INGESTION_SERVICE_URL)}", flush=True)

async def process_file_ingestion(file_id: Any, document_id: str, filename: str, user_id: str):
    print("🚀 START ingestion process")
    print("INGESTION URL:", INGESTION_SERVICE_URL)
    print("FINAL URL:", f"{INGESTION_SERVICE_URL}/ingest/pdf")
    """Forward the uploaded file to the ingestion service for chunking + embedding and persist results."""
    uploads = get_uploads_collection()

    # Determine file path on disk: prefer <document_id>.pdf, fallback to filename
    file_path = os.path.join(UPLOAD_DIRECTORY, f"{document_id}.pdf") if document_id else None
    if not file_path or not os.path.exists(file_path):
        file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    new_status = "Ready"
    chunks_stored = 0
    last_error = None
    returned_document_id = document_id

    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            async with httpx.AsyncClient(timeout=120) as client: 
                internal_token = create_access_token(email=user_id) 
                response = await client.post( 
                    f"{INGESTION_SERVICE_URL.rstrip('/')}/ingest/pdf", 
                    files={"file": (filename, file_bytes, "application/pdf")}, 
                    headers={"Authorization": f"Bearer {internal_token}"}, 
    ) 

            if response.status_code == 200:
                try:
                    data = response.json()
                    returned_document_id = data.get("document_id") or document_id
                    chunks_stored = data.get("chunks_stored", 0)
                    new_status = "Ready"
                except Exception:
                    new_status = "Ready"
            else:
                logger.warning(
                    f"Ingestion service responded with {response.status_code}: {response.text}"
                )
                new_status = "Failed"
                last_error = (
                    f"Ingestion failed ({response.status_code}): {response.text}"
                )

        except Exception as e:
            error_details = f"{type(e).__name__}: {repr(e)}"
            print(f"INGESTION_EXCEPTION: {error_details}", flush=True)
            logger.error(f"INGESTION_EXCEPTION: {error_details}", flush=True)
            new_status = "Failed"
            last_error = error_details
    else:
        new_status = "Failed"
        last_error = "File not found on disk"

    query: Dict[str, Any] = {"user_id": user_id}
    if file_id:
        try:
            query["_id"] = ObjectId(str(file_id))
        except Exception:
            query["_id"] = str(file_id)
    elif document_id:
        query["document_id"] = document_id
    else:
        query["filename"] = filename

    update_fields: Dict[str, Any] = {
        "status": new_status,
        "document_id": document_id,
        "vector_document_id": returned_document_id,
        "chunks_stored": chunks_stored,
        "processed_at": datetime.now(timezone.utc),
        "last_error": last_error,
    }

    await uploads.update_one(query, {"$set": update_fields})


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/signup")
async def signup(request: SignupRequest):
    users = get_users_collection()
    name_clean = request.name.strip()
    username_clean = request.username.strip().lower()
    email_clean = request.email.strip().lower()

    # ── Username format validation ───────────────────────────────────────────
    if not re.match(r"^[a-zA-Z0-9_.-]{3,30}$", username_clean):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-30 characters and contain only letters, numbers, underscores, dots, or hyphens."
        )

    # ── Username uniqueness check ─────────────────────────────────────────────
    existing_username_user = await users.find_one({"username": username_clean})
    if existing_username_user and existing_username_user.get("email") != email_clean:
        raise HTTPException(status_code=400, detail="Username is already taken.")
    # ─────────────────────────────────────────────────────────────────────────

    existing_user = await users.find_one({"email": email_clean})
    if existing_user and existing_user.get("is_verified") is not False:
        raise HTTPException(status_code=400, detail="Email already registered.")

    # ── Password strength validation ──────────────────────────────────────────
    pwd = request.password
    errors = []
    if len(pwd) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", pwd):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", pwd):
        errors.append("at least one lowercase letter")
    if not re.search(r"[0-9]", pwd):
        errors.append("at least one number")
    if not re.search(r"[^A-Za-z0-9]", pwd):
        errors.append("at least one special character (!@#$ etc.)")
    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Password must have: {', '.join(errors)}."
        )
    # ─────────────────────────────────────────────────────────────────────────

    hashed = hash_password(request.password)
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    if existing_user and existing_user.get("is_verified") is False:
        # User previously registered but didn't finish verification; update credentials, name, username & OTP
        await users.update_one(
            {"email": email_clean},
            {
                "$set": {
                    "name": name_clean,
                    "username": username_clean,
                    "hashed_password": hashed,
                    "otp_code": otp_code,
                    "otp_expires_at": otp_expires,
                    "otp_last_sent": datetime.now(timezone.utc),
                }
            }
        )
    else:
        new_user = {
            "name": name_clean,
            "username": username_clean,
            "email": email_clean,
            "hashed_password": hashed,
            "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
            "login_dates": [today_iso],
            "last_login": datetime.now(timezone.utc),
            "is_verified": False,
            "otp_code": otp_code,
            "otp_expires_at": otp_expires,
            "otp_last_sent": datetime.now(timezone.utc),
        }
        await users.insert_one(new_user)

    # Send OTP email (and log to console for dev mode)
    await send_otp_email(email_clean, otp_code)

    return {
        "message": "Verification code sent to your email.",
        "email": email_clean,
        "requires_verification": True,
    }


@app.post("/verify-otp")
async def verify_otp(request: VerifyOtpRequest):
    users = get_users_collection()
    email_clean = request.email.strip().lower()
    otp_clean = request.otp.strip()

    user = await users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.get("is_verified") is True:
        token = create_access_token(email=email_clean)
        return {"message": "Email is already verified.", "access_token": token, "token_type": "bearer"}

    stored_otp = str(user.get("otp_code", ""))
    expires_at = user.get("otp_expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now_utc = datetime.now(timezone.utc)
    if not stored_otp or stored_otp != otp_clean:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    if expires_at and expires_at < now_utc:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please click Resend Code.")

    await users.update_one(
        {"email": email_clean},
        {
            "$set": {
                "is_verified": True,
                "otp_code": None,
                "otp_expires_at": None,
            }
        }
    )

    token = create_access_token(email=email_clean)
    return {
        "message": "Email verified successfully!",
        "access_token": token,
        "token_type": "bearer",
    }


@app.post("/resend-otp")
async def resend_otp(request: ResendOtpRequest):
    users = get_users_collection()
    email_clean = request.email.strip().lower()

    user = await users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.get("is_verified") is True:
        raise HTTPException(status_code=400, detail="This account is already verified.")

    # 60-second cooldown protection
    last_sent = user.get("otp_last_sent")
    if last_sent:
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last_sent).total_seconds()
        if elapsed < 60:
            remaining = int(60 - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining}s before requesting another code."
            )

    new_otp = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    await users.update_one(
        {"email": email_clean},
        {
            "$set": {
                "otp_code": new_otp,
                "otp_expires_at": expires_at,
                "otp_last_sent": datetime.now(timezone.utc),
            }
        }
    )

    await send_otp_email(email_clean, new_otp)
    return {"message": "A new verification code has been sent to your email."}


@app.post("/login")
async def login(request: LoginRequest):
    users = get_users_collection()
    email_clean = request.email.strip().lower()

    user = await users.find_one({"email": email_clean})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # ── Lockout check ─────────────────────────────────────────────────────────
    lockout_until = user.get("lockout_until")
    if lockout_until:
        # Make lockout_until timezone-aware if it's naive
        if lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if lockout_until > now_utc:
            remaining = int((lockout_until - now_utc).total_seconds())
            mins = remaining // 60
            secs = remaining % 60
            raise HTTPException(
                status_code=423,
                detail=f"Account locked. Try again in {mins}m {secs}s."
            )
        else:
            # Lockout expired — clear it
            await users.update_one(
                {"email": email_clean},
                {"$set": {"failed_attempts": 0, "lockout_until": None}}
            )
    # ─────────────────────────────────────────────────────────────────────────

    # ── Wrong password ────────────────────────────────────────────────────────
    if not verify_password(request.password, user["hashed_password"]):
        failed = user.get("failed_attempts", 0) + 1
        MAX_ATTEMPTS = 5
        if failed >= MAX_ATTEMPTS:
            lock_time = datetime.now(timezone.utc) + timedelta(minutes=15)
            await users.update_one(
                {"email": email_clean},
                {"$set": {"failed_attempts": failed, "lockout_until": lock_time}}
            )
            raise HTTPException(
                status_code=423,
                detail="Too many failed attempts. Account locked for 15 minutes."
            )
        remaining_attempts = MAX_ATTEMPTS - failed
        await users.update_one(
            {"email": email_clean},
            {"$set": {"failed_attempts": failed}}
        )
        raise HTTPException(
            status_code=401,
            detail=f"Invalid password. {remaining_attempts} attempt{'s' if remaining_attempts != 1 else ''} remaining."
        )
    # ─────────────────────────────────────────────────────────────────────────

    # ── Successful login — reset counters ─────────────────────────────────────
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await users.update_one(
        {"email": email_clean},
        {
            "$addToSet": {"login_dates": today_iso},
            "$set": {
                "last_login": datetime.now(timezone.utc),
                "failed_attempts": 0,
                "lockout_until": None,
            },
        }
    )
    # ── Check Email Verification ──────────────────────────────────────────────
    if user.get("is_verified") is False:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please verify your email to continue."
        )
    # ─────────────────────────────────────────────────────────────────────────

    token = create_access_token(email=user["email"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
async def get_my_profile(
    tz: Optional[str] = None,
    current_user_email: str = Depends(get_current_user_email),
):
    users = get_users_collection()
    email_clean = current_user_email.strip().lower()
    user = await users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Determine user's local timezone
    user_tz = timezone.utc
    if tz and tz.strip():
        try:
            user_tz = ZoneInfo(tz.strip())
        except Exception:
            user_tz = timezone.utc

    today_local = datetime.now(user_tz).strftime("%Y-%m-%d")

    # Record login / active date
    await users.update_one(
        {"email": email_clean},
        {
            "$addToSet": {"login_dates": today_local},
            "$set": {"last_active": datetime.now(timezone.utc)},
        }
    )

    # Calculate distinct days active from login_dates
    login_dates_list = user.get("login_dates") or []
    login_dates_set = set(login_dates_list)
    login_dates_set.add(today_local)
    days_active = max(len(login_dates_set), 1)

    uploads = get_uploads_collection()
    upload_count = await uploads.count_documents({"user_id": email_clean})

    created_at = user.get("created_at") or user.get("created_date") or datetime.now(timezone.utc).strftime("%B %d, %Y")
    if isinstance(created_at, datetime):
        created_at = created_at.strftime("%B %d, %Y")

    fallback_name = user["email"].split("@")[0].capitalize()
    return {
        "email": user["email"],
        "name": user.get("name") or user.get("username") or fallback_name,
        "username": user.get("username") or user["email"].split("@")[0],
        "created_at": str(created_at),
        "document_count": upload_count,
        "days_active": days_active,
    }


@app.post("/update-profile")
@app.put("/me")
async def update_profile(
    request: UpdateProfileRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    users = get_users_collection()
    email_clean = current_user_email.strip().lower()

    update_fields: Dict[str, Any] = {}
    if request.name is not None and request.name.strip():
        update_fields["name"] = request.name.strip()
    if request.username is not None and request.username.strip():
        clean_user = request.username.strip().lower()
        # Check if username is taken by someone else
        existing = await users.find_one({"username": clean_user, "email": {"$ne": email_clean}})
        if existing:
            raise HTTPException(status_code=400, detail="This username is already taken. Please choose another.")
        update_fields["username"] = clean_user

    if update_fields:
        await users.update_one({"email": email_clean}, {"$set": update_fields})

    updated_user = await users.find_one({"email": email_clean})
    saved_name = updated_user.get("name") or updated_user.get("username") or email_clean.split("@")[0].capitalize()

    return {
        "message": "Profile updated successfully.",
        "name": saved_name,
        "username": updated_user.get("username") or email_clean.split("@")[0],
    }


@app.delete("/delete-account")
async def delete_account(
    current_user_email: str = Depends(get_current_user_email),
):
    """
    Permanently delete the currently logged-in user's account and all associated data.
    STRICT SECURITY: All operations are strictly filtered by current_user_email.
    Other users' accounts and documents are never touched.
    """
    if not current_user_email or not current_user_email.strip():
        raise HTTPException(status_code=400, detail="Invalid user identification.")

    email_clean = current_user_email.strip().lower()

    users = get_users_collection()
    user = await users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    uploads = get_uploads_collection()
    chat_history = get_chat_history_collection()
    quiz_results = get_quiz_results_collection()
    quiz_sessions = get_quiz_sessions_collection()
    flashcard_reviews = get_flashcard_reviews_collection()
    flashcards = get_flashcards_collection()

    # 1. Clean up only THIS user's uploaded files and vector embeddings
    try:
        user_uploads = await uploads.find({"user_id": email_clean}).to_list(length=None)
        for doc in user_uploads:
            # Purge vector embeddings for this specific doc
            document_id = doc.get("vector_document_id") or doc.get("document_id") or str(doc.get("_id"))
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    purge_url = f"{INGESTION_SERVICE_URL.rstrip('/')}/documents/{document_id}"
                    internal_token = create_access_token(email=email_clean)
                    await client.delete(
                        purge_url,
                        headers={"Authorization": f"Bearer {internal_token}"},
                        params={"user_id": email_clean},
                    )
            except Exception as e:
                logger.warning(f"Vector purge for doc {document_id} during account deletion failed: {e}")

            # Purge physical disk file if exists
            possible_filenames = []
            if doc.get("document_id"):
                possible_filenames.append(f"{doc['document_id']}.pdf")
            if doc.get("filename"):
                possible_filenames.append(doc["filename"])

            for fname in possible_filenames:
                file_path = os.path.join(UPLOAD_DIRECTORY, fname)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Could not remove physical file {file_path}: {e}")

        # Delete ONLY this user's uploads records
        await uploads.delete_many({"user_id": email_clean})
    except Exception as e:
        logger.warning(f"Error cleaning uploads for user {email_clean}: {e}")

    # 2. Clean up ONLY THIS user's chat history, quiz results, sessions, and flashcards
    try:
        await chat_history.delete_many({"user_id": email_clean})
        await quiz_results.delete_many({"user_id": email_clean})
        await quiz_sessions.delete_many({"user_id": email_clean})
        await flashcard_reviews.delete_many({"user_id": email_clean})
        await flashcards.delete_many({"user_id": email_clean})
    except Exception as e:
        logger.warning(f"Error cleaning activity data for user {email_clean}: {e}")

    # 3. Delete ONLY THIS user's account from users collection
    del_result = await users.delete_one({"email": email_clean})
    logger.info(f"User account permanently deleted for {email_clean} (deleted_count={getattr(del_result, 'deleted_count', 1)})")

    return {"message": "Account and all associated data deleted successfully."}


@app.get("/analytics/study-pulse")
async def get_study_pulse(
    tz: Optional[str] = None,
    current_user_email: str = Depends(get_current_user_email),
):
    email_clean = current_user_email.strip().lower()
    reviews_col = get_flashcard_reviews_collection()
    quiz_col = get_quiz_results_collection()
    uploads_col = get_uploads_collection()

    # Determine user's local country timezone (e.g. "Asia/Karachi", "America/New_York", etc.)
    user_tz = timezone.utc
    if tz and tz.strip():
        try:
            user_tz = ZoneInfo(tz.strip())
        except Exception:
            user_tz = timezone.utc

    # Current time and date in the user's country / local timezone
    # Exactly at midnight (12:00 AM) in their country, today_date advances to the new calendar day
    now_user = datetime.now(user_tz)
    today_date = now_user.date()
    yesterday_date = today_date - timedelta(days=1)

    # Helper to convert DB UTC datetimes / ISO strings to user's local date
    def to_user_date(val: Any) -> Optional[date]:
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                return None
        if isinstance(val, datetime):
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            return val.astimezone(user_tz).date()
        return None

    # 1. Collect all distinct study activity dates in user's local timezone
    real_activity_dates: set = set()

    # Flashcard reviews dates
    async for r in reviews_col.find({"user_id": email_clean}, {"date_reviewed": 1, "topic": 1, "status": 1}):
        d = to_user_date(r.get("date_reviewed"))
        if d:
            real_activity_dates.add(d)

    # Quiz results dates
    async for q in quiz_col.find({"user_id": email_clean}, {"timestamp": 1, "created_at": 1, "topic": 1}):
        d = to_user_date(q.get("timestamp") or q.get("created_at"))
        if d:
            real_activity_dates.add(d)

    # Uploads dates
    async for u in uploads_col.find({"user_id": email_clean}, {"upload_date": 1, "filename": 1}):
        d = to_user_date(u.get("upload_date"))
        if d:
            real_activity_dates.add(d)

    # 2. Compute Consecutive Day Streak with Local Midnight rollover:
    # If the user has studied TODAY (local timezone):
    #   Streak includes today and counts backward consecutively.
    # If the user has NOT studied today yet:
    #   Check if they studied YESTERDAY (local timezone).
    #   If yes, the streak is alive from yesterday (prompting them to study today to maintain it).
    #   If neither today nor yesterday has study activity, streak is 1 for an active session.
    has_activity_today = today_date in real_activity_dates
    has_activity_yesterday = yesterday_date in real_activity_dates

    if has_activity_today:
        streak_count = 0
        curr = today_date
        while curr in real_activity_dates:
            streak_count += 1
            curr = curr - timedelta(days=1)
        streak_days = max(streak_count, 1)
        streak_active_today = True
    elif has_activity_yesterday:
        streak_count = 0
        curr = yesterday_date
        while curr in real_activity_dates:
            streak_count += 1
            curr = curr - timedelta(days=1)
        streak_days = max(streak_count, 1)
        streak_active_today = False
    else:
        streak_days = 1
        streak_active_today = False

    # 3. Today's Milestones (Daily Goal) calculated from local midnight in user's timezone
    local_midnight = datetime.combine(today_date, datetime.min.time(), tzinfo=user_tz)
    today_start_utc = local_midnight.astimezone(timezone.utc)

    today_reviews = await reviews_col.count_documents({
        "user_id": email_clean,
        "date_reviewed": {"$gte": today_start_utc},
    })
    m1_login = True  # Milestone 1: Daily login/active session
    m2_flashcards = today_reviews > 0
    m3_quiz = False
    m4_extra = today_reviews >= 3

    today_quizzes = await quiz_col.count_documents({
        "user_id": email_clean,
        "timestamp": {"$gte": today_start_utc},
    })
    if today_quizzes > 0:
        m3_quiz = True

    today_uploads = await uploads_col.count_documents({
        "user_id": email_clean,
        "upload_date": {"$gte": today_start_utc},
    })
    if today_uploads > 0:
        m4_extra = True

    milestones_done = sum([1 if m else 0 for m in [m1_login, m2_flashcards, m3_quiz, m4_extra]])
    goal_percent = int((milestones_done / 4) * 100)

    # 4. Combined Mastery Pulse Stats (Flashcards + Quizzes)
    flashcard_known = await reviews_col.count_documents({"user_id": email_clean, "status": "known"})
    flashcard_learning = await reviews_col.count_documents({"user_id": email_clean, "status": "still_learning"})

    quiz_correct = await quiz_col.count_documents({"user_id": email_clean, "is_correct": True})
    quiz_incorrect = await quiz_col.count_documents({"user_id": email_clean, "is_correct": False})

    total_mastered = flashcard_known + quiz_correct
    total_in_review = flashcard_learning + quiz_incorrect

    # Identify distinct weak topics across both flashcards and quizzes
    topic_scores: Dict[str, Dict[str, int]] = {}
    async for r in reviews_col.find({"user_id": email_clean}, {"topic": 1, "status": 1}):
        t = r.get("topic") or "General"
        if t not in topic_scores:
            topic_scores[t] = {"correct": 0, "wrong": 0}
        if r.get("status") == "known":
            topic_scores[t]["correct"] += 1
        elif r.get("status") == "still_learning":
            topic_scores[t]["wrong"] += 1

    async for q in quiz_col.find({"user_id": email_clean}, {"topic": 1, "is_correct": 1}):
        t = q.get("topic") or "General"
        if t not in topic_scores:
            topic_scores[t] = {"correct": 0, "wrong": 0}
        if q.get("is_correct") is True:
            topic_scores[t]["correct"] += 1
        elif q.get("is_correct") is False:
            topic_scores[t]["wrong"] += 1

    weak_count = 0
    for t_name, scores in topic_scores.items():
        tot = scores["correct"] + scores["wrong"]
        if tot >= 2 and (scores["wrong"] > scores["correct"] or (scores["correct"] / tot) < 0.6):
            weak_count += 1

    # 5. Last Studied Activity: Check latest between flashcards and quiz
    latest_review = await reviews_col.find_one({"user_id": email_clean}, sort=[("date_reviewed", -1)])
    latest_quiz = await quiz_col.find_one({"user_id": email_clean}, sort=[("date_taken", -1), ("timestamp", -1)])

    last_studied_payload = None
    rev_time = latest_review.get("date_reviewed") if latest_review else None
    quiz_time = (latest_quiz.get("date_taken") or latest_quiz.get("timestamp")) if latest_quiz else None

    if rev_time and (not quiz_time or rev_time >= quiz_time):
        last_studied_payload = {
            "topic": latest_review.get("topic", "General"),
            "type": "flashcards",
            "sub_text": "Flashcards active recall",
            "target_tab": "flashcards",
        }
    elif quiz_time:
        last_studied_payload = {
            "topic": latest_quiz.get("topic", "General"),
            "type": "quiz",
            "sub_text": "Practice Quiz assessment",
            "target_tab": "quiz",
        }

    return {
        "streak_days": streak_days,
        "streak_active_today": streak_active_today,
        "goal_percent": goal_percent,
        "goals_completed": milestones_done,
        "total_goals": 4,
        "mastered": total_mastered,
        "in_review": total_in_review,
        "weak_topics": weak_count,
        "last_studied": last_studied_payload,
        "timezone": str(user_tz),
        "local_date": today_date.isoformat(),
    }


@app.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    users = get_users_collection()
    email_clean = current_user_email.strip().lower()
    user = await users.find_one({"email": email_clean})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=404, detail="User not found or password not set.")

    if not verify_password(request.old_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=400, detail="New password must be different from current password."
        )

    new_hashed = hash_password(request.new_password)
    await users.update_one(
        {"email": email_clean}, {"$set": {"hashed_password": new_hashed}}
    )

    return {"message": "Password changed successfully."}


@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user_email),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file: filename is missing.")

    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    filename = file.filename
    document_id = str(uuid.uuid4())
    physical_filename = f"{document_id}.pdf"
    file_path = os.path.join(UPLOAD_DIRECTORY, physical_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    upload_record = Upload(
        filename=filename,
        document_id=document_id,
        file_type=file.content_type or "application/pdf",
        user_id=current_user_email.strip().lower(),
        status="Processing",
        chunks_stored=0,
        last_error=None,
        processed_at=None,
    )

    uploads = get_uploads_collection()
    result = await uploads.insert_one(upload_record.model_dump())
    inserted_id = getattr(result, "inserted_id", None)

    background_tasks.add_task(
        process_file_ingestion,
        file_id=inserted_id,
        document_id=document_id,
        filename=filename,
        user_id=current_user_email.strip().lower(),
    )

    return {
        "message": "File uploaded successfully and ingestion pipeline started.",
        "document_id": upload_record.document_id,
        "filename": upload_record.filename,
        "status": upload_record.status,
    }


@app.get("/uploads")
async def get_uploads(current_user_email: str = Depends(get_current_user_email)):
    uploads = get_uploads_collection()
    email_clean = current_user_email.strip().lower()

    user_uploads = []
    cursor = uploads.find({"user_id": email_clean})

    async for document in cursor:
        upload_date = document.get("upload_date")
        if isinstance(upload_date, datetime):
            upload_date = upload_date.isoformat()
        processed_at = document.get("processed_at")
        if isinstance(processed_at, datetime):
            processed_at = processed_at.isoformat()

        user_uploads.append({
            "id": str(document["_id"]),
            "document_id": document.get("document_id"),
            "filename": document.get("filename", ""),
            "upload_date": upload_date,
            "processed_at": processed_at,
            "file_type": document.get("file_type", "application/pdf"),
            "status": document.get("status", "Processing"),
            "chunks_stored": document.get("chunks_stored", 0),
            "last_error": document.get("last_error"),
        })

    return user_uploads


@app.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()
    email_clean = current_user_email.strip().lower()

    try:
        search_query: Dict[str, Any] = {"_id": ObjectId(upload_id), "user_id": email_clean}
    except Exception:
        search_query = {"_id": upload_id, "user_id": email_clean}

    upload_doc = await uploads.find_one(search_query)
    if not upload_doc:
        upload_doc = await uploads.find_one({"_id": upload_id, "user_id": email_clean})
        if upload_doc:
            search_query = {"_id": upload_id, "user_id": email_clean}

    if not upload_doc:
        # Also support deleting by document_id
        upload_doc = await uploads.find_one({"document_id": upload_id, "user_id": email_clean})
        if upload_doc:
            search_query = {"document_id": upload_id, "user_id": email_clean}

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    # 1. Purge vector embeddings from ChromaDB via Lambda Ingestion service
    document_id = upload_doc.get("vector_document_id") or upload_doc.get("document_id") or str(upload_doc.get("_id"))

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            purge_url = f"{INGESTION_SERVICE_URL.rstrip('/')}/documents/{document_id}"
            internal_token = create_access_token(email=email_clean)
            purge_res = await client.delete(
                purge_url,
                headers={"Authorization": f"Bearer {internal_token}"},
                params={"user_id": email_clean},
            )
            if purge_res.status_code != 200:
                logger.warning(
                    f"Vector purge for doc {document_id} returned status {purge_res.status_code}: {purge_res.text}"
                )
    except Exception as e:
        logger.warning(f"Failed to connect to ingestion service for vector purge: {e}")

    # 2. Delete local physical file
    possible_filenames = []
    if upload_doc.get("document_id"):
        possible_filenames.append(f"{upload_doc['document_id']}.pdf")
    if upload_doc.get("filename"):
        possible_filenames.append(upload_doc["filename"])

    for fname in possible_filenames:
        file_path = os.path.join(UPLOAD_DIRECTORY, fname)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not remove file {file_path}: {e}")

    # 3. Delete MongoDB record
    await uploads.delete_one(search_query)
    return {"message": "Upload and vector embeddings deleted successfully"}


@app.get("/uploads/{upload_id}/preview")
async def get_document_preview(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()
    email_clean = current_user_email.strip().lower()

    try:
        search_query: Dict[str, Any] = {"_id": ObjectId(upload_id), "user_id": email_clean}
    except Exception:
        search_query = {"_id": upload_id, "user_id": email_clean}

    upload_doc = await uploads.find_one(search_query)
    if not upload_doc:
        upload_doc = await uploads.find_one({"_id": upload_id, "user_id": email_clean})

    if not upload_doc:
        # Also check by document_id
        upload_doc = await uploads.find_one({"document_id": upload_id, "user_id": email_clean})

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    doc_id = upload_doc.get("document_id")
    filename = upload_doc.get("filename", "")

    # Locate physical file: check <document_id>.pdf, then fallback to filename
    file_path = None
    if doc_id:
        candidate_path = os.path.join(UPLOAD_DIRECTORY, f"{doc_id}.pdf")
        if os.path.exists(candidate_path):
            file_path = candidate_path

    if not file_path and filename:
        candidate_path = os.path.join(UPLOAD_DIRECTORY, filename)
        if os.path.exists(candidate_path):
            file_path = candidate_path

    file_size = None
    if file_path and os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

    page_count = None
    word_count = None
    if file_path and (filename.lower().endswith(".pdf") or file_path.endswith(".pdf")) and os.path.exists(file_path):
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            if text.strip():
                word_count = len(text.split())
        except Exception:
            pass

    file_type = filename.split(".")[-1].upper() if "." in filename else "FILE"
    upload_date = upload_doc.get("upload_date")
    if isinstance(upload_date, datetime):
        upload_date = upload_date.isoformat()
    processed_at = upload_doc.get("processed_at")
    if isinstance(processed_at, datetime):
        processed_at = processed_at.isoformat()

    return {
        "id": str(upload_doc["_id"]),
        "document_id": doc_id,
        "filename": filename,
        "upload_date": upload_date,
        "processed_at": processed_at,
        "status": upload_doc.get("status", "Processing"),
        "chunks_stored": upload_doc.get("chunks_stored", 0),
        "last_error": upload_doc.get("last_error"),
        "file_size": file_size,
        "page_count": page_count,
        "word_count": word_count,
        "file_type": file_type,
    }


@app.post("/chat-history")
async def save_chat_message(
    message: dict,
    current_user_email: str = Depends(get_current_user_email),
):
    """Save one chat message (either a user question or an assistant answer)."""
    chat_history = get_chat_history_collection()
    email_clean = current_user_email.strip().lower()

    record = ChatMessage(
        user_id=email_clean,
        role=message.get("role", "user"),
        content=message.get("content", ""),
        sources=message.get("sources"),
        timing=message.get("timing"),
    )

    await chat_history.insert_one(record.model_dump())
    return {"message": "saved"}


@app.get("/chat-history")
async def get_chat_history(current_user_email: str = Depends(get_current_user_email)):
    """Return this user's past conversation, oldest first."""
    chat_history = get_chat_history_collection()
    email_clean = current_user_email.strip().lower()
    cursor = chat_history.find({"user_id": email_clean}).sort("timestamp", 1)

    messages = []
    async for doc in cursor:
        ts = doc.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.isoformat()
        messages.append({
            "role": doc.get("role"),
            "content": doc.get("content"),
            "sources": doc.get("sources"),
            "timing": doc.get("timing"),
            "timestamp": ts,
        })

    return messages


@app.delete("/chat-history")
async def clear_chat_history(current_user_email: str = Depends(get_current_user_email)):
    """Delete this user's entire conversation history."""
    chat_history = get_chat_history_collection()
    email_clean = current_user_email.strip().lower()
    await chat_history.delete_many({"user_id": email_clean})
    return {"message": "cleared"}


@app.post("/quiz-results")
async def save_quiz_results(
    request: QuizResultRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """Save quiz results for the current user."""
    quiz_results = get_quiz_results_collection()
    email_clean = current_user_email.strip().lower()

    saved_count = 0
    for result in request.results:
        record = QuizResult(
            user_id=email_clean,
            question_id=str(result.get("question_id", "")),
            topic=result.get("topic", "General"),
            selected_answer=str(result.get("selected_answer", "")),
            correct_answer=str(result.get("correct_answer", "")),
            is_correct=bool(result.get("is_correct", False)),
        )
        await quiz_results.insert_one(record.model_dump())
        saved_count += 1

    return {"message": f"Saved {saved_count} quiz results"}


@app.get("/quiz-results")
async def get_quiz_results(current_user_email: str = Depends(get_current_user_email)):
    """Return this user's quiz history."""
    quiz_results = get_quiz_results_collection()
    email_clean = current_user_email.strip().lower()
    cursor = quiz_results.find({"user_id": email_clean})

    results = []
    async for doc in cursor:
        dt = doc.get("date_taken")
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.isoformat()
        results.append({
            "id": str(doc.get("_id", "")),
            "question_id": doc.get("question_id"),
            "topic": doc.get("topic"),
            "selected_answer": doc.get("selected_answer"),
            "correct_answer": doc.get("correct_answer"),
            "is_correct": doc.get("is_correct"),
            "date_taken": dt,
        })

    return results


@app.get("/quiz-results/{user_id}")
async def get_quiz_results_by_user_id(
    user_id: str,
    x_internal_key: Optional[str] = Header(default=None),
):
    """Return quiz history for a specific user (internal service access only)."""
    verify_internal_service_key(x_internal_key)

    quiz_results = get_quiz_results_collection()
    cursor = quiz_results.find({"user_id": user_id.strip().lower()})

    results = []
    async for doc in cursor:
        dt = doc.get("date_taken")
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.isoformat()
        results.append({
            "id": str(doc.get("_id", "")),
            "question_id": doc.get("question_id"),
            "topic": doc.get("topic"),
            "selected_answer": doc.get("selected_answer"),
            "correct_answer": doc.get("correct_answer"),
            "is_correct": doc.get("is_correct"),
            "date_taken": dt,
        })

    return results

