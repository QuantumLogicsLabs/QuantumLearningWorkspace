from weak_topic_detection.app.services.weak_topic_service import WeakTopicService


class WeakTopicAPI:
    """Interface for accessing weak-topic detection."""

    def __init__(self):
        self.service = WeakTopicService()

    def get_weak_topics(self):
        """Return the weak topics detected from quiz results."""
        return self.service.get_weak_topics()
