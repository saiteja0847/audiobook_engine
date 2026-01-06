"""
Audio Utilities
===============

Helper functions for audio processing and analysis.
"""

import torch
from typing import Tuple


def normalize_audio(audio: torch.Tensor, target_level: float = 0.95) -> torch.Tensor:
    """
    Normalize audio to target peak level.

    Args:
        audio: Audio tensor
        target_level: Target peak level (0.0-1.0), default 0.95

    Returns:
        Normalized audio
    """
    max_val = audio.abs().max()

    if max_val > 0:
        return audio * (target_level / max_val)

    return audio


def detect_clipping(audio: torch.Tensor, threshold: float = 0.99) -> bool:
    """
    Detect if audio is clipping.

    Args:
        audio: Audio tensor
        threshold: Clipping threshold (default 0.99)

    Returns:
        True if clipping detected
    """
    return (audio.abs() >= threshold).any().item()


def get_audio_stats(audio: torch.Tensor, sample_rate: int) -> dict:
    """
    Get statistics about audio.

    Args:
        audio: Audio tensor
        sample_rate: Sample rate in Hz

    Returns:
        {
            "duration": duration in seconds,
            "peak": peak amplitude,
            "rms": root mean square,
            "is_clipping": bool,
            "samples": number of samples
        }
    """
    duration = audio.shape[-1] / sample_rate
    peak = audio.abs().max().item()
    rms = torch.sqrt(torch.mean(audio ** 2)).item()
    is_clipping = detect_clipping(audio)
    samples = audio.shape[-1]

    return {
        "duration": duration,
        "peak": peak,
        "rms": rms,
        "is_clipping": is_clipping,
        "samples": samples
    }


def estimate_completion_ratio(
    audio: torch.Tensor,
    sample_rate: int,
    text: str,
    chars_per_second: float = 15.0,
    words_per_second: float = 2.5
) -> Tuple[float, str]:
    """
    Estimate if audio is complete based on text length.

    Args:
        audio: Audio tensor
        sample_rate: Sample rate in Hz
        text: Text that was synthesized
        chars_per_second: Average speaking rate (chars/sec)
        words_per_second: Average speaking rate (words/sec)

    Returns:
        (completion_ratio, assessment)
        - completion_ratio: 0.0-1.0+ (1.0 = expected duration)
        - assessment: "complete", "clipped", or "slow"
    """
    actual_duration = audio.shape[-1] / sample_rate

    # Estimate expected duration
    text_words = len(text.split())
    expected_from_chars = len(text) / chars_per_second
    expected_from_words = text_words / words_per_second
    expected_duration = (expected_from_chars + expected_from_words) / 2

    if expected_duration == 0:
        return 1.0, "complete"

    completion_ratio = actual_duration / expected_duration

    # Assess completion
    if completion_ratio < 0.75:
        assessment = "clipped"
    elif completion_ratio > 1.5:
        assessment = "slow"
    else:
        assessment = "complete"

    return completion_ratio, assessment


def fade_in_out(
    audio: torch.Tensor,
    sample_rate: int,
    fade_ms: int = 50
) -> torch.Tensor:
    """
    Apply fade in and fade out to audio.

    Args:
        audio: Audio tensor
        sample_rate: Sample rate in Hz
        fade_ms: Fade duration in milliseconds

    Returns:
        Audio with fades applied
    """
    fade_samples = int((fade_ms / 1000.0) * sample_rate)

    if audio.shape[-1] <= fade_samples * 2:
        return audio  # Too short for fades

    # Ensure 2D
    was_1d = audio.dim() == 1
    if was_1d:
        audio = audio.unsqueeze(0)

    # Create fade curves
    fade_in = torch.linspace(0, 1, fade_samples)
    fade_out = torch.linspace(1, 0, fade_samples)

    # Apply fades
    audio = audio.clone()
    audio[:, :fade_samples] *= fade_in
    audio[:, -fade_samples:] *= fade_out

    return audio.squeeze(0) if was_1d else audio


def merge_audio_chunks(
    chunks: list,
    sample_rate: int,
    silence_ms: int = 500
) -> torch.Tensor:
    """
    Merge multiple audio chunks with silence between them.

    Args:
        chunks: List of audio tensors
        sample_rate: Sample rate in Hz
        silence_ms: Silence duration between chunks (ms)

    Returns:
        Merged audio tensor
    """
    if not chunks:
        return torch.zeros(0)

    silence_samples = int((silence_ms / 1000.0) * sample_rate)
    silence = torch.zeros(silence_samples)

    # Ensure all chunks are 1D
    chunks_1d = []
    for chunk in chunks:
        if chunk.dim() > 1:
            chunk = chunk.squeeze(0)
        chunks_1d.append(chunk)

    # Interleave with silence
    result = []
    for i, chunk in enumerate(chunks_1d):
        result.append(chunk)
        if i < len(chunks_1d) - 1:  # No silence after last chunk
            result.append(silence)

    return torch.cat(result)
