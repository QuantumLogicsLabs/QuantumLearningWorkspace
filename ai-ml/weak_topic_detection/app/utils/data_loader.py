import json
from pathlib import Path


def load_json_data(file_path: str) -> list[dict]:
    """Load quiz-result data from a JSON file."""

    path = Path(file_path)

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)