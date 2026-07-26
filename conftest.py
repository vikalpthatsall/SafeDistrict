import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# backend/config.py's get_settings() is lazy (lru_cache) now, so most modules
# no longer need GROQ_API_KEY just to import. backend/main.py is the one
# holdout — it still calls get_settings().allowed_origins at module level to
# build the CORS origin list, and test_api.py imports backend.main — so this
# is still required, just for a narrower reason than before. Confirmed by
# temporarily removing this line: only test_api.py's 7 tests failed, the
# other 21 (which never touch backend.main) passed fine without it.
# setdefault (not direct assignment) means a real key from an actual .env /
# real environment is never overwritten.
os.environ.setdefault("GROQ_API_KEY", "test-placeholder-key-not-real")

# backend_api_key is also a required Settings field now (Session 16's API-key
# auth) — same reasoning as GROQ_API_KEY above.
os.environ.setdefault("BACKEND_API_KEY", "test-placeholder-api-key-not-real")
