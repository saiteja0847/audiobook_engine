"""
Test CosyVoice2 inference_instruct2 method with emotion prompts
================================================================

This tests the instruct2 API that supports:
- Emotion cues as text prompts
- Audio tags like [breath], [laughter], etc.
"""

import sys
import torch
import torchaudio
import soundfile as sf
from pathlib import Path

# Add CosyVoice to path
BASE_DIR = Path(__file__).parent.parent
COSYVOICE_PATH = BASE_DIR / "CosyVoice"
sys.path.insert(0, str(COSYVOICE_PATH))
sys.path.insert(0, str(COSYVOICE_PATH / "third_party" / "Matcha-TTS"))

from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav


def test_instruct2_with_emotion():
    """Test inference_instruct2 method with emotion prompts"""

    print("\n" + "=" * 70)
    print("CosyVoice2 inference_instruct2 Emotion Test")
    print("=" * 70)

    # Load model
    model_path = COSYVOICE_PATH / "pretrained_models" / "CosyVoice2-0.5B"
    print(f"\n📦 Loading CosyVoice2 from: {model_path}")

    try:
        model = CosyVoice2(
            str(model_path),
            load_jit=False,
            load_trt=False,
            load_vllm=False,
            fp16=False
        )
        print("✓ Model loaded")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return

    # Check if inference_instruct2 exists
    if not hasattr(model, 'inference_instruct2'):
        print("\n❌ Model does not have inference_instruct2 method!")
        print(f"   Available methods: {[m for m in dir(model) if 'inference' in m]}")
        return

    print("✓ inference_instruct2 method found!")

    # Load voice seed
    project_dir = Path("projects/fourth-wing")
    seed_path = project_dir / "seeds" / "Xaden Riorson" / "seed.mp3"

    if not seed_path.exists():
        print(f"\n❌ Seed not found: {seed_path}")
        return

    print(f"\n🎤 Loading voice seed: {seed_path.name}")

    # Load seed audio at 16kHz (required by CosyVoice)
    try:
        # Use librosa to load MP3, then convert
        import librosa
        audio_data, sr = librosa.load(str(seed_path), sr=16000, mono=True)
        prompt_speech_16k = torch.from_numpy(audio_data).unsqueeze(0)
        print(f"✓ Loaded seed: {prompt_speech_16k.shape} at {sr}Hz")
    except Exception as e:
        print(f"❌ Failed to load seed: {e}")
        return

    # Test cases with different emotion cues
    test_cases = [
        {
            "name": "Neutral (no emotion cue)",
            "text": "Violet Sorrengail was supposed to enter the Scribe Quadrant.",
            "emotion_cue": "",
            "output": "test_output/instruct2_neutral.wav"
        },
        {
            "name": "Tense with breath",
            "text": "She held her breath as the dragon circled overhead. [breath]",
            "emotion_cue": "in a tense, fearful whisper with urgency",
            "output": "test_output/instruct2_tense.wav"
        },
        {
            "name": "Confident and determined",
            "text": "I will not break.",
            "emotion_cue": "with quiet defiance and sharp intensity",
            "output": "test_output/instruct2_defiant.wav"
        },
        {
            "name": "Excited with laughter",
            "text": "We did it! [laughter]",
            "emotion_cue": "with excitement and joy, laughing",
            "output": "test_output/instruct2_happy.wav"
        },
        {
            "name": "Low and menacing",
            "text": "You will regret this decision.",
            "emotion_cue": "in a low, threatening tone with rising menace",
            "output": "test_output/instruct2_threat.wav"
        }
    ]

    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    # Run tests
    print("\n" + "=" * 70)
    print("Running Emotion Tests")
    print("=" * 70)

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {test['name']}")
        print(f"    Text: {test['text']}")
        print(f"    Emotion: '{test['emotion_cue']}'")

        try:
            # Call inference_instruct2
            result = model.inference_instruct2(
                test['text'],
                test['emotion_cue'],
                prompt_speech_16k=prompt_speech_16k,
                stream=False,
                speed=1.0
            )

            # Extract audio
            if isinstance(result, dict):
                audio = result['tts_speech']
            else:
                # If it returns generator, get first item
                for output in result:
                    audio = output['tts_speech']
                    break

            # Ensure 1D
            if audio.dim() > 1:
                audio = audio.squeeze()

            # Save
            audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
            sf.write(test['output'], audio_np, model.sample_rate)

            duration = len(audio_np) / model.sample_rate
            print(f"    ✓ Generated: {duration:.2f}s → {test['output']}")

        except Exception as e:
            print(f"    ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print(f"\nOutput files saved to: {output_dir.absolute()}")
    print("\n🎧 Listen to the files and compare:")
    print("   - Does emotion cue affect the voice?")
    print("   - Do audio tags [breath], [laughter] work?")
    print("   - Is voice cloning quality good?")


def test_tags_support():
    """Test which audio tags are supported"""

    print("\n" + "=" * 70)
    print("Testing Audio Tag Support")
    print("=" * 70)

    tags_to_test = [
        "[breath]",
        "[sigh]",
        "[laughter]",
        "[laugh]",
        "[gasp]",
        "[whisper]",
        "[shout]",
    ]

    print("\nTags to test:")
    for tag in tags_to_test:
        print(f"  - {tag}")

    print("\nNote: Run test_instruct2_with_emotion() to see actual results")


if __name__ == "__main__":
    print("\n🔬 CosyVoice2 inference_instruct2 Investigation")
    print("=" * 70)

    # Check if method exists
    print("\n1. Testing inference_instruct2 with emotion prompts...")
    test_instruct2_with_emotion()

    print("\n" + "=" * 70)
    print("\n2. Audio tags reference:")
    test_tags_support()
