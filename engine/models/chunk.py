"""
Chunk Data Model
================

Enhanced chunk model with TTS configuration and audio effects.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AudioEffectConfig(BaseModel):
    """Configuration for a single audio effect"""

    type: str = Field(..., description="Effect type (reverb, speed, volume)")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Effect parameters"
    )

    @field_validator('type')
    @classmethod
    def validate_effect_type(cls, v):
        valid_types = ['reverb', 'speed', 'volume']
        if v not in valid_types:
            raise ValueError(f"Effect type must be one of {valid_types}")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "reverb", "params": {"intensity": 0.5}},
                {"type": "speed", "params": {"speed": 1.1}},
                {"type": "volume", "params": {"volume": 0.8}}
            ]
        }
    }


class TTSConfig(BaseModel):
    """TTS generation configuration for a chunk"""

    provider: str = Field(
        default="cosyvoice",
        description="TTS provider name (cosyvoice, chatterbox, etc.)"
    )
    inference_method: str = Field(
        default="auto",
        description="Inference method (auto, zero-shot, cross-lingual, etc.)"
    )
    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Generation speed multiplier"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "provider": "cosyvoice",
                    "inference_method": "zero-shot",
                    "speed": 1.0
                }
            ]
        }
    }


class Chunk(BaseModel):
    """
    Enhanced audiobook chunk with TTS and effects configuration.

    Backward compatible with old format:
    - If tts_config missing, uses defaults
    - If audio_effects missing, no effects applied
    """

    # Core fields (backward compatible)
    id: int = Field(..., alias="chunk_id", description="Chunk ID")
    text: str = Field(..., min_length=1, description="Text content")
    speaker: str = Field(..., description="Character/narrator name")
    emotion: str = Field(default="neutral", description="Emotion/tone")
    type: str = Field(
        default="dialogue",
        description="Chunk type (dialogue, narration, internal_monologue)"
    )

    # New fields for TTS control
    tts_config: Optional[TTSConfig] = Field(
        default=None,
        description="TTS generation configuration"
    )

    # New fields for audio effects
    audio_effects: List[AudioEffectConfig] = Field(
        default_factory=list,
        description="Audio effects to apply (in order)"
    )

    # Emotion prompt (for instruct2 method)
    emotion_prompt: Optional[str] = Field(
        default=None,
        description="Custom emotion instruction for TTS (e.g., 'in a tense whisper with urgency')"
    )

    # Optional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    @field_validator('type')
    @classmethod
    def validate_chunk_type(cls, v):
        valid_types = ['dialogue', 'narration', 'internal_monologue']
        if v not in valid_types:
            raise ValueError(f"Chunk type must be one of {valid_types}")
        return v

    def get_tts_provider(self) -> str:
        """Get TTS provider, with fallback to default"""
        if self.tts_config:
            return self.tts_config.provider
        return "cosyvoice"  # Default

    def get_inference_method(self) -> str:
        """Get inference method, with fallback to default"""
        if self.tts_config:
            return self.tts_config.inference_method
        return "auto"  # Default

    def has_effects(self) -> bool:
        """Check if chunk has any audio effects"""
        return len(self.audio_effects) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary (for JSON serialization)"""
        data = self.model_dump(by_alias=True)

        # Remove None values for cleaner JSON
        if self.tts_config is None:
            data.pop('tts_config', None)
        if not self.audio_effects:
            data.pop('audio_effects', None)
        if self.emotion_prompt is None:
            data.pop('emotion_prompt', None)
        if not self.metadata:
            data.pop('metadata', None)

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        """Create chunk from dictionary (backward compatible)"""
        # Handle both 'chunk_id' and 'id' fields
        if 'chunk_id' in data and 'id' not in data:
            data['id'] = data['chunk_id']

        return cls(**data)

    model_config = {
        "populate_by_name": True,  # Allow both 'id' and 'chunk_id'
        "json_schema_extra": {
            "examples": [
                {
                    "chunk_id": 1,
                    "text": "Hello world!",
                    "speaker": "NARRATOR",
                    "emotion": "neutral",
                    "type": "narration",
                    "tts_config": {
                        "provider": "cosyvoice",
                        "inference_method": "zero-shot",
                        "speed": 1.0
                    },
                    "audio_effects": [
                        {"type": "reverb", "params": {"intensity": 0.3}}
                    ]
                }
            ]
        }
    }
