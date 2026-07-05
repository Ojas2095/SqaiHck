# knowledge_base.py
"""
Loads BOTH local datasets (the 10,000-row ayurveda_dataset.csv and the
446-row AyurGenixAI_Dataset.xlsx) and the optional BhashaBench-Ayur set,
and turns them into:

  1. `records`      -- a unified list of dicts, one per disease entry, with
                        the same field names regardless of which file it
                        came from. This is what the recommender and the
                        NER gazetteer are built from.
  2. `chunks`        -- one retrievable text passage per record, for the
                        RAG engine to embed/index.
  3. vocabularies for symptoms / diseases / herbs, mined directly from the
     data (used by the gazetteer-based NER so it always matches this
     dataset's vocabulary instead of a generic pretrained label set).

NOTE on a bug in the previous version: the Excel loader used
`pd.read_excel(path, header=1)`, which threw away the real header row and
used the first *data* row ("Cough, ...") as column names instead. That
silently broke every column lookup in the old code (they were all falling
back to "N/A"). This loader uses `header=0`, which is correct here â€”
verified by inspecting the file directly.
"""
import os
import re
from typing import Dict, List, Optional

import pandas as pd

import config


def _split_list(value: str) -> List[str]:
    if not value or not isinstance(value, str):
        return []
    parts = re.split(r"[;,]", value)
    return [p.strip() for p in parts if p.strip() and p.strip().lower() != "nan"]


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


