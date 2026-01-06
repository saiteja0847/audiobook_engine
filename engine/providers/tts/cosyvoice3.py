"""
CosyVoice 3 TTS Provider
========================

Wrapper for CosyVoice 3.0 text-to-speech model.
Improved accuracy: CER 0.81-1.21% (vs 1.45%), Speaker similarity 77.4-78.0% (vs 75.7%)
"""

import sys
import torch
import logging
from pathlib import Path
from typing import Optional

from ..base import TTSProvider
from ...config import COSYVOICE_PATH

logger = logging.getLogger(__name__)


class CosyVoice3Provider(TTSProvider):
    """
    CosyVoice 3.0 TTS Provider

    Improved model with better accuracy and speaker similarity.
    Supports the same inference methods as CosyVoice 2.

    External Dependencies:
        Requires CosyVoice 3 model installed at COSYVOICE_PATH
    """

    def __init__(self):
        self._model = None
        self._model_loaded = False
        self._model_path = COSYVOICE_PATH / "pretrained_models" / "CosyVoice3-0.5B"

        # Add CosyVoice to Python path
        if str(COSYVOICE_PATH) not in sys.path:
            sys.path.insert(0, str(COSYVOICE_PATH))
            sys.path.insert(0, str(COSYVOICE_PATH / "third_party" / "Matcha-TTS"))

    @property
    def name(self) -> str:
        return "cosyvoice3"

    @property
    def display_name(self) -> str:
        return "CosyVoice 3"

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
        return 24000  # CosyVoice 3 default (24kHz)

    def load_model(self) -> None:
        """Load CosyVoice 3 model into memory"""
        if self._model_loaded:
            logger.info("CosyVoice 3 model already loaded")
            return

        if not self._model_path.exists():
            raise FileNotFoundError(
                f"CosyVoice 3 model not found at: {self._model_path}\n"
                f"Please install CosyVoice 3 at: {COSYVOICE_PATH}"
            )

        try:
            # Import CosyVoice3 class (not base CosyVoice - that looks for cosyvoice.yaml)
            from cosyvoice.cli.cosyvoice import CosyVoice3
            from cosyvoice.utils.file_utils import load_wav

            logger.info(f"Loading CosyVoice 3 model from {self._model_path}")
            self._model = CosyVoice3(
                str(self._model_path),
                load_trt=False,
                fp16=False
            )
            self._load_wav = load_wav
            self._model_loaded = True
            logger.info("✓ CosyVoice 3 model loaded successfully")

        except ImportError as e:
            raise ImportError(
                f"Failed to import CosyVoice 3. Make sure it's installed at {COSYVOICE_PATH}\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load CosyVoice 3 model: {e}")

    def generate_audio(
        self,
        text: str,
        voice_seed_path: Path,
        prompt_text: Optional[str] = None,
        inference_method: str = "instruct2",
        **kwargs
    ) -> torch.Tensor:
        """
        Generate audio using CosyVoice 3.

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

        # Load voice seed as file path string (CosyVoice 3 expects path, not tensor)
        voice_seed_str = str(voice_seed_path)

        # Get emotion settings
        emotion = kwargs.get('emotion', None)
        emotion_prompt = kwargs.get('emotion_prompt', '')

        # Text cleaning: Keep audio tags for instruct2 and cross-lingual
        import re
        if inference_method in ['instruct2', 'cross-lingual']:
            # Keep all tags - they work!
            text_clean = text.strip()
        else:
            # Remove unsupported tags for zero-shot
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
                # CosyVoice 3 format: "You are a helpful assistant. {instruction}<|endofprompt|>"
                instruct_text = self._build_emotion_prompt_v3(emotion, emotion_prompt)
                logger.info(f"Generating audio using instruct2 (instruction: '{instruct_text}')")

                for output in self._model.inference_instruct2(
                    text_clean,
                    instruct_text,
                    voice_seed_str,
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
                    # CosyVoice 3: add prefix for cross-lingual
                    instruct_prefix = 'You are a helpful assistant.<|endofprompt|>'
                    for output in self._model.inference_cross_lingual(
                        instruct_prefix + text_clean,
                        voice_seed_str,
                        stream=stream,
                        speed=speed,
                        text_frontend=text_frontend
                    ):
                        audio = output['tts_speech']
                        break
                else:
                    if not prompt_text:
                        logger.warning("Zero-shot method requested but no prompt_text provided. Using cross-lingual instead.")
                        instruct_prefix = 'You are a helpful assistant.<|endofprompt|>'
                        for output in self._model.inference_cross_lingual(
                            instruct_prefix + text_clean,
                            voice_seed_str,
                            stream=stream,
                            speed=speed,
                            text_frontend=text_frontend
                        ):
                            audio = output['tts_speech']
                            break
                    else:
                        # CosyVoice 3: add prefix to prompt_text
                        prompt_with_prefix = f'You are a helpful assistant.<|endofprompt|>{prompt_text}'
                        for output in self._model.inference_zero_shot(
                            text_clean,
                            prompt_with_prefix,
                            voice_seed_str,
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
            raise RuntimeError(f"CosyVoice 3 generation failed: {e}")

    def _build_emotion_prompt_v3(self, emotion: Optional[str], custom_prompt: str = "") -> str:
        """
        Convert emotion to instruction prompt for CosyVoice 3 instruct2.
        Format: "You are a helpful assistant. {instruction}<|endofprompt|>"

        Args:
            emotion: Emotion name (e.g., "happy", "sad", "angry")
            custom_prompt: Custom emotion instruction (overrides emotion)

        Returns:
            Formatted instruction text for CosyVoice 3
        """
        # If custom prompt provided, use it (add prefix if not present)
        if custom_prompt:
            if '<|endofprompt|>' not in custom_prompt:
                return f'You are a helpful assistant. {custom_prompt}<|endofprompt|>'
            return custom_prompt

        # If no emotion, return just the prefix (neutral)
        if not emotion or emotion == "neutral":
            return 'You are a helpful assistant.<|endofprompt|>'

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

        instruction = emotion_prompts.get(emotion.lower(), "")
        if instruction:
            return f'You are a helpful assistant. {instruction}<|endofprompt|>'
        return 'You are a helpful assistant.<|endofprompt|>'

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
