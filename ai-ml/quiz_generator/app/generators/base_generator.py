from __future__ import annotations
from abc import ABC, abstractmethod

from quiz_generator.app.models.question import Question


class BaseGenerator(ABC):
    """
    Base class for all quiz generators.
    Every quiz generator (MCQ, True/False, Fill in the Blank,
    Short Answer) will inherit from this class.
    """

    @abstractmethod
    def generate(
        self,
        text: str,
        number_of_questions: int = 5,
        difficulty: str = "medium",
        topic: str = "",
    ) -> list[Question]:
        """
        Generate quiz questions from the given text.

        Parameters:
            text (str): Input text from which questions are generated.
            number_of_questions (int): How many questions to generate.
            difficulty (str): Difficulty level (easy, medium, hard).
            topic (str): Topic label to attach to each generated question.

        Returns:
            list[Question]: A list of generated, structured questions.
        """
        pass
