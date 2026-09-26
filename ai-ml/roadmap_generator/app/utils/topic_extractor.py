"""
Topic extraction for mode="document" roadmap generation.

Uses YAKE (unsupervised keyword extraction — no API key, no cost,
runs locally) to pull candidate topic phrases out of a document's
raw text. Reuses the exact YAKE settings quiz_generator's config.py
already defines, rather than duplicating magic numbers.
"""

import yake

from quiz_generator.app.config import (
    YAKE_MAX_KEYWORDS,
    YAKE_NGRAM_SIZE,
    YAKE_DEDUP_THRESHOLD,
)


def extract_topics(text: str, max_keywords: int = None) -> list[str]:
    """
    Extracts candidate topic/keyword phrases from raw text.

    Returns a list of phrase strings, most relevant first (YAKE
    scores lower = more relevant, so we sort ascending by score).
    Returns an empty list for empty/whitespace-only input.
    """
    if not text or not text.strip():
        return []

    extractor = yake.KeywordExtractor(
        n=YAKE_NGRAM_SIZE,
        dedupLim=YAKE_DEDUP_THRESHOLD,
        top=max_keywords or YAKE_MAX_KEYWORDS,
    )
    keywords = extractor.extract_keywords(text)
    keywords.sort(key=lambda pair: pair[1])

    return [phrase for phrase, _score in keywords]
