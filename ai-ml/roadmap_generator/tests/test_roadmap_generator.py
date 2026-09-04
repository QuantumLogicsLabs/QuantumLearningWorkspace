import pytest

from roadmap_generator.app.config import GROQ_API_KEY
from roadmap_generator.app.generators.roadmap_generator import RoadmapGenerator
from roadmap_generator.app.models.topic import Topic
from roadmap_generator.app.models.roadmap import Roadmap

requires_groq = pytest.mark.skipif(
    not GROQ_API_KEY,
    reason="GROQ_API_KEY not set — skipping tests that call the live Groq API.",
)


@requires_groq
def test_generate_returns_roadmap_with_requested_step_count():
    generator = RoadmapGenerator()
    topics = [Topic(name="Photosynthesis"), Topic(name="Cellular respiration")]

    roadmap = generator.generate(topics, subject="Biology basics", step_count=4)

    assert isinstance(roadmap, Roadmap)
    assert roadmap.total_steps == 4
    assert len(roadmap.steps) == 4
    assert all(step.topic for step in roadmap.steps)
    assert all(step.description for step in roadmap.steps)


@requires_groq
def test_generate_steps_are_sequentially_numbered():
    generator = RoadmapGenerator()
    topics = [Topic(name="Linear algebra")]

    roadmap = generator.generate(topics, subject="Linear algebra", step_count=3)

    step_numbers = [s.step_number for s in roadmap.steps]
    assert step_numbers == sorted(step_numbers)


def test_generate_raises_on_empty_topics():
    generator = RoadmapGenerator()

    with pytest.raises(ValueError):
        generator.generate([], subject="Nothing")
