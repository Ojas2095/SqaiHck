# nlp_engine.py
"""
Speech-to-text, translation, and medical entity extraction for the
voice-based multilingual EHR capability.

Design choice on NER: the previous version pointed a generic
`dslim/bert-base-NER` model (which only knows PERSON/ORG/LOCATION/MISC) at
this problem and then looked for labels like "B-SYMPTOM" that model can
never produce â€” so it silently returned nothing. Instead, this module
builds a gazetteer (a lookup dictionary) directly from the real
symptom/disease/herb vocabulary mined from your two datasets in
`knowledge_base.py`. That guarantees extraction actually matches the
vocabulary your recommender and RAG corpus use, in both English and a
Hindi transliteration/script layer. A transformer NER model can be layered
on top later as a precision boost, but the gazetteer is the part that
makes the pipeline actually work end to end today.
"""
import os
import re
from typing import Dict, List, Optional

import config

try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False

try:
    from transformers import MarianMTModel, MarianTokenizer
    _MT_AVAILABLE = True
except ImportError:
    _MT_AVAILABLE = False


# Small Hindi<->English gazetteer covering common clinical terms, used as
# (a) the fallback translator when no MT model is loaded and (b) a source
# of Hindi surface forms for the NER gazetteer below.
HINDI_EN_TERMS = {
    "à¤¬à¥à¤–à¤¾à¤°": "fever", "à¤¸à¤¿à¤° à¤¦à¤°à¥à¤¦": "headache", "à¤œà¥‹à¤¡à¤¼à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¦à¤°à¥à¤¦": "joint pain",
    "à¤•à¤®à¤° à¤¦à¤°à¥à¤¦": "back pain", "à¤–à¤¾à¤‚à¤¸à¥€": "cough", "à¤¥à¤•à¤¾à¤¨": "fatigue",
    "à¤œà¤²à¤¨": "burning sensation", "à¤ à¤‚à¤¡": "cold", "à¤¶à¤°à¥€à¤° à¤®à¥‡à¤‚ à¤¦à¤°à¥à¤¦": "body ache",
    "à¤…à¤ªà¤š": "indigestion", "à¤ªà¥‡à¤Ÿ à¤¦à¤°à¥à¤¦": "stomach pain", "à¤‰à¤²à¥à¤Ÿà¥€": "vomiting",
    "à¤¦à¤¸à¥à¤¤": "diarrhea", "à¤šà¤•à¥à¤•à¤°": "dizziness", "à¤•à¤¬à¥à¤œ": "constipation",
    "à¤–à¥à¤œà¤²à¥€": "skin rash", "à¤¨à¥€à¤‚à¤¦ à¤¨ à¤†à¤¨à¤¾": "insomnia", "à¤šà¤¿à¤‚à¤¤à¤¾": "anxiety",
    "à¤¸à¥‚à¤œà¤¨": "swelling", "à¤¸à¤¾à¤‚à¤¸ à¤«à¥‚à¤²à¤¨à¤¾": "shortness of breath",
    "à¤­à¥‚à¤– à¤•à¤® à¤¹à¥‹à¤¨à¤¾": "loss of appetite", "à¤µà¤œà¤¨ à¤˜à¤Ÿà¤¨à¤¾": "weight loss",
}


class SpeechModel:
    """faster-whisper: multilingual, works fully offline once the model
    weights are downloaded once, so it fits AHMIS's need for voice EHR
    creation across Indian languages without depending on an external API."""

    def __init__(self, model_size: str = config.WHISPER_MODEL_SIZE, device: str = "cpu"):
        self.model = None
        if _WHISPER_AVAILABLE:
            try:
                self.model = WhisperModel(model_size, device=device, compute_type="int8")
            except Exception:
                self.model = None

    @property
    def is_available(self) -> bool:
        return self.model is not None

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict:
        if not self.model:
            return {"text": "", "language": language or "en", "error": "speech model not loaded"}
        segments, info = self.model.transcribe(audio_path, language=language)
        text = " ".join(seg.text for seg in segments).strip()
        return {"text": text, "language": info.language, "language_probability": round(info.language_probability, 3)}


