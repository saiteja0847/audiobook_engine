"""
Test CosyVoice Generation Only
===============================

Test audio generation for a single chunk with CosyVoice provider.
"""

import sys
from pathlib import Path
import json
import gc

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent))

import torch
import torchaudio

from engine.models import Chunk, VoiceSeed
from engine.providers.registry import ProviderRegistry
from engine.config import PROJECTS_DIR, AUDIO_SAMPLE_RATE

# Configuration
PROJECT_SLUG = "fourth-wing"
CHUNK_ID = 1  # Test with first chunk
TEST_OUTPUT_DIR = Path(__file__).parent / "test_outputs"


def clear_memory():
    """Clear GPU/CPU memory"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        torch.mps.empty_cache()
    gc.collect()
    print("  ✓ Memory cleared")


def load_test_data():
    """Load the test chunk and voice seed"""
    print("\n" + "="*60)
    print("Loading Test Data")
    print("="*60)

    project_dir = PROJECTS_DIR / PROJECT_SLUG

    # Load chunk
    chunks_path = project_dir / "chunked_book.json"
    with open(chunks_path) as f:
        chunks_data = json.load(f)

    chunk_data = chunks_data[CHUNK_ID - 1]  # Get first chunk
    chunk = Chunk.from_dict(chunk_data)

    print(f"✓ Loaded chunk {chunk.id}")
    print(f"  Text: {chunk.text[:80]}...")
    print(f"  Speaker: {chunk.speaker}")
    print(f"  Emotion: {chunk.metadata.get('emotion', 'neutral')}")

    # Load voice seed
    seeds_dir = project_dir / "seeds"
    seed_json = seeds_dir / chunk.speaker / "seed.json"

    if not seed_json.exists():
        raise FileNotFoundError(f"Seed not found for {chunk.speaker}")

    with open(seed_json) as f:
        seed_data = json.load(f)

    seed = VoiceSeed.from_dict(seed_data)
    seed_audio_path = seeds_dir / chunk.speaker / seed.audio_file

    if not seed_audio_path.exists():
        raise FileNotFoundError(f"Seed audio not found: {seed_audio_path}")

    print(f"✓ Loaded voice seed for {chunk.speaker}")
    print(f"  Audio: {seed_audio_path.name}")
    print(f"  Prompt: {seed.prompt_text[:60]}...")

    return chunk, seed, seed_audio_path


def test_cosyvoice(chunk, seed, seed_audio_path):
    """Test CosyVoice generation"""
    print("\n" + "="*60)
    print("Testing CosyVoice")
    print("="*60)

    # Register provider
    try:
        from engine.providers.tts.cosyvoice import CosyVoiceProvider
        ProviderRegistry.register_tts(CosyVoiceProvider)
        provider = ProviderRegistry.get_tts('cosyvoice')
        print("✓ CosyVoice provider registered")
    except Exception as e:
        print(f"❌ Failed to load CosyVoice: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get emotion
    emotion = chunk.metadata.get('emotion', 'neutral') if chunk.metadata else 'neutral'

    # Clean text - remove non-working emotion tags like the working script does
    # Only [breath] and [sigh] work in CosyVoice
    import re
    text_clean = re.sub(
        r'\[(whisper|mutter|shout|softly|snap|click|gasp|laugh|laughter|giggle|cough|sniff|sob|cry|scream|yawn|thunder|murmur|frustrated|ominous)\]',
        '',
        chunk.text,
        flags=re.IGNORECASE
    ).strip()

    # Test each inference method
    methods = ['zero-shot', 'cross-lingual']

    for method in methods:
        print(f"\n--- Testing {method} ---")

        try:
            text = text_clean
            print(f"  Text (cleaned): {text[:60]}...")

            # Generate audio
            print(f"  Generating audio...")
            audio = provider.generate_audio(
                text=text,
                voice_seed_path=seed_audio_path,
                prompt_text=seed.prompt_text,
                inference_method=method
            )

            if audio is None or audio.numel() == 0:
                print(f"  ❌ No audio generated")
                continue

            # Save audio using soundfile (avoid torchcodec dependency)
            output_file = TEST_OUTPUT_DIR / f"chunk_{CHUNK_ID}_cosyvoice_{method}.wav"
            import soundfile as sf
            import numpy as np
            audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
            sf.write(str(output_file), audio_np.T if audio_np.ndim > 1 else audio_np, AUDIO_SAMPLE_RATE)

            duration = audio.shape[-1] / AUDIO_SAMPLE_RATE
            print(f"  ✓ Generated {duration:.2f}s audio")
            print(f"  ✓ Saved: {output_file.name}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

    # Clear memory
    print("\n  Clearing CosyVoice from memory...")
    del provider
    ProviderRegistry._tts_providers.clear()
    clear_memory()


def main():
    """Run CosyVoice tests"""
    print("\n" + "="*60)
    print("CosyVoice Generation Test")
    print("="*60)
    print(f"Project: {PROJECT_SLUG}")
    print(f"Chunk ID: {CHUNK_ID}")
    print(f"Output: {TEST_OUTPUT_DIR}")

    # Create output directory
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Load test data
        chunk, seed, seed_audio_path = load_test_data()

        # Test CosyVoice
        test_cosyvoice(chunk, seed, seed_audio_path)

        print("\n" + "="*60)
        print("Test Complete!")
        print("="*60)
        print(f"Check audio files in: {TEST_OUTPUT_DIR}")
        print("\nGenerated files:")
        for audio_file in sorted(TEST_OUTPUT_DIR.glob("chunk_*_cosyvoice_*.wav")):
            print(f"  - {audio_file.name}")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
