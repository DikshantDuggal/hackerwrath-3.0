import { useState } from 'react';
import { X, ChevronRight } from 'lucide-react';
import Guardian from './Guardian';
import type { Tone } from '../spell/signals';

interface TutorialModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const steps: Array<{ title: string; tone: Tone; description: string; tip: string }> = [
  {
    title: 'A guardian on every call',
    tone: 'listening',
    description:
      'Edgerunners listens to a call and warns you the moment a caller asks for something no honest caller needs: a code, your UPI PIN, a QR scan, or an app on your phone.',
    tip: 'Works in English, Hindi and Punjabi, even when they’re mixed.',
  },
  {
    title: 'Tap the shield to listen',
    tone: 'calm',
    description:
      'Put the call on speaker and tap the shield. Every few words go to Sarvam for speech to text, then through the detector, while the call carries on.',
    tip: 'With headphones, pick “Mic + call audio” to hear Telegram calls directly.',
  },
  {
    title: 'Amber means listen carefully',
    tone: 'possible',
    description: 'When something sounds off but they haven’t asked yet, the shield turns amber and shows what they said.',
    tip: 'There are only two warnings: Possible risk, then High risk. Never a green “safe”.',
  },
  {
    title: 'Red means don’t',
    tone: 'high',
    description:
      'When they ask, the alert fills the screen with what not to do, what they said, and one question to help you see the trick. It looks different each time, so it never becomes wallpaper.',
    tip: 'Safety advice like “never share your OTP” doesn’t set it off.',
  },
];

export default function TutorialModal({ isOpen, onClose }: TutorialModalProps) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 sb-fade backdrop-blur-sm" style={{ background: 'var(--sb-scrim)' }} onClick={onClose} />

      <div role="dialog" aria-modal="true" aria-labelledby="sb-tour-title" className="relative max-w-lg w-full rounded-[32px] bg-paper p-6 sm:p-8 sb-rise shadow-2xl">
        <button type="button" onClick={onClose} aria-label="Close" className="sb-btn sb-btn-ghost absolute top-4 right-4 w-11 h-11 p-0 rounded-full">
          <X className="w-5 h-5" />
        </button>

        <div className="flex gap-1.5 mb-4 pr-12">
          {steps.map((_, i) => (
            <span key={i} className={`h-1.5 rounded-full flex-1 transition-colors ${i <= currentStep ? 'bg-accent' : 'bg-line'}`} />
          ))}
        </div>

        <div className="flex justify-center">
          <Guardian tone={step.tone} size={170} />
        </div>

        <h2 id="sb-tour-title" className="sb-display text-[34px] mt-2 mb-3">
          {step.title}
        </h2>
        <p className="text-[16px] leading-6 text-muted mb-4">{step.description}</p>
        <p className="sb-soft rounded-[16px] px-4 py-3 text-[14px] font-semibold text-head mb-6">{step.tip}</p>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            className="sb-btn sb-btn-ghost"
            disabled={currentStep === 0}
          >
            Back
          </button>
          <span className="text-[12px] text-faint">
            {currentStep + 1} of {steps.length}
          </span>
          <button
            type="button"
            onClick={() => {
              if (isLast) {
                onClose();
                setCurrentStep(0);
              } else {
                setCurrentStep(currentStep + 1);
              }
            }}
            className="sb-btn sb-btn-primary"
          >
            {isLast ? 'Start' : 'Next'}
            {!isLast && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
