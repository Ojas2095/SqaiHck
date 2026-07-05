# outbreak_engine.py
"""
Early-warning engine for the "dynamic detection and prediction of disease
outbreaks" capability.

Three stages, each mapping to an indicative capability in the problem
statement:

  1. Anomaly detection on historical daily case counts per
     (district, disease) â€” IsolationForest when available, z-score
     fallback otherwise (so it never silently does nothing).
  2. Geospatial clustering (DBSCAN on real lat/lon, haversine metric) of
     the districts currently showing anomalies, as a practical stand-in
     for the spatiotemporal graph neural network the problem statement
     mentions. A full STGNN needs a much denser, longer geo-tagged time
     series than a hackathon-scale demo has; DBSCAN over real coordinates
     gives an honest, working version of "is this an isolated blip or a
     regional cluster" today, and is the natural place to swap in a GNN
     later without changing the API.
  3. A short-term forecast (linear trend over the last 14 days) per
     district/disease, giving a same-week projection to support proactive
     planning.
"""
import math
from datetime import datetime
from typing import Dict, List

import numpy as np

import config
from database import get_db_connection

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.cluster import DBSCAN
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


class OutbreakEngine:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.DB_PATH

    # ------------------------------------------------------------------
    def _load_series(self) -> Dict:
        conn = get_db_connection(self.db_path)
        rows = conn.execute(
            "SELECT district, disease, date_detected, cases_reported, latitude, longitude "
            "FROM outbreak_alerts ORDER BY district, disease, date_detected"
        ).fetchall()
        conn.close()
        series = {}
        for r in rows:
            key = (r["district"], r["disease"])
            series.setdefault(key, {"points": [], "lat": r["latitude"], "lon": r["longitude"]})
            series[key]["points"].append((r["date_detected"], r["cases_reported"]))
        return series

    @staticmethod
    def _rolling_avg(values: List[float], window: int) -> List[float]:
        out = []
        for i in range(len(values)):
            chunk = values[max(0, i - window + 1): i + 1]
            out.append(sum(chunk) / len(chunk))
        return out

    @staticmethod
    def _severity(z: float) -> str:
        if z >= 2.5:
            return "HIGH"
        if z >= 1.5:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _forecast_next_7_days(cases: List[float]) -> Dict:
        """Simple linear trend over the last 14 points -> next-7-day projection.
        Deliberately simple/transparent rather than a black box, since the
        problem statement asks for explainable forecasting."""
        window = cases[-14:]
        if len(window) < 4:
            return {"trend": "insufficient_data", "projected_cases_day7": None}
        x = np.arange(len(window))
        slope, intercept = np.polyfit(x, window, 1)
        projected = max(0.0, slope * (len(window) + 6) + intercept)
        trend = "rising" if slope > 0.3 else "falling" if slope < -0.3 else "stable"
        return {
            "trend": trend,
            "daily_slope": round(float(slope), 2),
            "projected_cases_day7": round(float(projected), 1),
        }

    # ------------------------------------------------------------------
    def detect_anomalies(self, lookback_days: int = 14, top_n: int = 10) -> List[Dict]:
        series = self._load_series()
        alerts = []

        for (district, disease), data in series.items():
            points = data["points"]
            if len(points) < 10:
                continue

            dates = [p[0] for p in points]
            cases = [float(p[1]) for p in points]
            roll7 = self._rolling_avg(cases, 7)

            mean = sum(cases) / len(cases)
            std = (sum((c - mean) ** 2 for c in cases) / len(cases)) ** 0.5 or 1.0

            if _SKLEARN_AVAILABLE and len(cases) >= 15:
                X = np.array(list(zip(cases, roll7)))
                model = IsolationForest(n_estimators=100, contamination=0.1, random_state=config.RANDOM_SEED)
                preds = model.fit_predict(X)
                scores = -model.score_samples(X)
                is_anomaly = [p == -1 for p in preds]
                anomaly_scores = [float(s) for s in scores]
            else:
                anomaly_scores = [(c - mean) / std for c in cases]
                is_anomaly = [s >= 1.5 for s in anomaly_scores]

            recent = range(max(0, len(cases) - lookback_days), len(cases))
            best_idx = max((i for i in recent if is_anomaly[i]), key=lambda i: cases[i], default=None)
            if best_idx is None:
                continue

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
                "latitude": data["lat"],
                "longitude": data["lon"],
                "forecast": self._forecast_next_7_days(cases),
            })

        alerts = self._geospatial_cluster(alerts)
        severity_rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
        alerts.sort(key=lambda a: (severity_rank[a["severity"]], a["date"]), reverse=True)
        return alerts[:top_n]

    # ------------------------------------------------------------------
    def _geospatial_cluster(self, alerts: List[Dict]) -> List[Dict]:
        """DBSCAN over haversine distance between districts with active
        anomalies -> flags whether an alert is part of a wider regional
        cluster (proxy for spatiotemporal spread) or an isolated case."""
        if not alerts:
            return alerts
        coords = [a for a in alerts if a["latitude"] is not None and a["longitude"] is not None]
        if len(coords) < 2 or not _SKLEARN_AVAILABLE:
            for a in alerts:
                a["regional_cluster"] = False
                a["cluster_districts"] = []
            return alerts

        rad = np.radians([[a["latitude"], a["longitude"]] for a in coords])
        # ~150km neighbourhood radius, expressed in radians for haversine metric
        eps = 150 / 6371.0
        labels = DBSCAN(eps=eps, min_samples=2, metric="haversine").fit_predict(rad)

        for a in alerts:
            a["regional_cluster"] = False
            a["cluster_districts"] = []
        for label, a in zip(labels, coords):
            if label == -1:
                continue
            # "regional cluster" means spread to OTHER districts, not just
            # multiple diseases flagged in the same place.
            peers = [c["district"] for l, c in zip(labels, coords) if l == label and c["district"] != a["district"]]
            a["regional_cluster"] = bool(peers)
            a["cluster_districts"] = sorted(set(peers))
        return alerts


