# config.py
"""
Central configuration: file locations, model names, and tunable constants.
Keeping these in one place means every module (data loading, RAG, LLM,
recommender, outbreak engine) agrees on where things live.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
CHROMA_DIR = os.path.join(MODELS_DIR, "chroma_db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "ayush_ai.db")

# Primary knowledge sources. Both are loaded into the SAME corpus that
# backs RAG, the herb/diet/yoga recommender, and the NER gazetteer.
CSV_KNOWLEDGE_PATH = os.path.join(DATA_DIR, "ayurveda_dataset.csv")
XLSX_KNOWLEDGE_PATH = os.path.join(DATA_DIR, "AyurGenixAI_Dataset.xlsx")

# Gap-analysis list: diseases NOT covered by the two datasets above, each
# with its classical Ayurvedic/Sanskrit equivalent name only (no herbs,
# diet, or remedies -- those still need expert/classical-text mapping).
# Loaded as clearly-flagged "stub" records (see KnowledgeBase._load_not_there)
# so the system can recognise the disease name and say "not yet covered"
# instead of either staying silent or fabricating a generic remedy.
NOT_THERE_CSV_PATH = os.path.join(DATA_DIR, "not_there.csv")

# HF_TOKEN + BhashaBench-Ayur are OPTIONAL and used only for a separate
# "knowledge self-test" endpoint (evaluating the LLM), never for treatment
# retrieval â€” it's an exam/MCQ dataset, not a remedy corpus. See README.
HF_TOKEN = os.environ.get("HF_TOKEN", "")
BHASHABENCH_DATASET = "bharatgenai/BhashaBench-Ayur"
# None = load the full split (~15k questions/language -- it's text-only, so
# memory isn't a concern). Set to an int (e.g. via BHASHABENCH_MAX_ROWS env
# var) to cap load time during development. When capped, knowledge_base.py
# takes a SEEDED RANDOM SAMPLE, not the first N rows, so a capped set still
# covers the dataset's topics/difficulty levels roughly proportionally
# instead of whatever happened to be first in the file.
_bb_max_rows_env = os.environ.get("BHASHABENCH_MAX_ROWS", "")
BHASHABENCH_MAX_ROWS = int(_bb_max_rows_env) if _bb_max_rows_env.strip() else None

# Embedding + LLM model names (only used if the optional heavy deps in
# requirements.txt are installed; everything degrades gracefully otherwise)
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
LLM_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct" #"Qwen/Qwen2.5-3B-Instruct"
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-hi-en"
WHISPER_MODEL_SIZE = "base"

RAG_COLLECTION_NAME = "ayush_knowledge_corpus"
RAG_TOP_K = 4

# Districts with approximate lat/lon, used for geospatial outbreak
# clustering (DBSCAN on real coordinates rather than an unused text field).
DISTRICT_COORDS = {
    "Varanasi": (25.3176, 82.9739),
    "Jaipur": (26.9124, 75.7873),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Haridwar": (29.9457, 78.1642),
    "Mysuru": (12.2958, 76.6394),
    "Lucknow": (26.8467, 80.9462),
    "Patna": (25.5941, 85.1376),
    "Bhopal": (23.2599, 77.4126),
    "Nagpur": (21.1458, 79.0882),
    "Guwahati": (26.1445, 91.7362),
}

RANDOM_SEED = 42
