# AI Quiz Generator

## Overview

The AI Quiz Generator is a module of the QuantumLearningWorkspace project. It generates different types of quiz questions from input text using the Groq API.

## Features

- Multiple Choice Questions (MCQs)
- True/False Questions
- Fill in the Blank Questions
- Short Answer Questions
- Centralized QuizService for selecting question types

## Project Structure

```
quiz-generator/
│
├── app/
│   ├── api/
│   ├── generators/
│   ├── models/
│   ├── services/
│   ├── utils/
│   ├── validators/
│   └── config.py
│
├── tests/
├── .env
├── requirements.txt
└── README.md
```

## Installation

Clone the repository and install the required packages.

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Running the Tests

### MCQ Generator

```bash
python -m tests.test_mcq_generator
```

### True/False Generator

```bash
python -m tests.test_true_false_generator
```

### Fill in the Blank Generator

```bash
python -m tests.test_fill_blank_generator
```

### Short Answer Generator

```bash
python -m tests.test_short_answer_generator
```

### Quiz Service

```bash
python -m tests.test_quiz_service
```

## Supported Question Types

- mcq
- true_false
- fill_blank
- short_answer

## Technologies Used

- Python 3.11
- Groq API
- FastAPI
- Pydantic
- python-dotenv
- YAKE

## Author

Developed as part of the QuantumLearningWorkspace Internship Project.