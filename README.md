# Audiobook Generator

<div align="center">

Turn any text into immersive audiobooks featuring emotion-rich AI voices, unique character sound, and customizable audio environments.
A **modular, extensible Python-based audiobook generation system** with support for multiple TTS providers, emotion-controllable voice synthesis, audio effects, and a modern web interface.


[Features](#features) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [CLI Generation](#cli-generation)
  - [Project Structure](#project-structure)
  - [Configuration](#configuration)
- [TTS Providers](#tts-providers)
- [Audio Effects](#audio-effects)
- [Advanced Features](#advanced-features)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

Audiobook Engine transforms text files into professional-quality audiobooks using state-of-the-art text-to-speech models. It supports multiple TTS providers, emotion-controllable synthesis, voice cloning, and audio post-processing - all through an intuitive web interface or powerful CLI.

### Key Capabilities

- 🎭 **Multi-Character Narration**: Generate unique voices for each character using seed audio
- 🎚️ **Emotion Control**: Fine-tune emotional expression through natural language prompts
- 🔊 **Audio Effects**: Add reverb, adjust speed, and control volume per chunk
- 🎨 **Model Comparison**: Test different TTS providers side-by-side
- 🌐 **Web Interface**: Manage projects, generate audio, and preview results in real-time
- ⚙️ **Extensible**: Plugin architecture for adding new TTS/chunking/seed providers

---

## Features

### Core Functionality

✅ **Multiple TTS Providers**
- CosyVoice 2 (original implementation)
- CosyVoice 3 (improved accuracy: 0.81-1.21% CER vs 1.45%)
- MLX CosyVoice 3 (Apple Silicon optimization, experimental)

✅ **Emotion Control**
- Instruct2 mode for emotion-controllable synthesis
- Natural language emotion prompts (e.g., "Spoken with tension and urgency")
- 9 canonical emotions: neutral, somber, contemplative, tense, angry, joyful, fearful, tender, bitter

✅ **Voice Cloning**
- Generate character voices from 3-10 second seed audio samples
- Per-seed reference audio for consistent character voices
- Automatic speaker embedding extraction

✅ **Per-Chunk Customization**
- Different TTS providers per audio segment
- Unique emotion prompts per chunk
- Speaker and type tagging (dialogue/narration)
- Custom audio effects per chunk

✅ **Audio Effects**
- **Reverb**: Room size and damping control
- **Speed**: Playback rate adjustment (0.5x - 2.0x)
- **Volume**: Gain control in decibels

✅ **Quality Assurance**
- Clipping detection and warnings
- Audio normalization
- Duration validation
- Generation retry on failure

✅ **Background Audio Generation**
- Ambient sound effects via Stable Audio integration
- Configurable duration and prompts
- Automatic mixing with narration

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI Layer                         │
│  (Flask Application - Project Management & Generation)      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     Core Engine Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Providers   │  │    Audio     │  │    Models    │      │
│  │   System     │  │  Processing  │  │  (Pydantic)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Provider Plugins                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ TTS Providers│  │  Chunking    │  │   Seeds      │      │
│  │              │  │  Providers   │  │  Providers   │      │
│  │ • CosyVoice2 │  │ • Anthropic  │  │ • ElevenLabs │      │
│  │ • CosyVoice3 │  │ • OpenAI     │  │ • CosyVoice  │      │
│  │ • MLX CV3    │  │ • Local LLM  │  │ • Custom     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
audiobook_engine/
├── engine/                          # Core business logic
│   ├── providers/                   # Plugin system
│   │   ├── tts/                    # TTS provider implementations
│   │   │   ├── cosyvoice.py        # CosyVoice 2 provider
│   │   │   ├── cosyvoice3.py       # CosyVoice 3 provider
│   │   │   ├── mlx_cosyvoice3.py   # MLX-optimized for Apple Silicon
│   │   │   └── dia2.py             # Dia2 provider (experimental)
│   │   ├── base.py                 # Abstract base classes
│   │   └── registry.py             # Provider registration
│   ├── audio/                      # Audio processing
│   │   ├── utils.py                # Audio utilities (clipping, normalization)
│   │   ├── effects.py              # Audio effect chains
│   │   └── async_writer.py         # Non-blocking audio writes
│   ├── models/                     # Pydantic data models
│   │   ├── project.py              # Project configuration
│   │   ├── chunk.py                # Audio chunk metadata
│   │   └── seed.py                 # Voice seed configuration
│   └── config.py                   # Centralized configuration
├── scripts/                         # CLI tools
│   ├── generate_audiobook.py       # Main generation script
│   ├── generate_background_audio.py # Ambient sound generation
│   ├── test_chunking_prompt.py     # Chunking validation
│   └── convert_*.py                # Data migration utilities
├── web-ui/                          # Flask web application
│   ├── app.py                      # Web server
│   ├── templates/                  # HTML templates
│   │   ├── index.html             # Project list
│   │   └── project.html           # Project details
│   └── static/                     # JavaScript & CSS
│       ├── project.js             # Project management
│       ├── app.js                 # Application logic
│       └── style.css              # Styling
├── projects/                        # User projects (created at runtime)
│   └── <project-name>/
│       ├── project.json            # Project metadata
│       ├── book.txt               # Source text
│       ├── chunked_book.json      # Chunked content with TTS configs
│       ├── seeds/                  # Voice seed files
│       │   └── <character>/
│       │       ├── seed.wav       # Reference audio
│       │       └── seed.json      # Seed metadata
│       └── audio/                  # Generated audio chunks
│           ├── chunk_1.wav
│           └── ...
├── tests/                           # Unit tests
│   ├── test_cosyvoice_provider.py
│   ├── test_audio_effects.py
│   └── test_models.py
├── prompts/                         # Prompt templates
│   ├── phase1/                    # Chunking prompts
│   └── template_variables.json    # Prompt variables
├── README.md                        # This file
├── SETUP.md                         # Detailed installation guide
├── requirements.txt                 # Python dependencies
└── .gitignore                       # Git exclusions
```

### Data Flow

```
1. Text Input (book.txt)
       ↓
2. Chunking (LLM or manual)
   → chunked_book.json
   → Chunks tagged with: speaker, type, emotion
       ↓
3. TTS Generation (per chunk)
   → Load seed audio for speaker
   → Select TTS provider + mode
   → Apply emotion prompt
   → Generate audio chunk
       ↓
4. Audio Effects (optional)
   → Reverb, speed, volume
   → Quality checks (clipping, duration)
       ↓
5. Concatenation
   → Merge chunks in order
   → Crossfade between segments
       ↓
6. Final Output
   → full_audiobook.wav
```

---

## Installation

### Prerequisites

- **Python**: 3.9 or higher
- **Operating System**: Linux, macOS, or Windows
- **Hardware**:
  - Minimum: 8GB RAM, any modern CPU
  - Recommended: 16GB RAM, NVIDIA GPU (CUDA) or Apple Silicon (MPS)
- **Disk Space**: 10GB+ for models and projects

### Step 1: Clone Repository

```bash
git clone https://github.com/saiteja0847/audiobook_engine.git
cd audiobook_engine
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install PyTorch

Choose based on your hardware:

**CPU Only (Universal)**
```bash
pip install torch>=2.0.0 torchaudio>=2.0.0 --index-url https://download.pytorch.org/whl/cpu
```

**CUDA 11.8 (NVIDIA GPU)**
```bash
pip install torch>=2.0.0 torchaudio>=2.0.0 --index-url https://download.pytorch.org/whl/cu118
```

**Apple Silicon (M1/M2/M3/M4)**
```bash
pip install torch>=2.0.0 torchaudio>=2.0.0
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Flask & Flask-CORS (web framework)
- Pydantic (data validation)
- Soundfile & Librosa (audio processing)
- Anthropic & OpenAI (optional, for LLM-based chunking)
- python-dotenv (environment management)

### Step 5: Download CosyVoice Models

CosyVoice models are **NOT** included and must be downloaded separately:

```bash
# Navigate to parent directory
cd ..

# Clone CosyVoice repository
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt

# Models download automatically on first use
# (~2GB for CosyVoice-300M models)

cd ../audiobook_engine
```

For detailed instructions, see [SETUP.md](SETUP.md).

### Step 6: Configure Environment

Create a `.env` file:

```bash
# Device selection (cpu, cuda, mps, auto)
COSYVOICE_DEVICE=cpu

# Optional: API keys for LLM-based chunking
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

---

## Quick Start

### Web Interface (Recommended)

1. **Start the web server:**
   ```bash
   python web-ui/app.py
   ```

2. **Open browser:**
   ```
   http://localhost:5002
   ```

3. **Create a project:**
   - Click "New Project"
   - Enter project name
   - Upload text file

4. **Generate audiobook:**
   - Configure chunks (speakers, emotions, TTS settings)
   - Click "Generate All"
   - Monitor progress in real-time

### CLI Generation

```bash
# Generate audiobook for a project
python scripts/generate_audiobook.py --project fourth-wing

# Force regeneration (overwrite existing audio)
python scripts/generate_audiobook.py --project fourth-wing --force

# Generate specific chunks only
python scripts/generate_audiobook.py --project fourth-wing --chunks 1-10,15-20
```

---

## Usage

### Web Interface

#### Project Management

**Create Project:**
```python
# Via web UI or programmatically
from engine.models import Project

project = Project.create(
    name="my-audiobook",
    title="My Audiobook",
    author="Author Name",
    sample_rate=22050
)
```

**Configure Seeds:**
```python
# Add voice seed for a character
from engine.models import VoiceSeed

seed = VoiceSeed(
    character="NARRATOR",
    seed_path="seeds/NARRATOR/seed.wav",
    gender="neutral",
    age_range="30-40"
)
```

**Generate Audio:**
- Use web UI to select chunks and generate
- Or use CLI for batch processing

#### Chunk Management

Each chunk in `chunked_book.json`:

```json
{
  "id": 1,
  "text": "The dragon soared overhead, its scales catching the morning sun.",
  "speaker": "NARRATOR",
  "type": "narration",
  "emotion": "tense",
  "tts_config": {
    "provider": "cosyvoice3",
    "inference_mode": "instruct2",
    "emotion_prompt": "Spoken with building tension and awe",
    "speed": 1.0
  },
  "effects": [
    {
      "type": "reverb",
      "room_size": 0.3,
      "damping": 0.5
    }
  ]
}
```

### CLI Generation

#### Basic Generation

```bash
# Generate all chunks
python scripts/generate_audiobook.py --project my-project

# Generate with specific provider
python scripts/generate_audiobook.py --project my-project --provider cosyvoice3

# Generate with custom device
COSYVOICE_DEVICE=cuda python scripts/generate_audiobook.py --project my-project
```

#### Advanced Options

```bash
# Verbose output
python scripts/generate_audiobook.py --project my-project --verbose

# Dry run (show what would be generated)
python scripts/generate_audiobook.py --project my-project --dry-run

# Parallel generation (4 concurrent workers)
python scripts/generate_audiobook.py --project my-project --workers 4

# Skip existing chunks (incremental generation)
python scripts/generate_audiobook.py --project my-project --skip-existing
```

### Project Structure

Each project follows this structure:

```
projects/my-project/
├── project.json              # Project metadata
├── book.txt                 # Original text source
├── chunked_book.json        # Chunked content with configurations
├── seeds/                   # Voice seed files
│   ├── NARRATOR/
│   │   ├── seed.wav         # Reference audio (3-10 seconds)
│   │   └── seed.json        # Seed metadata
│   ├── Character1/
│   └── Character2/
├── audio/                   # Generated audio chunks
│   ├── chunk_1.wav
│   ├── chunk_2.wav
│   └── ...
└── full_audiobook.wav       # Concatenated final output
```

### Configuration

#### Environment Variables

```bash
# Device Selection
COSYVOICE_DEVICE=cpu|cuda|mps|auto

# Web UI Settings
FLASK_HOST=0.0.0.0
FLASK_PORT=5002
FLASK_DEBUG=false

# API Keys (for LLM chunking providers)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...

# Model Paths (if non-standard)
COSYVOICE_PATH=/path/to/CosyVoice
```

#### TTS Provider Configuration

```python
# In chunked_book.json or programmatically
tts_config = {
    "provider": "cosyvoice3",          # cosyvoice2, cosyvoice3, mlx_cosyvoice3
    "inference_mode": "instruct2",     # instruct2, zero_shot, cross_lingual, auto
    "emotion_prompt": "Spoken with urgency",
    "speed": 1.0,                      # 0.5 to 2.0
    "temperature": 0.5,                # Sampling temperature
    "top_p": 0.9,                      # Nucleus sampling
    "seed_audio": "seeds/NARRATOR/seed.wav"  # Reference audio
}
```

---

## TTS Providers

### CosyVoice 3 (Recommended)

**Best accuracy** with CER 0.81-1.21% (vs 1.45% for v2).

**Inference Modes:**
- `instruct2`: Emotion-controllable synthesis via natural language prompts
- `zero_shot`: Voice cloning from reference audio
- `cross_lingual`: Cross-language voice cloning
- `auto`: Automatic mode selection

**Usage:**
```python
from engine.providers.tts import CosyVoice3Provider

provider = CosyVoice3Provider(
    model_path="CosyVoice/ckpt/CosyVoice-300M-SFT",
    device="cpu"
)

audio = provider.synthesize(
    text="Hello world!",
    speaker_seed="seeds/narrator/seed.wav",
    inference_mode="instruct2",
    emotion_prompt="Spoken with warm enthusiasm"
)
```

### CosyVoice 2

Original implementation with good quality.

**Modes:** Same as CosyVoice 3

**When to use:** If you need compatibility with existing CosyVoice 2 setups.

### MLX CosyVoice 3 (Experimental)

Native Apple Silicon optimization using MLX framework.

**Advantages:**
- No audio corruption issues (unlike PyTorch MPS)
- Faster inference on M-series chips
- Lower memory usage

**Disadvantages:**
- Experimental quality
- Limited to Apple Silicon
- First run downloads ~2.8GB models

**Usage:**
```python
from engine.providers.tts import MLXCosyVoice3Provider

provider = MLXCosyVoice3Provider(
    model="mlx-community/Fun-CosyVoice3-0.5B-2512-fp16",
    device="auto"  # Automatically uses Apple Silicon
)
```

### Provider Comparison

| Provider | Accuracy | Speed | Device Support | Voice Quality |
|----------|----------|-------|----------------|---------------|
| CosyVoice 3 | ⭐⭐⭐⭐⭐ | Medium | CPU, CUDA, MPS | Excellent |
| CosyVoice 2 | ⭐⭐⭐⭐ | Medium | CPU, CUDA, MPS | Very Good |
| MLX CV3 | ⭐⭐⭐ | Fast (M-series) | Apple Silicon only | Good |

---

## Audio Effects

### Reverb

Add spatial depth to audio:

```json
{
  "type": "reverb",
  "room_size": 0.5,    // 0.0 to 1.0 (room size)
  "damping": 0.5,      // 0.0 to 1.0 (high frequency damping)
  "wet_level": 0.3,    // 0.0 to 1.0 (effect amount)
  "dry_level": 0.7     // 0.0 to 1.0 (original signal)
}
```

**Use cases:**
- Large room_size + low damping: Cave, large hall
- Small room_size + high damping: Small room, booth

### Speed

Adjust playback rate:

```json
{
  "type": "speed",
  "factor": 1.1  // 0.5 to 2.0 (1.0 = normal)
}
```

**Use cases:**
- < 1.0: Slow down for emphasis
- > 1.0: Speed up for fast-paced sections

### Volume

Control gain:

```json
{
  "type": "volume",
  "gain_db": -3.0  // -20 to +20 dB
}
```

**Use cases:**
- Negative values: Quieter sections (whispers, distance)
- Positive values: Louder sections (shouts, emphasis)

### Effect Chains

Combine multiple effects:

```json
"effects": [
  {"type": "speed", "factor": 1.1},
  {"type": "volume", "gain_db": -2.0},
  {"type": "reverb", "room_size": 0.4, "damping": 0.6}
]
```

Applied in order: speed → volume → reverb

---

## Advanced Features

### Model Comparison

Test different providers on the same content:

1. Open project in web UI
2. Select chunk(s) to test
3. Choose different providers from dropdown
4. Generate and compare results
5. Keep best version

### Chunking Strategies

**LLM-Based Chunking (Recommended):**
```python
from engine.providers.chunking import AnthropicChunkingProvider

chunker = AnthropicChunkingProvider(api_key="your_key")
chunks = chunker.chunk_text(
    text=book_content,
    speakers=["NARRATOR", "VIOLET", "XADEN"],
    emotions=["neutral", "tense", "joyful", "angry"],
    chunk_size=500  # words
)
```

**Manual Chunking:**
- Edit `chunked_book.json` directly
- Set speaker, type, emotion per chunk
- Control break points precisely

### Background Audio

Generate ambient sound effects:

```bash
python scripts/generate_background_audio.py \
  --project my-project \
  --prompt "gentle rain in a forest" \
  --duration 30 \
  --output background_audio/rain.wav
```

### Quality Monitoring

**Clipping Detection:**
```python
from engine.audio.utils import detect_clipping

has_clipping, clipped_samples = detect_clipping(audio_data)
if has_clipping:
    print(f"Warning: {clipped_samples} samples clipped!")
```

**Normalization:**
```python
from engine.audio.utils import normalize_audio

normalized = normalize_audio(audio_data, target_db=-3.0)
```

---

## Documentation

- **[SETUP.md](SETUP.md)**: Detailed installation and model setup guide
- **[COSYVOICE_PARAMETERS_GUIDE.md](COSYVOICE_PARAMETERS_GUIDE.md)**: CosyVoice parameter reference
- **[ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)**: Environment configuration

### Additional Documentation

- **[COSYVOICE_INSTRUCT2_DISCOVERY.md](COSYVOICE_INSTRUCT2_DISCOVERY.md)**: Emotion control research
- **[INSTRUCT2_IMPLEMENTATION_COMPLETE.md](INSTRUCT2_IMPLEMENTATION_COMPLETE.md)**: Implementation details
- **[PHASE7_SUMMARY.md](PHASE7_SUMMARY.md)**: Development progress

---

## Troubleshooting

### Common Issues

**Issue: "CosyVoice not found"**
```bash
# Solution: Check CosyVoice installation
ls ../CosyVoice
export COSYVOICE_PATH=/path/to/CosyVoice
```

**Issue: CUDA out of memory**
```bash
# Solution: Use CPU instead
export COSYVOICE_DEVICE=cpu
```

**Issue: Audio quality problems on Apple Silicon**
```bash
# Solution: MPS has issues - use CPU
export COSYVOICE_DEVICE=cpu

# Or try MLX provider (experimental)
# Change provider to "mlx_cosyvoice3" in chunked_book.json
```

**Issue: Slow generation**
```bash
# Solution: Use GPU if available
export COSYVOICE_DEVICE=cuda

# Or generate in parallel via web UI
# Multiple chunks generate simultaneously
```

**Issue: Port 5002 already in use**
```bash
# Solution: Use different port
export FLASK_PORT=5003
python web-ui/app.py
```

### Getting Help

1. Check existing [GitHub Issues](https://github.com/saiteja0847/audiobook_engine/issues)
2. Create new issue with:
   - OS and Python version
   - Error message (full traceback)
   - Steps to reproduce
   - Your configuration (device, models used)

---

## Contributing

Contributions welcome! Areas for improvement:

### Wanted Features

- [ ] Additional TTS providers (ElevenLabs, Azure, Google)
- [ ] Enhanced chunking algorithms
- [ ] More audio effects (equalization, compression)
- [ ] MPS device fixes for Apple Silicon
- [ ] Batch project processing
- [ ] Audio format conversion (MP3, AAC export)
- [ ] Automatic chapter detection
- [ ] Real-time preview streaming

### Development Setup

```bash
# Fork and clone repository
git clone https://github.com/your-username/audiobook_engine.git
cd audiobook_engine

# Create development branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest tests/

# Format code
black engine/ scripts/ web-ui/

# Submit pull request
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings for classes and functions
- Keep functions focused and concise

---

## Requirements

### Core Dependencies

```
torch>=2.0.0              # PyTorch framework
torchaudio>=2.0.0         # Audio processing
flask>=3.0.0              # Web framework
flask-cors>=4.0.0         # CORS support
pydantic>=2.0.0           # Data validation
soundfile>=0.12.0         # Audio I/O
librosa>=0.10.0           # Audio analysis
numpy>=1.24.0             # Numerical computing
python-dotenv>=1.0.0      # Environment management
```

### Optional Dependencies

```
anthropic>=0.25.0         # Claude API for chunking
openai>=1.0.0             # GPT API for chunking
elevenlabs>=0.2.0         # ElevenLabs TTS
mlx>=0.9.0                # Apple Silicon optimization
```

---

## Acknowledgments

- **[CosyVoice](https://github.com/FunAudioLLM/CosyVoice)** by FunAudioLLM
- **PyTorch** and **torchaudio** teams
- **Flask** web framework
- All contributors and testers

---

## Roadmap

### Version 1.0 (Current)
- ✅ Multiple TTS providers
- ✅ Emotion-controllable synthesis
- ✅ Web interface
- ✅ Audio effects
- ✅ Voice cloning

### Version 1.1 (Planned)
- [ ] Enhanced chunking with speaker diarization
- [ ] Multi-language support
- [ ] Export to MP3/AAC
- [ ] Automatic chapter detection

### Version 2.0 (Future)
- [ ] Real-time streaming generation
- [ ] Voice training from custom datasets
- [ ] Collaborative project editing
- [ ] Cloud deployment support

---

<div align="center">

**Built with ❤️ for audiobook enthusiasts**

[GitHub](https://github.com/saiteja0847/audiobook_engine) • [Issues](https://github.com/saiteja0847/audiobook_engine/issues) • [Documentation](#documentation)

</div>
