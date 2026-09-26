from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class GenerateRoadmapRequest(BaseModel):
    """
    Request body for POST /generate-roadmap.

    mode determines which fields are required:
      - "topic":            topic_names is required
      - "document":         document_id is required
      - "quiz_performance": no extra fields required — uses the
                             authenticated user's weak-topic results
    """

    mode: Literal["document", "topic", "quiz_performance"] = Field(
        ..., description="Which generation mode to use."
    )

    # mode="topic"
    topic_names: Optional[list[str]] = Field(
        default=None, description="Required when mode='topic'."
    )
    priorities: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional {topic_name: 'high'|'normal'|'low'} hints. Only used with mode='topic'.",
    )

    # mode="document"
    document_id: Optional[str] = Field(
        default=None, description="Required when mode='document'."
    )

    # shared across all modes
    subject: str = Field(default="", description="Optional overall subject/title for the roadmap.")
    step_count: int = Field(
        default=6, ge=3, le=15, description="Number of roadmap steps to generate."
    )

    @model_validator(mode="after")
    def _check_mode_specific_fields(self):
        if self.mode == "topic" and not self.topic_names:
            raise ValueError("topic_names is required when mode='topic'.")
        if self.mode == "document" and not self.document_id:
            raise ValueError("document_id is required when mode='document'.")
        return self


class GenerateRoadmapResponse(BaseModel):
    """Response body for POST /generate-roadmap."""

    success: bool
    message: str
    mode: str
    subject: str = ""
    steps: list[dict] = Field(default_factory=list)
    total_steps: int = 0
