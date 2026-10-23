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
import type { RiskAssessment, TranscriptSegment, RAGClassificationResponse } from './hooks/useLiveDetection';

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

  // Text analysis handler with concurrent RAG vector search
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

      // Execute both transcript heuristics and RAG vector store search concurrently
      const [res, ragRes] = await Promise.allSettled([
        fetch('/analyze/transcript', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcript: text,
            language_code: 'auto',
            transcript_confidence: 0.98,
          }),
        }),
        fetch('/rag/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text,
            top_k: 3,
            include_retrieved_examples: true,
          }),
        }),
      ]);

      if (res.status === 'fulfilled' && res.value.ok) {
        const assessment: RiskAssessment = await res.value.json();

        // Attach RAG vector classification and nearest neighbors if available
        if (ragRes.status === 'fulfilled' && ragRes.value.ok) {
          try {
            const ragData: RAGClassificationResponse = await ragRes.value.json();
            assessment.rag_classification = ragData;
          } catch (err) {
            console.warn('RAG parse warning in text analyzer:', err);
          }
        }

        setActiveRisk(assessment);

        if (assessment.risk_level === 'HIGH' || assessment.risk_level === 'CRITICAL') {
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

  // Segment analysis for Phone Simulator with concurrent RAG vector search
  const handleAnalyzeSegment = async (text: string): Promise<RiskAssessment | null> => {
    try {
      const [res, ragRes] = await Promise.allSettled([
        fetch('/analyze/transcript', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcript: text,
            language_code: 'auto',
            transcript_confidence: 0.95,
          }),
        }),
        fetch('/rag/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text,
            top_k: 3,
            include_retrieved_examples: true,
          }),
        }),
      ]);

      if (res.status === 'fulfilled' && res.value.ok) {
        const assessment: RiskAssessment = await res.value.json();

        if (ragRes.status === 'fulfilled' && ragRes.value.ok) {
          try {
            const ragData: RAGClassificationResponse = await ragRes.value.json();
            assessment.rag_classification = ragData;
          } catch (err) {
            console.warn('RAG parse warning in segment analyzer:', err);
          }
        }

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
    <div className="min-h-screen relative flex flex-col font-sans selection:bg-[#8B7CFF]/30 selection:text-white bg-[#0B0D12] text-[#E8ECF2]">
      {/* 3D Astra Orbital Canvas with Obsidian Cosmic palette & solar system */}
      <AstraOrbitalCanvas
        riskLevel={riskLevel}
        isListening={activeTab === 'mic'}
        audioLevel={audioLevel}
      />

      {/* Atmospheric gradient mesh */}
      <div className="bg-mesh pointer-events-none" />

      {/* Content Layer */}
      <div className="relative z-20 flex flex-col min-h-screen">
        {/* Navigation Bar */}
        <header className="bg-[#11141C]/90 backdrop-blur-xl border-b border-[#292F3C] px-4 sm:px-6 py-3.5 sticky top-0 z-30 shadow-2xl">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="relative group cursor-pointer" onClick={() => setShowTutorial(true)}>
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#8B7CFF] via-[#72D7E8] to-[#63D6A5] p-[1.5px] shadow-[0_0_20px_rgba(139,124,255,0.4)] transition-transform duration-300 group-hover:scale-105">
                  <div className="w-full h-full rounded-[14px] bg-[#0B0D12] flex items-center justify-center">
                    <Shield className="w-5 h-5 text-[#8B7CFF]" />
                  </div>
                </div>
                <div className="absolute -inset-1 rounded-2xl bg-[#72D7E8] opacity-20 blur-sm group-hover:opacity-40 transition-opacity" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-black tracking-wider gradient-text font-mono">
                    SURAKSHA
                  </h1>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#63D6A5]/15 text-[#63D6A5] border border-[#63D6A5]/30 font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#63D6A5] animate-ping" />
                    RAG v3.0 ACTIVE
                  </span>
                </div>
                <p className="text-[10px] text-[#7E889B] tracking-widest uppercase font-mono">
                  Neural Anti-Scam Intelligence & Negation Shield
                </p>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1.5 p-1 rounded-2xl bg-[#0B0D12]/80 border border-[#292F3C] overflow-x-auto max-w-full">
              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('mic');
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap
                  ${
                    activeTab === 'mic'
                      ? 'bg-gradient-to-r from-[#8B7CFF] to-[#6c5ce7] text-white shadow-[0_0_15px_rgba(139,124,255,0.35)] font-semibold'
                      : 'text-[#7E889B] hover:text-[#E8ECF2] hover:bg-white/5'
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
                      ? 'bg-gradient-to-r from-[#8B7CFF] to-[#6c5ce7] text-white shadow-[0_0_15px_rgba(139,124,255,0.35)] font-semibold'
                      : 'text-[#7E889B] hover:text-[#E8ECF2] hover:bg-white/5'
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
                      ? 'bg-gradient-to-r from-[#8B7CFF] to-[#6c5ce7] text-white shadow-[0_0_15px_rgba(139,124,255,0.35)] font-semibold'
                      : 'text-[#7E889B] hover:text-[#E8ECF2] hover:bg-white/5'
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
                      ? 'bg-gradient-to-r from-[#8B7CFF] to-[#6c5ce7] text-white shadow-[0_0_15px_rgba(139,124,255,0.35)] font-semibold'
                      : 'text-[#7E889B] hover:text-[#E8ECF2] hover:bg-white/5'
                  }
                `}
              >
                <Database className="w-3.5 h-3.5" />
                <span>Threat Intel & RAG</span>
              </button>
            </nav>

            {/* Quick Header Action Icons */}
            <div className="flex items-center gap-2">
              {/* Standalone Spellbreaker Preview Link */}
              <a
                href="/preview.html"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-xl bg-[#171B26] hover:bg-[#202534] transition-colors text-xs font-mono flex items-center gap-1.5 text-[#72D7E8] hover:text-white border border-[#72D7E8]/30 shadow-sm"
                title="Launch Standalone Spellbreaker Interactive Preview"
              >
                <Phone className="w-3.5 h-3.5 text-[#72D7E8]" />
                <span className="hidden sm:inline">Spellbreaker UI</span>
              </a>

              {/* Sound toggle */}
              <button
                onClick={handleToggleSound}
                className="p-2 rounded-xl bg-[#171B26] hover:bg-[#202534] transition-colors text-[#7E889B] hover:text-[#E8ECF2] border border-[#292F3C]"
                title={isAudioMuted ? 'Unmute Audio Alarms' : 'Mute Audio Alarms'}
              >
                {isAudioMuted ? (
                  <VolumeX className="w-4 h-4 text-[#F08091]" />
                ) : (
                  <Volume2 className="w-4 h-4 text-[#63D6A5]" />
                )}
              </button>

              {/* API Keys status trigger */}
              <button
                onClick={() => setShowKeysModal(true)}
                className="px-3 py-1.5 rounded-xl bg-[#171B26] hover:bg-[#202534] transition-colors text-xs font-mono flex items-center gap-1.5 text-[#A5AFBF] hover:text-white border border-[#292F3C]"
                title="API Keys Status"
              >
                <Key className="w-3.5 h-3.5 text-[#63D6A5]" />
                <span className="hidden sm:inline">Sarvam: Live</span>
              </button>

              {/* Tutorial trigger */}
              <button
                onClick={() => setShowTutorial(true)}
                className="p-2 rounded-xl bg-[#171B26] hover:bg-[#202534] transition-colors text-[#7E889B] hover:text-[#E8ECF2] border border-[#292F3C]"
                title="How Suraksha Works"
              >
                <HelpCircle className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Global Threat Alert Bar if HIGH or CRITICAL RISK detected */}
        {(riskLevel === 'HIGH' || riskLevel === 'CRITICAL') && (
          <div className={`${riskLevel === 'CRITICAL' ? 'bg-[#2A1218]/90 border-[#F08091]/70 shadow-[0_0_30px_rgba(240,128,145,0.3)]' : 'bg-[#25151A]/80 border-[#F08091]/40'} border-b py-2.5 px-4 backdrop-blur-md animate-pulse`}>
            <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2 text-[#FFE3E8] font-semibold">
                <Flame className="w-4 h-4 text-[#F08091] animate-bounce flex-shrink-0" />
                <span>
                  {riskLevel === 'CRITICAL'
                    ? 'EMERGENCY SCAM INTERCEPT: Active extortion or OTP theft pattern identified! Do not comply or disclose details.'
                    : 'HIGH FRAUD ALERT: High probability scam detected in caller speech! Never enter your UPI PIN or share OTP.'}
                </span>
              </div>
              <button
                onClick={() => setActiveTab('phone')}
                className="px-3 py-1 rounded-lg bg-[#F08091] hover:bg-[#fa5252] text-black font-bold text-[11px] uppercase transition-colors flex-shrink-0 shadow-md"
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
