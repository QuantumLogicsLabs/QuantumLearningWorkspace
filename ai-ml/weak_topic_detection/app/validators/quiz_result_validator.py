from weak_topic_detection.app.models.quiz_result import QuizResult


class QuizResultValidator:
    """Validates quiz-result data before processing."""

    REQUIRED_FIELDS = {
        "user_id",
        "question_id",
        "topic",
        "selected_answer",
        "correct_answer",
        "is_correct",
        "date_taken",
    }

    @classmethod
    def validate(cls, result: QuizResult) -> bool:
        """Return True when a quiz result contains valid required data."""

        if not result.user_id:
            return False

        if not result.question_id:
            return False

        if not result.topic:
            return False

        if not isinstance(result.is_correct, bool):
            return False

        if not result.date_taken:
            return False

        return True
