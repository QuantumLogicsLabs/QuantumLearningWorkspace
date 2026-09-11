import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Groq Configuration
# ==========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


# ==========================================
# YAKE Configuration
# ==========================================

YAKE_MAX_KEYWORDS = 15
YAKE_NGRAM_SIZE = 2
YAKE_DEDUP_THRESHOLD = 0.9


# ==========================================
# Quiz Configuration
# ==========================================

DEFAULT_QUESTION_COUNT = 10

SUPPORTED_QUESTION_TYPES = [
    "mcq",
    "true_false",
    "fill_blank",
    "short_answer"
]