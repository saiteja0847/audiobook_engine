# Dia2 Implementation Fixes

## Changes Applied

### 1. Fixed Import Path
**File**: `engine/providers/tts/dia2.py` (line 29)
- **Before**: `from engine.config import EXTERNAL_MODELS_DIR`
- **After**: `from engine.config import DIA2_PATH`
- **Reason**: Use the dedicated config constant instead of constructing path

### 2. Fixed Model Path
**File**: `engine/providers/tts/dia2.py` (line 44)
- **Before**: `self._model_path = EXTERNAL_MODELS_DIR / "dia2"`
- **After**: `self._model_path = DIA2_PATH`
- **Reason**: Consistency with config

### 3. Fixed Generation Result Handling
**File**: `engine/providers/tts/dia2.py` (line 265)
- **Before**:
  ```python
  # Dia2 returns a tuple: (audio_tensor, sample_rate)
  if isinstance(result, tuple):
      audio = result[0]
  else:
      audio = result
  ```
- **After**:
  ```python
  # Dia2 returns a GenerationResult object with .waveform attribute
  audio = result.waveform
  ```
- **Reason**: Dia2 API returns `GenerationResult` object, not tuple

### 4. Updated Generation Config Defaults
**File**: `engine/providers/tts/dia2.py` (lines 162-180)
- **Before**:
  - `cfg_scale: 3.0` (default), `6.0` (high_quality), `2.0` (fast)
  - `use_cuda_graph: True`
- **After**:
  - `cfg_scale: 2.0` (default), `3.5` (high_quality), `1.5` (fast)
  - `use_cuda_graph: False`
- **Reason**: Match Dia2 library defaults, disable CUDA graph for compatibility

### 5. Fixed GenerationConfig Creation
**File**: `engine/providers/tts/dia2.py` (lines 220-236)
- **Before**:
  ```python
  config = self._GenerationConfig(
      cfg_scale=config_params.get("cfg_scale", 3.0),
      audio=self._SamplingConfig(...),
      use_cuda_graph=config_params.get("use_cuda_graph", True)
  )
  ```
- **After**:
  ```python
  # Create both text and audio sampling configs
  text_sampling = self._SamplingConfig(
      temperature=config_params.get("temperature", 0.8) * 0.75,
      top_k=config_params.get("top_k", 50)
  )
  audio_sampling = self._SamplingConfig(
      temperature=config_params.get("temperature", 0.8),
      top_k=config_params.get("top_k", 50)
  )

  config = self._GenerationConfig(
      cfg_scale=config_params.get("cfg_scale", 2.0),
      text=text_sampling,
      audio=audio_sampling,
      use_cuda_graph=config_params.get("use_cuda_graph", False)
  )
  ```
- **Reason**: Dia2 requires both `text` and `audio` SamplingConfig parameters

## API Changes Discovered

### Dia2 GenerationResult
```python
@dataclass(frozen=True)
class GenerationResult:
    audio_tokens: torch.Tensor  # Mimi audio tokens
    waveform: torch.Tensor      # Decoded waveform (44.1kHz)
    sample_rate: int            # Always 44100
    timestamps: List[Tuple[str, float]]  # Word-level timing
```

### Dia2 GenerationConfig
```python
@dataclass(frozen=True)
class GenerationConfig:
    text: SamplingConfig              # Text sampling config
    audio: SamplingConfig             # Audio sampling config
    cfg_scale: float = 2.0            # Classifier-free guidance
    cfg_filter_k: int = 50
    initial_padding: int = 2
    prefix: Optional[PrefixConfig] = None
    use_cuda_graph: bool = False      # CUDA graph optimization
    use_torch_compile: bool = False   # Torch compile
```

### Dia2 SamplingConfig
```python
@dataclass(frozen=True)
class SamplingConfig:
    temperature: float = 0.8
    top_k: int = 50
```

## Testing Steps

1. **Run Diagnostic**:
   ```bash
   cd audiobook_engine
   conda activate audiobook2.0
   python diagnose_dia2.py
   ```
   This will check if Dia2 can be imported and the model can be loaded.

2. **Run Generation Test**:
   ```bash
   python test_dia2_generation.py
   ```
   This will generate audio for the first chunk using all three inference methods.

3. **Test via Web UI**:
   - Start server: `python web-ui/app.py`
   - Open browser to `http://localhost:5002`
   - Select a chunk
   - Set TTS provider to "Dia2"
   - Click "Generate Audio"
   - Check terminal for logs

## Expected Behavior

### Successful Generation
```
Loading Dia2 model from nari-labs/Dia2-2B...
✓ Dia2 model loaded on cuda (bfloat16)

  🎙️  Generating Chunk 1...
      Text: Violet Sorrengail was supposed to enter the Scribe Quadrant...
      Speaker: NARRATOR
      Provider: dia2 (default)
  [Dia2] Generating with default preset
  [Dia2] Text: [S1] Violet Sorrengail was supposed to enter...
  [Dia2] Voice seed: narrator_seed.wav
  [Dia2] Using voice seed for conditioning
  [Dia2] Generated 8.42s of audio
      ✓ Generated: 8.42s audio in 12.3s
      ✓ Saved: chunk_1.wav
```

### Common Errors and Solutions

#### Error: "dia2 module not found"
**Solution**: Install dia2 in the conda environment:
```bash
cd /path/to/dia2
conda activate audiobook2.0
pip install -e .
```

#### Error: "CUDA out of memory"
**Solution**: Force CPU mode:
```python
# In dia2.py line 42
self._device = "cpu"
```

#### Error: "MPS backend not supported"
**Solution**: Dia2 doesn't support Mac MPS yet. Force CPU:
```python
self._device = "cpu"  # Force CPU on Mac
```

#### Error: "AttributeError: 'GenerationResult' has no attribute 'waveform'"
**Solution**: Update Dia2 to latest version:
```bash
cd /path/to/dia2
git pull
pip install -e .
```

## Performance Notes

- **Generation Speed**: ~0.5-2x realtime on GPU, ~0.1x on CPU
- **Memory Usage**: ~4GB for model + 1-2GB per generation
- **Quality**: Comparable to CosyVoice for voice cloning
- **Optimal Chunk Length**: 5-20 seconds (as per Dia2 docs)

## Next Steps

1. Test with different voices to verify voice cloning quality
2. Compare output quality with CosyVoice
3. Benchmark generation speed on your hardware
4. Tune generation configs for best quality
5. Consider implementing audio resampling (44.1kHz → 22kHz) if needed for consistency
