"""Wraps Groq's OpenAI-compatible /chat/completions endpoint to drive the tutor conversation.

All conversational behavior (persona, topic adherence, correction style,
difficulty adaptation) is driven entirely by the system prompt built here —
there is no separate rules engine.
"""

import json

import httpx

from app.config import settings

PERSONA_RULES = """You are a friendly, encouraging English speaking-practice partner.
Rules:
- Stay on the given topic but flow naturally, like a real conversation, not a quiz.
- Ask follow-up questions to maximize how much the user speaks.
- Keep your responses short: 2-4 sentences.
- Correct mistakes gently and inline, without breaking the conversational flow.
- Adapt your vocabulary and sentence complexity to the difficulty level below.
- If the user drifts off-topic for too long, gently steer the conversation back."""

DIFFICULTY_GUIDANCE = {
    "beginner": "Use simple vocabulary and short sentences. Speak slowly and clearly in tone.",
    "intermediate": "Use everyday vocabulary and moderately complex sentences.",
    "advanced": "Use natural, idiomatic vocabulary and more complex sentence structures.",
}


class LLMUnavailableError(Exception):
    """Raised when Groq can't be reached, rejects the request, or returns an error."""


def _build_system_prompt(topic: str, difficulty: str) -> str:
    guidance = DIFFICULTY_GUIDANCE.get(difficulty, DIFFICULTY_GUIDANCE["beginner"])
    return f"{PERSONA_RULES}\n\nTopic for this session: {topic}\nDifficulty level: {difficulty}. {guidance}"


async def _chat(messages: list[dict[str, str]], json_mode: bool = False) -> str:
    if not settings.groq_api_key:
        raise LLMUnavailableError("GROQ_API_KEY is not set (add it to backend/.env)")

    payload = {"model": settings.groq_model, "messages": messages, "stream": False}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    try:
        async with httpx.AsyncClient(base_url=settings.groq_base_url, timeout=60.0) as client:
            response = await client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMUnavailableError(f"Groq request failed: {exc}") from exc

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


async def generate_opening_line(topic: str, difficulty: str) -> str:
    """Generate the AI tutor's opening line to kick off a new session."""
    messages = [
        {"role": "system", "content": _build_system_prompt(topic, difficulty)},
        {"role": "user", "content": "Start the conversation with a short, friendly opening line and question about the topic."},
    ]
    return await _chat(messages)


async def generate_reply(topic: str, difficulty: str, history: list[dict[str, str]]) -> str:
    """Generate the AI tutor's next reply given the full conversation history so far.

    `history` is a list of {"role": "user"|"assistant", "text": str} in order.
    """
    messages = [{"role": "system", "content": _build_system_prompt(topic, difficulty)}]
    messages += [{"role": turn["role"], "content": turn["text"]} for turn in history]
    return await _chat(messages)


async def generate_feedback(topic: str, difficulty: str, history: list[dict[str, str]]) -> dict:
    """Analyze the full transcript and produce a structured feedback report."""
    transcript = "\n".join(f"{turn['role']}: {turn['text']}" for turn in history)
    instructions = (
        "You are reviewing a transcript of an English-speaking practice session between a "
        "student (role=user) and their AI tutor (role=assistant). Analyze only the student's "
        "turns. Respond with a JSON object with exactly these keys: "
        '"summary_text" (a short encouraging paragraph summarizing performance), '
        '"common_mistakes" (a list of short strings describing grammar/vocabulary mistakes, '
        'each with a brief correction), "vocab_suggestions" (a list of short strings suggesting '
        "richer vocabulary or phrasing the student could have used)."
    )
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": f"Topic: {topic}\nDifficulty: {difficulty}\n\nTranscript:\n{transcript}"},
    ]
    raw = await _chat(messages, json_mode=True)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMUnavailableError(f"LLM returned invalid JSON feedback: {exc}") from exc

    return {
        "summary_text": parsed.get("summary_text", ""),
        "common_mistakes": parsed.get("common_mistakes", []),
        "vocab_suggestions": parsed.get("vocab_suggestions", []),
    }
