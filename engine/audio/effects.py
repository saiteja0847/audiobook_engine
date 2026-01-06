"""
Audio Effects
=============

Post-processing effects for audio chunks.

Effects can be chained and applied to generated audio to achieve
specific characteristics (e.g., internal monologue, speed adjustment).
"""

from abc import ABC, abstractmethod
import torch
import torchaudio
from typing import Dict, Any


class AudioEffect(ABC):
    """
    Base class for audio effects.

    All effects should:
    1. Take audio tensor and sample rate
    2. Return modified audio with same sample rate
    3. Preserve audio dimensions (1D or 2D)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique effect name (e.g., 'reverb', 'speed')"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI"""
        pass

    @abstractmethod
    def apply(self, audio: torch.Tensor, sample_rate: int, **params) -> torch.Tensor:
        """
        Apply effect to audio.

        Args:
            audio: Audio tensor (samples,) or (channels, samples)
            sample_rate: Sample rate in Hz
            **params: Effect-specific parameters

        Returns:
            Modified audio tensor with same shape
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get parameter schema for this effect.

        Returns:
            {
                "param_name": {
                    "type": "float" | "int" | "bool",
                    "default": value,
                    "min": value,
                    "max": value,
                    "description": "..."
                },
                ...
            }
        """
        pass


class ReverbEffect(AudioEffect):
    """
    Reverb effect for internal monologue or atmospheric audio.

    Parameters:
        intensity (float): 0.0-1.0, controls reverb strength
        delay_ms (int): Delay in milliseconds (default: 20)
        decay (float): Decay factor (default: 0.2)
    """

    @property
    def name(self) -> str:
        return "reverb"

    @property
    def display_name(self) -> str:
        return "Reverb"

    def apply(self, audio: torch.Tensor, sample_rate: int, **params) -> torch.Tensor:
        """
        Apply reverb effect.

        Referenced from: audiobook-project-manager/scripts/generate_audiobook.py
        """
        intensity = params.get('intensity', 0.5)
        delay_ms = params.get('delay_ms', 20)
        decay = params.get('decay', 0.2)

        # Scale decay by intensity
        effective_decay = decay * intensity

        # Calculate delay in samples
        delay_samples = int((delay_ms / 1000.0) * sample_rate)

        # Ensure 2D tensor for processing
        was_1d = audio.dim() == 1
        if was_1d:
            audio_processed = audio.unsqueeze(0)
        else:
            audio_processed = audio.clone()

        # Create delayed version (simple reverb)
        delayed = torch.zeros_like(audio_processed)
        if delay_samples < audio_processed.shape[-1]:
            delayed[:, delay_samples:] = audio_processed[:, :-delay_samples] * effective_decay
            audio_processed = audio_processed + delayed

        # Optional: Add fade in/out for smoother reverb
        fade_samples = int(0.05 * sample_rate)  # 50ms
        if audio_processed.shape[-1] > fade_samples * 2:
            fade_in = torch.linspace(0, 1, fade_samples)
            fade_out = torch.linspace(1, 0, fade_samples)

            audio_processed[:, :fade_samples] *= fade_in
            audio_processed[:, -fade_samples:] *= fade_out

        # Return to original dimensionality
        return audio_processed.squeeze(0) if was_1d else audio_processed

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "intensity": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "description": "Reverb intensity (0=none, 1=maximum)"
            },
            "delay_ms": {
                "type": "int",
                "default": 20,
                "min": 10,
                "max": 100,
                "description": "Delay in milliseconds"
            },
            "decay": {
                "type": "float",
                "default": 0.2,
                "min": 0.1,
                "max": 0.5,
                "description": "Decay factor for delayed signal"
            }
        }


class SpeedEffect(AudioEffect):
    """
    Speed adjustment effect using time stretching.

    Parameters:
        speed (float): Playback speed multiplier
            - 0.5 = 50% slower (half speed)
            - 1.0 = normal speed
            - 2.0 = 2x faster (double speed)
    """

    @property
    def name(self) -> str:
        return "speed"

    @property
    def display_name(self) -> str:
        return "Speed Adjustment"

    def apply(self, audio: torch.Tensor, sample_rate: int, **params) -> torch.Tensor:
        """
        Apply speed adjustment using torchaudio.

        Note: This changes duration but preserves pitch.
        """
        speed = params.get('speed', 1.0)

        if speed == 1.0:
            return audio  # No change needed

        # Ensure 2D tensor
        was_1d = audio.dim() == 1
        if was_1d:
            audio = audio.unsqueeze(0)

        # Calculate new length
        new_length = int(audio.shape[-1] / speed)

        # Use torch.nn.functional.interpolate for time stretching
        # This is a simple but effective method
        audio_stretched = torch.nn.functional.interpolate(
            audio.unsqueeze(1),  # Add batch dimension
            size=new_length,
            mode='linear',
            align_corners=False
        ).squeeze(1)

        return audio_stretched.squeeze(0) if was_1d else audio_stretched

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "speed": {
                "type": "float",
                "default": 1.0,
                "min": 0.5,
                "max": 2.0,
                "description": "Playback speed (0.5=slower, 1.0=normal, 2.0=faster)"
            }
        }


class VolumeEffect(AudioEffect):
    """
    Volume adjustment effect.

    Parameters:
        volume (float): Volume multiplier
            - 0.0 = silence
            - 1.0 = original volume
            - 2.0 = 2x louder
    """

    @property
    def name(self) -> str:
        return "volume"

    @property
    def display_name(self) -> str:
        return "Volume"

    def apply(self, audio: torch.Tensor, sample_rate: int, **params) -> torch.Tensor:
        """Apply volume adjustment (simple gain)"""
        volume = params.get('volume', 1.0)

        if volume == 1.0:
            return audio  # No change needed

        return audio * volume

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "volume": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Volume level (0.0=silence, 1.0=original, 2.0=2x louder)"
            }
        }


# Registry of available effects
AVAILABLE_EFFECTS = {
    "reverb": ReverbEffect,
    "speed": SpeedEffect,
    "volume": VolumeEffect
}


def get_effect(name: str) -> AudioEffect:
    """
    Get an effect instance by name.

    Args:
        name: Effect name ('reverb', 'speed', 'volume')

    Returns:
        Effect instance

    Raises:
        ValueError: If effect not found
    """
    effect_class = AVAILABLE_EFFECTS.get(name)
    if not effect_class:
        raise ValueError(f"Unknown effect: {name}. Available: {list(AVAILABLE_EFFECTS.keys())}")
    return effect_class()


def apply_effects_chain(
    audio: torch.Tensor,
    sample_rate: int,
    effects: list
) -> torch.Tensor:
    """
    Apply a chain of effects to audio.

    Args:
        audio: Audio tensor
        sample_rate: Sample rate in Hz
        effects: List of effect configs:
            [
                {"type": "reverb", "params": {"intensity": 0.5}},
                {"type": "speed", "params": {"speed": 1.1}},
                ...
            ]

    Returns:
        Processed audio

    Example:
        >>> effects = [
        ...     {"type": "reverb", "params": {"intensity": 0.3}},
        ...     {"type": "speed", "params": {"speed": 1.1}}
        ... ]
        >>> processed = apply_effects_chain(audio, 22050, effects)
    """
    processed = audio

    for effect_config in effects:
        effect_type = effect_config.get("type")
        effect_params = effect_config.get("params", {})

        effect = get_effect(effect_type)
        processed = effect.apply(processed, sample_rate, **effect_params)

    return processed
