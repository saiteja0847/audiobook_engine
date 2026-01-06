"""
Test Audio Effects
==================

Test audio effects and utilities.
"""

import sys
from pathlib import Path
import torch

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.audio.effects import (
    ReverbEffect,
    SpeedEffect,
    VolumeEffect,
    apply_effects_chain,
    get_effect
)
from engine.audio.utils import (
    normalize_audio,
    detect_clipping,
    get_audio_stats,
    estimate_completion_ratio
)


def test_reverb_effect():
    """Test reverb effect"""
    print("\nTesting Reverb Effect...")

    # Create test audio (1 second at 22050 Hz)
    sample_rate = 22050
    audio = torch.randn(sample_rate)  # 1D audio

    effect = ReverbEffect()

    # Test with default parameters
    processed = effect.apply(audio, sample_rate)
    assert processed.shape == audio.shape, "Audio shape changed"
    assert processed.dim() == audio.dim(), "Audio dimensions changed"

    # Test with custom parameters
    processed = effect.apply(audio, sample_rate, intensity=0.7, delay_ms=30)
    assert processed.shape == audio.shape

    print(f"  ✓ Reverb effect applied successfully")
    print(f"    Original: {audio.shape}")
    print(f"    Processed: {processed.shape}")


def test_speed_effect():
    """Test speed adjustment effect"""
    print("\nTesting Speed Effect...")

    sample_rate = 22050
    audio = torch.randn(sample_rate)  # 1 second

    effect = SpeedEffect()

    # Test normal speed (no change)
    processed = effect.apply(audio, sample_rate, speed=1.0)
    assert torch.allclose(processed, audio), "Speed=1.0 should not change audio"

    # Test slower speed
    processed_slow = effect.apply(audio, sample_rate, speed=0.5)
    assert processed_slow.shape[-1] > audio.shape[-1], "Slower should be longer"

    # Test faster speed
    processed_fast = effect.apply(audio, sample_rate, speed=2.0)
    assert processed_fast.shape[-1] < audio.shape[-1], "Faster should be shorter"

    print(f"  ✓ Speed effect working correctly")
    print(f"    Original: {audio.shape[-1]} samples (1.0s)")
    print(f"    0.5x speed: {processed_slow.shape[-1]} samples ({processed_slow.shape[-1]/sample_rate:.2f}s)")
    print(f"    2.0x speed: {processed_fast.shape[-1]} samples ({processed_fast.shape[-1]/sample_rate:.2f}s)")


def test_volume_effect():
    """Test volume adjustment effect"""
    print("\nTesting Volume Effect...")

    audio = torch.randn(1000) * 0.5  # Half amplitude

    effect = VolumeEffect()

    # Test normal volume (no change)
    processed = effect.apply(audio, 22050, volume=1.0)
    assert torch.allclose(processed, audio), "Volume=1.0 should not change audio"

    # Test louder
    processed_loud = effect.apply(audio, 22050, volume=2.0)
    assert torch.allclose(processed_loud, audio * 2.0)

    # Test quieter
    processed_quiet = effect.apply(audio, 22050, volume=0.5)
    assert torch.allclose(processed_quiet, audio * 0.5)

    print(f"  ✓ Volume effect working correctly")
    print(f"    Original peak: {audio.abs().max():.3f}")
    print(f"    2.0x volume peak: {processed_loud.abs().max():.3f}")
    print(f"    0.5x volume peak: {processed_quiet.abs().max():.3f}")


def test_effects_chain():
    """Test applying multiple effects in sequence"""
    print("\nTesting Effects Chain...")

    sample_rate = 22050
    audio = torch.randn(sample_rate)

    effects = [
        {"type": "reverb", "params": {"intensity": 0.3}},
        {"type": "volume", "params": {"volume": 0.8}},
        {"type": "speed", "params": {"speed": 1.1}}
    ]

    processed = apply_effects_chain(audio, sample_rate, effects)

    assert processed is not None, "Failed to apply effects chain"
    print(f"  ✓ Effects chain applied successfully")
    print(f"    Applied {len(effects)} effects")


def test_audio_utilities():
    """Test audio utility functions"""
    print("\nTesting Audio Utilities...")

    sample_rate = 22050
    audio = torch.randn(sample_rate) * 0.3  # 1 second, moderate amplitude (safely below clipping threshold)

    # Test normalization
    normalized = normalize_audio(audio, target_level=0.95)
    assert normalized.abs().max() <= 0.96, "Normalization failed"  # Allow small floating point error
    print(f"  ✓ Normalization: {audio.abs().max():.3f} → {normalized.abs().max():.3f}")

    # Test clipping detection
    clipping_audio = torch.ones(1000) * 1.5  # Definitely clipping
    assert detect_clipping(clipping_audio), "Failed to detect clipping"

    # Safe audio (definitely not clipping) - use controlled values
    safe_audio = torch.ones(1000) * 0.5
    assert not detect_clipping(safe_audio), "False positive for clipping"
    print(f"  ✓ Clipping detection working")

    # Test audio stats
    stats = get_audio_stats(audio, sample_rate)
    assert "duration" in stats
    assert "peak" in stats
    assert "rms" in stats
    print(f"  ✓ Audio stats:")
    print(f"    Duration: {stats['duration']:.2f}s")
    print(f"    Peak: {stats['peak']:.3f}")
    print(f"    RMS: {stats['rms']:.3f}")

    # Test completion ratio
    text = "This is a test sentence with some words."
    ratio, assessment = estimate_completion_ratio(audio, sample_rate, text)
    print(f"  ✓ Completion estimate: {ratio*100:.1f}% ({assessment})")


def test_effect_parameters():
    """Test getting effect parameters"""
    print("\nTesting Effect Parameters...")

    effects = [ReverbEffect(), SpeedEffect(), VolumeEffect()]

    for effect in effects:
        params = effect.get_parameters()
        print(f"\n  {effect.display_name} ({effect.name}):")
        for param_name, param_info in params.items():
            print(f"    - {param_name}: {param_info['type']} "
                  f"[{param_info.get('min', 'N/A')}-{param_info.get('max', 'N/A')}] "
                  f"(default: {param_info['default']})")


if __name__ == "__main__":
    print("=" * 60)
    print("Audio Effects Test Suite")
    print("=" * 60)

    try:
        test_reverb_effect()
        test_speed_effect()
        test_volume_effect()
        test_effects_chain()
        test_audio_utilities()
        test_effect_parameters()

        print("\n" + "=" * 60)
        print("✅ All audio effects tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
