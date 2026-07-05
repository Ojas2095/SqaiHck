# """
# AYUSH System â€” Database + Synthetic Data + Voice EHR + Outbreak Detection
# =========================================================================
# Self-contained module providing:
#   1. SQLite database schema & synthetic data generation
#   2. VoiceEHRCreator   â€” microphone-based EHR entry with Ayurvedic NER
#   3. DiseaseOutbreakDetector â€” anomaly detection & trend forecasting

# Tables:
#   â€¢ ehr_records       â€“ Electronic Health Records with Ayurvedic context
#   â€¢ treatments        â€“ Prescribed Ayurvedic treatments and feedback
#   â€¢ outbreak_alerts   â€“ District-level disease outbreak anomalies
#   â€¢ patient_history   â€“ Longitudinal patient demographics & outcomes

# Voice Features:
#   â€¢ Real microphone capture via speech_recognition + pyaudio
#   â€¢ Hindi (hi-IN) and English (en-US) speech recognition
#   â€¢ Bilingual AYUSH medical dictionary for entity extraction
#   â€¢ Hindiâ†’English translation via googletrans
#   â€¢ Graceful fallback to text input when mic is unavailable

# Outbreak Detection Features:
#   â€¢ Isolation Forest (scikit-learn) for anomaly detection
#   â€¢ Rolling averages (3-day, 7-day) for smoothing
#   â€¢ Severity classification (HIGH / MEDIUM / LOW)
#   â€¢ 7-day and 14-day moving average trend forecasting

# Usage:
#     python ayush_system.py
#     from ayush_system import VoiceEHRCreator, DiseaseOutbreakDetector
# """

# import sys
# import sqlite3
# import random
# import uuid
# import os
# import re
# import json
# import math
# from datetime import datetime, timedelta
# from functools import lru_cache

# # ANSI Colors (defined globally for all console rendering)
# C_GREEN = "\033[92m"
# C_YELLOW = "\033[93m"
# C_BLUE = "\033[94m"
# C_RED = "\033[91m"
# C_CYAN = "\033[96m"
# C_BOLD = "\033[1m"
# C_RESET = "\033[0m"

# # ---------------------------------------------------------------------------
# # Helper / Utility Functions for Windows safe CLI printing & validation
# # ---------------------------------------------------------------------------
# def safe_print(text: str = "", end: str = "\n") -> None:
#     """Print wrapper that gracefully handles encoding issues on Windows consoles."""
#     try:
#         sys.stdout.write(text + end)
#         sys.stdout.flush()
#     except UnicodeEncodeError:
#         # Fallback to pure ASCII characters replacing common emojis / non-ascii symbols
#         fallback = text
#         replacements = {
#             "âœ…": "[OK]", "âš ï¸": "[WARN]", "âŒ": "[ERROR]", "ðŸŽ™ï¸": "[MIC]",
#             "â±ï¸": "[TIME]", "ðŸ“Š": "[STATS]", "ðŸŒ¿": "[HERB]", "ðŸ“ˆ": "[TREND]",
#             "ðŸ“‹": "[PLAN]", "ðŸ€": "[AYUSH]", "ðŸ§¬": "[GENE]", "ðŸ”º": "[ALERT]",
#             "ðŸ›Žï¸": "[ALERT]", "ðŸšª": "[EXIT]", "ðŸŽ¤": "[MIC]", "ðŸš¨": "[ALERT]",
#             "ðŸ’Š": "[PLAN]", "ðŸ“œ": "[EVIDENCE]", "ðŸ“–": "[DOC]", "ðŸ”º": "[ALERT]",
#             "ðŸ™": "[NAMASTE]", "â”€": "-", "â•": "=", "âš¡": "[FAST]"
#         }
#         for emoji, representation in replacements.items():
#             fallback = fallback.replace(emoji, representation)
#         try:
#             sys.stdout.write(fallback.encode("ascii", errors="replace").decode("ascii") + end)
#             sys.stdout.flush()
#         except Exception:
#             # Absolute fallback
#             print(text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"), end=end)

# def clear_screen() -> None:
#     """Platform-independent screen clear."""
#     os.system("cls" if os.name == "nt" else "clear")

# def validate_patient_id(patient_id: str) -> bool:
#     """Check if the patient ID format is valid (e.g. PAT-XXXX)."""
#     return bool(re.match(r"^PAT-\d{4}$", patient_id))

# def print_splash_screen() -> None:
#     """Show a beautiful AYUSH clinical splash screen."""
#     clear_screen()
#     safe_print(f"{C_BOLD}{C_GREEN}")
#     safe_print("â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•—  â–ˆâ–ˆâ•— â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— ")
#     safe_print("â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•”â•â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—")
#     safe_print("â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â• â•šâ–ˆâ–ˆâ–ˆâ–ˆâ•”â• â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘")
#     safe_print("â–ˆâ–ˆâ•”â•â•â•â•   â•šâ–ˆâ–ˆâ•”â•  â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â•šâ•â•â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•‘")
#     safe_print("â–ˆâ–ˆâ•‘        â–ˆâ–ˆâ•‘   â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘")
#     safe_print("â•šâ•â•        â•šâ•â•    â•šâ•â•â•â•â•â• â•šâ•â•â•â•â•â•â•â•šâ•â•  â•šâ•â•â•šâ•â•  â•šâ•â•")
#     safe_print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
#     safe_print(f"      IMPACT Platform - AYUSH Clinical Grid       ")
#     safe_print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€" + C_RESET)

# def format_treatment_plan(rec: dict) -> str:
#     """Format treatment plan recommendations into a pretty card format."""
#     lines = []
#     lines.append("â”€" * 50)
#     lines.append(f"{C_BOLD}{C_GREEN}ðŸ“‹  PRESCRIBED PROTOCOL{C_RESET}")
#     lines.append("â”€" * 50)
#     lines.append(f"  Source:      {C_CYAN}{rec.get('source', 'Unknown')}{C_RESET}")
#     lines.append(f"  Confidence:  {C_GREEN}{rec.get('confidence_score', 0.0)*100:.1f}%{C_RESET}")
#     lines.append(f"  Herbs:       {C_YELLOW}{rec.get('herbs', 'Unspecified')}{C_RESET}")
#     lines.append(f"  Dietary:     {rec.get('diet', 'None')}")
#     lines.append(f"  Yoga/Asanas: {rec.get('yoga', 'None')}")
#     lines.append(f"  Lifestyle:   {rec.get('lifestyle', 'None')}")
#     lines.append("â”€" * 50)
#     return "\n".join(lines)

# # ---------------------------------------------------------------------------
# # Configuration
# # ---------------------------------------------------------------------------
# DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ayush.db")

# # ---------------------------------------------------------------------------
# # Domain constants (Ayurveda-specific)
# # ---------------------------------------------------------------------------
# PRAKRITI_TYPES = [
#     "Vata", "Pitta", "Kapha",
#     "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha",
#     "Tridosha (Sama)",
# ]

# SYMPTOMS_POOL = [
#     "joint pain", "fatigue", "indigestion", "headache", "skin rash",
#     "insomnia", "anxiety", "bloating", "constipation", "cough",
#     "fever", "body ache", "acidity", "weight gain", "hair loss",
#     "cold hands and feet", "dry skin", "excessive thirst",
#     "burning sensation", "nasal congestion", "loss of appetite",
#     "nausea", "dizziness", "muscle cramps", "irregular heartbeat",
#     "shortness of breath", "back pain", "swollen joints",
# ]

# DIAGNOSES_POOL = [
#     "Amavata (Rheumatoid Arthritis)", "Pandu (Anemia)",
#     "Prameha (Diabetes)", "Kushtha (Skin Disorders)",
#     "Jwara (Fever)", "Kasa (Cough)", "Shwasa (Asthma)",
#     "Arsha (Hemorrhoids)", "Udara Roga (Abdominal Disorders)",
#     "Hridroga (Heart Disease)", "Vatarakta (Gout)",
#     "Shula (Abdominal Pain)", "Atisara (Diarrhea)",
#     "Grahani (IBS)", "Kamala (Jaundice)",
#     "Rajayakshma (Tuberculosis)", "Unmada (Psychosis)",
#     "Apasmara (Epilepsy)", "Medoroga (Obesity)",
#     "Mukha Roga (Oral Diseases)",
# ]

# HERBS_POOL = [
#     "Ashwagandha", "Triphala", "Guduchi (Giloy)", "Brahmi",
#     "Shatavari", "Haridra (Turmeric)", "Tulsi", "Neem",
#     "Amalaki (Amla)", "Pippali", "Guggulu", "Yashtimadhu (Licorice)",
#     "Arjuna", "Shankhpushpi", "Bibhitaki", "Haritaki",
#     "Vacha", "Kutki", "Musta", "Punarnava",
#     "Dashamoola", "Bala", "Vidanga", "Chitraka",
# ]

# DIET_POOL = [
#     "warm cooked meals", "avoid cold/raw food", "light dinner before sunset",
#     "ghee with meals", "warm water throughout day", "seasonal fruits",
#     "avoid dairy", "reduce spicy food", "increase bitter greens",
#     "moong dal khichdi", "buttermilk post-lunch", "avoid fermented food",
#     "include turmeric milk at night", "rice water in morning",
#     "avoid heavy grains", "prefer barley and millet",
#     "soaked almonds in morning", "avoid excess salt",
# ]

# YOGA_POOL = [
#     "Surya Namaskar (12 rounds)", "Pranayama â€“ Anulom Vilom (15 min)",
#     "Bhujangasana", "Trikonasana", "Shavasana (guided relaxation)",
#     "Pawanmuktasana", "Vajrasana post meals", "Kapalbhati (10 min)",
#     "Meditation â€“ 20 min daily", "Tadasana", "Setu Bandhasana",
#     "Ardha Matsyendrasana", "Viparita Karani",
#     "Nadi Shodhana Pranayama", "Bhramari Pranayama",
# ]

# LIFESTYLE_POOL = [
#     "early to bed by 10 PM", "wake before sunrise",
#     "oil pulling with sesame oil", "Abhyanga (self-massage) daily",
#     "avoid screen time after 8 PM", "walk 30 min post dinner",
#     "Nasya with Anu Taila", "reduce caffeine intake",
#     "digital detox weekends", "sun exposure 15 min morning",
#     "journaling before sleep", "minimize daytime napping",
#     "practice gratitude meditation", "warm foot soak before bed",
# ]

# COMORBIDITIES_POOL = [
#     "Hypertension", "Type 2 Diabetes", "Hypothyroidism",
#     "Obesity", "Asthma", "PCOS", "Chronic Kidney Disease",
#     "Osteoarthritis", "Depression", "Anxiety Disorder",
#     "Hyperlipidemia", "Anemia", "Migraine",
# ]

# DISTRICTS = [
#     "Varanasi", "Jaipur", "Thiruvananthapuram", "Haridwar", "Mysuru",
# ]

# OUTBREAK_DISEASES = [
#     "Dengue", "Chikungunya", "Malaria", "Typhoid", "Leptospirosis",
# ]

# LANGUAGES = ["Hindi", "English", "Tamil", "Malayalam", "Kannada", "Marathi", "Bengali"]

# OUTCOMES = ["improved", "stable", "worsened", "remission", "ongoing_treatment"]


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------
# def _pick(pool: list, low: int = 1, high: int = 3) -> str:
#     """Pick between *low* and *high* random items from *pool* and return CSV."""
#     count = random.randint(low, min(high, len(pool)))
#     return ", ".join(random.sample(pool, count))


# def _random_date(start: datetime, end: datetime) -> str:
#     """Return a random ISO-format date string between *start* and *end*."""
#     delta = (end - start).days
#     offset = random.randint(0, max(delta, 0))
#     return (start + timedelta(days=offset)).strftime("%Y-%m-%d")


# def _generate_raw_text(symptoms: str, diagnosis: str, lang: str) -> tuple[str, str]:
#     """Simulate a raw clinical note and its English translation."""
#     raw = f"Patient presents with {symptoms}. Provisional diagnosis: {diagnosis}."

#     if lang != "English":
#         # Simulate that the original note was in another language
#         translated = raw
#         raw = f"[{lang} original] " + raw  # placeholder for non-English
#     else:
#         translated = raw

#     return raw, translated


# # ---------------------------------------------------------------------------
# # Database connection
# # ---------------------------------------------------------------------------
# def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
#     """Return a new SQLite connection with row-factory enabled."""
#     path = db_path or DB_PATH
#     conn = sqlite3.connect(path)
#     conn.row_factory = sqlite3.Row
#     conn.execute("PRAGMA journal_mode=WAL;")
#     conn.execute("PRAGMA foreign_keys=ON;")
#     return conn


# # ---------------------------------------------------------------------------
# # Schema creation
# # ---------------------------------------------------------------------------
# def init_database(db_path: str | None = None) -> None:
#     """Create all tables if they do not already exist."""
#     conn = get_db_connection(db_path)
#     cursor = conn.cursor()

#     cursor.executescript("""
#         -- Electronic Health Records
#         CREATE TABLE IF NOT EXISTS ehr_records (
#             id              TEXT PRIMARY KEY,
#             patient_id      TEXT NOT NULL,
#             visit_date      TEXT NOT NULL,
#             symptoms        TEXT,
#             diagnosis       TEXT,
#             prakriti        TEXT,
#             comorbidities   TEXT,
#             raw_text        TEXT,
#             translated_text TEXT,
#             language        TEXT
#         );

#         -- Ayurvedic Treatments
#         CREATE TABLE IF NOT EXISTS treatments (
#             id               TEXT PRIMARY KEY,
#             patient_id       TEXT NOT NULL,
#             date             TEXT NOT NULL,
#             herbs            TEXT,
#             diet             TEXT,
#             yoga             TEXT,
#             lifestyle        TEXT,
#             confidence_score REAL DEFAULT 0.0,
#             feedback_score   REAL,
#             approved         INTEGER DEFAULT 0
#         );

#         -- Disease Outbreak Alerts
#         CREATE TABLE IF NOT EXISTS outbreak_alerts (
#             id              TEXT PRIMARY KEY,
#             district        TEXT NOT NULL,
#             disease         TEXT NOT NULL,
#             anomaly_score   REAL DEFAULT 0.0,
#             date_detected   TEXT NOT NULL,
#             cases_reported  INTEGER DEFAULT 0
#         );

#         -- Patient History (longitudinal demographics & outcomes)
#         CREATE TABLE IF NOT EXISTS patient_history (
#             patient_id          TEXT PRIMARY KEY,
#             age                 INTEGER,
#             bmi                 REAL,
#             comorbidities_count INTEGER DEFAULT 0,
#             outcome             TEXT
#         );

#         -- Indexes for common queries
#         CREATE INDEX IF NOT EXISTS idx_ehr_patient      ON ehr_records(patient_id);
#         CREATE INDEX IF NOT EXISTS idx_ehr_visit_date   ON ehr_records(visit_date);
#         CREATE INDEX IF NOT EXISTS idx_treat_patient    ON treatments(patient_id);
#         CREATE INDEX IF NOT EXISTS idx_outbreak_district ON outbreak_alerts(district);
#         CREATE INDEX IF NOT EXISTS idx_outbreak_date    ON outbreak_alerts(date_detected);
#     """)

#     conn.commit()
#     conn.close()
#     print("âœ…  Database schema initialised.")


# # ---------------------------------------------------------------------------
# # Synthetic data generation
# # ---------------------------------------------------------------------------
# def generate_sample_data(db_path: str | None = None) -> None:
#     """
#     Populate the database with synthetic but realistic Ayurvedic data.

#     â€¢ 100 patients with random demographics
#     â€¢ Multiple EHR visits & treatment records per patient
#     â€¢ 120 days of daily case counts across 5 districts
#     â€¢ 2 simulated outbreak spikes injected into the time-series
#     """
#     conn = get_db_connection(db_path)
#     cursor = conn.cursor()

#     # Check if data already exists to avoid duplication
#     existing = cursor.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
#     if existing > 0:
#         print("âš ï¸  Data already exists â€” skipping generation.")
#         conn.close()
#         return

#     random.seed(42)  # reproducible data

#     now = datetime.now()
#     start_date = now - timedelta(days=365)
#     end_date = now

#     # ------------------------------------------------------------------
#     # 1. Generate 100 patients
#     # ------------------------------------------------------------------
#     patient_ids: list[str] = []

#     for i in range(100):
#         pid = f"PAT-{i+1:04d}"
#         patient_ids.append(pid)

#         age = random.randint(18, 85)
#         bmi = round(random.uniform(16.0, 38.0), 1)
#         n_comorbidities = random.choices([0, 1, 2, 3, 4], weights=[30, 30, 20, 12, 8])[0]
#         outcome = random.choice(OUTCOMES)

#         cursor.execute(
#             "INSERT INTO patient_history (patient_id, age, bmi, comorbidities_count, outcome) "
#             "VALUES (?, ?, ?, ?, ?)",
#             (pid, age, bmi, n_comorbidities, outcome),
#         )

#         # --- EHR records (1-5 visits per patient) ---
#         n_visits = random.randint(1, 5)
#         patient_comorbidities = (
#             _pick(COMORBIDITIES_POOL, 1, n_comorbidities) if n_comorbidities > 0 else "None"
#         )
#         prakriti = random.choice(PRAKRITI_TYPES)
#         lang = random.choice(LANGUAGES)

#         for _ in range(n_visits):
#             visit_date = _random_date(start_date, end_date)
#             symptoms = _pick(SYMPTOMS_POOL, 2, 5)
#             diagnosis = random.choice(DIAGNOSES_POOL)
#             raw_text, translated_text = _generate_raw_text(symptoms, diagnosis, lang)

#             cursor.execute(
#                 "INSERT INTO ehr_records "
#                 "(id, patient_id, visit_date, symptoms, diagnosis, prakriti, "
#                 " comorbidities, raw_text, translated_text, language) "
#                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                 (
#                     str(uuid.uuid4()),
#                     pid,
#                     visit_date,
#                     symptoms,
#                     diagnosis,
#                     prakriti,
#                     patient_comorbidities,
#                     raw_text,
#                     translated_text,
#                     lang,
#                 ),
#             )

#         # --- Treatment records (1-4 per patient) ---
#         n_treatments = random.randint(1, 4)
#         for _ in range(n_treatments):
#             t_date = _random_date(start_date, end_date)
#             herbs = _pick(HERBS_POOL, 2, 5)
#             diet = _pick(DIET_POOL, 2, 4)
#             yoga = _pick(YOGA_POOL, 1, 3)
#             lifestyle = _pick(LIFESTYLE_POOL, 1, 3)
#             confidence = round(random.uniform(0.55, 0.98), 2)
#             feedback = round(random.uniform(1.0, 5.0), 1) if random.random() > 0.3 else None
#             approved = 1 if confidence > 0.75 and random.random() > 0.2 else 0

#             cursor.execute(
#                 "INSERT INTO treatments "
#                 "(id, patient_id, date, herbs, diet, yoga, lifestyle, "
#                 " confidence_score, feedback_score, approved) "
#                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                 (
#                     str(uuid.uuid4()),
#                     pid,
#                     t_date,
#                     herbs,
#                     diet,
#                     yoga,
#                     lifestyle,
#                     confidence,
#                     feedback,
#                     approved,
#                 ),
#             )

#     # ------------------------------------------------------------------
#     # 2. Generate 120 days of outbreak surveillance data
#     # ------------------------------------------------------------------
#     surveillance_start = now - timedelta(days=120)

#     # Define 2 outbreak events: (district, disease, peak_day_offset, intensity)
#     outbreak_events = [
#         {"district": "Varanasi", "disease": "Dengue", "peak_day": 45, "intensity": 5.0},
#         {"district": "Thiruvananthapuram", "disease": "Leptospirosis", "peak_day": 90, "intensity": 4.2},
#     ]

#     for day_offset in range(120):
#         current_date = (surveillance_start + timedelta(days=day_offset)).strftime("%Y-%m-%d")

#         for district in DISTRICTS:
#             disease = random.choice(OUTBREAK_DISEASES)

#             # Baseline: 2-15 cases per day per district
#             base_cases = random.randint(2, 15)
#             anomaly_score = round(random.uniform(0.0, 0.3), 3)

#             # Inject outbreak spikes
#             for event in outbreak_events:
#                 if district == event["district"] and disease == event["disease"]:
#                     # Gaussian-like spike around the peak day
#                     distance = abs(day_offset - event["peak_day"])
#                     if distance <= 12:
#                         spike_factor = event["intensity"] * max(0, 1 - (distance / 12))
#                         extra_cases = int(base_cases * spike_factor)
#                         base_cases += extra_cases
#                         anomaly_score = round(min(1.0, 0.5 + spike_factor * 0.15), 3)

