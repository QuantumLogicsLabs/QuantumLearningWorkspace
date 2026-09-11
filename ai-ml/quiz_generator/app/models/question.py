from __future__ import annotations
from typing import List, Optional

from pydantic import BaseModel, Field


class Question(BaseModel):
    """
    Represents a single generated quiz question.
    """

    question: str = Field(
        ...,
        description="The question statement."
    )

    question_id: str = Field(
        ...,
        description="Unique ID linking this question to its answer."
    )

    topic: str = Field(
        default="",
        description="Topic this question was generated from."
    )

    question_type: str = Field(
        ...,
        description="Type of question (mcq, true_false, fill_blank, short_answer)."
    )

    options: Optional[List[str]] = Field(
        default=None,
        description="Answer options for MCQ questions."
    )

    answer: str = Field(
        ...,
        description="Correct answer."
    )

    difficulty: str = Field(
        default="medium",
        description="Difficulty level (easy, medium, hard)."
    )

    explanation: Optional[str] = Field(
        default=None,
        description="Optional explanation of the correct answer."
    )

