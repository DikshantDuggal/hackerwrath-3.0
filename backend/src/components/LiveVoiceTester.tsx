import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Mic,
  MicOff,
  Radio,
  Volume2,
  RefreshCw,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  Globe,
  Sparkles,
  Zap,
} from 'lucide-react';
import { audioAlerts } from '../utils/audioAlerts';
import type { RiskAssessment } from '../hooks/useLiveDetection';

interface LiveVoiceTesterProps {
  onAssessmentUpdate: (assessment: RiskAssessment | null) => void;
  onAudioLevelChange?: (level: number) => void;
  activeRisk: RiskAssessment | null;
}

export default function LiveVoiceTester({
  onAssessmentUpdate,
  onAudioLevelChange,
  activeRisk,
}: LiveVoiceTesterProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [languageCode, setLanguageCode] = useState('auto');
  const [liveCaptions, setLiveCaptions] = useState<string[]>([]);
  const [activeSegmentText, setActiveSegmentText] = useState('');
  const [statusText, setStatusText] = useState('Ready for live microphone voice detection');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [callId] = useState(() => `mic-live-${Date.now().toString(36)}`);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const sliceTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  const sendAudioChunkToBackend = useCallback(
    async (blob: Blob) => {
      if (blob.size < 400) return; // Discard tiny noise
      setStatusText('Transcribing speech with Sarvam Saaras...');

      try {
        const formData = new FormData();
        formData.append('file', blob, 'audio.webm');
        formData.append('language_code', languageCode);

        // Step 1: Speech-To-Text via Sarvam API
        const transcribeRes = await fetch('/transcribe', {
          method: 'POST',
          body: formData,
        });

        if (!transcribeRes.ok) {
          const err = await transcribeRes.json().catch(() => ({}));
          throw new Error(err.detail || `Sarvam STT failed with HTTP ${transcribeRes.status}`);
        }

        const data = await transcribeRes.json();
        const text = (data.transcript || '').trim();

        if (!text) {
          setStatusText('Listening... (No speech detected in last slice)');
          return;
        }

        setActiveSegmentText(text);
        setLiveCaptions((prev) => [...prev, text]);
        setStatusText(`Detected (${data.language_code || 'auto'}): "${text.slice(0, 40)}..."`);

        // Step 2: Scam Risk Analysis via Multi-Segment Conversation Manager
        const segmentRes = await fetch(`/calls/${callId}/segments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text,
            speaker: 'caller',
            language_code: languageCode,
            start_seconds: 0,
            end_seconds: data.duration_seconds || 4,
            transcript_confidence: data.confidence || 0.94,
          }),
        });

        if (segmentRes.ok) {
          const update = await segmentRes.json();
          if (update.assessment) {
            onAssessmentUpdate(update.assessment);

            if (update.assessment.risk_level === 'HIGH' || update.assessment.risk_level === 'CRITICAL') {
              audioAlerts.playHighRiskAlert();
            } else if (update.assessment.risk_level === 'MEDIUM') {
              audioAlerts.playCautionAlert();
            } else {
              audioAlerts.playSafeChime();
            }
          }
        }
      } catch (err: any) {
        console.error('STT Pipeline error:', err);
        setErrorMsg(err.message || 'Error communicating with Sarvam AI backend');
        setStatusText('Error transcribing audio');
      }
    },
    [callId, languageCode, onAssessmentUpdate]
  );

  const startRecording = async () => {
    setErrorMsg(null);
    audioAlerts.playClick();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Setup audio analyzer for waveform and volume
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const actx = new AudioCtx();
      audioContextRef.current = actx;
      const source = actx.createMediaStreamSource(stream);
      const analyser = actx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Monitor audio volume
      const buffer = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
          sum += buffer[i];
        }
        const avg = sum / buffer.length / 255;
        setAudioLevel(avg);
        if (onAudioLevelChange) onAudioLevelChange(avg);
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // Setup MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      recordedChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordedChunksRef.current.push(e.data);
        }
      };

      recorder.start();
      setIsRecording(true);
      setStatusText('Listening live... speak clearly in Hindi, English, or Punjabi');

      // Periodic slice slice every 4.5 seconds
      sliceTimerRef.current = setInterval(() => {
        if (recorder.state === 'recording') {
          recorder.stop();
          setTimeout(() => {
            const blob = new Blob(recordedChunksRef.current, { type: mimeType });
            recordedChunksRef.current = [];
            sendAudioChunkToBackend(blob);

            // Restart recorder on active stream
            if (streamRef.current && streamRef.current.active) {
              try {
                const newRec = new MediaRecorder(streamRef.current, { mimeType });
                mediaRecorderRef.current = newRec;
                newRec.ondataavailable = (e) => {
                  if (e.data.size > 0) recordedChunksRef.current.push(e.data);
                };
                newRec.start();
              } catch {
                // Stream stopped
              }
            }
          }, 100);
        }
      }, 4500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Microphone access denied or unavailable');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    audioAlerts.playClick();
    if (sliceTimerRef.current) {
      clearInterval(sliceTimerRef.current);
      sliceTimerRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    setIsRecording(false);
    setAudioLevel(0);
    if (onAudioLevelChange) onAudioLevelChange(0);
    setStatusText('Microphone paused');

    // Flush final chunk
    if (recordedChunksRef.current.length > 0) {
      const blob = new Blob(recordedChunksRef.current, { type: 'audio/webm' });
      recordedChunksRef.current = [];
      sendAudioChunkToBackend(blob);
    }
  };

  return (
    <div className="glass-card p-6 md:p-8 space-y-6">
      {/* Top Banner & Language Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
            <h2 className="text-lg font-bold gradient-text">Live Microphone Voice Shield</h2>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Powered by Sarvam AI Saaras (v3) Speech-To-Text & Real-Time Negation Guard
          </p>
        </div>

        {/* Language selector */}
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-[var(--purple-candle)]" />
          <select
            value={languageCode}
            onChange={(e) => setLanguageCode(e.target.value)}
            disabled={isRecording}
            className="glass px-3 py-1.5 rounded-xl text-xs font-mono bg-black/40 text-white border-white/15 focus:outline-none focus:border-[var(--purple-bright)]"
          >
            <option value="auto">🌐 Auto Detect (Hi/En/Pa)</option>
            <option value="hi-IN">🇮🇳 Hindi (हिन्दी)</option>
            <option value="en-IN">🇬🇧 Indian English</option>
            <option value="pa-IN">🇵🇦 Punjabi (ਪੰਜਾਬੀ)</option>
          </select>
        </div>
      </div>

      {/* Main Mic Control + Visualizer */}
      <div className="flex flex-col items-center justify-center py-6 text-center space-y-5">
        <div className="relative">
          {/* Animated Waveform rings */}
          {isRecording && (
            <>
              <div
                className="absolute inset-0 rounded-full border-2 border-emerald-400/40 animate-ping"
                style={{ transform: `scale(${1 + audioLevel * 1.5})` }}
              />
              <div
                className="absolute -inset-4 rounded-full border border-purple-400/20 animate-pulse"
                style={{ transform: `scale(${1 + audioLevel * 1.8})` }}
              />
            </>
          )}

          {/* Central Mic Button */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`
              relative z-10 w-28 h-28 rounded-full flex items-center justify-center shadow-2xl
              transition-all duration-500 transform hover:scale-105 active:scale-95
              ${
                isRecording
                  ? 'bg-gradient-to-tr from-red-600 via-rose-600 to-red-500 text-white shadow-[0_0_50px_rgba(239,68,68,0.5)]'
                  : 'bg-gradient-to-tr from-[var(--purple-dim)] via-[var(--purple-glow)] to-[var(--green-accent)] text-white shadow-[0_0_40px_rgba(168,85,247,0.35)]'
              }
            `}
          >
            {isRecording ? <MicOff className="w-12 h-12" /> : <Mic className="w-12 h-12" />}
          </button>
        </div>

        <div>
          <h3 className="text-xl font-bold text-white">
            {isRecording ? 'Listening & Protecting Call...' : 'Tap Mic to Start Protection'}
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-1 max-w-md mx-auto">{statusText}</p>
        </div>

        {/* Live Audio Level Waveform Bar */}
        <div className="w-full max-w-xs flex items-center gap-1.5 h-6 px-4 glass rounded-full justify-center">
          {[...Array(24)].map((_, i) => {
            const h = Math.max(3, Math.sin(i * 0.4 + audioLevel * 10) * audioLevel * 20);
            return (
              <div
                key={i}
                className="w-1 rounded-full transition-all duration-75"
                style={{
                  height: `${isRecording ? h : 3}px`,
                  background:
                    activeRisk?.risk_level === 'HIGH'
                      ? '#ef4444'
                      : isRecording
                      ? '#34d399'
                      : 'rgba(255,255,255,0.2)',
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Error alert if any */}
      {errorMsg && (
        <div className="glass p-4 rounded-xl border-red-500/30 bg-red-950/20 text-red-300 text-xs flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Real-Time Live Transcript & Detected Keywords */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        {/* Left: Active Captions */}
        <div className="glass p-4 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
            <span>🗣️ Live Saaras Captions</span>
            {isRecording && <span className="text-emerald-400 text-[10px]">● Live Stream</span>}
          </div>

          <div className="h-32 overflow-y-auto space-y-2 pr-1 text-xs">
            {liveCaptions.length === 0 ? (
              <p className="text-[var(--text-muted)] italic text-center py-10">
                Transcribed caller phrases will stream here in real-time...
              </p>
            ) : (
              liveCaptions.map((cap, i) => (
                <div key={i} className="p-2 rounded-lg bg-white/5 border border-white/5 text-white/90">
                  {cap}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Active Risk Status */}
        <div className="glass p-4 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)] mb-2">
            <span>🛡️ Threat Assessment</span>
            <span
              className={`font-mono text-[10px] px-2 py-0.5 rounded-full border ${
                activeRisk?.risk_level === 'CRITICAL'
                  ? 'bg-rose-500/30 text-rose-300 border-rose-500/50 animate-pulse'
                  : activeRisk?.risk_level === 'HIGH'
                  ? 'bg-red-500/20 text-red-400 border-red-500/40'
                  : activeRisk?.risk_level === 'MEDIUM'
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              }`}
            >
              {activeRisk?.risk_level || 'MONITORING'}
            </span>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-white">
              {activeRisk?.caption || 'Awaiting caller speech for fraud intent parsing...'}
            </p>
            {activeRisk?.recommended_action && (
              <p className="text-xs text-[var(--green-accent)]">
                <span className="font-semibold">Action: </span>
                {activeRisk.recommended_action}
              </p>
            )}
          </div>

          <div className="pt-2 text-[10px] text-[var(--text-muted)] flex items-center justify-between border-t border-white/5 mt-2">
            <span>Score: {Math.round((activeRisk?.risk_score || 0) > 1 ? (activeRisk?.risk_score || 0) : (activeRisk?.risk_score || 0) * 100)}/100</span>
            <span>Confidence: {Math.round(((activeRisk?.confidence ?? 0.9) > 1 ? (activeRisk?.confidence ?? 0.9) : (activeRisk?.confidence ?? 0.9) * 100))}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
