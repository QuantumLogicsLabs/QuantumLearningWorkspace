from pathlib import Path

from weak_topic_detection.app.detectors.weak_topic_detector import WeakTopicDetector
from weak_topic_detection.app.models.quiz_result import QuizResult
from weak_topic_detection.app.utils.data_loader import load_json_data
from weak_topic_detection.app.config import WEAK_TOPIC_THRESHOLD, MIN_TOPIC_ATTEMPTS

# [Fix] weak_topic_detection/app/services/ -> weak_topic_detection/data/
# Computed from this file's own location so it resolves correctly
# regardless of the process's working directory (previously a bare
# relative "data/quiz_results.json" string, which only worked if the
# process happened to be started from inside weak_topic_detection/
# itself — it broke for any other caller, e.g. roadmap_generator's
# quiz_performance mode, or this module's own HTTP endpoint, when run
# from ai-ml/ as the docs instruct).
DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "quiz_results.json"


class WeakTopicService:
    """
    Loads quiz results and uses WeakTopicDetector
    to identify weak topics.
    """

    def __init__(
        self,
        data_file: str = None,
        weak_threshold: float = WEAK_TOPIC_THRESHOLD,
        min_attempts: int = MIN_TOPIC_ATTEMPTS,
    ):
        self.data_file = data_file or DEFAULT_DATA_FILE
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