# database.py
"""
SQLite schema + connection helper + synthetic demo data.

The synthetic data exists ONLY so the dashboard has something to show on a
fresh install. Every real patient/EHR/treatment/outbreak record created
through the API is stored in the same tables and is what actually drives
the recommender and outbreak engine once the system is in use.
"""
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta

import config


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _migrate_schema(cursor: sqlite3.Cursor, table: str, expected_columns: dict) -> None:
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    for column, ddl_type in expected_columns.items():
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def init_database(db_path: str | None = None) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS ehr_records (
            id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, visit_date TEXT NOT NULL,
            symptoms TEXT, diagnosis TEXT, prakriti TEXT, comorbidities TEXT,
            raw_text TEXT, translated_text TEXT, language TEXT,
            district TEXT, confidence_score REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS treatments (
            id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, date TEXT NOT NULL,
            diagnosis TEXT, herbs TEXT, diet TEXT, yoga TEXT, lifestyle TEXT,
            confidence_score REAL DEFAULT 0.0, feedback_score REAL, approved INTEGER DEFAULT 0,
            ml_score REAL DEFAULT 0.0, retrieval_score REAL DEFAULT 0.0,
            llm_response TEXT, evidence_json TEXT
        );

        CREATE TABLE IF NOT EXISTS outbreak_alerts (
            id TEXT PRIMARY KEY, district TEXT NOT NULL, disease TEXT NOT NULL,
            anomaly_score REAL DEFAULT 0.0, date_detected TEXT NOT NULL,
            cases_reported INTEGER DEFAULT 0, severity TEXT,
            latitude REAL, longitude REAL, region_cluster TEXT
        );

        CREATE TABLE IF NOT EXISTS patient_history (
            patient_id TEXT PRIMARY KEY, age INTEGER, bmi REAL,
            comorbidities_count INTEGER DEFAULT 0, outcome TEXT,
            prakriti TEXT, feature_vector TEXT
        );

        -- One row per (diagnosis, herb) pair. Powers the reinforcement-learning
        -- style feedback loop: every clinician approval/rejection nudges the
        -- reward for that herb under that diagnosis, so future recommendations
        -- for the same diagnosis prefer herbs that worked before.
        CREATE TABLE IF NOT EXISTS herb_feedback_stats (
            diagnosis TEXT NOT NULL, herb TEXT NOT NULL,
            successes REAL DEFAULT 1.0, trials REAL DEFAULT 2.0,
            PRIMARY KEY (diagnosis, herb)
        );
        """
    )

    _migrate_schema(cursor, "ehr_records", {
        "district": "TEXT",
    })
    _migrate_schema(cursor, "treatments", {
        "diagnosis": "TEXT", "retrieval_score": "REAL DEFAULT 0.0", "evidence_json": "TEXT",
    })
    _migrate_schema(cursor, "outbreak_alerts", {
        "latitude": "REAL", "longitude": "REAL",
    })
    _migrate_schema(cursor, "patient_history", {
        "prakriti": "TEXT",
    })

    cursor.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_ehr_patient ON ehr_records(patient_id);
        CREATE INDEX IF NOT EXISTS idx_treat_patient ON treatments(patient_id);
        CREATE INDEX IF NOT EXISTS idx_outbreak_district ON outbreak_alerts(district);
        CREATE INDEX IF NOT EXISTS idx_outbreak_date ON outbreak_alerts(date_detected);
        """
    )
    conn.commit()
    conn.close()


def generate_sample_data(db_path: str | None = None) -> None:
    """Populates demo patients/EHRs/treatments/outbreak history on first run only."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    existing = cursor.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    random.seed(config.RANDOM_SEED)
    now = datetime.now()

    prakriti_types = ["Vata", "Pitta", "Kapha", "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Tridoshic"]
    symptoms_pool = ["joint pain", "fatigue", "indigestion", "headache", "fever", "cough",
                      "back pain", "burning sensation", "cold", "body ache"]
    diagnoses_pool = ["Amavata (Rheumatoid Arthritis)", "Pandu (Anemia)", "Prameha (Diabetes)",
                       "Jwara (Fever)", "Kasa (Cough)", "Obesity", "Hypertension", "Urolithiasis"]
    comorbidities_pool = ["Hypertension", "Diabetes", "Obesity", "Asthma"]
    districts = list(config.DISTRICT_COORDS.keys())
    outbreak_diseases = ["Dengue", "Chikungunya", "Malaria", "Typhoid", "Leptospirosis"]
    languages = ["English", "Hindi"]
    outcomes = ["improved", "stable", "worsened", "remission", "ongoing_treatment"]

    def _pick(pool, low=1, high=3):
        return ", ".join(random.sample(pool, random.randint(low, min(high, len(pool)))))

    def _random_date(start, end):
        delta = (end - start).days
        return (start + timedelta(days=random.randint(0, max(delta, 0)))).strftime("%Y-%m-%d")

    start_date = now - timedelta(days=365)
    for i in range(150):
        pid = f"PAT-{i + 1:04d}"
        age = random.randint(18, 85)
        bmi = round(random.uniform(16.0, 38.0), 1)
        n_como = random.choices([0, 1, 2, 3, 4], weights=[30, 30, 20, 12, 8])[0]
        outcome = random.choice(outcomes)
        prakriti = random.choice(prakriti_types)
        cursor.execute(
            "INSERT INTO patient_history VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pid, age, bmi, n_como, outcome, prakriti, ""),
        )
        district = random.choice(districts)
        lang = random.choice(languages)

        for _ in range(random.randint(1, 5)):
            visit_date = _random_date(start_date, now)
            symptoms = _pick(symptoms_pool, 2, 5)
            diagnosis = random.choice(diagnoses_pool)
            raw_text = f"Patient presents with {symptoms}. Diagnosis: {diagnosis}."
            cursor.execute(
                "INSERT INTO ehr_records "
                "(id, patient_id, visit_date, symptoms, diagnosis, prakriti, comorbidities, "
                "raw_text, translated_text, language, district, confidence_score) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), pid, visit_date, symptoms, diagnosis, prakriti,
                 _pick(comorbidities_pool, 0, n_como) if n_como else "None",
                 raw_text, raw_text, lang, district, 0.0),
            )

    surveillance_start = now - timedelta(days=120)
    outbreak_events = [
        {"district": "Varanasi", "disease": "Dengue", "peak_day": 45, "intensity": 5.0},
        {"district": "Thiruvananthapuram", "disease": "Leptospirosis", "peak_day": 90, "intensity": 4.2},
        {"district": "Lucknow", "disease": "Typhoid", "peak_day": 70, "intensity": 3.5},
    ]
    for day_offset in range(120):
        current_date = (surveillance_start + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for district in districts:
            disease = random.choice(outbreak_diseases)
            base_cases = random.randint(2, 15)
            for event in outbreak_events:
                if district == event["district"] and disease == event["disease"]:
                    distance = abs(day_offset - event["peak_day"])
                    if distance <= 12:
                        spike = event["intensity"] * max(0, 1 - distance / 12)
                        base_cases += int(base_cases * spike)
            lat, lon = config.DISTRICT_COORDS[district]
            cursor.execute(
                "INSERT INTO outbreak_alerts "
                "(id, district, disease, anomaly_score, date_detected, cases_reported, "
                "severity, latitude, longitude, region_cluster) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), district, disease, 0.0, current_date, base_cases,
                 "LOW", lat, lon, ""),
            )

    conn.commit()
    conn.close()

