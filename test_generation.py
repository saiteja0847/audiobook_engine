"""
Test TTS Generation
===================

Test audio generation for a single chunk with different providers.
Carefully manages memory by loading/unloading models one at a time.
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
        return

    # Get emotion
    emotion = chunk.metadata.get('emotion', 'neutral') if chunk.metadata else 'neutral'

    # Test each inference method
    methods = ['zero-shot', 'cross-lingual']

    for method in methods:
        print(f"\n--- Testing {method} ---")

        try:
            # Prepare text with emotion
            text = chunk.text
            if emotion and emotion != 'neutral':
                text = f"[{emotion}] {chunk.text}"
                print(f"  Text with emotion: {text[:60]}...")

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

            # Save audio
            output_file = TEST_OUTPUT_DIR / f"chunk_{CHUNK_ID}_cosyvoice_{method}.wav"
            audio_2d = audio.unsqueeze(0) if audio.dim() == 1 else audio
            torchaudio.save(str(output_file), audio_2d, AUDIO_SAMPLE_RATE)

            duration = audio.shape[-1] / AUDIO_SAMPLE_RATE
            print(f"  ✓ Generated {duration:.2f}s audio")
            print(f"  ✓ Saved: {output_file.name}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

    # Clear memory before next provider
    print("\n  Clearing CosyVoice from memory...")
    del provider
    ProviderRegistry._tts_providers.clear()
    clear_memory()


def test_dia2(chunk, seed, seed_audio_path):
    """Test Dia2 generation"""
    print("\n" + "="*60)
    print("Testing Dia2")
    print("="*60)

    # Register provider
    try:
        from engine.providers.tts.dia2 import Dia2Provider
        ProviderRegistry.register_tts(Dia2Provider)
        provider = ProviderRegistry.get_tts('dia2')
        print("✓ Dia2 provider registered")
    except Exception as e:
        print(f"❌ Failed to load Dia2: {e}")
        return

    # Test each inference method
    methods = ['default', 'high_quality']  # Skip 'fast' for now

    for method in methods:
        print(f"\n--- Testing {method} ---")

        try:
            # Generate audio
            print(f"  Generating audio...")
            audio = provider.generate_audio(
                text=chunk.text,
                voice_seed_path=seed_audio_path,
                prompt_text=None,  # Dia2 doesn't use prompt text
                inference_method=method
            )

            if audio is None or audio.numel() == 0:
                print(f"  ❌ No audio generated")
                continue

            # Dia2 outputs at 44.1kHz, resample to 22.05kHz for consistency
            if provider.sample_rate != AUDIO_SAMPLE_RATE:
                print(f"  Resampling from {provider.sample_rate}Hz to {AUDIO_SAMPLE_RATE}Hz...")
                resampler = torchaudio.transforms.Resample(provider.sample_rate, AUDIO_SAMPLE_RATE)
                audio = resampler(audio)

            # Save audio
            output_file = TEST_OUTPUT_DIR / f"chunk_{CHUNK_ID}_dia2_{method}.wav"
            audio_2d = audio.unsqueeze(0) if audio.dim() == 1 else audio
            torchaudio.save(str(output_file), audio_2d, AUDIO_SAMPLE_RATE)

            duration = audio.shape[-1] / AUDIO_SAMPLE_RATE
            print(f"  ✓ Generated {duration:.2f}s audio")
            print(f"  ✓ Saved: {output_file.name}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

    # Clear memory
    print("\n  Clearing Dia2 from memory...")
    del provider
    ProviderRegistry._tts_providers.clear()
    clear_memory()


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TTS Generation Test")
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

        # Test Dia2
        test_dia2(chunk, seed, seed_audio_path)

        print("\n" + "="*60)
        print("Test Complete!")
        print("="*60)
        print(f"Check audio files in: {TEST_OUTPUT_DIR}")
        print("\nGenerated files:")
        for audio_file in sorted(TEST_OUTPUT_DIR.glob("chunk_*.wav")):
            print(f"  - {audio_file.name}")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
