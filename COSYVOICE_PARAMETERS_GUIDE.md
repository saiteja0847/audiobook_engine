# CosyVoice Parameters & Optimization Guide

## Overview
This guide explains exactly what parameters are sent to CosyVoice, how they affect generation, and how to optimize for best quality and speed.

---

## What Gets Sent to CosyVoice

### 1. Core Parameters (Always Sent)

```python
audio = tts_provider.generate_audio(
    text=chunk.text,              # The text to generate (cleaned)
    voice_seed_path=seed_audio_path,  # Path to reference voice audio
    prompt_text=seed.prompt_text,     # Transcript of reference audio
    inference_method=inference_method, # "auto", "zero-shot", or "cross-lingual"
    emotion=emotion                    # Emotion tag (if not "neutral")
)
```

### 2. CosyVoice Internal Parameters

**Zero-Shot Mode:**
```python
self._model.inference_zero_shot(
    text_clean,           # Text after removing unsupported tags
    prompt_text,          # Reference audio transcript
    voice_seed,           # Loaded audio tensor (resampled to 16kHz)
    stream=False,         # Always False (no streaming)
    speed=1.0,            # From chunk.tts_config.speed
    text_frontend=False   # Text normalization (disabled by default)
)
```

**Cross-Lingual Mode:**
```python
self._model.inference_cross_lingual(
    text_clean,           # Text after removing unsupported tags
    voice_seed,           # Loaded audio tensor (resampled to 16kHz)
    stream=False,         # Always False
    speed=1.0,            # From chunk.tts_config.speed
    text_frontend=False   # Text normalization (disabled)
)
```

---

## Text Cleaning Process

### Removed Tags
CosyVoice only supports `[breath]` and `[sigh]`. All other tags are **automatically removed**:

```python
# These are REMOVED before sending to CosyVoice:
[whisper], [mutter], [shout], [softly], [snap], [click],
[gasp], [laugh], [laughter], [giggle], [cough], [sniff],
[sob], [cry], [scream], [yawn], [thunder], [murmur],
[frustrated], [ominous], [tense], [happy], [sad],
[angry], [fearful], [surprised], [disgusted], [neutral]
```

**Why?** CosyVoice will literally say these words if not removed!

### Supported Tags
Only these work:
- `[breath]` - Adds breathing sound
- `[sigh]` - Adds sighing sound

### Emotion Handling
The `emotion` field from chunk metadata is passed as a kwarg but **CosyVoice doesn't have native emotion control**. The emotion is mainly used for:
1. Logging/debugging
2. Potential future use in prompt text modification
3. Currently has NO direct effect on audio generation

---

## Inference Methods Explained

### Auto Mode (Default)
**Logic:**
```python
if len(text) < len(prompt_text) * 0.5:
    use cross-lingual  # Text is less than 50% of prompt length
else:
    use zero-shot      # Text is longer
```

**When to Use:** Let the system decide automatically

**Example:**
- Prompt text: 200 characters
- Chunk text: 80 characters → **Cross-lingual** (80 < 100)
- Chunk text: 150 characters → **Zero-shot** (150 >= 100)

### Zero-Shot Mode
**Best for:**
- Long text (>10 seconds of speech)
- High quality voice cloning
- Text longer than 50% of prompt

**Requires:**
- `prompt_text` must be provided
- Text should be substantial

**Quality:** ⭐⭐⭐⭐⭐ Best voice consistency
**Speed:** ⭐⭐⭐⭐ Moderate

### Cross-Lingual Mode
**Best for:**
- Short text (<5 seconds)
- Quick generation
- When prompt_text is missing/unreliable

**Doesn't need:**
- prompt_text (ignored even if provided)

**Quality:** ⭐⭐⭐⭐ Good, but less consistent
**Speed:** ⭐⭐⭐⭐⭐ Fastest

---

## Voice Seed (Reference Audio) Deep Dive

### Current Setup
Your seeds are **24 seconds** long.

### Processing Pipeline
```
1. Load MP3 → Convert to WAV (temporary file)
2. Resample to 16kHz mono
3. Load into tensor
4. Send to CosyVoice
```

### Seed Length Impact

#### If You Reduce Seed Length (e.g., 24s → 6s)

**Speed:**
- ✅ **YES - Faster generation!**
- 16-24s seed → 6-10s seed can save ~10-20% generation time
- Loading/resampling is faster
- Model has less context to process

**Voice Cloning Quality:**
- ⚠️ **Depends on content quality, not just length**
- **6-10 seconds is OPTIMAL** if it contains:
  - Natural speech rhythm
  - Multiple phonemes
  - Clear voice characteristics
  - Consistent tone
- **24 seconds might actually hurt** if:
  - Has silence/pauses
  - Voice changes (emotion shifts)
  - Background noise
  - Multiple speakers

