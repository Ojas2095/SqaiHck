import os
import subprocess
import sys

print("=== Fixing AYUSH AI Models ===\n")

# 1. Upgrade PyTorch
print("1. Upgrading PyTorch to v2.6+...")
subprocess.run([
    sys.executable, "-m", "pip", "install", "--upgrade",
    "torch", "torchvision", "torchaudio",
    "--index-url", "https://download.pytorch.org/whl/cpu"
], check=False)

# 2. Install smaller models
print("\n2. Installing smaller models...")

# Install TinyLlama (1.1B parameters, ~2GB)
print("   - Installing TinyLlama...")
subprocess.run([
    sys.executable, "-c",
    "from transformers import AutoTokenizer, AutoModelForCausalLM; "
    "AutoTokenizer.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0'); "
    "AutoModelForCausalLM.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')"
], check=False)

# Install translation model
print("   - Installing translation model...")
subprocess.run([
    sys.executable, "-c",
    "from transformers import MarianTokenizer, MarianMTModel; "
    "MarianTokenizer.from_pretrained('Helsinki-NLP/opus-mt-hi-en'); "
    "MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-hi-en')"
], check=False)

print("\nâœ… Installation complete!")
print("\nNow update config.py:")
print("LLM_MODEL_NAME = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'")
print("TRANSLATION_MODEL_NAME = 'Helsinki-NLP/opus-mt-hi-en'")
