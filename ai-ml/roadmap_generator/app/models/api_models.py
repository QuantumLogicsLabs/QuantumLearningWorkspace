from typing import Optional

from pydantic import BaseModel, Field


class GenerateRoadmapRequest(BaseModel):
    """Request body for POST /generate-roadmap."""

    topic_names: list[str] = Field(
        ..., min_length=1, description="List of topic/subject names to build a roadmap for."
    )
    subject: str = Field(
        default="", description="Optional overall subject/title for the roadmap."
    )
    step_count: int = Field(
        default=6, ge=3, le=15, description="Number of roadmap steps to generate."
    )
    priorities: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional {topic_name: 'high'|'normal'|'low'} hints to influence ordering.",
    )


class GenerateRoadmapResponse(BaseModel):
    """Response body for POST /generate-roadmap."""

    success: bool
    message: str
    subject: str = ""
    steps: list[dict] = Field(default_factory=list)
    total_steps: int = 0