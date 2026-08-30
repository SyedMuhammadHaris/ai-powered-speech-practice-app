import { useEffect, useRef, useState } from "react";
import { useMicRecorder } from "../hooks/useMicRecorder";
import { useWebSocketSession } from "../hooks/useWebSocketSession";
import MicButton from "./MicButton";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const STATUS_LABEL = {
  idle: "Ready",
  listening: "Listening...",
  thinking: "Thinking...",
  speaking: "Speaking...",
};

export default function ConversationView({ session, onEnd }) {
  const { connected, messages, status, error, sendAudioChunk, endTurn } = useWebSocketSession(session.session_id);
  const { start, stop, isRecording, error: micError } = useMicRecorder(sendAudioChunk);
  const [ending, setEnding] = useState(false);
  const transcriptEndRef = useRef(null);

  const transcript = [{ role: "assistant", text: session.opening_line }, ...messages];

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript.length]);

  useEffect(() => () => stop(), [stop]);

  const handleEnd = async () => {
    setEnding(true);
    stop();
    try {
      await fetch(`${API_BASE_URL}/session/${session.session_id}/end`, { method: "POST" });
    } finally {
      onEnd(session.session_id);
    }
  };

  return (
    <div className="conversation-view">
      <header>
        <h2>{session.topic}</h2>
        <span className="difficulty-badge">{session.difficulty}</span>
      </header>

      <div className="transcript">
        {transcript.map((turn, i) => (
          <p key={i} className={`turn ${turn.role}`}>
            <strong>{turn.role === "user" ? "You" : "Tutor"}:</strong> {turn.text}
          </p>
        ))}
        <div ref={transcriptEndRef} />
      </div>

      <div className="status-bar">
        {!connected ? "Connecting..." : STATUS_LABEL[status] || status}
      </div>

      {(error || micError) && <p className="error">{error || micError}</p>}

      <div className="controls">
        <MicButton
          isRecording={isRecording}
          onToggle={() => (isRecording ? stop() : start())}
          disabled={!connected || ending}
        />
        <button
          className="done-button"
          onClick={endTurn}
          disabled={!connected || ending || status !== "listening"}
        >
          I&apos;m done speaking
        </button>
        <button onClick={handleEnd} disabled={ending}>
          {ending ? "Ending..." : "End Session"}
        </button>
      </div>
    </div>
  );
}
