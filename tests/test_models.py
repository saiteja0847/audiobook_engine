"""
Test Data Models
================

Test Pydantic models for chunks, projects, and seeds.
"""

import sys
from pathlib import Path
import json

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.models import (
    Chunk,
    TTSConfig,
    AudioEffectConfig,
    Project,
    ProjectMetadata,
    VoiceSeed,
    SeedMetadata
)


def test_chunk_model():
    """Test Chunk model"""
    print("\nTesting Chunk Model...")

    # Test basic chunk creation
    chunk = Chunk(
        id=1,
        text="Hello world!",
        speaker="NARRATOR",
        emotion="neutral",
        type="narration"
    )

    assert chunk.id == 1
    assert chunk.text == "Hello world!"
    assert chunk.speaker == "NARRATOR"
    print(f"  ✓ Basic chunk created: ID={chunk.id}, Speaker={chunk.speaker}")

    # Test chunk with TTS config
    chunk_with_tts = Chunk(
        id=2,
        text="Test text",
        speaker="VIOLET",
        tts_config=TTSConfig(
            provider="cosyvoice",
            inference_method="zero-shot"
        )
    )

    assert chunk_with_tts.get_tts_provider() == "cosyvoice"
    assert chunk_with_tts.get_inference_method() == "zero-shot"
    print(f"  ✓ Chunk with TTS config: Provider={chunk_with_tts.get_tts_provider()}")

    # Test chunk with effects
    chunk_with_effects = Chunk(
        id=3,
        text="Internal thought",
        speaker="VIOLET",
        type="internal_monologue",
        audio_effects=[
            AudioEffectConfig(type="reverb", params={"intensity": 0.5}),
            AudioEffectConfig(type="speed", params={"speed": 1.1})
        ]
    )

    assert chunk_with_effects.has_effects() is True
    assert len(chunk_with_effects.audio_effects) == 2
    print(f"  ✓ Chunk with {len(chunk_with_effects.audio_effects)} audio effects")

    # Test JSON serialization
    chunk_dict = chunk_with_effects.to_dict()
    assert "chunk_id" in chunk_dict  # Uses alias
    assert chunk_dict["type"] == "internal_monologue"
    print(f"  ✓ JSON serialization working")

    # Test backward compatibility (old format)
    old_format = {
        "chunk_id": 10,
        "text": "Old format chunk",
        "speaker": "NARRATOR",
        "emotion": "neutral"
    }
    chunk_from_old = Chunk.from_dict(old_format)
    assert chunk_from_old.id == 10
    assert chunk_from_old.get_tts_provider() == "cosyvoice"  # Default
    print(f"  ✓ Backward compatibility with old format")


def test_project_model():
    """Test Project model"""
    print("\nTesting Project Model...")

    # Create new project
    project = Project.create_new(
        name="Test Audiobook",
        slug="test-audiobook"
    )

    assert project.name == "Test Audiobook"
    assert project.slug == "test-audiobook"
    print(f"  ✓ Project created: {project.name} ({project.slug})")

    # Test paths
    base_dir = Path("/projects")
    project_dir = project.get_project_dir(base_dir)
    assert project_dir == Path("/projects/test-audiobook")

    chunks_path = project.get_chunks_path(base_dir)
    assert chunks_path == Path("/projects/test-audiobook/chunked_book.json")
    print(f"  ✓ Path generation working")

    # Test stats update
    project.update_stats(total_chunks=100, generated_chunks=50, total_duration=300.0)
    assert project.metadata.total_chunks == 100
    assert project.metadata.generated_chunks == 50
    assert project.metadata.total_duration == 300.0
    print(f"  ✓ Stats: {project.metadata.total_chunks} chunks, {project.metadata.total_duration}s")

    # Test JSON serialization
    project_dict = project.to_dict()
    assert "slug" in project_dict
    assert "metadata" in project_dict
    print(f"  ✓ JSON serialization working")

    # Test from dict
    project_from_dict = Project.from_dict(project_dict)
    assert project_from_dict.slug == project.slug
    print(f"  ✓ Deserialization working")


