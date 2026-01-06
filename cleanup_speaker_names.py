#!/usr/bin/env python3
"""
Cleanup Speaker Names in Chunks
================================

This script:
1. Fixes character names to match seed folder names
2. Sets fallback to NARRATOR for characters without seeds
"""

import json
from pathlib import Path
from collections import Counter

# Paths
PROJECTS_DIR = Path(__file__).parent / "projects"

def get_available_seeds(project_dir: Path):
    """Get list of available seed folders"""
    seeds_dir = project_dir / "seeds"
    if not seeds_dir.exists():
        return []

    return [d.name for d in seeds_dir.iterdir() if d.is_dir()]

def cleanup_project_speakers(project_dir: Path):
    """Cleanup speaker names in a project"""

    # Load chunks
    chunks_file = project_dir / "chunked_book.json"
    if not chunks_file.exists():
        print(f"  ⏭  No chunked_book.json found in {project_dir.name}")
        return

    with open(chunks_file) as f:
        chunks = json.load(f)

    # Get available seeds
    available_seeds = get_available_seeds(project_dir)
    print(f"\n📁 Available seeds: {', '.join(available_seeds)}")

    # Character name mappings (short name -> full name)
    name_mappings = {
        "Violet": "Violet Sorrengail",
        "Mira": "Mira Sorrengail",
        "Xaden": "Xaden Riorson",
        "Rhiannon": "Rhiannon Matthias",
        "General Sorrengail": "General Sorrengail",
        "NARRATOR": "NARRATOR"
    }

    # Track changes
    original_speakers = Counter()
    updated_speakers = Counter()
    fallback_count = 0

    for chunk in chunks:
        original_speaker = chunk['speaker']
        original_speakers[original_speaker] += 1

        # Apply name mapping if exists
        mapped_name = name_mappings.get(original_speaker, original_speaker)

        # Check if seed exists
        if mapped_name not in available_seeds:
            # Fallback to NARRATOR for characters without seeds
            if mapped_name != "NARRATOR":
                print(f"  ⚠️  No seed for '{mapped_name}' -> using NARRATOR as fallback")
                chunk['speaker'] = "NARRATOR"
                fallback_count += 1
            else:
                chunk['speaker'] = mapped_name
        else:
            chunk['speaker'] = mapped_name

        updated_speakers[chunk['speaker']] += 1

    # Save updated chunks
    with open(chunks_file, 'w') as f:
        json.dump(chunks, f, indent=2)

    # Print summary
    print(f"\n📊 Summary:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Fallback to NARRATOR: {fallback_count}")

    print(f"\n📋 Original speaker distribution:")
    for speaker, count in sorted(original_speakers.items()):
        print(f"    {speaker}: {count}")

    print(f"\n📋 Updated speaker distribution:")
    for speaker, count in sorted(updated_speakers.items()):
        print(f"    {speaker}: {count}")

def main():
    print("=" * 70)
    print("Cleanup Speaker Names")
    print("=" * 70)

    if not PROJECTS_DIR.exists():
        print(f"❌ Projects directory not found: {PROJECTS_DIR}")
        return

    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        print(f"\n📁 Processing: {project_dir.name}")
        cleanup_project_speakers(project_dir)

    print("\n" + "=" * 70)
    print("✅ Complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
