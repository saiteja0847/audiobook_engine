"""
Dia2 TTS Provider
==================

Provider implementation for Nari Labs Dia2 TTS model (November 2025).

Dia2 is a streaming text-to-speech model with voice cloning capabilities
via conditional generation using prefix audio.

Key Features:
- Real-time streaming generation
- Voice cloning with prefix audio
- Speaker tag system ([S1], [S2])
- 44.1kHz sample rate
- Optimal for 5-20 second audio chunks

Documentation: https://github.com/nari-labs/dia2
"""

import sys
from pathlib import Path
from typing import Optional, List
import re

import torch
import torchaudio

from engine.providers.base import TTSProvider
from engine.config import DIA2_PATH


class Dia2Provider(TTSProvider):
    """
    Dia2 TTS Provider implementation.

    Supports voice cloning through prefix audio conditioning.
    Automatically formats text with speaker tags.
    """

    def __init__(self):
        self._model = None
        # Dia2 officially supports CUDA only, use CPU as fallback
        # MPS causes issues with Dia2's CUDA-specific optimizations
        if torch.cuda.is_available():
            self._device = "cuda"
            self._dtype = "bfloat16"
        else:
            self._device = "cpu"
            self._dtype = "float32"
        self._model_path = DIA2_PATH
        self._initialized = False

    @property
    def name(self) -> str:
        return "dia2"

    @property
    def display_name(self) -> str:
        return "Dia2 (Nari Labs)"

    @property
    def inference_methods(self) -> List[str]:
        """
        Dia2 uses a single generation method with configurable parameters.
        We expose different quality/speed presets.
        """
        return ["default", "high_quality", "fast"]

    @property
    def supports_voice_cloning(self) -> bool:
        return True

    @property
    def requires_prompt_text(self) -> bool:
        """Dia2 uses prefix audio instead of prompt text."""
        return False

    @property
    def sample_rate(self) -> int:
        """Get actual sample rate from loaded model."""
        if self._initialized and self._model:
            return self._model.sample_rate
        return 24000  # Dia2 default (Mimi codec rate)

    def load_model(self) -> None:
        """
        Load the Dia2 model into memory.
        Implementation of abstract method from TTSProvider.
        """
        if self._initialized:
            return

        try:
            # Add dia2 to path if installed locally
            dia2_path = self._model_path
            if dia2_path.exists():
                sys.path.insert(0, str(dia2_path))

            from dia2 import Dia2, GenerationConfig, SamplingConfig

            print(f"Loading Dia2 model from nari-labs/Dia2-1B...")

            self._model = Dia2.from_repo(
                "nari-labs/Dia2-1B",  # Using 1B model for better performance
                device=self._device,
                dtype=self._dtype
            )

            # Store config classes for later use
            self._GenerationConfig = GenerationConfig
            self._SamplingConfig = SamplingConfig

            self._initialized = True
            print(f"✓ Dia2 model loaded on {self._device} ({self._dtype})")

        except ImportError as e:
            raise ImportError(
                f"Failed to import dia2. Please install it:\n"
                f"  git clone https://github.com/nari-labs/dia2.git {dia2_path}\n"
                f"  cd {dia2_path}\n"
                f"  uv sync\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Dia2 model: {e}")

    def _ensure_initialized(self):
        """Lazy load the Dia2 model."""
        self.load_model()

    def _format_text_with_speaker_tags(self, text: str, speaker_tag: str = "[S1]") -> str:
        """
        Format text with Dia2 speaker tags.

        Dia2 requires:
        - Text must start with a speaker tag ([S1] or [S2])
        - For single speaker, use only [S1]
        - For dialogue, alternate [S1] and [S2]

        Args:
            text: Raw text to format
            speaker_tag: Default speaker tag to use (default: [S1])

        Returns:
            Text formatted with speaker tags
        """
        # Remove any existing speaker tags first
        text_clean = re.sub(r'\[S[12]\]\s*', '', text)

        # Check if text already has dialogue markers
        # (Could be enhanced to detect dialogue patterns)

        # For now, just prepend speaker tag if not present
        if not text.strip().startswith('[S'):
            text = f"{speaker_tag} {text_clean}"
        else:
            text = text_clean

        return text.strip()

    def _get_generation_config(self, inference_method: str = "default"):
        """
        Get Dia2 generation configuration based on inference method.

        Methods:
        - default: Balanced quality and speed (Dia2 defaults)
        - high_quality: Higher CFG scale, lower temperature
        - fast: Lower CFG scale, optimized for speed
        """
        configs = {
            "default": {
                "cfg_scale": 3.0,  # Higher CFG for better voice cloning
                "temperature": 0.7,  # Lower temp for more consistent voice
                "top_k": 50,
                "use_cuda_graph": False  # Disabled by default for compatibility
            },
            "high_quality": {
                "cfg_scale": 4.0,  # Even higher for quality
                "temperature": 0.6,
                "top_k": 45,
                "use_cuda_graph": False
            },
            "fast": {
                "cfg_scale": 2.0,  # Lower for speed
                "temperature": 0.85,
                "top_k": 60,
                "use_cuda_graph": False
            }
        }

        return configs.get(inference_method, configs["default"])

    def generate_audio(
        self,
        text: str,
        voice_seed_path: Path,
        prompt_text: Optional[str] = None,
        inference_method: str = "default",
        **kwargs
    ) -> torch.Tensor:
        """
        Generate audio using Dia2 with voice cloning.

        Args:
            text: Text to generate audio for
            voice_seed_path: Path to reference audio file for voice cloning
            prompt_text: Not used (Dia2 uses prefix audio instead)
            inference_method: Generation preset (default, high_quality, fast)
            **kwargs: Additional parameters (cfg_scale, temperature, etc.)

        Returns:
            Generated audio tensor (44.1kHz, mono)
        """
        self._ensure_initialized()

        # Format text with speaker tags
        formatted_text = self._format_text_with_speaker_tags(text, speaker_tag="[S1]")

        print(f"  [Dia2] Generating with {inference_method} preset")
        print(f"  [Dia2] Text: {formatted_text[:80]}...")
        print(f"  [Dia2] Voice seed: {voice_seed_path.name}")

        # Get generation config
        config_params = self._get_generation_config(inference_method)

        # Override with any provided kwargs
        config_params.update(kwargs)

        # Create sampling configs (text uses slightly lower temp than audio)
        text_sampling = self._SamplingConfig(
            temperature=config_params.get("temperature", 0.8) * 0.75,  # Lower temp for text
            top_k=config_params.get("top_k", 50)
        )
        audio_sampling = self._SamplingConfig(
            temperature=config_params.get("temperature", 0.8),
            top_k=config_params.get("top_k", 50)
        )

        # Create generation config
        config = self._GenerationConfig(
            cfg_scale=config_params.get("cfg_scale", 2.0),
            text=text_sampling,
            audio=audio_sampling,
            use_cuda_graph=config_params.get("use_cuda_graph", False)
        )

        # Load prefix audio for voice cloning
        # Dia2 expects prefix audio to condition the generation
        prefix_audio = None
        if voice_seed_path.exists():
            try:
                # Load audio and resample to 44.1kHz if needed
                audio, sr = torchaudio.load(str(voice_seed_path))

                print(f"  [Dia2] Seed audio: {sr}Hz, shape: {audio.shape}")

                # Resample if needed
                if sr != 44100:
                    print(f"  [Dia2] Resampling {sr}Hz -> 44100Hz")
                    resampler = torchaudio.transforms.Resample(sr, 44100)
                    audio = resampler(audio)
                    print(f"  [Dia2] Resampled shape: {audio.shape}")

                    # Save resampled audio to temp file for Dia2
                    import tempfile
                    temp_seed = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    torchaudio.save(temp_seed.name, audio, 44100)
                    prefix_audio = temp_seed.name
                    print(f"  [Dia2] Resampled seed saved to temp file")
                else:
                    # Use original if already 44.1kHz
                    prefix_audio = str(voice_seed_path)

                # Convert to mono if stereo (do this before saving if resampling)
                if audio.shape[0] > 1:
                    audio = audio.mean(dim=0, keepdim=True)
                    # Re-save if we're using temp file
                    if prefix_audio != str(voice_seed_path):
                        torchaudio.save(prefix_audio, audio, 44100)

                print(f"  [Dia2] Using voice seed for conditioning")

            except Exception as e:
                print(f"  [Dia2] Warning: Could not load voice seed: {e}")
                print(f"  [Dia2] Generating with default voice")

        # Generate audio
        # Note: Dia2 API uses prefix_speaker_1 for [S1] conditioning
        try:
            # Enable verbose to see what Dia2 is doing
            print(f"  [Dia2] Calling generate with:")
            print(f"         Text: {formatted_text[:50]}...")
            print(f"         Prefix path: {prefix_audio}")
            if prefix_audio:
                print(f"         Prefix exists: {Path(prefix_audio).exists()}")
                print(f"         Prefix is absolute: {Path(prefix_audio).is_absolute()}")
                print(f"         Prefix resolved: {Path(prefix_audio).resolve()}")
            else:
                print(f"         Prefix: None (no voice cloning!)")

            result = self._model.generate(
                formatted_text,
                config=config,
                prefix_speaker_1=prefix_audio,  # Condition on voice seed
                verbose=True  # Enable to debug voice cloning
            )

            # Dia2 returns a GenerationResult object with .waveform attribute
            audio = result.waveform

            # Ensure audio is 1D tensor
            if audio.dim() > 1:
                audio = audio.squeeze()

            # Convert to CPU if needed
            if audio.is_cuda:
                audio = audio.cpu()

            print(f"  [Dia2] Generated {audio.shape[-1] / 44100:.2f}s of audio")

            return audio

        except Exception as e:
            print(f"  [Dia2] Error during generation: {e}")
            raise RuntimeError(f"Dia2 generation failed: {e}")

    def get_model_info(self) -> dict:
        """Get information about the Dia2 model."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": "Dia2-2B (November 2025)",
            "sample_rate": self.sample_rate,
            "inference_methods": self.inference_methods,
            "supports_voice_cloning": self.supports_voice_cloning,
            "requires_prompt_text": self.requires_prompt_text,
            "device": self._device if self._initialized else "not loaded",
            "dtype": self._dtype,
            "features": [
                "Real-time streaming generation",
                "Voice cloning via prefix audio",
                "Speaker tag system ([S1], [S2])",
                "Optimal for 5-20 second chunks",
                "44.1kHz output"
            ],
            "limitations": [
                "English only",
                "Requires CUDA 12.8+ for GPU",
                "5-20 second optimal audio length",
                "Max ~2 minutes per generation"
            ]
        }


# Export
__all__ = ['Dia2Provider']
