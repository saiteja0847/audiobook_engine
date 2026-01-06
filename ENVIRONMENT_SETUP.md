# Audiobook Engine - Environment Setup

## Working Environment: audiobook2.0

The `audiobook2.0` conda environment has been verified to work correctly with CosyVoice TTS generation.

## Critical Requirements

### 1. NumPy Version
**MUST use NumPy 1.x** (NOT 2.x)
- CosyVoice is incompatible with NumPy 2.0+
- Use: `numpy<2` or `numpy==1.26.4`

### 2. PyTorch Versions
**torch and torchaudio versions MUST match exactly**
- Recommended: `torch==2.1.2` and `torchaudio==2.1.2`
- Or: `torch==2.0.1` and `torchaudio==2.0.1`

### 3. TorchAudio Backend
**Use older torchaudio (≤2.1.x) to avoid torchcodec dependency**
- Newer versions (2.2+) default to torchcodec backend
- This causes audio saving issues

### 4. Package Installation
**Do NOT mix conda and pip for the same packages**
- Choose either conda OR pip for each package, not both
- Mixing causes version conflicts and runtime errors

## Environment Creation

```bash
# Create fresh environment
conda create -n audiobook2.0 python=3.10 -y
conda activate audiobook2.0

# Install pynini (CosyVoice dependency)
conda install -c conda-forge pynini=2.1.5

# Install audio libraries
conda install -c conda-forge librosa

# Install PyTorch
pip install torch==2.1.2 torchaudio==2.1.2

# Install other requirements
pip install "numpy<2" soundfile pydantic anthropic instructor elevenlabs
```

## Key Issues Resolved

### Issue 1: Gibberish Audio Output
**Cause**: NumPy 2.x incompatibility with CosyVoice
**Solution**: Downgrade to NumPy 1.26.4

### Issue 2: TorchCodec Import Error
**Cause**: Newer torchaudio versions require torchcodec
**Solution**: Use torchaudio 2.1.2 or earlier

### Issue 3: OpenMP Library Conflicts
**Cause**: Multiple OpenMP runtimes (conda + homebrew)
**Solution**: Set environment variable:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

### Issue 4: Seed Transcript
**Cause**: Using partial/short transcript instead of complete one
**Solution**: Use the FULL, EXACT transcript from seed audio in `seed.json`

## Verification

Test the environment with:

```bash
conda activate audiobook2.0
cd /path/to/audiobook_engine
python test_working_script.py
```

Audio should be clear and match the expected voice.

## Environment Comparison

### ❌ Old audiobook environment (BROKEN)
- NumPy 2.0.2 (incompatible!)
- torch 2.8.0 / torchaudio 2.8.0 (version mismatch)
- Mixed conda/pip installs
- Result: Garbage audio

### ✅ New audiobook2.0 environment (WORKING)
- NumPy 1.26.4
- torch 2.1.2 / torchaudio 2.1.2 (matched)
- Clean installation
- Result: Clear, proper audio

## Notes for Future

- Always verify NumPy version before running TTS generation
- Keep torch/torchaudio versions matched
- Test with `test_working_script.py` after environment changes
- If audio becomes garbled again, check NumPy version first
