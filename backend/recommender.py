# recommender.py
"""
Hybrid recommendation engine, matching the problem statement's ask for
"hybrid recommendation engines that integrate codified AYUSH knowledge
systems (Prakriti-based logic) with patient clustering on historical
AHIMS outcomes, with reinforcement learning continuously refining
recommendations based on clinician feedback."

Three signals are combined into one confidence score:

  1. Knowledge-base match: records retrieved for this diagnosis/symptoms
     from the unified corpus (Prakriti-aware â€” dosha field is used to
     prefer records matching the patient's constitution).
  2. Patient-cluster outcome rate: KMeans clusters `patient_history` by
     (age, bmi, comorbidities_count); the fraction of "improved"/
     "remission" outcomes in the patient's cluster is used as a
     population-level prior â€” this is the "historical AHIMS outcomes"
     signal, and also the fallback used for cases with limited/no
     individual history.
  3. RL-style feedback: `herb_feedback_stats` tracks (successes, trials)
     per (diagnosis, herb) pair, updated every time a clinician approves
     or rejects a recommendation via /api/feedback. This is a simple
     Beta-Bernoulli bandit (Thompson-sampling-flavoured mean estimate) â€”
     lightweight, but a real online-learning loop rather than a static
     lookup table, and it's the part that makes recommendations "continue
     to improve" as the problem statement asks for.
"""
import sqlite3
from typing import Dict, List, Optional

import numpy as np

import config
from database import get_db_connection
from knowledge_base import KnowledgeBase

try:
    from sklearn.cluster import KMeans
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


