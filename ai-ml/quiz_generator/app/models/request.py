from pydantic import BaseModel, Field


class QuizRequest(BaseModel):
    """
    Represents the input required to generate a quiz.
    """

    text: str = Field(
        ...,
        description="Input text from which questions will be generated."
    )

    question_type: str = Field(
        ...,
        description="Type of questions to generate."
    )

    number_of_questions: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of questions to generate."
    )

    difficulty: str = Field(
        default="medium",
        description="Difficulty level (easy, medium, hard)."
    )