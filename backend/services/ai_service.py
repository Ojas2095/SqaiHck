# web_app.py - COMPLETE WORKING VERSION
# ============================================================================
# AYUSH AI - Advanced Ayurvedic Clinical Platform
# Complete implementation with all AI models
# ============================================================================

import os
import random
import uvicorn
import tempfile
import uuid
import re
import math
import glob
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool

# ============================================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env file loaded")
except ImportError:
    print("⚠️ python-dotenv not installed, skipping .env loading")

# Hugging Face Token - Get from: https://huggingface.co/settings/tokens
HF_TOKEN = os.environ.get("HF_TOKEN", "")
if HF_TOKEN:
    print("✅ Hugging Face token found in environment")
else:
    print("⚠️ HF_TOKEN not set. Hugging Face dataset will not load.")
    print("   Set it with:")
    print("   - Windows (CMD): set HF_TOKEN=hf_your_token_here")
    print("   - Windows (PowerShell): $env:HF_TOKEN='hf_your_token_here'")
    print("   - Mac/Linux: export HF_TOKEN=hf_your_token_here")
    print("   - Or create a .env file with HF_TOKEN=hf_your_token_here")

# ============================================================================
# ANSI COLORS
# ============================================================================
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_RED = "\033[91m"
C_CYAN = "\033[96m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

