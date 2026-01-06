# Audiobook Engine - Setup Guide

## Prerequisites

- Python 3.9+
- PyTorch
- CosyVoice models (downloaded separately)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download CosyVoice Models

CosyVoice models are NOT included and must be downloaded separately:

```bash
# Clone CosyVoice in parent directory
cd ..
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt
# Models will be downloaded on first use
```

### 3. Configure Environment

Create a `.env` file in `audiobook_engine/`:

```bash
# Device selection
COSYVOICE_DEVICE=cpu  # or cuda, mps, auto

# Optional: API keys for chunking providers
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

### 4. Run

```bash
# Web UI
python web-ui/app.py

# Access at http://localhost:5002
```

## Troubleshooting

### Issue: "CosyVoice not found"
**Solution:** Make sure CosyVoice is in parent directory: `../CosyVoice/`

### Issue: CUDA out of memory
**Solution:** Use CPU: `export COSYVOICE_DEVICE=cpu`

### Issue: Audio quality problems on Apple Silicon
**Solution:** MPS has known issues - use CPU instead

## Documentation

- [README.md](README.md) - Project overview
- [COSYVOICE_PARAMETERS_GUIDE.md](COSYVOICE_PARAMETERS_GUIDE.md) - Parameter reference

---

For detailed troubleshooting, see the main README.md.
