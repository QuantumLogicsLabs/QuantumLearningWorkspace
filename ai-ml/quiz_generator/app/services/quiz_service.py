from __future__ import annotations
# 1. Import the specific AI Generators
from quiz_generator.app.generators.mcq_generator import MCQGenerator
from quiz_generator.app.generators.true_false_generator import TrueFalseGenerator
from quiz_generator.app.generators.fill_blank_generator import FillBlankGenerator
from quiz_generator.app.generators.short_answer_generator import ShortAnswerGenerator

# 2. THE BRIDGE: Import the Embedder from your sibling folder
from embedding.embedder import Embedder


class QuizService:
    """
    The Bridge Service:
    Links the Vector Store (Memory) with the AI Generators (Logic).
    """

    def __init__(self):
        # [P0-1 fix] Embedder now searches the shared ChromaDB store —
        # the same one ingestion writes to — instead of the old,
        # disconnected Pinecone + MongoDB path.
        self.embedder = Embedder()

        # Initialize the AI Generators
        self.generators = {
            "mcq": MCQGenerator(),
            "true_false": TrueFalseGenerator(),
            "fill_blank": FillBlankGenerator(),
            "short_answer": ShortAnswerGenerator(),
        }

    def generate_quiz_from_topic(
        self,
        topic: str,
        question_type: str,
        user_id: str,
        number_of_questions: int = 5,
        difficulty: str = "medium",
        top_k: int = 3,
    ) -> dict:
        """
        RAG PIPELINE (The Bridge in action):
        1. Search: Finds relevant text chunks in the shared ChromaDB store,
           scoped to the authenticated user (Contract v1 Section 10 —
           quiz retrieval MUST be filtered by user_id).
        2. Generate: Feeds that specific text to the LLM to get structured questions.

        [Contract v1] Per Section 10, the existing question/answer split
        stays as-is: this returns BOTH a "questions" list (no answers)
        and an "answers" list (matched by question_id) — the shape
        Pluto's proxy already expects and stores server-side for
        grading. Do not strip "answers" from this return value; that
        was an earlier draft fix that turned out to contradict the
        signed-off contract.

        user_id is REQUIRED and must come from a verified JWT
        (see auth.py) — never from client input — so the search below
        can never cross into another user's content.
        """
        # A. Search for context based on the user's topic, scoped to
        #    this user's own content only.
        search_results = self.embedder.search(topic, top_k=top_k, user_id=user_id)

        if not search_results:
            return {
                "error": f"No relevant information found in your database for topic: '{topic}'"
            }

        # B. Combine all found text chunks into one context paragraph
        context_text = "\n\n".join([res["text"] for res in search_results])

        # C. Generate structured questions using the found text
        questions = self.generate_quiz(
            context_text,
            question_type,
            number_of_questions=number_of_questions,
            difficulty=difficulty,
            topic=topic,
        )

        return self._split_questions_and_answers(questions)

    def generate_quiz(
        self,
        text: str,
        question_type: str,
        number_of_questions: int = 5,
        difficulty: str = "medium",
        topic: str = "",
    ) -> list:
        """
        Selects the correct generator and returns a list of structured
        Question objects (not raw text, not a mixed dict).
        """
        if question_type not in self.generators:
            raise ValueError(
                f"Unsupported question type: {question_type}. "
                "Use: mcq, true_false, fill_blank, or short_answer"
            )

        return self.generators[question_type].generate(
            text,
            number_of_questions=number_of_questions,
            difficulty=difficulty,
            topic=topic,
        )

    @staticmethod
    def _split_questions_and_answers(questions: list) -> dict:
        """
        Splits a list of Question objects into two separate lists:
        one safe to send to the frontend before submission (no answers),
        and one kept server-side for grading. Per Contract v1 Section 10,
        this split — and its presence in the /generate-quiz response —
        is the intended, documented design; it is not being removed.
        """
        public_questions = []
        answers = []

        for q in questions:
            public_questions.append(
                {
                    "question_id": q.question_id,
                    "question": q.question,
                    "question_type": q.question_type,
                    "options": q.options,
                    "difficulty": q.difficulty,
                    "topic": q.topic,
                }
            )
            answers.append(
                {
                    "question_id": q.question_id,
                    "answer": q.answer,
                    "explanation": q.explanation,
                }
            )

        return {"questions": public_questions, "answers": answers}