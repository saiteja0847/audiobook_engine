"""
TTS Providers
=============

Text-to-Speech model providers.

Available providers:
- CosyVoice 2 ✓
- CosyVoice 3 ✓
- Chatterbox (to be implemented)
"""

from .cosyvoice import CosyVoiceProvider
from .cosyvoice3 import CosyVoice3Provider

__all__ = ["CosyVoiceProvider", "CosyVoice3Provider"]

# Chatterbox will be added later
# from .chatterbox import ChatterboxProvider
