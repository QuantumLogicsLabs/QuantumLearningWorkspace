from app.models.quiz_result import QuizResult
from app.validators.quiz_result_validator import QuizResultValidator


def main():
    valid_result = QuizResult(
        user_id="user_001",
        question_id="q001",
        topic="Machine Learning",
        selected_answer="A",
        correct_answer="B",
        is_correct=False,
        date_taken="2026-08-01",
    )

    invalid_result = QuizResult(
        user_id="",
        question_id="q002",
        topic="Machine Learning",
        selected_answer="A",
        correct_answer="B",
        is_correct=False,
        date_taken="2026-08-01",
    )

    print("Valid result:", QuizResultValidator.validate(valid_result))
    print("Invalid result:", QuizResultValidator.validate(invalid_result))


if __name__ == "__main__":
    main()