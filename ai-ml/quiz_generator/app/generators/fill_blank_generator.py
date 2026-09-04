from __future__ import annotations
import json
import uuid

from groq import Groq

from quiz_generator.app.generators.base_generator import BaseGenerator
from quiz_generator.app.config import GROQ_API_KEY, GROQ_MODEL
from quiz_generator.app.models.question import Question


class FillBlankGenerator(BaseGenerator):
    """
    Generator responsible for creating Fill in the Blank questions
    from the provided text using the Groq API.
    """

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(
        self,
        text: str,
        number_of_questions: int = 5,
        difficulty: str = "medium",
        topic: str = "",
    ) -> list[Question]:
        """
        Generate Fill in the Blank questions using the Groq API, returning
        structured Question objects (not raw text).
        """
        prompt = f"""
        Generate exactly {number_of_questions} Fill in the Blank questions
        from the following text.

        Rules:
        - Replace only one important word or phrase in each sentence with a blank (_____).
        - Clearly mark the correct answer (the word/phrase that fills the blank).
        - Questions should cover different concepts from the text.
        - Keep the difficulty at {difficulty} level.

        Respond with ONLY a JSON array, no other text, in this exact shape:
        [
          {{
            "question": "... _____ ...",
            "answer": "...",
            "explanation": "..."
          }}
        ]

        Text:
        {text}
        """

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        raw = response.choices[0].message.content or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"FillBlankGenerator: could not parse LLM response as JSON: {exc}"
            ) from exc

        questions: list[Question] = []
        for item in items:
            questions.append(
                Question(
                    question=item["question"],
                    question_id=str(uuid.uuid4()),
                    topic=topic,
                    question_type="fill_blank",
                    options=None,
                    answer=item["answer"],
                    difficulty=difficulty,
                    explanation=item.get("explanation"),
                )
            )
        return questions
