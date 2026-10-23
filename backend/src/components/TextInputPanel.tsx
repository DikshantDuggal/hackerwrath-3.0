import { useState } from 'react';
import { Send, Sparkles, Database, Shield, RefreshCw } from 'lucide-react';

const DEMO_SCENARIOS = [
  {
    label: '🇮🇳 Hindi Army QR Scam',
    text: 'भाई मैं आर्मी कैंट से बोल रहा हूँ, क्यूआर कोड भेज रहा हूँ, स्कैन करो और यूपीआई पिन डालो पेमेंट तुरंत आ जाएगा।',
    category: 'QR_SCAN',
  },
  {
    label: '🏛️ CBI Digital Arrest Extortion',
    text: 'This is Officer Verma calling from CBI Cyber Crime Branch. An arrest warrant is issued on your Aadhaar card for money laundering. Transfer ₹50,000 security clearance deposit to RBI escrow immediately.',
    category: 'DIGITAL_ARREST',
  },
  {
    label: '🔒 Bank KYC OTP Suspension',
    text: 'Aapke phone pe ek 6 digit ka bank verification OTP aaya hai, jaldi se batao. Account block ho jayega agar nahi bataya.',
    category: 'OTP_PHISHING',
  },
  {
    label: '⚡ Electricity Bill APK Hijack',
    text: 'Your electricity power connection will be disconnected tonight. Install AnyDesk application immediately to update your payment.',
    category: 'REMOTE_ACCESS',
  },
  {
    label: '✅ Safe - Protective Advice',
    text: 'Never share your confidential OTP or enter your UPI PIN with anyone on an incoming phone call. Call your bank directly from your card number.',
    category: 'SAFE',
  },
  {
    label: '🛒 Legitimate Inquirer',
    text: 'Hello, I saw your advertisement on OLX regarding the sofa set. Is it still available for inspection this weekend?',
    category: 'SAFE',
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
  };

  return (
    <div className="glass-card p-6 border border-[#292F3C] space-y-5 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#292F3C]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-[#11141C] border border-[#292F3C]">
            <Sparkles className="w-4 h-4 text-[#8B7CFF]" />
          </div>
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#F1F3F8]">
              Text Transcript & RAG Evaluator
            </h3>
            <p className="text-xs text-[#A2A9BA]">
              Evaluate suspicious call transcripts against rule engines and the 2,841-document vector index
            </p>
          </div>
        </div>
      </div>

      {/* Input Textarea Area */}
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste or type an utterance or call transcript here to test detection..."
          className="glass-input w-full p-4 pr-14 min-h-[120px] resize-none text-xs text-[#F1F3F8] leading-relaxed"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              handleSubmit();
            }
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || isProcessing}
          className="btn-primary absolute bottom-3.5 right-3.5 p-2.5 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center shadow-md"
          title="Analyze Transcript (Ctrl + Enter)"
        >
          {isProcessing ? (
            <RefreshCw className="w-4 h-4 text-white animate-spin" />
          ) : (
            <Send className="w-4 h-4 text-white" />
          )}
        </button>
      </div>

      {/* Quick Benchmark Scenarios */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#70798C]">
            Select Benchmark Fraud Patterns:
          </span>
          <span className="text-[10px] text-[#A2A9BA] font-mono">
            Ctrl + Enter to evaluate
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {DEMO_SCENARIOS.map((scenario, i) => (
            <button
              key={i}
              onClick={() => {
                setText(scenario.text);
              }}
              className="p-2.5 rounded-xl bg-[#11141C] hover:bg-[#171B26] text-left border border-[#292F3C] hover:border-[#8B7CFF]/40 transition group"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-[#F1F3F8] group-hover:text-[#8B7CFF] transition-colors">
                  {scenario.label}
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-[#171B26] text-[#A2A9BA] border border-[#292F3C]">
                  {scenario.category}
                </span>
              </div>
              <p className="text-[11px] text-[#A2A9BA] line-clamp-2 leading-relaxed">
                {scenario.text}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
