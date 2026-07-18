# API Contracts

## POST /upload
Uploads a single PDF file.

**Request:** multipart/form-data with a "file" field.

**Response (200):**
{
  "filename": "notes.pdf",
  "upload_date": "2026-07-19T10:15:00",
  "file_type": "pdf",
  "status": "pending",
  "metadata": null
}

**Response (400):** if file type is invalid
{
  "detail": "Only PDF files are accepted."
}

## GET /uploads
Returns a list of all uploaded files.

**Response (200):**
[
  {
    "filename": "notes.pdf",
    "upload_date": "2026-07-19T10:15:00",
    "file_type": "pdf",
    "status": "pending",
    "metadata": null
  },
  ...
]