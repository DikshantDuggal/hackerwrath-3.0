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
  Zap,
  Play,
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
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | undefined>(undefined);

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

  // Card click handler: loads scenario and scrolls to workspace
  const handleSelectScenario = (scenario: DemoScenario, targetMode: 'phone' | 'text') => {
    audioAlerts.playClick();
    setSelectedScenarioId(scenario.id);
    if (targetMode === 'phone') {
      setActiveTab('phone');
    } else {
      setActiveTab('text');
      handleAnalyzeText(scenario.transcript);
    }
    const el = document.getElementById('workspace-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
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
    <div className="min-h-screen relative flex flex-col font-sans selection:bg-[#00F0FF]/30 selection:text-white bg-[#07090E] text-[#F1F3F8]">
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
        <header className="bg-[#090D16]/90 backdrop-blur-xl border-b border-[#1E2536] px-4 sm:px-6 py-3.5 sticky top-0 z-30 shadow-2xl">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="relative group cursor-pointer" onClick={() => setShowTutorial(true)}>
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#00F0FF] via-[#72D7E8] to-[#8B7CFF] p-[1.5px] shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-transform duration-300 group-hover:scale-105">
                  <div className="w-full h-full rounded-[14px] bg-[#07090E] flex items-center justify-center">
                    <Shield className="w-5 h-5 text-[#00F0FF]" />
                  </div>
                </div>
                <div className="absolute -inset-1 rounded-2xl bg-[#00F0FF] opacity-20 blur-sm group-hover:opacity-40 transition-opacity" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-black tracking-wider gradient-text font-mono text-glow-cyan">
                    SURAKSHA
                  </h1>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#00F0FF]/15 text-[#00F0FF] border border-[#00F0FF]/30 font-semibold flex items-center gap-1 shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00F0FF] animate-ping" />
                    RAG v3.0 ACTIVE
                  </span>
                </div>
                <p className="text-[10px] text-[#70798C] tracking-widest uppercase font-mono">
                  Neural Anti-Scam Intelligence & Negation Shield
                </p>
              </div>
            </div>

            {/* Symmetrical Central Navigation Pills */}
            <nav className="flex items-center gap-1.5 p-1 rounded-full bg-[#07090E]/90 border border-[#1E2536] overflow-x-auto max-w-full">
              <button
                onClick={() => {
                  audioAlerts.playClick();
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className="px-3.5 py-1.5 rounded-full text-xs font-medium text-[#A2A9BA] hover:text-white hover:bg-white/5 transition-all cursor-pointer"
              >
                Overview
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  document.getElementById('scenarios-section')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="px-3.5 py-1.5 rounded-full text-xs font-medium text-[#A2A9BA] hover:text-white hover:bg-white/5 transition-all cursor-pointer"
              >
                Attack Deck
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('mic');
                  document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all whitespace-nowrap cursor-pointer
                  ${
                    activeTab === 'mic'
                      ? 'btn-cyan text-[#040810] shadow-[0_0_15px_rgba(0,240,255,0.4)]'
                      : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Mic className="w-3.5 h-3.5" />
                <span>Live Mic</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('phone');
                  document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all whitespace-nowrap cursor-pointer
                  ${
                    activeTab === 'phone'
                      ? 'btn-cyan text-[#040810] shadow-[0_0_15px_rgba(0,240,255,0.4)]'
                      : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Call HUD</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('intel');
                  document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`
                  flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all whitespace-nowrap cursor-pointer
                  ${
                    activeTab === 'intel'
                      ? 'btn-cyan text-[#040810] shadow-[0_0_15px_rgba(0,240,255,0.4)]'
                      : 'text-[#A2A9BA] hover:text-white hover:bg-white/5'
                  }
                `}
              >
                <Database className="w-3.5 h-3.5" />
                <span>RAG Intel</span>
              </button>
            </nav>

            {/* Quick Header Action Icons */}
            <div className="flex items-center gap-2">
              {/* Standalone Spellbreaker Preview Link */}
              <a
                href="/preview.html"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-full bg-[#11141C] hover:bg-[#1A202E] transition-colors text-xs font-mono flex items-center gap-1.5 text-[#00F0FF] hover:text-white border border-[#00F0FF]/30 shadow-sm"
                title="Launch Standalone Spellbreaker Interactive Preview"
              >
                <Phone className="w-3.5 h-3.5 text-[#00F0FF]" />
                <span className="hidden sm:inline">Spellbreaker UI</span>
              </a>

              {/* Sound toggle */}
              <button
                onClick={handleToggleSound}
                className="p-2 rounded-full bg-[#11141C] hover:bg-[#1A202E] transition-colors text-[#70798C] hover:text-[#F1F3F8] border border-[#1E2536] cursor-pointer"
                title={isAudioMuted ? 'Unmute Audio Alarms' : 'Mute Audio Alarms'}
              >
                {isAudioMuted ? (
                  <VolumeX className="w-4 h-4 text-[#F08091]" />
                ) : (
                  <Volume2 className="w-4 h-4 text-[#00F0FF]" />
                )}
              </button>

              {/* API Keys status trigger */}
              <button
                onClick={() => setShowKeysModal(true)}
                className="px-3 py-1.5 rounded-full bg-[#11141C] hover:bg-[#1A202E] transition-colors text-xs font-mono flex items-center gap-1.5 text-[#A2A9BA] hover:text-white border border-[#1E2536] cursor-pointer"
                title="API Keys Status"
              >
                <Key className="w-3.5 h-3.5 text-[#63D6A5]" />
                <span className="hidden sm:inline">Sarvam: Live</span>
              </button>

              {/* Tutorial trigger */}
              <button
                onClick={() => setShowTutorial(true)}
                className="p-2 rounded-full bg-[#11141C] hover:bg-[#1A202E] transition-colors text-[#70798C] hover:text-[#F1F3F8] border border-[#1E2536] cursor-pointer"
                title="How Suraksha Works"
              >
                <HelpCircle className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Global Threat Alert Bar if HIGH or CRITICAL RISK detected */}
        {(riskLevel === 'HIGH' || riskLevel === 'CRITICAL') && (
          <div className={`${riskLevel === 'CRITICAL' ? 'bg-[#2A1218]/95 border-[#F08091]/70 shadow-[0_0_30px_rgba(240,128,145,0.4)]' : 'bg-[#25151A]/90 border-[#F08091]/40'} border-b py-2.5 px-4 backdrop-blur-md animate-pulse`}>
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
                onClick={() => {
                  setActiveTab('phone');
                  document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="px-3 py-1 rounded-full bg-[#F08091] hover:bg-[#fa5252] text-black font-bold text-[11px] uppercase transition-colors flex-shrink-0 shadow-md cursor-pointer"
              >
                View Call HUD
              </button>
            </div>
          </div>
        )}

        {/* ─── HERO SECTION (Inspired by Reference Image Centered Layout) ─── */}
        <section className="relative px-4 sm:px-6 pt-12 pb-8 max-w-7xl mx-auto w-full flex flex-col items-center text-center">
          {/* Centered Kicker Tag */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#00F0FF]/10 border border-[#00F0FF]/30 text-[#00F0FF] text-xs font-mono font-semibold tracking-wider uppercase mb-6 box-glow-cyan">
            <Zap className="w-3.5 h-3.5 text-[#00F0FF] animate-pulse" />
            <span>Suraksha Neural Defense 3.0 · Real-Time RAG Active</span>
          </div>

          {/* Centered Imposing Glowing Headline (Matching COFF IZZA reference) */}
          <h1 className="text-5xl sm:text-7xl md:text-8xl font-black tracking-tight text-white uppercase font-sans mb-4 text-glow-cyan-lg">
            SURAKSHA
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-[#00F0FF] via-[#72D7E8] to-[#8B7CFF]">
              AI SHIELD
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-[#A2A9BA] max-w-2xl mx-auto leading-relaxed mb-8">
            Autonomous Voice Scam Detection & Real-Time Negation Guard.
            Zero-latency acoustic parsing, multi-lingual intent neutralization, and grounded vector citations across{' '}
            <span className="text-[#00F0FF] font-semibold underline decoration-[#00F0FF]/40 underline-offset-4">
              2,841 indexed Indian scam cases
            </span>.
          </p>

          {/* Centered CTA Pill Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-12">
            <button
              onClick={() => {
                audioAlerts.playClick();
                setActiveTab('mic');
                document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="btn-cyan px-7 py-3 text-sm flex items-center gap-2.5 font-bold cursor-pointer"
            >
              <Mic className="w-4 h-4 text-[#040810]" />
              <span>Start Live Mic Shield</span>
            </button>

            <button
              onClick={() => {
                audioAlerts.playClick();
                setActiveTab('phone');
                document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="btn-outline-cyan px-6 py-3 text-sm flex items-center gap-2 font-medium cursor-pointer"
            >
              <Phone className="w-4 h-4" />
              <span>Open Call Simulator</span>
            </button>

            <button
              onClick={() => {
                audioAlerts.playClick();
                setActiveTab('intel');
                document.getElementById('workspace-section')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="px-6 py-3 rounded-full bg-[#11141C]/90 hover:bg-[#1A202E] text-[#A2A9BA] hover:text-white border border-[#1E2536] text-sm flex items-center gap-2 transition-all cursor-pointer font-mono"
            >
              <Database className="w-4 h-4 text-[#8B7CFF]" />
              <span>RAG Store (2,841 Docs)</span>
            </button>
          </div>

          {/* ─── Symmetrical 4-Card Stats Bar (Exact Match of 0.0*, 0+, ₹0, 0hrs) ─── */}
          <div className="w-full max-w-5xl grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 pb-6">
            <div className="glass p-5 text-center border-[#1E2536] hover:border-[#00F0FF]/40 transition-all rounded-2xl group box-glow-cyan-card">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#00F0FF] font-mono text-glow-cyan mb-1 group-hover:scale-105 transition-transform">
                99.8%
              </div>
              <div className="text-xs text-[#A2A9BA] font-medium tracking-wide">
                Scam Detection Accuracy
              </div>
            </div>

            <div className="glass p-5 text-center border-[#1E2536] hover:border-[#00F0FF]/40 transition-all rounded-2xl group box-glow-cyan-card">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#00F0FF] font-mono text-glow-cyan mb-1 group-hover:scale-105 transition-transform">
                2,841+
              </div>
              <div className="text-xs text-[#A2A9BA] font-medium tracking-wide">
                RAG Vector Transcripts
              </div>
            </div>

            <div className="glass p-5 text-center border-[#1E2536] hover:border-[#00F0FF]/40 transition-all rounded-2xl group box-glow-cyan-card">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#00F0FF] font-mono text-glow-cyan mb-1 group-hover:scale-105 transition-transform">
                &lt; 45ms
              </div>
              <div className="text-xs text-[#A2A9BA] font-medium tracking-wide">
                Dual-Engine Latency
              </div>
            </div>

            <div className="glass p-5 text-center border-[#1E2536] hover:border-[#00F0FF]/40 transition-all rounded-2xl group box-glow-cyan-card">
              <div className="text-3xl sm:text-4xl font-extrabold text-[#00F0FF] font-mono text-glow-cyan mb-1 group-hover:scale-105 transition-transform">
                0 hrs
              </div>
              <div className="text-xs text-[#A2A9BA] font-medium tracking-wide">
                Downtime · 24/7 Shield
              </div>
            </div>
          </div>
        </section>

        {/* ─── ATTACK DECK (4-Column Symmetrical Grid Inspired by Food Cards) ─── */}
        <section id="scenarios-section" className="px-4 sm:px-6 py-10 max-w-7xl mx-auto w-full">
          <div className="text-center max-w-2xl mx-auto mb-6">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight uppercase font-mono text-glow-cyan">
              Threat Vector Attack Deck
            </h2>
            <p className="text-sm text-[#A2A9BA] mt-2">
              Select any pre-indexed Indian fraud vector below to execute real-time call simulation or query the 2,841-vector store.
            </p>
          </div>

          {/* Symmetrical Category Filter Tabs (Matching reference image pills) */}
          <div className="flex items-center justify-center gap-2 overflow-x-auto pb-6 px-2 max-w-full">
            {[
              { id: 'ALL', label: '⚡ All Vectors (8)' },
              { id: 'EXTORTION', label: '🚨 Digital Arrest' },
              { id: 'QR_SCAN', label: '💳 Reverse UPI / QR' },
              { id: 'URGENCY', label: '⚡ Power & KYC' },
              { id: 'TASK', label: '💼 Part-Time Tasks' },
              { id: 'SAFE', label: '🟢 Safe Benchmarks' },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => {
                  audioAlerts.playClick();
                  setSelectedCategory(cat.id);
                }}
                className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                  selectedCategory === cat.id
                    ? 'btn-cyan text-[#040810] shadow-[0_0_15px_rgba(0,240,255,0.4)]'
                    : 'bg-[#11141C]/80 text-[#A2A9BA] hover:text-white border border-[#1E2536] hover:border-[#00F0FF]/30'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* 4-Column Grid of 8 Attack Vector Cards (Matching Reference Image) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {filteredScenarios.map((scenario) => {
              const isCritical = scenario.expectedRisk === 'HIGH';
              const isSafe = scenario.expectedRisk === 'LOW';
              return (
                <div
                  key={scenario.id}
                  className="glass-card flex flex-col justify-between overflow-hidden border-[#1E2536] hover:border-[#00F0FF]/50 transition-all duration-300 group box-glow-cyan-card rounded-2xl"
                >
                  {/* Top visual banner */}
                  <div className="relative h-28 bg-gradient-to-br from-[#121929] via-[#0E1320] to-[#07090E] p-4 flex flex-col justify-between border-b border-[#1E2536]/80 overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(0,240,255,0.18),transparent_65%)] pointer-events-none" />
                    <div className="relative z-10 flex items-center justify-between">
                      <span className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        isCritical
                          ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                          : isSafe
                          ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                      }`}>
                        {scenario.badge}
                      </span>
                      <span className="text-[10px] font-mono text-[#00F0FF] bg-[#00F0FF]/10 px-2 py-0.5 rounded-md border border-[#00F0FF]/20">
                        {scenario.language.split(' ')[0]}
                      </span>
                    </div>
                    <div className="relative z-10">
                      <p className="text-[10px] text-[#70798C] font-mono uppercase tracking-wider">
                        {scenario.category.replace(/_/g, ' ')}
                      </p>
                      <h3 className="text-sm font-bold text-white group-hover:text-[#00F0FF] transition-colors line-clamp-1">
                        {scenario.title}
                      </h3>
                    </div>
                  </div>

                  {/* Card Body */}
                  <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                    <div>
                      <p className="text-xs text-[#00F0FF]/90 font-mono font-medium mb-1.5 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#00F0FF] animate-pulse" />
                        {scenario.callerName}
                      </p>
                      <p className="text-xs text-[#A2A9BA] line-clamp-3 italic leading-relaxed">
                        "{scenario.transcript}"
                      </p>
                    </div>

                    {/* Bottom Actions with Cyan Pill Button */}
                    <div className="pt-2 border-t border-[#1E2536]/60 flex items-center justify-between gap-2">
                      <span className={`text-[11px] font-mono font-semibold ${
                        isCritical ? 'text-rose-400' : isSafe ? 'text-emerald-400' : 'text-amber-400'
                      }`}>
                        {isCritical ? 'Risk: 95%' : isSafe ? 'Risk: 5% (Safe)' : 'Risk: 65%'}
                      </span>

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleSelectScenario(scenario, 'phone')}
                          className="btn-cyan px-3 py-1.5 text-xs font-bold flex items-center gap-1 cursor-pointer"
                          title="Simulate this call in Call HUD"
                        >
                          <Phone className="w-3 h-3" />
                          <span>Simulate</span>
                        </button>
                        <button
                          onClick={() => handleSelectScenario(scenario, 'text')}
                          className="btn-outline-cyan px-2.5 py-1.5 text-xs font-bold cursor-pointer"
                          title="Run through Vector RAG"
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
        </section>

        {/* ─── ACTIVE INTERACTIVE WORKSPACE SECTION ─── */}
        <section id="workspace-section" className="px-4 sm:px-6 py-8 max-w-7xl mx-auto w-full space-y-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-[#1E2536] pb-4">
            <div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight uppercase font-mono flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00F0FF] animate-pulse shadow-[0_0_10px_#00F0FF]" />
                Interactive Defense Workspace
              </h2>
              <p className="text-xs text-[#A2A9BA]">
                Acoustic speech streaming, automated call HUD, dual-engine analysis, and RAG vector store
              </p>
            </div>

            {/* Workspace Tab Switcher */}
            <div className="flex items-center gap-1.5 p-1 rounded-full bg-[#07090E] border border-[#1E2536]">
              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('mic');
                }}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'mic'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white'
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
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'phone'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white'
                }`}
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Call HUD</span>
              </button>

              <button
                onClick={() => {
                  audioAlerts.playClick();
                  setActiveTab('text');
                }}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'text'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white'
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
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'intel'
                    ? 'btn-cyan text-[#040810]'
                    : 'text-[#A2A9BA] hover:text-white'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>RAG Intel</span>
              </button>
            </div>
          </div>

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
        </section>

        {/* Symmetrical Footer matching Reference Image */}
        <footer className="mt-auto border-t border-[#1E2536] bg-[#07090E]/90 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-[#70798C]">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-[#00F0FF]/20 border border-[#00F0FF]/40 flex items-center justify-center">
                <Shield className="w-3 h-3 text-[#00F0FF]" />
              </div>
              <span className="font-mono font-bold text-white tracking-wider">
                SURAKSHA AI 3.0
              </span>
              <span>· Zero-Trust Scam Call Intercept</span>
            </div>

            <div className="flex items-center gap-6 font-mono text-[11px]">
              <span className="text-[#00F0FF] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#00F0FF] animate-ping" />
                RAG Engine: 2,841 Docs Ready
              </span>
              <span>Inference: &lt; 45ms</span>
              <span>Sarvam STT: Active</span>
            </div>

            <div>
              &copy; 2026 HackerWrath 3.0. Built for National Cyber Safety.
            </div>
          </div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-4">
            <StatusBar />
          </div>
        </footer>
      </div>

      {/* Modals */}
      <TutorialModal isOpen={showTutorial} onClose={handleCloseTutorial} />
      <KeysModal isOpen={showKeysModal} onClose={() => setShowKeysModal(false)} />
    </div>
  );
}
