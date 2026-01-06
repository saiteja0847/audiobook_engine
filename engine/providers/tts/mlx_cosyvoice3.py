"""
MLX CosyVoice 3 TTS Provider
=============================

Native Apple Silicon implementation using MLX framework.
Runs natively on M-series Macs without MPS fallback issues.

Performance:
    - Native Apple Silicon acceleration via MLX
    - No audio corruption (unlike MPS with PyTorch)
    - First run downloads models (~2.8GB) to ~/.cache/huggingface
    - Subsequent runs use cached models

Model:
    - mlx-community/Fun-CosyVoice3-0.5B-2512-fp16
    - 16-bit weights for better audio quality
    - Voice cloning via reference audio
"""

import os
import logging
from pathlib import Path
from typing import Optional
import torch
import numpy as np

from ..base import TTSProvider

logger = logging.getLogger(__name__)


class MLXCosyVoice3Provider(TTSProvider):
    """
    MLX CosyVoice 3.0 TTS Provider

    Native Apple Silicon implementation using MLX framework.
    Supports instruct2 for emotion control!

    Features:
        - Native Apple Silicon acceleration (M1/M2/M3/M4)
        - Emotion control via instruct2 (same as PyTorch CosyVoice 3)
        - Voice cloning from reference audio
        - No MPS fallback issues - runs natively on Metal

    Device Support:
        - Apple Silicon (M1/M2/M3/M4): Native MLX acceleration ✅
        - Intel Mac: Not supported (MLX requires Apple Silicon)
        - Other platforms: Not supported

    External Dependencies:
        - mlx-audio-plus: pip install -U mlx-audio-plus
        - Models auto-download to ~/.cache/huggingface (first run only)
    """

    def __init__(self):
        self._model_id = "mlx-community/Fun-CosyVoice3-0.5B-2512-fp16"
        self._model_loaded = False

        # Set cache directory for models
        cache_dir = Path.home() / ".cache" / "huggingface"
        os.environ["HF_HOME"] = str(cache_dir)

        # Check if we're on Apple Silicon
        import platform
        if platform.processor() != 'arm':
            logger.warning(
                "⚠️  MLX requires Apple Silicon (M1/M2/M3/M4)\n"
                "   This provider will not work on Intel Macs or other platforms."
            )

        # Check if models are cached
        if cache_dir.exists():
            logger.info(f"✓ Model cache found at {cache_dir}")
        else:
            logger.info(
                f"First run will download models (~2.8GB) to {cache_dir}\n"
                "Subsequent runs will use cached models."
            )

    @property
    def name(self) -> str:
        return "mlx-cosyvoice3"

    @property
    def display_name(self) -> str:
        return "MLX CosyVoice 3 (Apple Silicon)"

    @property
    def inference_methods(self):
        # MLX version uses simpler interface - only one mode
        return ["mlx"]

    @property
    def supports_voice_cloning(self) -> bool:
        return True

    @property
    def requires_prompt_text(self) -> bool:
        # MLX auto-transcribes reference audio, no prompt needed
        return False

    @property
    def sample_rate(self) -> int:
        return 24000  # CosyVoice 3 default

    def load_model(self) -> None:
        """
        MLX models load on-demand, so this is a no-op.
        First generate_audio() call will download/load models.
        """
        if self._model_loaded:
            logger.info("MLX CosyVoice 3 ready (models load on-demand)")
            return

        try:
            # Just verify mlx_audio is available
            import mlx_audio
            logger.info("✓ mlx_audio available")
            self._model_loaded = True

        except ImportError as e:
            raise ImportError(
                "mlx-audio-plus not installed.\n"
                "Install with: pip install -U mlx-audio-plus\n"
                f"Error: {e}"
            )

    def generate_audio(
        self,
        text: str,
        voice_seed_path: Path,
        prompt_text: Optional[str] = None,
        inference_method: str = "mlx",
        **kwargs
    ) -> torch.Tensor:
        """
        Generate audio using MLX CosyVoice 3.

        Args:
            text: Text to synthesize
            voice_seed_path: Path to voice reference audio (.wav file)
            prompt_text: Not used (MLX auto-transcribes reference audio)
            inference_method: "mlx" (only one method available)
            **kwargs: Additional options:
                - speed: float (default 1.0) - Playback speed

        Returns:
            Audio tensor with shape (samples,)
        """
        if not self._model_loaded:
            logger.info("Loading MLX models on first use...")
            self.load_model()

        try:
            from mlx_audio.tts.generate import generate_audio
            import soundfile as sf

        except ImportError as e:
            raise ImportError(
                "mlx-audio-plus not installed.\n"
                "Install with: pip install -U mlx-audio-plus\n"
                f"Error: {e}"
            )

        # Get speed parameter
        speed = kwargs.get('speed', 1.0)

        # Get emotion parameters for instruct2
        emotion = kwargs.get('emotion', None)
        emotion_prompt = kwargs.get('emotion_prompt', '')

        # Build instruction text for MLX (same format as CosyVoice 3)
        instruct_text = self._build_emotion_prompt_v3(emotion, emotion_prompt)

        # Clean text (remove unsupported tags)
        import re
        text_clean = re.sub(
            r'\[(whisper|mutter|shout|softly|snap|click|gasp|laugh|laughter|giggle|cough|sniff|sob|cry|scream|yawn|thunder|murmur|frustrated|ominous|tense|happy|sad|angry|fearful|surprised|disgusted|neutral)\]',
            '',
            text,
            flags=re.IGNORECASE
        ).strip()

        if not text_clean:
            raise ValueError("Text is empty after cleaning")

        logger.info(f"📝 Text to generate: '{text_clean}'")

        # Generate to temporary file (MLX uses its own naming)
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Change to temp directory (MLX saves to current directory)
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir_path)

                logger.info(f"Generating audio with MLX CosyVoice 3")
                logger.debug(f"  Text: {text_clean}")
                logger.debug(f"  Instruction: {instruct_text}")
                logger.debug(f"  Reference: {voice_seed_path.name}")
                logger.debug(f"  Speed: {speed}x")

                # Generate audio with instruct2 support (saves as audio_000.wav in current directory)
                generate_audio(
                    text=text_clean,
                    model=self._model_id,
                    ref_audio=str(voice_seed_path),
                    instruct_text=instruct_text,  # Add emotion/instruction support!
                    speed=speed
                )

                # Find generated file (MLX uses audio_000.wav, audio_001.wav, etc.)
                generated_files = list(temp_dir_path.glob("audio_*.wav"))
                if not generated_files:
                    raise RuntimeError("MLX did not generate output file")

                # Load the audio
                audio_path = generated_files[0]
                audio, sr = sf.read(str(audio_path))

                logger.debug(f"  Generated: {len(audio)} samples at {sr} Hz")

                # Verify sample rate matches
                if sr != self.sample_rate:
                    logger.warning(
                        f"Sample rate mismatch: expected {self.sample_rate}, got {sr}"
                    )

                # Convert to torch tensor (1D)
                audio_tensor = torch.from_numpy(audio.astype(np.float32))

                # Ensure 1D
                if audio_tensor.dim() > 1:
                    audio_tensor = audio_tensor.squeeze(0)

                return audio_tensor

            except Exception as e:
                logger.error(f"MLX audio generation failed: {e}")
                raise RuntimeError(f"MLX CosyVoice 3 generation failed: {e}")
            finally:
                # Restore original directory
                os.chdir(original_cwd)

    def _build_emotion_prompt_v3(self, emotion: Optional[str], custom_prompt: str = "") -> str:
        """
        Convert emotion to instruction prompt for MLX CosyVoice 3 instruct2.
        Format: "You are a helpful assistant. {instruction}<|endofprompt|>"

        Args:
            emotion: Emotion name (e.g., "happy", "sad", "angry")
            custom_prompt: Custom emotion instruction (overrides emotion)

        Returns:
            Formatted instruction text for MLX CosyVoice 3
        """
        # Map emotion to instruction prompt
        emotion_prompts = {
            "happy": "with excitement and joy",
            "sad": "with deep sadness and resignation",
            "angry": "angrily, with rising intensity",
            "fearful": "in a tense, fearful tone with urgency",
            "tense": "with tension and apprehension",
            "confident": "confidently and decisively",
            "defiant": "with quiet defiance and sharp intensity",
            "threatening": "in a low, threatening tone with menace",
            "excited": "breathlessly excited",
            "whisper": "in a quiet whisper, as if afraid to be heard",
            "shout": "loudly and forcefully",
            "sarcastic": "with a hint of sarcasm",
            "calm": "calmly and matter-of-factly",
            "urgent": "urgently, with rising pressure",
            "resigned": "with resignation and acceptance",
            "hopeful": "with cautious hope",
            "desperate": "desperately, voice breaking",
            "contempt": "with cold contempt",
            "surprise": "with sudden surprise",
            "disgust": "with disgust and revulsion",
        }

        # If custom prompt provided, check if it's a simple emotion word first
        if custom_prompt:
            # Check if custom_prompt is actually a simple emotion word (case-insensitive)
            custom_lower = custom_prompt.strip().lower()
            if custom_lower in emotion_prompts:
                # It's a simple emotion word, use the mapping
                instruction = emotion_prompts[custom_lower]
                return f'You are a helpful assistant. {instruction}<|endofprompt|>'

            # Not a simple emotion, treat as custom instruction
            if '<|endofprompt|>' not in custom_prompt:
                return f'You are a helpful assistant. {custom_prompt}<|endofprompt|>'
            return custom_prompt

        # If no emotion, return just the prefix (neutral)
        if not emotion or emotion == "neutral":
            return 'You are a helpful assistant.<|endofprompt|>'

        instruction = emotion_prompts.get(emotion.lower(), "")
        if instruction:
            return f'You are a helpful assistant. {instruction}<|endofprompt|>'
        return 'You are a helpful assistant.<|endofprompt|>'

    def get_method_info(self, method: str):
        """Get information about inference methods"""
        methods = {
            "mlx": {
                "name": "mlx",
                "display_name": "MLX Instruct2",
                "description": "Native Apple Silicon acceleration with emotion control via instruct2.",
                "requires_prompt_text": False
            }
        }
        return methods.get(method, super().get_method_info(method))
