from collections import defaultdict
from weak_topic_detection.app.models.quiz_result import QuizResult


class WeakTopicDetector:
    """
    Detects weak topics based on quiz performance.
    """

    def __init__(self, weak_threshold: float = 0.60, min_attempts: int = 3):
        self.weak_threshold = weak_threshold
        self.min_attempts = min_attempts

    def detect(self, results: list[QuizResult]) -> list[dict]:
        """
        Identify weak topics from quiz results.

        A topic is considered weak when:
        - It has at least the minimum number of attempts.
        - Its accuracy is below the weak-topic threshold.
        """

        topic_results = defaultdict(list)

        # Group quiz results by topic
        for result in results:
            topic_results[result.topic].append(result)

        weak_topics = []

        # Calculate accuracy for each topic
        for topic, topic_attempts in topic_results.items():

            total_attempts = len(topic_attempts)

            # Ignore topics with insufficient attempts
            if total_attempts < self.min_attempts:
                continue

            correct_answers = sum(
                result.is_correct for result in topic_attempts
            )

            accuracy = correct_answers / total_attempts

            # Identify weak topics
            if accuracy < self.weak_threshold:
                weak_topics.append({
                    "topic": topic,
                    "accuracy": round(accuracy * 100, 2),
                    "attempts": total_attempts
                })

        # Weakest topics first
        weak_topics.sort(key=lambda item: item["accuracy"])

        return weak_topics
