"""
Audio Processing
=================

Audio effects and utilities for post-processing.
"""

from .effects import AudioEffect, ReverbEffect, SpeedEffect, VolumeEffect
from .utils import normalize_audio, detect_clipping

__all__ = [
    "AudioEffect",
    "ReverbEffect",
    "SpeedEffect",
    "VolumeEffect",
    "normalize_audio",
    "detect_clipping"
]