#             cursor.execute(
#                 "INSERT INTO outbreak_alerts "
#                 "(id, district, disease, anomaly_score, date_detected, cases_reported) "
#                 "VALUES (?, ?, ?, ?, ?, ?)",
#                 (
#                     str(uuid.uuid4()),
#                     district,
#                     disease,
#                     anomaly_score,
#                     current_date,
#                     base_cases,
#                 ),
#             )

#     conn.commit()
#     conn.close()

#     print("âœ…  Synthetic data generated successfully.")
#     print(f"   â€¢ 100 patients with EHR records & treatments")
#     print(f"   â€¢ 120 days Ã— 5 districts of outbreak surveillance")
#     print(f"   â€¢ 2 outbreak events injected (Dengue in Varanasi, Leptospirosis in Thiruvananthapuram)")


# # ---------------------------------------------------------------------------
# # Summary / verification
# # ---------------------------------------------------------------------------
# def print_summary(db_path: str | None = None) -> None:
#     """Print a quick summary of the database contents."""
#     conn = get_db_connection(db_path)
#     cursor = conn.cursor()

#     tables = {
#         "patient_history": "SELECT COUNT(*) FROM patient_history",
#         "ehr_records":     "SELECT COUNT(*) FROM ehr_records",
#         "treatments":      "SELECT COUNT(*) FROM treatments",
#         "outbreak_alerts": "SELECT COUNT(*) FROM outbreak_alerts",
#     }

#     print("\nðŸ“Š  Database Summary")
#     print("â”€" * 40)
#     for table, query in tables.items():
#         count = cursor.execute(query).fetchone()[0]
#         print(f"   {table:<20s} â†’ {count:>6,} rows")

#     # Sample outbreak spike
#     print("\nðŸ”º  Top outbreak alerts (by anomaly score):")
#     rows = cursor.execute(
#         "SELECT district, disease, anomaly_score, date_detected, cases_reported "
#         "FROM outbreak_alerts ORDER BY anomaly_score DESC LIMIT 5"
#     ).fetchall()
#     for r in rows:
#         print(f"   {r['district']:<25s} | {r['disease']:<15s} | "
#               f"score={r['anomaly_score']:.3f} | {r['date_detected']} | "
#               f"{r['cases_reported']} cases")

#     # Prakriti distribution
#     print("\nðŸ§¬  Prakriti distribution:")
#     rows = cursor.execute(
#         "SELECT prakriti, COUNT(*) as cnt FROM ehr_records "
#         "GROUP BY prakriti ORDER BY cnt DESC"
#     ).fetchall()
#     for r in rows:
#         print(f"   {r['prakriti']:<20s} â†’ {r['cnt']:>4} records")

#     conn.close()


# # ===========================================================================
# #  VOICE EHR CREATOR â€” Microphone-based EHR entry with Ayurvedic NER
# # ===========================================================================

# # ---------------------------------------------------------------------------
# # Bilingual AYUSH Medical Dictionary
# # ---------------------------------------------------------------------------
# AYUSH_MEDICAL_DICTIONARY: dict[str, dict] = {
#     # â”€â”€ Symptoms (English â†’ Hindi mapping + canonical name) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     "symptoms": {
#         # Pain & musculoskeletal
#         "joint pain":       {"hi": ["à¤œà¥‹à¤¡à¤¼à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¦à¤°à¥à¤¦", "à¤œà¥‹à¤¡à¤¼ à¤¦à¤°à¥à¤¦", "à¤—à¤ à¤¿à¤¯à¤¾ à¤¦à¤°à¥à¤¦"], "canonical": "joint pain"},
#         "back pain":        {"hi": ["à¤•à¤®à¤° à¤¦à¤°à¥à¤¦", "à¤ªà¥€à¤  à¤¦à¤°à¥à¤¦"], "canonical": "back pain"},
#         "body ache":        {"hi": ["à¤¬à¤¦à¤¨ à¤¦à¤°à¥à¤¦", "à¤¶à¤°à¥€à¤° à¤®à¥‡à¤‚ à¤¦à¤°à¥à¤¦", "à¤…à¤‚à¤— à¤¦à¤°à¥à¤¦"], "canonical": "body ache"},
#         "headache":         {"hi": ["à¤¸à¤¿à¤° à¤¦à¤°à¥à¤¦", "à¤¸à¤¿à¤°à¤¦à¤°à¥à¤¦", "à¤®à¤¾à¤¥à¥‡ à¤®à¥‡à¤‚ à¤¦à¤°à¥à¤¦"], "canonical": "headache"},
#         "muscle cramps":    {"hi": ["à¤®à¤¾à¤‚à¤¸à¤ªà¥‡à¤¶à¤¿à¤¯à¥‹à¤‚ à¤®à¥‡à¤‚ à¤à¤‚à¤ à¤¨", "à¤à¤‚à¤ à¤¨"], "canonical": "muscle cramps"},
#         "swollen joints":   {"hi": ["à¤œà¥‹à¤¡à¤¼à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¸à¥‚à¤œà¤¨", "à¤¸à¥‚à¤œà¤¨"], "canonical": "swollen joints"},

#         # Digestive
#         "indigestion":      {"hi": ["à¤…à¤ªà¤š", "à¤¬à¤¦à¤¹à¤œà¤¼à¤®à¥€", "à¤¹à¤¾à¤œà¤®à¤¾ à¤–à¤°à¤¾à¤¬"], "canonical": "indigestion"},
#         "bloating":         {"hi": ["à¤ªà¥‡à¤Ÿ à¤«à¥‚à¤²à¤¨à¤¾", "à¤—à¥ˆà¤¸", "à¤…à¤«à¤¾à¤°à¤¾"], "canonical": "bloating"},
#         "constipation":     {"hi": ["à¤•à¤¬à¥à¤œ", "à¤•à¤¬à¥à¤œà¤¼"], "canonical": "constipation"},
#         "acidity":          {"hi": ["à¤…à¤®à¥à¤²à¤¤à¤¾", "à¤à¤¸à¤¿à¤¡à¤¿à¤Ÿà¥€", "à¤–à¤Ÿà¥à¤Ÿà¥€ à¤¡à¤•à¤¾à¤°"], "canonical": "acidity"},
#         "nausea":           {"hi": ["à¤®à¤¤à¤²à¥€", "à¤œà¥€ à¤®à¤¿à¤šà¤²à¤¾à¤¨à¤¾", "à¤‰à¤¬à¤•à¤¾à¤ˆ"], "canonical": "nausea"},
#         "loss of appetite": {"hi": ["à¤­à¥‚à¤– à¤¨ à¤²à¤—à¤¨à¤¾", "à¤­à¥‚à¤– à¤•à¤® à¤¹à¥‹à¤¨à¤¾", "à¤…à¤°à¥à¤šà¤¿"], "canonical": "loss of appetite"},

#         # Respiratory
#         "cough":            {"hi": ["à¤–à¤¾à¤‚à¤¸à¥€", "à¤–à¤¾à¤à¤¸à¥€", "à¤•à¤«"], "canonical": "cough"},
#         "fever":            {"hi": ["à¤¬à¥à¤–à¤¾à¤°", "à¤œà¥à¤µà¤°", "à¤¤à¤¾à¤µ"], "canonical": "fever"},
#         "nasal congestion": {"hi": ["à¤¨à¤¾à¤• à¤¬à¤‚à¤¦", "à¤¨à¤¾à¤• à¤œà¤¾à¤®", "à¤ªà¥à¤°à¤¤à¤¿à¤¶à¥à¤¯à¤¾à¤¯"], "canonical": "nasal congestion"},
#         "shortness of breath": {"hi": ["à¤¸à¤¾à¤‚à¤¸ à¤«à¥‚à¤²à¤¨à¤¾", "à¤¶à¥à¤µà¤¾à¤¸ à¤•à¤·à¥à¤Ÿ", "à¤¦à¤®à¤¾"], "canonical": "shortness of breath"},

#         # General
#         "fatigue":          {"hi": ["à¤¥à¤•à¤¾à¤¨", "à¤¥à¤•à¤¾à¤µà¤Ÿ", "à¤•à¤®à¤œà¥‹à¤°à¥€"], "canonical": "fatigue"},
#         "insomnia":         {"hi": ["à¤…à¤¨à¤¿à¤¦à¥à¤°à¤¾", "à¤¨à¥€à¤‚à¤¦ à¤¨ à¤†à¤¨à¤¾", "à¤¨à¥€à¤‚à¤¦ à¤•à¥€ à¤•à¤®à¥€"], "canonical": "insomnia"},
#         "anxiety":          {"hi": ["à¤šà¤¿à¤‚à¤¤à¤¾", "à¤˜à¤¬à¤°à¤¾à¤¹à¤Ÿ", "à¤¬à¥‡à¤šà¥ˆà¤¨à¥€"], "canonical": "anxiety"},
#         "dizziness":        {"hi": ["à¤šà¤•à¥à¤•à¤° à¤†à¤¨à¤¾", "à¤šà¤•à¥à¤•à¤°", "à¤­à¥à¤°à¤®"], "canonical": "dizziness"},
#         "skin rash":        {"hi": ["à¤¤à¥à¤µà¤šà¤¾ à¤ªà¤° à¤šà¤•à¤¤à¥à¤¤à¥‡", "à¤¦à¤¾à¤¨à¥‡", "à¤–à¥à¤œà¤²à¥€"], "canonical": "skin rash"},
#         "excessive thirst": {"hi": ["à¤…à¤§à¤¿à¤• à¤ªà¥à¤¯à¤¾à¤¸", "à¤¬à¤¹à¥à¤¤ à¤ªà¥à¤¯à¤¾à¤¸", "à¤¤à¥ƒà¤·à¥à¤£à¤¾"], "canonical": "excessive thirst"},
#         "burning sensation":{"hi": ["à¤œà¤²à¤¨", "à¤¦à¤¾à¤¹", "à¤œà¤²à¤¨ à¤¹à¥‹à¤¨à¤¾"], "canonical": "burning sensation"},
#         "weight gain":      {"hi": ["à¤µà¤œà¤¨ à¤¬à¤¢à¤¼à¤¨à¤¾", "à¤®à¥‹à¤Ÿà¤¾à¤ªà¤¾"], "canonical": "weight gain"},
#         "hair loss":        {"hi": ["à¤¬à¤¾à¤² à¤à¤¡à¤¼à¤¨à¤¾", "à¤¬à¤¾à¤²à¥‹à¤‚ à¤•à¤¾ à¤—à¤¿à¤°à¤¨à¤¾", "à¤•à¥‡à¤¶ à¤ªà¤¤à¤¨"], "canonical": "hair loss"},
#         "dry skin":         {"hi": ["à¤°à¥‚à¤–à¥€ à¤¤à¥à¤µà¤šà¤¾", "à¤¸à¥‚à¤–à¥€ à¤¤à¥à¤µà¤šà¤¾"], "canonical": "dry skin"},
#         "cold hands and feet": {"hi": ["à¤¹à¤¾à¤¥ à¤ªà¥ˆà¤° à¤ à¤‚à¤¡à¥‡", "à¤ à¤‚à¤¡à¥‡ à¤¹à¤¾à¤¥ à¤ªà¥ˆà¤°"], "canonical": "cold hands and feet"},
#         "irregular heartbeat": {"hi": ["à¤…à¤¨à¤¿à¤¯à¤®à¤¿à¤¤ à¤§à¤¡à¤¼à¤•à¤¨", "à¤¦à¤¿à¤² à¤•à¥€ à¤§à¤¡à¤¼à¤•à¤¨"], "canonical": "irregular heartbeat"},
#     },

#     # â”€â”€ Diagnoses (Ayurvedic + modern mapping) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     "diagnoses": {
#         "amavata":     {"hi": ["à¤†à¤®à¤µà¤¾à¤¤"],         "en": ["rheumatoid arthritis"],   "canonical": "Amavata (Rheumatoid Arthritis)"},
#         "pandu":       {"hi": ["à¤ªà¤¾à¤‚à¤¡à¥", "à¤ªà¤¾à¤£à¥à¤¡à¥"],  "en": ["anemia"],                 "canonical": "Pandu (Anemia)"},
#         "prameha":     {"hi": ["à¤ªà¥à¤°à¤®à¥‡à¤¹"],          "en": ["diabetes", "madhumeha"],   "canonical": "Prameha (Diabetes)"},
#         "kushtha":     {"hi": ["à¤•à¥à¤·à¥à¤ "],           "en": ["skin disorder", "eczema", "psoriasis"], "canonical": "Kushtha (Skin Disorders)"},
#         "jwara":       {"hi": ["à¤œà¥à¤µà¤°"],            "en": ["fever", "pyrexia"],        "canonical": "Jwara (Fever)"},
#         "kasa":        {"hi": ["à¤•à¤¾à¤¸", "à¤•à¤¾à¤¸à¤¾"],     "en": ["cough", "bronchitis"],     "canonical": "Kasa (Cough)"},
#         "shwasa":      {"hi": ["à¤¶à¥à¤µà¤¾à¤¸", "à¤¶à¥à¤µà¤¾à¤¸à¤¾"],   "en": ["asthma", "dyspnea"],       "canonical": "Shwasa (Asthma)"},
#         "arsha":       {"hi": ["à¤…à¤°à¥à¤¶"],             "en": ["hemorrhoids", "piles"],    "canonical": "Arsha (Hemorrhoids)"},
#         "udara":       {"hi": ["à¤‰à¤¦à¤° à¤°à¥‹à¤—"],          "en": ["abdominal disorder"],      "canonical": "Udara Roga (Abdominal Disorders)"},
#         "hridroga":    {"hi": ["à¤¹à¥ƒà¤¦à¥à¤°à¥‹à¤—"],           "en": ["heart disease", "cardiac"],"canonical": "Hridroga (Heart Disease)"},
#         "vatarakta":   {"hi": ["à¤µà¤¾à¤¤à¤°à¤•à¥à¤¤"],          "en": ["gout"],                    "canonical": "Vatarakta (Gout)"},
#         "shula":       {"hi": ["à¤¶à¥‚à¤²"],              "en": ["abdominal pain", "colic"], "canonical": "Shula (Abdominal Pain)"},
#         "atisara":     {"hi": ["à¤…à¤¤à¤¿à¤¸à¤¾à¤°"],           "en": ["diarrhea", "diarrhoea"],   "canonical": "Atisara (Diarrhea)"},
#         "grahani":     {"hi": ["à¤—à¥à¤°à¤¹à¤£à¥€"],            "en": ["ibs", "irritable bowel"],  "canonical": "Grahani (IBS)"},
#         "kamala":      {"hi": ["à¤•à¤®à¤²à¤¾", "à¤•à¤¾à¤®à¤²à¤¾"],    "en": ["jaundice"],                "canonical": "Kamala (Jaundice)"},
#         "rajayakshma": {"hi": ["à¤°à¤¾à¤œà¤¯à¤•à¥à¤·à¥à¤®à¤¾"],        "en": ["tuberculosis", "tb"],      "canonical": "Rajayakshma (Tuberculosis)"},
#         "unmada":      {"hi": ["à¤‰à¤¨à¥à¤®à¤¾à¤¦"],            "en": ["psychosis", "mania"],      "canonical": "Unmada (Psychosis)"},
#         "apasmara":    {"hi": ["à¤…à¤ªà¤¸à¥à¤®à¤¾à¤°"],           "en": ["epilepsy", "seizure"],     "canonical": "Apasmara (Epilepsy)"},
#         "medoroga":    {"hi": ["à¤®à¥‡à¤¦à¥‹à¤°à¥‹à¤—", "à¤¸à¥à¤¥à¥Œà¤²à¥à¤¯"], "en": ["obesity"],                 "canonical": "Medoroga (Obesity)"},
#     },

#     # â”€â”€ Prakriti types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     "prakriti": {
#         "vata":        {"hi": ["à¤µà¤¾à¤¤", "à¤µà¤¾à¤¤ à¤ªà¥à¤°à¤•à¥ƒà¤¤à¤¿"],               "canonical": "Vata"},
#         "pitta":       {"hi": ["à¤ªà¤¿à¤¤à¥à¤¤", "à¤ªà¤¿à¤¤à¥à¤¤ à¤ªà¥à¤°à¤•à¥ƒà¤¤à¤¿"],             "canonical": "Pitta"},
#         "kapha":       {"hi": ["à¤•à¤«", "à¤•à¤« à¤ªà¥à¤°à¤•à¥ƒà¤¤à¤¿", "à¤¶à¥à¤²à¥‡à¤·à¥à¤®à¤¾"],      "canonical": "Kapha"},
#         "vata-pitta":  {"hi": ["à¤µà¤¾à¤¤-à¤ªà¤¿à¤¤à¥à¤¤", "à¤µà¤¾à¤¤ à¤ªà¤¿à¤¤à¥à¤¤"],            "canonical": "Vata-Pitta"},
#         "pitta-kapha": {"hi": ["à¤ªà¤¿à¤¤à¥à¤¤-à¤•à¤«", "à¤ªà¤¿à¤¤à¥à¤¤ à¤•à¤«"],              "canonical": "Pitta-Kapha"},
#         "vata-kapha":  {"hi": ["à¤µà¤¾à¤¤-à¤•à¤«", "à¤µà¤¾à¤¤ à¤•à¤«"],                 "canonical": "Vata-Kapha"},
#         "tridosha":    {"hi": ["à¤¤à¥à¤°à¤¿à¤¦à¥‹à¤·", "à¤¸à¤® à¤ªà¥à¤°à¤•à¥ƒà¤¤à¤¿", "à¤¤à¥à¤°à¤¿à¤¦à¥‹à¤·à¤œ"], "canonical": "Tridosha (Sama)"},
#     },
# }


# # ---------------------------------------------------------------------------
# # VoiceEHRCreator Class
# # ---------------------------------------------------------------------------
# class VoiceEHRCreator:
#     """
#     Create Electronic Health Records from voice input.

#     Uses speech_recognition + pyaudio for real microphone capture,
#     supports Hindi (hi-IN) and English (en-US), and extracts Ayurvedic
#     medical entities (symptoms, diagnosis, prakriti) using the bilingual
#     AYUSH dictionary.  Falls back to typed text when mic is unavailable.
#     """

#     def __init__(self, db_path: str | None = None):
#         self._db_path = db_path or DB_PATH
#         self._recognizer = None
#         self._translator = None
#         self._mic_available = False

#         # --- Lazy-load speech_recognition ----------------------------------
#         try:
#             import speech_recognition as sr  # type: ignore
#             self._sr = sr
#             self._recognizer = sr.Recognizer()
#             # Tweak recognizer for clinical environments (slightly noisy)
#             self._recognizer.energy_threshold = 300
#             self._recognizer.dynamic_energy_threshold = True
#             self._recognizer.pause_threshold = 1.5  # longer pause for medical dictation
#         except ImportError:
#             print(
#                 "[VoiceEHR] WARNING: 'speech_recognition' not installed.\n"
#                 "           Install with:  pip install SpeechRecognition\n"
#                 "           Voice input will fall back to text."
#             )
#             self._sr = None

#         # --- Check pyaudio / microphone ------------------------------------
#         if self._sr is not None:
#             try:
#                 mic = self._sr.Microphone()
#                 self._mic_available = True
#                 del mic
#             except (AttributeError, OSError) as exc:
#                 print(
#                     f"[VoiceEHR] WARNING: Microphone not available ({exc}).\n"
#                     f"           Install PyAudio:  pip install pyaudio\n"
#                     f"           Voice input will fall back to text."
#                 )

#         # --- Lazy-load googletrans -----------------------------------------
#         try:
#             from googletrans import Translator  # type: ignore
#             self._translator = Translator()
#         except ImportError:
#             print(
#                 "[VoiceEHR] WARNING: 'googletrans' not installed.\n"
#                 "           Install with:  pip install googletrans==4.0.0-rc1\n"
#                 "           Hindiâ†’English translation will be unavailable."
#             )

#     # â”€â”€â”€ Internal: generic listen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def _listen(self, language_code: str, prompt: str) -> str | None:
#         """
#         Record from microphone and transcribe via Google Speech API.
#         Returns transcribed text or None on failure.
#         """
#         if not self._mic_available or self._recognizer is None:
#             return None

#         sr = self._sr
#         print(f"\nðŸŽ™ï¸  {prompt}")
#         print("   (Speak clearly, pause when done â€” timeout 8s, phrase limit 30s)")

