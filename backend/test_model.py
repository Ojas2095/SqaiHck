# test_models.py
import config
from transformers import MarianMTModel, MarianTokenizer, AutoTokenizer, AutoModelForCausalLM

print("=== Testing Translation Model ===")
try:
    print(f"Loading: {config.TRANSLATION_MODEL_NAME}")
    tokenizer = MarianTokenizer.from_pretrained(config.TRANSLATION_MODEL_NAME)
    model = MarianMTModel.from_pretrained(config.TRANSLATION_MODEL_NAME)
    print("âœ… Translation model loaded successfully!")
except Exception as e:
    print(f"âŒ Translation model failed: {type(e).__name__}: {e}")

print("\n=== Testing LLM Model ===")
try:
    print(f"Loading: {config.LLM_MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(config.LLM_MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        config.LLM_MODEL_NAME,
        trust_remote_code=True,
        device_map="auto"  # Will try to use GPU if available
    )
    print("âœ… LLM model loaded successfully!")
except Exception as e:
    print(f"âŒ LLM model failed: {type(e).__name__}: {e}")

