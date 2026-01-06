#!/usr/bin/env python3
"""
Test Working Script - Copy from audiobook-project-manager
Adapted to use audiobook_engine project structure
"""

import os
import sys
import json
from pathlib import Path
import warnings

# Suppress FutureWarnings about torch.cuda.amp.autocast
warnings.filterwarnings('ignore', category=FutureWarning)

# Set up paths
AUDIOBOOK_ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = AUDIOBOOK_ENGINE_DIR / "projects" / "fourth-wing"
COSYVOICE_PATH = AUDIOBOOK_ENGINE_DIR.parent / "CosyVoice"

# Add CosyVoice to path
sys.path.insert(0, str(COSYVOICE_PATH))
sys.path.insert(0, str(COSYVOICE_PATH / "third_party" / "Matcha-TTS"))

from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import torchaudio
import torch
import re
import time
import soundfile as sf

# Configuration
MODEL_PATH = COSYVOICE_PATH / "pretrained_models" / "CosyVoice2-0.5B"
AUDIO_SAMPLE_RATE = 22050

# CRITICAL: This must be the COMPLETE EXACT transcript of the seed audio!
# Using SHORT transcript causes gibberish output
STANDARD_SEED_TRANSCRIPT = """The morning sun cast long shadows across the ancient stone walls. She paused at the doorway, her heart pounding with anticipation. "Are you certain about this?" he asked, his voice barely a whisper. The answer came swiftly, without hesitation or doubt. In that moment, everything changed forever. Some journeys begin with a single step into the unknown. Others start with words spoken softly in the dark."""

# Test with first chunk only
CHUNK_ID = 1

def main():
    print("=" * 70)
    print("Testing Working Script with Audiobook Engine Data")
    print("=" * 70)

    # Load chunks
    chunks_path = PROJECT_DIR / "chunked_book.json"
    print(f"\nLoading chunks from: {chunks_path}")

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

    # Get prompt text
    prompt_text = seed_data.get("prompt_text") or seed_data.get("transcript") or STANDARD_SEED_TRANSCRIPT
    print(f"  Prompt: {prompt_text[:80]}...")

    # Load seed audio
    voice_seed = load_wav(str(seed_audio_path), 16000)
    print(f"✓ Loaded seed audio")

    # Clean text - strip non-working emotion tags
    has_working_tags = bool(re.search(r'\[(breath|sigh)\]', text, re.IGNORECASE))
    text_clean = re.sub(
        r'\[(whisper|mutter|shout|softly|snap|click|gasp|laugh|laughter|giggle|cough|sniff|sob|cry|scream|yawn|thunder|murmur|frustrated|ominous)\]',
        '',
        text,
        flags=re.IGNORECASE
    ).strip()

    print(f"\nCleaned text: {text_clean[:100]}...")
    print(f"Has working tags: {has_working_tags}")

    # Initialize CosyVoice
    print("\nLoading CosyVoice model...")
    # Check device
    print(f"  CUDA available: {torch.cuda.is_available()}")

    cosyvoice = CosyVoice2(str(MODEL_PATH), load_jit=False, load_trt=False, load_vllm=False, fp16=False)
    print(f"✓ Model loaded")

    # Create output directory
    output_dir = AUDIOBOOK_ENGINE_DIR / "test_output"
    output_dir.mkdir(exist_ok=True)

    # Test both inference methods
    methods = ['zero-shot', 'cross-lingual']

    for method in methods:
        print(f"\n{'='*70}")
        print(f"Testing {method} method")
        print(f"{'='*70}")

        try:
            # Detailed logging
            text_words = len(text_clean.split())
            prompt_words = len(prompt_text.split())
            text_ratio = len(text_clean) / len(prompt_text) if len(prompt_text) > 0 else 0

            print(f"\n📊 Generation Analysis:")
            print(f"   Text: {len(text_clean)} chars, {text_words} words")
            print(f"   Prompt: {len(prompt_text)} chars, {prompt_words} words")
            print(f"   Ratio: {text_ratio:.2%} (text/prompt)")

            generation_start = time.time()

            if method == 'cross-lingual':
                print(f"→ Using cross-lingual")
                for output in cosyvoice.inference_cross_lingual(text_clean, voice_seed, stream=False):
                    audio = output['tts_speech']
                    break
            else:
                print(f"→ Using zero-shot")
                for output in cosyvoice.inference_zero_shot(text_clean, prompt_text, voice_seed, stream=False, text_frontend=False):
                    audio = output['tts_speech']
                    break

            generation_time = time.time() - generation_start

            # Save using soundfile (avoid torchcodec dependency)
            output_path = output_dir / f"chunk_{chunk_id:04d}_{method}.wav"
            audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
            # Ensure proper shape for soundfile (samples,) or (samples, channels)
            if audio_np.ndim > 1:
                audio_np = audio_np.T if audio_np.shape[0] < audio_np.shape[1] else audio_np
            sf.write(str(output_path), audio_np, cosyvoice.sample_rate)
            duration = audio.shape[-1] / cosyvoice.sample_rate

            # Analysis
            CHARS_PER_SECOND = 15
            WORDS_PER_SECOND = 2.5

            expected_duration_chars = len(text_clean) / CHARS_PER_SECOND
            expected_duration_words = text_words / WORDS_PER_SECOND
            expected_duration_avg = (expected_duration_chars + expected_duration_words) / 2

            completion_ratio = duration / expected_duration_avg if expected_duration_avg > 0 else 1.0
            chars_per_sec = len(text_clean) / duration if duration > 0 else 0
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
    # Set OpenMP environment variable
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    main()
