#!/usr/bin/env python3
"""
Stable Audio background sound generator (runs in separate conda environment).
This script is called via subprocess from the main audiobook engine.
"""

import os
import sys
import argparse
from pathlib import Path

# Disable tokenizers parallelism to avoid fork warnings and hangs
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
import torchaudio
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond


def generate_background_audio(
    prompt: str,
    output_path: str,
    duration: float = 10.0,
    steps: int = 100,
    cfg_scale: float = 7.0,
    device: str = "mps"  # For M4 Mac
):
    """
    Generate background audio using Stable Audio Open.

    Args:
        prompt: Text description of the sound (e.g., "gentle rain ambience")
        output_path: Path to save the generated .wav file
        duration: Duration in seconds
        steps: Number of diffusion steps (higher = better quality, slower)
        cfg_scale: Classifier-free guidance scale (higher = more prompt adherence)
        device: Device to use ("mps" for Mac M4, "cuda" for GPU, "cpu" for CPU)
    """
    print(f"🎵 Generating background audio: '{prompt}'")
    print(f"   Duration: {duration}s")
    print(f"   Device: {device}")

    try:
        # Load Stable Audio Open model
        print("📦 Loading Stable Audio model...")
        model, model_config = get_pretrained_model("stabilityai/stable-audio-open-1.0")

        # Move to appropriate device
        if device == "mps" and torch.backends.mps.is_available():
            model = model.to("mps")
            print("   ✓ Using MPS (Apple Silicon)")
        elif device == "cuda" and torch.cuda.is_available():
            model = model.to("cuda")
            print("   ✓ Using CUDA")
        else:
            model = model.to("cpu")
            print("   ⚠️  Using CPU (slow)")

        # Get sample rate from model config
        sample_rate = model_config["sample_rate"]

        # Calculate sample_size based on desired duration
        # Stable Audio works in chunks, so we calculate the exact size we need
        sample_size = int(sample_rate * duration)

        # Round to nearest multiple of model's latent downsampling factor (usually 2048)
        latent_factor = 2048
        sample_size = ((sample_size + latent_factor - 1) // latent_factor) * latent_factor

        print(f"   Sample rate: {sample_rate} Hz")
        print(f"   Target duration: {duration}s")
        print(f"   Sample size: {sample_size} samples ({sample_size / sample_rate:.2f}s)")

        # Setup conditioning
        conditioning = [{
            "prompt": prompt,
            "seconds_start": 0,
            "seconds_total": duration
        }]

        # Generate audio
        print("🎨 Generating audio...")
        output = generate_diffusion_cond(
            model,
            steps=steps,
            cfg_scale=cfg_scale,
            conditioning=conditioning,
            sample_size=sample_size,
            sigma_min=0.3,
            sigma_max=500,
            sampler_type="dpmpp-3m-sde",
            device=model.device if hasattr(model, 'device') else device
        )

        # Output is (batch, channels, samples)
        # Convert to (channels, samples) for torchaudio
        print("💾 Converting and saving audio...")
        audio = output.squeeze(0).cpu()

        # Trim to exact duration (in case of any padding)
        target_samples = int(sample_rate * duration)
        if audio.shape[-1] > target_samples:
            audio = audio[:, :target_samples]
            print(f"   Trimmed to exact duration: {target_samples} samples")

        # Clean up model from memory BEFORE saving to avoid MPS hang
        del model
        del output
        if device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()
        elif device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Save audio file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        torchaudio.save(
            str(output_path),
            audio,
            sample_rate,
            encoding="PCM_S",
            bits_per_sample=16
        )

        print(f"✅ Background audio saved to: {output_path}")
        print(f"   Sample rate: {sample_rate} Hz")
        print(f"   Duration: {audio.shape[-1] / sample_rate:.2f}s")

        # Force flush output
        sys.stdout.flush()

        # Explicit cleanup
        del audio

        print("🏁 Done!")
        sys.stdout.flush()

        return str(output_path)

    except Exception as e:
        print(f"❌ Error generating background audio: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate background audio with Stable Audio")
    parser.add_argument("--prompt", required=True, help="Text description of the sound")
    parser.add_argument("--output", required=True, help="Output .wav file path")
    parser.add_argument("--duration", type=float, default=10.0, help="Duration in seconds")
    parser.add_argument("--steps", type=int, default=100, help="Diffusion steps")
    parser.add_argument("--cfg-scale", type=float, default=7.0, help="CFG scale")
    parser.add_argument("--device", default="mps", help="Device: mps, cuda, or cpu")

    args = parser.parse_args()

    try:
        generate_background_audio(
            prompt=args.prompt,
            output_path=args.output,
            duration=args.duration,
            steps=args.steps,
            cfg_scale=args.cfg_scale,
            device=args.device
        )
        print("✨ Script completed successfully")
        sys.stdout.flush()

        # Force immediate exit without cleanup (avoids hanging on background threads)
        os._exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.stdout.flush()
        os._exit(130)
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.stdout.flush()
        os._exit(1)


if __name__ == "__main__":
    main()
