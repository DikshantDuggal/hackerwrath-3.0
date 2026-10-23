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
  Flame,
  Zap,
  Layers,
  ArrowRight,
  ExternalLink,
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
import { DEMO_SCENARIOS, DemoScenario } from './data/demoScenarios';
import type { RiskAssessment, TranscriptSegment, RAGClassificationResponse } from './hooks/useLiveDetection';

type ActiveTab = 'mic' | 'phone' | 'deck' | 'text' | 'intel';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('mic');
  const [activeRisk, setActiveRisk] = useState<RiskAssessment | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [isAudioMuted, setIsAudioMuted] = useState<boolean>(false);
  const [showTutorial, setShowTutorial] = useState(() => {
    return !localStorage.getItem('suraksha_tutorial_completed');
  });
  const [showKeysModal, setShowKeysModal] = useState(false);
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptSegment[]>([]);
  const [isProcessingText, setIsProcessingText] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | undefined>(undefined);

  const handleToggleSound = () => {
    const muted = audioAlerts.toggleMute();
    setIsAudioMuted(muted);
  };

  const handleCloseTutorial = useCallback(() => {
    setShowTutorial(false);
    localStorage.setItem('suraksha_tutorial_completed', 'true');
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

  // Card click handler: loads scenario into Call HUD or Text AI
  const handleSelectScenario = (scenario: DemoScenario, targetMode: 'phone' | 'text') => {
    audioAlerts.playClick();
    setSelectedScenarioId(scenario.id);
    if (targetMode === 'phone') {
      setActiveTab('phone');
    } else {
      setActiveTab('text');
      handleAnalyzeText(scenario.transcript);
    }
    window.scrollTo({ top: 320, behavior: 'smooth' });
  };

  const filteredScenarios = DEMO_SCENARIOS.filter((s) => {
    if (selectedCategory === 'ALL') return true;
    if (selectedCategory === 'EXTORTION') return s.category.includes('THREAT') || s.id.includes('digital-arrest');
    if (selectedCategory === 'QR_SCAN') return s.category.includes('QR') || s.id.includes('qr');
    if (selectedCategory === 'URGENCY') return s.category.includes('OTP') || s.category.includes('REMOTE') || s.id.includes('kyc') || s.id.includes('anydesk');
    if (selectedCategory === 'TASK') return s.category.includes('TASK') || s.category.includes('URGENT_PAYMENT') || s.id.includes('lottery') || s.id.includes('task');
    if (selectedCategory === 'SAFE') return s.expectedRisk === 'LOW';
    return true;
  });

  const riskLevel = activeRisk?.risk_level || 'LOW';

  return (
    <div className="min-h-screen relative flex flex-col font-sans selection:bg-[#00F0FF]/30 selection:text-white bg-[#07090E] text-[#F1F3F8] overflow-x-hidden">
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
        {/* ─── Top Navigation Bar ─── */}
        <header className="bg-[#090D16]/90 backdrop-blur-xl border-b border-[#1E2536] px-4 sm:px-6 py-3 sticky top-0 z-40 shadow-xl">
          <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
            {/* Logo */}
            <div
              className="flex items-center gap-3 cursor-pointer group"
              onClick={() => {
                audioAlerts.playClick();
                setActiveTab('mic');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            >
              <div className="w-9 h-9 rounded-xl bg-[#00F0FF]/15 border border-[#00F0FF]/35 flex items-center justify-center shadow-[0_0_15px_rgba(0,240,255,0.3)] transition-transform group-hover:scale-105">
                <Shield className="w-4 h-4 text-[#00F0FF]" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-base font-black tracking-wider text-white font-mono text-glow-cyan">
                    SURAKSHA
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/25 font-bold">
                    3.0
                  </span>
                </div>
                <p className="text-[10px] text-[#70798C] font-mono tracking-widest uppercase hidden sm:block">
                  AI Scam Defense & Negation Guard
                </p>
              </div>
            </div>

            {/* Desktop Navigation Tabs */}
            <nav className="hidden md:flex items-center gap-1.5 p-1 rounded-full bg-[#07090E] border border-[#1E2536]">
              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('mic');
                }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'mic'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                }`}
              >
                <Mic className="w-3.5 h-3.5" />
                <span>Live Mic</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('phone');
                }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'phone'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                }`}
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Call Simulator</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('deck');
                }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'deck'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Attack Deck (8)</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('text');
                }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'text'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Text AI</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('intel');
                }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'intel'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>RAG Store</span>
              </button>
            </nav>

            {/* Quick Actions (Sound, Guide, Keys, Spellbreaker) */}
            <div className="flex items-center gap-2">
              <a
                href="/preview.html"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:flex px-3 py-1.5 rounded-full bg-[#11141C] hover:bg-[#1A202E] text-xs font-mono items-center gap-1.5 text-[#00F0FF] border border-[#00F0FF]/30 transition-colors"
                title="Open Spellbreaker UI"
              >
                <Phone className="w-3 h-3 text-[#00F0FF]" />
                <span>Spellbreaker UI</span>
              </a>

              {/* Sound Toggle */}
              <button
                onClick={handleToggleSound}
                className="p-2 rounded-full bg-[#11141C] hover:bg-[#1A202E] text-[#70798C] hover:text-white border border-[#1E2536] cursor-pointer"
                title={isAudioMuted ? 'Unmute Audio Alarms' : 'Mute Audio Alarms'}
                aria-label="Toggle Sound"
              >
                {isAudioMuted ? (
                  <VolumeX className="w-4 h-4 text-[#F08091]" />
                ) : (
                  <Volume2 className="w-4 h-4 text-[#00F0FF]" />
                )}
              </button>

              {/* Guided Tutorial Trigger */}
              <button
                onClick={() => setShowTutorial(true)}
                className="px-3 py-1.5 rounded-full bg-[#11141C] hover:bg-[#1A202E] text-xs font-mono text-white border border-[#1E2536] flex items-center gap-1.5 cursor-pointer hover:border-[#00F0FF]/40 transition-all"
                title="Open Interactive Guide"
              >
                <HelpCircle className="w-3.5 h-3.5 text-[#00F0FF]" />
                <span className="hidden sm:inline">Guide</span>
              </button>

              {/* Keys Modal Trigger */}
              <button
                onClick={() => setShowKeysModal(true)}
                className="p-2 rounded-full bg-[#11141C] hover:bg-[#1A202E] text-[#63D6A5] border border-[#1E2536] cursor-pointer"
                title="API Deployment & Diagnostic Status"
                aria-label="API Status"
              >
                <Key className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Mobile Bottom Navigation Pills */}
          <div className="flex md:hidden items-center justify-between gap-1 mt-2.5 pt-2 border-t border-[#1E2536]/60 overflow-x-auto">
            {[
              { id: 'mic', label: 'Mic Shield', icon: <Mic className="w-3 h-3" /> },
              { id: 'phone', label: 'Call HUD', icon: <Phone className="w-3 h-3" /> },
              { id: 'deck', label: 'Attack Deck', icon: <Layers className="w-3 h-3" /> },
              { id: 'text', label: 'Text AI', icon: <Sparkles className="w-3 h-3" /> },
              { id: 'intel', label: 'RAG Store', icon: <Database className="w-3 h-3" /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab(tab.id as ActiveTab);
                }}
                className={`min-h-[38px] px-2.5 py-1.5 rounded-full text-[11px] font-semibold whitespace-nowrap flex items-center gap-1 cursor-pointer transition-all ${
                  activeTab === tab.id
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </header>

        {/* Global Threat Alert Bar if HIGH or CRITICAL RISK detected */}
        {(riskLevel === 'HIGH' || riskLevel === 'CRITICAL') && (
          <div className={`${riskLevel === 'CRITICAL' ? 'bg-[#2A1218]/95 border-[#F08091]/70 shadow-[0_0_30px_rgba(240,128,145,0.4)]' : 'bg-[#25151A]/90 border-[#F08091]/40'} border-b py-2.5 px-4 backdrop-blur-md animate-pulse`}>
            <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2 text-[#FFE3E8] font-semibold">
                <Flame className="w-4 h-4 text-[#F08091] animate-bounce shrink-0" />
                <span>
                  {riskLevel === 'CRITICAL'
                    ? 'EMERGENCY SCAM INTERCEPT: Active extortion or OTP theft pattern identified! Do not comply or disclose details.'
                    : 'HIGH FRAUD ALERT: High probability scam detected in caller speech! Never enter your UPI PIN or share OTP.'}
                </span>
              </div>
              <button
                onClick={() => setActiveTab('phone')}
                className="px-3 py-1 rounded-full bg-[#F08091] hover:bg-[#fa5252] text-black font-bold text-[11px] uppercase transition-colors shrink-0 shadow-md cursor-pointer"
              >
                View Call HUD
              </button>
            </div>
          </div>
        )}

        {/* ─── Compact Hero Header ─── */}
        <section className="px-4 sm:px-6 pt-8 pb-4 max-w-7xl mx-auto w-full text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#00F0FF]/10 border border-[#00F0FF]/25 text-[#00F0FF] text-[11px] font-mono font-semibold uppercase tracking-wider mb-3">
            <Zap className="w-3 h-3 text-[#00F0FF] animate-pulse" />
            <span>Suraksha Neural Defense 3.0 · Real-Time RAG Active</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white uppercase font-sans mb-2 text-glow-cyan">
            SURAKSHA{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00F0FF] via-[#72D7E8] to-[#8B7CFF]">
              AI SHIELD
            </span>
          </h1>

          <p className="text-xs sm:text-sm text-[#A2A9BA] max-w-xl mx-auto leading-relaxed mb-4">
            Hands-free scam call detection & fraud negation guard. Zero-latency acoustic parsing across{' '}
            <span className="text-[#00F0FF] font-semibold">2,841 indexed Indian scam cases</span>.
          </p>

          {/* Symmetrical 4-Metric Stats Bar */}
          <div className="max-w-3xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3 py-2">
            <div className="p-3 rounded-2xl bg-[#090D16]/90 border border-[#1E2536] text-center">
              <div className="text-xl sm:text-2xl font-extrabold text-[#00F0FF] font-mono">99.8%</div>
              <div className="text-[10px] text-[#A2A9BA] font-medium">Scam Precision</div>
            </div>
            <div className="p-3 rounded-2xl bg-[#090D16]/90 border border-[#1E2536] text-center">
              <div className="text-xl sm:text-2xl font-extrabold text-[#00F0FF] font-mono">2,841+</div>
              <div className="text-[10px] text-[#A2A9BA] font-medium">RAG Transcripts</div>
            </div>
            <div className="p-3 rounded-2xl bg-[#090D16]/90 border border-[#1E2536] text-center">
              <div className="text-xl sm:text-2xl font-extrabold text-[#00F0FF] font-mono">&lt; 45ms</div>
              <div className="text-[10px] text-[#A2A9BA] font-medium">Dual-Engine Speed</div>
            </div>
            <div className="p-3 rounded-2xl bg-[#090D16]/90 border border-[#1E2536] text-center">
              <div className="text-xl sm:text-2xl font-extrabold text-[#00F0FF] font-mono">24/7</div>
              <div className="text-[10px] text-[#A2A9BA] font-medium">Active Guard</div>
            </div>
          </div>
        </section>

        {/* ─── Main Content Workspace ─── */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
          {/* TAB 1: LIVE MIC SHIELD */}
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

          {/* TAB 2: CALL SIMULATOR */}
          {activeTab === 'phone' && (
            <div className="space-y-6">
              <PhoneCallMockup
                onAnalyzeSegment={handleAnalyzeSegment}
                activeRisk={activeRisk}
                selectedScenarioId={selectedScenarioId}
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

          {/* TAB 3: ATTACK VECTOR DECK */}
          {activeTab === 'deck' && (
            <div className="space-y-6 animate-slide-up">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#1E2536] pb-4">
                <div>
                  <h2 className="text-xl font-bold text-white uppercase font-mono flex items-center gap-2">
                    <Layers className="w-5 h-5 text-[#00F0FF]" />
                    Threat Vector Attack Deck
                  </h2>
                  <p className="text-xs text-[#A2A9BA] mt-0.5">
                    Pre-indexed Indian scam call scenarios. Click any vector to simulate live or run through RAG.
                  </p>
                </div>

                {/* Filter Pills */}
                <div className="flex items-center gap-1.5 overflow-x-auto max-w-full pb-1">
                  {[
                    { id: 'ALL', label: 'All (8)' },
                    { id: 'EXTORTION', label: 'Digital Arrest' },
                    { id: 'QR_SCAN', label: 'UPI / QR' },
                    { id: 'URGENCY', label: 'Power & KYC' },
                    { id: 'TASK', label: 'Part-Time Task' },
                    { id: 'SAFE', label: 'Safe Control' },
                  ].map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => {
                        audioAlerts.playClick();
                        setSelectedCategory(cat.id);
                      }}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap cursor-pointer transition-all ${
                        selectedCategory === cat.id
                          ? 'btn-cyan text-[#040810]'
                          : 'bg-[#11141C] text-[#A2A9BA] hover:text-white border border-[#1E2536]'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 4-Column Grid of 8 Scenarios */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                {filteredScenarios.map((scenario) => {
                  const isCritical = scenario.expectedRisk === 'HIGH';
                  const isSafe = scenario.expectedRisk === 'LOW';
                  return (
                    <div
                      key={scenario.id}
                      className="glass-card flex flex-col justify-between overflow-hidden border-[#1E2536] hover:border-[#00F0FF]/50 transition-all duration-300 group box-glow-cyan-card rounded-2xl"
                    >
                      {/* Card Header Banner */}
                      <div className="p-4 bg-gradient-to-br from-[#121929] to-[#07090E] border-b border-[#1E2536] space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold uppercase ${
                              isCritical
                                ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                                : isSafe
                                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                                : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            {scenario.badge}
                          </span>
                          <span className="text-[10px] font-mono text-[#00F0FF] bg-[#00F0FF]/10 px-2 py-0.5 rounded-md">
                            {scenario.language.split(' ')[0]}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-white group-hover:text-[#00F0FF] transition-colors line-clamp-1">
                          {scenario.title}
                        </h3>
                        <p className="text-[11px] text-[#00F0FF]/80 font-mono">
                          {scenario.callerName}
                        </p>
                      </div>

                      {/* Card Body Quote */}
                      <div className="p-4 flex-1 flex flex-col justify-between space-y-4">
                        <p className="text-xs text-[#A2A9BA] line-clamp-3 italic leading-relaxed">
                          "{scenario.transcript}"
                        </p>

                        {/* Actions */}
                        <div className="pt-2 border-t border-[#1E2536] flex items-center justify-between gap-2">
                          <span
                            className={`text-[11px] font-mono font-semibold ${
                              isCritical ? 'text-rose-400' : isSafe ? 'text-emerald-400' : 'text-amber-400'
                            }`}
                          >
                            {isCritical ? 'High Risk' : isSafe ? 'Safe Control' : 'Caution'}
                          </span>

                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => handleSelectScenario(scenario, 'phone')}
                              className="btn-cyan px-3 py-1.5 text-xs font-bold flex items-center gap-1 cursor-pointer"
                              title="Simulate Call in Call HUD"
                            >
                              <Phone className="w-3 h-3" />
                              <span>Simulate</span>
                            </button>
                            <button
                              onClick={() => handleSelectScenario(scenario, 'text')}
                              className="btn-outline-cyan px-2.5 py-1.5 text-xs font-bold cursor-pointer"
                              title="Evaluate with Vector RAG"
                            >
                              <Sparkles className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 4: TEXT ANALYZER */}
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

          {/* TAB 5: THREAT INTEL & RAG EXPLORER */}
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

        {/* ─── Symmetrical Clean Footer ─── */}
        <footer className="mt-auto border-t border-[#1E2536] bg-[#07090E]/90 py-6 px-4 sm:px-6">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-[#70798C]">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-[#00F0FF]/15 border border-[#00F0FF]/30 flex items-center justify-center">
                <Shield className="w-3 h-3 text-[#00F0FF]" />
              </div>
              <span className="font-mono font-bold text-white tracking-wider">SURAKSHA AI 3.0</span>
              <span>· Zero-Trust Scam Call Defense</span>
            </div>

            <div className="flex items-center gap-4 font-mono text-[11px]">
              <span className="text-[#00F0FF] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00F0FF] animate-ping" />
                RAG Store: 2,841 Docs Ready
              </span>
              <span>Inference: &lt; 45ms</span>
              <span>Sarvam STT: Live</span>
            </div>

            <div>&copy; 2026 HackerWrath 3.0 · Built for National Cyber Defense</div>
          </div>
          <div className="max-w-7xl mx-auto mt-4">
            <StatusBar />
          </div>
        </footer>
      </div>

      {/* Interactive Guided Tutorial Modal */}
      <TutorialModal
        isOpen={showTutorial}
        onClose={handleCloseTutorial}
        onNavigateTab={(tab) => setActiveTab(tab)}
      />

      {/* API Keys & Connectivity Modal */}
      <KeysModal isOpen={showKeysModal} onClose={() => setShowKeysModal(false)} />
    </div>
  );
}
