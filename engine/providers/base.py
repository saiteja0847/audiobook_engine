"""
Base Provider Interfaces
========================

Abstract base classes for all provider types.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
import torch


class TTSProvider(ABC):
    """Base class for Text-to-Speech providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name (e.g., 'cosyvoice', 'chatterbox')
        Used for registry lookup and configuration.
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name for UI (e.g., 'CosyVoice 2', 'Chatterbox')
        """
        pass

    @property
    @abstractmethod
    def inference_methods(self) -> List[str]:
        """
        Available inference methods for this provider.
        Examples: ['auto', 'zero-shot', 'cross-lingual']
        """
        pass

    @property
    def supports_voice_cloning(self) -> bool:
        """
        Does this provider support voice cloning from audio samples?
        Default: True
        """
        return True

    @property
    def requires_prompt_text(self) -> bool:
        """
        Does this provider require prompt text along with audio seed?
        (e.g., CosyVoice zero-shot needs it, cross-lingual doesn't)
        Default: False
        """
        return False

    @abstractmethod
    def load_model(self) -> None:
        """
        Load the TTS model into memory.
        Called once during initialization.
        """
        pass

    @abstractmethod
    def generate_audio(
        self,
        text: str,
        voice_seed_path: Path,
        prompt_text: Optional[str] = None,
        inference_method: str = "auto",
        **kwargs
    ) -> torch.Tensor:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            voice_seed_path: Path to voice reference audio file
            prompt_text: Text spoken in the reference audio (if required)
            inference_method: Which method to use (provider-specific)
            **kwargs: Additional provider-specific parameters

        Returns:
            Audio tensor with shape (channels, samples) or (samples,)
        """
        pass

    @property
    def sample_rate(self) -> int:
        """
        Sample rate of generated audio.
        Default: 22050 Hz
        """
        return 22050

    def get_method_info(self, method: str) -> Dict[str, Any]:
        """
        Get information about a specific inference method.

        Returns:
            {
                "name": "zero-shot",
                "display_name": "Zero-Shot",
                "description": "High quality but needs matching prompt",
                "requires_prompt_text": True
            }
        """
        return {
            "name": method,
            "display_name": method.title(),
            "description": "",
            "requires_prompt_text": False
        }


class ChunkingProvider(ABC):
    """Base class for text chunking providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name (e.g., 'anthropic', 'openai')"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Claude (Anthropic)', 'GPT-4 (OpenAI)')"""
        pass

    @abstractmethod
    def chunk_text(
        self,
        text: str,
        max_chunk_size: int = 500,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into segments for audio generation.

        Args:
            text: The full text to chunk
            max_chunk_size: Maximum characters per chunk
            **kwargs: Provider-specific parameters

        Returns:
            List of chunks:
            [
                {
                    "id": 1,
                    "speaker": "NARRATOR",
                    "emotion": "neutral",
                    "text": "...",
                    "type": "dialogue" | "narration" | "internal_monologue"
                },
                ...
            ]
        """
        pass


class SeedProvider(ABC):
    """Base class for voice seed generation providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name (e.g., 'elevenlabs', 'cosyvoice')"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'ElevenLabs', 'CosyVoice')"""
        pass

    @abstractmethod
    def generate_seed(
        self,
        character_name: str,
        description: str,
        output_dir: Path,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a voice seed for a character.

        Args:
            character_name: Name of the character
            description: Character voice description
            output_dir: Where to save the seed files
            **kwargs: Provider-specific parameters

        Returns:
            {
                "audio_path": Path("seed.wav"),
                "prompt_text": "The text spoken in the seed",
                "metadata": {
                    "character": "...",
                    "description": "...",
                    "provider": "..."
                }
            }
        """
        pass
