"""
Test Dia2 Provider
==================

Test the Dia2 TTS provider registration and configuration.
"""

import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.providers.registry import ProviderRegistry


def test_dia2_registration():
    """Test that Dia2 provider can be registered."""
    print("\nTesting Dia2 Provider Registration...")

    try:
        from engine.providers.tts.dia2 import Dia2Provider
        ProviderRegistry.register_tts(Dia2Provider)
        print("  ✓ Dia2 provider imported and registered")
    except ImportError as e:
        print(f"  ⚠ Dia2 not available (expected if not installed): {e}")
        print("  ℹ To install Dia2:")
        print("    git clone https://github.com/nari-labs/dia2.git ../dia2")
        print("    cd ../dia2")
        print("    uv sync")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

    return True


def test_dia2_provider_info():
    """Test Dia2 provider information."""
    print("\nTesting Dia2 Provider Info...")

    # Get provider
    dia2 = ProviderRegistry.get_tts("dia2")
    if not dia2:
        print("  ⚠ Dia2 provider not registered")
        return False

    # Check properties
    assert dia2.name == "dia2"
    assert dia2.display_name == "Dia2 (Nari Labs)"
    assert dia2.sample_rate == 44100
    assert dia2.supports_voice_cloning is True
    assert dia2.requires_prompt_text is False

    print(f"  ✓ Provider name: {dia2.display_name}")
    print(f"  ✓ Sample rate: {dia2.sample_rate}Hz")
    print(f"  ✓ Inference methods: {', '.join(dia2.inference_methods)}")
    print(f"  ✓ Voice cloning: {dia2.supports_voice_cloning}")

    return True


def test_dia2_in_registry():
    """Test Dia2 appears in registry list."""
    print("\nTesting Dia2 in Registry...")

    providers = ProviderRegistry.list_tts()
    dia2_info = next((p for p in providers if p['name'] == 'dia2'), None)

    if not dia2_info:
        print("  ⚠ Dia2 not found in registry")
        return False

    print(f"  ✓ Found in registry: {dia2_info['display_name']}")
    print(f"  ✓ Methods: {', '.join(dia2_info['methods'])}")
    print(f"  ✓ Sample rate: {dia2_info['sample_rate']}Hz")

    return True


def test_text_formatting():
    """Test speaker tag formatting."""
    print("\nTesting Text Formatting...")

    try:
        from engine.providers.tts.dia2 import Dia2Provider

        provider = Dia2Provider()

        # Test basic text formatting
        text = "Hello, this is a test."
        formatted = provider._format_text_with_speaker_tags(text)
        assert formatted.startswith("[S1]")
        print(f"  ✓ Basic text: {formatted}")

        # Test text that already has tags
        text_with_tags = "[S1] Already tagged text."
        formatted = provider._format_text_with_speaker_tags(text_with_tags)
        print(f"  ✓ Pre-tagged text: {formatted}")

        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Dia2 Provider Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Registration", test_dia2_registration()))

    # Only run other tests if registration succeeded
    if results[0][1]:
        results.append(("Provider Info", test_dia2_provider_info()))
        results.append(("Registry List", test_dia2_in_registry()))
        results.append(("Text Formatting", test_text_formatting()))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✅ All Dia2 provider tests passed!")
    else:
        print("\n⚠ Some tests failed or skipped (Dia2 may not be installed)")

    print("=" * 60)

    sys.exit(0 if all_passed else 1)
