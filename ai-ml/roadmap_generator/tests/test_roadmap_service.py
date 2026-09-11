import pytest

from roadmap_generator.app.config import GROQ_API_KEY
from roadmap_generator.app.services.roadmap_service import RoadmapService

requires_groq = pytest.mark.skipif(
    not GROQ_API_KEY,
    reason="GROQ_API_KEY not set — skipping tests that call the live Groq API.",
)


def test_generate_roadmap_rejects_empty_topic_list():
    service = RoadmapService()

    with pytest.raises(ValueError):
        service.generate_roadmap([])


def test_generate_roadmap_rejects_blank_topic_name():
    service = RoadmapService()

    with pytest.raises(ValueError):
        service.generate_roadmap(["", "  "])


def test_generate_roadmap_rejects_out_of_range_step_count():
    service = RoadmapService()

    with pytest.raises(ValueError):
        service.generate_roadmap(["Algebra"], step_count=1)  # below MIN_STEP_COUNT

    with pytest.raises(ValueError):
        service.generate_roadmap(["Algebra"], step_count=100)  # above MAX_STEP_COUNT


@requires_groq
def test_generate_roadmap_end_to_end():
    service = RoadmapService()

    roadmap = service.generate_roadmap(
        ["Recursion", "Dynamic programming"],
        subject="Algorithms",
        step_count=4,
        priorities={"Recursion": "high"},
    )

    assert roadmap.subject == "Algorithms"
    assert roadmap.total_steps == 4
