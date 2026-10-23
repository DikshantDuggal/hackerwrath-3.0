import { useState, useEffect } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Shield,
  Mic,
  Phone,
  Database,
  Sparkles,
  Zap,
  Globe,
  CheckCircle2,
} from 'lucide-react';

interface TutorialModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateTab?: (tab: 'mic' | 'phone' | 'text' | 'intel') => void;
}

const tutorialSteps = [
  {
    step: 1,
    title: 'Welcome to Suraksha 3.0',
    subtitle: 'Autonomous AI Scam-Call Detection & Negation Guard',
    icon: <Shield className="w-8 h-8 text-[#00F0FF]" />,
    description:
      'Suraksha protects you against sophisticated phone scams, fake authority coercion (Digital Arrest), and reverse-UPI payment traps in real time.',
    highlight: 'Grounded by 2,841 real Indian fraud dialogues and Sarvam AI multilingual acoustic intelligence.',
    actionLabel: 'Next: Live Mic Shield',
  },
  {
    step: 2,
    title: 'Live Microphone Shield',
    subtitle: 'Hands-Free Protection During Live Calls',
    icon: <Mic className="w-8 h-8 text-[#00F0FF]" />,
    description:
      'Put your phone on speakerphone during any incoming call and tap the central microphone button. Suraksha streams 16kHz audio, transcribes live speech, and detects deceptive coercion every ~7-8 words.',
    highlight: 'Works across mixed Hindi, Indian English, and Punjabi speech.',
    actionLabel: 'Next: Call Simulator',
    tab: 'mic' as const,
  },
  {
    step: 3,
    title: 'Interactive Call Simulator HUD',
    subtitle: 'Experience Live Scam Interceptions',
    icon: <Phone className="w-8 h-8 text-[#72D7E8]" />,
    description:
      'Practice against realistic threat scenarios including CBI Digital Arrest, Customs Drug Parcels, and Electricity Power Cut threats. Watch the simulated caller HUD alert you before you enter a UPI PIN.',
    highlight: 'Includes both Nordic Editorial and Cyberpunk HUD interfaces.',
    actionLabel: 'Next: Grounded RAG Citations',
    tab: 'phone' as const,
  },
  {
    step: 4,
    title: 'Grounded RAG Vector Citations',
    subtitle: 'Evidence-Backed Scam Classification',
    icon: <Database className="w-8 h-8 text-[#8B7CFF]" />,
    description:
      'Every speech segment is vectorized and matched against our 2,841-transcript database using cosine similarity. The Risk Meter surfaces the top-3 nearest scam precedents with similarity scores and rationale.',
    highlight: 'No hallucinated risks — every warning is backed by semantic vector evidence.',
    actionLabel: 'Next: Smart Negation',
    tab: 'intel' as const,
  },
  {
    step: 5,
    title: 'Smart Negation & Zero False Alarms',
    subtitle: 'Distinguishes Protection from Fraud',
    icon: <Zap className="w-8 h-8 text-[#63D6A5]" />,
    description:
      'Suraksha understands contextual intent. It distinguishes between a fraudster demanding "Share your OTP" and an official advisory saying "Never share your OTP", suppressing false alarms on genuine safety tips.',
    highlight: 'Contextual AI Director checks caller claims, pressure tactics, and intent.',
    actionLabel: 'Next: Threat Intel & Text AI',
    tab: 'text' as const,
  },
  {
    step: 6,
    title: 'Threat Intel & Text Analyzer',
    subtitle: 'Explore Signatures & Test Messages',
    icon: <Sparkles className="w-8 h-8 text-[#F2C879]" />,
    description:
      'Paste suspicious SMS messages, explore synchronized fraud signatures across calls, or test the RAG vector store directly with your own phrases.',
    highlight: 'Ready to experience Suraksha 3.0? Click "Get Started" to launch your shield.',
    actionLabel: 'Get Started',
  },
];

