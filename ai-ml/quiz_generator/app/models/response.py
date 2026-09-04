from typing import List

from pydantic import BaseModel, Field

from app.models.question import Question


class QuizResponse(BaseModel):
    """
    Represents the response returned after quiz generation.
    """

    success: bool = Field(
        ...,
        description="Indicates whether quiz generation was successful."
    )

    message: str = Field(
        ...,
        description="Status message."
    )

    questions: List[Question] = Field(
        default_factory=list,
        description="List of generated quiz questions."
    )