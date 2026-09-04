from dataclasses import dataclass


@dataclass
class QuizResult:
    user_id: str
    question_id: str
    topic: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    date_taken: str