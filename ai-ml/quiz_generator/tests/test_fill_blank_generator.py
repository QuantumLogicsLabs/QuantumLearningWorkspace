from app.generators.fill_blank_generator import FillBlankGenerator


def main():
    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science that enables
    machines to simulate human intelligence. AI includes machine learning,
    natural language processing, computer vision, and robotics.
    """

    generator = FillBlankGenerator()

    result = generator.generate(sample_text)

    print("\n========== Generated Fill in the Blank Questions ==========\n")
    print(result)


if __name__ == "__main__":
    main()