from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router   # ADD THIS

app = FastAPI(title="StudyMind AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)   # ADD THIS

@app.get("/health")
def health_check():
    return {"status": "ok"}