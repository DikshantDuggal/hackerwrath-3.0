import { useState, useCallback } from 'react';
import {
  Shield,
  Mic,
  Phone,
  Sparkles,
  Database,
  HelpCircle,
  Key,
  Volume2,
  VolumeX,
  Radio,
  CheckCircle,
  AlertTriangle,
  Flame,
} from 'lucide-react';
import AstraOrbitalCanvas from './components/AstraOrbitalCanvas';
import RiskDisplay from './components/RiskDisplay';
import TranscriptPanel from './components/TranscriptPanel';
import TextInputPanel from './components/TextInputPanel';
import TutorialModal from './components/TutorialModal';
import KeysModal from './components/KeysModal';
import PhoneCallMockup from './components/PhoneCallMockup';
import LiveVoiceTester from './components/LiveVoiceTester';
import ThreatIntelPanel from './components/ThreatIntelPanel';
import StatusBar from './components/StatusBar';
import { audioAlerts } from './utils/audioAlerts';
import type { RiskAssessment, TranscriptSegment } from './hooks/useLiveDetection';

type ActiveTab = 'mic' | 'phone' | 'text' | 'intel';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('mic');
  const [activeRisk, setActiveRisk] = useState<RiskAssessment | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [isAudioMuted, setIsAudioMuted] = useState<boolean>(false);
  const [showTutorial, setShowTutorial] = useState(() => {
    return !localStorage.getItem('suraksha_tutorial_seen');
  });
  const [showKeysModal, setShowKeysModal] = useState(false);
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptSegment[]>([]);
  const [isProcessingText, setIsProcessingText] = useState(false);

  const handleToggleSound = () => {
    const muted = audioAlerts.toggleMute();
    setIsAudioMuted(muted);
  };

  const handleCloseTutorial = useCallback(() => {
    setShowTutorial(false);
    localStorage.setItem('suraksha_tutorial_seen', 'true');
  }, []);

  // Text analysis handler
  const handleAnalyzeText = async (text: string): Promise<void> => {
    if (!text.trim()) return;
    setIsProcessingText(true);

    try {
      const newSeg: TranscriptSegment = {
        text,
        timestamp: Date.now(),
        confidence: 0.98,
        speaker: 'text_input',
      };
      setTranscriptHistory((prev) => [...prev, newSeg]);

      const res = await fetch('/analyze/transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: text,
          language_code: 'auto',
          transcript_confidence: 0.98,
        }),
      });

      if (res.ok) {
        const assessment: RiskAssessment = await res.json();
        setActiveRisk(assessment);

        if (assessment.risk_level === 'HIGH') {
          audioAlerts.playHighRiskAlert();
        } else if (assessment.risk_level === 'MEDIUM') {
          audioAlerts.playCautionAlert();
        } else {
          audioAlerts.playSafeChime();
        }
      }
    } catch (e) {
      console.error('Analyze text error:', e);
    } finally {
      setIsProcessingText(false);
    }
  };

  // Segment analysis for Phone Simulator
  const handleAnalyzeSegment = async (text: string): Promise<RiskAssessment | null> => {
    try {
      const res = await fetch('/analyze/transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: text,
          language_code: 'auto',
          transcript_confidence: 0.95,
        }),
      });

      if (res.ok) {
        const assessment: RiskAssessment = await res.json();
        setActiveRisk(assessment);
        setTranscriptHistory((prev) => [
          ...prev,
          {
            text,
            timestamp: Date.now(),
            confidence: 0.95,
            speaker: 'caller',
          },
        ]);
        return assessment;
      }
    } catch (e) {
      console.error('Segment analysis error', e);
    }
    return null;
  };

  const riskLevel = activeRisk?.risk_level || 'LOW';

  return (
    <div className="min-h-screen relative flex flex-col font-sans selection:bg-purple-500/30 selection:text-white">
      {/* 3D Astra Orbital Canvas with Candlelight Obsidian + Green Shade */}
      <AstraOrbitalCanvas
        riskLevel={riskLevel}
        isListening={activeTab === 'mic'}
        audioLevel={audioLevel}
      />

      {/* Atmospheric gradient mesh */}
      <div className="bg-mesh" />

      {/* Content Layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Navigation Bar */}
        <header className="glass border-b border-[var(--glass-border)] px-4 sm:px-6 py-3.5 sticky top-0 z-30 shadow-md">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="relative group cursor-pointer" onClick={() => setShowTutorial(true)}>
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[var(--purple-dim)] via-[var(--purple-glow)] to-[var(--green-accent)] p-[1.5px] shadow-[0_0_20px_rgba(168,85,247,0.4)]">
                  <div className="w-full h-full rounded-[14px] bg-[#0c051a] flex items-center justify-center">
                    <Shield className="w-5 h-5 text-[var(--purple-bright)]" />
                  </div>
                </div>
                <div className="absolute -inset-1 rounded-2xl bg-[var(--green-accent)] opacity-20 blur-sm group-hover:opacity-40 transition-opacity" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-black tracking-wider gradient-text font-mono">
                    SURAKSHA
                  </h1>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--green-accent)]/15 text-[var(--green-bright)] border border-[var(--green-accent)]/30 font-semibold">
                    MVP 1.0
                  </span>
                </div>
                <p className="text-[10px] text-[var(--text-muted)] tracking-widest uppercase">
                  AI Scam-Call Detection & Negation Guard
                </p>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1.5 p-1 rounded-2xl glass border-white/10 overflow-x-auto max-w-full">
              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('mic');
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap
                  ${
                    activeTab === 'mic'
                      ? 'bg-gradient-to-r from-[var(--purple-dim)] to-[var(--purple-glow)] text-white shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                      : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Mic className="w-3.5 h-3.5" />
                <span>Live Mic Shield</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('phone');
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap
                  ${
                    activeTab === 'phone'
                      ? 'bg-gradient-to-r from-[var(--purple-dim)] to-[var(--purple-glow)] text-white shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                      : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Call Simulator</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('text');
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap
                  ${
                    activeTab === 'text'
                      ? 'bg-gradient-to-r from-[var(--purple-dim)] to-[var(--purple-glow)] text-white shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                      : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Text Analyzer</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('intel');
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap
                  ${
                    activeTab === 'intel'
                      ? 'bg-gradient-to-r from-[var(--purple-dim)] to-[var(--purple-glow)] text-white shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                      : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Database className="w-3.5 h-3.5" />
                <span>Threat Intel</span>
              </button>
            </nav>

            {/* Quick Header Action Icons */}
            <div className="flex items-center gap-2">
              {/* Sound toggle */}
              <button
                onClick={handleToggleSound}
                className="p-2 rounded-xl glass hover:bg-white/10 transition-colors text-[var(--text-muted)] hover:text-white"
                title={isAudioMuted ? 'Unmute Audio Alarms' : 'Mute Audio Alarms'}
              >
                {isAudioMuted ? (
                  <VolumeX className="w-4 h-4 text-red-400" />
                ) : (
                  <Volume2 className="w-4 h-4 text-emerald-400" />
                )}
              </button>

              {/* API Keys status trigger */}
              <button
                onClick={() => setShowKeysModal(true)}
                className="px-3 py-1.5 rounded-xl glass hover:bg-white/10 transition-colors text-xs font-mono flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-white border border-[var(--purple-border)]"
                title="API Keys Status"
              >
                <Key className="w-3.5 h-3.5 text-emerald-400" />
                <span className="hidden sm:inline">Sarvam: Live</span>
              </button>

              {/* Tutorial trigger */}
              <button
                onClick={() => setShowTutorial(true)}
                className="p-2 rounded-xl glass hover:bg-white/10 transition-colors text-[var(--text-muted)] hover:text-white"
                title="How Suraksha Works"
              >
                <HelpCircle className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Global Threat Alert Bar if HIGH RISK detected */}
        {riskLevel === 'HIGH' && (
          <div className="bg-red-950/80 border-b border-red-500/50 py-2.5 px-4 backdrop-blur-md animate-pulse">
            <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2 text-red-200 font-semibold">
                <Flame className="w-4 h-4 text-red-400 animate-bounce flex-shrink-0" />
                <span>
                  CRITICAL FRAUD ALERT: High probability scam detected in caller speech! Never enter
                  your UPI PIN or share OTP.
                </span>
              </div>
              <button
                onClick={() => setActiveTab('phone')}
                className="px-3 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-[11px] uppercase transition-colors flex-shrink-0"
              >
                View Call HUD
              </button>
            </div>
          </div>
        )}

        {/* Main Body View */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8">
          {/* Active Tab View */}
          {activeTab === 'mic' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <div className="lg:col-span-7">
                <LiveVoiceTester
                  onAssessmentUpdate={setActiveRisk}
                  onAudioLevelChange={setAudioLevel}
                  activeRisk={activeRisk}
                />
              </div>
              <div className="lg:col-span-5 space-y-6">
                <RiskDisplay assessment={activeRisk} isListening={true} />
              </div>
            </div>
          )}

          {activeTab === 'phone' && (
            <div className="space-y-6">
              <PhoneCallMockup
                onAnalyzeSegment={handleAnalyzeSegment}
                activeRisk={activeRisk}
              />
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-7">
                  <RiskDisplay assessment={activeRisk} isListening={false} />
                </div>
                <div className="lg:col-span-5">
                  <TranscriptPanel segments={transcriptHistory} isListening={false} />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'text' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <div className="lg:col-span-7 space-y-6">
                <TextInputPanel
                  onAnalyze={handleAnalyzeText}
                  isProcessing={isProcessingText}
                />
                <RiskDisplay assessment={activeRisk} isListening={false} />
              </div>
              <div className="lg:col-span-5">
                <TranscriptPanel segments={transcriptHistory} isListening={false} />
              </div>
            </div>
          )}

          {activeTab === 'intel' && (
            <div className="space-y-6">
              <ThreatIntelPanel />
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-7">
                  <RiskDisplay assessment={activeRisk} isListening={false} />
                </div>
                <div className="lg:col-span-5">
                  <TranscriptPanel segments={transcriptHistory} isListening={false} />
                </div>
              </div>
            </div>
          )}
        </main>

        {/* Footer with Live System Status */}
        <footer className="mt-auto border-t border-[var(--glass-border)]">
          <StatusBar />
        </footer>
      </div>

      {/* Modals */}
      <TutorialModal isOpen={showTutorial} onClose={handleCloseTutorial} />
      <KeysModal isOpen={showKeysModal} onClose={() => setShowKeysModal(false)} />
    </div>
  );
}
