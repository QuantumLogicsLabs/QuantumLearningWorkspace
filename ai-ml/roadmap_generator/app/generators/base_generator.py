from abc import ABC, abstractmethod
from typing import List

from roadmap_generator.app.models.topic import Topic
from roadmap_generator.app.models.roadmap import Roadmap


class BaseGenerator(ABC):
    """
    Base class for roadmap generators. Mirrors quiz_generator's
    BaseGenerator pattern so the two modules stay consistent in
    style, even though they don't depend on each other.
    """

    @abstractmethod
    def generate(
        self,
        topics: List[Topic],
        subject: str = "",
        step_count: int = 6,
    ) -> Roadmap:
        """
        Generate a study roadmap from the given topics.

        Parameters:
            topics (List[Topic]): The subject(s)/topic(s) to build a roadmap for.
            subject (str): Optional overall subject/title for the roadmap.
            step_count (int): Target number of steps in the roadmap.

        Returns:
            Roadmap: A structured, ordered study roadmap.
        """
        pass