#         try:
#             with sr.Microphone() as source:
#                 # Calibrate for ambient noise
#                 print("   ðŸ”‡  Calibrating for ambient noise...")
#                 self._recognizer.adjust_for_ambient_noise(source, duration=1.5)

#                 print("   ðŸŸ¢  Listening...")
#                 audio = self._recognizer.listen(
#                     source,
#                     timeout=8,           # max wait for speech to start
#                     phrase_time_limit=30  # max recording length
#                 )

#             print("   â³  Transcribing...")
#             text = self._recognizer.recognize_google(audio, language=language_code)
#             print(f"   âœ…  Transcribed: \"{text}\"")
#             return text

#         except sr.WaitTimeoutError:
#             print("   âš ï¸  No speech detected within timeout. Please try again.")
#         except sr.UnknownValueError:
#             print("   âš ï¸  Could not understand audio. Please speak more clearly.")
#         except sr.RequestError as exc:
#             print(f"   âŒ  Google Speech API error: {exc}")
#         except OSError as exc:
#             print(f"   âŒ  Microphone hardware error: {exc}")
#         except Exception as exc:
#             print(f"   âŒ  Unexpected error during recording: {exc}")

#         return None

#     # â”€â”€â”€ Public: language-specific listeners â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def listen_hindi(self) -> str:
#         """
#         Record and transcribe Hindi speech.
#         Falls back to text input if microphone or recognition fails.
#         """
#         result = self._listen("hi-IN", "à¤•à¥ƒà¤ªà¤¯à¤¾ à¤¹à¤¿à¤‚à¤¦à¥€ à¤®à¥‡à¤‚ à¤¬à¥‹à¤²à¥‡à¤‚ (Please speak in Hindi)")

#         if result is None:
#             print("\nâŒ¨ï¸  Microphone unavailable â€” falling back to text input.")
#             result = input("   à¤¹à¤¿à¤‚à¤¦à¥€ à¤®à¥‡à¤‚ à¤²à¤¿à¤–à¥‡à¤‚ (Type in Hindi): ").strip()
#             if not result:
#                 result = "à¤¬à¥à¤–à¤¾à¤° à¤”à¤° à¤¸à¤¿à¤° à¤¦à¤°à¥à¤¦ à¤¹à¥ˆ, à¤ªà¤¿à¤¤à¥à¤¤ à¤ªà¥à¤°à¤•à¥ƒà¤¤à¤¿"  # default sample
#                 print(f"   (Using sample input: \"{result}\")")

#         return result

#     def listen_english(self) -> str:
#         """
#         Record and transcribe English speech.
#         Falls back to text input if microphone or recognition fails.
#         """
#         result = self._listen("en-US", "Please speak in English")

#         if result is None:
#             print("\nâŒ¨ï¸  Microphone unavailable â€” falling back to text input.")
#             result = input("   Type in English: ").strip()
#             if not result:
#                 result = "Patient has fever and joint pain, Vata-Pitta prakriti"
#                 print(f"   (Using sample input: \"{result}\")")

#         return result

#     # â”€â”€â”€ Entity extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def extract_entities(self, text: str, language: str = "en") -> dict:
#         """
#         Extract symptoms, diagnosis, and prakriti from clinical text
#         using the bilingual AYUSH medical dictionary.

#         Parameters:
#             text:     The transcribed (or typed) clinical note.
#             language: "hi" for Hindi, "en" for English.

#         Returns:
#             dict with keys: symptoms, diagnosis, prakriti, raw_matches
#         """
#         text_lower = text.lower()
#         found_symptoms: list[str] = []
#         found_diagnoses: list[str] = []
#         found_prakriti: str | None = None
#         raw_matches: list[dict] = []

#         # --- Symptom matching ---
#         for eng_key, entry in AYUSH_MEDICAL_DICTIONARY["symptoms"].items():
#             matched = False
#             match_source = ""

#             if language == "hi":
#                 for hi_term in entry["hi"]:
#                     if hi_term in text:
#                         matched = True
#                         match_source = hi_term
#                         break
#             # Always also check English (text may be translated or mixed)
#             if not matched and eng_key in text_lower:
#                 matched = True
#                 match_source = eng_key

#             if matched:
#                 canonical = entry["canonical"]
#                 if canonical not in found_symptoms:
#                     found_symptoms.append(canonical)
#                     raw_matches.append({
#                         "type": "symptom",
#                         "matched_text": match_source,
#                         "canonical": canonical,
#                     })

#         # --- Diagnosis matching ---
#         for key, entry in AYUSH_MEDICAL_DICTIONARY["diagnoses"].items():
#             matched = False
#             match_source = ""

#             if language == "hi":
#                 for hi_term in entry["hi"]:
#                     if hi_term in text:
#                         matched = True
#                         match_source = hi_term
#                         break

#             if not matched:
#                 # Check English aliases
#                 for en_term in entry.get("en", []):
#                     if en_term in text_lower:
#                         matched = True
#                         match_source = en_term
#                         break

#             # Also check the Ayurvedic key name itself
#             if not matched and key in text_lower:
#                 matched = True
#                 match_source = key

#             if matched:
#                 canonical = entry["canonical"]
#                 if canonical not in found_diagnoses:
#                     found_diagnoses.append(canonical)
#                     raw_matches.append({
#                         "type": "diagnosis",
#                         "matched_text": match_source,
#                         "canonical": canonical,
#                     })

#         # --- Prakriti matching ---
#         # Check compound types first (more specific), then single doshas
#         prakriti_order = [
#             "vata-pitta", "pitta-kapha", "vata-kapha", "tridosha",
#             "vata", "pitta", "kapha",
#         ]
#         for key in prakriti_order:
#             entry = AYUSH_MEDICAL_DICTIONARY["prakriti"][key]
#             matched = False

#             if language == "hi":
#                 for hi_term in entry["hi"]:
#                     if hi_term in text:
#                         matched = True
#                         break

#             if not matched:
#                 # English check â€” use word boundary to avoid partial matches
#                 pattern = r'\b' + re.escape(entry["canonical"].split(" ")[0].lower()) + r'\b'
#                 if re.search(pattern, text_lower):
#                     # For single doshas, make sure it's not part of a compound
#                     if key in ("vata", "pitta", "kapha"):
#                         # Check no compound already matched
#                         if found_prakriti is None:
#                             matched = True
#                     else:
#                         matched = True

#             if matched and found_prakriti is None:
#                 found_prakriti = entry["canonical"]
#                 raw_matches.append({
#                     "type": "prakriti",
#                     "matched_text": key,
#                     "canonical": found_prakriti,
#                 })

#         return {
#             "symptoms":  found_symptoms,
#             "diagnosis": found_diagnoses,
#             "prakriti":  found_prakriti,
#             "raw_matches": raw_matches,
#         }

#     # â”€â”€â”€ Translate Hindi â†’ English â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def translate_to_english(self, hindi_text: str) -> str:
#         """
#         Translate Hindi text to English using googletrans.
#         Returns original text if translator is unavailable.
#         """
#         if self._translator is None:
#             print("   âš ï¸  Translator unavailable â€” storing original Hindi text.")
#             return hindi_text

#         try:
#             result = self._translator.translate(hindi_text, src="hi", dest="en")
#             translated = result.text
#             print(f"   ðŸ”„  Translated: \"{translated}\"")
#             return translated
#         except Exception as exc:
#             print(f"   âš ï¸  Translation failed ({exc}) â€” using original text.")
#             return hindi_text

#     # â”€â”€â”€ Create and save EHR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def create_ehr(
#         self,
#         patient_id: str,
#         voice_text: str,
#         language: str = "en",
#     ) -> dict:
#         """
#         Process voice/text input, extract entities, translate if needed,
#         and save a new EHR record to the database.

#         Parameters:
#             patient_id: The patient identifier (e.g., "PAT-0001").
#             voice_text: Raw transcribed or typed clinical text.
#             language:   "hi" for Hindi, "en" for English.

#         Returns:
#             dict with the complete EHR record that was saved.
#         """
#         print(f"\n{'â”€'*60}")
#         print(f"ðŸ“‹  Creating EHR for patient: {patient_id}")
#         print(f"   Language: {language.upper()}")
#         print(f"   Raw text: \"{voice_text}\"")

#         # Translate if Hindi
#         raw_text = voice_text
#         if language == "hi":
#             translated_text = self.translate_to_english(voice_text)
#         else:
#             translated_text = voice_text

#         # Extract entities from both raw and translated text
#         entities_raw = self.extract_entities(voice_text, language)
#         entities_translated = self.extract_entities(translated_text, "en")

#         # Merge: prefer raw-language matches, supplement with translated
#         symptoms = list(dict.fromkeys(
#             entities_raw["symptoms"] + entities_translated["symptoms"]
#         ))
#         diagnoses = list(dict.fromkeys(
#             entities_raw["diagnosis"] + entities_translated["diagnosis"]
#         ))
#         prakriti = entities_raw["prakriti"] or entities_translated["prakriti"]

#         symptoms_str = ", ".join(symptoms) if symptoms else "unspecified"
#         diagnosis_str = ", ".join(diagnoses) if diagnoses else "pending evaluation"
#         prakriti_str = prakriti or "not assessed"

#         # Build record
#         record_id = str(uuid.uuid4())
#         visit_date = datetime.now().strftime("%Y-%m-%d")
#         lang_label = "Hindi" if language == "hi" else "English"

#         ehr_record = {
#             "id": record_id,
#             "patient_id": patient_id,
#             "visit_date": visit_date,
#             "symptoms": symptoms_str,
#             "diagnosis": diagnosis_str,
#             "prakriti": prakriti_str,
#             "comorbidities": "None",
#             "raw_text": raw_text,
#             "translated_text": translated_text,
#             "language": lang_label,
#         }

#         # Save to database
#         conn = get_db_connection(self._db_path)
#         conn.execute(
#             "INSERT INTO ehr_records "
#             "(id, patient_id, visit_date, symptoms, diagnosis, prakriti, "
#             " comorbidities, raw_text, translated_text, language) "
#             "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#             (
#                 ehr_record["id"],
#                 ehr_record["patient_id"],
#                 ehr_record["visit_date"],
#                 ehr_record["symptoms"],
#                 ehr_record["diagnosis"],
#                 ehr_record["prakriti"],
#                 ehr_record["comorbidities"],
#                 ehr_record["raw_text"],
#                 ehr_record["translated_text"],
#                 ehr_record["language"],
#             ),
#         )
#         conn.commit()
#         conn.close()

#         # Print summary
#         print(f"\n   âœ…  EHR saved successfully!")
#         print(f"   {'â”€'*50}")
#         print(f"   Record ID  : {record_id[:16]}...")
#         print(f"   Patient    : {patient_id}")
#         print(f"   Date       : {visit_date}")
#         print(f"   Symptoms   : {symptoms_str}")
#         print(f"   Diagnosis  : {diagnosis_str}")
#         print(f"   Prakriti   : {prakriti_str}")
#         print(f"   Language   : {lang_label}")
#         print(f"   {'â”€'*50}")

#         return ehr_record


# # ---------------------------------------------------------------------------
# # Voice EHR Demo
# # ---------------------------------------------------------------------------
# def _run_voice_demo() -> None:
#     """Interactive demo of the VoiceEHRCreator."""
#     print("\n" + "=" * 60)
#     print("  AYUSH Voice EHR Demo")
#     print("=" * 60)

#     creator = VoiceEHRCreator()

#     while True:
#         print("\nSelect language for voice input:")
#         print("  1. English (en-US)")
#         print("  2. Hindi   (hi-IN)")
#         print("  3. Exit demo")

#         choice = input("\nEnter choice (1/2/3): ").strip()

#         if choice == "3":
#             print("\nExiting Voice EHR demo.")
#             break

#         patient_id = input("Enter Patient ID (e.g., PAT-0101): ").strip()
#         if not patient_id:
#             patient_id = f"PAT-{random.randint(100, 999):04d}"
#             print(f"   (Auto-assigned: {patient_id})")

#         if choice == "1":
#             text = creator.listen_english()
#             record = creator.create_ehr(patient_id, text, language="en")
#         elif choice == "2":
#             text = creator.listen_hindi()
#             record = creator.create_ehr(patient_id, text, language="hi")
#         else:
#             print("Invalid choice. Please enter 1, 2, or 3.")
#             continue

#         print(f"\n   Full record (JSON):")
#         print(f"   {json.dumps(record, indent=2, ensure_ascii=False)}")


# # ===========================================================================
# #  DISEASE OUTBREAK DETECTOR â€” Isolation Forest + Trend Forecasting
# # ===========================================================================

# class DiseaseOutbreakDetector:
#     """
#     Detect disease outbreaks using Isolation Forest anomaly detection
#     and forecast trends with moving averages.

#     Features:
#       â€¢ Generates 120-day synthetic surveillance data for 5 districts Ã— 5 diseases
#       â€¢ Rolling 3-day and 7-day averages for noise smoothing
#       â€¢ Isolation Forest (scikit-learn) for anomaly scoring
#       â€¢ Severity levels: HIGH / MEDIUM / LOW
#       â€¢ 7-day and 14-day moving average trend forecasting
#       â€¢ Persists alerts to the outbreak_alerts table
#     """

#     DISTRICTS = ["Varanasi", "Jaipur", "Thiruvananthapuram", "Haridwar", "Mysuru"]
#     DISEASES = ["Dengue", "Chikungunya", "Malaria", "Typhoid", "Leptospirosis"]

#     # Outbreak events to inject: (district, disease, peak_day_offset, intensity, spread_radius)
#     OUTBREAK_EVENTS = [
#         {"district": "Varanasi",            "disease": "Dengue",        "peak_day": 45,  "intensity": 5.0, "spread": 12},
#         {"district": "Thiruvananthapuram",  "disease": "Leptospirosis", "peak_day": 90,  "intensity": 4.2, "spread": 10},
#     ]

#     def __init__(self, db_path: str | None = None):
#         self._db_path = db_path or DB_PATH
#         self._sklearn_available = False

#         # Lazy-load scikit-learn
#         try:
#             from sklearn.ensemble import IsolationForest  # type: ignore
#             self._IsolationForest = IsolationForest
#             self._sklearn_available = True
#         except ImportError:
#             print(
#                 "[OutbreakDetector] WARNING: scikit-learn not installed.\n"
#                 "                   Install with:  pip install scikit-learn\n"
#                 "                   Anomaly detection will use a statistical fallback."
#             )
#             self._IsolationForest = None

#     # â”€â”€â”€ Synthetic surveillance data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def generate_synthetic_data(self, days: int = 120, seed: int = 42) -> list[dict]:
#         """
#         Generate synthetic daily disease case counts for all districts.

#         Returns a list of dicts with keys:
#           district, disease, date, cases, day_index
#         """
#         random.seed(seed)
#         now = datetime.now()
#         start_date = now - timedelta(days=days)
#         records: list[dict] = []

#         for day_offset in range(days):
#             current_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

#             for district in self.DISTRICTS:
#                 for disease in self.DISEASES:
#                     # Baseline: Poisson-like with seasonal variation
#                     seasonal_factor = 1.0 + 0.3 * math.sin(2 * math.pi * day_offset / 60)
#                     base_cases = max(1, int(random.gauss(8, 3) * seasonal_factor))

#                     # Inject outbreak spikes
#                     for event in self.OUTBREAK_EVENTS:
#                         if district == event["district"] and disease == event["disease"]:
#                             distance = abs(day_offset - event["peak_day"])
#                             if distance <= event["spread"]:
#                                 spike = event["intensity"] * max(0, 1 - (distance / event["spread"]))
#                                 base_cases += int(base_cases * spike)

#                     records.append({
#                         "district": district,
#                         "disease": disease,
#                         "date": current_date,
#                         "cases": base_cases,
#                         "day_index": day_offset,
#                     })

#         print(f"[OutbreakDetector] Generated {len(records)} surveillance records ")
#         print(f"                   ({days} days x {len(self.DISTRICTS)} districts x {len(self.DISEASES)} diseases)")
#         return records

#     # â”€â”€â”€ Rolling averages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     @staticmethod
#     def _compute_rolling_averages(case_series: list[int]) -> dict:
#         """
#         Compute 3-day and 7-day rolling averages for a case time-series.
#         Returns dict with 'avg_3d' and 'avg_7d' lists (same length as input,
#         with None for positions where window is insufficient).
#         """
#         n = len(case_series)
#         avg_3d: list[float | None] = [None] * n
#         avg_7d: list[float | None] = [None] * n

#         for i in range(n):
#             if i >= 2:
#                 avg_3d[i] = round(sum(case_series[i-2:i+1]) / 3, 2)
#             if i >= 6:
#                 avg_7d[i] = round(sum(case_series[i-6:i+1]) / 7, 2)

#         return {"avg_3d": avg_3d, "avg_7d": avg_7d}

#     # â”€â”€â”€ Severity classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     @staticmethod
#     def _classify_severity(anomaly_score: float, cases: int, avg_7d: float | None) -> str:
#         """
#         Classify outbreak severity based on anomaly score and case deviation.

#         Returns: "HIGH", "MEDIUM", or "LOW"
#         """
#         if avg_7d is not None and avg_7d > 0:
#             deviation_ratio = cases / avg_7d
#         else:
#             deviation_ratio = 1.0

#         if anomaly_score > 0.7 or deviation_ratio > 3.0:
#             return "HIGH"
#         elif anomaly_score > 0.4 or deviation_ratio > 2.0:
#             return "MEDIUM"
#         else:
#             return "LOW"

#     # â”€â”€â”€ Core: Anomaly detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def detect_anomalies(
#         self,
#         data: list[dict] | None = None,
#         contamination: float = 0.08,
#     ) -> list[dict]:
#         """
#         Run anomaly detection on surveillance data.

#         Parameters:
#             data:          Output from generate_synthetic_data(). If None,
#                            generates fresh data automatically.
#             contamination: Expected proportion of anomalies (0.0â€“0.5).

#         Returns:
#             List of alert dicts with keys:
#               district, disease, date, cases, anomaly_score, severity,
#               avg_3d, avg_7d, is_anomaly
#         """
#         if data is None:
#             data = self.generate_synthetic_data()

#         # Group data by (district, disease)
#         groups: dict[tuple[str, str], list[dict]] = {}
#         for rec in data:
#             key = (rec["district"], rec["disease"])
#             groups.setdefault(key, []).append(rec)

#         all_alerts: list[dict] = []

#         for (district, disease), series in groups.items():
#             # Sort by date
#             series.sort(key=lambda r: r["date"])
#             case_values = [r["cases"] for r in series]

#             # Compute rolling averages
#             rolling = self._compute_rolling_averages(case_values)

#             # Build feature matrix: [cases, avg_3d, avg_7d, day_index]
#             feature_rows = []
#             valid_indices = []
#             for i, rec in enumerate(series):
#                 a3 = rolling["avg_3d"][i]
#                 a7 = rolling["avg_7d"][i]
#                 if a3 is not None and a7 is not None:
#                     feature_rows.append([rec["cases"], a3, a7, rec["day_index"]])
#                     valid_indices.append(i)

#             if len(feature_rows) < 10:
#                 continue  # not enough data for meaningful detection

#             # --- Anomaly detection ---
#             if self._sklearn_available and self._IsolationForest is not None:
#                 model = self._IsolationForest(
#                     contamination=contamination,
#                     random_state=42,
#                     n_estimators=100,
#                 )
#                 predictions = model.fit_predict(feature_rows)
#                 raw_scores = model.decision_function(feature_rows)

#                 # Normalize scores to [0, 1] where 1 = most anomalous
#                 min_s, max_s = min(raw_scores), max(raw_scores)
#                 score_range = max_s - min_s if max_s != min_s else 1.0
#                 norm_scores = [(max_s - s) / score_range for s in raw_scores]
#             else:
#                 # Statistical fallback: z-score based
#                 mean_cases = sum(r[0] for r in feature_rows) / len(feature_rows)
#                 std_cases = max(
#                     1.0,
#                     (sum((r[0] - mean_cases) ** 2 for r in feature_rows) / len(feature_rows)) ** 0.5
#                 )
#                 predictions = []
#                 norm_scores = []
#                 for row in feature_rows:
#                     z = (row[0] - mean_cases) / std_cases
#                     score = min(1.0, max(0.0, (z - 1.0) / 3.0))  # map z>1 to [0,1]
#                     norm_scores.append(score)
#                     predictions.append(-1 if z > 2.0 else 1)

#             # Build alerts
#             for idx_pos, orig_idx in enumerate(valid_indices):
#                 rec = series[orig_idx]
#                 anomaly_score = round(norm_scores[idx_pos], 3)
#                 is_anomaly = predictions[idx_pos] == -1
#                 avg_7d_val = rolling["avg_7d"][orig_idx]

