"""
Ensures ai-ml/ (the parent of this tests/ folder) is on sys.path, so
`import embedding.chroma_store`, `import ingestion...`, etc. resolve
the same way regardless of the working directory pytest is invoked
from. This is what main.py's docstrings assume ("Run from ai-ml/")
but wasn't guaranteed for test collection before this.
"""

import sys
from pathlib import Path

AI_ML_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))
