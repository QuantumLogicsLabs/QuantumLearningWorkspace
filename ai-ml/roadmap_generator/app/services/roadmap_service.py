from roadmap_generator.app.generators.roadmap_generator import RoadmapGenerator
from roadmap_generator.app.models.topic import Topic
from roadmap_generator.app.models.roadmap import Roadmap
from roadmap_generator.app.validators.topic_validator import (
    validate_topic_names,
    validate_step_count,
)
from roadmap_generator.app.utils.topic_extractor import extract_topics
from roadmap_generator.app.config import DEFAULT_STEP_COUNT

from embedding.chroma_store import get_document_chunks

# Cross-module import, same convention already used elsewhere
# (e.g. weak_topic_detection/app/main.py importing quiz_generator's
# auth) — not an HTTP call, a direct Python import within the same
# codebase.
from weak_topic_detection.app.services.weak_topic_service import WeakTopicService


class RoadmapService:
    """
    Coordinates roadmap generation across all three supported modes:
      - "topic"            — caller supplies topic names directly
      - "document"          — topics are extracted from an ingested document's content
      - "quiz_performance"  — topics come from Weak Topic Detection's output
    """

    def __init__(self):
        self.generator = RoadmapGenerator()
        self._weak_topic_service: WeakTopicService | None = None

    def _get_weak_topic_service(self) -> WeakTopicService:
        # Lazy — avoids paying WeakTopicService's init cost for
        # callers who only ever use mode="topic" or mode="document".
        if self._weak_topic_service is None:
            self._weak_topic_service = WeakTopicService()
        return self._weak_topic_service

    # ------------------------------------------------------------------
    # mode="topic" — unchanged from the original single-mode version
    # ------------------------------------------------------------------
    def generate_roadmap(
        self,
        topic_names: list[str],
        subject: str = "",
        step_count: int = DEFAULT_STEP_COUNT,
        priorities: dict[str, str] | None = None,
    ) -> Roadmap:
        validate_topic_names(topic_names)
        validate_step_count(step_count)

        priorities = priorities or {}
        topics = [Topic(name=name, priority=priorities.get(name)) for name in topic_names]

        return self.generator.generate(topics, subject=subject, step_count=step_count)

    # ------------------------------------------------------------------
    # mode="document"
    # ------------------------------------------------------------------
    def generate_roadmap_from_document(
        self,
        user_id: str,
        document_id: str,
        subject: str = "",
        step_count: int = DEFAULT_STEP_COUNT,
    ) -> Roadmap:
        """
        Builds a roadmap from an already-ingested document's own
        content. Pulls every chunk belonging to (document_id, user_id)
        — ownership enforced, so a caller can't generate a roadmap
        from a document that isn't theirs — extracts topic keywords
        with YAKE, then generates the same way mode="topic" does.
        """
        validate_step_count(step_count)

        chunks = get_document_chunks(document_id=document_id, user_id=user_id)
        if not chunks:
            raise ValueError(
                f"No content found for document_id '{document_id}'. It may not "
                "exist, may still be processing, or may belong to another user."
            )

        full_text = "\n\n".join(chunks)
        topic_names = extract_topics(full_text)
        if not topic_names:
            raise ValueError("Could not extract any topics from this document's content.")

        topics = [Topic(name=name) for name in topic_names]
        return self.generator.generate(
            topics,
            subject=subject or f"Document {document_id}",
            step_count=step_count,
        )

    # ------------------------------------------------------------------
    # mode="quiz_performance"
    # ------------------------------------------------------------------
    def generate_roadmap_from_quiz_performance(
        self,
        user_id: str,
        subject: str = "",
        step_count: int = DEFAULT_STEP_COUNT,
    ) -> Roadmap:
        """
        Builds a roadmap focused on topics the user is weak in, using
        Weak Topic Detection's output. Weak topics are marked "high"
        priority so the generator sequences them early.

        NOTE (known limitation — same one documented on Weak Topic
        Detection's own endpoint): WeakTopicService currently reads a
        static demo dataset, not this user's live quiz history, so
        results aren't truly personalized per-user yet. user_id is
        still threaded through so this works correctly once live
        per-user quiz ingestion exists — no further contract change
        needed here when that lands.
        """
        validate_step_count(step_count)

        weak_topics = self._get_weak_topic_service().get_weak_topics()
        if not weak_topics:
            raise ValueError(
                "No weak topics found — take a quiz first to get a personalized roadmap."
            )

        topic_names = [wt.get("topic", "Unknown Topic") for wt in weak_topics]
        topics = [Topic(name=name, priority="high") for name in topic_names]

        return self.generator.generate(
            topics,
            subject=subject or "Focus Areas From Your Quiz Performance",
            step_count=step_count,
        )
