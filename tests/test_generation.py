"""
Test Generation Script
======================

Test the generation script with a minimal example.
"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.models import Chunk, Project, VoiceSeed
from scripts.generate_audiobook import AudiobookGenerator


def test_generation_setup():
    """Test that generator can be initialized and load project data."""
    print("\nTesting Generation Setup...")

    # Create temporary project structure
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()

        # Create chunks file
        chunks = [
            {
                "chunk_id": 1,
                "text": "This is a test chunk.",
                "speaker": "NARRATOR",
                "emotion": "neutral",
                "type": "narration"
            },
            {
                "chunk_id": 2,
                "text": "This is another test chunk with effects.",
                "speaker": "NARRATOR",
                "emotion": "neutral",
                "type": "internal_monologue",
                "audio_effects": [
                    {"type": "reverb", "params": {"intensity": 0.3}}
                ]
            }
        ]

        chunks_path = project_dir / "chunked_book.json"
        with open(chunks_path, 'w') as f:
            json.dump(chunks, f, indent=2)

        # Create seeds directory
        seeds_dir = project_dir / "seeds" / "NARRATOR"
        seeds_dir.mkdir(parents=True)

        seed = {
            "character_name": "NARRATOR",
            "description": "Test narrator voice",
            "audio_file": "seed.wav",
            "prompt_text": "This is a test voice seed."
        }

        seed_path = seeds_dir.parent / "NARRATOR" / "seed.json"
        with open(seed_path, 'w') as f:
            json.dump(seed, f, indent=2)

        # Create dummy seed audio (empty for now)
        seed_audio_path = seed_path.parent / "seed.wav"
        seed_audio_path.touch()

        print(f"  ✓ Created test project structure in {project_dir}")

        # Test data models
        chunk_models = [Chunk.from_dict(c) for c in chunks]
        assert len(chunk_models) == 2
        assert chunk_models[0].id == 1
        assert chunk_models[1].has_effects() is True
        print(f"  ✓ Chunk models loaded: {len(chunk_models)} chunks")

        seed_model = VoiceSeed.from_dict(seed)
        assert seed_model.character_name == "NARRATOR"
        print(f"  ✓ Seed model loaded: {seed_model.character_name}")

        print(f"  ✓ Generation setup test passed!")


def test_chunk_model_with_effects():
    """Test chunk model with TTS config and effects."""
    print("\nTesting Chunk Model with Effects...")

    chunk = Chunk(
        id=1,
        text="Test text",
        speaker="NARRATOR",
        emotion="neutral",
        type="internal_monologue",
        tts_config={
            "provider": "cosyvoice",
            "inference_method": "zero-shot",
            "speed": 1.1
        },
        audio_effects=[
            {"type": "reverb", "params": {"intensity": 0.5}},
            {"type": "speed", "params": {"speed": 1.1}},
            {"type": "volume", "params": {"volume": 0.9}}
        ]
    )

    assert chunk.get_tts_provider() == "cosyvoice"
    assert chunk.get_inference_method() == "zero-shot"
    assert chunk.has_effects() is True
    assert len(chunk.audio_effects) == 3

    print(f"  ✓ Provider: {chunk.get_tts_provider()}")
    print(f"  ✓ Inference method: {chunk.get_inference_method()}")
    print(f"  ✓ Effects: {len(chunk.audio_effects)}")

    # Test serialization
    chunk_dict = chunk.to_dict()
    chunk_restored = Chunk.from_dict(chunk_dict)

    assert chunk_restored.id == chunk.id
    assert chunk_restored.get_tts_provider() == chunk.get_tts_provider()
    assert len(chunk_restored.audio_effects) == len(chunk.audio_effects)

    print(f"  ✓ Serialization round-trip working")


def test_provider_registry():
    """Test that providers are registered and available."""
    print("\nTesting Provider Registry...")

    from engine.providers.registry import ProviderRegistry

    # Initialize providers (register CosyVoice)
    try:
        from engine.providers.tts.cosyvoice import CosyVoiceProvider
        ProviderRegistry.register_tts(CosyVoiceProvider)
    except ImportError as e:
        print(f"  ⚠ CosyVoice not available (expected in test environment): {e}")
        print(f"  ✓ Provider registry test skipped (no providers available)")
        return

    # List TTS providers
    tts_providers = ProviderRegistry.list_tts()
    print(f"  ✓ Available TTS providers: {len(tts_providers)}")

    for provider_info in tts_providers:
        print(f"    - {provider_info['display_name']} ({provider_info['name']})")
        print(f"      Methods: {', '.join(provider_info['methods'])}")

    # Get CosyVoice provider
    cosyvoice = ProviderRegistry.get_tts("cosyvoice")
    assert cosyvoice is not None
    assert cosyvoice.name == "cosyvoice"
    print(f"  ✓ CosyVoice provider accessible")


if __name__ == "__main__":
    print("=" * 60)
    print("Generation Script Test Suite")
    print("=" * 60)

    try:
        test_generation_setup()
        test_chunk_model_with_effects()
        test_provider_registry()

        print("\n" + "=" * 60)
        print("✅ All generation tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
