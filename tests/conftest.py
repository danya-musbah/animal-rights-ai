"""
conftest.py
-----------
Ensures the project root is on sys.path so `import backend...` works when
running pytest from the project root, and forces demo-mode-safe env vars
so tests never accidentally try to hit real external services.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force a clean, deterministic test environment: no real Supabase/LLM calls.
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("EMBEDDING_API_KEY", "")
os.environ.setdefault("FORCE_DEMO_MODE", "true")
