# Dia2 TTS Provider

Integration of Nari Labs Dia2 TTS model (November 2025) with the audiobook engine.

## Overview

Dia2 is a streaming text-to-speech model with excellent voice cloning capabilities. It uses prefix audio conditioning instead of traditional prompt text.

**Key Features:**
- Real-time streaming generation
- Voice cloning with 5-10 second reference audio
- 44.1kHz high-quality output
- Speaker tag system for natural dialogue
- GPU-accelerated with CUDA graph optimization

## Installation

### Prerequisites
- Python 3.10+
- CUDA 12.8+ (for GPU acceleration)
- `uv` package manager

### Install Dia2

```bash
# Navigate to parent directory of audiobook_engine
cd /Users/saiteja/Downloads/My-Projects/Claude-Code/Audiobook-Attempt-3

# Clone Dia2 repository
git clone https://github.com/nari-labs/dia2.git

# Install dependencies
cd dia2
uv sync

# Test installation
uv run -m dia2.cli --help
```

### Verify Installation

```bash
cd audiobook_engine
python tests/test_dia2_provider.py
```

Expected output:
```
============================================================
Dia2 Provider Test Suite
============================================================

Testing Dia2 Provider Registration...
  ✓ Dia2 provider imported and registered

Testing Dia2 Provider Info...
  ✓ Provider name: Dia2 (Nari Labs)
  ✓ Sample rate: 44100Hz
  ✓ Inference methods: default, high_quality, fast
  ✓ Voice cloning: True

✅ All Dia2 provider tests passed!
```

## Usage

### Command Line Generation

```bash
# Generate audiobook with Dia2
python scripts/generate_audiobook.py --project my-audiobook
```

The generation script will automatically use the TTS provider specified in each chunk's `tts_config`:

```json
{
  "chunk_id": 1,
  "text": "This is a test chunk.",
  "speaker": "NARRATOR",
  "tts_config": {
    "provider": "dia2",
    "inference_method": "default"
  }
}
```

### Web UI

1. Start the web server:
```bash
python web-ui/app.py
```

2. Open http://localhost:5002

3. Select a project and edit a chunk

4. In the chunk editor modal:
   - Set **TTS Provider**: `Dia2 (Nari Labs)`
   - Set **Inference Method**:
     - `default` - Balanced quality/speed
     - `high_quality` - Better quality, slower
     - `fast` - Faster generation, slightly lower quality

5. Save and generate

### Python API

```python
from pathlib import Path
from engine.providers.registry import ProviderRegistry
from engine.providers.tts.dia2 import Dia2Provider

# Register provider
ProviderRegistry.register_tts(Dia2Provider)

# Get provider
dia2 = ProviderRegistry.get_tts("dia2")

# Generate audio
audio = dia2.generate_audio(
    text="Hello, this is a test of Dia2 voice cloning.",
    voice_seed_path=Path("path/to/reference_audio.wav"),
    inference_method="default"
)

# Save audio
import torchaudio
torchaudio.save("output.wav", audio.unsqueeze(0), 44100)
```

## Configuration

### Inference Methods

The provider supports three preset configurations:

#### `default` (Recommended)
```python
{
    "cfg_scale": 3.0,
    "temperature": 0.8,
    "top_k": 50,
    "use_cuda_graph": True
}
```
Balanced quality and speed for general audiobook generation.

#### `high_quality`
```python
{
    "cfg_scale": 6.0,
    "temperature": 0.7,
    "top_k": 45,
    "use_cuda_graph": True
}
```
Higher classifier-free guidance for better adherence to voice characteristics. Slightly slower.

#### `fast`
```python
{
    "cfg_scale": 2.0,
    "temperature": 0.9,
    "top_k": 60,
    "use_cuda_graph": True
}
```
Optimized for speed. Good for testing or less critical chunks.

### Custom Parameters

You can override parameters programmatically:

```python
audio = dia2.generate_audio(
    text="Custom generation",
    voice_seed_path=voice_seed,
    inference_method="default",
    cfg_scale=4.0,           # Custom CFG scale
    temperature=0.75,        # Custom temperature
    top_k=55,               # Custom top_k
    use_cuda_graph=True     # Enable CUDA graphs
)
```

## Voice Cloning

Dia2 uses **prefix audio conditioning** for voice cloning instead of prompt text.

### Requirements
- Reference audio: 5-10 seconds (optimal)
- Format: WAV, MP3, or any format supported by torchaudio
- Sample rate: Any (automatically resampled to 44.1kHz)
- Channels: Mono or stereo (automatically converted to mono)

### How It Works

1. The provider loads your voice seed audio
2. Resamples it to 44.1kHz if needed
3. Converts to mono if stereo
4. Passes it to Dia2 as `prefix_speaker_1` parameter
5. Dia2 conditions the generation on this reference

### Example

