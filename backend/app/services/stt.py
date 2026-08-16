"""Wraps faster-whisper for turning buffered PCM audio into text."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from faster_whisper import WhisperModel

from app.config import settings

_model: WhisperModel | None = None
_executor = ThreadPoolExecutor(max_workers=1)


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    return _model


def _transcribe_sync(samples: np.ndarray) -> str:
    model = _get_model()
    segments, _info = model.transcribe(samples, language="en")
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe_audio(samples: np.ndarray) -> str:
    """Transcribe a mono float32 array of samples at 16kHz to text."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _transcribe_sync, samples)
