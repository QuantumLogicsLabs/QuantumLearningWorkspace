from app.detectors.weak_topic_detector import WeakTopicDetector
from app.models.quiz_result import QuizResult


def main():
    results = [
        # 3 attempts — should be evaluated
        QuizResult(
            user_id="user_001",
            question_id="q1",
            topic="Machine Learning",
            selected_answer="A",
            correct_answer="B",
            is_correct=False,
            date_taken="2026-08-01",
        ),
        QuizResult(
            user_id="user_001",
            question_id="q2",
            topic="Machine Learning",
            selected_answer="B",
            correct_answer="B",
            is_correct=True,
            date_taken="2026-08-02",
        ),
        QuizResult(
            user_id="user_001",
            question_id="q3",
            topic="Machine Learning",
            selected_answer="A",
            correct_answer="B",
            is_correct=False,
            date_taken="2026-08-03",
        ),

        # Only 2 attempts — should be ignored
        QuizResult(
            user_id="user_001",
            question_id="q4",
            topic="Python",
            selected_answer="A",
            correct_answer="B",
            is_correct=False,
            date_taken="2026-08-01",
        ),
        QuizResult(
            user_id="user_001",
            question_id="q5",
            topic="Python",
            selected_answer="A",
            correct_answer="B",
            is_correct=False,
            date_taken="2026-08-02",
        ),
    ]

    detector = WeakTopicDetector(
        weak_threshold=0.60,
        min_attempts=3,
    )

    weak_topics = detector.detect(results)

    print("\n========== Minimum Attempt Rule Test ==========\n")

    for topic in weak_topics:
        print(
            f"{topic['topic']} - "
            f"Accuracy: {topic['accuracy']}% - "
            f"Attempts: {topic['attempts']}"
        )


if __name__ == "__main__":
    main()