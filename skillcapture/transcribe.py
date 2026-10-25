"""
Audio transcription using faster-whisper.

Model: base, running on CPU with int8 quantisation.

We decode the audio ourselves with PyAV (bypassing faster-whisper's internal
av.open call that passes metadata_errors="ignore", which was removed in PyAV 15+).
The decoded float32 numpy array is passed directly to WhisperModel.transcribe(),
which accepts either a file path or a numpy array.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path


def transcribe_audio(audio_bytes: bytes, filename: str) -> dict:
    """
    Transcribe audio bytes using faster-whisper (base model, CPU int8).

    Decodes audio via PyAV directly to avoid the metadata_errors API
    incompatibility between faster-whisper 1.2.1 and PyAV 15+.

    Returns:
        {
            "transcript": str,
            "segments":   list[dict],   # [{start, end, text}, ...]
            "error":      str | None
        }
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return {
            "transcript": "",
            "segments": [],
            "error": "faster-whisper is not installed. Run: pip install faster-whisper",
        }

    # Decode audio to a float32 numpy array ourselves, avoiding the broken
    # av.open(..., metadata_errors=...) call inside faster-whisper.
    audio_array, decode_error = _decode_audio_bytes(audio_bytes)

    if decode_error:
        return {"transcript": "", "segments": [], "error": decode_error}

    try:
        model = WhisperModel("base", device="cpu", compute_type="int8")
        # Pass numpy array directly — faster-whisper accepts this
        segments_iter, _info = model.transcribe(audio_array, beam_size=5)

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            segments.append(
                {
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                }
            )
            full_text_parts.append(seg.text.strip())

        transcript = " ".join(full_text_parts)
        return {"transcript": transcript, "segments": segments, "error": None}

    except Exception as exc:  # noqa: BLE001
        return {
            "transcript": "",
            "segments": [],
            "error": f"Transcription failed: {exc}",
        }


def _decode_audio_bytes(audio_bytes: bytes) -> tuple:
    """
    Decode raw audio bytes to a mono float32 numpy array at 16 kHz.

    Returns (array, None) on success or (None, error_string) on failure.
    Uses PyAV directly with no metadata_errors argument.
    """
    try:
        import av        # type: ignore
        import numpy as np
    except ImportError as exc:
        return None, f"Missing dependency: {exc}. Run: pip install av numpy"

    try:
        resampler = av.audio.resampler.AudioResampler(
            format="s16",
            layout="mono",
            rate=16000,
        )

        raw_buffer = io.BytesIO()

        # Open WITHOUT metadata_errors kwarg — compatible with all PyAV versions
        with av.open(io.BytesIO(audio_bytes), mode="r") as container:
            frames = container.decode(audio=0)
            for frame in frames:
                frame.pts = None
                for resampled in resampler.resample(frame):
                    raw_buffer.write(resampled.to_ndarray().tobytes())

        # Flush the resampler
        for resampled in resampler.resample(None):
            raw_buffer.write(resampled.to_ndarray().tobytes())

        audio = np.frombuffer(raw_buffer.getvalue(), dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0
        return audio, None

    except Exception as exc:  # noqa: BLE001
        return None, f"Audio decoding failed: {exc}"


def segments_to_annotated_text(segments: list[dict]) -> str:
    """
    Convert [{start, end, text}] segments into a timestamped transcript string.

    Example:
        [00:05] First segment.
        [00:12] Second segment.
    """
    lines = []
    for seg in segments:
        minutes = int(seg["start"] // 60)
        seconds = int(seg["start"] % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {seg['text']}")
    return "\n".join(lines)
