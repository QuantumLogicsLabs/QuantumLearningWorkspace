"""
Ensures ai-ml/ (two levels up from this tests/ folder) is on sys.path,
so `import roadmap_generator.app...` resolves regardless of the
working directory pytest is invoked from. Same fix as ai-ml/tests/conftest.py.
"""

import sys
from pathlib import Path

AI_ML_ROOT = Path(__file__).resolve().parent.parent.parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))