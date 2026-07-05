# web_app.py
# ============================================================================
# AYUSH AI Platform
# Rebuilt to address Ministry of AYUSH Problem Statement 3:
#   1. Voice-based multilingual EHR creation
#   2. Early outbreak detection & short-term forecasting
#   3. Personalised, evidence-grounded AYUSH treatment recommendations
#   4. Explainable output + a feedback loop that keeps improving it
# ============================================================================
import os
import tempfile
import uuid
import asyncio
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import config
import database
from knowledge_base import KnowledgeBase
from rag_engine import RAGEngine
from nlp_engine import SpeechModel, TranslationModel, MedicalNER
from llm_engine import LLMEngine, TemplateFallbackGenerator, build_prompt
from recommender import HybridRecommender
from outbreak_engine import OutbreakEngine
from benchmark_engine import BenchmarkEngine

BASE_DIR = Path(__file__).parent

# ----------------------------------------------------------------------
# STARTUP: build the knowledge base + all engines ONCE, in the right order
# ----------------------------------------------------------------------
print("=" * 70)
print("Initialising AYUSH AI platform...")

database.init_database()
database.generate_sample_data()

kb = KnowledgeBase()
kb.load_all()
print(f"Knowledge base: {len(kb.records)} records "
      f"({len(kb.disease_vocab)} diseases, {len(kb.herb_vocab)} herbs, "
      f"{len(kb.symptom_vocab)} symptoms)")
if config.HF_TOKEN:
    bhashabench_status = kb.load_bhashabench()  # optional, evaluation only
    print(f"BhashaBench-Ayur status: {bhashabench_status}")
else:
    print("BhashaBench-Ayur: not attempted (HF_TOKEN not set)")

rag_engine = RAGEngine()
rag_engine.build(kb.chunks, kb.chunk_sources)
print(f"RAG backend: {rag_engine.backend_name} | corpus size: {rag_engine.corpus_size}")

speech_model = SpeechModel()
translation_model = TranslationModel()
ner_model = MedicalNER(kb.symptom_vocab, kb.disease_vocab, kb.herb_vocab)

# Initialize LLM with optimizations
llm_engine = LLMEngine()
print(f"LLM loaded: {llm_engine.is_available} "
      f"({'generation will use ' + config.LLM_MODEL_NAME if llm_engine.is_available else 'using retrieval-grounded template fallback'})")

recommender = HybridRecommender(kb)
outbreak_engine = OutbreakEngine()
benchmark_engine = BenchmarkEngine(kb, llm_engine)

print(f"Speech (faster-whisper) loaded: {speech_model.is_available}")
print(f"Translation neural model loaded: {translation_model.uses_neural_model}")
print("=" * 70)

# ----------------------------------------------------------------------
app = FastAPI(title="AYUSH AI - AHMIS Decision Support Platform", version="3.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# ----------------------------------------------------------------------
# request/response models
# ----------------------------------------------------------------------
class EHRInput(BaseModel):
    patient_id: Optional[str] = None
    voice_text: str
    language: str = "en"
    age: Optional[int] = None
    bmi: Optional[float] = None
    district: Optional[str] = None


class TreatmentInput(BaseModel):
    patient_id: str


class FeedbackInput(BaseModel):
    treatment_id: str
    approved: bool
    score: Optional[float] = None


class EvidenceInput(BaseModel):
    disease: str
    herb: Optional[str] = ""


class TranslationInput(BaseModel):
    text: str
    source_lang: str = "hi"
    target_lang: str = "en"


class NerInput(BaseModel):
    text: str


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _get_or_create_patient(patient_id: str, age: Optional[int], bmi: Optional[float]) -> None:
    conn = database.get_db_connection()
    exists = conn.execute("SELECT 1 FROM patient_history WHERE patient_id = ?", (patient_id,)).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO patient_history (patient_id, age, bmi, comorbidities_count, outcome, prakriti, feature_vector) "
            "VALUES (?, ?, ?, 0, 'ongoing_treatment', '', '')",
            (patient_id, age or 40, bmi or 24.0),
        )
        conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# ROUTES
