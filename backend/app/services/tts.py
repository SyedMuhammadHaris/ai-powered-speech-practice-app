"""Wraps edge-tts for synthesizing the AI tutor's spoken replies."""

import edge_tts

DEFAULT_VOICE = "en-US-AriaNeural"


async def synthesize_speech(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """Synthesize text to MP3 audio bytes. edge-tts is natively async, no thread pool needed."""
    communicate = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
