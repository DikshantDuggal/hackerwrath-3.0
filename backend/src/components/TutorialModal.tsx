import { useState } from 'react';
import { X, ChevronRight, Shield, Mic, Send, Eye, Zap, Globe } from 'lucide-react';

interface TutorialModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const steps = [
  {
    title: 'Welcome to Suraksha',
    icon: <Shield className="w-10 h-10 text-[var(--purple-bright)]" />,
    description: 'Suraksha is your AI-powered scam call detection shield. It listens to phone calls in real-time and alerts you when it detects suspicious patterns like OTP requests, impersonation, or urgent payment demands.',
    tip: 'Works with English, Hindi, and Punjabi — even mixed-language calls!',
  },
  {
    title: 'Live Voice Detection',
    icon: <Mic className="w-10 h-10 text-[var(--green-accent)]" />,
    description: 'Click the microphone button to start recording. Suraksha captures audio in 5-second chunks, transcribes it using Sarvam AI Saaras, and runs it through our detection pipeline — all in real-time.',
    tip: 'Put your phone on speaker and let Suraksha listen to the call.',
  },
  {
    title: 'Text Analysis',
    icon: <Send className="w-10 h-10 text-[var(--purple-candle)]" />,
    description: 'Can\'t use the mic? No problem! Paste any suspicious transcript text into the input box and Suraksha will analyze it instantly for scam patterns.',
    tip: 'Try pasting: "I am calling from RBI. An arrest warrant is issued against your Aadhaar."',
  },
  {
    title: 'Understanding Risk Levels',
    icon: <Eye className="w-10 h-10 text-[var(--amber-warn)]" />,
    description: 'Suraksha uses a dual-engine detection system: a Rule-Based Engine scans for 8 categories of scam patterns, while the Contextual AI Director analyzes the caller\'s actual intent.',
    tip: 'GREEN = Safe · YELLOW = Be Cautious · RED = Likely Scam · GREY = Insufficient Data',
  },
  {
    title: 'Smart Protection',
    icon: <Zap className="w-10 h-10 text-[var(--green-bright)]" />,
    description: 'Suraksha is smart enough to distinguish between actual scam requests ("Share your OTP") and protective advice ("Never share your OTP"). It won\'t raise false alarms on safety tips.',
    tip: 'The system even detects prompt injection attempts trying to bypass detection!',
  },
  {
    title: 'Multilingual Support',
    icon: <Globe className="w-10 h-10 text-[var(--purple-bright)]" />,
    description: 'Suraksha understands English, Hindi (Devanagari + Romanized), Punjabi (Gurmukhi + Romanized), and code-mixed speech. Perfect for real-world Indian phone calls.',
    tip: 'Try: "भाई QR भेज रहा हूँ, scan करो payment आ जाएगा" — Suraksha will catch this!',
  },
];

export default function TutorialModal({ isOpen, onClose }: TutorialModalProps) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="glass-card relative max-w-lg w-full p-8 animate-slide-up" style={{ borderColor: 'rgba(139, 92, 246, 0.3)' }}>
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-white/5 transition-colors"
        >
          <X className="w-5 h-5 text-[var(--text-muted)]" />
        </button>

        {/* Step indicator */}
        <div className="flex gap-1.5 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className="h-1 rounded-full flex-1 transition-all duration-300"
              style={{
                background: i <= currentStep
                  ? 'linear-gradient(90deg, var(--purple-glow), var(--green-accent))'
                  : 'rgba(255,255,255,0.05)',
              }}
            />
          ))}
        </div>

        {/* Content */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-[var(--purple-dim)]/20 mb-4">
            {step.icon}
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-3">{step.title}</h2>
          <p className="text-[var(--text-secondary)] leading-relaxed">{step.description}</p>
        </div>

        {/* Tip */}
        <div className="glass p-4 mb-6 border-[var(--green-accent)]/20">
          <p className="text-sm text-[var(--green-accent)]">
            <span className="font-semibold">💡 Tip: </span>{step.tip}
          </p>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors disabled:opacity-30"
            disabled={currentStep === 0}
          >
            ← Back
          </button>

          <span className="text-xs text-[var(--text-muted)]">
            {currentStep + 1} / {steps.length}
          </span>

          <button
            onClick={() => {
              if (isLast) {
                onClose();
                setCurrentStep(0);
              } else {
                setCurrentStep(currentStep + 1);
              }
            }}
            className="btn-primary flex items-center gap-2 text-sm py-2 px-5"
          >
            {isLast ? 'Get Started' : 'Next'}
            {!isLast && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