# ----------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>AYUSH AI Platform</h1><p>index.html not found.</p>"


@app.get("/api/dashboard")
async def dashboard():
    conn = database.get_db_connection()
    total_patients = conn.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
    total_treatments = conn.execute("SELECT COUNT(*) FROM treatments").fetchone()[0]
    total_ehr = conn.execute("SELECT COUNT(*) FROM ehr_records").fetchone()[0]

    herb_counter = Counter()
    for row in conn.execute("SELECT herbs FROM treatments").fetchall():
        for h in (row["herbs"] or "").split(","):
            h = h.strip()
            if h:
                herb_counter[h] += 1
    conn.close()

    alerts = outbreak_engine.detect_anomalies()
    recent_alerts = [
        {"district": a["district"], "disease": a["disease"], "cases": a["cases"],
         "severity": a["severity"], "regional_cluster": a.get("regional_cluster", False),
         "forecast": a.get("forecast")}
        for a in alerts[:5]
    ]

    return {
        "total_patients": total_patients,
        "total_treatments": total_treatments,
        "total_ehr": total_ehr,
        "active_alerts": len(alerts),
        "top_herbs": herb_counter.most_common(4),
        "recent_alerts": recent_alerts,
        "knowledge_base": {
            "records": len(kb.records),
            "diseases": len(kb.disease_vocab),
            "herbs": len(kb.herb_vocab),
        },
        "rag_status": rag_engine.backend_name,
        "corpus_size": rag_engine.corpus_size,
        "models": {
            "speech_faster_whisper": speech_model.is_available,
            "translation_neural": translation_model.uses_neural_model,
            "rag_backend": rag_engine.backend_name,
            "llm_loaded": llm_engine.is_available,
        },
    }


@app.post("/api/ehr")
async def create_ehr(data: EHRInput):
    """Voice/typed multilingual EHR creation: translate -> extract entities
    (gazetteer NER, matched against the real knowledge-base vocabulary) ->
    persist a structured record."""
    patient_id = data.patient_id or f"PAT-{uuid.uuid4().hex[:6].upper()}"

    if data.language == "hi":
        translated = await run_in_threadpool(translation_model.translate, data.voice_text, "hi", "en")
    else:
        translated = data.voice_text

    entities = await run_in_threadpool(ner_model.extract, translated, data.voice_text if data.language == "hi" else None)

    symptoms = entities["symptoms"]
    prakriti = entities["prakriti"] or "not assessed"

    # 1) Direct hit: patient's own words literally named a disease/problem.
    # 2) Fallback: no disease named, but symptoms were recognised â€” look up
    #    the closest-matching KB record by symptom overlap and use its
    #    disease as the working diagnosis.
    diagnosis_source = "not determined"
    if entities["diseases"]:
        diagnosis = entities["diseases"][0]
        diagnosis_source = "disease name mentioned directly"
    elif symptoms:
        matched = kb.find_by_symptoms(symptoms, top_n=1)
        if matched:
            diagnosis = matched[0]["disease"]
            diagnosis_source = "matched from symptoms"
        else:
            diagnosis = "pending evaluation"
    else:
        diagnosis = "pending evaluation"

    record = {
        "id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "visit_date": datetime.now().strftime("%Y-%m-%d"),
        "symptoms": ", ".join(symptoms) if symptoms else "unspecified",
        "diagnosis": diagnosis,
        "prakriti": prakriti,
        "comorbidities": "None",
        "raw_text": data.voice_text,
        "translated_text": translated,
        "language": "Hindi" if data.language == "hi" else "English",
        "district": data.district or "",
        "confidence_score": round(min(1.0, 0.3 + 0.15 * (len(symptoms) + len(entities["diseases"]))), 2),
    }

    conn = database.get_db_connection()
    conn.execute(
        "INSERT INTO ehr_records (id, patient_id, visit_date, symptoms, diagnosis, prakriti, "
        "comorbidities, raw_text, translated_text, language, district, confidence_score) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        tuple(record[k] for k in [
            "id", "patient_id", "visit_date", "symptoms", "diagnosis", "prakriti",
            "comorbidities", "raw_text", "translated_text", "language", "district", "confidence_score",
        ]),
    )
    conn.commit()
    conn.close()

    _get_or_create_patient(patient_id, data.age, data.bmi)
    record["entities"] = entities
    record["diagnosis_source"] = diagnosis_source
    return record


