from .ai_service import (
    SpeechModel, TranslationModel, MedicalNER, RAGEngine, LLMEngine,
    PatientSimilarity, RecommenderSystem, OutbreakPredictor, VoiceEHRCreator,
    DiseaseOutbreakDetector, AyurvedaDataLoader, safe_print,
    WHISPER_AVAILABLE, NER_AVAILABLE, RAG_AVAILABLE, LLM_AVAILABLE, ML_AVAILABLE, FAISS_AVAILABLE, SHAP_AVAILABLE
)

safe_print("="*60)
safe_print("🚀 INITIALIZING AYUSH AI SERVICES")
safe_print("="*60)

try:
    speech_model = SpeechModel(model_size="base", device="cpu")
    translation_model = TranslationModel()
    ner_model = MedicalNER()
    rag_engine = RAGEngine()
    llm_engine = LLMEngine(use_gpu=False)
    patient_similarity = PatientSimilarity(dimension=128)
    recommender_system = RecommenderSystem()
    outbreak_predictor = OutbreakPredictor()
    voice_creator = VoiceEHRCreator()
    outbreak_detector = DiseaseOutbreakDetector()
    data_loader = AyurvedaDataLoader()
    
    # Optionally load standard data if needed
    # data_loader.load_local_excel()
    safe_print("✅ All AI services initialized successfully!")
except Exception as e:
    safe_print(f"⚠️ Error initializing AI services: {e}")
