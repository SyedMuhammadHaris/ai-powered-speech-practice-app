import { useCallback, useEffect, useRef, useState } from "react";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";

/**
 * Owns the /session/{id}/talk WebSocket: connects on mount, streams outgoing
 * PCM audio chunks, and receives transcript JSON + AI reply audio (played
 * back as it arrives, queued so replies never overlap).
 */
export function useWebSocketSession(sessionId) {
  const wsRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | listening | thinking | speaking
  const [error, setError] = useState(null);

  const playNextAudio = useCallback(() => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    const blob = audioQueueRef.current.shift();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    isPlayingRef.current = true;
    setStatus("speaking");
    audio.onended = () => {
      URL.revokeObjectURL(url);
      isPlayingRef.current = false;
      setStatus("idle");
      playNextAudio();
    };
    audio.play().catch(() => {
      isPlayingRef.current = false;
    });
  }, []);

  useEffect(() => {
    if (!sessionId) return undefined;

    const ws = new WebSocket(`${WS_BASE_URL}/session/${sessionId}/talk`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError("WebSocket connection error");

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const data = JSON.parse(event.data);
        if (data.type === "transcript") {
          setMessages((prev) => [...prev, { role: data.role, text: data.text }]);
          if (data.role === "user") setStatus("thinking");
        } else if (data.type === "error") {
          setError(data.detail);
        }
      } else {
        audioQueueRef.current.push(event.data);
        playNextAudio();
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId, playNextAudio]);

  const sendAudioChunk = useCallback((chunk) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk);
      setStatus((prev) => (prev === "speaking" ? prev : "listening"));
    }
  }, []);

  return { connected, messages, status, error, sendAudioChunk };
}
