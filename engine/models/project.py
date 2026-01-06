"""
Project Data Model
==================

Model for audiobook projects.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime


class ProjectMetadata(BaseModel):
    """Project metadata"""

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Project creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    version: str = Field(
        default="1.0",
        description="Project format version"
    )
    engine_version: str = Field(
        default="0.1.0",
        description="Audiobook engine version used"
    )

    # Statistics
    total_chunks: int = Field(default=0, description="Total number of chunks")
    generated_chunks: int = Field(default=0, description="Chunks with audio")
    total_duration: float = Field(default=0.0, description="Total audio duration (seconds)")

    # Custom metadata
    custom: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom user metadata"
    )


class Project(BaseModel):
    """
    Audiobook project.

    Manages book content, chunks, seeds, and generated audio.
    """

    # Core identification
    slug: str = Field(..., description="Project URL-safe identifier")
    name: str = Field(..., description="Project display name")

    # Content
    book_text: Optional[str] = Field(
        default=None,
        description="Original book text"
    )

    # Characters
    characters: List[str] = Field(
        default_factory=list,
        description="List of character names"
    )

    # Metadata
    metadata: ProjectMetadata = Field(
        default_factory=ProjectMetadata,
        description="Project metadata"
    )

    # Paths (relative to project directory)
    book_file: Optional[str] = Field(
        default="book.txt",
        description="Original book file path"
    )
    chunks_file: str = Field(
        default="chunked_book.json",
        description="Chunks JSON file path"
    )
    seeds_dir: str = Field(
        default="voice_seeds",
        description="Voice seeds directory"
    )
    audio_dir: str = Field(
        default="audiobook_chunks",
        description="Generated audio directory"
    )
    full_audio_file: str = Field(
        default="full_audiobook.wav",
        description="Combined audiobook file"
    )

    def get_project_dir(self, base_dir: Path) -> Path:
        """Get project directory path"""
        return base_dir / self.slug

    def get_chunks_path(self, base_dir: Path) -> Path:
        """Get path to chunks JSON file"""
        return self.get_project_dir(base_dir) / self.chunks_file

    def get_seeds_dir(self, base_dir: Path) -> Path:
        """Get voice seeds directory"""
        return self.get_project_dir(base_dir) / self.seeds_dir

    def get_audio_dir(self, base_dir: Path) -> Path:
        """Get audio output directory"""
        return self.get_project_dir(base_dir) / self.audio_dir

    def get_full_audio_path(self, base_dir: Path) -> Path:
        """Get full audiobook path"""
        return self.get_project_dir(base_dir) / self.full_audio_file

    def update_stats(self, total_chunks: int, generated_chunks: int, total_duration: float):
        """Update project statistics"""
        self.metadata.total_chunks = total_chunks
        self.metadata.generated_chunks = generated_chunks
        self.metadata.total_duration = total_duration
        self.metadata.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create project from dictionary"""
        return cls(**data)

    @classmethod
    def create_new(cls, name: str, slug: str) -> "Project":
        """Create a new project with defaults"""
        return cls(
            slug=slug,
            name=name,
            metadata=ProjectMetadata()
        )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "slug": "fourth-wing",
                    "name": "Fourth Wing",
                    "characters": ["NARRATOR", "VIOLET", "XADEN"],
                    "metadata": {
                        "total_chunks": 801,
                        "generated_chunks": 8,
                        "total_duration": 53.4
                    }
                }
            ]
        }
    }
