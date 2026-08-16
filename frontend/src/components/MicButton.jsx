export default function MicButton({ isRecording, onToggle, disabled }) {
  return (
    <button
      className={`mic-button${isRecording ? " recording" : ""}`}
      onClick={onToggle}
      disabled={disabled}
    >
      {isRecording ? "Mute mic" : "Unmute mic"}
    </button>
  );
}