class TranslationModel:
    """Machine translation for Indian-language EHR text. Uses a real MT
    model (MarianMT hi->en) if transformers + the model weights are
    available; otherwise falls back to the gazetteer above so the pipeline
    still functions offline."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        if _MT_AVAILABLE:
            try:
                self.tokenizer = MarianTokenizer.from_pretrained(config.TRANSLATION_MODEL_NAME)
                self.model = MarianMTModel.from_pretrained(config.TRANSLATION_MODEL_NAME)
            except Exception:
                self.model = None

    @property
    def uses_neural_model(self) -> bool:
        return self.model is not None

    def translate(self, text: str, src: str = "hi", tgt: str = "en") -> str:
        if not text:
            return text
        if src == "hi" and tgt == "en" and self.model is not None:
            try:
                batch = self.tokenizer([text], return_tensors="pt", padding=True, truncation=True)
                generated = self.model.generate(**batch, max_new_tokens=128)
                return self.tokenizer.decode(generated[0], skip_special_tokens=True)
            except Exception:
                pass
        # Gazetteer fallback (also used for en->hi, which MarianMT hi-en can't do)
        result = text
        table = HINDI_EN_TERMS if src == "hi" else {v: k for k, v in HINDI_EN_TERMS.items()}
        for src_term, tgt_term in table.items():
            result = result.replace(src_term, tgt_term)
        return result


class MedicalNER:
    """Gazetteer-based extraction over the vocabulary mined from your own
    datasets (see knowledge_base.KnowledgeBase). Deterministic, requires no
    model download, and â€” unlike a mismatched generic NER model â€” actually
    recognises the terms your corpus and recommender use.

    Matching is fuzzy at the token level (not exact-phrase) so that layman
    phrasing like "no appetite" still matches a vocab entry stored as "loss
    of appetite" regardless of word order, pluralisation, or synonym --
    the previous version required the patient's exact wording to appear
    verbatim, which silently failed on any reordering or rephrasing.

    IMPORTANT: `_layman_synonyms` below maps everyday phrasing to a
    canonical term. That canonical term is only useful if it actually
    exists in this dataset's mined symptom vocabulary -- __init__ validates
    this at startup and prints a warning for any target that doesn't
    exist, since a plausible-sounding-but-absent target (e.g. an earlier
    version of this file mapped "blurry vision" to "weak eyesight", which
    never occurs anywhere in either source dataset) makes that phrase
    silently unmatchable no matter how the patient words it."""

    _STOPWORDS = {"of", "in", "on", "a", "an", "the", "and", "or", "to", "with", "for"}

    def __init__(self, symptom_vocab: set, disease_vocab: set, herb_vocab: set):
        self.symptom_vocab = sorted(symptom_vocab, key=len, reverse=True)
        self.disease_vocab = sorted(disease_vocab, key=len, reverse=True)
        self.herb_vocab = sorted(herb_vocab, key=len, reverse=True)
        self._prakriti_terms = {
            "vata": "Vata", "pitta": "Pitta", "kapha": "Kapha",
            "tridosha": "Tridoshic", "tridoshic": "Tridoshic",
        }
        # Common everyday phrasing -> a normalized form more likely to line
        # up with clinical vocabulary wording. Extend this table as you
        # notice more patient phrasings that should map to a known term.
        # NOTE: every canonical target here MUST be a term that actually
        # occurs in the mined symptom_vocab -- mapping to a plausible-sounding
        # but non-existent term (e.g. the old "weak eyesight"/"tongue ulcer",
        # neither of which appears anywhere in ayurveda_dataset.csv or
        # AyurGenixAI_Dataset.xlsx) makes the phrase unmatchable no matter
        # how the patient words it. __init__ below checks this at startup.
        self._layman_synonyms = {
            "can't see properly": "blurred vision", "cant see properly": "blurred vision",
            "blurry vision": "blurred vision", "blur vision": "blurred vision",
            "blurry eyesight": "blurred vision", "weak eyesight": "blurred vision",
            "weak eyes": "blurred vision", "eyes are weak": "blurred vision",
            "eyesight is weak": "blurred vision", "eyesight weak": "blurred vision",
            "mouth ulcer": "mouth sores", "ulcer in mouth": "mouth sores",
            "ulcer on tongue": "mouth sores", "sore in mouth": "mouth sores",
            "tongue ulcer": "mouth sores", "tongue ulcers": "mouth sores",
            "stomach ache": "stomach pain", "tummy ache": "stomach pain",
            "loose motion": "diarrhea", "loose motions": "diarrhea",
            "can't sleep": "insomnia", "cant sleep": "insomnia",
            "no appetite": "loss of appetite", "not hungry": "loss of appetite",
            "out of breath": "shortness of breath",
        }
        self._validate_synonym_targets()

    def _validate_synonym_targets(self) -> None:
        """Startup guardrail: warn loudly (don't fail silently) if any
        _layman_synonyms canonical target isn't actually in the mined
        symptom vocabulary -- that's exactly the bug that made "blurry
        vision" / "weak eyesight" undetectable before, and it can silently
        recur any time the dataset changes or someone edits the table
        without checking it against real data."""
        vocab_lower = set(self.symptom_vocab)  # already lowercased by KnowledgeBase._build_vocab
        unmatched = sorted({c for c in self._layman_synonyms.values() if c.lower() not in vocab_lower})
        if unmatched:
            print(f"âš ï¸  MedicalNER: {len(unmatched)} layman-synonym target(s) do not exist in the "
                  f"symptom vocabulary and will NEVER match anything: {unmatched}. "
                  f"Fix the mapping in nlp_engine._layman_synonyms or check for a dataset change.")

    @staticmethod
    def _singularize(word: str) -> str:
        """Naive plural stripping â€” good enough for gazetteer matching,
        not a real stemmer. Errs on the side of leaving ambiguous words
        alone (e.g. words ending 'ss', or short words) rather than risk
        mangling an already-singular term."""
        if len(word) > 4 and word.endswith("ies"):
            return word[:-3] + "y"
        if len(word) > 5 and word.endswith(("ches", "shes", "xes")):
            return word[:-2]
        if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            return word[:-1]
        return word

    @classmethod
    def _tokenize(cls, text: str) -> set:
        words = re.findall(r"[a-z]+", text.lower())
        return {cls._singularize(w) for w in words if w not in cls._STOPWORDS and len(w) >= 3}

    def _apply_layman_synonyms(self, text_lower: str) -> str:
        expanded = text_lower
        for phrase, canonical in self._layman_synonyms.items():
            if phrase in text_lower:
                expanded += f" {canonical}"
        return expanded

    def _find_terms(self, text_lower: str, vocab: List[str]) -> List[str]:
        text_tokens = self._tokenize(text_lower)
        found = []
        for term in vocab:
            term_l = term.lower()
            if len(term_l) < 3:
                continue
            # Fast path: exact phrase present (handles single words and the
            # common case where wording matches verbatim).
            if re.search(r"\b" + re.escape(term_l) + r"\b", text_lower):
                found.append(term)
                continue
            # Fuzzy path: every meaningful word of the vocab term shows up
            # somewhere in the text, regardless of order or plural form.
            # This is what catches "weak eyesight" vs "eyesight weak" and
            # "tongue ulcers" vs "tongue ulcer".
            term_tokens = self._tokenize(term_l)
            if len(term_tokens) >= 2 and term_tokens.issubset(text_tokens):
                found.append(term)
        return found

    def extract(self, text: str, hindi_text: Optional[str] = None) -> Dict:
        combined = f"{text} {hindi_text or ''}"
        # also expand any Hindi gazetteer terms present, so "à¤¬à¥à¤–à¤¾à¤°" surfaces as "fever" too
        for hi, en in HINDI_EN_TERMS.items():
            if hi in combined:
                combined += f" {en}"
        text_lower = combined.lower()
        text_lower = self._apply_layman_synonyms(text_lower)

        symptoms = self._find_terms(text_lower, self.symptom_vocab)
        diseases = self._find_terms(text_lower, self.disease_vocab)
        herbs = self._find_terms(text_lower, self.herb_vocab)

        prakriti = None
        for term, label in self._prakriti_terms.items():
            if re.search(r"\b" + term + r"\b", text_lower):
                prakriti = label
                break

        return {
            "symptoms": sorted(set(symptoms)),
            "diseases": sorted(set(diseases)),
            "herbs_mentioned": sorted(set(herbs)),
            "prakriti": prakriti,
        }

