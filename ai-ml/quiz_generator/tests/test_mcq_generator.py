from app.generators.mcq_generator import MCQGenerator


def main():
    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science that enables
    machines to simulate human intelligence. AI includes machine learning,
    natural language processing, computer vision, and robotics.
    """

    generator = MCQGenerator()

    result = generator.generate(sample_text)

    print("\nGenerated MCQs:\n")
    print(result)


if __name__ == "__main__":
    main()
    