#                 severity = self._classify_severity(anomaly_score, rec["cases"], avg_7d_val)

#                 alert = {
#                     "district": district,
#                     "disease": disease,
#                     "date": rec["date"],
#                     "cases": rec["cases"],
#                     "anomaly_score": anomaly_score,
#                     "severity": severity,
#                     "avg_3d": rolling["avg_3d"][orig_idx],
#                     "avg_7d": avg_7d_val,
#                     "is_anomaly": is_anomaly,
#                 }
#                 all_alerts.append(alert)

#         # Persist anomaly alerts to DB
#         anomalies = [a for a in all_alerts if a["is_anomaly"]]
#         self._save_alerts(anomalies)

#         total = len(all_alerts)
#         n_anom = len(anomalies)
#         print(f"[OutbreakDetector] Analysed {total} data points, found {n_anom} anomalies.")
#         return all_alerts

#     # â”€â”€â”€ Persist alerts to DB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def _save_alerts(self, alerts: list[dict]) -> None:
#         """Insert anomaly alerts into the outbreak_alerts table."""
#         if not alerts:
#             return

#         conn = get_db_connection(self._db_path)
#         cursor = conn.cursor()

#         for alert in alerts:
#             # Avoid duplicates: check if (district, disease, date) already exists
#             existing = cursor.execute(
#                 "SELECT COUNT(*) FROM outbreak_alerts "
#                 "WHERE district = ? AND disease = ? AND date_detected = ?",
#                 (alert["district"], alert["disease"], alert["date"]),
#             ).fetchone()[0]

#             if existing == 0:
#                 cursor.execute(
#                     "INSERT INTO outbreak_alerts "
#                     "(id, district, disease, anomaly_score, date_detected, cases_reported) "
#                     "VALUES (?, ?, ?, ?, ?, ?)",
#                     (
#                         str(uuid.uuid4()),
#                         alert["district"],
#                         alert["disease"],
#                         alert["anomaly_score"],
#                         alert["date"],
#                         alert["cases"],
#                     ),
#                 )

#         conn.commit()
#         conn.close()

#     # â”€â”€â”€ Recent alerts query â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def get_recent_alerts(self, days: int = 7) -> list[dict]:
#         """
#         Retrieve outbreak alerts from the last *days* days.

#         Returns list of dicts sorted by anomaly_score descending.
#         """
#         cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
#         conn = get_db_connection(self._db_path)
#         rows = conn.execute(
#             "SELECT district, disease, anomaly_score, date_detected, cases_reported "
#             "FROM outbreak_alerts "
#             "WHERE date_detected >= ? "
#             "ORDER BY anomaly_score DESC",
#             (cutoff,),
#         ).fetchall()
#         conn.close()

#         return [
#             {
#                 "district": r["district"],
#                 "disease": r["disease"],
#                 "anomaly_score": r["anomaly_score"],
#                 "date": r["date_detected"],
#                 "cases": r["cases_reported"],
#             }
#             for r in rows
#         ]

#     # â”€â”€â”€ Trend forecasting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def forecast_trend(
#         self,
#         district: str,
#         disease: str,
#         data: list[dict] | None = None,
#     ) -> dict:
#         """
#         Predict the trend direction for a specific district+disease pair
#         using 7-day and 14-day moving averages.

#         Parameters:
#             district: District name (e.g., "Varanasi")
#             disease:  Disease name (e.g., "Dengue")
#             data:     Full surveillance dataset. If None, generates fresh.

#         Returns:
#             dict with keys:
#               district, disease, trend, ma_7d, ma_14d, latest_cases,
#               percent_change_7d, assessment
#         """
#         if data is None:
#             data = self.generate_synthetic_data()

#         # Filter to the specific (district, disease) pair
#         series = [
#             r for r in data
#             if r["district"] == district and r["disease"] == disease
#         ]
#         series.sort(key=lambda r: r["date"])

#         if len(series) < 14:
#             return {
#                 "district": district,
#                 "disease": disease,
#                 "trend": "INSUFFICIENT_DATA",
#                 "ma_7d": None,
#                 "ma_14d": None,
#                 "latest_cases": None,
#                 "percent_change_7d": None,
#                 "assessment": "Not enough data for trend analysis.",
#             }

#         case_values = [r["cases"] for r in series]

#         # Compute moving averages over the most recent window
#         ma_7d = round(sum(case_values[-7:]) / 7, 2)
#         ma_14d = round(sum(case_values[-14:]) / 14, 2)

#         # Previous 7-day average (days -14 to -8) for comparison
#         ma_7d_prev = round(sum(case_values[-14:-7]) / 7, 2) if len(case_values) >= 14 else ma_7d

#         # Percent change
#         if ma_7d_prev > 0:
#             pct_change = round(((ma_7d - ma_7d_prev) / ma_7d_prev) * 100, 1)
#         else:
#             pct_change = 0.0

#         latest_cases = case_values[-1]

#         # Determine trend direction
#         if pct_change > 20:
#             trend = "RISING_FAST"
#             assessment = (f"Rapid increase detected. 7-day avg ({ma_7d}) is {pct_change}% "
#                           f"above the prior week ({ma_7d_prev}). Immediate attention recommended.")
#         elif pct_change > 5:
#             trend = "RISING"
#             assessment = (f"Gradual increase. 7-day avg ({ma_7d}) is {pct_change}% "
#                           f"above the prior week ({ma_7d_prev}). Monitor closely.")
#         elif pct_change < -20:
#             trend = "DECLINING_FAST"
#             assessment = (f"Rapid decline. 7-day avg ({ma_7d}) is {abs(pct_change)}% "
#                           f"below the prior week ({ma_7d_prev}). Situation improving.")
#         elif pct_change < -5:
#             trend = "DECLINING"
#             assessment = (f"Gradual decline. 7-day avg ({ma_7d}) is {abs(pct_change)}% "
#                           f"below the prior week ({ma_7d_prev}). Positive trend.")
#         else:
#             trend = "STABLE"
#             assessment = (f"Stable trend. 7-day avg ({ma_7d}) is within 5% of "
#                           f"the prior week ({ma_7d_prev}). No significant change.")

#         return {
#             "district": district,
#             "disease": disease,
#             "trend": trend,
#             "ma_7d": ma_7d,
#             "ma_14d": ma_14d,
#             "latest_cases": latest_cases,
#             "percent_change_7d": pct_change,
#             "assessment": assessment,
#         }

#     # â”€â”€â”€ Summary report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#     def print_detection_report(self, alerts: list[dict]) -> None:
#         """Print a formatted outbreak detection report."""
#         anomalies = [a for a in alerts if a["is_anomaly"]]
#         high = [a for a in anomalies if a["severity"] == "HIGH"]
#         medium = [a for a in anomalies if a["severity"] == "MEDIUM"]
#         low = [a for a in anomalies if a["severity"] == "LOW"]

#         print(f"\n{'='*70}")
#         print(f"  DISEASE OUTBREAK DETECTION REPORT")
#         print(f"{'='*70}")
#         print(f"  Total data points analysed : {len(alerts):>6}")
#         print(f"  Anomalies detected         : {len(anomalies):>6}")
#         print(f"    - HIGH severity           : {len(high):>6}")
#         print(f"    - MEDIUM severity         : {len(medium):>6}")
#         print(f"    - LOW severity            : {len(low):>6}")

#         if high:
#             print(f"\n  {'â”€'*66}")
#             print(f"  TOP HIGH-SEVERITY ALERTS:")
#             print(f"  {'â”€'*66}")
#             print(f"  {'District':<25s} {'Disease':<16s} {'Score':>6s} {'Cases':>6s} {'7d Avg':>7s} {'Date'}")
#             print(f"  {'â”€'*25} {'â”€'*15} {'â”€'*6} {'â”€'*6} {'â”€'*7} {'â”€'*10}")
#             for a in sorted(high, key=lambda x: x["anomaly_score"], reverse=True)[:15]:
#                 avg7 = f"{a['avg_7d']:.1f}" if a['avg_7d'] else "  N/A"
#                 print(f"  {a['district']:<25s} {a['disease']:<16s} {a['anomaly_score']:>6.3f} "
#                       f"{a['cases']:>6d} {avg7:>7s} {a['date']}")

#         # Trend forecast for outbreak districts
#         print(f"\n  {'â”€'*66}")
#         print(f"  TREND FORECASTS FOR OUTBREAK DISTRICTS:")
#         print(f"  {'â”€'*66}")

#         data = self.generate_synthetic_data()
#         for event in self.OUTBREAK_EVENTS:
#             forecast = self.forecast_trend(event["district"], event["disease"], data)
#             arrow = {
#                 "RISING_FAST": "  ^",
#                 "RISING": "  /",
#                 "STABLE": " --",
#                 "DECLINING": "  \\",
#                 "DECLINING_FAST": "  v",
#             }.get(forecast["trend"], "  ?")
#             print(f"\n  {arrow} {forecast['district']} â€” {forecast['disease']}")
#             print(f"     Trend     : {forecast['trend']}")
#             print(f"     7-day MA  : {forecast['ma_7d']}")
#             print(f"     14-day MA : {forecast['ma_14d']}")
#             print(f"     Change    : {forecast['percent_change_7d']}%")
#             print(f"     Latest    : {forecast['latest_cases']} cases")
#             print(f"     {forecast['assessment']}")

#         print(f"\n{'='*70}")


# # ===========================================================================
# #  AYUSH RECOMMENDER â€” Hybrid Patient Recommendation System
# # ===========================================================================

# class AyushRecommender:
#     """
#     Hybrid Ayurvedic treatment recommender.
#     Uses cold-start knowledge base for patients with < 3 visits,
#     and cluster-based K-Means patient similarity for patients with >= 3 visits.
#     """

#     COLD_START_KB = {
#         "Vata": {
#             "herbs": "Ashwagandha, Guggulu, Triphala",
#             "diet": "Warm cooked meals, ghee with meals, avoid cold/raw foods",
#             "yoga": "Shavasana, Pawanmuktasana, Vajrasana post meals",
#             "lifestyle": "Abhyanga (self-massage) daily, sleep by 10 PM, wake before sunrise"
#         },
#         "Pitta": {
#             "herbs": "Guduchi (Giloy), Shatavari, Brahmi",
#             "diet": "Avoid excess spicy/fermented foods, cooling foods, bitter greens",
#             "yoga": "Bhujangasana, Meditation, Sheetali Pranayama",
#             "lifestyle": "Avoid excess heat exposure, warm foot soak before bed, walk in nature"
#         },
#         "Kapha": {
#             "herbs": "Punarnava, Pippali, Gokshura",
#             "diet": "Light meals, avoid dairy, prefer warm water, barley and millet",
#             "yoga": "Surya Namaskar, Kapalbhati, Trikonasana",
#             "lifestyle": "Wake before sunrise, avoid daytime napping, active daily exercise"
#         },
#         "Vata-Pitta": {
#             "herbs": "Ashwagandha, Shatavari, Brahmi",
#             "diet": "Warm and cooling balance, avoid extreme spices, include ghee",
#             "yoga": "Anulom Vilom Pranayama, Shavasana, Vajrasana",
#             "lifestyle": "Regular daily routine, Nasya, early sleep, avoid stress"
#         },
#         "Pitta-Kapha": {
#             "herbs": "Guduchi (Giloy), Punarnava, Triphala",
#             "diet": "Light and cooling foods, reduce salt, include bitter herbs",
#             "yoga": "Meditation, Surya Namaskar, Pranayama",
#             "lifestyle": "Stay active, dry skin brushing, walk post meals"
#         },
#         "Vata-Kapha": {
#             "herbs": "Ashwagandha, Pippali, Gokshura",
#             "diet": "Warm and light cooked meals, avoid cold dairy, use warm spices like ginger",
#             "yoga": "Kapalbhati, Surya Namaskar, Pawanmuktasana",
#             "lifestyle": "Stay warm, wake early, active exercise, dry massage"
#         },
#         "Tridosha (Sama)": {
#             "herbs": "Triphala, Guduchi (Giloy), Ashwagandha, Shatavari",
#             "diet": "Balanced seasonal diet, light meals, warm water",
#             "yoga": "Nadi Shodhana Pranayama, Surya Namaskar, Shavasana",
#             "lifestyle": "Balanced daily routine (Dinacharya), regular sleep, moderate exercise"
#         }
#     }

#     DIAGNOSIS_REMEDIES = {
#         "Amavata (Rheumatoid Arthritis)": {
#             "herbs": "Guggulu, Ashwagandha",
#             "diet": "Avoid yogurt and fermented foods, drink warm ginger tea",
#             "yoga": "Gentle joint movements, Vajrasana",
#             "lifestyle": "Apply dry heat fermentation, avoid cold breeze, warm water bath"
#         },
#         "Pandu (Anemia)": {
#             "herbs": "Punarnava, Amalaki (Amla)",
#             "diet": "Pomegranate, beetroot juice, green leafy vegetables, raisins",
#             "yoga": "Nadi Shodhana Pranayama, Sarvangasana",
#             "lifestyle": "Moderate morning sunlight, avoid physical exhaustion, adequate rest"
#         },
#         "Prameha (Diabetes)": {
#             "herbs": "Chandraprabha Vati, Haridra (Turmeric)",
#             "diet": "Barley, bitter gourd, limit heavy grains and dairy",
#             "yoga": "Paschimottanasana, Ardha Matsyendrasana, Kapalbhati",
#             "lifestyle": "Regular brisk walking, avoid day sleeping, keep feet clean and dry"
#         },
#         "Kushtha (Skin Disorders)": {
#             "herbs": "Neem, Haridra (Turmeric)",
#             "diet": "Bitter vegetables, avoid fish and milk combination",
#             "yoga": "Sheetali Pranayama, Bhujangasana",
#             "lifestyle": "Apply coconut oil, wash skin with neem water, avoid harsh soap"
#         },
#         "Jwara (Fever)": {
#             "herbs": "Guduchi (Giloy), Tulsi, Pippali",
#             "diet": "Light gruel (Peya), hot water, avoid heavy foods and dairy",
#             "yoga": "Rest (Shavasana), no strenuous postures",
#             "lifestyle": "Complete bed rest, warm sponge bath, avoid direct fan/AC wind"
#         }
#     }

#     def __init__(self, db_path: str | None = None):
#         self._db_path = db_path or DB_PATH

#     def get_cold_start(self, prakriti: str, diagnosis: str) -> dict:
#         """Knowledge base lookup for Ayurvedic recommendation."""
#         # Find matches for Prakriti
#         prak_rec = self.COLD_START_KB.get(prakriti, self.COLD_START_KB["Tridosha (Sama)"])
        
#         # Find matches for Diagnosis
#         diag_rec = None
#         for d_key, remedies in self.DIAGNOSIS_REMEDIES.items():
#             if d_key.lower() in diagnosis.lower() or diagnosis.lower() in d_key.lower():
#                 diag_rec = remedies
#                 break
        
#         if not diag_rec:
#             # Fallback default diagnosis remedies
#             diag_rec = {
#                 "herbs": "Triphala, Guduchi (Giloy)",
#                 "diet": "Light freshly cooked warm food",
#                 "yoga": "Nadi Shodhana Pranayama",
#                 "lifestyle": "Adequate rest, timely meals"
#             }

#         # Combine
#         herbs = list(set([h.strip() for h in (prak_rec["herbs"] + ", " + diag_rec["herbs"]).split(",") if h.strip()]))
#         diet = prak_rec["diet"] + "; " + diag_rec["diet"]
#         yoga = prak_rec["yoga"] + "; " + diag_rec["yoga"]
#         lifestyle = prak_rec["lifestyle"] + "; " + diag_rec["lifestyle"]

#         return {
#             "herbs": ", ".join(herbs),
#             "diet": diet,
#             "yoga": yoga,
#             "lifestyle": lifestyle,
#             "confidence_score": 0.85
#         }

#     def _kmeans_clustering(self, features: list[list[float]], n_clusters: int = 5, max_iter: int = 20) -> list[int]:
#         """Simple pure-Python K-Means clustering algorithm to avoid external dependencies."""
#         num_samples = len(features)
#         if num_samples <= n_clusters:
#             return list(range(num_samples)) + [0] * (num_samples - n_clusters)
            
#         num_features = len(features[0])
        
#         # Initialize centroids randomly
#         random.seed(42)
#         centroid_indices = random.sample(range(num_samples), n_clusters)
#         centroids = [list(features[idx]) for idx in centroid_indices]
        
#         assignments = [0] * num_samples
        
#         for _ in range(max_iter):
#             changed = False
#             for i in range(num_samples):
#                 feat = features[i]
#                 min_dist = float('inf')
#                 best_cluster = 0
#                 for c_idx in range(n_clusters):
#                     dist = sum((feat[j] - centroids[c_idx][j])**2 for j in range(num_features))
#                     if dist < min_dist:
#                         min_dist = dist
#                         best_cluster = c_idx
#                 if assignments[i] != best_cluster:
#                     assignments[i] = best_cluster
#                     changed = True
                    
#             if not changed:
#                 break
                
#             # Update centroids
#             cluster_sums = [[0.0] * num_features for _ in range(n_clusters)]
#             cluster_counts = [0] * n_clusters
#             for i in range(num_samples):
#                 c_idx = assignments[i]
#                 cluster_counts[c_idx] += 1
#                 for j in range(num_features):
#                     cluster_sums[c_idx][j] += features[i][j]
                    
#             for c_idx in range(n_clusters):
#                 if cluster_counts[c_idx] > 0:
#                     centroids[c_idx] = [cluster_sums[c_idx][j] / cluster_counts[c_idx] for j in range(num_features)]
                    
#         return assignments

#     def get_cluster_recommendation(self, patient_id: str) -> dict | None:
#         """Similar patient analysis using patient demographics (Age, BMI, Comorbidities)."""
#         conn = get_db_connection(self._db_path)
#         cursor = conn.cursor()

#         # Get target patient metadata
#         target = cursor.execute(
#             "SELECT age, bmi, comorbidities_count FROM patient_history WHERE patient_id = ?",
#             (patient_id,)
#         ).fetchone()

#         if not target:
#             conn.close()
#             return None

#         # Get all patients metadata
#         all_patients = cursor.execute(
#             "SELECT patient_id, age, bmi, comorbidities_count FROM patient_history"
#         ).fetchall()

#         if len(all_patients) < 10:
#             conn.close()
#             return None

#         patient_list = [p["patient_id"] for p in all_patients]
#         features = [[float(p["age"]), float(p["bmi"]), float(p["comorbidities_count"])] for p in all_patients]

#         # Standardize features (min-max scaling)
#         scaled_features = []
#         for j in range(3):
#             col = [f[j] for f in features]
#             min_v, max_v = min(col), max(col)
#             rng = max_v - min_v if max_v != min_v else 1.0
#             for i in range(len(features)):
#                 if len(scaled_features) <= i:
#                     scaled_features.append([])
#                 scaled_features[i].append((features[i][j] - min_v) / rng)

#         # Cluster patients
#         assignments = self._kmeans_clustering(scaled_features, n_clusters=min(5, len(all_patients)))

#         # Find target cluster
#         target_idx = patient_list.index(patient_id)
#         target_cluster = assignments[target_idx]

#         # Get other patients in same cluster
#         peer_ids = [patient_list[i] for i, c in enumerate(assignments) if c == target_cluster and patient_list[i] != patient_id]

#         if not peer_ids:
#             conn.close()
#             return None

#         # Find treatments of peers that were approved or had high feedback_score
#         placeholders = ",".join("?" for _ in peer_ids)
#         peer_treatments = cursor.execute(
#             f"SELECT herbs, diet, yoga, lifestyle, feedback_score, approved FROM treatments "
#             f"WHERE patient_id IN ({placeholders}) AND (approved = 1 OR feedback_score >= 4.0)",
#             peer_ids
#         ).fetchall()

#         conn.close()

#         if not peer_treatments:
#             return None

#         # Aggregate recommendations
#         herb_freq = {}
#         diet_freq = {}
#         yoga_freq = {}
#         life_freq = {}
#         total_feedback = 0.0
#         feedback_count = 0

#         for t in peer_treatments:
#             if t["feedback_score"] is not None:
#                 total_feedback += t["feedback_score"]
#                 feedback_count += 1
            
