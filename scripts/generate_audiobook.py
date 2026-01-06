"""
Audiobook Generation Script
===========================

Generate audiobook audio chunks using the provider system.

Features:
- Multi-provider TTS support (per-chunk selection)
- Audio effects chain processing
- Clipping detection and warnings
- Detailed logging and statistics
- Resume capability (skip already generated chunks)

Usage:
    python scripts/generate_audiobook.py --project PROJECT_SLUG [options]

Examples:
    # Generate all chunks with default settings
    python scripts/generate_audiobook.py --project my-audiobook

    # Force regeneration of all chunks
    python scripts/generate_audiobook.py --project my-audiobook --force

    # Generate specific chunk range
    python scripts/generate_audiobook.py --project my-audiobook --start 10 --end 20

    # Dry run to see what would be generated
    python scripts/generate_audiobook.py --project my-audiobook --dry-run
"""

import sys
from pathlib import Path
import argparse
import json
import time
from typing import List, Optional, Dict

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torchaudio

from engine.models import Chunk, Project, VoiceSeed
from engine.providers.registry import ProviderRegistry
from engine.audio.effects import apply_effects_chain
from engine.audio.utils import (
    normalize_audio,
    detect_clipping,
    get_audio_stats,
    estimate_completion_ratio
)
from engine.config import (
    BASE_DIR,
    PROJECTS_DIR,
    AUDIO_SAMPLE_RATE,
    MIN_VALID_AUDIO_DURATION
)


