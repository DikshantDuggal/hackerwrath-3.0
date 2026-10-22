import { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';

const DEMO_SCENARIOS = [
  {
    label: '🇮🇳 Hindi QR Scam',
    text: 'भाई मैं आर्मी में हूँ, क्यूआर भेज रहा हूँ, स्कैन करो पेमेंट तुरंत आ जाएगा।',
  },
  {
    label: '🏛️ RBI Impersonation',
    text: 'I am calling from RBI Cyber Crime Branch. An arrest warrant is issued against your Aadhaar. Install AnyDesk and share the OTP immediately.',
  },
  {
    label: '🔒 OTP Request (Hindi)',
    text: 'Aapke phone pe ek OTP aaya hai, jaldi se batao. Account block ho jayega agar nahi bataya.',
  },
  {
    label: '✅ Safe - Protective Advice',
    text: 'Never share your OTP or UPI PIN with anyone on a phone call. Kabhi bhi kisi ko OTP mat batana.',
  },
  {
    label: '🛒 Legitimate Buyer',
    text: 'Can you send me your QR? I\'ll pay you now. I am interested in the refrigerator you listed.',
  },
  {
    label: '🇵🇦 Punjabi OTP Scam',
    text: 'ਤੁਹਾਡੇ ਫੋਨ ਤੇ ਓਟੀਪੀ ਆਇਆ ਹੋਣਾ, ਮੈਨੂੰ ਦੱਸੋ ਜਲਦੀ। ਖਾਤਾ ਬੰਦ ਹੋ ਜਾਵੇਗਾ।',
  },
];

interface TextInputPanelProps {
  onAnalyze: (text: string) => Promise<void>;
  isProcessing: boolean;
}

export default function TextInputPanel({ onAnalyze, isProcessing }: TextInputPanelProps) {
  const [text, setText] = useState('');

  const handleSubmit = async () => {
    if (!text.trim() || isProcessing) return;
    await onAnalyze(text);
    setText('');
  };

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-[var(--purple-bright)]" />
        Text Analysis
      </h3>

      {/* Input */}
      <div className="relative mb-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste or type a suspicious transcript here..."
          className="glass-input w-full p-4 pr-12 min-h-[100px] resize-none text-sm"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              handleSubmit();
            }
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || isProcessing}
          className="absolute bottom-3 right-3 p-2 rounded-lg bg-[var(--purple-dim)] hover:bg-[var(--purple-glow)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4 text-white" />
        </button>
      </div>

      {/* Demo Scenarios */}
      <div>
        <p className="text-xs text-[var(--text-muted)] mb-2">Quick test scenarios:</p>
        <div className="flex flex-wrap gap-2">
          {DEMO_SCENARIOS.map((scenario, i) => (
            <button
              key={i}
              onClick={() => setText(scenario.text)}
              className="text-xs px-3 py-1.5 rounded-full glass hover:bg-[var(--glass-bg-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all border border-transparent hover:border-[var(--purple-dim)]/30"
            >
              {scenario.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