#             for h in t["herbs"].split(","):
#                 h_clean = h.strip()
#                 if h_clean:
#                     herb_freq[h_clean] = herb_freq.get(h_clean, 0) + 1
#             for d in t["diet"].split(";"):
#                 d_clean = d.strip()
#                 if d_clean:
#                     diet_freq[d_clean] = diet_freq.get(d_clean, 0) + 1
#             for y in t["yoga"].split(";"):
#                 y_clean = y.strip()
#                 if y_clean:
#                     yoga_freq[y_clean] = yoga_freq.get(y_clean, 0) + 1
#             for l in t["lifestyle"].split(";"):
#                 l_clean = l.strip()
#                 if l_clean:
#                     life_freq[l_clean] = life_freq.get(l_clean, 0) + 1

#         # Select most popular
#         top_herbs = sorted(herb_freq.keys(), key=lambda k: herb_freq[k], reverse=True)[:3]
#         top_diet = sorted(diet_freq.keys(), key=lambda k: diet_freq[k], reverse=True)[:2]
#         top_yoga = sorted(yoga_freq.keys(), key=lambda k: yoga_freq[k], reverse=True)[:2]
#         top_life = sorted(life_freq.keys(), key=lambda k: life_freq[k], reverse=True)[:2]

#         avg_feedback = total_feedback / feedback_count if feedback_count > 0 else 4.0
#         confidence = min(1.0, 0.7 + (avg_feedback / 5.0) * 0.3)

#         return {
#             "herbs": ", ".join(top_herbs),
#             "diet": "; ".join(top_diet),
#             "yoga": "; ".join(top_yoga),
#             "lifestyle": "; ".join(top_life),
#             "confidence_score": round(confidence, 2)
#         }

#     def hybrid_recommend(self, patient_id: str) -> dict:
#         """Main hybrid recommendation logic."""
#         conn = get_db_connection(self._db_path)
#         cursor = conn.cursor()

#         # Count visits
#         visits_count = cursor.execute(
#             "SELECT COUNT(*) FROM ehr_records WHERE patient_id = ?",
#             (patient_id,)
#         ).fetchone()[0]

#         # Get latest visit details for cold-start extraction
#         latest_visit = cursor.execute(
#             "SELECT prakriti, diagnosis FROM ehr_records WHERE patient_id = ? ORDER BY visit_date DESC LIMIT 1",
#             (patient_id,)
#         ).fetchone()

#         conn.close()

#         prakriti = latest_visit["prakriti"] if latest_visit else "Tridosha (Sama)"
#         diagnosis = latest_visit["diagnosis"] if latest_visit else "General Health Maintenance"

#         if visits_count < 3:
#             rec = self.get_cold_start(prakriti, diagnosis)
#             rec["source"] = "Cold-Start (Knowledge Base)"
#         else:
#             cluster_rec = self.get_cluster_recommendation(patient_id)
#             if cluster_rec:
#                 rec = cluster_rec
#                 rec["source"] = "Cluster-Based (Patient Similarity)"
#             else:
#                 rec = self.get_cold_start(prakriti, diagnosis)
#                 rec["source"] = "Cold-Start Fallback (Knowledge Base)"

#         # Save recommendation
#         rec_id = str(uuid.uuid4())
#         date_str = datetime.now().strftime("%Y-%m-%d")
#         approved_flag = 1 if rec["confidence_score"] >= 0.80 else 0

#         conn = get_db_connection(self._db_path)
#         conn.execute(
#             "INSERT INTO treatments "
#             "(id, patient_id, date, herbs, diet, yoga, lifestyle, confidence_score, feedback_score, approved) "
#             "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#             (
#                 rec_id,
#                 patient_id,
#                 date_str,
#                 rec["herbs"],
#                 rec["diet"],
#                 rec["yoga"],
#                 rec["lifestyle"],
#                 rec["confidence_score"],
#                 None,
#                 approved_flag
#             )
#         )
#         conn.commit()
#         conn.close()

#         rec["treatment_id"] = rec_id
#         return rec

#     def add_feedback(self, treatment_id: str, approved: bool, feedback_score: float = 5.0) -> None:
#         """Update treatment feedback scores."""
#         conn = get_db_connection(self._db_path)
#         conn.execute(
#             "UPDATE treatments SET approved = ?, feedback_score = ? WHERE id = ?",
#             (1 if approved else 0, feedback_score if approved else 1.0, treatment_id)
#         )
#         conn.commit()
#         conn.close()
#         print(f"âœ…  Feedback updated for treatment {treatment_id[:16]}... (approved={approved}, score={feedback_score})")


# # ===========================================================================
# #  EVIDENCE RETRIEVER â€” Loads YOUR Kaggle dataset (Ayurveda Dataset folder)
# # ===========================================================================

# import os
# import glob
# import re
# import math
# from pathlib import Path

# class SimpleTFIDF:
#     """Pure-Python TF-IDF Vectorizer & Cosine Similarity search engine."""
    
#     def __init__(self, docs: list[str]):
#         self.raw_docs = docs
#         self.docs = [self._tokenize(d) for d in docs]
#         self.vocab = sorted(list(set(w for doc in self.docs for w in doc)))
#         self.vocab_idx = {w: i for i, w in enumerate(self.vocab)}
        
#         # Calculate IDF
#         num_docs = len(docs)
#         self.idf = {}
#         for word in self.vocab:
#             doc_count = sum(1 for doc in self.docs if word in doc)
#             self.idf[word] = math.log((1 + num_docs) / (1 + doc_count)) + 1
            
#         # Calculate TF-IDF vectors
#         self.tfidf_vectors = [self._to_vector(doc) for doc in self.docs]
        
#     def _tokenize(self, text: str) -> list[str]:
#         return re.findall(r'\b\w+\b', text.lower())
        
#     def _to_vector(self, tokens: list[str]) -> list[float]:
#         vector = [0.0] * len(self.vocab)
#         if not tokens:
#             return vector
#         tf = {}
#         for t in tokens:
#             tf[t] = tf.get(t, 0) + 1
#         for word, count in tf.items():
#             if word in self.vocab_idx:
#                 idx = self.vocab_idx[word]
#                 vector[idx] = (count / len(tokens)) * self.idf[word]
#         # L2 Normalization
#         magnitude = math.sqrt(sum(v**2 for v in vector))
#         if magnitude > 0:
#             vector = [v / magnitude for v in vector]
#         return vector

#     def search(self, query: str, top_k: int = 3) -> list[tuple[int, float]]:
#         q_tokens = self._tokenize(query)
#         q_vector = self._to_vector(q_tokens)
        
#         results = []
#         for doc_idx, doc_vector in enumerate(self.tfidf_vectors):
#             similarity = sum(qv * dv for qv, dv in zip(q_vector, doc_vector))
#             results.append((doc_idx, similarity))
            
#         results.sort(key=lambda x: x[1], reverse=True)
#         return results[:top_k]


# class EvidenceRetriever:
#     """
#     RAG-based evidence generator using YOUR Kaggle Ayurveda dataset.
#     Loads ALL text files from ayurveda_books/ and ayurveda_texts/ folders.
#     """
    
#     def __init__(self, data_path: str = None):
#         # Auto-detect the correct folder path
#         if data_path is None:
#             # Try common locations
#             possible_paths = [
#                 "./Ayurveda Dataset",           # Your actual folder name
#                 "./ayurveda_data",              # Alternative
#                 "../Ayurveda Dataset",          # One level up
#                 "D:/ayush/Ayurveda Dataset",    # Absolute path from your screenshot
#                 "./Ayurveda_Dataset",           # Without space
#                 "./AyurvedaDataset",            # Without space
#             ]
            
#             found_path = None
#             for path in possible_paths:
#                 if Path(path).exists():
#                     found_path = path
#                     break
            
#             if found_path:
#                 self.data_path = Path(found_path)
#                 print(f"ðŸ“‚ Found dataset at: {self.data_path}")
#             else:
#                 # Use the current directory and hope the user creates the folder
#                 self.data_path = Path("./Ayurveda Dataset")
#                 print(f"âš ï¸  Dataset not found. Looking for: {self.data_path}")
#                 print("   If your dataset is in a different location, pass the path:")
#                 print("   EvidenceRetriever(data_path='D:/path/to/Ayurveda Dataset')")
#         else:
#             self.data_path = Path(data_path)
        
#         self.corpus: list[str] = []
#         self.file_sources: list[str] = []  # Track which file each chunk came from
#         self.engine: SimpleTFIDF | None = None
#         self._load_corpus_from_files()
    
#     def _load_corpus_from_files(self) -> None:
#         """Load ALL text files from the Kaggle dataset folders."""
#         print(f"\n{'='*60}")
#         print("ðŸ“š LOADING AYURVEDA CORPUS")
#         print(f"{'='*60}")
#         print(f"ðŸ“‚ Base path: {self.data_path}")
        
#         # Check if the folder exists
#         if not self.data_path.exists():
#             print(f"âŒ Folder not found: {self.data_path}")
#             print("   Creating fallback corpus...")
#             self._create_fallback_corpus()
#             return
        
#         # Look for both folders
#         books_path = self.data_path / "ayurveda_books"
#         texts_path = self.data_path / "ayurveda_texts"
        
#         print(f"ðŸ“– Books folder: {books_path} -> {'âœ… EXISTS' if books_path.exists() else 'âŒ NOT FOUND'}")
#         print(f"ðŸ“– Texts folder: {texts_path} -> {'âœ… EXISTS' if texts_path.exists() else 'âŒ NOT FOUND'}")
        
#         loaded_count = 0
#         file_count = 0
        
#         # --- Load from ayurveda_books folder (21 books) ---
#         if books_path.exists():
#             print(f"\nðŸ“– Loading from ayurveda_books/ ...")
#             all_files = []
            
#             # Get all files (PDFs and text files)
#             for ext in ['*.txt', '*.TXT', '*.pdf', '*.PDF', '*']:
#                 files = glob.glob(str(books_path / ext))
#                 all_files.extend(f for f in files if os.path.isfile(f))
            
#             # Remove duplicates
#             all_files = list(set(all_files))
#             print(f"   Found {len(all_files)} files")
            
#             for file_path in all_files[:50]:  # Limit to 50 files for performance
#                 try:
#                     content = self._read_file(file_path)
#                     if content and len(content) > 100:
#                         chunks = self._chunk_text(content, chunk_size=500)
#                         for chunk in chunks:
#                             self.corpus.append(chunk)
#                             self.file_sources.append(os.path.basename(file_path))
#                             loaded_count += 1
#                         file_count += 1
#                 except Exception as e:
#                     # Skip problematic files silently
#                     pass
            
#             print(f"   âœ… Loaded {loaded_count} chunks from {file_count} books")
#         else:
#             print(f"   âš ï¸  ayurveda_books/ not found")
        
#         # --- Load from ayurveda_texts folder (2000+ articles) ---
#         if texts_path.exists():
#             print(f"\nðŸ“– Loading from ayurveda_texts/ ...")
#             all_files = []
            
#             # Get all text files
#             for ext in ['*.txt', '*.TXT', '*']:
#                 files = glob.glob(str(texts_path / ext))
#                 all_files.extend(f for f in files if os.path.isfile(f))
            
#             all_files = list(set(all_files))
#             print(f"   Found {len(all_files)} files")
            
#             # Load first 1000 files (adjust based on performance)
#             max_files = min(len(all_files), 1000)
#             print(f"   Loading first {max_files} files...")
            
#             for file_path in all_files[:max_files]:
#                 try:
#                     content = self._read_file(file_path)
#                     if content and len(content) > 100:
#                         chunks = self._chunk_text(content, chunk_size=500)
#                         for chunk in chunks:
#                             self.corpus.append(chunk)
#                             self.file_sources.append(os.path.basename(file_path))
#                             loaded_count += 1
#                         file_count += 1
#                 except Exception as e:
#                     # Skip problematic files silently
#                     pass
            
#             print(f"   âœ… Loaded {loaded_count} chunks from {file_count} text files")
#         else:
#             print(f"   âš ï¸  ayurveda_texts/ not found")
        
#         # If we loaded nothing, use fallback
#         if loaded_count == 0:
#             print("\nâš ï¸  No files loaded. Using fallback corpus.")
#             self._create_fallback_corpus()
#         else:
#             print(f"\nâœ… Total: {loaded_count} text chunks from {file_count} files")
        
#         # Build the TF-IDF index
#         if self.corpus:
#             print("\nðŸ”¨ Building TF-IDF index...")
#             print(f"   Corpus size: {len(self.corpus)} chunks")
#             print(f"   Total characters: {sum(len(c) for c in self.corpus):,}")
#             self.engine = SimpleTFIDF(self.corpus)
#             print(f"âœ… TF-IDF index ready with {len(self.engine.vocab)} unique words!")
#         else:
#             print("âŒ No corpus loaded. TF-IDF index not created.")
        
#         print(f"{'='*60}\n")
    
#     def _read_file(self, file_path: str) -> str:
#         """Read a file, handling different encodings and PDFs."""
#         try:
#             # Check if it's a PDF
#             if file_path.lower().endswith('.pdf'):
#                 try:
#                     import PyPDF2
#                     text = ""
#                     with open(file_path, 'rb') as f:
#                         reader = PyPDF2.PdfReader(f)
#                         for page in reader.pages:
#                             text += page.extract_text()
#                     return text
#                 except ImportError:
#                     # PyPDF2 not installed, skip PDF
#                     return ""
#                 except:
#                     return ""
            
#             # Try UTF-8 first
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 return f.read()
#         except UnicodeDecodeError:
#             try:
#                 # Try Latin-1
#                 with open(file_path, 'r', encoding='latin-1') as f:
#                     return f.read()
#             except UnicodeDecodeError:
#                 try:
#                     # Try with errors='ignore'
#                     with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
#                         return f.read()
#                 except:
#                     return ""
    
#     def _chunk_text(self, text: str, chunk_size: int = 500) -> list[str]:
#         """Split text into overlapping chunks."""
#         # Clean the text
#         text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
#         text = re.sub(r'[^\w\s.,;:!?()-]', '', text)  # Remove weird characters
        
#         # Remove very long runs of text without spaces
#         text = re.sub(r'[A-Za-z]{50,}', '', text)
        
#         words = text.split()
#         chunks = []
        
#         for i in range(0, len(words), chunk_size // 2):  # 50% overlap
#             chunk = ' '.join(words[i:i + chunk_size])
#             if len(chunk) > 50:  # Only keep substantial chunks
#                 chunks.append(chunk)
        
#         return chunks[:100]  # Limit chunks per file to avoid memory issues
    
#     def _create_fallback_corpus(self) -> None:
#         """Create a fallback corpus if the dataset is not found."""
#         self.corpus = [
#             "Charaka Samhita: Ashwagandha is best among promoter of strength and vitality. It pacifies Vata and Kapha dosha, nourishing all tissues.",
#             "Charaka Samhita: Chandraprabha Vati is indicated in Prameha (diabetes) and urinary disorders. It clears blockages and reduces Kapha excess.",
#             "Charaka Samhita: Triphala is the ultimate rejuvenator. It regulates digestion, clears toxins, and balances all three doshas.",
#             "Sushruta Samhita: Gokshura is the premier herb for urinary calculi and painful micturition. It functions as a natural diuretic and pacifies Vata and Pitta.",
#             "Sushruta Samhita: Punarnava is highly effective for swelling, fluid retention, and kidney rejuvenation.",
#             "Sharangdhara Samhita: Chandraprabha Vati contains Guggulu, iron, and various herbs. It regulates insulin secretion and manages Prameha.",
#             "Classical text: Yogaraj Guggulu is the formulation of choice for Amavata (Rheumatoid Arthritis) and Vata disorders.",
#             "Herbal Monograph: Ashwagandha reduces cortisol, alleviates stress, and promotes sleep by calming the central nervous system.",
#             "Herbal Monograph: Guduchi is a potent immunomodulator beneficial in chronic fevers, cleansing the liver and spleen.",
#             "Herbal Monograph: Pippali is a strong rejuvenator for the respiratory system, helping clear mucus and relieve asthma.",
#             "Ayurvedic Pathology: Amavata is caused by accumulation of Ama in the joints. Treatment uses Guggulu and Shunthi.",
#             "Ayurvedic Pathology: Prameha arises from Kapha imbalance causing excessive turbid urine. Management requires bitter herbs.",
#             "Ayurvedic Pathology: Pandu is characterized by paleness due to depletion of Rasa and Rakta dhatus.",
#         ]
#         self.file_sources = ["fallback_corpus"] * len(self.corpus)
#         print(f"âœ… Created fallback corpus with {len(self.corpus)} entries")

#     def retrieve_evidence(self, herb: str, disease: str) -> list[dict]:
#         """Retrieve relevant text passages for any herb-disease combination."""
#         if not self.engine or not self.corpus:
#             return []
        
#         query = f"{herb} {disease}"
#         search_results = self.engine.search(query, top_k=3)
        
#         evidence_snippets = []
#         for doc_idx, score in search_results:
#             if doc_idx < len(self.corpus):
#                 text = self.corpus[doc_idx]
#                 source = self.file_sources[doc_idx] if doc_idx < len(self.file_sources) else "Unknown source"
                
#                 confidence = self._score_to_confidence(score)
                
#                 evidence_snippets.append({
#                     "text": text[:500] + ("..." if len(text) > 500 else ""),
#                     "source": source,
#                     "relevance_score": round(score, 3),
#                     "confidence": confidence
#                 })
            
#         return evidence_snippets

#     def _score_to_confidence(self, score: float) -> str:
#         if score > 0.3:
#             return "HIGH"
#         elif score > 0.15:
#             return "MEDIUM"
#         else:
#             return "LOW"

#     def get_confidence_score(self, herb: str, disease: str) -> float:
#         """Calculate numerical confidence score based on similarity match."""
#         if not self.engine:
#             return 0.0
#         query = f"{herb} {disease}"
#         search_results = self.engine.search(query, top_k=1)
#         if search_results:
#             return round(search_results[0][1], 3)
#         return 0.0
# # ---------------------------------------------------------------------------
# # Outbreak Detection Demo
# # ---------------------------------------------------------------------------
# def _run_outbreak_demo() -> None:
#     """Interactive demo of the DiseaseOutbreakDetector."""
#     print("\n" + "=" * 60)
#     print("  AYUSH Outbreak Detection Demo")
#     print("=" * 60)

#     detector = DiseaseOutbreakDetector()

#     # Step 1: Generate data & detect
#     print("\n[Step 1] Generating surveillance data...")
#     data = detector.generate_synthetic_data()

#     print("\n[Step 2] Running anomaly detection...")
#     alerts = detector.detect_anomalies(data)

#     # Step 3: Report
#     print("\n[Step 3] Generating report...")
#     detector.print_detection_report(alerts)

#     # Step 4: Recent alerts
#     print("\n[Step 4] Recent alerts (last 30 days):")
#     recent = detector.get_recent_alerts(days=30)
#     for r in recent[:10]:
#         print(f"  {r['district']:<25s} {r['disease']:<16s} "
#               f"score={r['anomaly_score']:.3f}  cases={r['cases']}  {r['date']}")
#     if len(recent) > 10:
#         print(f"  ... and {len(recent) - 10} more alerts.")


# # # ANSI Colors
# # C_GREEN = "\033[92m"
# # C_YELLOW = "\033[93m"
# # C_BLUE = "\033[94m"
# # C_RED = "\033[91m"
# # C_CYAN = "\033[96m"
# # C_BOLD = "\033[1m"
# # C_RESET = "\033[0m"

# def show_progress(msg: str) -> None:
#     import time
#     print(f"{C_CYAN}â±ï¸  {msg}", end="", flush=True)
#     for _ in range(3):
#         time.sleep(0.3)
#         print(".", end="", flush=True)
#     print(f" Done!{C_RESET}")

# def main() -> None:
#     """Main interactive menu integrating all AYUSH features."""
#     import time
#     init_database()
#     generate_sample_data()

#     voice_creator = VoiceEHRCreator()
#     outbreak_detector = DiseaseOutbreakDetector()
#     recommender = AyushRecommender()
#     evidence_retriever = EvidenceRetriever()

#     while True:
#         print("\n" + "=" * 60)
#         print(f"{C_BOLD}{C_GREEN}ðŸ€  AYUSH AI SYSTEM - CLINICAL PORTAL v1.0  ðŸ€{C_RESET}")
#         print("=" * 60)
#         print(f"1. {C_CYAN}ðŸŽ¤ Create EHR via Voice Input (Hindi/English){C_RESET}")
#         print(f"2. {C_YELLOW}ðŸš¨ View Outbreak Alerts & Disease Trends{C_RESET}")
#         print(f"3. {C_BLUE}ðŸ’Š Get Personalized Treatment Plan & Evidence{C_RESET}")
#         print(f"4. {C_GREEN}ðŸ“œ Show Classical Treatment Evidence (RAG){C_RESET}")
#         print(f"5. {C_GREEN}âœ… Submit Clinician Feedback on Treatments{C_RESET}")
#         print(f"6. {C_CYAN}ðŸ“Š System Dashboard & Analytics{C_RESET}")
#         print(f"7. {C_RED}ðŸšª Exit{C_RESET}")
#         print("=" * 60)

