# llm_engine.py
"""
Generation step of the RAG pipeline.
"""
from typing import Dict, List, Optional
import time

import config

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    _LLM_STACK_AVAILABLE = True
except ImportError:
    _LLM_STACK_AVAILABLE = False


SYSTEM_PROMPT = (
    "You are an AYUSH clinical assistant supporting a registered Ayurvedic "
    "practitioner. Base your answer strictly on the CONTEXT passages "
    "provided below, which come from the practitioner's own clinical "
    "knowledge base. If the context does not fully cover the case, say so "
    "explicitly rather than inventing details. Always add a note that this "
    "is decision support, not a replacement for clinical judgement."
)


def build_prompt(patient_summary: str, evidence: List[Dict]) -> str:
    context_block = "\n\n".join(
        f"[Evidence {i + 1} | source: {e['source']} | relevance: {e['relevance_score']}]\n{e['text']}"
        for i, e in enumerate(evidence)
    ) or "(no closely matching evidence retrieved)"

    return f"""CONTEXT:
{context_block}

PATIENT CASE:
{patient_summary}

Using ONLY the context above and standard Ayurvedic reasoning about dosha
balance, provide:
1. Recommended herbs/formulations (and why, referencing the evidence)
2. Diet recommendations
3. Yoga / physical therapy
4. Lifestyle & preventive advice
5. Any contraindications to flag

Keep it concise and clinically actionable."""


class LLMEngine:
    def __init__(self, model_name: str = config.LLM_MODEL_NAME, use_gpu: bool = False):
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self.model_name = model_name
        
        # If no model name provided, skip loading
        if not model_name or model_name.strip() == "":
            print("â„¹ï¸ No LLM model specified, using template fallback")
            return
            
        if not _LLM_STACK_AVAILABLE:
            print("âš ï¸ Transformers not installed, using template fallback")
            return
            
        try:
            # Check for GPU
            if use_gpu and torch.cuda.is_available():
                self.device = "cuda"
                print(f"ðŸŸ¢ Using GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("ðŸŸ¡ Using CPU for LLM")
            
            print(f"ðŸ“¥ Loading LLM model: {model_name}")
            start_time = time.time()
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True,
                use_fast=True
            )
            
            # Set padding token if not set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with optimizations
            try:
                # Try to load with 8-bit quantization if bitsandbytes is available
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_threshold=6.0,
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=quantization_config,
                    trust_remote_code=True,
                    device_map="auto" if self.device == "cuda" else None,
                    low_cpu_mem_usage=True,
                )
            except (ImportError, Exception) as e:
                # Fallback to normal loading
                print(f"âš ï¸ 8-bit quantization not available: {e}")
                print("   Loading model normally (this may take a moment)...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,  # Use float32 for CPU stability
                    low_cpu_mem_usage=True,
                )
                if self.device == "cpu":
                    self.model.to(self.device)
            
            # Set to evaluation mode
            self.model.eval()
            
            load_time = time.time() - start_time
            print(f"âœ… LLM model loaded successfully in {load_time:.1f}s on {self.device}")
            
        except Exception as e:
            print(f"âŒ Failed to load LLM: {type(e).__name__}: {e}")
            print("   Using template fallback instead")
            self.model = None
            self.tokenizer = None

    @property
    def is_available(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def generate_raw(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 8) -> Optional[str]:
        """Generic single-turn generation, independent of the treatment-plan
        prompt template in build_prompt(). Used by benchmark_engine.py to ask
        MCQ questions without dragging in patient-summary/evidence framing."""
        if not self.is_available:
            return None
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            try:
                text = self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                sys_part = f"System: {system_prompt}\n\n" if system_prompt else ""
                text = f"{sys_part}User: {prompt}\n\nAssistant:"

            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    num_beams=1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,
                )

            input_length = inputs["input_ids"].shape[1]
            decoded = self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)
            return decoded.strip() if decoded else None
        except Exception as e:
            print(f"âŒ LLM generate_raw error: {type(e).__name__}: {e}")
            return None

    def generate(self, patient_summary: str, evidence: List[Dict], max_tokens: int = 200) -> Optional[str]:
        if not self.is_available:
            return None
            
        try:
            prompt = build_prompt(patient_summary, evidence)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            
            # Apply chat template (try different formats)
            try:
                text = self.tokenizer.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
            except Exception:
                # Fallback: simple prompt format
                text = f"System: {SYSTEM_PROMPT}\n\nUser: {prompt}\n\nAssistant:"
            
            # Tokenize with truncation
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=1024
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate with optimized parameters
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.6,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1,
                    use_cache=True,
                    num_beams=1,  # Greedy decoding for speed
                )
            
            # Decode only the new tokens
            input_length = inputs["input_ids"].shape[1]
            generated_tokens = outputs[0][input_length:]
            decoded = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            return decoded.strip() if decoded else None
            
        except Exception as e:
            print(f"âŒ LLM generation error: {type(e).__name__}: {e}")
            return None


class TemplateFallbackGenerator:
    """Deterministic, evidence-grounded plan used whenever no LLM is
    loaded or when the LLM generation fails/times out."""

    @staticmethod
    def generate(patient_summary: str, evidence: List[Dict], best_records: List[Dict]) -> str:
        if not best_records:
            return (
                "No closely matching record was found in the knowledge base for this "
                "case. Recommend manual review by an AYUSH practitioner; general "
                "dosha-balancing advice (regular routine, seasonally appropriate diet, "
                "adequate sleep) applies until a fuller history is available."
            )

        herbs, diets, yogas, contraindications, sources = set(), set(), set(), set(), set()
        for rec in best_records:
            for h in (rec.get("herbs_raw") or "").split(","):
                if h.strip():
                    herbs.add(h.strip())
            if rec.get("diet"):
                diets.add(rec["diet"])
            if rec.get("yoga"):
                yogas.add(rec["yoga"])
            if rec.get("contraindications"):
                contraindications.add(rec["contraindications"])
            if rec.get("evidence_source"):
                sources.add(rec["evidence_source"])

        lines = [
            f"ðŸŒ¿ Herbs/Formulations: {', '.join(sorted(herbs)[:6]) or 'consult evidence below'}",
            f"ðŸ½ï¸ Diet: {' | '.join(sorted(diets)[:3]) or 'general sattvic, dosha-appropriate diet'}",
            f"ðŸ§˜ Yoga/Lifestyle: {' | '.join(sorted(yogas)[:3]) or 'daily Pranayama and gentle movement'}",
        ]
        if contraindications:
            lines.append(f"âš ï¸ Contraindications to flag: {' | '.join(sorted(contraindications)[:3])}")
        if sources:
            lines.append(f"ðŸ“š Drawn from: {', '.join(sorted(sources)[:3])}")
        lines.append(
            "\nðŸ“‹ This is retrieval-grounded decision support generated without a full "
            "language model; a qualified AYUSH practitioner should review before use."
        )
        return "\n".join(lines)


