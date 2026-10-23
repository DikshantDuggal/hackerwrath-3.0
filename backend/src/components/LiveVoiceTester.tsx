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
  Trash2,
  Play,
  Send,
  ShieldAlert,
  Flame,
  PhoneCall,
  Clock,
  Headphones,
  Sliders,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { audioAlerts } from '../utils/audioAlerts';
import type { RiskAssessment, RAGClassificationResponse } from '../hooks/useLiveDetection';

interface StoredUtterance {
  id: string;
  text: string;
  timestamp: number;
  speaker: string;
  language: string;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  riskScore: number;
  flaggedKeywords: string[];
  safeAction?: string;
  source: 'microphone' | 'preset' | 'telegram_bridge' | 'dual_capture';
}

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
  const [captureMode, setCaptureMode] = useState<'mic' | 'dual'>('mic');
  const [languageCode, setLanguageCode] = useState('auto');
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [statusText, setStatusText] = useState('Ready for live voice detection');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [callId] = useState(() => `mic-live-${Date.now().toString(36)}`);
  const [audioLevel, setAudioLevel] = useState(0);
  const [storedUtterances, setStoredUtterances] = useState<StoredUtterance[]>([]);
  const [liveTranscriptPreview, setLiveTranscriptPreview] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSimulatingTelegram, setIsSimulatingTelegram] = useState(false);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const liveWsRef = useRef<WebSocket | null>(null);
  const animFrameRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const systemStreamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechRecognitionRef = useRef<any>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecordingSync();
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const stopRecordingSync = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (processorNodeRef.current) {
      try {
        processorNodeRef.current.disconnect();
      } catch {}
      processorNodeRef.current = null;
    }
    if (liveWsRef.current) {
      try {
        if (liveWsRef.current.readyState === WebSocket.OPEN) {
          liveWsRef.current.send(JSON.stringify({ type: 'stop' }));
        }
        liveWsRef.current.close();
      } catch {}
      liveWsRef.current = null;
    }
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch {}
      speechRecognitionRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (systemStreamRef.current) {
      systemStreamRef.current.getTracks().forEach((t) => t.stop());
      systemStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setIsRecording(false);
    setAudioLevel(0);
    if (onAudioLevelChange) onAudioLevelChange(0);
  };

  // Process text through scam detection engine
  const evaluateTranscript = useCallback(
    async (
      text: string,
      source: 'microphone' | 'preset' | 'telegram_bridge' = 'microphone',
      confidence: number = 0.95
    ) => {
      if (!text.trim()) return;

      try {
        const res = await fetch(`/calls/${callId}/segments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text.trim(),
            speaker: 'caller',
            language_code: languageCode,
            start_seconds: 0,
            end_seconds: 4,
            transcript_confidence: confidence,
          }),
        });

        if (res.ok) {
          const update = await res.json();
          const assessment: RiskAssessment = update.assessment;
          if (assessment) {
            // Concurrently query RAG semantic retrieval endpoint
            try {
              const ragRes = await fetch('/rag/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  text: text.trim(),
                  top_k: 3,
                  include_retrieved_examples: true,
                }),
              });
              if (ragRes.ok) {
                assessment.rag_classification = await ragRes.json();
              }
            } catch (ragErr) {
              console.debug('RAG query skipped:', ragErr);
            }

            onAssessmentUpdate(assessment);

            const keywords = (assessment.rule_analysis?.triggered_indicators || []).map(
              (i: any) => i.keyword_or_pattern
            );

            // Add to speech history
            const newUtterance: StoredUtterance = {
              id: `utt_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              text: text.trim(),
              timestamp: Date.now(),
              speaker: 'caller',
              language: languageCode,
              riskLevel: assessment.risk_level,
              riskScore: assessment.risk_score,
              flaggedKeywords: keywords,
              safeAction: assessment.recommended_action,
              source,
            };

            setStoredUtterances((prev) => [newUtterance, ...prev]);

            // Audio Alert
            if (assessment.risk_level === 'HIGH' || assessment.risk_level === 'CRITICAL') {
              audioAlerts.playHighRiskAlert();
            } else if (assessment.risk_level === 'MEDIUM') {
              audioAlerts.playCautionAlert();
            } else {
              audioAlerts.playSafeChime();
            }

            setStatusText(
              `Analyzed: "${text.slice(0, 32)}..." → ${assessment.risk_level} (${Math.round(
                assessment.risk_score
              )}%)`
            );
          }
        }
      } catch (err: any) {
        console.error('Error evaluating transcript:', err);
        setErrorMsg('Error evaluating speech with detection engine');
      }
    },
    [callId, languageCode, onAssessmentUpdate]
  );

  // Start Live Microphone Recording & Continuous WebSocket Stream
  const startRecording = async () => {
    setErrorMsg(null);
    setLiveTranscriptPreview('');
    setRecordingSeconds(0);
    chunksRef.current = [];
    audioAlerts.playClick();

    try {
      // 1. Microphone capture
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = micStream;

      // 2. Dual Mode: System / Telegram Audio capture if selected
      let systemStream: MediaStream | null = null;
      if (captureMode === 'dual') {
        try {
          systemStream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            audio: {
              echoCancellation: false,
              noiseSuppression: false,
              autoGainControl: false,
            },
          });
          systemStreamRef.current = systemStream;
        } catch (displayErr) {
          console.warn('System audio selection cancelled or unavailable:', displayErr);
          setStatusText('System audio sharing cancelled. Proceeding with Microphone only.');
        }
      }

      // Connect Direct WebSocket to Backend Live Stream
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/internal/live/browser-stream`;
      const ws = new WebSocket(wsUrl);
      liveWsRef.current = ws;

      ws.onopen = () => {
        setStatusText(
          captureMode === 'dual' && systemStream
            ? 'Dual Shield Active: Listening to Mic & System Audio...'
            : 'Live Shield Active: Streaming audio to detection engine...'
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'session_ready') {
            setStatusText(`Call monitoring connected (${data.callId}) — listening continuously...`);
          } else if (data.type === 'caption_chunk') {
            const textChunk = data.text || '';
            const newUtterance: StoredUtterance = {
              id: `utt_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
              text: textChunk,
              timestamp: Date.now(),
              speaker: data.speaker || 'caller',
              language: data.language || languageCode,
              riskLevel: data.riskLevel,
              riskScore: data.riskScore,
              flaggedKeywords: data.flaggedKeywords || [],
              safeAction: data.recommendedAction,
              source: data.source || (captureMode === 'dual' && systemStream ? 'dual_capture' : 'microphone'),
            };

            setStoredUtterances((prev) => [newUtterance, ...prev]);

            if (onAssessmentUpdate) {
              const triggered = (data.flaggedKeywords || []).map((k: string) => ({
                indicator_name: k,
                keyword_or_pattern: k,
                category: 'SUSPICIOUS_PHRASE',
                weight: 15,
                matched_text: k,
              }));

              onAssessmentUpdate({
                risk_score: data.riskScore ?? 0,
                risk_level: data.riskLevel ?? 'LOW',
                caption: data.text || textChunk,
                reasons: (data.flaggedKeywords && data.flaggedKeywords.length > 0)
                  ? data.flaggedKeywords.map((k: string) => `Flagged indicator: ${k}`)
                  : ['Analyzing conversation in real time'],
                recommended_action: data.recommendedAction || 'Continue with normal caution',
                confidence: 0.94,
                evidence: data.flaggedKeywords || [],
                rule_analysis: {
                  rule_score: data.riskScore ?? 0,
                  triggered_indicators: triggered,
                  suppressed_protective_matches: [],
                },
                contextual_analysis: {
                  caller_identity_claim: 'Call Participant',
                  claimed_organisation: 'Unknown',
                  intent_classification: (data.riskLevel === 'CRITICAL' || data.riskLevel === 'HIGH') ? 'Suspicious Solicitation' : 'General Speech',
                  possible_impersonation: Boolean(data.riskLevel === 'CRITICAL' || data.riskLevel === 'HIGH'),
                },
              } as any);
            }

            if (data.riskLevel === 'HIGH' || data.riskLevel === 'CRITICAL') {
              audioAlerts.playHighRiskAlert();
            } else if (data.riskLevel === 'MEDIUM') {
              audioAlerts.playCautionAlert();
            }

            setStatusText(
              `Live Caption: "${textChunk.slice(0, 30)}..." → ${data.riskLevel} (${Math.round(
                data.riskScore
              )}%)`
            );
          }
        } catch (wsErr) {
          console.warn('WS message parse error:', wsErr);
        }
      };

      ws.onerror = (err) => {
        console.warn('WebSocket streaming error; fallback active:', err);
      };

      // Web Audio Context for Waveform & Real-Time PCM16 Extraction
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const actx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = actx;

      const mixer = actx.createGain();
      mixer.gain.value = 1.0;

      const micSource = actx.createMediaStreamSource(micStream);
      micSource.connect(mixer);

      if (systemStream && systemStream.getAudioTracks().length > 0) {
        const sysSource = actx.createMediaStreamSource(systemStream);
        sysSource.connect(mixer);
      }

      const analyser = actx.createAnalyser();
      analyser.fftSize = 64;
      mixer.connect(analyser);
      analyserRef.current = analyser;

      const processor = actx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => {
        if (!liveWsRef.current || liveWsRef.current.readyState !== WebSocket.OPEN) return;
        const channelData = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(channelData.length);
        for (let i = 0; i < channelData.length; i++) {
          const s = Math.max(-1, Math.min(1, channelData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        liveWsRef.current.send(pcm16.buffer);
      };
      mixer.connect(processor);

      const muteGain = actx.createGain();
      muteGain.gain.value = 0;
      processor.connect(muteGain);
      muteGain.connect(actx.destination);
      processorNodeRef.current = processor;

      const buffer = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) sum += buffer[i];
        const avg = sum / buffer.length / 255;
        setAudioLevel(avg);
        if (onAudioLevelChange) onAudioLevelChange(avg);
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // Browser Web Speech recognition for instant zero-latency preview
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const recognizer = new SpeechRecognition();
          recognizer.continuous = true;
          recognizer.interimResults = true;
          recognizer.lang =
            languageCode === 'hi-IN'
              ? 'hi-IN'
              : languageCode === 'pa-IN'
              ? 'pa-IN'
              : languageCode === 'en-IN'
              ? 'en-IN'
              : 'hi-IN';
          recognizer.onresult = (event: any) => {
            let current = '';
            for (let i = 0; i < event.results.length; i++) {
              current += event.results[i][0].transcript + ' ';
            }
            setLiveTranscriptPreview(current.trim());
          };
          recognizer.start();
          speechRecognitionRef.current = recognizer;
        } catch (e) {
          console.warn('Web Speech recognizer init skipped:', e);
        }
      }

      setIsRecording(true);
      setStatusText('Listening live · Transcribing and analyzing speech in real time...');

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Microphone access denied. Please grant microphone permissions.');
      setIsRecording(false);
    }
  };

  // Stop Recording & Send Final Flush
  const stopRecording = () => {
    audioAlerts.playClick();
    if (liveWsRef.current && liveWsRef.current.readyState === WebSocket.OPEN) {
      try {
        liveWsRef.current.send(JSON.stringify({ type: 'stop' }));
      } catch {}
    }
    stopRecordingSync();
    setStatusText('Session ended. Audio buffers processed.');
  };

  // Test Simulation of Telegram VoIP Call Bridge
  const handleTestTelegramBridge = async () => {
    setIsSimulatingTelegram(true);
    setStatusText('Simulating Telegram VoIP Call Bridge Spike...');
    try {
      const res = await fetch('/internal/live/spike', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript:
            'Hello sir, I am calling from bank headquarters. Your account is blocked today. Share the 6-digit OTP immediately.',
          customer_name: 'Telegram Audio Caller',
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const assessment = data.assessment;
        onAssessmentUpdate(assessment);

        const newUtterance: StoredUtterance = {
          id: `utt_tg_${Date.now()}`,
          text: data.customer_name + ': ' + 'Your account is blocked today. Share the 6-digit OTP immediately.',
          timestamp: Date.now(),
          speaker: 'telegram_caller',
          language: 'mixed',
          riskLevel: assessment.risk_level,
          riskScore: assessment.risk_score,
          flaggedKeywords: data.flagged_keywords || ['OTP', 'ACCOUNT_SUSPENSION'],
          safeAction: assessment.recommended_action,
          source: 'telegram_bridge',
        };

        setStoredUtterances((prev) => [newUtterance, ...prev]);
        audioAlerts.playHighRiskAlert();
        setStatusText('Telegram VoIP Call Bridge: Intercepted & Flagged!');
      }
    } catch (err: any) {
      setErrorMsg('Failed to test Telegram bridge: ' + err.message);
    } finally {
      setIsSimulatingTelegram(false);
    }
  };

  const renderHighlightedText = (text: string, keywords: string[]) => {
    if (!keywords || keywords.length === 0) return text;
    const escaped = keywords
      .filter(Boolean)
      .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('|');
    if (!escaped) return text;

    const regex = new RegExp(`(${escaped})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <span
          key={i}
          className="px-1.5 py-0.5 rounded bg-rose-500/25 text-rose-300 border border-rose-500/40 font-bold mx-0.5"
        >
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="glass-card p-6 sm:p-8 space-y-8 border border-[#1E2536] rounded-3xl">
      {/* ─── Header: Clear & Spacious ─── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[#1E2536]">
        <div>
          <div className="flex items-center gap-2.5">
            <span className={`w-2.5 h-2.5 rounded-full ${isRecording ? 'bg-rose-500 animate-ping' : 'bg-[#00F0FF]'}`} />
            <h2 className="text-xl font-bold text-white tracking-wide">Live Microphone Shield</h2>
            <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/25">
              16kHz Continuous
            </span>
          </div>
          <p className="text-xs text-[#A2A9BA] mt-1">
            Put your phone on speaker. Suraksha listens to conversation audio and flags scam coercion in real time.
          </p>
        </div>

        {/* Secondary Settings Toggle Button */}
        <button
          onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
          className="px-3.5 py-1.5 rounded-full bg-[#11141C] hover:bg-[#1A202E] text-xs font-mono text-[#A2A9BA] hover:text-white border border-[#1E2536] transition-all flex items-center gap-2 cursor-pointer self-start sm:self-auto"
        >
          <Sliders className="w-3.5 h-3.5 text-[#00F0FF]" />
          <span>{showAdvancedSettings ? 'Hide Audio Settings' : 'Audio & Lang Settings'}</span>
          {showAdvancedSettings ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* ─── Collapsible Audio Settings Tray (Keeps main interface clean) ─── */}
      {showAdvancedSettings && (
        <div className="p-4 sm:p-5 rounded-2xl bg-[#090D16] border border-[#1E2536] space-y-4 animate-slide-up">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Audio Source */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-[#70798C] mb-1.5 flex items-center gap-1.5">
                <Headphones className="w-3.5 h-3.5 text-[#8B7CFF]" />
                Audio Ingestion Mode
              </label>
              <select
                value={captureMode}
                onChange={(e) => setCaptureMode(e.target.value as 'mic' | 'dual')}
                disabled={isRecording}
                className="w-full px-3 py-2 rounded-xl text-xs font-mono bg-[#11141C] text-white border border-[#1E2536] focus:outline-none focus:border-[#00F0FF]"
              >
                <option value="mic">🎙️ Microphone Only (Speakerphone mode)</option>
                <option value="dual">🎧 Dual Stream: Mic + Telegram Audio (Headphones)</option>
              </select>
            </div>

            {/* Language */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-[#70798C] mb-1.5 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-[#72D7E8]" />
                Speech Language
              </label>
              <select
                value={languageCode}
                onChange={(e) => setLanguageCode(e.target.value)}
                disabled={isRecording}
                className="w-full px-3 py-2 rounded-xl text-xs font-mono bg-[#11141C] text-white border border-[#1E2536] focus:outline-none focus:border-[#00F0FF]"
              >
                <option value="auto">🌐 Auto Detect (Hindi / English / Punjabi)</option>
                <option value="hi-IN">🇮🇳 Hindi (हिन्दी)</option>
                <option value="en-IN">🇬🇧 Indian English</option>
                <option value="pa-IN">🇵🇦 Punjabi (ਪੰਜਾਬੀ)</option>
              </select>
            </div>
          </div>

          <div className="pt-2 border-t border-[#1E2536] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
            <span className="text-[#A2A9BA] text-[11px]">
              Telegram Live VoIP Call Hook: Test WebSocket ingest via synthetic call spike.
            </span>
            <button
              onClick={handleTestTelegramBridge}
              disabled={isSimulatingTelegram}
              className="px-3 py-1.5 rounded-full bg-[#171B26] hover:bg-[#202636] text-[#8B7CFF] border border-[#1E2536] text-xs font-mono flex items-center gap-1.5 cursor-pointer"
            >
              <Sparkles className="w-3 h-3 text-[#F2C879]" />
              <span>{isSimulatingTelegram ? 'Testing...' : 'Test Telegram Bridge Spike'}</span>
            </button>
          </div>
        </div>
      )}

      {/* ─── MAIN MICROPHONE INTERACTION ARENA (Spacious, Central, Uncluttered) ─── */}
      <div className="flex flex-col items-center justify-center py-6 sm:py-10 text-center space-y-6">
        {/* Large Central Microphone Button */}
        <div className="relative">
          {/* Audio Pulsing Rings when recording */}
          {isRecording && (
            <>
              <div
                className="absolute -inset-4 rounded-full border-2 border-rose-500/40 animate-ping pointer-events-none"
                style={{ transform: `scale(${1 + audioLevel * 1.4})` }}
              />
              <div
                className="absolute -inset-8 rounded-full border border-[#00F0FF]/30 animate-pulse pointer-events-none"
                style={{ transform: `scale(${1 + audioLevel * 1.8})` }}
              />
            </>
          )}

          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isTranscribing}
            aria-label={isRecording ? 'Stop Recording' : 'Start Recording'}
            className={`
              relative z-10 w-32 h-32 sm:w-36 sm:h-36 rounded-full flex flex-col items-center justify-center
              transition-all duration-300 transform hover:scale-105 active:scale-95 cursor-pointer shadow-2xl
              ${
                isRecording
                  ? 'bg-gradient-to-tr from-rose-600 via-red-600 to-rose-500 text-white shadow-[0_0_50px_rgba(244,63,94,0.6)] animate-pulse'
                  : 'btn-cyan text-[#040810] shadow-[0_0_40px_rgba(0,240,255,0.45)]'
              }
            `}
          >
            {isRecording ? (
              <MicOff className="w-12 h-12 stroke-[2.2]" />
            ) : (
              <Mic className="w-12 h-12 stroke-[2.2]" />
            )}
            <span className="text-xs font-mono font-bold uppercase tracking-wider mt-2">
              {isRecording ? 'Stop Shield' : 'Tap to Listen'}
            </span>
          </button>
        </div>

        {/* Clear State Text */}
        <div className="space-y-1 max-w-md mx-auto">
          <div className="flex items-center justify-center gap-2">
            <span className={`text-base font-bold ${isRecording ? 'text-rose-400' : 'text-white'}`}>
              {isRecording
                ? `Recording Active (${formatTimer(recordingSeconds)})`
                : isTranscribing
                ? 'Transcribing & Evaluating Intent...'
                : 'Shield Standing By'}
            </span>
          </div>
          <p className="text-xs text-[#A2A9BA] leading-relaxed">{statusText}</p>
        </div>

        {/* Symmetrical Balanced Waveform Bar */}
        <div className="w-full max-w-xs flex items-center gap-1.5 h-7 px-4 bg-[#090D16] border border-[#1E2536] rounded-full justify-center">
          {[...Array(24)].map((_, i) => {
            const h = Math.max(3, Math.sin(i * 0.35 + audioLevel * 10) * audioLevel * 22);
            return (
              <div
                key={i}
                className="w-1 rounded-full transition-all duration-75"
                style={{
                  height: `${isRecording ? h : 3}px`,
                  background:
                    activeRisk?.risk_level === 'HIGH' || activeRisk?.risk_level === 'CRITICAL'
                      ? '#F08091'
                      : isRecording
                      ? '#00F0FF'
                      : 'rgba(241, 243, 248, 0.2)',
                }}
              />
            );
          })}
        </div>

        {/* Live Interim Transcript Bubble */}
        {isRecording && liveTranscriptPreview && (
          <div className="w-full max-w-lg p-4 rounded-2xl bg-[#090D16] border border-[#00F0FF]/30 text-xs text-white text-left animate-slide-up shadow-lg">
            <span className="text-[10px] font-mono text-[#00F0FF] font-semibold block mb-1">
              🎙️ Live Interim Speech:
            </span>
            <p className="italic text-[#E8ECF2] leading-relaxed">{liveTranscriptPreview}</p>
          </div>
        )}
      </div>

      {/* Error Alert with Permission Retry */}
      {errorMsg && (
        <div className="p-4 rounded-2xl border border-rose-500/40 bg-rose-950/20 text-rose-200 text-xs flex items-center justify-between gap-3 animate-slide-up">
          <div className="flex items-center gap-2.5">
            <AlertOctagon className="w-5 h-5 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => {
              setErrorMsg(null);
              startRecording();
            }}
            className="px-3 py-1 rounded-full bg-rose-500 text-white font-bold text-[11px] hover:bg-rose-600 transition-colors cursor-pointer shrink-0"
          >
            Retry Access
          </button>
        </div>
      )}

      {/* ─── QUICK TEST PHRASES (Clean & Symmetrical) ─── */}
      <div className="p-5 rounded-2xl bg-[#090D16] border border-[#1E2536] space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-[#A2A9BA] flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-[#F2C879]" />
            <span>One-Click Voice Test Phrases</span>
          </span>
          <span className="text-[10px] text-[#70798C] font-mono">Instant Dual Engine Check</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
          <button
            onClick={() =>
              evaluateTranscript('Sir, please share your 6 digit OTP right now to verify your bank account.', 'preset')
            }
            className="p-3 rounded-xl bg-[#11141C] hover:bg-[#1A202E] text-left border border-[#1E2536] hover:border-rose-500/50 text-white transition-all flex items-center justify-between group cursor-pointer"
          >
            <span className="line-clamp-1 group-hover:text-rose-300">🚨 "Please share your 6-digit OTP right now"</span>
            <Play className="w-3 h-3 shrink-0 text-rose-400 fill-current ml-2" />
          </button>

          <button
            onClick={() =>
              evaluateTranscript('Your electricity connection will be disconnected today. Download AnyDesk.', 'preset')
            }
            className="p-3 rounded-xl bg-[#11141C] hover:bg-[#1A202E] text-left border border-[#1E2536] hover:border-rose-500/50 text-white transition-all flex items-center justify-between group cursor-pointer"
          >
            <span className="line-clamp-1 group-hover:text-rose-300">🚨 "Power disconnected today, download AnyDesk"</span>
            <Play className="w-3 h-3 shrink-0 text-rose-400 fill-current ml-2" />
          </button>

          <button
            onClick={() =>
              evaluateTranscript('This is Officer Verma from CBI Cyber Cell. An arrest warrant is issued in your Aadhaar name.', 'preset')
            }
            className="p-3 rounded-xl bg-[#11141C] hover:bg-[#1A202E] text-left border border-[#1E2536] hover:border-rose-500/50 text-white transition-all flex items-center justify-between group cursor-pointer"
          >
            <span className="line-clamp-1 group-hover:text-rose-300">🚨 "Digital arrest by CBI, arrest warrant issued"</span>
            <Play className="w-3 h-3 shrink-0 text-rose-400 fill-current ml-2" />
          </button>

          <button
            onClick={() =>
              evaluateTranscript('Security reminder from your bank: never share your OTP or UPI PIN with anyone.', 'preset')
            }
            className="p-3 rounded-xl bg-[#11141C] hover:bg-[#1A202E] text-left border border-[#1E2536] hover:border-[#63D6A5]/50 text-white transition-all flex items-center justify-between group cursor-pointer"
          >
            <span className="line-clamp-1 group-hover:text-[#63D6A5]">✅ "Never share your OTP with anyone" (Negation Safe)</span>
            <Play className="w-3 h-3 shrink-0 text-[#63D6A5] fill-current ml-2" />
          </button>
        </div>
      </div>

      {/* ─── TEMPORARILY STORED SPEECH HISTORY ─── */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-[#A2A9BA] flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-[#00F0FF]" />
            <span>Live Speech History ({storedUtterances.length})</span>
          </span>

          {storedUtterances.length > 0 && (
            <button
              onClick={() => setStoredUtterances([])}
              className="text-[11px] text-[#70798C] hover:text-white flex items-center gap-1 hover:underline cursor-pointer"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear History</span>
            </button>
          )}
        </div>

        {storedUtterances.length === 0 ? (
          <div className="p-6 rounded-2xl bg-[#090D16] border border-[#1E2536] text-center text-xs text-[#70798C] italic">
            No speech has been recorded in this session. Tap the microphone above or click any test phrase to see real-time fraud analysis.
          </div>
        ) : (
          <div className="space-y-3 max-h-[340px] overflow-y-auto pr-1">
            {storedUtterances.map((utt) => {
              const isDanger = utt.riskLevel === 'HIGH' || utt.riskLevel === 'CRITICAL';
              const isCaution = utt.riskLevel === 'MEDIUM';

              return (
                <div
                  key={utt.id}
                  className={`p-4 rounded-2xl border transition-all animate-slide-up ${
                    isDanger
                      ? 'border-rose-500/40 bg-rose-950/10'
                      : isCaution
                      ? 'border-amber-500/40 bg-amber-950/10'
                      : 'border-[#1E2536] bg-[#090D16]'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] text-[#70798C] mb-2 font-mono">
                    <span className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${isDanger ? 'bg-rose-400' : 'bg-[#63D6A5]'}`} />
                      <span>{new Date(utt.timestamp).toLocaleTimeString()}</span>
                      <span className="text-[#1E2536]">·</span>
                      <span className="uppercase text-[10px] text-[#A2A9BA]">
                        {utt.source.replace('_', ' ')}
                      </span>
                    </span>

                    <span
                      className={`px-2.5 py-0.5 rounded-full font-bold text-[10px] border ${
                        utt.riskLevel === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                          : isDanger
                          ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                          : isCaution
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          : 'bg-[#63D6A5]/15 text-[#63D6A5] border-[#63D6A5]/30'
                      }`}
                    >
                      {utt.riskLevel} ({Math.round(utt.riskScore)}%)
                    </span>
                  </div>

                  <p className="text-xs font-medium text-white leading-relaxed mb-2">
                    {renderHighlightedText(utt.text, utt.flaggedKeywords)}
                  </p>

                  {utt.flaggedKeywords && utt.flaggedKeywords.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap mt-2 pt-2 border-t border-[#1E2536]">
                      <span className="text-[10px] font-mono text-rose-400 font-semibold flex items-center gap-1">
                        <Flame className="w-3 h-3 text-rose-400" />
                        Flagged Threats:
                      </span>
                      {utt.flaggedKeywords.map((kw, i) => (
                        <span
                          key={i}
                          className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  )}

                  {utt.safeAction && isDanger && (
                    <div className="mt-2 text-xs text-amber-200 bg-amber-950/20 p-2.5 rounded-xl border border-amber-500/30 flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
                      <span>{utt.safeAction}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