#         choice = input(f"{C_BOLD}Select option (1-7): {C_RESET}").strip()

#         if choice == "1":
#             print(f"\n{C_BOLD}--- Create EHR via Voice Input ---{C_RESET}")
#             patient_id = input("Enter Patient ID (e.g. PAT-0001) [Press Enter to auto-generate]: ").strip()
#             if not patient_id:
#                 patient_id = f"PAT-{random.randint(100, 999):04d}"
#                 print(f"Auto-generated Patient ID: {C_YELLOW}{patient_id}{C_RESET}")
            
#             print("\nSelect voice input language:")
#             print("1. English (en-US)")
#             print("2. Hindi / à¤¹à¤¿à¤‚à¤¦à¥€ (hi-IN)")
#             lang_choice = input("Select choice (1/2): ").strip()
            
#             if lang_choice == "1":
#                 text = voice_creator.listen_english()
#                 show_progress("Processing English voice transcript")
#                 voice_creator.create_ehr(patient_id, text, language="en")
#             elif lang_choice == "2":
#                 text = voice_creator.listen_hindi()
#                 show_progress("Processing Hindi voice transcript")
#                 voice_creator.create_ehr(patient_id, text, language="hi")
#             else:
#                 print(f"{C_RED}Invalid language choice.{C_RESET}")

#         elif choice == "2":
#             print(f"\n{C_BOLD}--- Outbreak Alerts & Trends ---{C_RESET}")
#             show_progress("Analyzing 120-day outbreak surveillance data")
#             alerts = outbreak_detector.detect_anomalies()
#             outbreak_detector.print_detection_report(alerts)

#         elif choice == "3":
#             print(f"\n{C_BOLD}--- Get Personalized Treatment Plan ---{C_RESET}")
#             patient_id = input("Enter Patient ID (e.g. PAT-0001): ").strip()
#             if not patient_id:
#                 print(f"{C_RED}Patient ID cannot be empty.{C_RESET}")
#                 continue
            
#             show_progress("Running hybrid recommendation pipeline")
#             rec = recommender.hybrid_recommend(patient_id)
            
#             print("\n" + "â”€" * 50)
#             print(f"{C_BOLD}{C_GREEN}ðŸ“‹  TREATMENT RECOMMENDATION{C_RESET}")
#             print("â”€" * 50)
#             print(f"Patient ID:  {patient_id}")
#             print(f"Source:      {C_CYAN}{rec['source']}{C_RESET}")
#             print(f"Confidence:  {C_GREEN}{rec['confidence_score']*100:.1f}%{C_RESET}")
#             print(f"Herbs:       {C_YELLOW}{rec['herbs']}{C_RESET}")
#             print(f"Diet:        {rec['diet']}")
#             print(f"Yoga/Asana:  {rec['yoga']}")
#             print(f"Lifestyle:   {rec['lifestyle']}")
#             print("â”€" * 50)

#             # RAG Integration
#             show_progress("Retrieving evidence snippets for recommended herbs")
#             print(f"\n{C_BOLD}ðŸ“– RAG Classical Evidence Context:{C_RESET}")
#             for herb in rec["herbs"].split(","):
#                 h_name = herb.strip()
#                 if not h_name:
#                     continue
#                 snippets = evidence_retriever.retrieve_evidence(h_name, "general")
#                 if snippets:
#                     print(f"\n  * {C_BOLD}{h_name}{C_RESET} Evidence:")
#                     for idx, s in enumerate(snippets[:2]):
#                         print(f"    - [{s['confidence']} Match score={s['relevance_score']}]: \"{s['text']}\"")

#         elif choice == "4":
#             print(f"\n{C_BOLD}--- Show Classical Treatment Evidence (RAG) ---{C_RESET}")
#             herb = input("Enter Herb name (e.g., Ashwagandha, Chandraprabha Vati): ").strip()
#             disease = input("Enter Disease name (e.g., diabetes, arthritis, fever): ").strip()
#             if not herb or not disease:
#                 print(f"{C_RED}Herb and disease names are required.{C_RESET}")
#                 continue
            
#             show_progress(f"Searching Ayurvedic corpus for {herb} + {disease}")
#             snippets = evidence_retriever.retrieve_evidence(herb, disease)
#             print(f"\n{C_BOLD}Matches for: {herb} + {disease}{C_RESET}")
#             print("=" * 60)
#             for idx, s in enumerate(snippets):
#                 print(f"{idx+1}. [{s['confidence']} match, relevance: {s['relevance_score']}]:")
#                 print(f"   \"{s['text']}\"\n")

#         elif choice == "5":
#             print(f"\n{C_BOLD}--- Submit Clinician Feedback ---{C_RESET}")
#             patient_id = input("Enter Patient ID (e.g. PAT-0001): ").strip()
#             if not patient_id:
#                 print(f"{C_RED}Patient ID required.{C_RESET}")
#                 continue
            
#             # Find last treatment
#             conn = get_db_connection()
#             t = conn.execute(
#                 "SELECT id, date, herbs, approved FROM treatments WHERE patient_id = ? ORDER BY date DESC LIMIT 1",
#                 (patient_id,)
#             ).fetchone()
#             conn.close()

#             if not t:
#                 print(f"{C_RED}No previous treatment recommendations found for this patient.{C_RESET}")
#                 continue
            
#             print(f"\nFound latest treatment from {C_YELLOW}{t['date']}{C_RESET}:")
#             print(f"  Herbs: {t['herbs']}")
#             print(f"  Current Approval Status: {'APPROVED' if t['approved'] == 1 else 'PENDING/REJECTED'}")
            
#             feedback = input("\nDo you approve this treatment? (y/n): ").strip().lower()
#             approved = (feedback == "y")
            
#             score_input = input("Enter quality score (1.0 to 5.0, where 5 is highest) [Press Enter for 5.0]: ").strip()
#             try:
#                 score = float(score_input) if score_input else 5.0
#                 if not (1.0 <= score <= 5.0):
#                     raise ValueError
#             except ValueError:
#                 score = 5.0
#                 print(f"{C_YELLOW}Invalid input. Using default score: 5.0{C_RESET}")
            
#             recommender.add_feedback(t["id"], approved, score)

#         elif choice == "6":
#             print(f"\n{C_BOLD}--- System Dashboard & Analytics ---{C_RESET}")
#             show_progress("Calculating real-time platform analytics")
            
#             conn = get_db_connection()
#             cursor = conn.cursor()
            
#             total_patients = cursor.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
#             total_ehr = cursor.execute("SELECT COUNT(*) FROM ehr_records").fetchone()[0]
#             total_treatments = cursor.execute("SELECT COUNT(*) FROM treatments").fetchone()[0]
            
#             # Top recommended herbs
#             all_t = cursor.execute("SELECT herbs FROM treatments").fetchall()
#             herb_freq = {}
#             for t in all_t:
#                 for h in t["herbs"].split(","):
#                     h_clean = h.strip()
#                     if h_clean:
#                         herb_freq[h_clean] = herb_freq.get(h_clean, 0) + 1
#             top_herbs = sorted(herb_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            
#             # Feedback approval stats
#             feedback_stats = cursor.execute(
#                 "SELECT COUNT(*), AVG(feedback_score) FROM treatments WHERE feedback_score IS NOT NULL"
#             ).fetchone()
            
#             conn.close()

#             print("\n" + "=" * 50)
#             print(f"{C_BOLD}{C_GREEN}ðŸ“Š  IMPACT PLATFORM ANALYTICS{C_RESET}")
#             print("=" * 50)
#             print(f"  Total Registered Patients : {C_CYAN}{total_patients}{C_RESET}")
#             print(f"  Total Clinical EHR Visits : {C_CYAN}{total_ehr}{C_RESET}")
#             print(f"  Total Recommendations Given: {C_CYAN}{total_treatments}{C_RESET}")
            
#             print(f"\n  {C_BOLD}ðŸŒ¿ Top 5 Recommended Herbs:{C_RESET}")
#             for rank, (h_name, count) in enumerate(top_herbs):
#                 print(f"    {rank+1}. {h_name:<25s} ({count} times)")
                
#             print(f"\n  {C_BOLD}ðŸ“ˆ Clinician Feedback Success Rate:{C_RESET}")
#             if feedback_stats and feedback_stats[0] > 0:
#                 print(f"    - Rated Treatments : {feedback_stats[0]} recommendations")
#                 print(f"    - Average Clinician Rating : {C_GREEN}{feedback_stats[1]:.2f} / 5.00{C_RESET}")
#             else:
#                 print("    - No clinician feedback submitted yet.")
#             print("=" * 50)

#         elif choice == "7":
#             print(f"\n{C_GREEN}Thank you for using the AYUSH Clinical Portal. Namaste. ðŸ™{C_RESET}\n")
#             break
#         else:
#             print(f"{C_RED}Invalid option selected. Please select a valid option from 1 to 7.{C_RESET}")

# if __name__ == "__main__":
#     main()
"""
AYUSH System â€” Neural RAG with AI Models
========================================
No googletrans dependency - uses simple text processing instead.
"""

import sys
import sqlite3
import random
import uuid
import os
import re
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
import glob
import time

