from roadmap_generator.app.generators.roadmap_generator import RoadmapGenerator
from roadmap_generator.app.models.topic import Topic
from roadmap_generator.app.models.roadmap import Roadmap
from roadmap_generator.app.validators.topic_validator import (
    validate_topic_names,
    validate_step_count,
)
from roadmap_generator.app.config import DEFAULT_STEP_COUNT


class RoadmapService:
    """
    Coordinates the roadmap-generation workflow. This is the
    integration point other code (a future API layer, or another
    module) should call, rather than using RoadmapGenerator directly.
    """

    def __init__(self):
        self.generator = RoadmapGenerator()

    def generate_roadmap(
        self,
        topic_names: list[str],
        subject: str = "",
        step_count: int = DEFAULT_STEP_COUNT,
        priorities: dict[str, str] | None = None,
    ) -> Roadmap:
        """
        Generates a study roadmap from a plain list of topic names.

        priorities: optional {topic_name: "high"|"normal"|"low"} map.
        This is how a caller (e.g. a future weak-topic integration)
        could nudge topic ordering WITHOUT this module importing or
        depending on that other module — the caller does the mapping,
        this service just accepts plain data.
        """
        validate_topic_names(topic_names)
        validate_step_count(step_count)

        priorities = priorities or {}
        topics = [
            Topic(name=name, priority=priorities.get(name))
            for name in topic_names
        ]

        return self.generator.generate(topics, subject=subject, step_count=step_count)
