import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const PRESETS = ["Daily routine", "Travel", "Food & cooking", "Movies & TV", "Work life", "Hobbies"];

export default function TopicSelector({ onStart }) {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/profile/difficulty`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Failed to load difficulty"))))
      .then((data) => setDifficulty(data.difficulty))
      .catch(() => setDifficulty(null));
  }, []);

  const startSession = async (chosenTopic) => {
    if (!chosenTopic.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: chosenTopic }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Failed to start session (${res.status})`);
      }
      onStart(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="topic-selector">
      <h1>SpeakPractice</h1>
      <p>Pick a topic and start talking.</p>
      {difficulty && <p className="difficulty-badge">Level: {difficulty}</p>}

      <div className="presets">
        {PRESETS.map((preset) => (
          <button key={preset} onClick={() => startSession(preset)} disabled={loading}>
            {preset}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          startSession(topic);
        }}
      >
        <input
          type="text"
          placeholder="Or type your own topic..."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !topic.trim()}>
          {loading ? "Starting..." : "Start Session"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