# ANSI Colors
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_RED = "\033[91m"
C_CYAN = "\033[96m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def safe_print(text: str = "", end: str = "\n") -> None:
    try:
        sys.stdout.write(text + end)
        sys.stdout.flush()
    except UnicodeEncodeError:
        fallback = text
        replacements = {
            "âœ…": "[OK]", "âš ï¸": "[WARN]", "âŒ": "[ERROR]", "ðŸŽ™ï¸": "[MIC]",
            "ðŸ“Š": "[STATS]", "ðŸŒ¿": "[HERB]", "ðŸ“ˆ": "[TREND]", "ðŸ“‹": "[PLAN]",
            "ðŸ€": "[AYUSH]", "ðŸ§¬": "[GENE]", "ðŸš¨": "[ALERT]", "ðŸ’Š": "[PLAN]",
            "ðŸ“œ": "[EVIDENCE]", "ðŸ“–": "[DOC]", "ðŸ™": "[NAMASTE]"
        }
        for emoji, representation in replacements.items():
            fallback = fallback.replace(emoji, representation)
        try:
            sys.stdout.write(fallback.encode("ascii", errors="replace").decode("ascii") + end)
            sys.stdout.flush()
        except Exception:
            print(text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"), end=end)

def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")

def print_splash_screen() -> None:
    clear_screen()
    safe_print(f"{C_BOLD}{C_GREEN}")
    safe_print("â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•—  â–ˆâ–ˆâ•— â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— ")
    safe_print("â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•”â•â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—")
    safe_print("â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â• â•šâ–ˆâ–ˆâ–ˆâ–ˆâ•”â• â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘")
    safe_print("â–ˆâ–ˆâ•”â•â•â•â•   â•šâ–ˆâ–ˆâ•”â•  â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â•šâ•â•â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•‘")
    safe_print("â–ˆâ–ˆâ•‘        â–ˆâ–ˆâ•‘   â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘")
    safe_print("â•šâ•â•        â•šâ•â•    â•šâ•â•â•â•â•â• â•šâ•â•â•â•â•â•â•â•šâ•â•  â•šâ•â•â•šâ•â•  â•šâ•â•")
    safe_print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    safe_print(f"      NEURAL RAG - AYUSH Clinical Grid           ")
    safe_print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€" + C_RESET)

def format_treatment_plan(rec: dict) -> str:
    lines = []
    lines.append("â”€" * 50)
    lines.append(f"{C_BOLD}{C_GREEN}ðŸ“‹  PRESCRIBED PROTOCOL{C_RESET}")
    lines.append("â”€" * 50)
    lines.append(f"  Source:      {C_CYAN}{rec.get('source', 'Unknown')}{C_RESET}")
    lines.append(f"  Confidence:  {C_GREEN}{rec.get('confidence_score', 0.0)*100:.1f}%{C_RESET}")
    lines.append(f"  Herbs:       {C_YELLOW}{rec.get('herbs', 'Unspecified')}{C_RESET}")
    lines.append(f"  Dietary:     {rec.get('diet', 'None')}")
    lines.append(f"  Yoga/Asanas: {rec.get('yoga', 'None')}")
    lines.append(f"  Lifestyle:   {rec.get('lifestyle', 'None')}")
    lines.append("â”€" * 50)
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ayush.db")
MODELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODELS_PATH, exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_database(db_path: str | None = None) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS ehr_records (
            id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, visit_date TEXT NOT NULL,
            symptoms TEXT, diagnosis TEXT, prakriti TEXT, comorbidities TEXT,
            raw_text TEXT, translated_text TEXT, language TEXT
        );
        CREATE TABLE IF NOT EXISTS treatments (
            id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, date TEXT NOT NULL,
            herbs TEXT, diet TEXT, yoga TEXT, lifestyle TEXT,
            confidence_score REAL DEFAULT 0.0, feedback_score REAL, approved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS outbreak_alerts (
            id TEXT PRIMARY KEY, district TEXT NOT NULL, disease TEXT NOT NULL,
            anomaly_score REAL DEFAULT 0.0, date_detected TEXT NOT NULL, cases_reported INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS patient_history (
            patient_id TEXT PRIMARY KEY, age INTEGER, bmi REAL,
            comorbidities_count INTEGER DEFAULT 0, outcome TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ehr_patient ON ehr_records(patient_id);
        CREATE INDEX IF NOT EXISTS idx_treat_patient ON treatments(patient_id);
    """)
    conn.commit()
    conn.close()
    print("âœ…  Database schema initialised.")

def generate_sample_data(db_path: str | None = None) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    existing = cursor.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
    if existing > 0:
        print("âš ï¸  Data already exists â€” skipping generation.")
        conn.close()
        return

    random.seed(42)
    now = datetime.now()
    start_date = now - timedelta(days=365)
    end_date = now

    # Domain constants (simplified)
    prakriti_types = ["Vata", "Pitta", "Kapha", "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Tridosha (Sama)"]
    symptoms_pool = ["joint pain", "fatigue", "indigestion", "headache", "fever", "cough", "back pain", "burning sensation"]
    diagnoses_pool = ["Amavata (Rheumatoid Arthritis)", "Pandu (Anemia)", "Prameha (Diabetes)", "Jwara (Fever)"]
    herbs_pool = ["Ashwagandha", "Triphala", "Guduchi", "Brahmi", "Shatavari", "Haridra", "Tulsi", "Neem"]
    diet_pool = ["warm cooked meals", "avoid cold food", "light dinner", "ghee with meals", "warm water"]
    yoga_pool = ["Surya Namaskar", "Pranayama", "Bhujangasana", "Shavasana", "Kapalbhati"]
    lifestyle_pool = ["sleep by 10 PM", "wake before sunrise", "Abhyanga daily", "walk 30 min"]
    comorbidities_pool = ["Hypertension", "Diabetes", "Obesity", "Asthma"]
    districts = ["Varanasi", "Jaipur", "Thiruvananthapuram", "Haridwar", "Mysuru"]
    outbreak_diseases = ["Dengue", "Chikungunya", "Malaria", "Typhoid"]
    languages = ["English", "Hindi"]
    outcomes = ["improved", "stable", "worsened", "remission", "ongoing_treatment"]

    def _pick(pool: list, low: int = 1, high: int = 3) -> str:
        count = random.randint(low, min(high, len(pool)))
        return ", ".join(random.sample(pool, count))

    def _random_date(start: datetime, end: datetime) -> str:
        delta = (end - start).days
        offset = random.randint(0, max(delta, 0))
        return (start + timedelta(days=offset)).strftime("%Y-%m-%d")

    for i in range(100):
        pid = f"PAT-{i+1:04d}"
        age = random.randint(18, 85)
        bmi = round(random.uniform(16.0, 38.0), 1)
        n_comorbidities = random.choices([0, 1, 2, 3, 4], weights=[30, 30, 20, 12, 8])[0]
        outcome = random.choice(outcomes)
        cursor.execute("INSERT INTO patient_history VALUES (?, ?, ?, ?, ?)", (pid, age, bmi, n_comorbidities, outcome))

        patient_comorbidities = _pick(comorbidities_pool, 1, n_comorbidities) if n_comorbidities > 0 else "None"
        prakriti = random.choice(prakriti_types)
        lang = random.choice(languages)

        for _ in range(random.randint(1, 5)):
            visit_date = _random_date(start_date, end_date)
            symptoms = _pick(symptoms_pool, 2, 5)
            diagnosis = random.choice(diagnoses_pool)
            raw_text = f"Patient presents with {symptoms}. Diagnosis: {diagnosis}."
            cursor.execute(
                "INSERT INTO ehr_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, visit_date, symptoms, diagnosis, prakriti,
                 patient_comorbidities, raw_text, raw_text, lang)
            )

        for _ in range(random.randint(1, 4)):
            t_date = _random_date(start_date, end_date)
            herbs = _pick(herbs_pool, 2, 5)
            diet = _pick(diet_pool, 2, 4)
            yoga = _pick(yoga_pool, 1, 3)
            lifestyle = _pick(lifestyle_pool, 1, 3)
            confidence = round(random.uniform(0.55, 0.98), 2)
            approved = 1 if confidence > 0.75 and random.random() > 0.2 else 0
            cursor.execute(
                "INSERT INTO treatments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, t_date, herbs, diet, yoga, lifestyle, confidence, None, approved)
            )

    # Outbreak data
    surveillance_start = now - timedelta(days=120)
    outbreak_events = [{"district": "Varanasi", "disease": "Dengue", "peak_day": 45, "intensity": 5.0},
                       {"district": "Thiruvananthapuram", "disease": "Leptospirosis", "peak_day": 90, "intensity": 4.2}]
    for day_offset in range(120):
        current_date = (surveillance_start + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for district in districts:
            disease = random.choice(outbreak_diseases)
            base_cases = random.randint(2, 15)
            anomaly_score = round(random.uniform(0.0, 0.3), 3)
            for event in outbreak_events:
                if district == event["district"] and disease == event["disease"]:
                    distance = abs(day_offset - event["peak_day"])
                    if distance <= 12:
                        spike_factor = event["intensity"] * max(0, 1 - (distance / 12))
                        extra_cases = int(base_cases * spike_factor)
                        base_cases += extra_cases
                        anomaly_score = round(min(1.0, 0.5 + spike_factor * 0.15), 3)
            cursor.execute(
                "INSERT INTO outbreak_alerts VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), district, disease, anomaly_score, current_date, base_cases)
            )
    conn.commit()
    conn.close()
    print("âœ…  Synthetic data generated successfully.")

# ===========================================================================
#  VOICE EHR CREATOR (No googletrans)
# ===========================================================================

class VoiceEHRCreator:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DB_PATH
        self._recognizer = None
        self._mic_available = False
        
        # Simple Hindi keyword mapping (fallback for translation)
        self.hindi_to_english = {
            'à¤¬à¥à¤–à¤¾à¤°': 'fever',
            'à¤¸à¤¿à¤° à¤¦à¤°à¥à¤¦': 'headache',
            'à¤œà¥‹à¤¡à¤¼à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¦à¤°à¥à¤¦': 'joint pain',
            'à¤•à¤®à¤° à¤¦à¤°à¥à¤¦': 'back pain',
            'à¤–à¤¾à¤‚à¤¸à¥€': 'cough',
            'à¤¥à¤•à¤¾à¤¨': 'fatigue',
            'à¤œà¤²à¤¨': 'burning sensation',
            'à¤ªà¤¿à¤¤à¥à¤¤': 'pitta',
            'à¤µà¤¾à¤¤': 'vata',
            'à¤•à¤«': 'kapha',
            'à¤—à¥à¤°à¥à¤¦à¥‡ à¤•à¥€ à¤ªà¤¥à¤°à¥€': 'kidney stones',
            'à¤‰à¤šà¥à¤š à¤°à¤•à¥à¤¤à¤šà¤¾à¤ª': 'hypertension',
            'à¤®à¤§à¥à¤®à¥‡à¤¹': 'diabetes',
        }
        
        try:
            import speech_recognition as sr
            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
        except ImportError:
            print("[VoiceEHR] WARNING: 'speech_recognition' not installed.")
            self._sr = None
            
        if self._sr is not None:
            try:
                mic = self._sr.Microphone()
                self._mic_available = True
                del mic
            except:
                pass

    def _listen(self, language_code: str, prompt: str) -> str | None:
        if not self._mic_available or self._recognizer is None:
            return None
        sr = self._sr
        print(f"\nðŸŽ™ï¸  {prompt}")
        try:
            with sr.Microphone() as source:
                print("   ðŸ”‡  Calibrating...")
                self._recognizer.adjust_for_ambient_noise(source, duration=1.0)
                print("   ðŸŸ¢  Listening...")
                audio = self._recognizer.listen(source, timeout=8, phrase_time_limit=30)
            print("   â³  Transcribing...")
            text = self._recognizer.recognize_google(audio, language=language_code)
            print(f"   âœ…  Transcribed: \"{text}\"")
            return text
        except Exception as e:
            print(f"   âš ï¸  Error: {e}")
            return None

    def listen_hindi(self) -> str:
        result = self._listen("hi-IN", "à¤•à¥ƒà¤ªà¤¯à¤¾ à¤¹à¤¿à¤‚à¤¦à¥€ à¤®à¥‡à¤‚ à¤¬à¥‹à¤²à¥‡à¤‚")
        if result is None:
            print("\nâŒ¨ï¸  Falling back to text input.")
            result = input("   Type in Hindi/English: ").strip()
            if not result:
                result = "à¤¬à¥à¤–à¤¾à¤° à¤”à¤° à¤¸à¤¿à¤° à¤¦à¤°à¥à¤¦ à¤¹à¥ˆ, à¤ªà¤¿à¤¤à¥à¤¤ à¤ªà¥à¤°à¤•à¥ƒà¤¤à¤¿"
        return result

    def listen_english(self) -> str:
        result = self._listen("en-US", "Please speak in English")
        if result is None:
            print("\nâŒ¨ï¸  Falling back to text input.")
            result = input("   Type in English: ").strip()
            if not result:
                result = "Patient has fever and joint pain, Vata-Pitta prakriti"
        return result

    def _simple_translate(self, hindi_text: str) -> str:
        """Simple Hindi to English translation using keyword mapping."""
        result = hindi_text
        for hi, en in self.hindi_to_english.items():
            if hi in result:
                result = result.replace(hi, en)
        return result

    def extract_entities(self, text: str, language: str = "en") -> dict:
        text_lower = text.lower()
        found_symptoms = []
        found_diagnoses = []
        found_prakriti = None

        # Simple keyword matching
        symptoms_map = {
            'joint pain': ['joint pain', 'joint pain', 'joint'],
            'fever': ['fever', 'fever', 'à¤¤à¤¾à¤ª'],
            'headache': ['headache', 'headache', 'à¤¸à¤¿à¤° à¤¦à¤°à¥à¤¦'],
            'cough': ['cough', 'cough', 'à¤–à¤¾à¤‚à¤¸à¥€'],
            'fatigue': ['fatigue', 'fatigue', 'à¤¥à¤•à¤¾à¤¨'],
            'back pain': ['back pain', 'back pain', 'à¤•à¤®à¤° à¤¦à¤°à¥à¤¦'],
            'burning': ['burning', 'burning', 'à¤œà¤²à¤¨'],
        }
        
        for symptom, patterns in symptoms_map.items():
            for p in patterns:
                if p in text_lower:
                    found_symptoms.append(symptom)
                    break

        diagnoses_map = {
            'Amavata (Rheumatoid Arthritis)': ['amavata', 'arthritis', 'joint pain chronic'],
            'Pandu (Anemia)': ['pandu', 'anemia', 'low blood'],
            'Prameha (Diabetes)': ['prameha', 'diabetes', 'sugar'],
            'Jwara (Fever)': ['jwara', 'fever', 'fever'],
        }
        
        for diagnosis, patterns in diagnoses_map.items():
            for p in patterns:
                if p in text_lower:
                    found_diagnoses.append(diagnosis)
                    break

        prakriti_map = {
            'Vata': ['vata', 'à¤µà¤¾à¤¤'],
            'Pitta': ['pitta', 'à¤ªà¤¿à¤¤à¥à¤¤'],
            'Kapha': ['kapha', 'à¤•à¤«'],
        }
        
        for prakriti, patterns in prakriti_map.items():
            for p in patterns:
                if p in text_lower:
                    found_prakriti = prakriti
                    break

        return {
            "symptoms": found_symptoms,
            "diagnosis": found_diagnoses,
            "prakriti": found_prakriti
        }

    def create_ehr(self, patient_id: str, voice_text: str, language: str = "en") -> dict:
        print(f"\nðŸ“‹  Creating EHR for patient: {patient_id}")
        
        # Simple translation if Hindi
        if language == "hi":
            translated_text = self._simple_translate(voice_text)
        else:
            translated_text = voice_text

        entities = self.extract_entities(voice_text, language)
        entities_en = self.extract_entities(translated_text, "en")

        symptoms = list(set(entities["symptoms"] + entities_en["symptoms"]))
        diagnosis = list(set(entities["diagnosis"] + entities_en["diagnosis"]))
        prakriti = entities["prakriti"] or entities_en["prakriti"] or "not assessed"

        record = {
            "id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "visit_date": datetime.now().strftime("%Y-%m-%d"),
            "symptoms": ", ".join(symptoms) if symptoms else "unspecified",
            "diagnosis": diagnosis[0] if diagnosis else "pending evaluation",
            "prakriti": prakriti,
            "comorbidities": "None",
            "raw_text": voice_text,
            "translated_text": translated_text,
            "language": "Hindi" if language == "hi" else "English",
        }

        conn = get_db_connection(self._db_path)
        conn.execute(
            "INSERT INTO ehr_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record["id"], record["patient_id"], record["visit_date"],
             record["symptoms"], record["diagnosis"], record["prakriti"],
             record["comorbidities"], record["raw_text"], record["translated_text"], record["language"])
        )
        conn.commit()
        conn.close()
        print(f"   âœ…  EHR saved successfully!")
        return record

# ===========================================================================
#  DISEASE OUTBREAK DETECTOR
# ===========================================================================

class DiseaseOutbreakDetector:
    """
    Detects localized disease-surge anomalies from historical outbreak
    surveillance data using Isolation Forest (with a z-score fallback when
    scikit-learn isn't available), smoothed by 3-day/7-day rolling averages.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DB_PATH
        self._sklearn_available = False
        try:
            from sklearn.ensemble import IsolationForest
            self._IsolationForest = IsolationForest
            self._sklearn_available = True
        except ImportError:
            pass

    def _load_series(self) -> dict:
        """Load (district, disease) -> [(date, cases_reported), ...] time series."""
        conn = get_db_connection(self._db_path)
        rows = conn.execute(
            "SELECT district, disease, date_detected, cases_reported "
            "FROM outbreak_alerts ORDER BY district, disease, date_detected"
        ).fetchall()
        conn.close()

        series = {}
        for r in rows:
            key = (r["district"], r["disease"])
            series.setdefault(key, []).append((r["date_detected"], r["cases_reported"]))
        return series

    @staticmethod
    def _rolling_avg(values: list, window: int) -> list:
        out = []
        for i in range(len(values)):
            lo = max(0, i - window + 1)
            chunk = values[lo:i + 1]
            out.append(sum(chunk) / len(chunk))
        return out

    @staticmethod
    def _severity(z: float) -> str:
        if z >= 2.5:
            return "HIGH"
        elif z >= 1.5:
            return "MEDIUM"
        return "LOW"

    def detect_anomalies(self, lookback_days: int = 14, top_n: int = 10) -> list[dict]:
        """
        Scan every (district, disease) time series for statistically anomalous
        recent case spikes and return the most recent alert per district/disease,
        sorted by severity/date. Returns [] gracefully if no data exists yet.
        """
        series = self._load_series()
        alerts = []

        for (district, disease), points in series.items():
            if len(points) < 10:
                continue

            dates = [p[0] for p in points]
            cases = [p[1] for p in points]
            roll3 = self._rolling_avg(cases, 3)
            roll7 = self._rolling_avg(cases, 7)

            mean = sum(cases) / len(cases)
            variance = sum((c - mean) ** 2 for c in cases) / len(cases)
            std = math.sqrt(variance) or 1.0

            if self._sklearn_available and len(cases) >= 15:
                import numpy as np
                X = np.array(list(zip(cases, roll3, roll7)))
                model = self._IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
                preds = model.fit_predict(X)
                raw_scores = -model.score_samples(X)  # higher => more anomalous
                is_anomaly = [p == -1 for p in preds]
                anomaly_scores = [float(s) for s in raw_scores]
            else:
                anomaly_scores = [(c - mean) / std for c in cases]
                is_anomaly = [s >= 1.5 for s in anomaly_scores]

            recent_idx = range(max(0, len(cases) - lookback_days), len(cases))
            best_idx = None
            for i in recent_idx:
                if is_anomaly[i]:
                    if best_idx is None or cases[i] > cases[best_idx]:
                        best_idx = i

            if best_idx is not None:
                z = (cases[best_idx] - mean) / std
                alerts.append({
                    "district": district,
                    "disease": disease,
                    "date": dates[best_idx],
                    "cases": cases[best_idx],
                    "baseline_avg": round(mean, 1),
                    "rolling_avg_7d": round(roll7[best_idx], 1),
                    "severity": self._severity(z),
                    "anomaly_score": round(anomaly_scores[best_idx], 3),
                })

        severity_rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
        alerts.sort(key=lambda a: (severity_rank[a["severity"]], a["date"]), reverse=True)
        self._flag_regional_clusters(alerts, window_days=10)
        return alerts[:top_n]

    @staticmethod
    def _flag_regional_clusters(alerts: list[dict], window_days: int = 10) -> None:
        """
        Lightweight stand-in for geospatial clustering / spatiotemporal spread
        detection: if the same disease shows an anomaly in 2+ districts within
        a short time window, it's flagged as a likely regional cluster rather
        than an isolated local blip â€” a much stronger outbreak signal.
        """
        by_disease: dict = {}
        for a in alerts:
            by_disease.setdefault(a["disease"], []).append(a)

        for disease, group in by_disease.items():
            dates = [datetime.strptime(a["date"], "%Y-%m-%d") for a in group]
            for a, d in zip(group, dates):
                co_occurring = [
                    g["district"] for g, gd in zip(group, dates)
                    if g["district"] != a["district"] and abs((gd - d).days) <= window_days
                ]
                a["regional_cluster"] = bool(co_occurring)
                a["cluster_districts"] = sorted(set(co_occurring))


# ===========================================================================
#  AYUSH RECOMMENDER
# ===========================================================================

class AyushRecommender:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DB_PATH
        self._kmeans = None
        self._patient_clusters = {}   # patient_id -> cluster label
        self._cluster_fit_count = 0   # number of patients the model was fit on (cache-invalidation trigger)

    # -----------------------------------------------------------------
    # Patient clustering (real KMeans over demographic/clinical features)
    # -----------------------------------------------------------------
    def _fit_patient_clusters(self) -> None:
        """
        Fit KMeans over (age, bmi, comorbidities_count) so patients with
        similar demographic/clinical profiles land in the same cluster.
        Cheap to refit; cached and only rebuilt when the patient count changes.
        """
        conn = get_db_connection(self._db_path)
        rows = conn.execute("SELECT patient_id, age, bmi, comorbidities_count FROM patient_history").fetchall()
        conn.close()

        if len(rows) == self._cluster_fit_count and self._kmeans is not None:
            return  # cache still valid

        if len(rows) < 4:
            self._kmeans = None
            self._patient_clusters = {}
            self._cluster_fit_count = len(rows)
            return

        try:
            import numpy as np
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler

            ids = [r["patient_id"] for r in rows]
            X = np.array([[r["age"], r["bmi"], r["comorbidities_count"]] for r in rows], dtype=float)
            X_scaled = StandardScaler().fit_transform(X)

            n_clusters = max(2, min(6, len(rows) // 15))
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = model.fit_predict(X_scaled)

            self._kmeans = model
            self._patient_clusters = dict(zip(ids, labels.tolist()))
            self._cluster_fit_count = len(rows)
        except Exception as e:
            print(f"âš ï¸  Patient clustering failed ({e}). Falling back to cold-start only.")
            self._kmeans = None
            self._patient_clusters = {}
            self._cluster_fit_count = len(rows)

    def _get_cluster_peers(self, patient_id: str) -> list[str]:
        """Return other patient_ids sharing this patient's cluster."""
        self._fit_patient_clusters()
        if not self._patient_clusters or patient_id not in self._patient_clusters:
            return []
        my_cluster = self._patient_clusters[patient_id]
        return [pid for pid, c in self._patient_clusters.items() if c == my_cluster and pid != patient_id]

    def _peer_herb_stats(self, peer_ids: list[str]) -> dict:
        """
        Aggregate herb usage among a peer group's *approved* treatments,
        weighted by clinician feedback score â€” this is the piece that lets
        clinician feedback continuously reshape future recommendations
        (a lightweight, interpretable stand-in for full RL fine-tuning).
        """
        if not peer_ids:
            return {}
        conn = get_db_connection(self._db_path)
        placeholders = ",".join("?" for _ in peer_ids)
        rows = conn.execute(
            f"SELECT herbs, feedback_score FROM treatments "
            f"WHERE patient_id IN ({placeholders}) AND approved = 1",
            peer_ids
        ).fetchall()
        conn.close()

        stats = {}
        for row in rows:
            score = row["feedback_score"] if row["feedback_score"] is not None else 3.0
            for h in (row["herbs"] or "").split(","):
                h = h.strip()
                if not h:
                    continue
                s = stats.setdefault(h, {"count": 0, "total_feedback": 0.0})
                s["count"] += 1
                s["total_feedback"] += score

        for h, s in stats.items():
            s["avg_feedback"] = round(s["total_feedback"] / s["count"], 2)
        return stats

    COLD_START_KB = {
        "Vata": {"herbs": "Ashwagandha, Guggulu, Triphala", "diet": "Warm cooked meals, ghee", "yoga": "Shavasana, Pawanmuktasana", "lifestyle": "Abhyanga daily, sleep by 10 PM"},
        "Pitta": {"herbs": "Guduchi, Shatavari, Brahmi", "diet": "Avoid spicy foods, cooling foods", "yoga": "Bhujangasana, Sheetali Pranayama", "lifestyle": "Avoid heat, walk in nature"},
        "Kapha": {"herbs": "Punarnava, Pippali, Gokshura", "diet": "Light meals, avoid dairy", "yoga": "Surya Namaskar, Kapalbhati", "lifestyle": "Wake before sunrise, active exercise"},
        "Vata-Pitta": {"herbs": "Ashwagandha, Shatavari, Brahmi", "diet": "Warm and cooling balance", "yoga": "Anulom Vilom, Shavasana", "lifestyle": "Regular routine, avoid stress"},
        "Pitta-Kapha": {"herbs": "Guduchi, Punarnava, Triphala", "diet": "Light and cooling foods", "yoga": "Meditation, Surya Namaskar", "lifestyle": "Stay active, walk post meals"},
        "Vata-Kapha": {"herbs": "Ashwagandha, Pippali, Gokshura", "diet": "Warm light cooked meals", "yoga": "Kapalbhati, Surya Namaskar", "lifestyle": "Stay warm, active exercise"},
        "Tridosha (Sama)": {"herbs": "Triphala, Guduchi, Ashwagandha", "diet": "Balanced seasonal diet", "yoga": "Nadi Shodhana, Surya Namaskar", "lifestyle": "Balanced daily routine"},
    }

    DIAGNOSIS_REMEDIES = {
        "Amavata": {"herbs": "Guggulu, Ashwagandha", "diet": "Avoid yogurt, drink ginger tea", "yoga": "Gentle joint movements", "lifestyle": "Dry heat fermentation"},
        "Pandu": {"herbs": "Punarnava, Amalaki", "diet": "Pomegranate, beetroot, greens", "yoga": "Nadi Shodhana", "lifestyle": "Morning sunlight, rest"},
        "Prameha": {"herbs": "Chandraprabha Vati, Haridra", "diet": "Barley, bitter gourd", "yoga": "Paschimottanasana, Kapalbhati", "lifestyle": "Brisk walking, avoid day sleeping"},
        "Jwara": {"herbs": "Guduchi, Tulsi, Pippali", "diet": "Light gruel, hot water", "yoga": "Rest (Shavasana)", "lifestyle": "Complete bed rest"},
    }

    def get_cold_start(self, prakriti: str, diagnosis: str) -> dict:
        prak_rec = self.COLD_START_KB.get(prakriti, self.COLD_START_KB["Tridosha (Sama)"])
        diag_rec = None
        for d_key, remedies in self.DIAGNOSIS_REMEDIES.items():
            if d_key.lower() in diagnosis.lower() or diagnosis.lower() in d_key.lower():
                diag_rec = remedies
                break
        if not diag_rec:
            diag_rec = {"herbs": "Triphala, Guduchi", "diet": "Light freshly cooked warm food", "yoga": "Nadi Shodhana", "lifestyle": "Adequate rest"}

        herbs = list(set([h.strip() for h in (prak_rec["herbs"] + ", " + diag_rec["herbs"]).split(",") if h.strip()]))
        return {
            "herbs": ", ".join(herbs[:5]),
            "diet": prak_rec["diet"] + "; " + diag_rec["diet"],
            "yoga": prak_rec["yoga"] + "; " + diag_rec["yoga"],
            "lifestyle": prak_rec["lifestyle"] + "; " + diag_rec["lifestyle"],
            "confidence_score": 0.85,
            "source": "Cold-Start (Knowledge Base)"
        }

    def hybrid_recommend(self, patient_id: str) -> dict:
        conn = get_db_connection(self._db_path)
        cursor = conn.cursor()
        visits_count = cursor.execute("SELECT COUNT(*) FROM ehr_records WHERE patient_id = ?", (patient_id,)).fetchone()[0]
        latest_visit = cursor.execute("SELECT prakriti, diagnosis FROM ehr_records WHERE patient_id = ? ORDER BY visit_date DESC LIMIT 1", (patient_id,)).fetchone()
        has_history = cursor.execute("SELECT COUNT(*) FROM patient_history WHERE patient_id = ?", (patient_id,)).fetchone()[0] > 0
        conn.close()

        prakriti = latest_visit["prakriti"] if latest_visit else "Tridosha (Sama)"
        diagnosis = latest_visit["diagnosis"] if latest_visit else "General Health Maintenance"

        rec = self.get_cold_start(prakriti, diagnosis)
        rec["diagnosis"] = diagnosis
        rec["prakriti"] = prakriti
        explanation = [f"Cold-start base: Prakriti '{prakriti}' + diagnosis '{diagnosis}' matched against the codified AYUSH knowledge base."]

        # Hybrid step: for patients with enough history, blend in real KMeans
        # patient-similarity clustering + clinician-feedback-weighted herb stats.
        if visits_count >= 3 and has_history:
            peers = self._get_cluster_peers(patient_id)
            herb_stats = self._peer_herb_stats(peers)

            if herb_stats:
                ranked = sorted(
                    herb_stats.items(),
                    key=lambda kv: (kv[1]["avg_feedback"], kv[1]["count"]),
                    reverse=True
                )
                # Drop herbs with a poor historical approval/feedback record
                # (bandit-style exploitation of clinician feedback).
                ranked = [(h, s) for h, s in ranked if s["avg_feedback"] >= 2.5] or ranked
                top_peer_herbs = [h for h, _ in ranked[:3]]

                cold_herbs = [h.strip() for h in rec["herbs"].split(",") if h.strip()]
                combined = list(dict.fromkeys(top_peer_herbs + cold_herbs))[:5]
                rec["herbs"] = ", ".join(combined)
                rec["source"] = "Cluster-Based (Patient Similarity + Feedback)"

                top_herb, top_stat = ranked[0]
                agreement = top_stat["count"] / max(len(peers), 1)
                rec["confidence_score"] = round(min(0.97, 0.80 + agreement * 0.15), 2)
                explanation.append(
                    f"{len(peers)} patients with similar age/BMI/comorbidity profile were grouped by KMeans "
                    f"clustering; '{top_herb}' appeared in {top_stat['count']}/{len(peers)} of their approved "
                    f"treatments with an average clinician feedback score of {top_stat['avg_feedback']}/5."
                )
            else:
                explanation.append(
                    f"Found {len(peers)} similar patients via clustering, but none have approved/rated "
                    f"treatments yet â€” using the cold-start knowledge base until feedback accumulates."
                )
        else:
            explanation.append(
                "Limited patient history (fewer than 3 recorded visits) â€” using cold-start "
                "recommendation only until enough longitudinal data is available for clustering."
            )

        rec["explanation"] = " ".join(explanation)

        rec_id = str(uuid.uuid4())
        conn = get_db_connection(self._db_path)
        conn.execute(
            "INSERT INTO treatments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rec_id, patient_id, datetime.now().strftime("%Y-%m-%d"),
             rec["herbs"], rec["diet"], rec["yoga"], rec["lifestyle"],
             rec["confidence_score"], None, 1 if rec["confidence_score"] >= 0.80 else 0)
        )
        conn.commit()
        conn.close()

        rec["treatment_id"] = rec_id
        return rec

    def add_feedback(self, treatment_id: str, approved: bool, feedback_score: float = 5.0) -> None:
        conn = get_db_connection(self._db_path)
        conn.execute("UPDATE treatments SET approved = ?, feedback_score = ? WHERE id = ?",
                     (1 if approved else 0, feedback_score if approved else 1.0, treatment_id))
        conn.commit()
        conn.close()
        print(f"âœ…  Feedback updated")

# ===========================================================================
#  NEURAL RAG WITH AI MODELS
# ===========================================================================

class _TfidfEmbedder:
    """
    Offline vector-embedding fallback used when sentence-transformers/HF Hub
    is unavailable (no internet, blocked network, air-gapped hospital
    deployment, etc). Exposes the same .encode()/.get_sentence_embedding_dimension()
    interface as a SentenceTransformer so it can be dropped into the same
    ChromaDB indexing/query path with zero other code changes.
    """

    def __init__(self, corpus: list[str]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
        corpus = corpus or [""]
        self.vectorizer.fit(corpus)
        self._dim = len(self.vectorizer.get_feature_names_out()) or 1

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

    def encode(self, texts):
        matrix = self.vectorizer.transform(texts)
        return matrix.toarray()


class NeuralRAG:
    """
    Neural RAG implementation with Sentence Transformers + ChromaDB.
    No googletrans dependency!
    """
    
    def __init__(self, data_path: str = None, use_llm: bool = False):
        self.use_llm = use_llm
        self.embedding_model = None
        self.llm_model = None
        self.llm_tokenizer = None
        self.collection = None
        self.chroma_client = None
        self.corpus = []
        self.file_sources = []
        
        # Find dataset path
        if data_path is None:
            possible_paths = [
                "./Ayurveda Dataset",
                "../Ayurveda Dataset",
                "D:/ayush/Ayurveda Dataset",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Ayurveda Dataset"),
            ]
            found_path = None
            for path in possible_paths:
                if Path(path).exists():
                    found_path = path
                    break
            self.data_path = Path(found_path) if found_path else Path("./Ayurveda Dataset")
        else:
            self.data_path = Path(data_path)
        
        print("\n" + "=" * 60)
        print("ðŸ§  INITIALIZING NEURAL RAG SYSTEM")
        print("=" * 60)
        
        # Step 1: Load the data (limited for performance)
        self._load_corpus()
        
        # Step 2: Load embedding model
        self._load_embedding_model()
        
        # Step 3: Setup ChromaDB
        self._setup_vector_db()
        
        # Step 4: Load LLM (optional)
        if self.use_llm:
            self._load_llm()
        
        print("=" * 60)
        print(f"âœ… Neural RAG System Ready!")
        print(f"   ðŸ“š Corpus: {len(self.corpus)} chunks")
        print(f"   ðŸ§¬ Model: {self.embedding_model_name if hasattr(self, 'embedding_model_name') else 'None'}")
        print(f"   ðŸ¤– LLM: {'Loaded' if self.use_llm else 'Disabled'}")
        print("=" * 60 + "\n")
    
    def _load_corpus(self):
        """Load text chunks from your dataset (limited for performance)"""
        print("\nðŸ“š Loading Ayurveda corpus...")
        
        if not self.data_path.exists():
            print(f"âŒ Dataset not found at: {self.data_path}")
            self._create_fallback_corpus()
            return
        
        books_path = self.data_path / "ayurveda_books"
        texts_path = self.data_path / "ayurveda_texts"
        
        loaded_count = 0
        max_chunks = 300  # Limit for memory
        
        # Load from books (priority)
        if books_path.exists():
            print("   ðŸ“– Loading from ayurveda_books/...")
            book_files = []
            for ext in ['*.txt', '*.TXT']:
                book_files.extend(glob.glob(str(books_path / ext)))
            book_files = list(set(book_files))
            
            for file_path in book_files[:30]:
                content = self._read_file(file_path)
                if content and len(content) > 200:
                    chunks = self._chunk_text(content, max_chunks_per_file=4)
                    for chunk in chunks:
                        if len(self.corpus) < max_chunks:
                            self.corpus.append(chunk)
                            self.file_sources.append(os.path.basename(file_path))
                            loaded_count += 1
        
        # Load from texts (sample)
        if texts_path.exists() and len(self.corpus) < max_chunks:
            print("   ðŸ“– Sampling from ayurveda_texts/...")
            all_files = glob.glob(str(texts_path / "*.txt")) + glob.glob(str(texts_path / "*.TXT"))
            all_files = list(set(all_files))
            random.seed(42)
            random.shuffle(all_files)
            
            for file_path in all_files[:50]:
                content = self._read_file(file_path)
                if content and len(content) > 200:
                    chunks = self._chunk_text(content, max_chunks_per_file=2)
                    for chunk in chunks:
                        if len(self.corpus) < max_chunks:
                            self.corpus.append(chunk)
                            self.file_sources.append(os.path.basename(file_path))
                            loaded_count += 1
        
        if loaded_count == 0:
            print("   âš ï¸  No files loaded. Using fallback.")
            self._create_fallback_corpus()
        else:
            print(f"   âœ… Loaded {loaded_count} chunks")
    
    def _read_file(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except:
                return ""
    
    def _chunk_text(self, text: str, max_chunks_per_file: int = 3) -> list:
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        chunks = []
        current = ""
        for sentence in sentences[:20]:
            if len(current) + len(sentence) < 400:
                current += sentence + ". "
            else:
                if current:
                    chunks.append(current)
                current = sentence + ". "
        if current:
            chunks.append(current)
        return chunks[:max_chunks_per_file]
    
    def _create_fallback_corpus(self):
        self.corpus = [
            "Charaka Samhita: Ashwagandha is best among promoter of strength and vitality.",
            "Charaka Samhita: Chandraprabha Vati is indicated in Prameha (diabetes).",
            "Charaka Samhita: Triphala is the ultimate rejuvenator.",
            "Sushruta Samhita: Gokshura is the premier herb for urinary calculi.",
            "Sushruta Samhita: Punarnava is highly effective for kidney rejuvenation.",
            "Sushruta Samhita: Ashwagandha is used in Jwara (fever).",
            "Sharangdhara Samhita: Chandraprabha Vati contains Guggulu and iron.",
            "Classical text: Yogaraj Guggulu is for Amavata.",
            "Herbal Monograph: Ashwagandha reduces cortisol and stress.",
            "Herbal Monograph: Guduchi is a potent immunomodulator.",
            "Herbal Monograph: Pippali is a rejuvenator for the respiratory system.",
            "Ayurvedic Pathology: Amavata is caused by Ama in joints.",
        ]
        self.file_sources = ["fallback"] * len(self.corpus)
    
    def _load_embedding_model(self):
        """
        Load an embedding model using a graceful 3-tier fallback chain:
          1. sentence-transformers (semantic, needs internet on first run)
          2. TF-IDF vectors (statistical, fully offline, no download needed)
          3. None -> NeuralRAG.search() falls back further to keyword overlap
        """
        print("\nðŸ§¬ Loading embedding model...")
        try:
            from sentence_transformers import SentenceTransformer

            self.embedding_model_name = 'all-MiniLM-L6-v2'
            model_path = os.path.join(MODELS_PATH, self.embedding_model_name)

            if os.path.exists(model_path):
                print(f"   ðŸ“ Found cached model at: {model_path}")
            else:
                print(f"   ðŸ“¥ Downloading model '{self.embedding_model_name}' (~80 MB)...")
                print("   â³ This will take 2-5 minutes on first run...")

            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            print(f"   âœ… Model loaded! Vector dimension: {self.embedding_model.get_sentence_embedding_dimension()}")
            return

        except ImportError:
            print("   âŒ sentence-transformers not installed.")
        except Exception as e:
            # Covers network errors, blocked Hugging Face Hub access, air-gapped
            # hospital networks, HF Hub outages, etc.
            print(f"   âš ï¸  Could not load transformer model ({e}).")

        # Tier 2: offline TF-IDF vector embeddings (no network required)
        try:
            self.embedding_model_name = 'TF-IDF (offline vectors)'
            self.embedding_model = _TfidfEmbedder(self.corpus)
            print(f"   âœ… Using offline TF-IDF vector embeddings "
                  f"(dim={self.embedding_model.get_sentence_embedding_dimension()}) â€” "
                  f"no internet required, works in air-gapped deployments.")
        except Exception as e:
            print(f"   âš ï¸  TF-IDF fallback failed ({e}). Using keyword search fallback.")
            self.embedding_model = None
            self.embedding_model_name = None
    
    def _setup_vector_db(self):
        """Setup ChromaDB for vector storage"""
        print("\nðŸ’¾ Setting up vector database...")

        if self.embedding_model is None:
            print("   âš ï¸  No embedding model available - skipping vector DB, using keyword search fallback.")
            self.collection = None
            return

        try:
            import chromadb

            chroma_path = os.path.join(MODELS_PATH, "chroma_db")
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            
            collection_name = "ayurveda_corpus"
            existing_collections = self.chroma_client.list_collections()
            
            if collection_name in [c.name for c in existing_collections]:
                print(f"   ðŸ“ Found existing collection: {collection_name}")
                self.collection = self.chroma_client.get_collection(collection_name)
            else:
                print(f"   ðŸ†• Creating new collection: {collection_name}")
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                
                if self.corpus:
                    print(f"   ðŸ”¨ Indexing {len(self.corpus)} documents...")
                    self._index_documents()
            
        except ImportError:
            print("   âŒ chromadb not installed. Run: pip install chromadb. Using keyword search fallback.")
            self.collection = None
        except Exception as e:
            print(f"   âš ï¸  Vector DB setup failed ({e}). Using keyword search fallback.")
            self.collection = None
    
    def _index_documents(self):
        """Index documents in ChromaDB"""
        if not self.corpus:
            return
        
        batch_size = 50
        for i in range(0, len(self.corpus), batch_size):
            batch = self.corpus[i:i+batch_size]
            batch_sources = self.file_sources[i:i+batch_size]
            
            embeddings = self.embedding_model.encode(batch)
            
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=batch,
                metadatas=[{"source": s} for s in batch_sources],
                ids=[f"doc_{i+j}" for j in range(len(batch))]
            )
            
            if (i + batch_size) % 100 == 0:
                print(f"      Indexed {i + batch_size}/{len(self.corpus)} docs")
        
        print(f"   âœ… Indexed {len(self.corpus)} documents")
    
    def _load_llm(self):
        """Load a small LLM for generative responses (optional)"""
        print("\nðŸ¤– Loading LLM model...")
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            model_name = "microsoft/phi-2"
            print(f"   ðŸ“¥ Downloading '{model_name}' (~2.7 GB)...")
            print("   â³ This will take 5-15 minutes on first run...")
            
            self.llm_tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.llm_model = AutoModelForCausalLM.from_pretrained(
                model_name, 
                trust_remote_code=True,
                torch_dtype="auto",
                device_map="auto"
            )
            print("   âœ… LLM loaded successfully!")
            
        except ImportError:
            print("   âš ï¸  transformers not installed. LLM disabled.")
            self.use_llm = False
        except Exception as e:
            print(f"   âš ï¸  LLM loading failed: {e}. Disabled.")
            self.use_llm = False
    
    def _keyword_search(self, query: str, top_k: int = 3) -> list[dict]:
        """Simple keyword-overlap search used when embeddings/vector DB are unavailable."""
        if not self.corpus:
            return []

        query_terms = [t for t in re.findall(r"[a-zA-Z]+", query.lower()) if len(t) > 2]
        if not query_terms:
            return []

        scored = []
        for doc, source in zip(self.corpus, self.file_sources):
            doc_lower = doc.lower()
            hits = sum(doc_lower.count(term) for term in query_terms)
            if hits > 0:
                scored.append((hits, doc, source))

        scored.sort(key=lambda x: x[0], reverse=True)
        max_hits = scored[0][0] if scored else 1

        evidence = []
        for hits, doc, source in scored[:top_k]:
            similarity = round(hits / max_hits, 3)
            confidence = "HIGH" if similarity > 0.66 else "MEDIUM" if similarity > 0.33 else "LOW"
            evidence.append({
                "text": doc[:400] + ("..." if len(doc) > 400 else ""),
                "source": source,
                "relevance_score": similarity,
                "confidence": confidence,
                "full_text": doc
            })
        return evidence

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Neural search using embeddings, with keyword fallback."""
        if not self.collection or not self.embedding_model:
            return self._keyword_search(query, top_k)
        
        try:
            query_embedding = self.embedding_model.encode([query]).tolist()
            
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            evidence = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                if doc:
                    similarity = 1 - dist
                    confidence = "HIGH" if similarity > 0.5 else "MEDIUM" if similarity > 0.3 else "LOW"
                    evidence.append({
                        "text": doc[:400] + ("..." if len(doc) > 400 else ""),
                        "source": meta.get("source", "Unknown"),
                        "relevance_score": round(similarity, 3),
                        "confidence": confidence,
                        "full_text": doc
                    })
            
            return evidence
            
        except Exception as e:
            print(f"âŒ Search error: {e}")
            return []
    
    def generate_response(self, query: str, evidence: list[dict]) -> str:
        """Generate AI response using LLM (if available)"""
        if not self.use_llm or not self.llm_model:
            response = f"Query: {query}\n\n"
            for i, e in enumerate(evidence, 1):
                response += f"{i}. {e['text']}\n   Source: {e['source']}\n\n"
            return response
        
        try:
            context = "\n".join([f"- {e['text']}" for e in evidence])
            prompt = f"""Based on the following Ayurvedic texts:

{context}

Question: How does this Ayurvedic knowledge apply to a patient with {query}?

Answer: Let me explain the Ayurvedic perspective:"""
            
            inputs = self.llm_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.llm_model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True
            )
            return self.llm_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
        except Exception as e:
            print(f"âŒ LLM generation error: {e}")
            return f"Based on Ayurvedic texts: {evidence[0]['text'] if evidence else 'No evidence found'}"
    
    def get_evidence(self, herb: str, disease: str) -> list[dict]:
        """Main API method for RAG retrieval"""
        query = f"{herb} {disease}"
        return self.search(query, top_k=3)

# ===========================================================================
#  MAIN
# ===========================================================================

def main():
    init_database()
    generate_sample_data()

    voice_creator = VoiceEHRCreator()
    outbreak_detector = DiseaseOutbreakDetector()
    recommender = AyushRecommender()
    
    # Initialize Neural RAG
    print("\n" + "=" * 60)
    print("ðŸ§  INITIALIZING NEURAL RAG SYSTEM")
    print("=" * 60)
    use_llm = input("Load LLM for generative responses? (y/n, default=n): ").strip().lower() == 'y'
    rag = NeuralRAG(data_path="./Ayurveda Dataset", use_llm=use_llm)

    while True:
        print("\n" + "=" * 60)
        print(f"{C_BOLD}{C_GREEN}ðŸ€  NEURAL RAG - AYUSH CLINICAL PORTAL  ðŸ€{C_RESET}")
        print("=" * 60)
        print(f"1. {C_CYAN}ðŸŽ¤ Create EHR via Voice Input{C_RESET}")
        print(f"2. {C_YELLOW}ðŸš¨ View Outbreak Alerts{C_RESET}")
        print(f"3. {C_BLUE}ðŸ’Š Get Treatment Plan (with Neural RAG){C_RESET}")
        print(f"4. {C_GREEN}ðŸ“œ Neural RAG Evidence Search{C_RESET}")
        print(f"5. {C_GREEN}âœ… Submit Clinician Feedback{C_RESET}")
        print(f"6. {C_CYAN}ðŸ“Š System Dashboard{C_RESET}")
        print(f"7. {C_RED}ðŸšª Exit{C_RESET}")
        print("=" * 60)

        choice = input(f"{C_BOLD}Select option (1-7): {C_RESET}").strip()

        if choice == "1":
            patient_id = input("Patient ID (Enter for auto): ").strip()
            if not patient_id:
                patient_id = f"PAT-{random.randint(100, 999):04d}"
            print("\n1. English\n2. Hindi")
            lang_choice = input("Select: ").strip()
            if lang_choice == "1":
                text = voice_creator.listen_english()
                if text:
                    voice_creator.create_ehr(patient_id, text, "en")
            elif lang_choice == "2":
                text = voice_creator.listen_hindi()
                if text:
                    voice_creator.create_ehr(patient_id, text, "hi")

        elif choice == "2":
            print("\nðŸ“Š Outbreak Alerts:")
            alerts = outbreak_detector.detect_anomalies()
            if not alerts:
                print("  No anomalies detected in current surveillance data.")
            else:
                sev_color = {"HIGH": C_RED, "MEDIUM": C_YELLOW, "LOW": C_CYAN}
                for a in alerts:
                    color = sev_color.get(a["severity"], C_CYAN)
                    print(f"  {color}[{a['severity']}]{C_RESET} {a['district']} â€” {a['disease']}: "
                          f"{a['cases']} cases on {a['date']} (baseline avg {a['baseline_avg']}, "
                          f"score {a['anomaly_score']})")

        elif choice == "3":
            patient_id = input("Enter Patient ID: ").strip()
            if not patient_id:
                print("âŒ Patient ID required")
                continue
            
            rec = recommender.hybrid_recommend(patient_id)
            print(format_treatment_plan(rec))
            
            top_herb = rec["herbs"].split(",")[0].strip() if rec["herbs"] else "general"
            print(f"\n{C_BOLD}ðŸ§  Neural RAG Evidence for {top_herb}:{C_RESET}")
            evidence = rag.get_evidence(top_herb, rec["diagnosis"].split()[0] if rec["diagnosis"] else "general")
            
            if evidence:
                for e in evidence:
                    print(f"\n  [{e['confidence']}] Score: {e['relevance_score']}")
                    print(f"  ðŸ“– {e['text']}")
                    print(f"  ðŸ“‚ Source: {e['source']}")
                
                if rag.use_llm:
                    print(f"\n{C_BOLD}ðŸ¤– AI-Generated Summary:{C_RESET}")
                    response = rag.generate_response(top_herb, evidence)
                    print(f"  {response[:300]}...")
            else:
                print("  No evidence found in corpus")

        elif choice == "4":
            herb = input("Enter Herb name: ").strip()
            disease = input("Enter Disease name: ").strip()
            if not herb or not disease:
                print("âŒ Both fields required")
                continue
            
            print(f"\nðŸ§  Neural RAG Search: {herb} + {disease}")
            evidence = rag.get_evidence(herb, disease)
            
            if evidence:
                for i, e in enumerate(evidence, 1):
                    print(f"\n{i}. [{e['confidence']}] Score: {e['relevance_score']}")
                    print(f"   ðŸ“– {e['text']}")
                    print(f"   ðŸ“‚ Source: {e['source']}")
            else:
                print("  No evidence found")

        elif choice == "5":
            patient_id = input("Enter Patient ID: ").strip()
            if not patient_id:
                print("âŒ Patient ID required")
                continue
            conn = get_db_connection()
            t = conn.execute("SELECT id, date, herbs FROM treatments WHERE patient_id = ? ORDER BY date DESC LIMIT 1", (patient_id,)).fetchone()
            conn.close()
            if not t:
                print("âŒ No treatments found")
                continue
            print(f"\nLatest treatment: {t['herbs']} ({t['date']})")
            approved = input("Approve? (y/n): ").strip().lower() == 'y'
            recommender.add_feedback(t["id"], approved, 5.0 if approved else 1.0)

        elif choice == "6":
            conn = get_db_connection()
            total = conn.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
            treatments = conn.execute("SELECT COUNT(*) FROM treatments").fetchone()[0]
            conn.close()
            print(f"\nðŸ“Š Dashboard:")
            print(f"  Patients: {total}")
            print(f"  Treatments: {treatments}")
            print(f"  RAG Corpus: {len(rag.corpus)} chunks")
            if rag.embedding_model:
                print(f"  Embedding Model: {rag.embedding_model_name}")

        elif choice == "7":
            print(f"\n{C_GREEN}Thank you! Namaste. ðŸ™{C_RESET}")
            break
        else:
            print(f"{C_RED}Invalid option{C_RESET}")

if __name__ == "__main__":
    main()
