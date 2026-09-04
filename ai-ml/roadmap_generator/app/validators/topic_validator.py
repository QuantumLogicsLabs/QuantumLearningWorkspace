from roadmap_generator.app.config import MIN_STEP_COUNT, MAX_STEP_COUNT


def validate_topic_names(topic_names: list[str]) -> None:
    """
    Validates raw topic name input before it's wrapped into Topic
    models. Raises ValueError on invalid input.
    """
    if not topic_names:
        raise ValueError("At least one topic name is required.")

    for name in topic_names:
        if not name or not name.strip():
            raise ValueError("Topic names must not be empty or whitespace-only.")


def validate_step_count(step_count: int) -> None:
    """Ensures the requested roadmap length is within a sane range."""
    if not (MIN_STEP_COUNT <= step_count <= MAX_STEP_COUNT):
        raise ValueError(
            f"step_count must be between {MIN_STEP_COUNT} and {MAX_STEP_COUNT} "
            f"(got {step_count})."
        )
