from typing import List, Optional

from pydantic import BaseModel, Field


class RoadmapStep(BaseModel):
    """A single stage in a generated study roadmap."""

    step_number: int = Field(..., description="Order of this step in the roadmap, starting at 1.")

    topic: str = Field(..., description="The topic covered in this step.")

    description: str = Field(
        ..., description="What the learner should focus on or do during this step."
    )

    estimated_duration: Optional[str] = Field(
        default=None,
        description="Rough suggested time for this step, e.g. '2-3 days'. Optional — LLM-provided, not a guarantee.",
    )


class Roadmap(BaseModel):
    """The full generated study roadmap for a subject or set of topics."""

    subject: str = Field(
        default="", description="Overall subject/title this roadmap covers, if provided."
    )

    steps: List[RoadmapStep] = Field(default_factory=list)

    total_steps: int = Field(default=0)
