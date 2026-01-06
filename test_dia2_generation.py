#!/usr/bin/env python3
"""
Test Dia2 TTS Generation
=========================

Test actual audio generation with Dia2 provider.
"""

import os
import sys
import json
from pathlib import Path
import warnings

# Suppress FutureWarnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Set up paths
AUDIOBOOK_ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = AUDIOBOOK_ENGINE_DIR / "projects" / "fourth-wing"

# Add engine to path
sys.path.insert(0, str(AUDIOBOOK_ENGINE_DIR))

from engine.providers.registry import ProviderRegistry
from engine.providers.tts.dia2 import Dia2Provider
import torch
import time

def main():
    print("=" * 70)
    print("Testing Dia2 TTS Generation")
    print("=" * 70)

    # Register Dia2 provider
    print("\nRegistering Dia2 provider...")
    try:
        ProviderRegistry.register_tts(Dia2Provider)
        print("✓ Dia2 provider registered")
    except Exception as e:
        print(f"❌ Failed to register Dia2: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get provider
    dia2 = ProviderRegistry.get_tts("dia2")
    if not dia2:
        print("❌ Could not get Dia2 provider from registry")
        return

    print(f"✓ Got provider: {dia2.display_name}")
    print(f"  Sample rate: {dia2.sample_rate}Hz")
    print(f"  Inference methods: {', '.join(dia2.inference_methods)}")

    # Load chunks
    chunks_path = PROJECT_DIR / "chunked_book.json"
    print(f"\nLoading chunks from: {chunks_path}")

    if not chunks_path.exists():
        print(f"❌ Chunks file not found: {chunks_path}")
        return

    with open(chunks_path) as f:
        all_chunks = json.load(f)

    print(f"✓ Loaded {len(all_chunks)} chunks")

    # Get first chunk
    chunk = all_chunks[0]
    chunk_id = chunk["chunk_id"]
    text = chunk["text"]
    speaker = chunk["speaker"]

    print(f"\nTest Chunk {chunk_id}:")
    print(f"  Speaker: {speaker}")
    print(f"  Text: {text[:100]}...")

    # Load voice seed for this speaker
    seeds_dir = PROJECT_DIR / "seeds"

    # Try to find seed directory for speaker
    speaker_dir = seeds_dir / speaker
    if not speaker_dir.exists():
        # Try finding by matching
        for seed_dir in seeds_dir.iterdir():
            if seed_dir.is_dir() and seed_dir.name.upper() == speaker.upper():
                speaker_dir = seed_dir
                break

    if not speaker_dir.exists():
        print(f"❌ No seed directory found for speaker: {speaker}")
        return

    # Load seed.json
    seed_json_path = speaker_dir / "seed.json"
    if not seed_json_path.exists():
        print(f"❌ No seed.json found at: {seed_json_path}")
        return

    with open(seed_json_path) as f:
        seed_data = json.load(f)

    print(f"✓ Loaded seed for {speaker}")

    # Get audio file path
    audio_file = seed_data.get("audio_path") or seed_data.get("audio_file") or seed_data.get("seed_file")
    if not audio_file:
        print(f"❌ No audio file path in seed.json")
        return

    seed_audio_path = speaker_dir / audio_file
    if not seed_audio_path.exists():
        print(f"❌ Seed audio not found: {seed_audio_path}")
        return

    print(f"  Audio: {seed_audio_path.name}")

    # Get prompt text (not needed for Dia2, but stored in seed)
    prompt_text = seed_data.get("prompt_text") or seed_data.get("transcript") or ""
    print(f"  Prompt: {prompt_text[:80]}..." if prompt_text else "  Prompt: (none)")

    # Create output directory
    output_dir = AUDIOBOOK_ENGINE_DIR / "test_output"
    output_dir.mkdir(exist_ok=True)

    # Test all available inference methods
    methods = dia2.inference_methods

    for method in methods:
        print(f"\n{'='*70}")
        print(f"Testing {method} method")
        print(f"{'='*70}")

        try:
            # Detailed logging
            text_words = len(text.split())

            print(f"\n📊 Generation Analysis:")
            print(f"   Text: {len(text)} chars, {text_words} words")
            print(f"   Method: {method}")

            generation_start = time.time()

            # Generate audio using Dia2
            print(f"→ Calling Dia2 generate_audio...")
            audio = dia2.generate_audio(
                text=text,
                voice_seed_path=seed_audio_path,
                prompt_text=None,  # Dia2 doesn't use prompt text
                inference_method=method
            )

            generation_time = time.time() - generation_start

            if audio is None:
                print(f"❌ Generation returned None")
                continue

            # Save using soundfile (consistent with CosyVoice test)
            import soundfile as sf
            output_path = output_dir / f"chunk_{chunk_id:04d}_dia2_{method}.wav"

            audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
            # Ensure proper shape for soundfile (samples,) or (samples, channels)
            if audio_np.ndim > 1:
                audio_np = audio_np.squeeze()

            # Dia2 outputs at 44.1kHz
            print(f"   Audio shape: {audio_np.shape}")
            sf.write(str(output_path), audio_np, dia2.sample_rate)

            duration = audio.shape[-1] / dia2.sample_rate

            # Analysis
            CHARS_PER_SECOND = 15
            WORDS_PER_SECOND = 2.5

            expected_duration_chars = len(text) / CHARS_PER_SECOND
            expected_duration_words = text_words / WORDS_PER_SECOND
            expected_duration_avg = (expected_duration_chars + expected_duration_words) / 2

            completion_ratio = duration / expected_duration_avg if expected_duration_avg > 0 else 1.0
            chars_per_sec = len(text) / duration if duration > 0 else 0
            words_per_sec = text_words / duration if duration > 0 else 0

            print(f"\n📈 Results:")
            print(f"   Generated: {duration:.2f}s (in {generation_time:.1f}s real-time)")
            print(f"   Expected: {expected_duration_avg:.2f}s (based on avg speech rate)")
            print(f"   Completion: {completion_ratio*100:.1f}%")
            print(f"   Speed: {chars_per_sec:.1f} chars/sec, {words_per_sec:.1f} words/sec")

            if completion_ratio < 0.75:
                print(f"⚠️  WARNING: Possible clipping detected!")
            else:
                print(f"✓ Duration looks good")

            print(f"✓ Saved to {output_path}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*70}")
    print("✅ Test Complete")
    print(f"{'='*70}")
    print(f"\nOutput files saved to: {output_dir}")

if __name__ == "__main__":
    # Check device
    print(f"\n🖥️  Device Information:")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"   MPS available: {torch.backends.mps.is_available()}")

    main()