export default function TutorialModal({ isOpen, onClose, onNavigateTab }: TutorialModalProps) {
  const [currentStep, setCurrentStep] = useState(0);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowRight') {
        setCurrentStep((prev) => Math.min(tutorialSteps.length - 1, prev + 1));
      } else if (e.key === 'ArrowLeft') {
        setCurrentStep((prev) => Math.max(0, prev - 1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const current = tutorialSteps[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === tutorialSteps.length - 1;

  const handleNext = () => {
    if (isLast) {
      onClose();
      setCurrentStep(0);
    } else {
      const nextIdx = currentStep + 1;
      setCurrentStep(nextIdx);
      if (onNavigateTab && tutorialSteps[nextIdx].tab) {
        onNavigateTab(tutorialSteps[nextIdx].tab);
      }
    }
  };

  const handlePrev = () => {
    const prevIdx = Math.max(0, currentStep - 1);
    setCurrentStep(prevIdx);
    if (onNavigateTab && tutorialSteps[prevIdx].tab) {
      onNavigateTab(tutorialSteps[prevIdx].tab);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog (Responsive & Centered) */}
      <div className="relative glass-card max-w-lg w-full p-6 sm:p-8 border border-[#1E2536] rounded-3xl animate-slide-up shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Top Header Bar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#00F0FF] bg-[#00F0FF]/10 px-2.5 py-1 rounded-full border border-[#00F0FF]/20">
              Interactive Guide · Step {currentStep + 1} of {tutorialSteps.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="text-xs text-[#70798C] hover:text-white transition-colors cursor-pointer px-2 py-1"
            >
              Skip
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-white/10 text-[#70798C] hover:text-white transition-colors cursor-pointer"
              aria-label="Close Guide"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Step Progress Line */}
        <div className="flex gap-1.5 mb-6">
          {tutorialSteps.map((_, i) => (
            <button
              key={i}
              onClick={() => {
                setCurrentStep(i);
                if (onNavigateTab && tutorialSteps[i].tab) {
                  onNavigateTab(tutorialSteps[i].tab);
                }
              }}
              className="h-1.5 rounded-full flex-1 transition-all cursor-pointer"
              style={{
                background:
                  i === currentStep
                    ? '#00F0FF'
                    : i < currentStep
                    ? 'rgba(0, 240, 255, 0.4)'
                    : 'rgba(255, 255, 255, 0.1)',
                boxShadow: i === currentStep ? '0 0 10px rgba(0,240,255,0.6)' : 'none',
              }}
              title={`Go to step ${i + 1}`}
            />
          ))}
        </div>

        {/* Center Icon & Content */}
        <div className="text-center space-y-4 mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#00F0FF]/10 border border-[#00F0FF]/30 box-glow-cyan">
            {current.icon}
          </div>

          <div>
            <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              {current.title}
            </h3>
            <p className="text-xs text-[#00F0FF] font-mono mt-1 font-medium">
              {current.subtitle}
            </p>
          </div>

          <p className="text-sm text-[#A2A9BA] leading-relaxed">
            {current.description}
          </p>

          <div className="p-3.5 rounded-2xl bg-[#090D16] border border-[#1E2536] text-left flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-[#00F0FF] shrink-0 mt-0.5" />
            <p className="text-xs text-[#E8ECF2] leading-relaxed font-medium">
              {current.highlight}
            </p>
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between pt-4 border-t border-[#1E2536]">
          <button
            onClick={handlePrev}
            disabled={isFirst}
            className={`px-4 py-2 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              isFirst
                ? 'opacity-30 cursor-not-allowed text-[#70798C]'
                : 'text-[#A2A9BA] hover:text-white hover:bg-white/5 border border-[#1E2536]'
            }`}
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Back</span>
          </button>

          <span className="text-[11px] font-mono text-[#70798C] hidden sm:inline">
            Press Esc to close · Arrow keys to navigate
          </span>

          <button
            onClick={handleNext}
            className="btn-cyan px-5 py-2 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg"
          >
            <span>{current.actionLabel}</span>
            {!isLast && <ChevronRight className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
