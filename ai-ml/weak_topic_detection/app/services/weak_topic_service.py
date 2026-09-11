from weak_topic_detection.app.detectors.weak_topic_detector import WeakTopicDetector
from weak_topic_detection.app.models.quiz_result import QuizResult
from weak_topic_detection.app.utils.data_loader import load_json_data
from weak_topic_detection.app.config import WEAK_TOPIC_THRESHOLD, MIN_TOPIC_ATTEMPTS


class WeakTopicService:
    """
    Loads quiz results and uses WeakTopicDetector
    to identify weak topics.
    """

    def __init__(
        self,
        data_file: str = "data/quiz_results.json",
        weak_threshold: float = WEAK_TOPIC_THRESHOLD,
min_attempts: int = MIN_TOPIC_ATTEMPTS,
    ):
        self.data_file = data_file
        self.detector = WeakTopicDetector(
            weak_threshold=weak_threshold,
            min_attempts=min_attempts,
        )

    def load_results(self) -> list[QuizResult]:
        """Load quiz results from the JSON file."""

        data = load_json_data(self.data_file)

        return [QuizResult(**item) for item in data]

    def get_weak_topics(self) -> list[dict]:
        """Return weak topics detected from quiz results."""

        results = self.load_results()

        return self.detector.detect(results)
