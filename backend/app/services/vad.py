"""Wraps silero-vad to detect when the user has stopped talking (end of turn)."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch

SAMPLE_RATE = 16000
# silero-vad's JIT model requires exactly this many samples per call at 16kHz (32ms).
WINDOW_SAMPLES = 512

_model = None
_executor = ThreadPoolExecutor(max_workers=1)


def _load_model():
    global _model
    if _model is None:
        _model, _utils = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True)
    return _model


def _speech_probability_sync(samples: np.ndarray) -> float:
    model = _load_model()
    tensor = torch.from_numpy(samples)
    with torch.no_grad():
        return model(tensor, SAMPLE_RATE).item()


async def speech_probability(samples: np.ndarray) -> float:
    """Probability (0-1) that a WINDOW_SAMPLES-length chunk contains speech."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _speech_probability_sync, samples)


class TurnDetector:
    """Tracks speech/silence across incoming audio chunks to detect end-of-turn."""

    def __init__(self, silence_threshold_s: float = 0.7, speech_prob_threshold: float = 0.5):
        self.silence_threshold_s = silence_threshold_s
        self.speech_prob_threshold = speech_prob_threshold
        self.silence_duration_s = 0.0
        self.has_spoken = False

    async def feed(self, samples: np.ndarray) -> bool:
        """Feed one WINDOW_SAMPLES-length chunk; returns True once end-of-turn is detected."""
        prob = await speech_probability(samples)
        chunk_duration_s = len(samples) / SAMPLE_RATE
        if prob >= self.speech_prob_threshold:
            self.has_spoken = True
            self.silence_duration_s = 0.0
        else:
            self.silence_duration_s += chunk_duration_s

        return self.has_spoken and self.silence_duration_s >= self.silence_threshold_s

    def reset(self) -> None:
        self.has_spoken = False
        self.silence_duration_s = 0.0