class KnowledgeBase:
    def __init__(self, csv_path: str = config.CSV_KNOWLEDGE_PATH,
                 xlsx_path: str = config.XLSX_KNOWLEDGE_PATH,
                 not_there_path: str = config.NOT_THERE_CSV_PATH,
                 hf_token: Optional[str] = config.HF_TOKEN):
        self.csv_path = csv_path
        self.xlsx_path = xlsx_path
        self.not_there_path = not_there_path
        self.hf_token = hf_token

        self.records: List[Dict] = []
        self.chunks: List[str] = []
        self.chunk_sources: List[str] = []

        self.symptom_vocab: set = set()
        self.disease_vocab: set = set()
        self.herb_vocab: set = set()

        # disease name (lowercased) -> list of record indices, for direct
        # lookup by the recommender (fast path, no embedding needed)
        self.by_disease: Dict[str, List[int]] = {}

        # kept for an optional /api/benchmark self-test endpoint only
        self.bhashabench_en = pd.DataFrame()
        self.bhashabench_hi = pd.DataFrame()

    # ------------------------------------------------------------------
    def load_all(self) -> None:
        self._load_csv()
        self._load_xlsx()
        self._load_not_there()
        self._build_vocab()
        self._build_index()

    def _add_record(self, rec: Dict, source: str) -> None:
        idx = len(self.records)
        self.records.append(rec)
        chunk = self._format_chunk(rec, source)
        self.chunks.append(chunk)
        self.chunk_sources.append(source)
        key = rec["disease"].strip().lower()
        if key:
            self.by_disease.setdefault(key, []).append(idx)

    @staticmethod
    def _format_chunk(rec: Dict, source: str) -> str:
        if rec.get("is_stub"):
            # Gap-analysis entry: we know the disease name and its classical
            # Ayurvedic equivalent, but have NO verified herbs/diet/remedies
            # for it. Say so explicitly rather than leaving the chunk looking
            # like a normal (empty) record, so retrieval/RAG can't present
            # this as if it were a real treatment match.
            lines = [
                f"Disease/Problem: {rec.get('disease', '')}",
                f"Ayurvedic Equivalent (name only -- NOT a verified formulation): {rec.get('ayurvedic_equivalent') or 'unknown'}",
                f"Status: {rec.get('gap_status') or 'Missing'} -- no herbs, diet, or remedy data exists for this condition in the current knowledge base.",
            ]
            if rec.get("gap_description"):
                lines.append(f"Note: {rec['gap_description']}")
            lines.append(f"[source: {source}]")
            return "\n".join(lines)

        lines = [f"Disease/Problem: {rec.get('disease', '')}"]
        for label, key in [
            ("Symptoms", "symptoms_raw"),
            ("Dosha/Prakriti", "dosha"),
            ("Body System", "body_system"),
            ("Ayurvedic Herbs", "herbs_raw"),
            ("Remedies / Formulation", "remedies_raw"),
            ("Diet & Lifestyle Recommendations", "diet"),
            ("Yoga & Physical Therapy", "yoga"),
            ("Contraindications", "contraindications"),
            ("Preventive Advice", "prevention"),
            ("Seasonal Suitability", "seasonal"),
            ("Classical / Evidence Source", "evidence_source"),
        ]:
            val = rec.get(key)
            if val:
                lines.append(f"{label}: {val}")
        lines.append(f"[source: {source}]")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def _load_csv(self) -> int:
        if not os.path.exists(self.csv_path):
            return 0
        df = pd.read_csv(self.csv_path)
        count = 0
        for _, row in df.iterrows():
            disease = _clean(row.get("Problem"))
            if not disease:
                continue
            rec = {
                "disease": disease,
                "symptoms_raw": _clean(row.get("Symptoms")),
                "dosha": _clean(row.get("Dosha Type")),
                "body_system": _clean(row.get("Body System")),
                "herbs_raw": _clean(row.get("Medicines")),
                "remedies_raw": _clean(row.get("Remedies")),
                "diet": "",
                "yoga": "",
                "contraindications": _clean(row.get("Contraindications")),
                "prevention": _clean(row.get("Preventive Advice")),
                "seasonal": _clean(row.get("Seasonal Suitability")),
                "chronic_acute": _clean(row.get("Chronic/Acute")),
                "treatment_type": _clean(row.get("Treatment Type")),
                "evidence_source": _clean(row.get("Classical Texts")) or _clean(row.get("Source")),
                "confidence": _safe_float(row.get("Confidence"), 0.7),
            }
            self._add_record(rec, source="ayurveda_dataset.csv")
            count += 1
        return count

    def _load_xlsx(self) -> int:
        if not os.path.exists(self.xlsx_path):
            return 0
        # header=0 is correct: row 0 in the file IS the real header
        # ("Disease", "Hindi Name", ...). Using header=1, as the earlier
        # version did, drops the header AND the first data row.
        df = pd.read_excel(self.xlsx_path, header=0)
        df.columns = [str(c).strip() for c in df.columns]
        count = 0
        for _, row in df.iterrows():
            disease = _clean(row.get("Disease"))
            if not disease:
                continue
            rec = {
                "disease": disease,
                "symptoms_raw": _clean(row.get("Symptoms")),
                "dosha": _clean(row.get("Doshas")) or _clean(row.get("Constitution/Prakriti")),
                "body_system": "",
                "herbs_raw": _clean(row.get("Ayurvedic Herbs")),
                "remedies_raw": _clean(row.get("Herbal/Alternative Remedies")) or _clean(row.get("Formulation")),
                "diet": _clean(row.get("Diet and Lifestyle Recommendations")) or _clean(row.get("Dietary Habits")),
                "yoga": _clean(row.get("Yoga & Physical Therapy")),
                "contraindications": _clean(row.get("Allergies (Food/Env)")),
                "prevention": _clean(row.get("Prevention")),
                "seasonal": _clean(row.get("Seasonal Variation")),
                "chronic_acute": _clean(row.get("Symptom Severity")),
                "treatment_type": _clean(row.get("Medical Intervention")),
                "evidence_source": "AyurGenixAI_Dataset",
                "confidence": 0.75,
                "prognosis": _clean(row.get("Prognosis")),
                "complications": _clean(row.get("Complications")),
                "patient_recommendations": _clean(row.get("Patient Recommendations")),
            }
            self._add_record(rec, source="AyurGenixAI_Dataset.xlsx")
            count += 1
        return count

    def _load_not_there(self) -> int:
        """Loads the gap-analysis list of diseases NOT covered by the CSV/XLSX
        datasets. Each becomes a `is_stub=True` record: disease name + its
        classical Ayurvedic/Sanskrit equivalent name only, with every
        herb/diet/remedy field left blank. This lets the NER gazetteer and
        RAG corpus *recognise* the disease name (instead of returning nothing
        for it) while making it impossible to mistake the entry for a
        verified treatment -- the recommender checks `is_stub` and refuses
        to fabricate herbs/diet/yoga for these (see recommender.py)."""
        if not os.path.exists(self.not_there_path):
            return 0
        df = pd.read_csv(self.not_there_path)
        df.columns = [str(c).strip() for c in df.columns]
        count = 0
        for _, row in df.iterrows():
            disease = _clean(row.get("Missing Disease / Condition"))
            if not disease:
                continue
            rec = {
                "disease": disease,
                "symptoms_raw": "",
                "dosha": "",
                "body_system": "",
                "herbs_raw": "",
                "remedies_raw": "",
                "diet": "",
                "yoga": "",
                "contraindications": "",
                "prevention": "",
                "seasonal": "",
                "chronic_acute": "",
                "treatment_type": "",
                "evidence_source": "not_there.csv (gap-analysis list, unmapped)",
                "confidence": 0.0,
                "ayurvedic_equivalent": _clean(row.get("Ayurvedic Equivalent")),
                "gap_status": _clean(row.get("Status")) or "Missing",
                "gap_description": _clean(row.get("Description")),
                "is_stub": True,
            }
            self._add_record(rec, source="not_there.csv")
            count += 1
        return count

    def load_bhashabench(self, max_rows: Optional[int] = config.BHASHABENCH_MAX_ROWS) -> Dict[str, str]:
        """Optional, evaluation-only. Requires HF_TOKEN + internet + accepted
        dataset terms. Never feeds into RAG/recommendation (see module docstring).

        `max_rows=None` (the default, via config.BHASHABENCH_MAX_ROWS) loads
        the FULL split for each language (~15k questions) -- it's small,
        text-only data, so there's no real memory reason to cap it. If you do
        pass a max_rows, rows are a SEEDED RANDOM SAMPLE of the full split,
        not the first N rows: the dataset appears to be grouped by exam/
        topic, so `.head(500)` (the old behaviour) silently gave you a
        skewed, topic-clustered slice rather than a representative one.

        Returns a per-language status dict (e.g. {"English": "loaded (500 rows)",
        "Hindi": "failed: <reason>"}) instead of failing silently, so startup
        logs actually show whether the gated dataset came through."""
        status: Dict[str, str] = {}
        if not self.hf_token:
            status["English"] = status["Hindi"] = "skipped (no HF_TOKEN set)"
            print("â„¹ï¸  BhashaBench-Ayur: skipped -- HF_TOKEN not set")
            return status
        try:
            from datasets import load_dataset
            from huggingface_hub import login
            login(token=self.hf_token)
        except Exception as e:
            status["English"] = status["Hindi"] = f"failed: login error ({type(e).__name__}: {e})"
            print(f"âŒ BhashaBench-Ayur: could not log in to Hugging Face -- {type(e).__name__}: {e}")
            return status

        for lang, attr in [("English", "bhashabench_en"), ("Hindi", "bhashabench_hi")]:
            try:
                ds = load_dataset(config.BHASHABENCH_DATASET, data_dir=lang, split="test", token=self.hf_token)
                df = ds.to_pandas()
                full_size = len(df)
                if max_rows and max_rows < full_size:
                    df = df.sample(n=max_rows, random_state=config.RANDOM_SEED).reset_index(drop=True)
                setattr(self, attr, df)
                note = f" (random sample of {full_size})" if max_rows and max_rows < full_size else " (full split)"
                status[lang] = f"loaded ({len(df)} rows{note})"
                print(f"âœ… BhashaBench-Ayur [{lang}]: loaded {len(df)}/{full_size} rows{note}")
            except Exception as e:
                status[lang] = f"failed: {type(e).__name__}: {e}"
                print(f"âŒ BhashaBench-Ayur [{lang}]: failed to load -- {type(e).__name__}: {e}")
                print("   Common causes: dataset access not yet approved on your HF account "
                      "(visit the dataset page and accept the gated-access terms), or no "
                      "internet access to huggingface.co from this machine.")
        return status

    # ------------------------------------------------------------------
    def _build_vocab(self) -> None:
        for rec in self.records:
            self.disease_vocab.add(rec["disease"].strip())
            for s in _split_list(rec.get("symptoms_raw", "")):
                self.symptom_vocab.add(s.lower())
            for h in _split_list(rec.get("herbs_raw", "")):
                self.herb_vocab.add(h)

    def _build_index(self) -> None:
        pass  # by_disease is built incrementally in _add_record

    # ------------------------------------------------------------------
    def find_by_diagnosis(self, diagnosis: str) -> List[Dict]:
        """Exact + fuzzy (substring) match on disease name."""
        if not diagnosis:
            return []
        key = diagnosis.strip().lower()
        idxs = self.by_disease.get(key)
        if idxs:
            return [self.records[i] for i in idxs]
        # fuzzy: diagnosis words appear in a record's disease name or vice versa
        matches = []
        for name, idxs in self.by_disease.items():
            if key in name or name in key or any(w in name for w in key.split() if len(w) > 3):
                matches.extend(self.records[i] for i in idxs)
        return matches

    def find_by_symptoms(self, symptoms: List[str], top_n: int = 5) -> List[Dict]:
        """Simple overlap scoring between given symptoms and each record's symptom list."""
        symptoms_set = {s.lower().strip() for s in symptoms if s}
        if not symptoms_set:
            return []
        scored = []
        for rec in self.records:
            rec_symptoms = {s.lower() for s in _split_list(rec.get("symptoms_raw", ""))}
            overlap = len(symptoms_set & rec_symptoms)
            if overlap:
                scored.append((overlap, rec))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [rec for _, rec in scored[:top_n]]


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

