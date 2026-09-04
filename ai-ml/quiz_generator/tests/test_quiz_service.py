from app.services.quiz_service import QuizService


def main():
    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science that enables
    machines to simulate human intelligence. AI includes machine learning,
    natural language processing, computer vision, and robotics.
    """

    service = QuizService()

    result = service.generate_quiz(
        sample_text,
        "mcq"
    )

    print("\n========== Quiz Service Output ==========\n")
    print(result)


if __name__ == "__main__":
    main()