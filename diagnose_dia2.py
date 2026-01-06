#!/usr/bin/env python3
"""
Dia2 Diagnostic Script
======================

Quick diagnostic to check Dia2 installation and model loading.
"""

import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("Dia2 Diagnostic")
print("=" * 70)

# Step 1: Check config
print("\n1. Checking configuration...")
try:
    from engine.config import DIA2_PATH
    print(f"   ✓ DIA2_PATH: {DIA2_PATH}")
    print(f"   ✓ Path exists: {DIA2_PATH.exists()}")
    if DIA2_PATH.exists():
        print(f"   ✓ Contents: {list(DIA2_PATH.iterdir())[:5]}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Step 2: Try to import dia2
print("\n2. Trying to import dia2...")
try:
    sys.path.insert(0, str(DIA2_PATH))
    import dia2
    print(f"   ✓ dia2 imported successfully")
    print(f"   ✓ dia2 location: {dia2.__file__}")
    print(f"   ✓ dia2 version: {getattr(dia2, '__version__', 'unknown')}")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    print(f"\n   💡 Possible fixes:")
    print(f"      - cd {DIA2_PATH}")
    print(f"      - uv sync  (or pip install -e .)")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Step 3: Import Dia2 classes
print("\n3. Importing Dia2 classes...")
try:
    from dia2 import Dia2, GenerationConfig, SamplingConfig
    print(f"   ✓ Dia2 class imported")
    print(f"   ✓ GenerationConfig imported")
    print(f"   ✓ SamplingConfig imported")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Step 4: Check PyTorch
print("\n4. Checking PyTorch...")
try:
    import torch
    print(f"   ✓ PyTorch version: {torch.__version__}")
    print(f"   ✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   ✓ CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"   ✓ MPS available: {torch.backends.mps.is_available()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Step 5: Try to load Dia2 model
print("\n5. Attempting to load Dia2 model...")
print("   ⚠️  This may take a while and download ~4GB...")

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = "bfloat16" if torch.cuda.is_available() else "float32"

print(f"   Using device: {device}, dtype: {dtype}")

try:
    print("   Loading Dia2-2B from HuggingFace...")
    model = Dia2.from_repo(
        "nari-labs/Dia2-2B",
        device=device,
        dtype=dtype
    )
    print(f"   ✓ Model loaded successfully!")
    print(f"   ✓ Model type: {type(model)}")
except Exception as e:
    print(f"   ❌ Model loading failed: {e}")
    print(f"\n   💡 Common issues:")
    print(f"      - HuggingFace authentication required")
    print(f"      - Not enough memory (needs ~4GB)")
    print(f"      - Device not supported (try CPU)")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 6: Check Dia2Provider
print("\n6. Checking Dia2Provider...")
try:
    from engine.providers.tts.dia2 import Dia2Provider
    provider = Dia2Provider()
    print(f"   ✓ Dia2Provider created")
    print(f"   ✓ Name: {provider.name}")
    print(f"   ✓ Display name: {provider.display_name}")
    print(f"   ✓ Sample rate: {provider.sample_rate}Hz")
    print(f"   ✓ Inference methods: {provider.inference_methods}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ Dia2 diagnostic complete!")
print("=" * 70)
print("\nIf all checks passed, Dia2 should work for generation.")
print("Try running: python test_dia2_generation.py")
