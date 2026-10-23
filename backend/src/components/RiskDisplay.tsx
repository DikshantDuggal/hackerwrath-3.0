import { useState } from 'react';
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Database,
  Search,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react';
import type { RiskAssessment, RetrievedExample } from '../hooks/useLiveDetection';

interface RiskDisplayProps {
  assessment: RiskAssessment | null;
  isListening: boolean;
}

export default function RiskDisplay({ assessment, isListening }: RiskDisplayProps) {
  const [showAllRagExamples, setShowAllRagExamples] = useState(false);

  if (!assessment) {
    return (
      <div className="glass-card p-6 md:p-8 text-center animate-fade-in border border-[#292F3C]">
        <div className="flex flex-col items-center gap-4 py-6">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-[#171B26] border border-[#292F3C] flex items-center justify-center shadow-lg">
              <Shield className="w-8 h-8 text-[#8B7CFF]" />
            </div>
            <div className="absolute -inset-2 rounded-2xl bg-[#8B7CFF] opacity-15 blur-md" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[#F1F3F8]">
              {isListening ? 'Active Call Interceptor Online' : 'Ready for Audio or Text Input'}
            </h3>
            <p className="text-xs text-[#A2A9BA] max-w-sm mt-1.5 leading-relaxed mx-auto">
              {isListening
                ? 'Continuously monitoring dual-channel speech streams against 2,841 indexed scam cases and real-time rule signatures.'
                : 'Speak into the microphone, simulate an incoming call, or paste text to perform live RAG and rule analysis.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const {
    risk_level = 'LOW',
    risk_score = 0,
    caption = 'Monitoring conversation',
    reasons = [],
    recommended_action = 'Continue with normal caution',
    confidence = 0.9,
    rule_analysis = { rule_score: 0, triggered_indicators: [], suppressed_protective_matches: [] },
    contextual_analysis = {} as any,
    rag_classification = null,
  } = assessment;

  const safeReasons = Array.isArray(reasons) ? reasons : [];
  const safeTriggered = Array.isArray(rule_analysis?.triggered_indicators)
    ? rule_analysis.triggered_indicators
    : [];
  const safeSuppressed = Array.isArray(rule_analysis?.suppressed_protective_matches)
    ? rule_analysis.suppressed_protective_matches
    : [];
  const retrievedExamples: RetrievedExample[] = rag_classification?.retrieved_examples || [];

  const levelConfig = {
    LOW: {
      icon: <CheckCircle className="w-7 h-7 text-[#63D6A5]" />,
      color: '#63D6A5',
      badgeBg: 'bg-[#63D6A5]/15 text-[#63D6A5] border-[#63D6A5]/30',
      label: 'SAFE',
    },
    MEDIUM: {
      icon: <AlertTriangle className="w-7 h-7 text-[#F2C879]" />,
      color: '#F2C879',
      badgeBg: 'bg-[#F2C879]/15 text-[#F2C879] border-[#F2C879]/30',
      label: 'CAUTION',
    },
    HIGH: {
      icon: <XCircle className="w-7 h-7 text-[#F08091]" />,
      color: '#F08091',
      badgeBg: 'bg-[#F08091]/15 text-[#F08091] border-[#F08091]/30',
      label: 'DANGER',
    },
    CRITICAL: {
      icon: <XCircle className="w-7 h-7 text-[#F08091] animate-pulse" />,
      color: '#F08091',
      badgeBg: 'bg-[#F08091]/20 text-[#F08091] border-[#F08091]/50',
      label: 'CRITICAL FRAUD',
    },
    UNKNOWN: {
      icon: <Info className="w-7 h-7 text-[#A2A9BA]" />,
      color: '#A2A9BA',
      badgeBg: 'bg-[#A2A9BA]/15 text-[#A2A9BA] border-[#A2A9BA]/30',
      label: 'EVALUATING',
    },
  };

  const config = levelConfig[risk_level] || levelConfig.UNKNOWN;
  const scorePercent = Math.round(risk_score > 1 ? risk_score : risk_score * 100);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Primary Assessment Card */}
      <div className="glass-card p-6 border border-[#292F3C] space-y-5">
        {/* Top Header Row */}
        <div className="flex items-center justify-between gap-4 pb-4 border-b border-[#292F3C]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-[#11141C] border border-[#292F3C] shrink-0">
              {config.icon}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${config.badgeBg}`}>
                  {config.label}
                </span>
                <span className="text-xs text-[#70798C] font-mono">
                  Confidence: {Math.round((confidence || 0.9) * 100)}%
                </span>
              </div>
              <h3 className="text-base font-bold text-[#F1F3F8] mt-1 leading-snug">
                {caption}
              </h3>
            </div>
          </div>

          {/* Radial Score Gauge */}
          <div className="relative w-16 h-16 shrink-0">
            <svg className="w-16 h-16 -rotate-90" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(41, 47, 60, 0.6)" strokeWidth="6" />
              <circle
                cx="40"
                cy="40"
                r="34"
                fill="none"
                stroke={config.color}
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 34}`}
                strokeDashoffset={`${2 * Math.PI * 34 * (1 - scorePercent / 100)}`}
                style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-sm font-bold font-mono" style={{ color: config.color }}>
                {scorePercent}
              </span>
              <span className="text-[9px] text-[#70798C]">/100</span>
            </div>
          </div>
        </div>

        {/* Recommended Immediate Action */}
        <div className="p-3.5 rounded-xl bg-[#11141C] border border-[#292F3C] flex items-start gap-2.5">
          <Shield className="w-4 h-4 text-[#8B7CFF] shrink-0 mt-0.5" />
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#8B7CFF] block mb-0.5">
              Defensive Recommendation
            </span>
            <p className="text-xs text-[#F1F3F8] font-medium leading-relaxed">
              {recommended_action}
            </p>
          </div>
        </div>

        {/* Rationale Excerpts */}
        {safeReasons.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[#A2A9BA]">
              Behavioral Evaluation
            </h4>
            <div className="space-y-1">
              {safeReasons.slice(0, 3).map((reason, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-[#A2A9BA]">
                  <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: config.color }} />
                  <span>{reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* RAG GROUNDED SEMANTIC RETRIEVAL CARD */}
      {(retrievedExamples.length > 0 || rag_classification) && (
        <div className="glass-card p-5 border border-[#292F3C] space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-[#72D7E8]" />
              <h4 className="text-xs font-bold text-[#F1F3F8] uppercase tracking-wider">
                Grounded Vector Citations (RAG)
              </h4>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#72D7E8]/15 text-[#72D7E8] border border-[#72D7E8]/30">
              2,841 Indexed Corpus
            </span>
          </div>

          {rag_classification?.explanation && (
            <p className="text-xs text-[#A2A9BA] bg-[#11141C] p-2.5 rounded-xl border border-[#292F3C] leading-relaxed">
              <span className="font-semibold text-[#F1F3F8]">RAG Classification: </span>
              {rag_classification.explanation}
            </p>
          )}

          {/* Retrieved Semantic Reference Examples */}
          {retrievedExamples.length > 0 && (
            <div className="space-y-2 pt-1">
              <span className="text-[10px] text-[#70798C] uppercase tracking-wider block">
                Top Semantic Neighbor Dialogues:
              </span>
              {(showAllRagExamples ? retrievedExamples : retrievedExamples.slice(0, 2)).map((ex, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-[#11141C] border border-[#292F3C] space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[9px] font-bold font-mono px-2 py-0.5 rounded-full border ${
                        ex.label === 'SCAM'
                          ? 'bg-[#F08091]/15 text-[#F08091] border-[#F08091]/30'
                          : 'bg-[#63D6A5]/15 text-[#63D6A5] border-[#63D6A5]/30'
                      }`}
                    >
                      {ex.label}
                    </span>
                    <span className="text-[10px] text-[#72D7E8] font-mono">
                      Cosine Sim: {(ex.similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-[#A2A9BA] text-[11px] leading-relaxed line-clamp-3 italic">
                    "{ex.text}"
                  </p>
                </div>
              ))}

              {retrievedExamples.length > 2 && (
                <button
                  onClick={() => setShowAllRagExamples(!showAllRagExamples)}
                  className="w-full py-1 text-[11px] text-[#8B7CFF] hover:underline flex items-center justify-center gap-1"
                >
                  {showAllRagExamples ? (
                    <>
                      <span>Show Less</span>
                      <ChevronUp className="w-3 h-3" />
                    </>
                  ) : (
                    <>
                      <span>View All {retrievedExamples.length} Citations</span>
                      <ChevronDown className="w-3 h-3" />
                    </>
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Triggered Rule Indicators */}
      {safeTriggered.length > 0 && (
        <div className="glass-card p-5 border border-[#292F3C] space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-[#F08091] uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Triggered Rule Indicators ({safeTriggered.length})</span>
            </h4>
          </div>
          <div className="grid gap-2">
            {safeTriggered.map((ind, i) => (
              <div key={i} className="p-2.5 rounded-xl bg-[#11141C] border border-[#292F3C] text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-[#F08091]/15 text-[#F08091] border border-[#F08091]/30">
                    {ind.category}
                  </span>
                  <span className="text-[10px] text-[#70798C] font-mono">
                    Weight: {Math.round(ind.weight > 1.0 ? ind.weight : ind.weight * 100)}%
                  </span>
                </div>
                <p className="text-[#A2A9BA] text-[11px] mt-1">{ind.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suppressed Protective Matches */}
      {safeSuppressed.length > 0 && (
        <div className="glass-card p-4 border border-[#292F3C]">
          <h4 className="text-xs font-bold text-[#63D6A5] uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Protective Negation Suppressed</span>
          </h4>
          <div className="space-y-1">
            {safeSuppressed.map((match, i) => (
              <div key={i} className="text-xs text-[#A2A9BA] flex items-center gap-2 py-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#63D6A5] shrink-0" />
                <span>{match}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
