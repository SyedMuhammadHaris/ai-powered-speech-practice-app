import { useCallback, useRef, useState } from "react";

// Must match the backend's silero-vad window: 512 samples @ 16kHz (32ms).
const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 512;

/**
 * Captures mic audio via the Web Audio API and delivers raw PCM16 mono
 * 16kHz chunks to `onAudioChunk`, matching the backend's VAD/STT wire
 * protocol. Uses ScriptProcessorNode (not MediaRecorder) so we get raw
 * samples instead of an encoded container the backend would need to decode.
 */
export function useMicRecorder(onAudioChunk) {
  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          const s = Math.max(-1, Math.min(1, input[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        onAudioChunk(pcm16.buffer);
      };

      // Route through a silent gain node: ScriptProcessorNode only fires
      // onaudioprocess while connected to a destination.
      const silentGain = audioContext.createGain();
      silentGain.gain.value = 0;
      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioContext.destination);

      setIsRecording(true);
    } catch (err) {
      setError(err.message || "Microphone permission denied");
    }
  }, [onAudioChunk]);

  const stop = useCallback(() => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    audioContextRef.current?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    processorRef.current = null;
    sourceRef.current = null;
    audioContextRef.current = null;
    streamRef.current = null;
    setIsRecording(false);
  }, []);

  return { start, stop, isRecording, error };
}