```python
# Your voice seed structure
projects/my-audiobook/seeds/NARRATOR/
├── seed.json
└── seed.wav  # 7 seconds of narrator voice

# Chunk configuration
{
  "chunk_id": 1,
  "text": "Once upon a time...",
  "speaker": "NARRATOR",
  "tts_config": {
    "provider": "dia2",
    "inference_method": "default"
  }
}

# Generation will use NARRATOR/seed.wav for voice cloning
```

## Speaker Tags

Dia2 requires speaker tags in the text. The provider automatically formats your text:

**Input:**
```
Hello, this is a test.
```

**Formatted for Dia2:**
```
[S1] Hello, this is a test.
```

For single-speaker audiobooks, all text gets `[S1]` tags automatically.

## Performance

### Hardware Requirements
- **Minimum:** RTX 3090 (24GB VRAM)
- **Recommended:** RTX 4090 or A4000
- **CUDA:** 12.8+

### Generation Speed
- RTX 4090: ~2.1x real-time (bfloat16 with compile)
- A4000: ~1.5x real-time
- CPU: Not supported

### Memory Usage
- ~4-6GB VRAM per generation
- CUDA graphs enabled by default for better performance

## Limitations

1. **English only** - Dia2 currently only supports English
2. **Chunk length** - Optimal for 5-20 second audio chunks
   - Under 5s: Unnatural sounding
   - Over 20s: May become unnaturally fast
3. **Max generation** - ~2 minutes per generation (1500 context steps)
4. **GPU required** - No CPU inference support

## Troubleshooting

### Error: "Failed to import dia2"

**Solution:**
```bash
cd /path/to/Audiobook-Attempt-3
git clone https://github.com/nari-labs/dia2.git
cd dia2
uv sync
```

### Error: "CUDA 12.8+ required"

**Solution:** Update your CUDA drivers
```bash
nvidia-smi  # Check current version
# Update CUDA drivers from nvidia.com
```

### Warning: "Could not load voice seed"

**Causes:**
- Voice seed file doesn't exist
- File is corrupted
- Unsupported audio format

**Solution:**
- Verify seed file path: `projects/PROJECT/seeds/SPEAKER/seed.wav`
- Check file format (use WAV for reliability)
- Try re-encoding: `ffmpeg -i old.mp3 -ar 44100 -ac 1 seed.wav`

### Audio too fast/slow

**Solution:** Adjust chunk text length
- Too fast: Split into smaller chunks (5-10s each)
- Too slow: Combine smaller chunks
- Rule of thumb: 1 second audio ≈ 86 tokens ≈ 12-15 words

## Comparison with CosyVoice

| Feature | Dia2 | CosyVoice |
|---------|------|-----------|
| Sample Rate | 44.1kHz | 22.05kHz |
| Voice Cloning | Prefix audio | Prompt text + audio |
| Inference Methods | 3 presets | Zero-shot, Cross-lingual |
| Streaming | Yes | No |
| Speed (RTX 4090) | 2.1x realtime | ~1.5x realtime |
| Languages | English only | Multi-language |
| Speaker Tags | Required ([S1]) | Optional |
| Optimal Chunk Length | 5-20s | Any length |

## Best Practices

1. **Voice Seeds:**
   - Use 5-10 second reference audio
   - Choose clear, representative samples
   - Avoid background noise
   - Single speaker only in reference

2. **Chunk Length:**
   - Keep chunks 5-20 seconds of audio
   - Split long paragraphs into multiple chunks
   - Use natural sentence boundaries

3. **Quality Settings:**
   - Use `default` for most cases
   - Use `high_quality` for important character introductions
   - Use `fast` for testing or less critical narration

4. **Performance:**
   - Enable CUDA graphs (default)
   - Use bfloat16 precision (default)
   - Close other GPU applications during generation

## Examples

### Basic Audiobook Generation

```bash
# 1. Prepare project
projects/my-book/
├── chunked_book.json
└── seeds/
    └── NARRATOR/
        ├── seed.json
        └── seed.wav

# 2. Generate with Dia2
python scripts/generate_audiobook.py --project my-book

# 3. Output
projects/my-book/audio/
├── chunk_1.wav  (44.1kHz)
├── chunk_2.wav
└── ...
```

### Multi-Provider Workflow

```json
// chunked_book.json - Mix providers for optimal results
[
  {
    "chunk_id": 1,
    "text": "Chapter narration...",
    "speaker": "NARRATOR",
    "tts_config": {"provider": "dia2", "inference_method": "default"}
  },
  {
    "chunk_id": 2,
    "text": "Dialogue in another language...",
    "speaker": "CHARACTER",
    "tts_config": {"provider": "cosyvoice", "inference_method": "cross-lingual"}
  }
]
```

## References

- **Dia2 GitHub:** https://github.com/nari-labs/dia2
- **Original Dia:** https://github.com/nari-labs/dia
- **Hugging Face:** https://huggingface.co/nari-labs/Dia2-2B
- **Discord Community:** https://discord.gg/bJq6vjRRKv

## License

Dia2 is licensed under Apache 2.0 License.
