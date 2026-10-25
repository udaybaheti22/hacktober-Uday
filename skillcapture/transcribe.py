"""
Audio transcription using faster-whisper.

Model: base, running on CPU with int8 quantisation.
Returns a plain transcript string with optional timestamps.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def transcribe_audio(audio_bytes: bytes, filename: str) -> dict:
    """
    Transcribe audio bytes using faster-whisper (base model, CPU int8).

    Returns:
        {
            "transcript": str,          # full plain text
            "segments": list[dict],     # [{start, end, text}, ...]
            "error": str | None
        }
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return {
            "transcript": "",
            "segments": [],
            "error": (
                "faster-whisper is not installed. "
                "Run: pip install faster-whisper"
            ),
        }

    # Write to a temp file so faster-whisper can open it by path
    suffix = Path(filename).suffix or ".audio"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
    except OSError as exc:
        return {"transcript": "", "segments": [], "error": f"Could not write temp file: {exc}"}

    try:
        # base model, CPU, int8 — balances speed and accuracy for a hackathon demo
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(tmp_path, beam_size=5)

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
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def segments_to_annotated_text(segments: list[dict]) -> str:
    """
    Convert a list of {start, end, text} segments into a readable
    timestamped transcript string passed to the model.

    Example output:
        [00:05] This is the first segment.
        [00:12] And this is the second.
    """
    lines = []
    for seg in segments:
        minutes = int(seg["start"] // 60)
        seconds = int(seg["start"] % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {seg['text']}")
    return "\n".join(lines)
