#!/usr/bin/env python3
"""
Download and cache ML models locally for embedding in Docker image.
Run at Docker build time to pre-cache models before runtime.
"""

import os
import sys

# Set HuggingFace cache directory
os.environ["HF_HOME"] = "/app/models"

print("Downloading models to /app/models...")

try:
    print("Loading moondream2 model and tokenizer...")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    AutoModelForCausalLM.from_pretrained(
        "vikhyatk/moondream2",
        trust_remote_code=True,
        attn_implementation="eager",
    )
    AutoTokenizer.from_pretrained("vikhyatk/moondream2", trust_remote_code=True)
    print("✓ moondream2 cached")

    print("Loading KeyBERT model...")
    from keybert import KeyBERT

    KeyBERT()
    print("✓ KeyBERT cached")

    print("\n✓ All models downloaded and cached to /app/models")
    sys.exit(0)

except Exception as e:
    print(f"✗ Error downloading models: {e}", file=sys.stderr)
    sys.exit(1)
