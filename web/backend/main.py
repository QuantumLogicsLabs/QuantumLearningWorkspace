import os
import uuid
import shutil
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from bson import ObjectId

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
import httpx

from models import (
    SignupRequest,
    LoginRequest,
    Upload,
    ChatMessage,
    ChangePasswordRequest,
    QuizResult,
    QuizResultRequest,
)
from database import (
    get_users_collection,
    get_uploads_collection,
    get_chat_history_collection,
    get_quiz_results_collection,
)
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_email,
    verify_internal_service_key,
)
from routes.chat import router as chat_router
from routes.oauth import router as oauth_router
from routes.quiz import router as quiz_router
from routes.flashcards import router as flashcards_router

logger = logging.getLogger("uvicorn")

app = FastAPI(title="StudyMind AI Backend")

origins = [
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


UPLOAD_DIRECTORY = os.getenv(
    "UPLOAD_DIRECTORY",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploaded_files"),
)
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001")


async def process_file_ingestion(file_id: Any, document_id: str, filename: str, user_id: str):
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

            async with httpx.AsyncClient(timeout=15) as client:
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
            logger.warning(
                f"Ingestion error for {filename} ({document_id}): {e}"
            )
            new_status = "Failed"
            last_error = str(e)
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
        "document_id": returned_document_id,
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
    email_clean = request.email.strip().lower()

    existing_user = await users.find_one({"email": email_clean})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed = hash_password(request.password)

    new_user = {
        "email": email_clean,
        "hashed_password": hashed,
        "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
    }

    await users.insert_one(new_user)
    return {"message": "User created successfully.", "email": email_clean}


@app.post("/login")
async def login(request: LoginRequest):
    users = get_users_collection()
    email_clean = request.email.strip().lower()

    user = await users.find_one({"email": email_clean})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(email=user["email"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
async def get_my_profile(current_user_email: str = Depends(get_current_user_email)):
    users = get_users_collection()
    email_clean = current_user_email.strip().lower()
    user = await users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    uploads = get_uploads_collection()
    upload_count = await uploads.count_documents({"user_id": email_clean})

    created_at = user.get("created_at") or user.get("created_date") or datetime.now(timezone.utc).strftime("%B %d, %Y")
    if isinstance(created_at, datetime):
        created_at = created_at.strftime("%B %d, %Y")

    return {
        "email": user["email"],
        "created_at": str(created_at),
        "document_count": upload_count,
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
    document_id = upload_doc.get("document_id") or str(upload_doc.get("_id"))

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