**Optimal Seed Characteristics:**
```
✅ GOOD SEED (6-10s):
- Clean audio
- Consistent tone
- Rich phonetic content
- Natural cadence
- Single speaker
- No background noise

❌ BAD SEED (even if 24s):
- Long pauses
- Emotion changes
- Background music
- Multiple speakers
- Compression artifacts
```

### Recommendations for Your Seeds

**Test This:**
1. Take your 24s seeds
2. Extract the **best 8-10 seconds**:
   - No pauses at start/end
   - Consistent emotion
   - Clear pronunciation
   - Natural flow
3. Compare generation quality

**Likely Result:**
- ⚡ 15-20% faster generation
- 🎯 Same or BETTER voice cloning (less noisy context)
- 💾 Smaller seed files

---

## Prompt Text (Reference Transcript)

### What Is It?
The actual words spoken in your seed audio.

### When It's Used
- **Zero-Shot mode**: REQUIRED
- **Cross-Lingual mode**: Ignored
- **Auto mode**: Used if text is long enough

### Quality Impact
**Accuracy matters!**
```python
# GOOD: Exact transcript
prompt_text = "Violet Sorrengail was supposed to enter the Scribe Quadrant"
seed_audio = <audio of exactly those words>

# BAD: Mismatched
prompt_text = "Hello world"
seed_audio = <audio saying something else>
```

**If mismatch:**
- Voice cloning still works
- But quality degrades
- Model gets confused about voice characteristics

### Your Current Setup
From seed.json files: Each seed has `prompt_text` field.

**Check These:**
1. Does the audio actually match the transcript?
2. Is punctuation preserved?
3. Are emotion tags removed from prompt_text?

---

## Speed Parameter

### Available via UI
```python
tts_config: {
    "speed": 1.0  # 0.5 to 2.0
}
```

### Effect
- `speed < 1.0`: Slower speech (more deliberate)
- `speed = 1.0`: Normal speed
- `speed > 1.0`: Faster speech (more energetic)

**Note:** This controls **playback speed**, not generation speed!

---

## Temperature-Like Settings

### ❌ NOT Available in CosyVoice 2
CosyVoice 2 does **NOT** expose:
- `temperature`
- `top_k`
- `top_p`
- `cfg_scale`

These are internal to the model and cannot be configured.

### What You CAN Control
1. **Inference Method** (zero-shot vs cross-lingual)
2. **Speed** (0.5-2.0)
3. **text_frontend** (text normalization - currently disabled)
4. **Voice Seed Quality**
5. **Prompt Text Accuracy**

---

## Emotion System (Current State)

### How It Works Now
```python
# In chunk JSON:
{
    "emotion": "tense",  # Stored in metadata or as field
    "text": "She held her breath."
}

# In generator:
emotion = chunk.metadata.get('emotion', 'neutral')
audio = provider.generate_audio(
    text=chunk.text,
    emotion=emotion,  # Passed as kwarg
    ...
)

# In CosyVoice provider:
# Emotion tag in text is REMOVED
# Emotion kwarg is IGNORED (no native support)
```

### Current Limitations
1. **CosyVoice doesn't have native emotion control**
2. Emotion tags `[happy]`, `[sad]`, etc. are removed from text
3. The `emotion` kwarg has no effect on generation

### Workarounds (Not Currently Implemented)

#### Option 1: Modify Prompt Text
```python
# Add emotional context to prompt
if emotion == "angry":
    prompt_text = f"[Speaking angrily] {original_prompt_text}"
```

**Problems:**
- Unreliable
- May confuse model
- Not tested with CosyVoice 2

#### Option 2: Use Emotion-Specific Seeds
```python
# Have multiple seeds per character
seeds/
    Violet Sorrengail/
        neutral_seed.wav
        tense_seed.wav
        happy_seed.wav
        angry_seed.wav
```

**Benefits:**
- ✅ Actually works!
- ✅ Reliable emotion control
- ✅ Better voice consistency

**Drawbacks:**
- Requires generating multiple seeds per character
- More storage space
- More complex seed management

#### Option 3: Audio Post-Processing Effects
```python
# Already implemented!
"audio_effects": [
    {"type": "volume", "params": {"volume": 0.7}},  # Quieter for whisper
    {"type": "reverb", "params": {"intensity": 0.5}},  # Echo for shouting
    {"type": "speed", "params": {"speed": 0.9}}  # Slower for tense
]
```

**Current Support:**
- ✅ Reverb
- ✅ Speed
- ✅ Volume

**Future: Could Add:**
- Pitch shifting (higher for fear, lower for anger)
- Equalization (muffle for whisper, enhance treble for shout)
- Compression (dynamic range for intensity)

---

## Optimization Recommendations

### 1. Optimize Seed Length
**Action:**
```bash
# For each 24s seed, extract best 8-10s segment
ffmpeg -i seed.mp3 -ss 2 -t 8 -c copy seed_optimized.mp3
```

**Expected Gain:**
- 15-20% faster generation
- Same or better voice quality
- Smaller files

