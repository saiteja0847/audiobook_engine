# Audiobook Engine

A modular, extensible Python-based audiobook generation system with support for multiple TTS providers, emotion-controllable voice synthesis, audio effects, and a modern web interface.

## Features

- ✅ **Multiple TTS Providers**: CosyVoice 2, CosyVoice 3, MLX-optimized CosyVoice for Apple Silicon
- ✅ **Emotion Control**: Fine-grained emotion prompting for expressive narration (instruct2 mode)
- ✅ **Per-Chunk Customization**: Different voices, models, and settings for each audio segment
- ✅ **Audio Effects**: Reverb, speed adjustment, volume control
- ✅ **Voice Cloning**: Generate character voices from seed audio samples
- ✅ **Web Interface**: Modern Flask-based UI for project management and generation
- ✅ **Background Audio**: Generate ambient sound effects using Stable Audio
- ✅ **Quality Monitoring**: Clipping detection, normalization, duration validation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run web UI
python web-ui/app.py

# Access at http://localhost:5002
```

## Documentation

- [SETUP.md](SETUP.md) - Detailed installation and model setup guide
- [COSYVOICE_PARAMETERS_GUIDE.md](COSYVOICE_PARAMETERS_GUIDE.md) - CosyVoice parameter reference
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Environment configuration

## Requirements

- Python 3.9+
- PyTorch
- CosyVoice models (downloaded separately - see SETUP.md)

## License

See LICENSE file
