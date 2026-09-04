from datetime import datetime, timezone
from typing import Literal, Optional, List, Dict, Any

from pydantic import BaseModel, Field, EmailStr


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    email: EmailStr
    hashed_password: Optional[str] = None
    auth_provider: Optional[str] = None
    created_at: Optional[str] = None
    created_date: datetime = Field(default_factory=utc_now)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class Upload(BaseModel):
    filename: str = Field(..., min_length=1)
    upload_date: datetime = Field(default_factory=utc_now)
    file_type: Optional[str] = "application/pdf"
    status: str = Field(default="uploaded")
    metadata: Optional[dict] = None
    user_id: str
    document_id: Optional[str] = None
    chunks_stored: Optional[int] = 0
    last_error: Optional[str] = None
    processed_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[Any]] = None
    timing: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=utc_now)


class QuizResult(BaseModel):
    user_id: str
    question_id: Optional[str] = None
    topic: Optional[str] = "General"
    selected_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: bool = False
    date_taken: datetime = Field(default_factory=utc_now)


class QuizResultRequest(BaseModel):
    results: List[Dict[str, Any]] = Field(default_factory=list)


class GenerateQuizProxyRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to generate the quiz from.")
    question_count: int = Field(default=5, ge=1, le=20, description="Number of questions (1-20).")
    quiz_type: str = Field(..., description="One of: mcq, true_false, fill_blank, short_answer.")


class QuizSubmissionAnswer(BaseModel):
    question_id: str
    selected_answer: Optional[str] = ""


class SubmitQuizRequest(BaseModel):
    quiz_id: Optional[str] = None
    topic: Optional[str] = "General"
    answers: Optional[Any] = None
    results: Optional[List[Dict[str, Any]]] = None


class HistoryMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    filename: Optional[str] = None
    history: Optional[List[HistoryMessage]] = None
    top_k: Optional[int] = 4
    include_sources: Optional[bool] = True
    rerank: Optional[bool] = True
    multi_hop: Optional[bool] = True
    skip_cache: Optional[bool] = False


# ==========================================
# Flashcard & Weak-Topic Data Models
# ==========================================

class Flashcard(BaseModel):
    id: str
    front: str
    back: str
    question: str
    answer: str
    topic: str
    difficulty: str = Field(default="medium")
    created_at: datetime = Field(default_factory=utc_now)


class GenerateFlashcardsRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to generate flashcards for")
    num_cards: Optional[int] = Field(default=5, ge=1, le=20, description="Number of cards to generate (1-20)")
    difficulty: Optional[str] = Field(default="medium", description="Difficulty level (easy, medium, hard)")
    content: Optional[str] = Field(default=None, description="Optional raw text / notes to extract flashcards from")


class GenerateFlashcardsResponse(BaseModel):
    success: bool = True
    topic: str
    total_cards: int
    cards: List[Flashcard]


class FlashcardReviewRequest(BaseModel):
    flashcard_id: str = Field(..., min_length=1, description="Unique identifier of the flashcard")
    topic: str = Field(..., min_length=1, description="Topic of the flashcard")
    status: Literal["known", "still_learning"] = Field(..., description="Review status: 'known' or 'still_learning'")
    user_id: Optional[str] = Field(default=None, description="Optional user ID; inferred from auth token if available")


class FlashcardReview(BaseModel):
    user_id: str
    flashcard_id: str
    topic: str
    status: Literal["known", "still_learning"]
    date_reviewed: datetime = Field(default_factory=utc_now)
    # Schema alignment with quiz results for weak-topic detection
    item_type: str = Field(default="flashcard", description="Type of learning item: 'flashcard' or 'quiz'")
    is_weak: bool = Field(default=False, description="True if status is 'still_learning' or incorrect")


class WeakTopicSummary(BaseModel):
    topic: str
    total_reviews: int
    known_count: int
    still_learning_count: int
    mastery_score: float
    is_weak: bool


class TopicReviewStatsResponse(BaseModel):
    user_id: str
    weak_topics: List[WeakTopicSummary]
    total_reviews: int
