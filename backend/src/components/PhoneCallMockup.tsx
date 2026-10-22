import { useState, useEffect, useRef } from 'react';
import {
  Phone,
  PhoneOff,
  Shield,
  AlertTriangle,
  CheckCircle,
  Volume2,
  Mic,
  MicOff,
  Flame,
  Radio,
  Play,
  RotateCcw,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { DEMO_SCENARIOS, DemoScenario } from '../data/demoScenarios';
import { audioAlerts } from '../utils/audioAlerts';
import type { RiskAssessment } from '../hooks/useLiveDetection';

interface PhoneCallMockupProps {
  onAnalyzeSegment: (text: string) => Promise<RiskAssessment | null>;
  activeRisk: RiskAssessment | null;
}

export default function PhoneCallMockup({ onAnalyzeSegment, activeRisk }: PhoneCallMockupProps) {
  const [selectedScenario, setSelectedScenario] = useState<DemoScenario>(DEMO_SCENARIOS[0]);
  const [callState, setCallState] = useState<'IDLE' | 'RINGING' | 'IN_CALL' | 'ENDED'>('IDLE');
  const [currentSegmentIdx, setCurrentSegmentIdx] = useState(0);
  const [callDuration, setCallDuration] = useState(0);
  const [displayedTranscript, setDisplayedTranscript] = useState<Array<{ speaker: string; text: string }>>([]);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulatedRisk, setSimulatedRisk] = useState<RiskAssessment | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scenarioTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Call timer
  useEffect(() => {
    if (callState === 'IN_CALL') {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [callState]);

  // Clean timeouts on unmount
  useEffect(() => {
    return () => {
      if (scenarioTimeoutRef.current) clearTimeout(scenarioTimeoutRef.current);
    };
  }, []);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
      .toString()
      .padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const startScenario = async (scenario: DemoScenario) => {
    setSelectedScenario(scenario);
    setDisplayedTranscript([]);
    setCurrentSegmentIdx(0);
    setSimulatedRisk(null);
    setCallState('RINGING');
    audioAlerts.playCautionAlert();

    // Auto answer after 1.5s
    scenarioTimeoutRef.current = setTimeout(() => {
      setCallState('IN_CALL');
      audioAlerts.playClick();
      playScenarioSegments(scenario, 0);
    }, 1500);
  };

  const playScenarioSegments = (scenario: DemoScenario, index: number) => {
    if (index >= scenario.segments.length) {
      setIsSimulating(false);
      return;
    }

    setIsSimulating(true);
    const seg = scenario.segments[index];

    scenarioTimeoutRef.current = setTimeout(async () => {
      setDisplayedTranscript((prev) => [...prev, { speaker: seg.speaker, text: seg.text }]);
      setCurrentSegmentIdx(index + 1);

      // Send to real backend for full risk evaluation
      try {
        const assessment = await onAnalyzeSegment(seg.text);
        if (assessment) {
          setSimulatedRisk(assessment);
          if (assessment.risk_level === 'HIGH') {
            audioAlerts.playHighRiskAlert();
          } else if (assessment.risk_level === 'MEDIUM') {
            audioAlerts.playCautionAlert();
          } else {
            audioAlerts.playSafeChime();
          }
        }
      } catch (e) {
        console.error('Segment analysis error', e);
      }

      playScenarioSegments(scenario, index + 1);
    }, seg.delayMs);
  };

  const handleHangUp = () => {
    if (scenarioTimeoutRef.current) clearTimeout(scenarioTimeoutRef.current);
    setCallState('ENDED');
    setIsSimulating(false);
    audioAlerts.playClick();
    setTimeout(() => {
      setCallState('IDLE');
      setDisplayedTranscript([]);
    }, 1800);
  };

  const effectiveRisk = simulatedRisk || activeRisk;
  const isHighRisk = effectiveRisk?.risk_level === 'HIGH';
  const isMedRisk = effectiveRisk?.risk_level === 'MEDIUM';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Scenario Selector Panel (Left) */}
      <div className="lg:col-span-5 space-y-4">
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--purple-bright)]" />
              Real Indian Scam Scenarios
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded-full glass border-[var(--purple-border)] text-[var(--purple-bright)] font-mono">
              7 Test Scenarios
            </span>
          </div>

          <p className="text-xs text-[var(--text-muted)] mb-3">
            Choose a multi-turn call simulation to watch Suraksha intercept speech, suppress false positives, and trigger in-call defensive actions.
          </p>

          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {DEMO_SCENARIOS.map((scen) => {
              const isSelected = selectedScenario.id === scen.id;
              const isDanger = scen.expectedRisk === 'HIGH';
              return (
                <div
                  key={scen.id}
                  onClick={() => {
                    if (callState === 'IN_CALL' || callState === 'RINGING') handleHangUp();
                    startScenario(scen);
                  }}
                  className={`
                    p-3.5 rounded-xl cursor-pointer transition-all border
                    ${
                      isSelected && (callState === 'IN_CALL' || callState === 'RINGING')
                        ? 'bg-[var(--glass-bg-hover)] border-[var(--purple-bright)] shadow-[0_0_20px_rgba(168,85,247,0.2)]'
                        : 'glass border-[var(--glass-border)] hover:border-[var(--purple-dim)]/40 hover:bg-white/[0.03]'
                    }
                  `}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-sm font-medium text-[var(--text-primary)]">
                      {scen.title}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full flex-shrink-0 border ${
                        isDanger
                          ? 'bg-red-500/15 text-red-400 border-red-500/30'
                          : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      }`}
                    >
                      {scen.badge}
                    </span>
                  </div>

                  <p className="text-xs text-[var(--text-muted)] line-clamp-2 mb-2">
                    {scen.explanation}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)] font-mono">
                    <span className="text-[var(--purple-candle)]">🗣️ {scen.language}</span>
                    <button
                      className="inline-flex items-center gap-1 text-[var(--green-accent)] hover:underline"
                      onClick={(e) => {
                        e.stopPropagation();
                        startScenario(scen);
                      }}
                    >
                      <Play className="w-3 h-3 fill-current" />
                      Simulate Call
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Quick Helpline Box */}
        <div className="glass p-4 rounded-xl border-red-500/20 bg-red-950/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center text-red-400 font-bold">
              1930
            </div>
            <div>
              <p className="text-xs font-semibold text-white">National Cyber Crime Helpline</p>
              <p className="text-[11px] text-[var(--text-muted)]">Government of India citizen cyber defense</p>
            </div>
          </div>
          <a
            href="https://cybercrime.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 glass rounded-lg hover:bg-white/10 text-[var(--purple-bright)] transition-colors"
            title="Open cybercrime.gov.in"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Phone Mockup Screen (Right) */}
      <div className="lg:col-span-7 flex justify-center">
        <div
          className={`
            relative w-full max-w-[340px] sm:max-w-[370px] rounded-[44px] p-4
            border-4 transition-all duration-500 shadow-2xl
            ${
              isHighRisk
                ? 'border-red-500/60 shadow-[0_0_60px_rgba(239,68,68,0.3)] bg-gradient-to-b from-[#18040a] to-[#0c0205]'
                : isMedRisk
                ? 'border-amber-500/60 shadow-[0_0_60px_rgba(245,158,11,0.25)] bg-gradient-to-b from-[#180e04] to-[#0c0702]'
                : 'border-[var(--glass-border)] shadow-[0_0_60px_rgba(139,92,246,0.18)] bg-gradient-to-b from-[#0e051c] to-[#06020c]'
            }
          `}
        >
          {/* Dynamic Island / Speaker Notch */}
          <div className="relative z-20 flex justify-center mb-4">
            <div className="w-28 h-5 bg-black/90 rounded-full flex items-center justify-between px-3 border border-white/10 shadow-inner">
              <div className="w-2 h-2 rounded-full bg-emerald-500/70 animate-pulse" />
              <div className="w-3 h-3 rounded-full bg-[#1e1038] border border-white/20" />
            </div>
          </div>

          {/* Phone Status Bar */}
          <div className="flex justify-between items-center text-[11px] text-white/60 px-3 mb-4 font-mono">
            <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-emerald-400">Jio 5G</span>
              <Radio className="w-3.5 h-3.5 text-white/70" />
            </div>
          </div>

          {/* Caller Profile Area */}
          <div className="text-center mb-4">
            <div className="relative inline-block mb-2">
              <div
                className={`
                  w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold
                  border-2 shadow-lg mx-auto transition-transform duration-500
                  ${
                    isHighRisk
                      ? 'border-red-500 bg-red-950/60 text-red-300 animate-pulse'
                      : 'border-[var(--purple-bright)] bg-[var(--purple-dim)]/40 text-[var(--purple-bright)]'
                  }
                `}
              >
                {selectedScenario.callerName.slice(0, 1)}
              </div>

              {callState === 'IN_CALL' && (
                <div
                  className={`
                    absolute -bottom-1 -right-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase
                    border shadow
                    ${
                      isHighRisk
                        ? 'bg-red-500 text-white border-red-300'
                        : isMedRisk
                        ? 'bg-amber-500 text-black border-amber-300'
                        : 'bg-emerald-500 text-black border-emerald-300'
                    }
                  `}
                >
                  {effectiveRisk?.risk_level || 'ANALYZING'}
                </div>
              )}
            </div>

            <h4 className="text-base font-bold text-white line-clamp-1">
              {selectedScenario.callerName}
            </h4>
            <p className="text-xs text-white/60 font-mono">{selectedScenario.callerNumber}</p>

            <p className="text-xs mt-1 font-mono">
              {callState === 'RINGING' && (
                <span className="text-amber-400 animate-pulse">Incoming Call...</span>
              )}
              {callState === 'IN_CALL' && (
                <span className="text-emerald-400">Active Call · {formatTime(callDuration)}</span>
              )}
              {callState === 'ENDED' && <span className="text-red-400">Call Ended</span>}
              {callState === 'IDLE' && (
                <span className="text-[var(--text-muted)]">Select a scenario to test</span>
              )}
            </p>
          </div>

          {/* In-Call Real-Time HUD Overlay */}
          <div className="min-h-[220px] max-h-[260px] overflow-y-auto mb-4 p-3 rounded-2xl glass border-white/10 flex flex-col justify-end space-y-2">
            {callState === 'IDLE' && (
              <div className="text-center py-10 text-white/50 text-xs">
                <Shield className="w-8 h-8 mx-auto mb-2 text-[var(--purple-bright)] opacity-60" />
                <p>Suraksha AI Call Interceptor</p>
                <p className="text-[10px] mt-1 text-[var(--text-muted)]">
                  Live voice stream will be monitored for scams
                </p>
              </div>
            )}

            {/* Critical Scam Alert Banner inside Phone */}
            {isHighRisk && callState === 'IN_CALL' && (
              <div className="p-2.5 rounded-xl bg-red-600/30 border border-red-500 text-white animate-bounce">
                <div className="flex items-center gap-1.5 font-bold text-xs text-red-300 mb-0.5">
                  <Flame className="w-4 h-4 text-red-400" />
                  CRITICAL SCAM WARNING
                </div>
                <p className="text-[11px] leading-tight text-white/90">
                  {effectiveRisk?.recommended_action ||
                    'Never share your OTP or scan any QR code to receive money!'}
                </p>
              </div>
            )}

            {/* Live Captions Stream */}
            {displayedTranscript.map((seg, i) => (
              <div
                key={i}
                className={`
                  p-2 rounded-xl text-xs leading-relaxed transition-all animate-slide-up
                  ${
                    seg.speaker === 'caller'
                      ? 'bg-white/10 text-white border border-white/10'
                      : 'bg-emerald-500/20 text-emerald-200 ml-auto max-w-[80%]'
                  }
                `}
              >
                <span className="text-[9px] block text-white/40 uppercase mb-0.5">
                  {seg.speaker}
                </span>
                {seg.text}
              </div>
            ))}

            {isSimulating && (
              <div className="flex items-center gap-1.5 text-[10px] text-[var(--purple-candle)]">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--purple-candle)] animate-ping" />
                <span>Transcribing caller speech with Sarvam Saaras...</span>
              </div>
            )}
          </div>

          {/* Call Screen Action Buttons */}
          <div className="pt-2">
            {callState === 'IN_CALL' ? (
              <div className="space-y-3">
                {/* Secondary controls row */}
                <div className="grid grid-cols-3 gap-2 px-2 text-center text-[10px] text-white/70">
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    className={`p-3 rounded-full flex flex-col items-center justify-center transition-colors ${
                      isMuted ? 'bg-amber-500/30 text-amber-300' : 'bg-white/10 hover:bg-white/20'
                    }`}
                  >
                    {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    <span className="mt-1">Mute</span>
                  </button>
                  <button
                    onClick={() => setIsSpeakerOn(!isSpeakerOn)}
                    className={`p-3 rounded-full flex flex-col items-center justify-center transition-colors ${
                      isSpeakerOn ? 'bg-emerald-500/30 text-emerald-300' : 'bg-white/10 hover:bg-white/20'
                    }`}
                  >
                    <Volume2 className="w-4 h-4" />
                    <span className="mt-1">Speaker</span>
                  </button>
                  <button
                    onClick={() => {
                      audioAlerts.playHighRiskAlert();
                      alert('Triggered Voice Warning: "Warning, this call is flagged by Suraksha AI as a suspected scam."');
                    }}
                    className="p-3 rounded-full bg-white/10 hover:bg-white/20 flex flex-col items-center justify-center text-red-300 transition-colors"
                  >
                    <AlertTriangle className="w-4 h-4" />
                    <span className="mt-1">Warn Caller</span>
                  </button>
                </div>

                {/* Primary Hang Up Button */}
                <div className="flex justify-center">
                  <button
                    onClick={handleHangUp}
                    className="w-16 h-16 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-105 active:scale-95"
                    title="Hang Up"
                  >
                    <PhoneOff className="w-7 h-7" />
                  </button>
                </div>
              </div>
            ) : callState === 'RINGING' ? (
              <div className="flex justify-around items-center px-6">
                <button
                  onClick={handleHangUp}
                  className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-105"
                  title="Decline"
                >
                  <PhoneOff className="w-6 h-6" />
                </button>
                <button
                  onClick={() => {
                    setCallState('IN_CALL');
                    playScenarioSegments(selectedScenario, 0);
                  }}
                  className="w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center shadow-lg animate-pulse transition-transform hover:scale-105"
                  title="Accept Call"
                >
                  <Phone className="w-6 h-6" />
                </button>
              </div>
            ) : (
              <div className="flex justify-center">
                <button
                  onClick={() => startScenario(selectedScenario)}
                  className="btn-primary w-full py-3 text-xs flex items-center justify-center gap-2 rounded-2xl"
                >
                  <Play className="w-4 h-4 fill-current" />
                  Simulate Call Now
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
