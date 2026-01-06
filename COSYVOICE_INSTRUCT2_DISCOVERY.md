# CosyVoice2 inference_instruct2 Discovery

## 🎉 Major Discovery!

CosyVoice2 has an **`inference_instruct2` method** that supports:
1. ✅ **Emotion prompts** (text-based emotion control!)
2. ✅ **Audio tags** like `[breath]`, `[laughter]`, etc.
3. ✅ **Voice cloning** with emotion control

This is **NOT currently used** in the audiobook engine!

---

## Current vs. New API

### Currently Used (Old API)
```python
# Zero-shot mode
model.inference_zero_shot(
    tts_text,
    prompt_text,  # Transcript of seed
    voice_seed,
    stream=False,
    speed=1.0
)

# Cross-lingual mode
model.inference_cross_lingual(
    tts_text,
    voice_seed,
    stream=False,
    speed=1.0
)
```

**Limitations:**
- ❌ No emotion control
- ❌ Very limited audio tags (`[breath]`, `[sigh]` only)
- ❌ Emotion tags must be removed or model says them literally

### New API (inference_instruct2)
```python
model.inference_instruct2(
    tts_text,              # Text to generate (can include tags!)
    instruct_text,         # Emotion/style prompt!
    voice_seed,            # Voice reference
    zero_shot_spk_id='',   # Optional speaker ID
    stream=False,
    speed=1.0
)
```

**Benefits:**
- ✅ **Emotion control via text prompt!**
- ✅ **Audio tags work: `[breath]`, `[laughter]`, etc.**
- ✅ **Natural language instructions**: "in a tense whisper", "with rising anger"
- ✅ **Voice cloning with emotion**

---

## Example from Internet Script

```python
# Example 1: Low, dominating tone with sarcasm
result = model.inference_instruct2(
    "You will not break me [laughter].",
    "in a low, dominating tone with a hint of sarcasm",
    prompt_speech_16k=voice_seed,
    stream=False
)

# Example 2: Quiet defiance
result = model.inference_instruct2(
    "I already have.",
    "with quiet defiance and sharp intensity",
    prompt_speech_16k=voice_seed,
    stream=False
)

# Example 3: Building anger
result = model.inference_instruct2(
    "This is treason!",
    "angrily, building to outrage",
    prompt_speech_16k=voice_seed,
    stream=False
)
```

---

## Emotion Prompt Examples

### For Audiobook Narration

**Tense/Suspenseful:**
```python
instruct_text = "in a tense, fearful whisper with urgency"
instruct_text = "with rising tension and dread"
instruct_text = "quietly, as if afraid to be heard"
```

**Confident/Determined:**
```python
instruct_text = "with quiet defiance and sharp intensity"
instruct_text = "confidently and decisively"
instruct_text = "with unwavering determination"
```

**Sad/Sorrowful:**
```python
instruct_text = "with deep sadness and resignation"
instruct_text = "voice breaking with emotion"
instruct_text = "softly, holding back tears"
```

**Angry/Frustrated:**
```python
instruct_text = "angrily, building to outrage"
instruct_text = "with barely contained fury"
instruct_text = "through gritted teeth, seething"
```

**Excited/Happy:**
```python
instruct_text = "with excitement and joy, laughing"
instruct_text = "breathlessly excited"
instruct_text = "bubbling with enthusiasm"
```

**Threatening/Menacing:**
```python
instruct_text = "in a low, threatening tone with rising menace"
instruct_text = "coldly, with quiet malice"
instruct_text = "dangerously calm"
```

**Neutral/Calm:**
```python
instruct_text = "calmly and matter-of-factly"
instruct_text = "in a steady, measured tone"
instruct_text = ""  # Empty for completely neutral
```

---

## Audio Tags That Work

Based on the script and CosyVoice2 documentation:

### Confirmed Working
- `[breath]` - Breathing sound
- `[laughter]` - Laughing
- `[sigh]` - Sighing

### Likely Working (Need Testing)
- `[laugh]` - Alternative to laughter
- `[gasp]` - Gasping
- `[cough]` - Coughing
- `[whisper]` - Whispering (may work with instruct2)

### Unknown (Need Testing)
- `[shout]` - Shouting
- `[sob]` - Sobbing/crying
- `[scream]` - Screaming