@app.post("/api/treatment")
async def get_treatment(data: TreatmentInput):
    """Generate treatment plan with LLM timeout handling."""
    conn = database.get_db_connection()
    exists = conn.execute("SELECT COUNT(*) FROM ehr_records WHERE patient_id = ?", (data.patient_id,)).fetchone()[0]
    if exists == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Patient not found")

    patient = conn.execute("SELECT * FROM patient_history WHERE patient_id = ?", (data.patient_id,)).fetchone()
    latest_visit = conn.execute(
        "SELECT * FROM ehr_records WHERE patient_id = ? ORDER BY visit_date DESC LIMIT 1", (data.patient_id,)
    ).fetchone()
    conn.close()

    diagnosis = latest_visit["diagnosis"] if latest_visit else "General Health"
    symptoms = latest_visit["symptoms"].split(", ") if latest_visit and latest_visit["symptoms"] else []
    prakriti = latest_visit["prakriti"] if latest_visit else None
    age = float(patient["age"]) if patient else 40.0
    bmi = float(patient["bmi"]) if patient else 24.0
    comorbidities_count = float(patient["comorbidities_count"]) if patient else 0.0

    # ---- Signal 1+2+3: hybrid recommendation (Prakriti logic + patient
    # clustering on historical outcomes + RL-style herb feedback) ----
    rec = await run_in_threadpool(
        recommender.recommend, diagnosis, symptoms, prakriti, age, bmi, comorbidities_count
    )

    # ---- RAG: retrieve evidence actually used for generation ----
    query = f"{diagnosis} {' '.join(symptoms)} Ayurvedic treatment herbs diet"
    evidence = await run_in_threadpool(rag_engine.search, query, config.RAG_TOP_K)
    retrieval_score = round(sum(e["relevance_score"] for e in evidence) / len(evidence), 3) if evidence else 0.0

    patient_summary = (
        f"Patient ID: {data.patient_id}\nAge: {age}\nBMI: {bmi}\n"
        f"Symptoms: {', '.join(symptoms) or 'unspecified'}\nDiagnosis: {diagnosis}\n"
        f"Prakriti (constitution): {prakriti or 'not assessed'}\n"
        f"Comorbidities count: {int(comorbidities_count)}"
    )

    # ---- Generation with timeout and fallback ----
    llm_response = None
    used_llm = False
    
    if llm_engine.is_available:
        try:
            print(f"â³ Generating LLM response for patient {data.patient_id}...")
            # Use a timeout to prevent hanging
            llm_response = await asyncio.wait_for(
                run_in_threadpool(llm_engine.generate, patient_summary, evidence),
                timeout=20.0  # 20 second timeout
            )
            used_llm = llm_response is not None and len(llm_response) > 10
            if used_llm:
                print(f"âœ… LLM generation completed ({len(llm_response)} chars)")
            else:
                print("âš ï¸ LLM returned empty response, using fallback")
        except asyncio.TimeoutError:
            print("â° LLM generation timed out after 20 seconds, using fallback")
            llm_response = None
        except Exception as e:
            print(f"âŒ LLM generation error: {type(e).__name__}: {e}")
            llm_response = None
    
    # Fallback to template if LLM failed or not available
    if not used_llm:
        print("ðŸ“ Using template fallback generator")
        llm_response = TemplateFallbackGenerator.generate(patient_summary, evidence, rec["matched_records"])
        used_llm = False

    unmapped = rec.get("no_verified_ayurvedic_mapping", False)
    # Never backfill a generic herb list for a condition we've explicitly
    # flagged as having no verified Ayurvedic mapping (see
    # knowledge_base._load_not_there / recommender.recommend) -- that would
    # look like a real, evidence-based recommendation when it isn't.
    herbs = rec["herbs"] or ([] if unmapped else ["Ashwagandha", "Triphala", "Guduchi"])
    if unmapped:
        diet = "No verified Ayurvedic dietary guidance for this condition yet"
        yoga = "No verified Ayurvedic yoga/therapy guidance for this condition yet"
    else:
        diet = " | ".join(rec["diet"]) if rec["diet"] else "General dosha-appropriate diet (see evidence)"
        yoga = " | ".join(rec["yoga"]) if rec["yoga"] else "Daily Pranayama"
    contraindications = " | ".join(rec["contraindications"]) if rec["contraindications"] else ""

    treatment_id = str(uuid.uuid4())
    recommendation = {
        "treatment_id": treatment_id,
        "patient_id": data.patient_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "diagnosis": diagnosis,
        "herbs": ", ".join(herbs),
        "diet": diet,
        "yoga": yoga,
        "lifestyle": contraindications or "Maintain regular routine; adequate sleep; seasonal adjustment",
        "confidence_score": rec["confidence_score"],
        "cluster_outcome_rate": rec["cluster_outcome_rate"],
        "retrieval_score": retrieval_score,
        "generation_method": "llm" if used_llm else "retrieval_template",
        "source": "AI-Generated (Hybrid Recommender + RAG" + (" + LLM)" if used_llm else ")"),
        "evidence": evidence,
        "llm_response": llm_response,
        "prakriti": prakriti or "not assessed",
        "symptoms": symptoms,
        "no_verified_ayurvedic_mapping": unmapped,
        "ayurvedic_equivalent": rec.get("ayurvedic_equivalent"),
        "gap_note": rec.get("gap_note"),
    }

    conn = database.get_db_connection()
    conn.execute(
        "INSERT INTO treatments (id, patient_id, date, diagnosis, herbs, diet, yoga, lifestyle, "
        "confidence_score, feedback_score, approved, ml_score, retrieval_score, llm_response, evidence_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (treatment_id, data.patient_id, recommendation["date"], diagnosis, recommendation["herbs"],
         diet, yoga, recommendation["lifestyle"], recommendation["confidence_score"], None,
         1 if recommendation["confidence_score"] >= 0.6 else 0, rec["cluster_outcome_rate"],
         retrieval_score, llm_response, str([e["source"] for e in evidence])),
    )
    conn.commit()
    conn.close()

    return recommendation


