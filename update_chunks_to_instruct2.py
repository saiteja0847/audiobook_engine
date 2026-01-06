"""
Update All Chunks to Use Instruct2
====================================

This script updates all chunks in all projects to use instruct2 as the default
inference method (if they don't already have a specific method set).
"""

import json
from pathlib import Path

def update_project_chunks(project_dir: Path):
    """Update all chunks in a project to use instruct2"""

    # Try both possible filenames
    chunks_file = project_dir / "chunked_book.json"
    if not chunks_file.exists():
        chunks_file = project_dir / "chunks.json"

    if not chunks_file.exists():
        print(f"  ⏭  No chunks file found in {project_dir.name}")
        return 0

    # Load chunks
    with open(chunks_file) as f:
        chunks = json.load(f)

    updated_count = 0

    # Update each chunk
    for chunk in chunks:
        # Add tts_config if missing
        if 'tts_config' not in chunk or chunk['tts_config'] is None:
            chunk['tts_config'] = {
                'provider': 'cosyvoice',
                'inference_method': 'instruct2',
                'speed': 1.0
            }
            updated_count += 1
        # Update existing tts_config
        elif 'inference_method' not in chunk['tts_config']:
            chunk['tts_config']['inference_method'] = 'instruct2'
            updated_count += 1
        # Update if not already instruct2
        elif chunk['tts_config']['inference_method'] != 'instruct2':
            chunk['tts_config']['inference_method'] = 'instruct2'
            updated_count += 1

    if updated_count > 0:
        # Save updated chunks
        with open(chunks_file, 'w') as f:
            json.dump(chunks, f, indent=2)

        print(f"  ✓ Updated {updated_count} chunks in {project_dir.name}")
    else:
        print(f"  ⏭  No updates needed in {project_dir.name}")

    return updated_count


def main():
    """Update all projects"""

    print("\n" + "=" * 70)
    print("Updating All Chunks to Use Instruct2")
    print("=" * 70)

    projects_dir = Path("projects")
    if not projects_dir.exists():
        print("\n❌ Projects directory not found!")
        return

    total_updated = 0

    # Process each project
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            print(f"\n📁 Processing: {project_dir.name}")
            updated = update_project_chunks(project_dir)
            total_updated += updated

    print("\n" + "=" * 70)
    print(f"✅ Complete! Updated {total_updated} chunks total")
    print("=" * 70)

    if total_updated > 0:
        print("\n💡 Refresh your browser to see the changes!")


if __name__ == "__main__":
    main()
