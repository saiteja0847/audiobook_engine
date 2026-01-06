"""
Provider Registry
=================

Central registry for managing all providers (TTS, chunking, seeds).
"""

from typing import Dict, List, Optional, Type
from .base import TTSProvider, ChunkingProvider, SeedProvider


class ProviderRegistry:
    """
    Central registry for all providers.

    Usage:
        # Register a provider
        ProviderRegistry.register_tts(CosyVoiceProvider)

        # Get a provider
        tts = ProviderRegistry.get_tts("cosyvoice")

        # List all providers
        providers = ProviderRegistry.list_tts()
    """

    _tts_providers: Dict[str, TTSProvider] = {}
    _chunking_providers: Dict[str, ChunkingProvider] = {}
    _seed_providers: Dict[str, SeedProvider] = {}

    # === TTS Providers ===

    @classmethod
    def register_tts(cls, provider_class: Type[TTSProvider]) -> None:
        """Register a TTS provider"""
        provider = provider_class()
        cls._tts_providers[provider.name] = provider
        print(f"✓ Registered TTS provider: {provider.display_name} ({provider.name})")

    @classmethod
    def get_tts(cls, name: str) -> Optional[TTSProvider]:
        """Get a TTS provider by name"""
        return cls._tts_providers.get(name)

    @classmethod
    def list_tts(cls) -> List[Dict[str, any]]:
        """
        List all registered TTS providers.

        Returns:
            [
                {
                    "name": "cosyvoice",
                    "display_name": "CosyVoice 2",
                    "methods": ["auto", "zero-shot", "cross-lingual"],
                    "supports_voice_cloning": True,
                    "requires_prompt_text": False
                },
                ...
            ]
        """
        return [
            {
                "name": p.name,
                "display_name": p.display_name,
                "methods": p.inference_methods,
                "supports_voice_cloning": p.supports_voice_cloning,
                "requires_prompt_text": p.requires_prompt_text,
                "sample_rate": p.sample_rate
            }
            for p in cls._tts_providers.values()
        ]

    # === Chunking Providers ===

    @classmethod
    def register_chunking(cls, provider_class: Type[ChunkingProvider]) -> None:
        """Register a chunking provider"""
        provider = provider_class()
        cls._chunking_providers[provider.name] = provider
        print(f"✓ Registered chunking provider: {provider.display_name} ({provider.name})")

    @classmethod
    def get_chunking(cls, name: str) -> Optional[ChunkingProvider]:
        """Get a chunking provider by name"""
        return cls._chunking_providers.get(name)

    @classmethod
    def list_chunking(cls) -> List[Dict[str, str]]:
        """List all registered chunking providers"""
        return [
            {
                "name": p.name,
                "display_name": p.display_name
            }
            for p in cls._chunking_providers.values()
        ]

    # === Seed Providers ===

    @classmethod
    def register_seed(cls, provider_class: Type[SeedProvider]) -> None:
        """Register a seed provider"""
        provider = provider_class()
        cls._seed_providers[provider.name] = provider
        print(f"✓ Registered seed provider: {provider.display_name} ({provider.name})")

    @classmethod
    def get_seed(cls, name: str) -> Optional[SeedProvider]:
        """Get a seed provider by name"""
        return cls._seed_providers.get(name)

    @classmethod
    def list_seed(cls) -> List[Dict[str, str]]:
        """List all registered seed providers"""
        return [
            {
                "name": p.name,
                "display_name": p.display_name
            }
            for p in cls._seed_providers.values()
        ]

    # === Utility Methods ===

    @classmethod
    def get_default_tts(cls) -> Optional[TTSProvider]:
        """Get the default TTS provider (first registered)"""
        if cls._tts_providers:
            return next(iter(cls._tts_providers.values()))
        return None

    @classmethod
    def get_default_chunking(cls) -> Optional[ChunkingProvider]:
        """Get the default chunking provider (first registered)"""
        if cls._chunking_providers:
            return next(iter(cls._chunking_providers.values()))
        return None

    @classmethod
    def get_default_seed(cls) -> Optional[SeedProvider]:
        """Get the default seed provider (first registered)"""
        if cls._seed_providers:
            return next(iter(cls._seed_providers.values()))
        return None

    @classmethod
    def reset(cls) -> None:
        """Clear all registered providers (useful for testing)"""
        cls._tts_providers.clear()
        cls._chunking_providers.clear()
        cls._seed_providers.clear()
