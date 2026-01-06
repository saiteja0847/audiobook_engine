#!/usr/bin/env python3
"""
Quick Dia2 Test - Test with different seed
"""

import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent))

from engine.providers.registry import ProviderRegistry
from engine.providers.tts.dia2 import Dia2Provider
import soundfile as sf

def main():
    print("=" * 70)
    print("Quick Dia2 Test (1B model, Xaden's voice)")
    print("=" * 70)

    # Register provider
    ProviderRegistry.register_tts(Dia2Provider)
    dia2 = ProviderRegistry.get_tts("dia2")

    # Test text (shorter for faster test)
    test_text = "Every Navarrian officer, whether they choose to be schooled as healers, scribes, infantry, or riders, is molded within these cruel walls over three years, honed into weapons to secure our mountainous borders from the violent invasion attempts of the kingdom of Poromiel and their gryphon riders."

    # Use Xaden's seed (male voice)
    project_dir = Path("projects/fourth-wing")
    seed_path = project_dir / "seeds" / "Xaden Riorson" / "seed.mp3"

    if not seed_path.exists():
        print(f"❌ Seed not found: {seed_path}")
        return

    print(f"\n📝 Text: {test_text}")
    print(f"🎤 Seed: {seed_path.name}")
    print(f"🔧 Method: fast (for speed)")
    print(f"\n⏳ Generating...")

    try:
        # Generate with fast preset
        audio = dia2.generate_audio(
            text=test_text,
            voice_seed_path=seed_path,
            inference_method="fast"
        )

        # Save
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "dia2_xaden_test.wav"

        audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
        if audio_np.ndim > 1:
            audio_np = audio_np.squeeze()

        # Get actual sample rate from model
        actual_sr = dia2.sample_rate

        print(f"\n📊 Audio info:")
        print(f"   Tensor shape: {audio.shape}")
        print(f"   NumPy shape: {audio_np.shape}")
        print(f"   Model sample rate: {actual_sr}Hz")

        sf.write(str(output_path), audio_np, actual_sr)

        duration = audio.shape[-1] / 44100
        print(f"\n✅ Success!")
        print(f"   Duration: {duration:.2f}s")
        print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"   Saved to: {output_path}")

        # Also save at 22050Hz to test if it sounds better
        output_path_22k = output_dir / "dia2_xaden_test_22khz.wav"
        sf.write(str(output_path_22k), audio_np, 22050)
        print(f"   Also saved at 22kHz: {output_path_22k}")

        print(f"\n🔊 Try playing BOTH files:")
        print(f"   1. {output_path.name} (44.1kHz)")
        print(f"   2. {output_path_22k.name} (22kHz - if this sounds normal, we have a sample rate issue)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
