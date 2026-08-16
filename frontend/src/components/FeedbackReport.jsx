import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function FeedbackReport({ sessionId, onRestart }) {
  const [feedback, setFeedback] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/session/${sessionId}/feedback`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Failed to load feedback"))))
      .then((data) => !cancelled && setFeedback(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (error) {
    return (
      <div className="feedback-report">
        <p className="error">{error}</p>
        <button onClick={onRestart}>Start New Session</button>
      </div>
    );
  }

  if (!feedback) {
    return <div className="feedback-report">Generating feedback...</div>;
  }

  return (
    <div className="feedback-report">
      <h2>Session Feedback</h2>
      <p>{feedback.summary_text}</p>

      {feedback.common_mistakes.length > 0 && (
        <>
          <h3>Common Mistakes</h3>
          <ul>
            {feedback.common_mistakes.map((mistake, i) => (
              <li key={i}>{mistake}</li>
            ))}
          </ul>
        </>
      )}

      {feedback.vocab_suggestions.length > 0 && (
        <>
          <h3>Vocabulary Suggestions</h3>
          <ul>
            {feedback.vocab_suggestions.map((suggestion, i) => (
              <li key={i}>{suggestion}</li>
            ))}
          </ul>
        </>
      )}

      <button onClick={onRestart}>Start New Session</button>
    </div>
  );
}
