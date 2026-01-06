"""
Convert Old Seed Audio Format to New Format
============================================

Converts voice seeds from old audiobook-project-manager format to new audiobook_engine format.
Copies audio files and creates seed.json for each speaker.
"""

import json
import shutil
import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def convert_seeds(old_seeds_dir: Path, seed_manifest_path: Path, new_seeds_dir: Path):
    """
    Convert old seed format to new format.

    Old structure:
    voice_seeds/
    ├── violet_sorrengail_seed.mp3
    ├── xaden_riorson_seed.mp3
    └── seed_manifest.json

    New structure:
    seeds/
    ├── NARRATOR/
    │   ├── seed.json
    │   └── seed.wav
    ├── Violet Sorrengail/
    │   ├── seed.json
    │   └── seed.wav
    """

    print(f"Loading seed manifest from: {seed_manifest_path}")

    with open(seed_manifest_path, 'r') as f:
        seed_manifest = json.load(f)

    print(f"Found {len(seed_manifest)} voice seeds")

    for seed_info in seed_manifest:
        character_name = seed_info["character_name"]
        seed_file = seed_info["seed_file"]
        transcript = seed_info.get("transcript", "")

        # Create speaker directory
        speaker_dir = new_seeds_dir / character_name
        speaker_dir.mkdir(parents=True, exist_ok=True)

        # Copy audio file
        old_audio_path = old_seeds_dir.parent / seed_file

        # Determine new audio extension (convert to wav if needed)
        new_audio_path = speaker_dir / "seed.mp3"  # Keep as mp3 for now

        if old_audio_path.exists():
            print(f"  Copying {character_name}: {old_audio_path.name} -> {new_audio_path.name}")
            shutil.copy2(old_audio_path, new_audio_path)
        else:
            print(f"  ⚠ Warning: Audio file not found: {old_audio_path}")
            continue

        # Create seed.json
        seed_json = {
            "speaker": character_name,
            "prompt_text": transcript,
            "audio_path": "seed.mp3",
            "metadata": {
                "voice_source": seed_info.get("voice_source", "elevenlabs"),
                "elevenlabs_voice_id": seed_info.get("elevenlabs_voice_id"),
                "elevenlabs_voice_name": seed_info.get("elevenlabs_voice_name"),
                "duration_seconds": seed_info.get("duration_seconds")
            }
        }

        seed_json_path = speaker_dir / "seed.json"
        print(f"  Creating {seed_json_path.relative_to(new_seeds_dir.parent)}")

        with open(seed_json_path, 'w') as f:
            json.dump(seed_json, f, indent=2)

    print("\n✓ Seed conversion complete!")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python convert_seeds.py <old_seeds_dir> <seed_manifest.json> <new_seeds_dir>")
        print("Example: python convert_seeds.py old/voice_seeds old/voice_seeds/seed_manifest.json new/seeds")
        sys.exit(1)

    old_seeds_dir = Path(sys.argv[1])
    seed_manifest = Path(sys.argv[2])
    new_seeds_dir = Path(sys.argv[3])

    if not old_seeds_dir.exists():
        print(f"Error: Old seeds directory not found: {old_seeds_dir}")
        sys.exit(1)

    if not seed_manifest.exists():
        print(f"Error: Seed manifest not found: {seed_manifest}")
        sys.exit(1)

    # Create new seeds directory
    new_seeds_dir.mkdir(parents=True, exist_ok=True)

    convert_seeds(old_seeds_dir, seed_manifest, new_seeds_dir)
