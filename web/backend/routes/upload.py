import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException

from database import get_uploads_collection
from models import Upload

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Stretch goal: only accept PDFs
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Avoid overwriting files with the same name
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    upload_record = Upload(
        filename=safe_filename,
        file_type=file.content_type or "application/pdf",
        status="pending",
    )

    collection = get_uploads_collection()
    await collection.insert_one(upload_record.model_dump())

    return {
        "filename": safe_filename,
        "status": "pending",
        "message": "File uploaded successfully",
    }


@router.get("/uploads")
async def list_uploads():
    collection = get_uploads_collection()
    cursor = collection.find({}, {"_id": 0})
    uploads = await cursor.to_list(length=100)
    return {"uploads": uploads}