class HybridRecommender:
    def __init__(self, kb: KnowledgeBase, db_path: Optional[str] = None):
        self.kb = kb
        self.db_path = db_path or config.DB_PATH
        self._kmeans = None
        self._cluster_outcome_rate: Dict[int, float] = {}
        self._cluster_ready = False

    # ------------------------------------------------------------------
    # Signal 1: knowledge-base retrieval, Prakriti-aware
    # ------------------------------------------------------------------
    def _candidate_records(self, diagnosis: str, symptoms: List[str], prakriti: Optional[str]) -> List[Dict]:
        candidates = self.kb.find_by_diagnosis(diagnosis)
        if not candidates:
            candidates = self.kb.find_by_symptoms(symptoms, top_n=8)
        if not candidates:
            return []
        if prakriti:
            prakriti_key = prakriti.lower().split("-")[0].split(" ")[0]
            matching = [r for r in candidates if prakriti_key in (r.get("dosha") or "").lower()]
            if matching:
                return matching
        return candidates

    # ------------------------------------------------------------------
    # Signal 2: patient clustering on historical outcomes
    # ------------------------------------------------------------------
    def _fit_clusters(self, n_clusters: int = 5) -> None:
        conn = get_db_connection(self.db_path)
        rows = conn.execute(
            "SELECT age, bmi, comorbidities_count, outcome FROM patient_history"
        ).fetchall()
        conn.close()
        if len(rows) < n_clusters * 2 or not _SKLEARN_AVAILABLE:
            self._cluster_ready = False
            return

        X = np.array([[r["age"], r["bmi"], r["comorbidities_count"]] for r in rows], dtype=float)
        good = {"improved", "remission"}
        y = np.array([1 if r["outcome"] in good else 0 for r in rows])

        self._kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=config.RANDOM_SEED)
        labels = self._kmeans.fit_predict(X)

        for c in range(n_clusters):
            mask = labels == c
            if mask.sum() > 0:
                self._cluster_outcome_rate[c] = float(y[mask].mean())
        self._cluster_ready = True

    def _cluster_outcome_for(self, age: float, bmi: float, comorbidities_count: float) -> float:
        if not self._cluster_ready:
            self._fit_clusters()
        if not self._cluster_ready or self._kmeans is None:
            return 0.5  # neutral prior when there isn't enough history yet
        cluster = int(self._kmeans.predict([[age, bmi, comorbidities_count]])[0])
        return self._cluster_outcome_rate.get(cluster, 0.5)

    # ------------------------------------------------------------------
    # Signal 3: RL-style feedback (Beta-Bernoulli bandit per diagnosis/herb)
    # ------------------------------------------------------------------
    def _herb_reward(self, diagnosis: str, herb: str, conn: sqlite3.Connection) -> float:
        row = conn.execute(
            "SELECT successes, trials FROM herb_feedback_stats WHERE diagnosis = ? AND herb = ?",
            (diagnosis, herb),
        ).fetchone()
        if row is None:
            return 0.5  # uninformative prior (1/2 successes/trials, i.e. Beta(1,1))
        return row["successes"] / row["trials"]

    def record_feedback(self, diagnosis: str, herbs: List[str], approved: bool, outcome_positive: Optional[bool] = None) -> None:
        """Called from /api/feedback. `approved` = clinician approved the
        plan as given; `outcome_positive`, if later known, additionally
        reinforces/penalises based on real patient outcome."""
        reward = 1.0 if approved else 0.0
        if outcome_positive is not None:
            reward = (reward + (1.0 if outcome_positive else 0.0)) / 2.0

        conn = get_db_connection(self.db_path)
        for herb in herbs:
            conn.execute(
                "INSERT INTO herb_feedback_stats (diagnosis, herb, successes, trials) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(diagnosis, herb) DO UPDATE SET "
                "successes = successes + excluded.successes - 1, "
                "trials = trials + 1",
                (diagnosis, herb, 1.0 + reward, 2.0),
            )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    def recommend(self, diagnosis: str, symptoms: List[str], prakriti: Optional[str],
                  age: float = 40, bmi: float = 24, comorbidities_count: int = 0) -> Dict:
        records = self._candidate_records(diagnosis, symptoms, prakriti)

        # Gap-analysis entries (knowledge_base._load_not_there) are flagged
        # is_stub=True: we recognise the disease name but have no verified
        # herbs/diet/remedies for it. If every candidate is a stub, don't
        # fall through into the normal scoring path below -- that would
        # either return nothing useful or (worse, upstream in web_app.py)
        # get silently backfilled with a generic herb list that has nothing
        # to do with this specific condition. Say plainly that it's unmapped.
        verified_records = [r for r in records if not r.get("is_stub")]
        stub_records = [r for r in records if r.get("is_stub")]
        if not verified_records and stub_records:
            stub = stub_records[0]
            return {
                "diagnosis": diagnosis,
                "herbs": [],
                "diet": [],
                "yoga": [],
                "contraindications": [],
                "matched_records": stub_records[:5],
                "cluster_outcome_rate": None,
                "retrieval_strength": 0.0,
                "confidence_score": 0.0,
                "no_verified_ayurvedic_mapping": True,
                "ayurvedic_equivalent": stub.get("ayurvedic_equivalent") or None,
                "gap_note": stub.get("gap_description")
                or "This condition is not yet mapped to a classical Ayurvedic "
                   "formulation in the current knowledge base -- flag for "
                   "clinician review rather than auto-recommending.",
            }
        records = verified_records

        herb_pool = {}
        for rec in records:
            for h in (rec.get("herbs_raw") or "").split(","):
                h = h.strip()
                if h:
                    herb_pool[h] = herb_pool.get(h, rec.get("confidence", 0.6))

        conn = get_db_connection(self.db_path)
        ranked_herbs = sorted(
            herb_pool.keys(),
            key=lambda h: (self._herb_reward(diagnosis, h, conn), herb_pool[h]),
            reverse=True,
        )
        conn.close()
        top_herbs = ranked_herbs[:4] if ranked_herbs else []

        diets = list({rec["diet"] for rec in records if rec.get("diet")})[:3]
        yogas = list({rec["yoga"] for rec in records if rec.get("yoga")})[:3]
        contraindications = list({rec["contraindications"] for rec in records if rec.get("contraindications")})[:3]

        cluster_rate = self._cluster_outcome_for(age, bmi, comorbidities_count)
        retrieval_strength = min(1.0, len(records) / 5.0) if records else 0.0
        confidence = round(0.5 * retrieval_strength + 0.5 * cluster_rate, 3)

        return {
            "diagnosis": diagnosis,
            "herbs": top_herbs,
            "diet": diets,
            "yoga": yogas,
            "contraindications": contraindications,
            "matched_records": records[:5],
            "cluster_outcome_rate": round(cluster_rate, 3),
            "retrieval_strength": round(retrieval_strength, 3),
            "confidence_score": confidence,
            "no_verified_ayurvedic_mapping": False,
        }
