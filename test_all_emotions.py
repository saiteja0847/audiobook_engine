#!/usr/bin/env python3
"""
Test All Emotions
=================

Extract all unique emotions from chunks and generate test audio for each.
This helps verify how different emotions sound with the current settings.
"""

import json
import sys
from pathlib import Path
from collections import Counter

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent))

import torch
import torchaudio

from engine.models import Chunk, VoiceSeed
from engine.providers.registry import ProviderRegistry
from engine.config import PROJECTS_DIR

# Test sentence (medium length, neutral content)
TEST_SENTENCE = "The dragon circled overhead as the candidates gathered in the courtyard below."

def initialize_providers():
    """Initialize TTS providers."""
    try:
        from engine.providers.tts.cosyvoice import CosyVoiceProvider
        ProviderRegistry.register_tts(CosyVoiceProvider)
        print("✓ Registered CosyVoice provider")
    except Exception as e:
        print(f"❌ Error registering CosyVoice provider: {e}")
        raise

def get_unique_emotions(project_slug: str):
    """Extract all unique emotions from chunks"""
    project_dir = PROJECTS_DIR / project_slug
    chunks_file = project_dir / "chunked_book.json"

    with open(chunks_file) as f:
        chunks = json.load(f)

    # Get emotions from metadata and emotion_prompt
    emotions = set()
    emotion_counts = Counter()

    for chunk in chunks:
        # From metadata
        if chunk.get('metadata') and chunk['metadata'].get('emotion'):
            emotion = chunk['metadata']['emotion']
            emotions.add(emotion)
            emotion_counts[emotion] += 1

        # From emotion_prompt
        if chunk.get('emotion_prompt'):
            emotion = chunk['emotion_prompt']
            emotions.add(emotion)
            emotion_counts[emotion] += 1

    return sorted(emotions), emotion_counts

def generate_emotion_test(project_slug: str, output_dir: Path):
    """Generate test audio for all emotions"""

    # Get unique emotions
    emotions, emotion_counts = get_unique_emotions(project_slug)

    print("=" * 70)
    print(f"Found {len(emotions)} unique emotions")
    print("=" * 70)

    for emotion, count in sorted(emotion_counts.items(), key=lambda x: -x[1]):
        print(f"  {emotion}: {count} occurrences")

    print("\n" + "=" * 70)
    print("Generating test audio for each emotion")
    print("=" * 70)
    print(f"Test sentence: \"{TEST_SENTENCE}\"")
    print()

    # Load NARRATOR seed
    project_dir = PROJECTS_DIR / project_slug
    narrator_seed_dir = project_dir / "seeds" / "NARRATOR"

    if not narrator_seed_dir.exists():
        print(f"❌ NARRATOR seed not found at {narrator_seed_dir}")
        return

    # Check for seed.json
    seed_json = narrator_seed_dir / "seed.json"
    if seed_json.exists():
        # Load from JSON
        with open(seed_json) as f:
            seed_data = json.load(f)
        voice_seed = VoiceSeed.from_dict(seed_data)
        print(f"Using seed: {voice_seed.audio_file}\n")
    else:
        # Fallback: create minimal seed from first wav file
        seed_files = list(narrator_seed_dir.glob("*.wav"))
        if not seed_files:
            print(f"❌ No seed audio files found in {narrator_seed_dir}")
            return

        seed_path = seed_files[0]
        print(f"Using seed: {seed_path.name}\n")

        voice_seed = VoiceSeed(
            character_name="NARRATOR",
            description="Narrator voice",
            audio_file=seed_path.name,
            prompt_text="Sample text for voice seed"
        )

    # Initialize TTS provider
    provider = ProviderRegistry.get_tts("cosyvoice")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate audio for each emotion
    successful = 0
    failed = 0

    for i, emotion in enumerate(emotions, 1):
        print(f"[{i}/{len(emotions)}] Generating: {emotion}")

        try:
            # Get voice seed path
            seed_audio_path = narrator_seed_dir / voice_seed.audio_file

            # Generate audio with emotion prompt
            audio_data = provider.generate_audio(
                text=TEST_SENTENCE,
                voice_seed_path=seed_audio_path,
                prompt_text=voice_seed.prompt_text,
                inference_method="instruct2",
                emotion_prompt=emotion
            )

            # Save
            output_file = output_dir / f"{i:02d}_{emotion.replace(' ', '_')}.wav"

            # Ensure audio is 2D (channels, samples)
            if audio_data.dim() == 1:
                audio_data = audio_data.unsqueeze(0)

            torchaudio.save(
                str(output_file),
                audio_data,
                provider.sample_rate
            )

            duration = len(audio_data) / provider.sample_rate
            print(f"  ✓ Saved: {output_file.name} ({duration:.1f}s)")
            successful += 1

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total emotions: {len(emotions)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nOutput directory: {output_dir.absolute()}")
    print("=" * 70)

def main():
    import argparse

    # Initialize providers first
    initialize_providers()

    parser = argparse.ArgumentParser(description='Test all emotions with sample audio')
    parser.add_argument('--project', default='fourth-wing', help='Project slug')
    parser.add_argument('--output', default='emotion_tests', help='Output directory name')
    args = parser.parse_args()

    output_dir = PROJECTS_DIR / args.project / args.output

    generate_emotion_test(args.project, output_dir)

if __name__ == "__main__":
    main()
