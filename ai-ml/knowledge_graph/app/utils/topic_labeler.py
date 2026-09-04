"""
Generates a short, human-readable label explaining why two chunks of
text are related — using shared keyword overlap, not an LLM. Keeps
this free of any paid API dependency.
"""
import re
from collections import Counter

# Small built-in stopword list — enough to filter common noise words
# without pulling in a heavier NLP dependency for this lightweight task.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "in", "on", "at", "to", "for", "of", "with", "by", "as", "that",
    "this", "it", "be", "from", "which", "these", "those", "their",
    "its", "has", "have", "had", "not", "can", "will", "would", "also",
}


def _extract_keywords(text: str, top_n: int = 15) -> set:
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    words = [w for w in words if w not in _STOPWORDS]
    most_common = [w for w, _ in Counter(words).most_common(top_n)]
    return set(most_common)


def generate_label(text_a: str, text_b: str, max_terms: int = 3) -> str:
    """
    Returns a short label like "shared terms: neural networks, training"
    based on keyword overlap between two texts. Returns a generic
    fallback label if no meaningful overlap is found.
    """
    keywords_a = _extract_keywords(text_a)
    keywords_b = _extract_keywords(text_b)
    shared = keywords_a & keywords_b

    if not shared:
        return "related topics"

    top_shared = sorted(shared)[:max_terms]
    return f"shared terms: {', '.join(top_shared)}"
