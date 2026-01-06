# Generation Scripts

Audio generation scripts for the audiobook engine.

## generate_audiobook.py

Main script for generating audiobook audio from chunks.

### Features

- **Multi-Provider TTS**: Per-chunk TTS provider selection (CosyVoice, Chatterbox, etc.)
- **Audio Effects**: Apply reverb, speed, volume adjustments per chunk
- **Clipping Detection**: Warns about incomplete audio generation
- **Resume Support**: Skip already-generated chunks
- **Detailed Logging**: Statistics, warnings, and progress tracking

### Usage

```bash
# Generate all chunks for a project
python scripts/generate_audiobook.py --project PROJECT_SLUG

# Force regenerate all chunks
python scripts/generate_audiobook.py --project PROJECT_SLUG --force

# Generate specific chunk range (1-indexed)
python scripts/generate_audiobook.py --project PROJECT_SLUG --start 10 --end 20

# Dry run (see what would be generated)
python scripts/generate_audiobook.py --project PROJECT_SLUG --dry-run
```

### Requirements

**Project Structure**:
```
projects/
└── PROJECT_SLUG/
    ├── chunked_book.json      # Required: Chunk data
    ├── project.json           # Optional: Project metadata
    ├── seeds/                 # Required: Voice seeds
    │   └── CHARACTER_NAME/
    │       ├── seed.json      # Seed metadata
    │       └── seed.wav       # Seed audio
    └── audio/                 # Output: Generated audio
        ├── chunk_1.wav
        ├── chunk_2.wav
        └── ...
```

**chunked_book.json Format**:
```json
[
  {
    "chunk_id": 1,
    "text": "This is a narration chunk.",
    "speaker": "NARRATOR",
    "emotion": "neutral",
    "type": "narration"
  },
  {
    "chunk_id": 2,
    "text": "This is internal monologue with effects.",
    "speaker": "VIOLET",
    "emotion": "thoughtful",
    "type": "internal_monologue",
    "tts_config": {
      "provider": "cosyvoice",
      "inference_method": "zero-shot",
      "speed": 1.1
    },
    "audio_effects": [
      {"type": "reverb", "params": {"intensity": 0.3}},
      {"type": "speed", "params": {"speed": 1.1}}
    ]
  }
]
```

**seed.json Format**:
```json
{
  "character_name": "NARRATOR",
  "description": "Male narrator voice, calm and clear",
  "gender": "male",
  "age": "adult",
  "audio_file": "seed.wav",
  "prompt_text": "This is the transcription of the seed audio."
}
```

### Output

Generated audio files are saved as:
- `projects/PROJECT_SLUG/audio/chunk_N.wav`
- WAV format, 22050 Hz sample rate, mono

### Logging

The script provides detailed logging:

```
============================================================
Loading Project: my-audiobook
============================================================
✓ Project: My Audiobook
✓ Loaded 50 chunks
✓ Loaded 3 voice seeds: ['NARRATOR', 'VIOLET', 'XADEN']
✓ Audio directory: projects/my-audiobook/audio

============================================================
Generating Audio Chunks
============================================================

  🎙️  Generating Chunk 1...
      Text: This is the first chunk of narration...
      Speaker: NARRATOR
      Provider: cosyvoice (zero-shot)
      ✓ Generated: 5.2s audio in 2.1s
      ✓ Saved: chunk_1.wav

  🎙️  Generating Chunk 2...
      Text: Violet's internal thoughts with reverb effect...
      Speaker: VIOLET
      Provider: cosyvoice (zero-shot)
      Applying 2 effects...
      ⚠️  Chunk 2: Possible clipping detected!
      Completion: 68.5% (expected ~100%)
      ✓ Generated: 3.8s audio in 1.9s
      ✓ Saved: chunk_2.wav

============================================================
Generation Summary
============================================================
Total chunks:       50
Generated:          45 ✓
Skipped:            5
Failed:             0
Clipping warnings:  2 ⚠️

Total audio:        245.6s (4.1m)
Generation time:    98.2s (1.6m)
Avg time/chunk:     2.18s
============================================================
```

### Warnings

**⚠️ Clipping Warnings**:
- Generated when audio appears incomplete
- Caused by TTS model cutting off text
- Check inference method (zero-shot vs cross-lingual)
- Adjust text/prompt ratio

**⚠️ Failed Chunks**:
- Missing voice seeds
- TTS provider errors
- Invalid chunk configuration

### Tips

1. **Resume Generation**: Don't use `--force` to resume interrupted generation
2. **Test First**: Use `--dry-run` to verify project structure
3. **Chunk Ranges**: Generate problematic chunks individually with `--start N --end N`
4. **Effects**: Add effects in `chunked_book.json` before generation

### Examples

```bash
# Generate full audiobook
python scripts/generate_audiobook.py --project fourth-wing

# Fix chunk 15 that had clipping
python scripts/generate_audiobook.py --project fourth-wing --start 15 --end 15 --force

# Generate chapters 5-8 (chunks 100-200)
python scripts/generate_audiobook.py --project fourth-wing --start 100 --end 200

# Test run
python scripts/generate_audiobook.py --project fourth-wing --dry-run
```

## Future Scripts

- `merge_audiobook.py` - Merge all chunks into final audiobook
- `validate_project.py` - Validate project structure and data
- `compare_methods.py` - Compare TTS methods side-by-side