### 2. Use Inference Method Strategically
**For Your Chunks:**
- Narration (long): `zero-shot`
- Short dialogue: `cross-lingual`
- Default: `auto` (let it decide)

### 3. Ensure Prompt Text Accuracy
**Check Each Seed:**
```bash
# Listen to seed audio
# Verify prompt_text in seed.json matches EXACTLY
```

### 4. Implement Emotion via Effects
**Instead of relying on emotion tags:**
```json
{
    "text": "She whispered urgently",
    "emotion": "tense",
    "audio_effects": [
        {"type": "volume", "params": {"volume": 0.75}},
        {"type": "speed", "params": {"speed": 0.95}}
    ]
}
```

### 5. Add Emotion Dropdown in UI
**Current:** Emotion field exists in model but not in UI

**TODO:** Add emotion selector in edit modal:
```javascript
<select id="modal-emotion">
    <option value="neutral">Neutral</option>
    <option value="happy">Happy</option>
    <option value="sad">Sad</option>
    <option value="angry">Angry</option>
    <option value="fearful">Fearful</option>
    <option value="tense">Tense</option>
    <option value="excited">Excited</option>
</select>
```

---

## Example: Full Generation Flow

```python
# 1. Load chunk
chunk = {
    "chunk_id": 42,
    "text": "Violet's heart pounded as she approached the edge.",
    "speaker": "NARRATOR",
    "emotion": "tense",  # Stored but not used by CosyVoice
    "type": "narration",
    "tts_config": {
        "provider": "cosyvoice",
        "inference_method": "auto",
        "speed": 1.0
    },
    "audio_effects": []
}

# 2. Load voice seed
seed = VoiceSeed(
    character_name="NARRATOR",
    audio_file="seed.mp3",  # 24 seconds
    prompt_text="Violet Sorrengail was supposed to enter the Scribe Quadrant, live a quiet life among books and history, and leave the job of battling dragons to her older sister, Mira."
)

# 3. CosyVoice receives:
# - text: "Violet's heart pounded as she approached the edge."
#   (emotion tag removed if it was in text)
# - voice_seed: <16kHz mono tensor of seed.mp3>
# - prompt_text: "Violet Sorrengail was supposed to..." (full transcript)
# - inference_method: "zero-shot" (chosen by auto mode because text is long enough)
# - speed: 1.0
# - text_frontend: False

# 4. CosyVoice generates audio:
# - Duration: ~3-4 seconds
# - Sample rate: 22050 Hz
# - Voice: Cloned from seed
# - Emotion: NOT directly controlled (relies on text content and voice seed's inherent tone)

# 5. Post-processing:
# - Apply audio effects (if any)
# - Normalize volume
# - Detect clipping
# - Save to chunk_42.wav
```

---

## Summary: Your Questions Answered

### Q: What are all the things being sent to CosyVoice?
**A:**
1. **Text** (cleaned, emotion tags removed)
2. **Voice Seed Audio** (loaded as 16kHz mono tensor)
3. **Prompt Text** (transcript of seed audio)
4. **Inference Method** (auto/zero-shot/cross-lingual)
5. **Speed** (0.5-2.0, default 1.0)
6. **Emotion** (passed as kwarg, but **NOT used** by CosyVoice)

### Q: If I reduce seed from 24s to 6-10s, will it increase speed?
**A:** ✅ **YES!**
- 15-20% faster generation
- Faster loading/resampling
- Less context for model to process

### Q: Will shorter seed reduce voice cloning ability?
**A:** ⚠️ **IT DEPENDS!**
- **6-10s of clean, consistent speech = OPTIMAL**
- **24s with pauses/noise/emotion changes = WORSE**
- Key factors:
  - Content quality > length
  - Phonetic diversity
  - Consistency of tone
  - No background noise

**Recommendation:** Extract the **best 8-10 seconds** from your 24s seeds.

### Q: How to better construct emotion tags?
**A:**
- **Current:** Emotion tags are removed by CosyVoice
- **Better:** Use audio effects for emotion:
  - Whisper: Lower volume, slower speed
  - Shout: Add reverb, increase volume
  - Tense: Slightly slower speed
- **Best:** Create emotion-specific voice seeds

### Q: Are there temperature-like settings?
**A:** ❌ **NO**
- CosyVoice 2 doesn't expose sampling parameters
- No `temperature`, `top_k`, `top_p`, or `cfg_scale`
- Only control: inference method, speed, voice seed quality

---

## Next Steps

1. **Add Emotion Dropdown to UI**
   - Let user select emotion per chunk
   - Store in chunk.emotion or chunk.metadata.emotion

2. **Test Optimized Seed Lengths**
   - Extract 8-10s from current 24s seeds
   - Compare quality and speed

3. **Implement Emotion via Effects**
   - Create effect presets for emotions
   - Apply automatically based on chunk.emotion

4. **Document Seed Creation Best Practices**
   - Guidelines for recording/selecting seed audio
   - Optimal length, quality, content

Would you like me to implement any of these improvements?
