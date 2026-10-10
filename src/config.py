"""Central configuration: file locations, pipeline modes and thresholds."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
WEB_DIR = BASE_DIR / "web"

QUERIES_CSV = DATA_DIR / "queries.csv"
KNOWLEDGE_BASE_CSV = DATA_DIR / "knowledge_base.csv"
MODULES_CSV = DATA_DIR / "modules.csv"

# Baseline = rule-based matching only (exact + keyword).
# Enhanced = full pipeline (adds the intent classifier and semantic retrieval).
MODE_BASELINE = "baseline"
MODE_ENHANCED = "enhanced"
MODES = (MODE_BASELINE, MODE_ENHANCED)
DEFAULT_MODE = MODE_ENHANCED

# A stage only answers when it is at least this sure; otherwise the query
# drops to the next stage and, finally, to the fallback response.
CLASSIFIER_THRESHOLD = 0.30
RETRIEVAL_THRESHOLD = 0.55

FALLBACK_INTENT = "fallback"
FALLBACK_RESPONSE = (
    "Sorry, I don't have an answer for that yet. I've recorded your question so it "
    "can be reviewed. Try rephrasing it, or contact your course leader for help."
)