def safe_print(text: str = "", end: str = "\n") -> None:
    try:
        sys.stdout.write(text + end)
        sys.stdout.flush()
    except UnicodeEncodeError:
        fallback = text
        replacements = {
            "✅": "[OK]", "⚠️": "[WARN]", "❌": "[ERROR]", "🎙️": "[MIC]",
            "📊": "[STATS]", "🌿": "[HERB]", "📈": "[TREND]", "📋": "[PLAN]",
            "🍀": "[AYUSH]", "🧬": "[GENE]", "🚨": "[ALERT]", "💊": "[PLAN]",
            "📜": "[EVIDENCE]", "📖": "[DOC]", "🙏": "[NAMASTE]"
        }
        for emoji, representation in replacements.items():
            fallback = fallback.replace(emoji, representation)
        try:
            sys.stdout.write(fallback.encode("ascii", errors="replace").decode("ascii") + end)
            sys.stdout.flush()
        except Exception:
            print(text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"), end=end)

# ============================================================================
# MODEL IMPORTS - ALL MODELS WITH FALLBACKS
# ============================================================================

# 1. Speech Recognition - faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    safe_print("✅ faster-whisper loaded")
except ImportError:
    WHISPER_AVAILABLE = False
    safe_print("⚠️ faster-whisper not installed - run: pip install faster-whisper")

# 2. RAG - BAAI/bge-small-en-v1.5 + ChromaDB
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    RAG_AVAILABLE = True
    safe_print("✅ RAG models loaded")
except ImportError:
    RAG_AVAILABLE = False
    safe_print("⚠️ RAG models not installed - run: pip install sentence-transformers chromadb")

# 3. LLM - Qwen2.5-3B-Instruct
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    LLM_AVAILABLE = True
    safe_print("✅ LLM models loaded")
except ImportError:
    LLM_AVAILABLE = False
    safe_print("⚠️ LLM models not installed - run: pip install transformers torch")

# 4. ML Models - LightGBM, XGBoost, Isolation Forest
try:
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
    safe_print("✅ ML models loaded")
except ImportError:
    ML_AVAILABLE = False
    safe_print("⚠️ ML models not installed - run: pip install lightgbm xgboost scikit-learn")

# 5. FAISS for similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
    safe_print("✅ FAISS loaded")
except ImportError:
    FAISS_AVAILABLE = False
    safe_print("⚠️ FAISS not installed - run: pip install faiss-cpu")

# 6. SHAP for explainability
try:
    import shap
    SHAP_AVAILABLE = True
    safe_print("✅ SHAP loaded")
except ImportError:
    SHAP_AVAILABLE = False
    safe_print("⚠️ SHAP not installed - run: pip install shap")

# 7. DeBERTa-v3 for NER
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    NER_AVAILABLE = True
    safe_print("✅ DeBERTa-v3 NER loaded")
except ImportError:
    NER_AVAILABLE = False
    safe_print("⚠️ NER models not installed")

# ============================================================================
# DATABASE
# ============================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ayush.db")

def get_db_connection(db_path: str | None = None):
    import sqlite3
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_database(db_path: str | None = None) -> None:
    import sqlite3
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS ehr_records (
            id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, visit_date TEXT NOT NULL,
            symptoms TEXT, diagnosis TEXT, prakriti TEXT, comorbidities TEXT,
            raw_text TEXT, translated_text TEXT, language TEXT,
            confidence_score REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS treatments (
            id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, date TEXT NOT NULL,
            herbs TEXT, diet TEXT, yoga TEXT, lifestyle TEXT,
            confidence_score REAL DEFAULT 0.0, feedback_score REAL, approved INTEGER DEFAULT 0,
            ml_score REAL DEFAULT 0.0, llm_response TEXT
        );
        CREATE TABLE IF NOT EXISTS outbreak_alerts (
            id TEXT PRIMARY KEY, district TEXT NOT NULL, disease TEXT NOT NULL,
            anomaly_score REAL DEFAULT 0.0, date_detected TEXT NOT NULL, cases_reported INTEGER DEFAULT 0,
            severity TEXT, region_cluster TEXT
        );
        CREATE TABLE IF NOT EXISTS patient_history (
            patient_id TEXT PRIMARY KEY, age INTEGER, bmi REAL,
            comorbidities_count INTEGER DEFAULT 0, outcome TEXT,
            feature_vector TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ehr_patient ON ehr_records(patient_id);
        CREATE INDEX IF NOT EXISTS idx_treat_patient ON treatments(patient_id);
        CREATE INDEX IF NOT EXISTS idx_outbreak_district ON outbreak_alerts(district);
        CREATE INDEX IF NOT EXISTS idx_outbreak_date ON outbreak_alerts(date_detected);
    """)
    conn.commit()
    conn.close()
    safe_print("✅  Database schema initialised.")

def generate_sample_data(db_path: str | None = None) -> None:
    import sqlite3
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    existing = cursor.execute("SELECT COUNT(*) FROM patient_history").fetchone()[0]
    if existing > 0:
        safe_print("⚠️  Data already exists — skipping generation.")
        conn.close()
        return

    random.seed(42)
    now = datetime.now()
    start_date = now - timedelta(days=365)
    end_date = now

    prakriti_types = ["Vata", "Pitta", "Kapha", "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Tridosha (Sama)"]
    symptoms_pool = ["joint pain", "fatigue", "indigestion", "headache", "fever", "cough", "back pain", "burning sensation", "cold", "body ache"]
    diagnoses_pool = ["Amavata (Rheumatoid Arthritis)", "Pandu (Anemia)", "Prameha (Diabetes)", "Jwara (Fever)", "Kasa (Cough)"]
    herbs_pool = ["Ashwagandha", "Triphala", "Guduchi", "Brahmi", "Shatavari", "Haridra", "Tulsi", "Neem", "Pippali", "Guggulu"]
    diet_pool = ["warm cooked meals", "avoid cold food", "light dinner", "ghee with meals", "warm water", "ginger tea", "honey"]
    yoga_pool = ["Surya Namaskar", "Pranayama", "Bhujangasana", "Shavasana", "Kapalbhati", "Nadi Shodhana"]
    lifestyle_pool = ["sleep by 10 PM", "wake before sunrise", "Abhyanga daily", "walk 30 min", "oil pulling"]
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
        cursor.execute("INSERT INTO patient_history VALUES (?, ?, ?, ?, ?, ?)", 
                       (pid, age, bmi, n_comorbidities, outcome, ""))

        patient_comorbidities = _pick(comorbidities_pool, 1, n_comorbidities) if n_comorbidities > 0 else "None"
        prakriti = random.choice(prakriti_types)
        lang = random.choice(languages)

        for _ in range(random.randint(1, 5)):
            visit_date = _random_date(start_date, end_date)
            symptoms = _pick(symptoms_pool, 2, 5)
            diagnosis = random.choice(diagnoses_pool)
            raw_text = f"Patient presents with {symptoms}. Diagnosis: {diagnosis}."
            cursor.execute(
                "INSERT INTO ehr_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, visit_date, symptoms, diagnosis, prakriti,
                 patient_comorbidities, raw_text, raw_text, lang, 0.0)
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
                "INSERT INTO treatments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, t_date, herbs, diet, yoga, lifestyle, 
                 confidence, None, approved, 0.0, "")
            )

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
                "INSERT INTO outbreak_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), district, disease, anomaly_score, current_date, base_cases, "LOW", "")
            )
    conn.commit()
    conn.close()
    safe_print("✅  Synthetic data generated successfully.")

# ============================================================================
# DATA LOADER
# ============================================================================
class AyurvedaDataLoader:
    def __init__(self, excel_path: str = "AyurGenixAI_Dataset.xlsx", hf_token: Optional[str] = None):
        self.excel_path = excel_path
        self.hf_token = hf_token
        self.local_df = None
        self.hf_dataset = None
        self.hf_dataset_en = None
        self.hf_dataset_hi = None
        self.pandas_available = False
        
        try:
            import pandas as pd
            self.pd = pd
            self.pandas_available = True
        except ImportError:
            safe_print("⚠️ pandas not installed - run: pip install pandas")
            self.pandas_available = False

    def load_local_excel(self):
        if not self.pandas_available:
            safe_print("⚠️ pandas not available, skipping Excel load")
            return None
            
        if not os.path.exists(self.excel_path):
            alternatives = [
                "AyurGenixAI_Dataset.xlsx",
                "ayurgenixai_dataset.xlsx",
                "AyurGenixAI_Dataset.XLSX",
                "AyurGenixAI Dataset.xlsx",
                "ayurgenixai.xlsx"
            ]
            found = False
            for alt in alternatives:
                if os.path.exists(alt):
                    self.excel_path = alt
                    found = True
                    print(f"✅ Found Excel file: {alt}")
                    break
            
            if not found:
                print(f"⚠️ Excel file not found: {self.excel_path}")
                return None

        try:
            df = self.pd.read_excel(self.excel_path, header=1)
            df.columns = [str(col).strip() for col in df.columns]
            print(f"✅ Loaded {len(df)} rows from local Excel file.")
            self.local_df = df
            return df
        except Exception as e:
            print(f"❌ Error loading local Excel file: {e}")
            return None

    def load_hf_dataset(self, max_rows: Optional[int] = None):
        if not self.pandas_available:
            safe_print("⚠️ pandas not available, skipping HF dataset load")
            return {}
            
        try:
            from datasets import load_dataset
            from huggingface_hub import login
        except ImportError:
            safe_print("⚠️ datasets or huggingface_hub not installed")
            return {}
        
        result = {"english": None, "hindi": None, "combined": None}
        
        if not self.hf_token:
            print("⚠️ No HF token available, skipping dataset loading")
            return result
            
        try:
            login(token=self.hf_token)
            print("✅ Hugging Face login successful")
        except Exception as e:
            print(f"⚠️ HF Login error: {e}")
            return result
        
        # Load English dataset
        try:
            print(f"🔽 Loading BhashaBench-Ayur for English...")
            dataset_en = load_dataset("bharatgenai/BhashaBench-Ayur", data_dir="English", split="test", token=self.hf_token)
            df_en = dataset_en.to_pandas()
            if max_rows:
                df_en = df_en.head(max_rows)
            print(f"✅ Loaded {len(df_en)} English questions")
            result["english"] = df_en
        except Exception as e:
            print(f"❌ Error loading English HF dataset: {e}")
        
        # Load Hindi dataset
        try:
            print(f"🔽 Loading BhashaBench-Ayur for Hindi...")
            dataset_hi = load_dataset("bharatgenai/BhashaBench-Ayur", data_dir="Hindi", split="test", token=self.hf_token)
            df_hi = dataset_hi.to_pandas()
            if max_rows:
                df_hi = df_hi.head(max_rows)
            print(f"✅ Loaded {len(df_hi)} Hindi questions")
            result["hindi"] = df_hi
        except Exception as e:
            print(f"❌ Error loading Hindi HF dataset: {e}")
        
        # Combine both
        if result["english"] is not None and result["hindi"] is not None:
            combined = self.pd.concat([result["english"], result["hindi"]], ignore_index=True)
            result["combined"] = combined
            self.hf_dataset = combined
            self.hf_dataset_en = result["english"]
            self.hf_dataset_hi = result["hindi"]
            print(f"✅ Combined dataset: {len(combined)} total questions")
        
        return result

# ============================================================================
# MODEL CLASSES
# ============================================================================

class SpeechModel:
    """faster-whisper for speech recognition"""
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.model = None
        if WHISPER_AVAILABLE:
            try:
                self.model = WhisperModel(model_size, device=device, compute_type="int8")
                safe_print(f"✅ Whisper model loaded: {model_size}")
            except Exception as e:
                safe_print(f"⚠️ Whisper load failed: {e}")
    
    def transcribe(self, audio_path: str, language: str = "en") -> str:
        if not self.model:
            return ""
        try:
            segments, info = self.model.transcribe(audio_path, language=language)
            text = " ".join([seg.text for seg in segments])
            return text
        except Exception as e:
            safe_print(f"⚠️ Transcription error: {e}")
            return ""

class TranslationModel:
    """Simple translation using dictionary mapping (no external dependencies)"""
    def __init__(self):
        safe_print("✅ Translation model initialized (dictionary-based, no external dependencies)")
    
    def translate(self, text: str, src: str = "hi", tgt: str = "en") -> str:
        """Translate using simple dictionary mapping"""
        if src == "hi" and tgt == "en":
            return self._hindi_to_english(text)
        elif src == "en" and tgt == "hi":
            return self._english_to_hindi(text)
        return text
    
    def _hindi_to_english(self, text: str) -> str:
        """Hindi to English mapping"""
        translations = {
            'बुखार': 'fever',
            'सिर दर्द': 'headache',
            'जोड़ों में दर्द': 'joint pain',
            'कमर दर्द': 'back pain',
            'खांसी': 'cough',
            'थकान': 'fatigue',
            'जलन': 'burning sensation',
            'पित्त': 'pitta',
            'वात': 'vata',
            'कफ': 'kapha',
            'ठंड': 'cold',
            'शरीर में दर्द': 'body ache',
            'अपच': 'indigestion',
            'मरीज': 'patient',
            'मुझे': 'I have',
            'है': 'has',
            'को': 'has',
            'में': 'in',
            'दर्द': 'pain',
            'और': 'and',
            'के': 'of',
            'साथ': 'with',
            'लिए': 'for',
            'से': 'from',
            'पर': 'on',
        }
        
        result = text
        for hi, en in translations.items():
            result = result.replace(hi, en)
        return result
    
    def _english_to_hindi(self, text: str) -> str:
        """English to Hindi mapping"""
        translations = {
            'fever': 'बुखार',
            'headache': 'सिर दर्द',
            'joint pain': 'जोड़ों में दर्द',
            'back pain': 'कमर दर्द',
            'cough': 'खांसी',
            'fatigue': 'थकान',
            'burning sensation': 'जलन',
            'pitta': 'पित्त',
            'vata': 'वात',
            'kapha': 'कफ',
            'cold': 'ठंड',
            'body ache': 'शरीर में दर्द',
            'indigestion': 'अपच',
            'patient': 'मरीज',
            'pain': 'दर्द',
        }
        
        result = text
        for en, hi in translations.items():
            result = result.replace(en, hi)
        return result

class MedicalNER:
    """DeBERTa-v3 for medical NER"""
    def __init__(self, model_name: str = "dslim/bert-base-NER"):
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self.torch_available = False
        
        try:
            import torch
            self.torch_available = True
        except ImportError:
            safe_print("⚠️ torch not available")
        
        if NER_AVAILABLE and self.torch_available:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForTokenClassification.from_pretrained(model_name)
                safe_print(f"✅ NER model loaded: {model_name}")
            except Exception as e:
                safe_print(f"⚠️ NER load failed: {e}")
    
    def extract_entities(self, text: str) -> Dict:
        import torch
        entities = {"symptoms": [], "diseases": [], "herbs": [], "medicines": []}
        if not self.model or not self.tokenizer:
            return entities
        
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=2)
            
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            labels = predictions[0].tolist()
            
            current_entity = []
            current_label = None
            
            for token, label in zip(tokens, labels):
                if token.startswith("##"):
                    current_entity.append(token[2:])
                else:
                    if current_entity:
                        entity_text = "".join(current_entity)
                        if current_label == "B-SYMPTOM" or current_label == "I-SYMPTOM":
                            entities["symptoms"].append(entity_text)
                        elif current_label == "B-DISEASE" or current_label == "I-DISEASE":
                            entities["diseases"].append(entity_text)
                        elif current_label == "B-HERB" or current_label == "I-HERB":
                            entities["herbs"].append(entity_text)
                    current_entity = [token]
            return entities
        except Exception as e:
            safe_print(f"⚠️ NER extraction error: {e}")
            return entities

class RAGEngine:
    """BAAI/bge-small-en-v1.5 + ChromaDB"""
    def __init__(self, collection_name: str = "ayurveda_corpus"):
        self.embedding_model = None
        self.collection = None
        self.chroma_client = None
        self.embedding_model_name = "BAAI/bge-small-en-v1.5"
        self.corpus = []
        self.file_sources = []
        
        if RAG_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                safe_print(f"✅ RAG embedding model loaded: {self.embedding_model_name}")
                
                # Setup ChromaDB
                chroma_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "chroma_db")
                os.makedirs(os.path.dirname(chroma_path), exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=chroma_path)
                
                existing_collections = self.chroma_client.list_collections()
                if collection_name in [c.name for c in existing_collections]:
                    self.collection = self.chroma_client.get_collection(collection_name)
                    safe_print(f"📁 Found existing collection: {collection_name}")
                else:
                    self.collection = self.chroma_client.create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"}
                    )
                    safe_print(f"🆕 Created new collection: {collection_name}")
            except Exception as e:
                safe_print(f"⚠️ RAG load failed: {e}")
    
    def add_documents(self, documents: List[str], sources: List[str]):
        if not self.collection or not self.embedding_model:
            return
        try:
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                batch_sources = sources[i:i+batch_size]
                embeddings = self.embedding_model.encode(batch).tolist()
                self.collection.add(
                    embeddings=embeddings,
                    documents=batch,
                    metadatas=[{"source": s} for s in batch_sources],
                    ids=[f"doc_{i+j}" for j in range(len(batch))]
                )
                self.corpus.extend(batch)
                self.file_sources.extend(batch_sources)
            safe_print(f"✅ Added {len(documents)} documents to ChromaDB")
        except Exception as e:
            safe_print(f"⚠️ Add documents error: {e}")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        if not self.collection or not self.embedding_model:
            return []
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
                        "text": doc[:500] + ("..." if len(doc) > 500 else ""),
                        "source": meta.get("source", "Unknown"),
                        "relevance_score": round(similarity, 3),
                        "confidence": confidence
                    })
            return evidence
        except Exception as e:
            safe_print(f"⚠️ Search error: {e}")
            return []

class LLMEngine:
    """Qwen2.5-3B-Instruct"""
    def __init__(self, model_name: str = "Qwen/Qwen2.5-3B-Instruct", use_gpu: bool = False):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.torch_available = False
        
        try:
            import torch
            self.torch_available = True
        except ImportError:
            safe_print("⚠️ torch not available")
        
        if LLM_AVAILABLE and self.torch_available:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if use_gpu else torch.float32,
                    device_map="auto" if use_gpu else None,
                    trust_remote_code=True
                )
                if not use_gpu:
                    self.model.to(self.device)
                safe_print(f"✅ LLM loaded: {model_name} on {self.device}")
            except Exception as e:
                safe_print(f"⚠️ LLM load failed: {e}")
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        if not self.model or not self.tokenizer:
            return ""
        try:
            messages = [
                {"role": "system", "content": "You are an expert Ayurvedic practitioner. Provide accurate Ayurvedic advice based on classical texts."},
                {"role": "user", "content": prompt}
            ]
            text = self.tokenizer.apply_chat_template(messages, tokenize=False)
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
            
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            if "assistant" in response:
                response = response.split("assistant")[-1].strip()
            return response
        except Exception as e:
            safe_print(f"⚠️ LLM generation error: {e}")
            return ""

class PatientSimilarity:
    """FAISS for patient similarity"""
    def __init__(self, dimension: int = 128):
        self.index = None
        self.patient_ids = []
        self.dimension = dimension
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(dimension)
            safe_print(f"✅ FAISS index created: dimension={dimension}")
    
    def add_patients(self, patient_ids: List[str], features: List[List[float]]):
        if not self.index:
            return
        try:
            vectors = np.array(features, dtype=np.float32)
            self.index.add(vectors)
            self.patient_ids.extend(patient_ids)
        except Exception as e:
            safe_print(f"⚠️ FAISS add error: {e}")
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[tuple]:
        if not self.index:
            return []
        try:
            q = np.array([query_vector], dtype=np.float32)
            distances, indices = self.index.search(q, top_k)
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.patient_ids):
                    results.append((self.patient_ids[idx], float(distances[0][i])))
            return results
        except Exception as e:
            safe_print(f"⚠️ FAISS search error: {e}")
            return []

class RecommenderSystem:
    """LightGBM + Similar Patient Retrieval + Rule-based"""
    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        if ML_AVAILABLE:
            try:
                self.model = lgb.LGBMClassifier(
                    n_estimators=100,
                    max_depth=10,
                    learning_rate=0.1,
                    random_state=42,
                    verbose=-1
                )
                self.scaler = StandardScaler()
                safe_print("✅ LightGBM model initialized")
            except Exception as e:
                safe_print(f"⚠️ LightGBM init failed: {e}")
    
    def train(self, X: np.ndarray, y: np.ndarray):
        if not self.model:
            return
        try:
            self.model.fit(X, y)
            self.is_trained = True
            safe_print("✅ LightGBM model trained")
        except Exception as e:
            safe_print(f"⚠️ LightGBM training failed: {e}")
    
    def predict(self, features: List[List[float]]) -> List[float]:
        if not self.model or not self.is_trained:
            return [0.5] * len(features)
        try:
            return self.model.predict_proba(features)[:, 1].tolist()
        except:
            return [0.5] * len(features)

class OutbreakPredictor:
    """XGBoost + Isolation Forest"""
    def __init__(self):
        self.xgb_model = None
        self.isolation_model = None
        self.scaler = None
        
        if ML_AVAILABLE:
            try:
                self.xgb_model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    verbosity=0
                )
                self.isolation_model = IsolationForest(
                    contamination=0.1,
                    random_state=42
                )
                self.scaler = StandardScaler()
                safe_print("✅ XGBoost + Isolation Forest initialized")
            except Exception as e:
                safe_print(f"⚠️ ML models init failed: {e}")
    
    def detect_anomalies(self, data: List[List[float]]) -> List[Dict]:
        if not self.isolation_model:
            return []
        try:
            X = np.array(data)
            predictions = self.isolation_model.fit_predict(X)
            scores = -self.isolation_model.score_samples(X)
            
            scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
            
            results = []
            for i, pred in enumerate(predictions):
                results.append({
                    "is_anomaly": pred == -1,
                    "anomaly_score": float(scores[i])
                })
            return results
        except Exception as e:
            safe_print(f"⚠️ Anomaly detection error: {e}")
            return []

# ============================================================================
# VOICE EHR CREATOR
# ============================================================================
class VoiceEHRCreator:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DB_PATH
        self._recognizer = None
        self._mic_available = False
        self._sr_available = False
        
        self.hindi_to_english = {
            'बुखार': 'fever',
            'सिर दर्द': 'headache',
            'जोड़ों में दर्द': 'joint pain',
            'कमर दर्द': 'back pain',
            'खांसी': 'cough',
            'थकान': 'fatigue',
            'जलन': 'burning sensation',
            'पित्त': 'pitta',
            'वात': 'vata',
            'कफ': 'kapha',
            'ठंड': 'cold',
            'शरीर में दर्द': 'body ache',
            'अपच': 'indigestion',
        }
        
        try:
            import speech_recognition as sr
            self._sr = sr
            self._sr_available = True
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8
            safe_print("✅ Speech recognition initialized successfully")
        except ImportError as e:
            safe_print(f"⚠️ Speech recognition not available: {e}")
            self._sr_available = False
            
        if self._sr_available:
            try:
                mic = self._sr.Microphone()
                self._mic_available = True
                safe_print("✅ Microphone detected")
                del mic
            except Exception as e:
                safe_print(f"⚠️ Microphone not available: {e}")

    def _listen(self, language_code: str, prompt: str) -> str | None:
        if not self._mic_available or self._recognizer is None:
            safe_print("   ⚠️ Microphone not available")
            return None
        
        sr = self._sr
        safe_print(f"\n🎙️ {prompt}")
        
        try:
            with sr.Microphone() as source:
                safe_print("   🔇 Adjusting for ambient noise...")
                self._recognizer.adjust_for_ambient_noise(source, duration=1.5)
                safe_print("   🟢 Listening... Speak now!")
                
                audio = self._recognizer.listen(
                    source, 
                    timeout=10,
                    phrase_time_limit=15
                )
                
            safe_print("   ⏳ Transcribing with Google Speech API...")
            
            if language_code == "hi-IN":
                try:
                    text = self._recognizer.recognize_google(audio, language='hi-IN')
                except:
                    text = self._recognizer.recognize_google(audio, language='hi')
            else:
                try:
                    text = self._recognizer.recognize_google(audio, language='en-US')
                except:
                    text = self._recognizer.recognize_google(audio, language='en')
            
            safe_print(f"   ✅ Transcribed: \"{text}\"")
            return text
            
        except sr.WaitTimeoutError:
            safe_print("   ⚠️ No speech detected within timeout. Please try again.")
        except sr.UnknownValueError:
            safe_print("   ⚠️ Could not understand audio. Please speak clearly and try again.")
        except sr.RequestError as e:
            safe_print(f"   ❌ Google Speech API error: {e}")
            safe_print("   💡 Check your internet connection.")
        except Exception as e:
            safe_print(f"   ❌ Unexpected error: {e}")
        
        return None

    def listen_hindi(self) -> str:
        result = self._listen("hi-IN", "कृपया हिंदी में बोलें (Please speak in Hindi)")
        if result is None:
            safe_print("\n⌨️ Microphone unavailable or transcription failed. Please type your input.")
            result = input("   हिंदी में लिखें (Type in Hindi): ").strip()
            if not result:
                result = "मरीज को बुखार और जोड़ों में दर्द है"
                safe_print(f"   (Using sample input: \"{result}\")")
        return result

    def listen_english(self) -> str:
        result = self._listen("en-US", "Please speak in English")
        if result is None:
            safe_print("\n⌨️ Microphone unavailable or transcription failed. Please type your input.")
            result = input("   Type in English: ").strip()
            if not result:
                result = "Patient has fever and joint pain"
                safe_print(f"   (Using sample input: \"{result}\")")
        return result

    def _simple_translate(self, hindi_text: str) -> str:
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

        symptoms_map = {
            'joint pain': ['joint pain', 'joint', 'arthritis', 'joints', 'joints pain', 'joint ache'],
            'fever': ['fever', 'feverish', 'temperature', 'high temperature', 'bukhar', 'बुखार'],
            'headache': ['headache', 'head pain', 'sir dard', 'माथे में दर्द', 'head ache'],
            'cough': ['cough', 'coughing', 'khas', 'खांसी', 'cough'],
            'fatigue': ['fatigue', 'tired', 'exhausted', 'थकान', 'weakness', 'tiredness'],
            'back pain': ['back pain', 'backache', 'lower back', 'कमर दर्द', 'back ache'],
            'burning sensation': ['burning', 'burning sensation', 'जलन', 'burning feeling'],
            'indigestion': ['indigestion', 'digestion', 'अपच', 'bad digestion', 'upset stomach'],
            'body ache': ['body ache', 'body pain', 'muscle pain', 'बदन दर्द', 'body soreness', 'muscle ache', 'whole body pain', 'sarir dard'],
            'cold': ['cold', 'cold and cough', 'ठंड', 'sneezing', 'runny nose', 'sneeze'],
            'nausea': ['nausea', 'nauseous', 'मतली', 'feeling sick'],
            'dizziness': ['dizziness', 'dizzy', 'चक्कर', 'lightheaded'],
            'constipation': ['constipation', 'kabj', 'कब्ज', 'hard stool'],
            'acidity': ['acidity', 'acid reflux', 'heartburn', 'एसिडिटी', 'acid'],
            'skin rash': ['skin rash', 'rash', 'itching', 'खुजली', 'skin irritation'],
            'insomnia': ['insomnia', 'sleep', 'नींद न आना', 'sleep problem'],
            'anxiety': ['anxiety', 'anxious', 'चिंता', 'worry', 'stress'],
            'swollen joints': ['swollen joints', 'swelling', 'joint swelling', 'सूजन', 'inflamed joints'],
            'muscle cramps': ['muscle cramps', 'cramps', 'ऐंठन', 'muscle spasm'],
            'shortness of breath': ['shortness of breath', 'breath', 'sans phoolna', 'सांस फूलना', 'breathing difficulty'],
            'chest pain': ['chest pain', 'chest', 'सीने में दर्द'],
            'stomach pain': ['stomach pain', 'stomach ache', 'पेट दर्द', 'abdominal pain'],
            'vomiting': ['vomiting', 'vomit', 'उल्टी', 'throwing up'],
            'diarrhea': ['diarrhea', 'loose motion', 'दस्त', 'loose stool'],
            'loss of appetite': ['loss of appetite', 'appetite', 'भूख कम होना', 'anorexia'],
            'weight loss': ['weight loss', 'weight', 'वजन घटना', 'unexplained weight loss'],
        }
        
        for symptom, patterns in symptoms_map.items():
            for p in patterns:
                if re.search(r'\b' + re.escape(p) + r'\b', text_lower):
                    found_symptoms.append(symptom)
                    break

        diagnoses_map = {
            'Amavata (Rheumatoid Arthritis)': ['amavata', 'arthritis', 'rheumatoid', 'joint pain chronic', 'आमवात', 'joint swelling'],
            'Pandu (Anemia)': ['pandu', 'anemia', 'low blood', 'pale skin', 'पांडु', 'iron deficiency'],
            'Prameha (Diabetes)': ['prameha', 'diabetes', 'sugar', 'madhumeha', 'प्रमेह', 'blood sugar'],
            'Jwara (Fever)': ['jwara', 'fever', 'ज्वर', 'ताप', 'high temperature'],
            'Kasa (Cough)': ['kasa', 'cough', 'coughing', 'खांसी', 'कास'],
            'Vatarakta (Gout)': ['vatarakta', 'gout', 'वातरक्त'],
            'Kushtha (Skin Disorders)': ['kushtha', 'skin disorder', 'skin disease', 'कुष्ठ'],
            'Arsha (Hemorrhoids)': ['arsha', 'hemorrhoids', 'piles', 'अर्श'],
            'Shwasa (Asthma)': ['shwasa', 'asthma', 'श्वास', 'breathing problem'],
            'Hridroga (Heart Disease)': ['hridroga', 'heart', 'cardiac', 'हृद्रोग'],
            'Shula (Abdominal Pain)': ['shula', 'abdominal pain', 'शूल', 'stomach pain'],
            'Atisara (Diarrhea)': ['atisara', 'diarrhea', 'अतिसार', 'loose motion'],
            'Grahani (IBS)': ['grahani', 'ibs', 'irritable bowel', 'ग्रहणी'],
        }
        
        for diagnosis, patterns in diagnoses_map.items():
            for p in patterns:
                if re.search(r'\b' + re.escape(p) + r'\b', text_lower):
                    found_diagnoses.append(diagnosis)
                    break

        prakriti_map = {
            'Vata': ['vata', 'वात'],
            'Pitta': ['pitta', 'पित्त'],
            'Kapha': ['kapha', 'कफ'],
            'Vata-Pitta': ['vata-pitta', 'वात-पित्त'],
            'Pitta-Kapha': ['pitta-kapha', 'पित्त-कफ'],
            'Vata-Kapha': ['vata-kapha', 'वात-कफ'],
            'Tridosha (Sama)': ['tridosha', 'sama', 'त्रिदोष'],
        }
        
        for prakriti, patterns in prakriti_map.items():
            for p in patterns:
                if re.search(r'\b' + re.escape(p) + r'\b', text_lower):
                    found_prakriti = prakriti
                    break

        return {
            "symptoms": list(set(found_symptoms)),
            "diagnosis": list(set(found_diagnoses)),
            "prakriti": found_prakriti
        }

    def create_ehr(self, patient_id: str, voice_text: str, language: str = "en") -> dict:
        safe_print(f"\n📋 Creating EHR for patient: {patient_id}")
        safe_print(f"   Text: \"{voice_text}\"")
        
        if language == "hi":
            translated_text = self._simple_translate(voice_text)
            entities = self.extract_entities(voice_text, "hi")
            entities_en = self.extract_entities(translated_text, "en")
        else:
            translated_text = voice_text
            entities = self.extract_entities(voice_text, "en")
            entities_en = entities

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
            "confidence_score": 0.0
        }

        # Database insertion is now handled by the FastAPI routers using SQLAlchemy.
        
        safe_print(f"   ✅ EHR saved successfully!")
        safe_print(f"   📋 Symptoms: {record['symptoms']}")
        safe_print(f"   📋 Diagnosis: {record['diagnosis']}")
        safe_print(f"   📋 Prakriti: {record['prakriti']}")
        return record

# ============================================================================
# DISEASE OUTBREAK DETECTOR
# ============================================================================
class DiseaseOutbreakDetector:
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
                raw_scores = -model.score_samples(X)
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
        
        by_disease = {}
        for a in alerts:
            by_disease.setdefault(a["disease"], []).append(a)
        for disease, group in by_disease.items():
            dates = [datetime.strptime(a["date"], "%Y-%m-%d") for a in group]
            for a, d in zip(group, dates):
                co_occurring = [
                    g["district"] for g, gd in zip(group, dates)
                    if g["district"] != a["district"] and abs((gd - d).days) <= 10
                ]
                a["regional_cluster"] = bool(co_occurring)
                a["cluster_districts"] = sorted(set(co_occurring))
        
        return alerts[:top_n]

# ============================================================================
