# Audiobook Engine Prompts

This directory contains versioned prompts for the two-phase audiobook generation system.

## Directory Structure

```
prompts/
├── phase1/                          # Character Registry Generation (Gemini)
│   ├── system_prompt_v1.txt        # System/role definition
│   ├── task_character_registry_v1.txt  # Task-specific instructions
│   ├── TESTING_combined_prompt.txt # Combined prompt for manual testing
│   └── examples/
│       └── registry_example.json   # Expected output format
├── phase2/                          # Scene Direction (Claude) - Coming Soon
│   ├── system_prompt_v1.txt
│   ├── task_scene_direction_v1.txt
│   └── examples/
│       └── toon_example.txt
└── template_variables.json         # Variable definitions

```

## Phase 1: Character Registry

**Purpose**: Analyze book chapters to create a character registry with AI-optimized voice descriptions.

**Model**: Gemini 1.5 Pro (recommended)

**Input**: Book chapter(s) text

**Output**: JSON character registry with voice seed prompts

### Testing Phase 1 Manually

1. Open `phase1/TESTING_combined_prompt.txt`
2. Replace placeholders:
   - `[REPLACE WITH YOUR BOOK TITLE]`
   - `[REPLACE WITH GENRE]`
   - `[REPLACE WITH CHAPTER RANGE]`
3. Paste 1-2 chapters of your book at the end
4. Copy entire content to Gemini AI Studio
5. Verify output matches `examples/registry_example.json` format

### Key Requirements for Voice Seed Prompts

✅ **Good Examples:**
- "Young adult American female, alto range, breathy texture with high clarity. Quick intelligent speech."
- "Middle-aged male, deep baritone, British RP accent, commanding presence, measured pacing."

❌ **Bad Examples:**
- "High Navarrian accent" (fantasy term)
- "Sounds like a dragon rider" (not grounded in reality)
- "Voice of command" (too vague)

### Template Variables

Replace these in prompts before API calls:

- `{{BOOK_TITLE}}`: "Fourth Wing"
- `{{GENRE}}`: "Fantasy"
- `{{CHAPTER_RANGE}}`: "Chapters 1-5"
- `{{MODEL_NAME}}`: "gemini-1.5-pro"

## Phase 2: Scene Direction (Coming Soon)

**Purpose**: Convert book segments into TOON-formatted chunks with emotion/audio cues.

**Model**: Claude 3.5 Sonnet (recommended)

**Input**:
- Character registry (from Phase 1)
- Book segment (700-800 words)
- Context (100 words from previous)

**Output**: TOON-formatted chunks with metadata

## Version History

### v1.0 (2025-01-04)
- Initial prompts created
- Phase 1 complete with examples
- Phase 2 structure defined

## Usage in Scripts

See `scripts/phase1_character_registry.py` for automated implementation.

```python
from utils.prompt_loader import load_prompt

# Load and populate template
system_prompt = load_prompt('phase1/system_prompt_v1.txt')
task_prompt = load_prompt('phase1/task_character_registry_v1.txt', {
    'BOOK_TITLE': 'Fourth Wing',
    'GENRE': 'Fantasy',
    'CHAPTER_RANGE': 'Chapters 1-3'
})
```

## Testing Checklist

Before running Phase 1 on full book:

- [ ] Test on 1-2 chapters manually
- [ ] Verify JSON output format
- [ ] Check voice_seed_prompt quality (real-world terms only)
- [ ] Confirm dialogue_count accuracy
- [ ] Validate vocal_characteristics completeness
- [ ] Review character aliases coverage

## Notes

- Always use versioned prompts (v1, v2, etc.)
- Keep examples up-to-date with latest schema
- Document any prompt changes in version history
- Test new prompts on small samples before full runs
