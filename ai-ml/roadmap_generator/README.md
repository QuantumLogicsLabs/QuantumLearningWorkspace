# Roadmap Generator

## Overview

The Roadmap Generator is a module of the QuantumLearningWorkspace project (ai-ml). It generates a simple, ordered study roadmap from subject/topic input using the Groq API.

This module is **general-purpose**: it generates a roadmap for a subject or set of topics, and does not depend on Weak-topic Detection or any other module's output. A caller may optionally supply per-topic `priority` hints (e.g. sourced from weak-topic results elsewhere) without this module importing or depending on that source.

## Features

- Ordered, sequential study roadmap generation
- Configurable step count
- Optional per-topic priority hints to influence ordering
- Service layer for integration with other code

## Project Structure

```
roadmap_generator/
│
├── app/
│   ├── api/           # reserved for API endpoints — not yet built,
│   │                     pending cross-team contract confirmation
│   ├── generators/
│   ├── models/
│   ├── services/
│   ├── utils/
│   ├── validators/
│   └── config.py
│
├── tests/
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

From the `ai-ml/` directory:

```bash
pip install -r roadmap_generator/requirements.txt
```

## Environment Variables

Add to your `.env` (same one used by the other ai-ml modules):

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Running the Tests

From `ai-ml/`:

```bash
pytest roadmap_generator/tests
```

Tests that call the live Groq API are skipped automatically if `GROQ_API_KEY` isn't set.

## Usage

```python
from roadmap_generator.app.services.roadmap_service import RoadmapService

service = RoadmapService()
roadmap = service.generate_roadmap(
    topic_names=["Recursion", "Dynamic programming"],
    subject="Algorithms",
    step_count=6,
)
```

## Supported Inputs

- `topic_names`: list of topic/subject name strings (required)
- `subject`: optional overall title for the roadmap
- `step_count`: number of steps to generate (3-15, default 6)
- `priorities`: optional `{topic_name: "high"|"normal"|"low"}` map

## Technologies Used

- Python 3.11
- Groq API
- Pydantic
- python-dotenv
- pytest

## Author

Developed as part of the QuantumLearningWorkspace Internship Project — Team Lambda.
