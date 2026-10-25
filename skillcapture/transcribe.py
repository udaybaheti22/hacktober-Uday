"""
Audio transcription using faster-whisper.

Model: base, running on CPU with int8 quantisation.

The WhisperModel is expensive to initialise (~2-5 s, downloads ~150 MB on first
run). It is exposed via get_whisper_model() so the caller (app.py) can wrap it
with @st.cache_resource and reuse the same instance across Streamlit reruns.

Audio is decoded with PyAV directly (bypassing faster-whisper's internal
av.open call that passes metadata_errors="ignore", removed in PyAV 15+).
The decoded float32 numpy array is passed to WhisperModel.transcribe(), which
accepts either a file path or a numpy array.
"""

from __future__ import annotations

import io
import time


# ---------------------------------------------------------------------------
# Model accessor — call this once; wrap with @st.cache_resource in app.py
# ---------------------------------------------------------------------------

def get_whisper_model():
    """
    Initialise and return a WhisperModel (base, CPU, int8).

    Intended to be called through @st.cache_resource so the model is loaded
    once per server process, not once per Streamlit rerun.

    Returns (model, init_seconds) where init_seconds is the wall-clock time
    spent loading the model.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Run: pip install faster-whisper"
        ) from exc

    t0 = time.perf_counter()
    model = WhisperModel("base", device="cpu", compute_type="int8")
    elapsed = time.perf_counter() - t0
    return model, elapsed


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe_audio_with_model(model, audio_bytes: bytes) -> dict:
    """
    Transcribe pre-decoded audio using an already-loaded WhisperModel.

    Parameters
    ----------
    model       : WhisperModel instance (from get_whisper_model)
    audio_bytes : raw audio file bytes

    Returns
    -------
    {
        "transcript":         str,
        "segments":           list[dict],   # [{start, end, text}, ...]
        "decode_seconds":     float,        # PyAV decode time
        "transcribe_seconds": float,        # Whisper inference time
        "error":              str | None
    }
    """
    # Step 1: decode audio bytes → float32 numpy array
    t0 = time.perf_counter()
    audio_array, decode_error = _decode_audio_bytes(audio_bytes)
    decode_seconds = time.perf_counter() - t0

    if decode_error:
        return {
            "transcript": "",
            "segments": [],
            "decode_seconds": decode_seconds,
            "transcribe_seconds": 0.0,
            "error": decode_error,
        }

    # Step 2: transcribe
    t1 = time.perf_counter()
    try:
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

        transcribe_seconds = time.perf_counter() - t1
        transcript = " ".join(full_text_parts)
        return {
            "transcript": transcript,
            "segments": segments,
            "decode_seconds": decode_seconds,
            "transcribe_seconds": transcribe_seconds,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "transcript": "",
            "segments": [],
            "decode_seconds": decode_seconds,
            "transcribe_seconds": time.perf_counter() - t1,
            "error": f"Transcription failed: {exc}",
        }


# ---------------------------------------------------------------------------
# Audio decoding (PyAV, no metadata_errors kwarg)
# ---------------------------------------------------------------------------

def _decode_audio_bytes(audio_bytes: bytes) -> tuple:
    """
    Decode raw audio bytes to a mono float32 numpy array at 16 kHz.

    Returns (array, None) on success or (None, error_string) on failure.
    Does NOT use metadata_errors= so it works with all PyAV versions.
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

        with av.open(io.BytesIO(audio_bytes), mode="r") as container:
            frames = container.decode(audio=0)
            for frame in frames:
                frame.pts = None
                for resampled in resampler.resample(frame):
                    raw_buffer.write(resampled.to_ndarray().tobytes())

        # Flush resampler
        for resampled in resampler.resample(None):
            raw_buffer.write(resampled.to_ndarray().tobytes())

        import numpy as np
        audio = np.frombuffer(raw_buffer.getvalue(), dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0
        return audio, None

    except Exception as exc:  # noqa: BLE001
        return None, f"Audio decoding failed: {exc}"


# ---------------------------------------------------------------------------
# Timestamp formatting
# ---------------------------------------------------------------------------

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