@app.post("/api/evidence")
async def search_evidence(data: EvidenceInput):
    query = f"{data.herb} {data.disease} Ayurveda treatment".strip()
    return await run_in_threadpool(rag_engine.search, query, config.RAG_TOP_K)


@app.post("/api/feedback")
async def submit_feedback(data: FeedbackInput):
    conn = database.get_db_connection()
    row = conn.execute("SELECT diagnosis, herbs FROM treatments WHERE id = ?", (data.treatment_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Treatment not found")

    conn.execute(
        "UPDATE treatments SET approved = ?, feedback_score = ? WHERE id = ?",
        (1 if data.approved else 0, data.score, data.treatment_id),
    )
    conn.commit()
    conn.close()

    # RL-style update: reinforce/penalise the herbs from this treatment for
    # this diagnosis, so future recommendations shift with clinician feedback.
    herbs = [h.strip() for h in (row["herbs"] or "").split(",") if h.strip()]
    if herbs:
        await run_in_threadpool(recommender.record_feedback, row["diagnosis"], herbs, data.approved)

    return {"status": "success"}


@app.get("/api/feedback/lookup/{patient_id}")
async def lookup_feedback(patient_id: str):
    conn = database.get_db_connection()
    row = conn.execute(
        "SELECT id, date, herbs, approved FROM treatments WHERE patient_id = ? ORDER BY date DESC LIMIT 1",
        (patient_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="No treatments found")
    return {"id": row["id"], "date": row["date"], "herbs": row["herbs"], "approved": row["approved"]}


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(None), language: str = Form("en")):
    if not audio:
        return JSONResponse({"error": "No audio file"}, status_code=400)
    audio_bytes = await audio.read()
    if len(audio_bytes) < 100:
        return JSONResponse({"error": "Audio too short"}, status_code=400)

    if not speech_model.is_available:
        return JSONResponse(
            {"error": "Speech model not loaded on this server (faster-whisper not installed/no model weights). "
                       "Type the note instead, or install faster-whisper and restart."},
            status_code=503,
        )

    original_name = audio.filename or ""
    suffix = os.path.splitext(original_name)[1].lower()
    if suffix not in (".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac"):
        suffix = ".webm" if (audio.content_type or "").endswith("webm") else ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        result = await run_in_threadpool(speech_model.transcribe, tmp_path, None if language == "auto" else language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not result.get("text"):
        return JSONResponse({"error": result.get("error", "transcription failed")}, status_code=500)
    return {"text": result["text"], "language": result.get("language", language), "success": True, "engine": "faster-whisper"}


@app.post("/api/translation/translate")
async def translate_text(data: TranslationInput):
    translated = await run_in_threadpool(translation_model.translate, data.text, data.source_lang, data.target_lang)
    return {"original": data.text, "translated": translated,
            "engine": "neural" if translation_model.uses_neural_model else "gazetteer", "success": True}


@app.post("/api/ner/extract")
async def extract_entities_endpoint(data: NerInput):
    entities = await run_in_threadpool(ner_model.extract, data.text)
    return {"entities": entities, "success": True}


@app.post("/api/rag/search")
async def rag_search_endpoint(data: EvidenceInput):
    query = f"{data.herb} {data.disease} Ayurveda treatment".strip()
    results = await run_in_threadpool(rag_engine.search, query, config.RAG_TOP_K)
    return {"results": results, "success": True}


@app.get("/api/outbreak/detect")
async def detect_outbreaks():
    alerts = await run_in_threadpool(outbreak_engine.detect_anomalies)
    return {"alerts": alerts, "success": True}


@app.get("/api/benchmark")
async def run_benchmark(language: str = "English", max_questions: int = 20,
                         question_level: Optional[str] = None):
    """Self-test: scores the currently-loaded LLM against BhashaBench-Ayur
    MCQs. Evaluation only -- has no effect on /api/treatment or any other
    endpoint. Requires kb.load_bhashabench() to have succeeded at startup
    (see the 'BhashaBench-Ayur status' line in the server log); if it
    didn't, this returns a clear error instead of an empty/misleading result.
    `max_questions` is capped at 200 per call since each question is a real
    LLM generation and this runs on CPU by default."""
    max_questions = max(1, min(max_questions, 200))
    result = await run_in_threadpool(
        benchmark_engine.run, language, max_questions, question_level
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@app.get("/api/models/status")
async def model_status():
    return {
        "speech": {"model": "faster-whisper", "loaded": speech_model.is_available},
        "translation": {"model": config.TRANSLATION_MODEL_NAME, "neural_loaded": translation_model.uses_neural_model,
                         "gazetteer_fallback": True},
        "ner": {"model": "gazetteer (mined from knowledge base)",
                "vocab_size": len(kb.symptom_vocab) + len(kb.disease_vocab) + len(kb.herb_vocab)},
        "rag": {"backend": rag_engine.backend_name, "corpus_size": rag_engine.corpus_size},
        "llm": {"model": config.LLM_MODEL_NAME, "loaded": llm_engine.is_available,
                "fallback": "retrieval-grounded template" if not llm_engine.is_available else None},
        "recommender": {"type": "Prakriti rules + KMeans patient clustering + RL feedback (Beta-Bernoulli)"},
        "outbreak_engine": {"type": "IsolationForest/z-score anomaly + DBSCAN geospatial clustering + linear forecast"},
        "benchmark": {"bhashabench_en_loaded": not kb.bhashabench_en.empty,
                      "bhashabench_hi_loaded": not kb.bhashabench_hi.empty},
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"\nðŸš€ Starting server on http://localhost:{port}")
    print(f"ðŸ“Š LLM status: {'LOADED' if llm_engine.is_available else 'FALLBACK (template)'}")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=port)


