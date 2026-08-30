import json
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import Message as MessageModel
from app.models import Session as SessionModel
from app.models import SessionFeedback as SessionFeedbackModel
from app.schemas import FeedbackResponse, SessionEndResponse, SessionStartRequest, SessionStartResponse
from app.services import difficulty, llm, stt, tts, vad

router = APIRouter(prefix="/session", tags=["session"])

PCM_BYTES_PER_SAMPLE = 2  # int16
WINDOW_BYTES = vad.WINDOW_SAMPLES * PCM_BYTES_PER_SAMPLE


def _pcm16_bytes_to_float32(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    body: SessionStartRequest,
    override_difficulty: str | None = None,
    db: DBSession = Depends(get_db),
) -> SessionStartResponse:
    if override_difficulty is not None and override_difficulty not in difficulty.VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"override_difficulty must be one of {difficulty.VALID_DIFFICULTIES}")

    profile = difficulty.get_or_create_profile(db)
    week = difficulty.current_week(profile.program_start_date)
    level = override_difficulty or difficulty.get_difficulty(week)

    session = SessionModel(topic=body.topic, difficulty=level)
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        opening_line = await llm.generate_opening_line(topic=body.topic, difficulty=level)
    except llm.LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.add(MessageModel(session_id=session.id, role="assistant", text=opening_line))
    db.commit()

    return SessionStartResponse(
        session_id=session.id,
        topic=session.topic,
        difficulty=session.difficulty,
        opening_line=opening_line,
    )


@router.websocket("/{session_id}/talk")
async def talk(websocket: WebSocket, session_id: str, db: DBSession = Depends(get_db)) -> None:
    session = db.get(SessionModel, session_id)
    if session is None:
        await websocket.close(code=4404, reason="Session not found")
        return

    await websocket.accept()

    history: list[dict[str, str]] = [{"role": m.role, "text": m.text} for m in session.messages]

    # Play the opening line (already generated + persisted in /session/start) over the WS.
    if history and history[-1]["role"] == "assistant":
        try:
            opening_audio = await tts.synthesize_speech(history[-1]["text"])
            await websocket.send_bytes(opening_audio)
        except Exception:
            pass  # audio playback is best-effort; text was already shown from /session/start

    detector = vad.TurnDetector()
    audio_buffer = bytearray()
    pcm_leftover = b""

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            turn_ended = False

            chunk_bytes = message.get("bytes")
            if chunk_bytes:
                audio_buffer.extend(chunk_bytes)
                pcm_leftover += chunk_bytes

                while len(pcm_leftover) >= WINDOW_BYTES:
                    window, pcm_leftover = pcm_leftover[:WINDOW_BYTES], pcm_leftover[WINDOW_BYTES:]
                    samples = _pcm16_bytes_to_float32(window)
                    if await detector.feed(samples):
                        turn_ended = True
                        break
            else:
                # Text frame: the student's "I'm done speaking" control message.
                # Ends the turn immediately on whatever audio is buffered so far,
                # instead of waiting for the VAD silence timeout (which can cut
                # off a mid-sentence pause).
                control_text = message.get("text")
                if not control_text:
                    continue
                try:
                    control = json.loads(control_text)
                except ValueError:
                    continue
                if control.get("type") != "end_turn" or not audio_buffer:
                    continue
                turn_ended = True

            if not turn_ended:
                continue

            user_samples = _pcm16_bytes_to_float32(bytes(audio_buffer))
            audio_buffer.clear()
            pcm_leftover = b""
            detector.reset()

            user_text = await stt.transcribe_audio(user_samples)
            if not user_text.strip():
                continue

            history.append({"role": "user", "text": user_text})
            db.add(MessageModel(session_id=session.id, role="user", text=user_text))
            db.commit()
            await websocket.send_json({"type": "transcript", "role": "user", "text": user_text})

            try:
                reply = await llm.generate_reply(session.topic, session.difficulty, history)
            except llm.LLMUnavailableError as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue

            history.append({"role": "assistant", "text": reply})
            db.add(MessageModel(session_id=session.id, role="assistant", text=reply))
            db.commit()
            await websocket.send_json({"type": "transcript", "role": "assistant", "text": reply})

            reply_audio = await tts.synthesize_speech(reply)
            await websocket.send_bytes(reply_audio)
    except WebSocketDisconnect:
        pass


@router.post("/{session_id}/end", response_model=SessionEndResponse)
def end_session(session_id: str, db: DBSession = Depends(get_db)) -> SessionEndResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is None:
        session.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

    return SessionEndResponse(session_id=session.id, ended_at=session.ended_at)


@router.get("/{session_id}/feedback", response_model=FeedbackResponse)
async def get_feedback(session_id: str, db: DBSession = Depends(get_db)) -> FeedbackResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.feedback is not None:
        fb = session.feedback
        return FeedbackResponse(
            session_id=session.id,
            summary_text=fb.summary_text,
            common_mistakes=fb.common_mistakes,
            vocab_suggestions=fb.vocab_suggestions,
        )

    history = [{"role": m.role, "text": m.text} for m in session.messages]
    try:
        result = await llm.generate_feedback(session.topic, session.difficulty, history)
    except llm.LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    fb = SessionFeedbackModel(
        session_id=session.id,
        summary_text=result["summary_text"],
        common_mistakes=result["common_mistakes"],
        vocab_suggestions=result["vocab_suggestions"],
    )
    db.add(fb)
    db.commit()

    return FeedbackResponse(
        session_id=session.id,
        summary_text=fb.summary_text,
        common_mistakes=fb.common_mistakes,
        vocab_suggestions=fb.vocab_suggestions,
    )