def test_voice_seed_model():
    """Test VoiceSeed model"""
    print("\nTesting VoiceSeed Model...")

    # Create voice seed
    seed = VoiceSeed.create_new(
        character_name="VIOLET",
        description="Young female voice, determined",
        audio_file="seed.wav",
        prompt_text="Test transcript",
        gender="female",
        age="young"
    )

    assert seed.character_name == "VIOLET"
    assert seed.audio_file == "seed.wav"
    assert seed.prompt_text == "Test transcript"
    print(f"  ✓ Seed created: {seed.character_name}")

    # Test paths
    seeds_dir = Path("/seeds")
    audio_path = seed.get_audio_path(seeds_dir)
    assert audio_path == Path("/seeds/VIOLET/seed.wav")
    print(f"  ✓ Audio path: {audio_path}")

    # Test JSON serialization
    seed_dict = seed.to_dict()
    assert "character_name" in seed_dict
    assert "prompt_text" in seed_dict
    print(f"  ✓ JSON serialization working")

    # Test backward compatibility
    old_seed_format = {
        "character": "XADEN",  # Old field name
        "transcript": "Old transcript",  # Old field name
        "seed_file": "old_seed.wav",  # Old field name
        "description": "Male voice"
    }
    seed_from_old = VoiceSeed.from_dict(old_seed_format)
    assert seed_from_old.character_name == "XADEN"
    assert seed_from_old.prompt_text == "Old transcript"
    assert seed_from_old.audio_file == "old_seed.wav"
    print(f"  ✓ Backward compatibility working")


def test_model_validation():
    """Test model validation"""
    print("\nTesting Model Validation...")

    # Test invalid chunk type
    try:
        Chunk(
            id=1,
            text="Test",
            speaker="TEST",
            type="invalid_type"
        )
        assert False, "Should have raised validation error"
    except Exception as e:
        print(f"  ✓ Chunk type validation working")

    # Test invalid effect type
    try:
        AudioEffectConfig(
            type="invalid_effect",
            params={}
        )
        assert False, "Should have raised validation error"
    except Exception as e:
        print(f"  ✓ Effect type validation working")

    # Test TTS speed validation
    try:
        TTSConfig(
            provider="cosyvoice",
            inference_method="auto",
            speed=5.0  # Out of range
        )
        assert False, "Should have raised validation error"
    except Exception as e:
        print(f"  ✓ TTS speed validation working")


def test_json_round_trip():
    """Test full JSON serialization round trip"""
    print("\nTesting JSON Round Trip...")

    # Create complex chunk
    chunk = Chunk(
        id=5,
        text="Complex chunk with everything",
        speaker="VIOLET",
        emotion="determined",
        type="internal_monologue",
        tts_config=TTSConfig(
            provider="cosyvoice",
            inference_method="zero-shot",
            speed=1.1
        ),
        audio_effects=[
            AudioEffectConfig(type="reverb", params={"intensity": 0.3}),
            AudioEffectConfig(type="volume", params={"volume": 0.8})
        ],
        metadata={"custom_field": "custom_value"}
    )

    # Serialize to JSON
    json_str = json.dumps(chunk.to_dict(), indent=2)
    print(f"  ✓ Serialized to JSON ({len(json_str)} chars)")

    # Deserialize from JSON
    chunk_dict = json.loads(json_str)
    chunk_restored = Chunk.from_dict(chunk_dict)

    # Verify
    assert chunk_restored.id == chunk.id
    assert chunk_restored.text == chunk.text
    assert chunk_restored.get_tts_provider() == "cosyvoice"
    assert len(chunk_restored.audio_effects) == 2
    print(f"  ✓ Deserialized and verified")


if __name__ == "__main__":
    print("=" * 60)
    print("Data Models Test Suite")
    print("=" * 60)

    try:
        test_chunk_model()
        test_project_model()
        test_voice_seed_model()
        test_model_validation()
        test_json_round_trip()

        print("\n" + "=" * 60)
        print("✅ All model tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
