# Dia2 Implementation Status

## Overview
Dia2 TTS provider is implemented but needs testing and potential debugging.

## Current Status

### ✅ What's Implemented

1. **Dia2Provider Class** (`engine/providers/tts/dia2.py`)
   - Lazy model loading from `nari-labs/Dia2-2B`
   - Voice cloning via prefix audio conditioning
   - Speaker tag formatting ([S1], [S2])
   - Three inference presets: `default`, `high_quality`, `fast`
   - Sample rate: 44.1kHz
   - Device: CUDA (if available) or CPU

2. **Provider Registration**
   - Registered in `web-ui/app.py` (line 541)
   - Appears in provider registry alongside CosyVoice

3. **UI Integration**
   - Dia2 appears in TTS provider dropdown
   - Bulk generation settings support Dia2
   - Per-chunk provider selection supports Dia2

4. **AudiobookGenerator Integration** (`scripts/generate_audiobook.py`)
   - Supports per-chunk provider selection
   - Passes voice seed path and inference method
   - Handles Dia2's 44.1kHz sample rate

### 🔍 Key Implementation Details

**Model Loading** (dia2.py:76-116):
```python
def load_model(self) -> None:
    # Adds dia2 directory to Python path
    dia2_path = DIA2_PATH  # /path/to/dia2
    sys.path.insert(0, str(dia2_path))

    from dia2 import Dia2, GenerationConfig, SamplingConfig

    self._model = Dia2.from_repo(
        "nari-labs/Dia2-2B",
        device=self._device,
        dtype=self._dtype
    )
```

**Audio Generation** (dia2.py:184-284):
```python
def generate_audio(
    text: str,
    voice_seed_path: Path,
    prompt_text: Optional[str] = None,  # Not used
    inference_method: str = "default",
    **kwargs
) -> torch.Tensor:
    # 1. Format text with speaker tags
    formatted_text = self._format_text_with_speaker_tags(text)

    # 2. Load and resample prefix audio to 44.1kHz
    prefix_audio = str(voice_seed_path)

    # 3. Get generation config (default, high_quality, or fast)
    config = self._get_generation_config(inference_method)

    # 4. Generate using Dia2
    result = self._model.generate(
        formatted_text,
        config=config,
        prefix_speaker_1=prefix_audio,  # Voice cloning
        verbose=False
    )

    return audio  # Tensor at 44.1kHz
```

**Generation Config Presets** (dia2.py:146-182):
- **default**: cfg_scale=3.0, temp=0.8, top_k=50
- **high_quality**: cfg_scale=4.0, temp=0.7, top_k=30
- **fast**: cfg_scale=2.0, temp=0.9, top_k=100

### ⚠️ Potential Issues to Check

1. **Dia2 Installation**
   - Is dia2 installed at `/Users/saiteja/Downloads/My-Projects/Claude-Code/Audiobook-Attempt-3/dia2`?
   - Does it have a `.venv` with required dependencies?
   - Can the dia2 module be imported?

2. **Model Download**
   - Does `Dia2.from_repo("nari-labs/Dia2-2B")` work?
   - Are HuggingFace credentials configured if needed?
   - Does the model fit in memory (check GPU/CPU RAM)?

3. **Device Compatibility**
   - Mac M4 (MPS): Dia2 may not support MPS backend
   - May need to force CPU mode on Mac
   - Check if CUDA is correctly detected on Linux/Windows

4. **Audio Resampling**
   - Dia2 outputs 44.1kHz, engine expects 22kHz
   - Need to verify resampling works correctly
   - Check if AudiobookGenerator handles this

5. **Generation Config**
   - Are the config params valid for Dia2 API?
   - Check if `use_cuda_graph` works on Mac/CPU
   - Verify GenerationConfig and SamplingConfig imports

### 🧪 Testing Needed

1. **Basic Provider Test**
   ```bash
   cd audiobook_engine
   python tests/test_dia2_provider.py
   ```
   - Should register provider
   - Should report inference methods
   - Should format text with speaker tags

2. **Generation Test**
   ```bash
   cd audiobook_engine
   python test_dia2_generation.py
   ```
   - Should load model
   - Should generate audio from first chunk
   - Should save WAV files

3. **UI Generation Test**
   - Start web UI
   - Select a chunk
   - Set TTS provider to "Dia2"
   - Generate
   - Check for errors in terminal

### 📝 Next Steps

1. **Immediate**:
   - Run `python tests/test_dia2_provider.py` to check registration
   - Check if dia2 can be imported: `python -c "import dia2; print(dia2.__version__)"`
   - Verify model path exists: `ls -la /path/to/dia2`

2. **If Import Fails**:
   - Check dia2 virtual environment is activated
   - Install dia2 in audiobook2.0 environment
   - Or update `_model_path` to point to working dia2 installation

3. **If Model Loading Fails**:
   - Check device compatibility (MPS vs CUDA vs CPU)
   - Try forcing CPU mode
   - Check HuggingFace credentials
   - Check available memory

4. **If Generation Fails**:
   - Check audio resampling (44.1kHz → 22kHz)
   - Verify GenerationConfig parameters
   - Test with shorter text first
   - Enable verbose mode for debugging

### 🔧 Quick Fixes

**Force CPU Mode** (if device issues):
```python
# In dia2.py line 42, change:
self._device = "cpu"  # Always use CPU
```

**Disable CUDA Graph** (if not supported):
```python
# In dia2.py line 167, change:
"use_cuda_graph": False,  # Disable CUDA graph
```

**Enable Verbose Output** (for debugging):
```python
# In dia2.py line 261, change:
verbose=True  # See detailed generation logs
```

### 📊 Comparison: CosyVoice vs Dia2

| Feature | CosyVoice | Dia2 |
|---------|-----------|------|
| Sample Rate | 22.05kHz | 44.1kHz |
| Voice Cloning | Prompt text + seed | Prefix audio only |
| Inference Methods | zero-shot, cross-lingual | default, high_quality, fast |
| Device Support | CUDA, CPU | CUDA, CPU (MPS unclear) |
| Speaker Tags | Optional | Required ([S1], [S2]) |
| Status | ✅ Working | ❓ Needs testing |

## User's Request

User said: "Can you check whats happening, I started generate with dia."

This suggests user attempted to generate audio using Dia2 but encountered an issue.

### Likely Scenarios:
1. **Model not loading**: Import error or missing dependencies
2. **Generation failing**: Device incompatibility or API mismatch
3. **Silent failure**: Audio generated but empty/corrupted
4. **UI error**: Provider selection not working correctly

### To Diagnose:
1. Check browser console for frontend errors
2. Check Flask terminal for backend errors
3. Run test scripts to isolate the issue
4. Check if any audio files were created

## Conclusion

The Dia2 implementation is **complete** but **untested**. All the code is in place:
- Provider class fully implemented
- Registered in the system
- Integrated with UI and generator
- Test scripts created

**Next action**: Run tests to identify and fix any issues with model loading, device compatibility, or generation.
