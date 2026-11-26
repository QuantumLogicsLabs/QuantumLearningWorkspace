"""
Text Cleaning Module
---------------------
All extracted content (documents / pdf / youtube / web) passes through this
SAME cleaning process before being wrapped in the common schema.

Tasks:
- Remove extra spaces
- Remove empty lines
- Remove special / control characters
- Normalize text format
- Remove duplicated lines
"""

import re


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = raw_text.replace("\r", "\n")

    # Remove control / non-printable characters (keep basic punctuation & unicode letters)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse multiple spaces/tabs into one
    text = re.sub(r"[ \t]+", " ", text)

    # Split into lines, strip each, drop empties
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    # Remove duplicated consecutive lines (common in PDF/transcript extraction)
    deduped = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    # Join lines back with a single space to normalize into flowing text,
    # matching the spec's example: "Machine     Learning\nis a field"
    # -> "Machine Learning is a field"
    cleaned = " ".join(deduped)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned
