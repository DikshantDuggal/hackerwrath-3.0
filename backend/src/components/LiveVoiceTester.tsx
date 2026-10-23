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
} from 'lucide-react';
import { audioAlerts } from '../utils/audioAlerts';
import type { RiskAssessment } from '../hooks/useLiveDetection';

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

            // Add to temporary speech history
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
              `Analyzed: "${text.slice(0, 35)}..." → ${assessment.risk_level} (${Math.round(
                assessment.risk_score
              )}/100)`
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

  // Send recorded Audio Blob to Sarvam STT
  const transcribeAudioBlob = useCallback(
    async (blob: Blob, liveFallbackText?: string) => {
      setIsTranscribing(true);
      setStatusText('Transcribing audio via Sarvam Saaras AI...');

      try {
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');
        formData.append('language_code', languageCode);

        const transcribeRes = await fetch('/transcribe', {
          method: 'POST',
          body: formData,
        });

        let transcript = '';
        let confidence = 0.94;

        if (transcribeRes.ok) {
          const data = await transcribeRes.json();
          transcript = (data.transcript || '').trim();
          confidence = data.confidence || 0.94;
        }

        // If Sarvam returned empty (or failed due to short audio), use Web Speech live preview as fallback
        if (!transcript && liveFallbackText && liveFallbackText.trim()) {
          transcript = liveFallbackText.trim();
        }

        if (transcript) {
          await evaluateTranscript(transcript, 'microphone', confidence);
        } else {
          setStatusText('No speech could be transcribed from the recording.');
        }
      } catch (err: any) {
        console.warn('Sarvam STT error, trying live preview fallback:', err);
        if (liveFallbackText && liveFallbackText.trim()) {
          await evaluateTranscript(liveFallbackText.trim(), 'microphone', 0.92);
        } else {
          setErrorMsg(err.message || 'Sarvam STT failed to transcribe speech.');
          setStatusText('Transcription error');
        }
      } finally {
        setIsTranscribing(false);
      }
    },
    [evaluateTranscript, languageCode]
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
          setStatusText('⚠️ System audio sharing cancelled. Proceeding with Microphone only.');
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
            ? '🟢 Dual Shield Active: Capturing Microphone + Telegram/System Audio...'
            : '🟢 Continuous Call Shield Active: Streaming 16kHz audio & transcribing every ~7-8 words...'
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
              `Live Caption (~${data.wordCount || 8} words): "${textChunk.slice(0, 30)}..." → ${data.riskLevel} (${Math.round(
                data.riskScore
              )}/100)`
            );
          } else if (data.type === 'telegram_alert_sent') {
            setStatusText(`🚨 Telegram Alert dispatched to @EdgingToRunner_bot (ID #${data.messageId})!`);
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

      // Audio Graph with Mixer Bus
      const mixer = actx.createGain();
      mixer.gain.value = 1.0;

      // Connect Mic
      const micSource = actx.createMediaStreamSource(micStream);
      micSource.connect(mixer);

      // Connect System Audio if present
      if (systemStream && systemStream.getAudioTracks().length > 0) {
        const sysSource = actx.createMediaStreamSource(systemStream);
        sysSource.connect(mixer);
      }

      const analyser = actx.createAnalyser();
      analyser.fftSize = 64;
      mixer.connect(analyser);
      analyserRef.current = analyser;

      // Extract 16kHz PCM16LE mono chunks and stream over WebSocket
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

      // Connect processor to destination with zero gain to prevent mic feedback echo
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
      setStatusText('🟢 Continuous Call Shield Active: Listening live & transcribing every ~7-8 words...');

      // Recording timer
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Microphone access denied or unavailable.');
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
    setStatusText('Call monitoring ended. Audio buffers flushed and session saved.');
  };

  // Test Simulation of Telegram VoIP Call Bridge
  const handleTestTelegramBridge = async () => {
    setIsSimulatingTelegram(true);
    setStatusText('Testing Telegram VoIP Call Bridge Spike...');
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
        setStatusText('Telegram VoIP Call Bridge Spike: Successfully intercepted & flagged!');
      }
    } catch (err: any) {
      setErrorMsg('Failed to test Telegram bridge spike: ' + err.message);
    } finally {
      setIsSimulatingTelegram(false);
    }
  };

  // Highlight flagged keywords in text
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
          className="px-1.5 py-0.5 rounded bg-red-500/30 text-red-200 border border-red-500/40 font-bold mx-0.5"
        >
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  return (
    <div className="glass-card p-6 md:p-8 space-y-6 border border-[#292F3C]">
      {/* Top Banner, Audio Mode & Language Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[#292F3C]">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#63D6A5] animate-ping" />
            <h2 className="text-lg font-bold text-[#F1F3F8]">Live Call & Voice Shield</h2>
          </div>
          <p className="text-xs text-[#A2A9BA] mt-0.5">
            Real-Time Speech Ingestion, Telegram Monitoring & Immediate Scam Keyword Flagging
          </p>
        </div>

        {/* Audio Mode & Language selectors */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Audio Source Mode */}
          <div className="flex items-center gap-1.5">
            <Headphones className="w-4 h-4 text-[#8B7CFF]" />
            <select
              value={captureMode}
              onChange={(e) => setCaptureMode(e.target.value as 'mic' | 'dual')}
              disabled={isRecording}
              className="glass px-3 py-1.5 rounded-xl text-xs font-mono bg-[#11141C] text-[#F1F3F8] border-[#292F3C] focus:outline-none focus:border-[#8B7CFF]"
              title="Select audio source: Mic only (speakers) or Dual (captures Telegram call audio directly)"
            >
              <option value="mic">🎙️ Mic Only (Speakers / Laptop)</option>
              <option value="dual">🎧 Dual: Mic + Telegram Call Audio (Headphones)</option>
            </select>
          </div>

          {/* Language selector */}
          <div className="flex items-center gap-1.5">
            <Globe className="w-4 h-4 text-[#72D7E8]" />
            <select
              value={languageCode}
              onChange={(e) => setLanguageCode(e.target.value)}
              disabled={isRecording}
              className="glass px-3 py-1.5 rounded-xl text-xs font-mono bg-[#11141C] text-[#F1F3F8] border-[#292F3C] focus:outline-none focus:border-[#8B7CFF]"
            >
              <option value="auto">🌐 Auto Detect (Hi/En/Pa)</option>
              <option value="hi-IN">🇮🇳 Hindi (हिन्दी)</option>
              <option value="en-IN">🇬🇧 Indian English</option>
              <option value="pa-IN">🇵🇦 Punjabi (ਪੰਜਾਬੀ)</option>
            </select>
          </div>
        </div>
      </div>

      {captureMode === 'dual' && !isRecording && (
        <div className="px-4 py-2.5 rounded-xl border border-[#292F3C] bg-[#11141C] text-xs text-[#A2A9BA] flex items-center gap-2">
          <Headphones className="w-4 h-4 text-[#8B7CFF] shrink-0" />
          <span>
            <strong className="text-[#F1F3F8]">Dual Mode Active:</strong> When you click Talk, your browser will prompt to share audio. Select your <strong>Telegram Window / Screen</strong> and ensure <strong>"Also share system audio"</strong> is checked so your caller's voice is captured through headphones.
          </span>
        </div>
      )}

      {/* Main Mic Control + Visualizer */}
      <div className="flex flex-col items-center justify-center py-4 text-center space-y-4">
        <div className="relative">
          {/* Animated Waveform rings */}
          {isRecording && (
            <>
              <div
                className="absolute inset-0 rounded-full border-2 border-[#63D6A5]/40 animate-ping"
                style={{ transform: `scale(${1 + audioLevel * 1.5})` }}
              />
              <div
                className="absolute -inset-4 rounded-full border border-[#8B7CFF]/25 animate-pulse"
                style={{ transform: `scale(${1 + audioLevel * 1.8})` }}
              />
            </>
          )}

          {/* Central Mic Button */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isTranscribing}
            className={`
              relative z-10 w-28 h-28 rounded-full flex flex-col items-center justify-center shadow-2xl
              transition-all duration-300 transform hover:scale-105 active:scale-95 cursor-pointer
              ${
                isRecording
                  ? 'bg-gradient-to-tr from-rose-600 via-red-600 to-rose-500 text-white shadow-[0_0_50px_rgba(240,128,145,0.5)] animate-pulse'
                  : 'bg-gradient-to-tr from-[#8B7CFF] via-[#7280FF] to-[#72D7E8] text-white shadow-[0_0_35px_rgba(139,124,255,0.35)]'
              }
            `}
            title={isRecording ? 'Click to Stop and Analyze' : 'Click to Speak'}
          >
            {isRecording ? <MicOff className="w-10 h-10" /> : <Mic className="w-10 h-10" />}
            <span className="text-[10px] font-mono mt-1 font-bold uppercase">
              {isRecording ? `${recordingSeconds}s Stop` : 'Click to Talk'}
            </span>
          </button>
        </div>

        <div>
          <h3 className="text-xl font-bold text-[#F1F3F8]">
            {isRecording
              ? 'Listening to Speech... Click when done'
              : isTranscribing
              ? 'Transcribing & Evaluating Risk...'
              : 'Tap Mic to Speak & Check Keywords'}
          </h3>
          <p className="text-xs text-[#A2A9BA] mt-1 max-w-md mx-auto">{statusText}</p>
        </div>

        {/* Live Audio Level Waveform Bar */}
        <div className="w-full max-w-xs flex items-center gap-1.5 h-6 px-4 bg-[#11141C] border border-[#292F3C] rounded-full justify-center">
          {[...Array(24)].map((_, i) => {
            const h = Math.max(3, Math.sin(i * 0.4 + audioLevel * 10) * audioLevel * 20);
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
                      ? '#63D6A5'
                      : 'rgba(241, 243, 248, 0.2)',
                }}
              />
            );
          })}
        </div>

        {/* Live speech interim preview while speaking */}
        {isRecording && liveTranscriptPreview && (
          <div className="w-full max-w-lg p-3 rounded-xl bg-[#11141C] border border-[#8B7CFF]/30 text-xs text-[#F1F3F8] animate-slide-up">
            <span className="text-[10px] font-mono text-[#8B7CFF] block mb-1">
              🎙️ Live Speech Interim Preview:
            </span>
            <p className="italic">{liveTranscriptPreview}</p>
          </div>
        )}
      </div>

      {/* Error alert if any */}
      {errorMsg && (
        <div className="p-4 rounded-xl border border-[#F08091]/30 bg-[#11141C] text-[#F08091] text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 shrink-0 text-[#F08091]" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-[11px] underline text-[#F08091] hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Quick Speech Simulator Presets */}
      <div className="p-4 rounded-2xl bg-[#11141C] border border-[#292F3C] space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-[#A2A9BA] flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-[#F2C879]" />
            <span>One-Click Voice Test Phrases (Immediate Keyword Flagging)</span>
          </span>
          <span className="text-[10px] text-[#70798C] font-mono">Instant Test</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          <button
            onClick={() =>
              evaluateTranscript('Sir, please share your 6 digit OTP right now to verify account.', 'preset')
            }
            className="p-2.5 rounded-xl bg-[#171B26] hover:bg-[#202636] text-left border border-[#292F3C] hover:border-[#F08091]/50 text-[#F1F3F8] transition-all flex items-center justify-between"
          >
            <span className="line-clamp-1">🚨 "Sir, please share your 6-digit OTP right now"</span>
            <Play className="w-3 h-3 shrink-0 text-[#F08091] fill-current ml-2" />
          </button>

          <button
            onClick={() =>
              evaluateTranscript('Your bank account is blocked, give me your UPI PIN immediately.', 'preset')
            }
            className="p-2.5 rounded-xl bg-[#171B26] hover:bg-[#202636] text-left border border-[#292F3C] hover:border-[#F08091]/50 text-[#F1F3F8] transition-all flex items-center justify-between"
          >
            <span className="line-clamp-1">🚨 "Account is blocked, give me your UPI PIN"</span>
            <Play className="w-3 h-3 shrink-0 text-[#F08091] fill-current ml-2" />
          </button>

          <button
            onClick={() =>
              evaluateTranscript('You are under digital arrest by CBI Mumbai. Non-bailable warrant issued.', 'preset')
            }
            className="p-2.5 rounded-xl bg-[#171B26] hover:bg-[#202636] text-left border border-[#292F3C] hover:border-[#F08091]/50 text-[#F1F3F8] transition-all flex items-center justify-between"
          >
            <span className="line-clamp-1">🚨 "Digital arrest by CBI, arrest warrant issued"</span>
            <Play className="w-3 h-3 shrink-0 text-[#F08091] fill-current ml-2" />
          </button>

          <button
            onClick={() =>
              evaluateTranscript('Hello, I want to check my account balance and get a mini statement.', 'preset')
            }
            className="p-2.5 rounded-xl bg-[#171B26] hover:bg-[#202636] text-left border border-[#292F3C] hover:border-[#63D6A5]/50 text-[#F1F3F8] transition-all flex items-center justify-between"
          >
            <span className="line-clamp-1">✅ "Hello, I want to check my account balance" (Safe)</span>
            <Play className="w-3 h-3 shrink-0 text-[#63D6A5] fill-current ml-2" />
          </button>
        </div>
      </div>

      {/* Telegram VoIP Voice Call Bridge Card */}
      <div className="p-4 rounded-2xl border border-[#292F3C] bg-[#11141C] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <PhoneCall className="w-4 h-4 text-[#8B7CFF]" />
            <span className="text-xs font-semibold text-[#F1F3F8]">Telegram VoIP Call Bridge</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#63D6A5]/15 text-[#63D6A5] border border-[#63D6A5]/30">
              WS: /internal/live/ingest
            </span>
          </div>
          <p className="text-[11px] text-[#A2A9BA]">
            Connects live Telegram VoIP phone calls from <code>py-tgcalls</code> directly into the scam detection engine.
          </p>
        </div>

        <button
          onClick={handleTestTelegramBridge}
          disabled={isSimulatingTelegram}
          className="btn-secondary px-3.5 py-1.5 text-xs font-medium text-[#8B7CFF] border-[#292F3C] flex items-center gap-1.5 shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#F2C879]" />
          <span>{isSimulatingTelegram ? 'Testing...' : 'Test Telegram Bridge Call'}</span>
        </button>
      </div>

      {/* Temporarily Stored Speech & Keyword Detection History */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-[#A2A9BA] flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-[#63D6A5]" />
            <span>Temporarily Stored Speech & Flagged Keywords ({storedUtterances.length})</span>
          </span>

          {storedUtterances.length > 0 && (
            <button
              onClick={() => setStoredUtterances([])}
              className="text-[11px] text-[#70798C] hover:text-[#F1F3F8] flex items-center gap-1 hover:underline"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear Temporary Storage</span>
            </button>
          )}
        </div>

        {storedUtterances.length === 0 ? (
          <div className="p-8 rounded-2xl bg-[#11141C] border border-[#292F3C] text-center text-xs text-[#70798C] italic">
            No speech has been recorded yet. Click the mic button above, say a phrase (e.g. "tell me your OTP"), and your spoken words will appear here with highlighted keywords!
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
            {storedUtterances.map((utt) => {
              const isDanger = utt.riskLevel === 'HIGH' || utt.riskLevel === 'CRITICAL';
              const isCaution = utt.riskLevel === 'MEDIUM';

              return (
                <div
                  key={utt.id}
                  className={`p-3.5 rounded-2xl border transition-all animate-slide-up ${
                    isDanger
                      ? 'border-[#F08091]/40 bg-[#11141C]'
                      : isCaution
                      ? 'border-[#F2C879]/40 bg-[#11141C]'
                      : 'border-[#292F3C] bg-[#11141C]'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] text-[#70798C] mb-2 font-mono">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#63D6A5]" />
                      <span>{new Date(utt.timestamp).toLocaleTimeString()}</span>
                      <span className="text-[#292F3C]">·</span>
                      <span className={`uppercase text-[10px] font-semibold ${utt.speaker === 'agent' ? 'text-[#63D6A5]' : 'text-[#8B7CFF]'}`}>
                        {utt.speaker ? `${utt.speaker.toUpperCase()} · ` : ''}{utt.source.replace('_', ' ')}
                      </span>
                    </span>

                    <span
                      className={`px-2 py-0.5 rounded-full font-bold text-[10px] border ${
                        utt.riskLevel === 'CRITICAL'
                          ? 'bg-[#F08091]/20 text-[#F08091] border-[#F08091]/40'
                          : isDanger
                          ? 'bg-[#F08091]/15 text-[#F08091] border-[#F08091]/30'
                          : isCaution
                          ? 'bg-[#F2C879]/15 text-[#F2C879] border-[#F2C879]/30'
                          : 'bg-[#63D6A5]/15 text-[#63D6A5] border-[#63D6A5]/30'
                      }`}
                    >
                      {utt.riskLevel} ({Math.round(utt.riskScore)}/100)
                    </span>
                  </div>

                  {/* Spoken Text with Keyword Highlighting */}
                  <p className="text-xs font-medium text-[#F1F3F8] leading-relaxed mb-2">
                    {renderHighlightedText(utt.text, utt.flaggedKeywords)}
                  </p>

                  {/* Flagged Keywords Pills */}
                  {utt.flaggedKeywords && utt.flaggedKeywords.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap mt-2 pt-2 border-t border-[#292F3C]">
                      <span className="text-[10px] font-mono text-[#F08091] font-semibold flex items-center gap-1">
                        <Flame className="w-3 h-3 text-[#F08091]" />
                        Flagged Threats:
                      </span>
                      {utt.flaggedKeywords.map((kw, i) => (
                        <span
                          key={i}
                          className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#F08091]/15 text-[#F08091] border border-[#F08091]/30"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Recommended Action */}
                  {utt.safeAction && isDanger && (
                    <div className="mt-2 text-xs text-[#F2C879] bg-[#171B26] p-2 rounded-xl border border-[#292F3C] flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-[#F2C879] shrink-0" />
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
