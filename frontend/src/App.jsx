import { useState } from "react";
import ConversationView from "./components/ConversationView";
import FeedbackReport from "./components/FeedbackReport";
import TopicSelector from "./components/TopicSelector";
import "./App.css";

function App() {
  const [view, setView] = useState("home"); // home | conversation | feedback
  const [session, setSession] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const handleStart = (startedSession) => {
    setSession(startedSession);
    setView("conversation");
  };

  const handleEnd = (endedSessionId) => {
    setSessionId(endedSessionId);
    setView("feedback");
  };

  const handleRestart = () => {
    setSession(null);
    setSessionId(null);
    setView("home");
  };

  return (
    <main className="app">
      {view === "home" && <TopicSelector onStart={handleStart} />}
      {view === "conversation" && session && <ConversationView session={session} onEnd={handleEnd} />}
      {view === "feedback" && sessionId && <FeedbackReport sessionId={sessionId} onRestart={handleRestart} />}
    </main>
  );
}

export default App;
