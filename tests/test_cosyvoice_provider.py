"""
Test CosyVoice Provider
========================

Simple test to verify CosyVoice provider registration and basic functionality.
"""

import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.providers.registry import ProviderRegistry
from engine.providers.tts.cosyvoice import CosyVoiceProvider


def test_provider_registration():
    """Test that CosyVoice can be registered"""
    print("Testing CosyVoice Provider Registration...")

    # Register provider
    ProviderRegistry.register_tts(CosyVoiceProvider)

    # Get provider
    provider = ProviderRegistry.get_tts("cosyvoice")
    assert provider is not None, "Failed to get registered provider"

    # Check properties
    assert provider.name == "cosyvoice"
    assert provider.display_name == "CosyVoice 2"
    assert "zero-shot" in provider.inference_methods
    assert "cross-lingual" in provider.inference_methods
    assert provider.supports_voice_cloning == True

    print("✓ Provider registered successfully")
    print(f"  Name: {provider.name}")
    print(f"  Display: {provider.display_name}")
    print(f"  Methods: {provider.inference_methods}")

    # List all TTS providers
    providers = ProviderRegistry.list_tts()
    print(f"\n✓ Total TTS providers: {len(providers)}")
    for p in providers:
        print(f"  - {p['display_name']} ({p['name']})")


def test_method_info():
    """Test method information retrieval"""
    print("\nTesting Method Information...")

    provider = ProviderRegistry.get_tts("cosyvoice")

    for method in provider.inference_methods:
        info = provider.get_method_info(method)
        print(f"\n  {info['display_name']}:")
        print(f"    Description: {info['description']}")
        print(f"    Requires prompt: {info['requires_prompt_text']}")


if __name__ == "__main__":
    print("=" * 60)
    print("CosyVoice Provider Test")
    print("=" * 60)

    try:
        test_provider_registration()
        test_method_info()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
