import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Groq Configuration
# ==========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = "openai/gpt-oss-120b"
# NOTE: llama-3.3-70b-versatile (used elsewhere, e.g. quiz_generator's
# config.py) has been deprecated by Groq. openai/gpt-oss-120b is
# their current recommended general-purpose/reasoning replacement as
# of this writing. Worth flagging to the team — quiz_generator likely
# hits the same 404 right now.


# ==========================================
# Roadmap Configuration
# ==========================================

DEFAULT_STEP_COUNT = 6
MIN_STEP_COUNT = 3
MAX_STEP_COUNT = 15