---

## Test Script

Created: `test_cosyvoice_instruct2.py`

**Tests:**
1. Neutral (no emotion cue)
2. Tense with breath tag
3. Confident and determined
4. Excited with laughter tag
5. Low and menacing

**Run Test:**
```bash
cd audiobook_engine
conda activate audiobook2.0
python test_cosyvoice_instruct2.py
```

**Output:**
- `test_output/instruct2_neutral.wav`
- `test_output/instruct2_tense.wav`
- `test_output/instruct2_defiant.wav`
- `test_output/instruct2_happy.wav`
- `test_output/instruct2_threat.wav`

---

## Implementation Plan

### Phase 1: Add instruct2 as Inference Method

**Update CosyVoice Provider:**
```python
@property
def inference_methods(self):
    return ["auto", "zero-shot", "cross-lingual", "instruct2"]  # Add instruct2
```

**Add Generation Logic:**
```python
def generate_audio(self, text, voice_seed_path, prompt_text=None,
                   inference_method="auto", emotion=None, **kwargs):

    # ... existing code ...

    if inference_method == 'instruct2':
        # Build emotion prompt
        emotion_prompt = self._build_emotion_prompt(emotion, kwargs.get('emotion_prompt', ''))

        for output in self._model.inference_instruct2(
            text,  # Don't remove emotion tags anymore!
            emotion_prompt,  # Emotion instruction
            voice_seed,
            stream=False,
            speed=speed
        ):
            audio = output['tts_speech']
            break
```

**Build Emotion Prompt:**
```python
def _build_emotion_prompt(self, emotion: Optional[str], custom_prompt: str = "") -> str:
    """Convert emotion to instruction prompt."""

    # If custom prompt provided, use it
    if custom_prompt:
        return custom_prompt

    # Map emotion to prompt
    emotion_prompts = {
        "neutral": "",
        "happy": "with excitement and joy",
        "sad": "with deep sadness",
        "angry": "angrily, with rising intensity",
        "fearful": "in a tense, fearful tone with urgency",
        "tense": "with tension and apprehension",
        "confident": "confidently and decisively",
        "defiant": "with quiet defiance and sharp intensity",
        "threatening": "in a low, threatening tone with menace",
        "excited": "breathlessly excited",
        "whisper": "in a quiet whisper, as if afraid to be heard",
        "shout": "loudly and forcefully"
    }

    return emotion_prompts.get(emotion, "")
```

### Phase 2: Add UI Support

**1. Add Emotion Prompt Field to Chunk Model:**
```python
class Chunk(BaseModel):
    emotion: str = Field(default="neutral")
    emotion_prompt: Optional[str] = Field(
        default=None,
        description="Custom emotion instruction (overrides emotion)"
    )
```

**2. Add to Edit Modal (project.html):**
```html
<div class="form-group">
    <label for="modal-emotion">Emotion</label>
    <select id="modal-emotion">
        <option value="neutral">Neutral</option>
        <option value="happy">Happy</option>
        <option value="sad">Sad</option>
        <option value="angry">Angry</option>
        <option value="fearful">Fearful</option>
        <option value="tense">Tense</option>
        <option value="confident">Confident</option>
        <option value="defiant">Defiant</option>
        <option value="threatening">Threatening</option>
        <option value="excited">Excited</option>
        <option value="whisper">Whisper</option>
        <option value="shout">Shout</option>
    </select>
</div>

<div class="form-group">
    <label for="modal-emotion-prompt">
        Custom Emotion Prompt
        <span class="hint">(Optional: Override emotion with custom instruction)</span>
    </label>
    <input
        type="text"
        id="modal-emotion-prompt"
        placeholder="e.g., 'in a tense whisper with urgency'"
    >
</div>
```

**3. Update Save Logic (project.js):**
```javascript
function saveChunkChanges() {
    const chunk = currentEditingChunk;

    // Update emotion
    chunk.emotion = document.getElementById('modal-emotion').value;

    // Update custom emotion prompt (if provided)
    const emotionPrompt = document.getElementById('modal-emotion-prompt').value.trim();
    if (emotionPrompt) {
        if (!chunk.metadata) chunk.metadata = {};
        chunk.metadata.emotion_prompt = emotionPrompt;
    }

    // ... rest of save logic ...
}
```

