# benchmark_engine.py
"""
Self-test: evaluates the loaded LLM (llm_engine.LLMEngine) against the
BhashaBench-Ayur MCQ benchmark (knowledge_base.KnowledgeBase.bhashabench_en /
.bhashabench_hi), and reports accuracy.

This is intentionally kept separate from RAG/recommendation -- it never
touches kb.records/kb.chunks and has no bearing on what gets recommended to
a patient. It exists purely to answer "how good is the currently-loaded LLM
at Ayurvedic exam questions", which is what BhashaBench-Ayur is for.

Dataset columns (per the dataset's own eval scripts): question, option_a,
option_b, option_c, option_d, correct_answer, topic, subject_domain,
question_level. `correct_answer` has been observed as either a bare letter
("A"/"B"/"C"/"D") or the full option text -- _normalise_answer() handles
both so a format quirk doesn't just silently score everything wrong.
"""
import random
import re
from typing import Dict, List, Optional

import pandas as pd

MCQ_SYSTEM_PROMPT = (
    "You are answering a multiple-choice Ayurveda examination question. "
    "Reply with ONLY the single letter of the correct option (A, B, C, or D) "
    "and nothing else -- no explanation."
)

_LETTER_RE = re.compile(r"\b([ABCD])\b", re.IGNORECASE)


def _normalise_answer(raw_correct: str, options: Dict[str, str]) -> Optional[str]:
    """Map whatever `correct_answer` contains (a letter, or the option's full
    text) to one of 'A'/'B'/'C'/'D', so we can compare it to the model's
    letter output. Returns None if it can't be resolved -- callers should
    skip such rows rather than silently guessing."""
    if not raw_correct:
        return None
    raw = str(raw_correct).strip()
    m = _LETTER_RE.fullmatch(raw)
    if m:
        return m.group(1).upper()
    raw_lower = raw.lower()
    for letter, text in options.items():
        if text and text.strip().lower() == raw_lower:
            return letter
    return None


def _extract_letter(model_output: str) -> Optional[str]:
    if not model_output:
        return None
    m = _LETTER_RE.search(model_output)
    return m.group(1).upper() if m else None


class BenchmarkEngine:
    def __init__(self, kb, llm_engine):
        self.kb = kb
        self.llm_engine = llm_engine

    def is_ready(self, language: str) -> bool:
        df = self._df_for(language)
        return df is not None and not df.empty

    def _df_for(self, language: str) -> Optional[pd.DataFrame]:
        if language.lower().startswith("hi"):
            return self.kb.bhashabench_hi
        return self.kb.bhashabench_en

    def run(self, language: str = "English", max_questions: int = 20,
            question_level: Optional[str] = None, seed: int = 42) -> Dict:
        df = self._df_for(language)
        if df is None or df.empty:
            return {
                "error": (
                    f"BhashaBench-Ayur [{language}] is not loaded. Check the "
                    f"'BhashaBench-Ayur status' line printed at server startup "
                    f"for the reason (HF_TOKEN not set, dataset access not yet "
                    f"approved on Hugging Face, or no internet access)."
                ),
            }
        if not self.llm_engine.is_available:
            return {"error": "LLM is not loaded, cannot run benchmark (see 'LLM loaded' at server startup)."}

        if question_level:
            df = df[df["question_level"].str.lower() == question_level.lower()]
            if df.empty:
                return {"error": f"No questions found for question_level='{question_level}'."}

        n = min(max_questions, len(df))
        sample = df.sample(n=n, random_state=seed) if n < len(df) else df

        results: List[Dict] = []
        correct_count = 0
        skipped = 0
        by_domain: Dict[str, Dict[str, int]] = {}

        for _, row in sample.iterrows():
            options = {
                "A": str(row.get("option_a", "")),
                "B": str(row.get("option_b", "")),
                "C": str(row.get("option_c", "")),
                "D": str(row.get("option_d", "")),
            }
            correct_letter = _normalise_answer(row.get("correct_answer"), options)
            if correct_letter is None:
                skipped += 1
                continue

            question = str(row.get("question", "")).strip()
            prompt = (
                f"Question: {question}\n"
                f"A. {options['A']}\nB. {options['B']}\nC. {options['C']}\nD. {options['D']}\n\n"
                f"Answer (single letter only):"
            )
            raw_output = self.llm_engine.generate_raw(prompt, system_prompt=MCQ_SYSTEM_PROMPT, max_tokens=8)
            model_letter = _extract_letter(raw_output or "")
            is_correct = model_letter == correct_letter
            if is_correct:
                correct_count += 1

            domain = str(row.get("subject_domain", "unknown"))
            bucket = by_domain.setdefault(domain, {"correct": 0, "total": 0})
            bucket["total"] += 1
            if is_correct:
                bucket["correct"] += 1

            if len(results) < 10:  # keep the payload small; full accuracy stats cover the rest
                results.append({
                    "question": question[:200],
                    "model_answer": model_letter,
                    "correct_answer": correct_letter,
                    "is_correct": is_correct,
                    "topic": row.get("topic"),
                    "question_level": row.get("question_level"),
                })

        scored = n - skipped
        accuracy = round(correct_count / scored, 3) if scored else None

        return {
            "language": language,
            "model": getattr(self.llm_engine, "model_name", "unknown"),
            "questions_sampled": int(n),
            "questions_scored": int(scored),
            "questions_skipped_unparseable_answer": int(skipped),
            "correct": int(correct_count),
            "accuracy": accuracy,
            "accuracy_by_subject_domain": {
                domain: round(v["correct"] / v["total"], 3) for domain, v in by_domain.items()
            },
            "sample_results": results,
        }

