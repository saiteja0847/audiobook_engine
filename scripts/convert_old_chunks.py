"""
Convert Old Chunks Format to New Format
=========================================

Converts chunks from old audiobook-project-manager format to new audiobook_engine format.
Adds TTS configuration with default provider (cosyvoice) for testing.
"""

import json
import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def convert_chunks(old_chunks_path: Path, output_path: Path, default_provider: str = "cosyvoice"):
    """
    Convert old chunks format to new format.

    Old format:
    {
      "chunk_id": 1,
      "text": "...",
      "speaker": "NARRATOR",
      "type": "narration",
      "emotion": "ominous",
      "start_paragraph": 1,
      "end_paragraph": 1
    }

    New format:
    {
      "chunk_id": 1,
      "text": "...",
      "speaker": "NARRATOR",
      "tts_config": {
        "provider": "cosyvoice",
        "inference_method": "zero-shot"
      },
      "audio_effects": [],
      "metadata": {
        "type": "narration",
        "emotion": "ominous",
        "start_paragraph": 1,
        "end_paragraph": 1
      }
    }
    """

    print(f"Loading chunks from: {old_chunks_path}")

    with open(old_chunks_path, 'r') as f:
        data = json.load(f)

    # Handle both formats: {"original_chunks": [...]} or [...]
    if isinstance(data, dict) and "original_chunks" in data:
        old_chunks = data["original_chunks"]
    else:
        old_chunks = data

    print(f"Found {len(old_chunks)} chunks")

    new_chunks = []

    for chunk in old_chunks:
        new_chunk = {
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "speaker": chunk["speaker"],
            "tts_config": {
                "provider": default_provider,
                "inference_method": "zero-shot" if default_provider == "cosyvoice" else "default"
            },
            "audio_effects": [],
            "metadata": {
                "type": chunk.get("type", "narration"),
                "emotion": chunk.get("emotion", "neutral"),
                "start_paragraph": chunk.get("start_paragraph", 0),
                "end_paragraph": chunk.get("end_paragraph", 0)
            }
        }

        new_chunks.append(new_chunk)

    # Save converted chunks
    print(f"Saving {len(new_chunks)} converted chunks to: {output_path}")

    with open(output_path, 'w') as f:
        json.dump(new_chunks, f, indent=2)

    print("✓ Conversion complete!")

    return new_chunks


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_old_chunks.py <old_chunks.json> <output.json> [provider]")
        print("Example: python convert_old_chunks.py old/chunked_book.json new/chunked_book.json cosyvoice")
        sys.exit(1)

    old_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    provider = sys.argv[3] if len(sys.argv) > 3 else "cosyvoice"

    if not old_path.exists():
        print(f"Error: Input file not found: {old_path}")
        sys.exit(1)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    convert_chunks(old_path, output_path, provider)
