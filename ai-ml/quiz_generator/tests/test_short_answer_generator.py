from app.generators.short_answer_generator import ShortAnswerGenerator


def main():
    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science that enables
    machines to simulate human intelligence. AI includes machine learning,
    natural language processing, computer vision, and robotics.
    """

    generator = ShortAnswerGenerator()

    result = generator.generate(sample_text)

    print("\n========== Generated Short Answer Questions ==========\n")
    print(result)


if __name__ == "__main__":
    main()