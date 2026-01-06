"""
CosyVoice TTS Provider
======================

Wrapper for CosyVoice 2 text-to-speech model.
References: audiobook-project-manager/scripts/generate_audiobook.py
"""

import sys
import torch
import logging
from pathlib import Path
from typing import Optional

from ..base import TTSProvider
from ...config import COSYVOICE_PATH

logger = logging.getLogger(__name__)


class CosyVoiceProvider(TTSProvider):
    """
    CosyVoice 2 TTS Provider

    Supports two inference methods:
    - zero-shot: High quality, requires prompt text matching audio
    - cross-lingual: More reliable for short text, doesn't need prompt text

    External Dependencies:
        Requires CosyVoice model installed at COSYVOICE_PATH
    """

    def __init__(self):
        self._model = None
        self._model_loaded = False
        self._model_path = COSYVOICE_PATH / "pretrained_models" / "CosyVoice2-0.5B"

        # Add CosyVoice to Python path
        if str(COSYVOICE_PATH) not in sys.path:
            sys.path.insert(0, str(COSYVOICE_PATH))
            sys.path.insert(0, str(COSYVOICE_PATH / "third_party" / "Matcha-TTS"))

    @property
    def name(self) -> str:
        return "cosyvoice"

    @property
    def display_name(self) -> str:
        return "CosyVoice 2"

    @property
    def inference_methods(self):
        return ["instruct2", "auto", "zero-shot", "cross-lingual"]  # instruct2 first (default)

    @property
    def supports_voice_cloning(self) -> bool:
        return True

    @property
    def requires_prompt_text(self) -> bool:
        # Zero-shot needs it, cross-lingual doesn't
        # Return True to indicate it's beneficial to provide
        return True

    @property
    def sample_rate(self) -> int:
        if self._model:
            return self._model.sample_rate
        return 22050  # Default

    def load_model(self) -> None:
        """Load CosyVoice model into memory"""
        if self._model_loaded:
            logger.info("CosyVoice model already loaded")
            return

        if not self._model_path.exists():
            raise FileNotFoundError(
                f"CosyVoice model not found at: {self._model_path}\n"
                f"Please install CosyVoice at: {COSYVOICE_PATH}"
            )

        try:
            from cosyvoice.cli.cosyvoice import CosyVoice2
            from cosyvoice.utils.file_utils import load_wav

            logger.info(f"Loading CosyVoice model from {self._model_path}")
            self._model = CosyVoice2(
                str(self._model_path),
                load_jit=False,
                load_trt=False,
                load_vllm=False,
                fp16=False
            )
            self._load_wav = load_wav
            self._model_loaded = True
            logger.info("✓ CosyVoice model loaded successfully")

        except ImportError as e:
            raise ImportError(
                f"Failed to import CosyVoice. Make sure it's installed at {COSYVOICE_PATH}\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load CosyVoice model: {e}")

    def generate_audio(
        self,
        text: str,
        voice_seed_path: Path,
        prompt_text: Optional[str] = None,
        inference_method: str = "instruct2",
        **kwargs
    ) -> torch.Tensor:
        """
        Generate audio using CosyVoice.

        Args:
            text: Text to synthesize
            voice_seed_path: Path to voice reference audio (.wav file)
            prompt_text: Text spoken in reference audio (needed for zero-shot)
            inference_method: "instruct2" (default), "auto", "zero-shot", or "cross-lingual"
            **kwargs: Additional options:
                - emotion: str - Emotion name (e.g., "happy", "sad", "angry")
                - emotion_prompt: str - Custom emotion instruction text (overrides emotion)
                - text_frontend: bool (default False) - Enable text normalization
                - stream: bool (default False) - Stream output
                - speed: float (default 1.0) - Playback speed

        Returns:
            Audio tensor with shape (samples,) or (1, samples)
        """
        if not self._model_loaded:
            self.load_model()

        # Load voice seed
        # If it's MP3, convert to WAV first since CosyVoice's internal loader has issues with MP3
        import tempfile
        from pathlib import Path

        seed_path_to_use = voice_seed_path
        temp_wav = None

        try:
            if str(voice_seed_path).lower().endswith('.mp3'):
                # Convert MP3 to temporary WAV using librosa (which uses audioread/Core Audio on Mac)
                import librosa
                import soundfile as sf

                # Load MP3
                audio, sr = librosa.load(str(voice_seed_path), sr=None, mono=False)

                # If stereo, keep stereo for now (will convert to mono later)
                if audio.ndim == 1:
                    audio = audio.reshape(1, -1)

                # Create temporary WAV file
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                sf.write(temp_wav.name, audio.T, sr)  # Transpose for soundfile
                seed_path_to_use = Path(temp_wav.name)
                temp_wav.close()

            voice_seed = self._load_wav(str(seed_path_to_use), 16000)

            # Clean up temporary file if created
            if temp_wav:
                Path(temp_wav.name).unlink()

        except Exception as e:
            # Clean up temporary file on error
            if temp_wav:
                try:
                    Path(temp_wav.name).unlink()
                except:
                    pass
            raise ValueError(f"Failed to load voice seed from {voice_seed_path}: {e}")

        # Get emotion settings
        emotion = kwargs.get('emotion', None)
        emotion_prompt = kwargs.get('emotion_prompt', '')

        # Text cleaning: For instruct2, keep audio tags! They work now!
        # For other methods, remove unsupported tags
        import re
        if inference_method == 'instruct2':
            # Keep all tags - they work with instruct2!
            text_clean = text.strip()
        else:
            # Remove unsupported tags for zero-shot/cross-lingual
            text_clean = re.sub(
                r'\[(whisper|mutter|shout|softly|snap|click|gasp|laugh|laughter|giggle|cough|sniff|sob|cry|scream|yawn|thunder|murmur|frustrated|ominous|tense|happy|sad|angry|fearful|surprised|disgusted|neutral)\]',
                '',
                text,
                flags=re.IGNORECASE
            ).strip()

        if not text_clean:
            raise ValueError("Text is empty after cleaning")

        # Get options
        text_frontend = kwargs.get('text_frontend', False)
        stream = kwargs.get('stream', False)
        speed = kwargs.get('speed', 1.0)

        # Generate audio
        try:
            if inference_method == 'instruct2':
                # Use instruct2 method with emotion prompt
                instruct_text = self._build_emotion_prompt(emotion, emotion_prompt)
                logger.info(f"Generating audio using instruct2 (emotion: '{instruct_text}')")

                for output in self._model.inference_instruct2(
                    text_clean,
                    instruct_text,
                    voice_seed,
                    stream=stream,
                    speed=speed,
                    text_frontend=text_frontend
                ):
                    audio = output['tts_speech']
                    break

            else:
                # Legacy methods: auto, zero-shot, cross-lingual
                use_cross_lingual = False
                method_reason = ""

                if inference_method == 'zero-shot':
                    use_cross_lingual = False
                    method_reason = "forced zero-shot"
                elif inference_method == 'cross-lingual':
                    use_cross_lingual = True
                    method_reason = "forced cross-lingual"
                else:
                    # Auto mode: choose based on text/prompt length ratio
                    if prompt_text and len(text_clean) < len(prompt_text) * 0.5:
                        use_cross_lingual = True
                        method_reason = f"short text ({len(text_clean)}/{len(prompt_text)} chars)"
                    else:
                        use_cross_lingual = False
                        method_reason = f"long text ({len(text_clean)}/{len(prompt_text) if prompt_text else 0} chars)"

                logger.info(f"Generating audio using {'cross-lingual' if use_cross_lingual else 'zero-shot'} ({method_reason})")

                if use_cross_lingual:
                    for output in self._model.inference_cross_lingual(
                        text_clean,
                        voice_seed,
                        stream=stream,
                        speed=speed,
                        text_frontend=text_frontend
                    ):
                        audio = output['tts_speech']
                        break
                else:
                    if not prompt_text:
                        logger.warning("Zero-shot method requested but no prompt_text provided. Using cross-lingual instead.")
                        for output in self._model.inference_cross_lingual(
                            text_clean,
                            voice_seed,
                            stream=stream,
                            speed=speed,
                            text_frontend=text_frontend
                        ):
                            audio = output['tts_speech']
                            break
                    else:
                        for output in self._model.inference_zero_shot(
                            text_clean,
                            prompt_text,
                            voice_seed,
                            stream=stream,
                            speed=speed,
                            text_frontend=text_frontend
                        ):
                            audio = output['tts_speech']
                            break

            # Ensure audio is 1D tensor
            if audio.dim() > 1:
                audio = audio.squeeze(0)

            return audio

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise RuntimeError(f"CosyVoice generation failed: {e}")

    def _build_emotion_prompt(self, emotion: Optional[str], custom_prompt: str = "") -> str:
        """
        Convert emotion to instruction prompt for instruct2.

        Args:
            emotion: Emotion name (e.g., "happy", "sad", "angry")
            custom_prompt: Custom emotion instruction (overrides emotion)

        Returns:
            Emotion instruction text
        """
        # If custom prompt provided, use it
        if custom_prompt:
            return custom_prompt

        # If no emotion, return empty (neutral)
        if not emotion or emotion == "neutral":
            return ""

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

        return emotion_prompts.get(emotion.lower(), "")

    def get_method_info(self, method: str):
        """Get information about inference methods"""
        methods = {
            "instruct2": {
                "name": "instruct2",
                "display_name": "Instruct2 (Emotion Control)",
                "description": "Best quality with emotion control and audio tags support. Default method.",
                "requires_prompt_text": False
            },
            "auto": {
                "name": "auto",
                "display_name": "Auto (Smart Selection)",
                "description": "Automatically chooses between zero-shot and cross-lingual based on text length",
                "requires_prompt_text": True
            },
            "zero-shot": {
                "name": "zero-shot",
                "display_name": "Zero-Shot",
                "description": "High quality and consistency, but requires text length > 50% of prompt",
                "requires_prompt_text": True
            },
            "cross-lingual": {
                "name": "cross-lingual",
                "display_name": "Cross-Lingual",
                "description": "More reliable for short text, doesn't need prompt text",
                "requires_prompt_text": False
            }
        }
        return methods.get(method, super().get_method_info(method))