class AudiobookGenerator:
    """
    Main audiobook generation orchestrator.

    Handles:
    - Loading project data (chunks, seeds)
    - Per-chunk TTS generation with provider selection
    - Audio effects processing
    - Quality checks and warnings
    - Saving audio files
    """

    def __init__(self, project_slug: str, force: bool = False):
        self.project_slug = project_slug
        self.force = force

        # Paths
        self.project_dir = PROJECTS_DIR / project_slug
        self.audio_dir = self.project_dir / "audio"
        self.seeds_dir = self.project_dir / "seeds"
        self.chunks_path = self.project_dir / "chunked_book.json"
        self.project_path = self.project_dir / "project.json"

        # Data
        self.project: Optional[Project] = None
        self.chunks: List[Chunk] = []
        self.seeds: Dict[str, VoiceSeed] = {}

        # Stats
        self.stats = {
            "total_chunks": 0,
            "generated": 0,
            "skipped": 0,
            "failed": 0,
            "clipping_warnings": 0,
            "total_duration": 0.0,
            "start_time": 0.0
        }

    def load_project(self) -> bool:
        """Load project data and validate."""
        print(f"\n{'='*60}")
        print(f"Loading Project: {self.project_slug}")
        print(f"{'='*60}")

        # Check project directory
        if not self.project_dir.exists():
            print(f"❌ Error: Project directory not found: {self.project_dir}")
            return False

        # Load project metadata
        if self.project_path.exists():
            with open(self.project_path) as f:
                self.project = Project.from_dict(json.load(f))
            print(f"✓ Project: {self.project.name}")
        else:
            # Create minimal project
            self.project = Project.create_new(
                name=self.project_slug.replace("-", " ").title(),
                slug=self.project_slug
            )
            print(f"✓ Created new project metadata")

        # Load chunks
        if not self.chunks_path.exists():
            print(f"❌ Error: Chunks file not found: {self.chunks_path}")
            return False

        with open(self.chunks_path) as f:
            chunks_data = json.load(f)
            self.chunks = [Chunk.from_dict(c) for c in chunks_data]

        self.stats["total_chunks"] = len(self.chunks)
        print(f"✓ Loaded {len(self.chunks)} chunks")

        # Load voice seeds
        self._load_seeds()

        # Create audio directory
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Audio directory: {self.audio_dir}")

        return True

    def _load_seeds(self):
        """Load all voice seeds for this project."""
        if not self.seeds_dir.exists():
            print(f"⚠ Warning: Seeds directory not found: {self.seeds_dir}")
            return

        seed_count = 0
        for seed_file in self.seeds_dir.glob("*/seed.json"):
            try:
                with open(seed_file) as f:
                    seed_data = json.load(f)
                    seed = VoiceSeed.from_dict(seed_data)
                    self.seeds[seed.character_name] = seed
                    seed_count += 1
            except Exception as e:
                print(f"⚠ Warning: Failed to load seed {seed_file}: {e}")

        print(f"✓ Loaded {seed_count} voice seeds: {list(self.seeds.keys())}")

    def generate_chunk(self, chunk: Chunk, dry_run: bool = False, default_provider: Optional[str] = None, default_method: Optional[str] = None, default_speed: float = 1.0) -> bool:
        """
        Generate audio for a single chunk.

        Args:
            chunk: Chunk to generate
            dry_run: If True, only simulate generation
            default_provider: Default TTS provider if chunk doesn't specify one
            default_method: Default inference method if chunk doesn't specify one
            default_speed: Default playback speed if chunk doesn't specify one (0.5-2.0)

        Returns:
            True if successful, False if failed
        """
        chunk_id = chunk.id

        # Check if already generated (and not force mode)
        audio_path = self.audio_dir / f"chunk_{chunk_id}.wav"
        if audio_path.exists() and not self.force:
            print(f"  ⏭  Chunk {chunk_id}: Already exists (use --force to regenerate)")
            self.stats["skipped"] += 1
            return True

        if dry_run:
            print(f"  [DRY RUN] Would generate chunk {chunk_id}")
            return True

        # Get TTS provider
        provider_name = chunk.get_tts_provider() if chunk.tts_config else (default_provider or "cosyvoice")
        inference_method = chunk.get_inference_method() if chunk.tts_config else (default_method or "auto")
        speed = chunk.tts_config.speed if chunk.tts_config else default_speed

        tts_provider = ProviderRegistry.get_tts(provider_name)
        if not tts_provider:
            print(f"  ❌ Chunk {chunk_id}: TTS provider not found: {provider_name}")
            self.stats["failed"] += 1
            return False

        # Get voice seed
        speaker = chunk.speaker
        if speaker not in self.seeds:
            print(f"  ❌ Chunk {chunk_id}: Voice seed not found for speaker: {speaker}")
            self.stats["failed"] += 1
            return False

        seed = self.seeds[speaker]
        seed_audio_path = seed.get_audio_path(self.seeds_dir)

        if not seed_audio_path.exists():
            print(f"  ❌ Chunk {chunk_id}: Seed audio not found: {seed_audio_path}")
            self.stats["failed"] += 1
            return False

        # Generate audio
        print(f"\n  🎙️  Generating Chunk {chunk_id}...")
        print(f"      Text: {chunk.text[:60]}{'...' if len(chunk.text) > 60 else ''}")
        print(f"      Speaker: {speaker}")
        print(f"      Provider: {provider_name} ({inference_method})")
        if speed != 1.0:
            print(f"      Speed: {speed}x")

        # Get emotion from metadata (fallback for non-instruct2 methods)
        emotion = chunk.metadata.get('emotion', 'neutral') if chunk.metadata else 'neutral'

        # Show emotion control (prioritize emotion_prompt over metadata emotion)
        if chunk.emotion_prompt:
            print(f"      Emotion: {chunk.emotion_prompt}")
        elif emotion and emotion != 'neutral':
            print(f"      Emotion: {emotion} (from metadata)")

        try:
            start_time = time.time()

            # TTS generation
            # For instruct2: emotion_prompt is used for emotion control
            # For other methods: emotion is passed as kwarg (limited support)
            audio = tts_provider.generate_audio(
                text=chunk.text,
                voice_seed_path=seed_audio_path,
                prompt_text=seed.prompt_text,
                inference_method=inference_method,
                emotion=emotion if emotion != 'neutral' else None,
                emotion_prompt=chunk.emotion_prompt if chunk.emotion_prompt else '',
                speed=speed
            )

            if audio is None or audio.numel() == 0:
                print(f"  ❌ Chunk {chunk_id}: TTS returned empty audio")
                self.stats["failed"] += 1
                return False

            # Ensure 1D audio
            if audio.dim() > 1:
                audio = audio.squeeze()

            # Get stats before effects
            duration = audio.shape[-1] / AUDIO_SAMPLE_RATE

            # Check minimum duration
            if duration < MIN_VALID_AUDIO_DURATION:
                print(f"  ⚠️  Chunk {chunk_id}: Audio too short ({duration:.2f}s)")
                self.stats["clipping_warnings"] += 1

            # Check completion ratio
            completion_ratio, assessment = estimate_completion_ratio(
                audio, AUDIO_SAMPLE_RATE, chunk.text
            )

            if assessment == "clipped":
                print(f"  ⚠️  Chunk {chunk_id}: Possible clipping detected!")
                print(f"      Completion: {completion_ratio*100:.1f}% (expected ~100%)")
                self.stats["clipping_warnings"] += 1

            # Apply audio effects
            if chunk.has_effects():
                print(f"      Applying {len(chunk.audio_effects)} effects...")
                audio = apply_effects_chain(
                    audio,
                    AUDIO_SAMPLE_RATE,
                    [e.model_dump() for e in chunk.audio_effects]
                )

            # Normalize audio
            audio = normalize_audio(audio, target_level=0.95)

            # Check for clipping
            if detect_clipping(audio):
                print(f"  ⚠️  Chunk {chunk_id}: Clipping detected in normalized audio!")
                self.stats["clipping_warnings"] += 1

            # Save audio using soundfile (avoid torchcodec dependency)
            import soundfile as sf
            audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
            # Ensure 1D for mono audio
            if audio_np.ndim > 1:
                audio_np = audio_np.squeeze()
            sf.write(str(audio_path), audio_np, AUDIO_SAMPLE_RATE)

            # Final stats
            final_duration = audio.shape[-1] / AUDIO_SAMPLE_RATE
            generation_time = time.time() - start_time

            print(f"      ✓ Generated: {final_duration:.2f}s audio in {generation_time:.2f}s")
            print(f"      ✓ Saved: {audio_path.name}")

            self.stats["generated"] += 1
            self.stats["total_duration"] += final_duration

            return True

        except Exception as e:
            print(f"  ❌ Chunk {chunk_id}: Generation failed!")
            print(f"      Error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.stats["failed"] += 1
            return False

    def generate_all(
        self,
        start_chunk: Optional[int] = None,
        end_chunk: Optional[int] = None,
        dry_run: bool = False,
        default_provider: Optional[str] = None,
        default_method: Optional[str] = None
    ):
        """Generate all chunks (or a range)."""

        # Filter chunks by range
        chunks_to_generate = self.chunks
        if start_chunk is not None or end_chunk is not None:
            start_idx = (start_chunk - 1) if start_chunk else 0
            end_idx = end_chunk if end_chunk else len(self.chunks)
            chunks_to_generate = self.chunks[start_idx:end_idx]
            print(f"\n📝 Generating chunks {start_idx + 1} to {end_idx}")

        if dry_run:
            print(f"\n📝 [DRY RUN] Would generate {len(chunks_to_generate)} chunks")

        if default_provider:
            print(f"\n📝 Using default TTS provider: {default_provider}")
        if default_method:
            print(f"📝 Using default inference method: {default_method}")

        # Start generation
        self.stats["start_time"] = time.time()

        print(f"\n{'='*60}")
        print(f"Generating Audio Chunks")
        print(f"{'='*60}")

        for chunk in chunks_to_generate:
            self.generate_chunk(chunk, dry_run=dry_run, default_provider=default_provider, default_method=default_method)

        # Print summary
        self._print_summary()

        # Update project metadata
        if not dry_run:
            self._save_project_stats()

    def _print_summary(self):
        """Print generation summary statistics."""
        elapsed = time.time() - self.stats["start_time"]

        print(f"\n{'='*60}")
        print(f"Generation Summary")
        print(f"{'='*60}")
        print(f"Total chunks:       {self.stats['total_chunks']}")
        print(f"Generated:          {self.stats['generated']} ✓")
        print(f"Skipped:            {self.stats['skipped']}")
        print(f"Failed:             {self.stats['failed']} {'❌' if self.stats['failed'] > 0 else ''}")
        print(f"Clipping warnings:  {self.stats['clipping_warnings']} {'⚠️' if self.stats['clipping_warnings'] > 0 else ''}")
        print(f"")
        print(f"Total audio:        {self.stats['total_duration']:.1f}s ({self.stats['total_duration']/60:.1f}m)")
        print(f"Generation time:    {elapsed:.1f}s ({elapsed/60:.1f}m)")

        if self.stats["generated"] > 0:
            avg_time = elapsed / self.stats["generated"]
            print(f"Avg time/chunk:     {avg_time:.2f}s")

        print(f"{'='*60}\n")

    def _save_project_stats(self):
        """Update and save project statistics."""
        # Count actually generated chunks
        generated_count = len(list(self.audio_dir.glob("chunk_*.wav")))

        self.project.update_stats(
            total_chunks=self.stats["total_chunks"],
            generated_chunks=generated_count,
            total_duration=self.stats["total_duration"]
        )

        # Save project metadata
        with open(self.project_path, 'w') as f:
            json.dump(self.project.to_dict(), f, indent=2)

        print(f"✓ Updated project metadata: {self.project_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate audiobook audio chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all chunks
  python scripts/generate_audiobook.py --project my-audiobook

  # Force regenerate all chunks
  python scripts/generate_audiobook.py --project my-audiobook --force

  # Generate chunks 10-20
  python scripts/generate_audiobook.py --project my-audiobook --start 10 --end 20

  # Dry run
  python scripts/generate_audiobook.py --project my-audiobook --dry-run
        """
    )

    parser.add_argument(
        "--project",
        required=True,
        help="Project slug (directory name in projects/)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regenerate all chunks (ignore existing audio)"
    )

    parser.add_argument(
        "--start",
        type=int,
        help="Start chunk number (1-indexed)"
    )

    parser.add_argument(
        "--end",
        type=int,
        help="End chunk number (1-indexed, inclusive)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without actually generating"
    )

    args = parser.parse_args()

    # Create generator
    generator = AudiobookGenerator(
        project_slug=args.project,
        force=args.force
    )

    # Load project
    if not generator.load_project():
        sys.exit(1)

    # Generate audio
    try:
        generator.generate_all(
            start_chunk=args.start,
            end_chunk=args.end,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        generator._print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