### Phase 3: Update Text Cleaning

**IMPORTANT:** With instruct2, DON'T remove emotion tags from text!

```python
# OLD (for zero-shot/cross-lingual):
text_clean = re.sub(
    r'\[(whisper|laughter|breath|...)\]',
    '',  # REMOVE tags
    text
)

# NEW (for instruct2):
# Keep the tags! They work now!
text_clean = text  # No cleaning needed
```

---

## Expected Benefits

### 1. Better Emotion Control
- ✅ Natural language emotion instructions
- ✅ Fine-grained control (e.g., "tense whisper" vs "fearful whisper")
- ✅ Consistent emotional delivery

### 2. Audio Tags Work
- ✅ `[breath]` for dramatic pauses
- ✅ `[laughter]` for joy/sarcasm
- ✅ `[sigh]` for resignation

### 3. More Expressive Narration
- ✅ Dialogue feels more natural
- ✅ Narration has appropriate tone
- ✅ Better match to book's emotional arc

### 4. Flexibility
- ✅ Preset emotions for quick selection
- ✅ Custom prompts for unique situations
- ✅ Per-chunk emotion control

---

## Testing Strategy

### Step 1: Run Test Script
```bash
python test_cosyvoice_instruct2.py
```

**Listen for:**
- Does emotion prompt affect the voice?
- Do `[breath]` and `[laughter]` tags work?
- Is voice cloning quality maintained?

### Step 2: Compare with Current Method
Generate same text with:
1. Current `zero-shot` method
2. New `instruct2` method with emotion prompt

**Compare:**
- Quality difference
- Emotion effectiveness
- Generation speed

### Step 3: Test Different Emotion Prompts
Try various prompts:
- Short: "angrily"
- Medium: "with rising anger"
- Long: "angrily, building to outrage, voice trembling with fury"

**Find optimal prompt length and style**

### Step 4: Test Audio Tags
Test all suspected working tags:
```python
texts = [
    "She paused. [breath] Then continued.",
    "He laughed bitterly. [laughter]",
    "She sighed deeply. [sigh]",
    "He gasped. [gasp]",
    "She coughed. [cough]"
]
```

---

## Migration Path

### Option A: Add as New Method (Recommended)
- Keep existing zero-shot/cross-lingual methods
- Add instruct2 as new inference method
- Let users choose per chunk
- Gradual migration

### Option B: Replace Default
- Make instruct2 the default
- Fallback to zero-shot if emotion prompt empty
- Immediate benefits for all generations

### Option C: Hybrid
- Use instruct2 when emotion != "neutral"
- Use zero-shot/cross-lingual for neutral chunks
- Best of both worlds

---

## Questions to Answer via Testing

1. **Does instruct2 work with emotion prompts?**
   - Run test script, listen to results

2. **Which audio tags are supported?**
   - Test each tag individually

3. **How does quality compare to zero-shot?**
   - A/B test same text with both methods

4. **Does generation speed differ?**
   - Time multiple generations

5. **What's the optimal emotion prompt format?**
   - Test short vs long prompts
   - Test descriptive vs directive prompts

6. **Can we combine multiple emotions?**
   - E.g., "with sadness and resignation"

7. **Do custom prompts work better than presets?**
   - Test both approaches

---

## Next Actions

1. ✅ Created test script: `test_cosyvoice_instruct2.py`
2. ⏳ **YOU**: Run test script and listen to outputs
3. ⏳ Share results: Which emotions work? Which tags work?
4. ⏳ Implement instruct2 in CosyVoice provider
5. ⏳ Add emotion prompt field to UI
6. ⏳ Update documentation with findings
7. ⏳ Add example emotion prompts to UI

---

## Conclusion

This is a **game-changer** for audiobook generation!

The `inference_instruct2` method provides:
- ✅ Emotion control we've been missing
- ✅ Audio tags that actually work
- ✅ Natural language instructions
- ✅ Fine-grained control over delivery

**Next step:** Run the test script and see how well it works!

```bash
cd audiobook_engine
conda activate audiobook2.0
python test_cosyvoice_instruct2.py
```

Then listen to the generated files in `test_output/` and let me know:
1. Does emotion prompt make a difference?
2. Which audio tags work?
3. Is voice quality maintained?
4. Any surprising results?
