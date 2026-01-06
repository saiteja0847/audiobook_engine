"""
Voice Seed Data Model
=====================

Model for voice seeds (reference audio for TTS).
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime


class SeedMetadata(BaseModel):
    """Voice seed metadata"""

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Seed creation timestamp"
    )
    provider: str = Field(
        default="elevenlabs",
        description="Provider used to generate seed"
    )
    sample_rate: int = Field(
        default=16000,
        description="Audio sample rate (Hz)"
    )
    duration: float = Field(
        default=0.0,
        description="Audio duration (seconds)"
    )

    # Custom metadata
    custom: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata"
    )


class VoiceSeed(BaseModel):
    """
    Voice seed for a character.

    Contains reference audio and transcript for TTS voice cloning.
    """

    # Core identification
    character_name: str = Field(..., description="Character name")

    # Voice description
    description: str = Field(
        ...,
        description="Voice characteristics description"
    )
    gender: Optional[str] = Field(
        default=None,
        description="Voice gender (male, female, neutral)"
    )
    age: Optional[str] = Field(
        default=None,
        description="Voice age (young, middle-aged, old)"
    )
    accent: Optional[str] = Field(
        default=None,
        description="Voice accent"
    )

    # Audio files (relative paths)
    audio_file: str = Field(
        ...,
        description="Path to seed audio file (relative to seeds dir)"
    )
    prompt_text: str = Field(
        ...,
        description="Text spoken in the seed audio"
    )

    # Metadata
    metadata: SeedMetadata = Field(
        default_factory=SeedMetadata,
        description="Seed metadata"
    )

    def get_audio_path(self, seeds_dir: Path) -> Path:
        """Get absolute path to seed audio file"""
        return seeds_dir / self.character_name / self.audio_file

    def get_json_path(self, seeds_dir: Path) -> Path:
        """Get absolute path to seed JSON file"""
        return seeds_dir / self.character_name / "seed.json"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = self.model_dump()

        # Remove None values for cleaner JSON
        if self.gender is None:
            data.pop('gender', None)
        if self.age is None:
            data.pop('age', None)
        if self.accent is None:
            data.pop('accent', None)

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceSeed":
        """Create seed from dictionary"""
        # Handle backward compatibility with old format
        if 'character' in data and 'character_name' not in data:
            data['character_name'] = data['character']

        if 'speaker' in data and 'character_name' not in data:
            data['character_name'] = data['speaker']

        if 'transcript' in data and 'prompt_text' not in data:
            data['prompt_text'] = data['transcript']

        if 'seed_file' in data and 'audio_file' not in data:
            data['audio_file'] = data['seed_file']

        if 'audio_path' in data and 'audio_file' not in data:
            data['audio_file'] = data['audio_path']

        # Set default description if missing
        if 'description' not in data:
            data['description'] = f"Voice for {data.get('character_name', 'Unknown')}"

        return cls(**data)

    @classmethod
    def create_new(
        cls,
        character_name: str,
        description: str,
        audio_file: str,
        prompt_text: str,
        **kwargs
    ) -> "VoiceSeed":
        """Create a new voice seed"""
        return cls(
            character_name=character_name,
            description=description,
            audio_file=audio_file,
            prompt_text=prompt_text,
            **kwargs
        )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "character_name": "VIOLET",
                    "description": "Young female voice, determined and strong",
                    "gender": "female",
                    "age": "young",
                    "audio_file": "seed.wav",
                    "prompt_text": "The morning sun cast long shadows across the ancient stone walls.",
                    "metadata": {
                        "provider": "elevenlabs",
                        "sample_rate": 16000,
                        "duration": 4.2
                    }
                }
            ]
        }
    }
