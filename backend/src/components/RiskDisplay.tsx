import { Shield, Mic, MicOff, AlertTriangle, CheckCircle, XCircle, Info } from 'lucide-react';
import type { RiskAssessment } from '../hooks/useLiveDetection';

interface RiskDisplayProps {
  assessment: RiskAssessment | null;
  isListening: boolean;
}

export default function RiskDisplay({ assessment, isListening }: RiskDisplayProps) {
  if (!assessment) {
    return (
      <div className="glass-card p-6 md:p-8 text-center animate-fade-in">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <Shield className="w-16 h-16 text-[var(--purple-bright)] animate-breathe" />
            <div className="absolute -inset-3 rounded-full bg-[var(--purple-glow)] opacity-10 animate-breathe" />
          </div>
          <h3 className="text-xl font-semibold text-[var(--text-primary)]">
            {isListening ? 'Listening & Monitoring...' : 'Ready to Protect'}
          </h3>
          <p className="text-[var(--text-muted)] max-w-md">
            {isListening
              ? 'Analyzing speech patterns in real-time. The shield will alert you if any suspicious patterns are detected.'
              : 'Start listening or paste a transcript to analyze for potential scam patterns.'}
          </p>
        </div>
      </div>
    );
  }

  const { risk_level, risk_score, caption, reasons, recommended_action, confidence, evidence, rule_analysis, contextual_analysis } = assessment;

  const levelConfig = {
    LOW: {
      icon: <CheckCircle className="w-8 h-8" />,
      color: 'var(--green-accent)',
      bgGlow: 'rgba(52, 211, 153, 0.08)',
      border: 'rgba(52, 211, 153, 0.25)',
      label: 'SAFE',
      gradient: 'from-emerald-500/20 to-green-500/10',
    },
    MEDIUM: {
      icon: <AlertTriangle className="w-8 h-8" />,
      color: 'var(--amber-warn)',
      bgGlow: 'rgba(251, 191, 36, 0.08)',
      border: 'rgba(251, 191, 36, 0.25)',
      label: 'CAUTION',
      gradient: 'from-amber-500/20 to-yellow-500/10',
    },
    HIGH: {
      icon: <XCircle className="w-8 h-8" />,
      color: 'var(--red-alert)',
      bgGlow: 'rgba(248, 113, 113, 0.08)',
      border: 'rgba(248, 113, 113, 0.25)',
      label: 'DANGER',
      gradient: 'from-red-500/20 to-rose-500/10',
    },
    CRITICAL: {
      icon: <XCircle className="w-8 h-8 text-rose-500 animate-pulse" />,
      color: '#ff2d55',
      bgGlow: 'rgba(255, 45, 85, 0.16)',
      border: 'rgba(255, 45, 85, 0.45)',
      label: 'CRITICAL',
      gradient: 'from-rose-600/30 to-red-600/20',
    },
    UNKNOWN: {
      icon: <Info className="w-8 h-8" />,
      color: 'var(--text-muted)',
      bgGlow: 'rgba(139, 122, 173, 0.08)',
      border: 'rgba(139, 122, 173, 0.25)',
      label: 'UNKNOWN',
      gradient: 'from-gray-500/20 to-slate-500/10',
    },
  };

  const config = levelConfig[risk_level] || levelConfig.UNKNOWN;
  const scorePercent = Math.round(risk_score > 1 ? risk_score : risk_score * 100);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Main Risk Card */}
      <div
        className="glass-card p-6 md:p-8 relative overflow-hidden"
        style={{ borderColor: config.border }}
      >
        {/* Background glow */}
        <div
          className="absolute inset-0 opacity-30 pointer-events-none"
          style={{
            background: `radial-gradient(circle at 50% 0%, ${config.bgGlow}, transparent 70%)`,
          }}
        />

        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div style={{ color: config.color }}>{config.icon}</div>
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className="text-sm font-bold tracking-widest"
                    style={{ color: config.color }}
                  >
                    {config.label}
                  </span>
                  {(risk_level === 'HIGH' || risk_level === 'CRITICAL') && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                      {risk_level === 'CRITICAL' ? '🚨 CRITICAL SCAM DETECTED' : '⚠ SCAM DETECTED'}
                    </span>
                  )}
                </div>
                <p className="text-[var(--text-primary)] font-semibold mt-1">{caption}</p>
              </div>
            </div>

            {/* Risk Score Circle */}
            <div className="relative w-20 h-20 flex-shrink-0">
              <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="35" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                <circle
                  cx="40" cy="40" r="35"
                  fill="none"
                  stroke={config.color}
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 35}`}
                  strokeDashoffset={`${2 * Math.PI * 35 * (1 - (scorePercent / 100))}`}
                  style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold" style={{ color: config.color }}>{scorePercent}</span>
                <span className="text-[10px] text-[var(--text-muted)]">/ 100</span>
              </div>
            </div>
          </div>

          {/* Confidence Bar */}
          {confidence !== null && (
            <div className="mb-4">
              <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1">
                <span>Analysis Confidence</span>
                <span>{Math.round(confidence * 100)}%</span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: `${confidence * 100}%`,
                    background: `linear-gradient(90deg, ${config.color}, var(--purple-glow))`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Recommended Action */}
          <div className="glass p-4 mb-4" style={{ borderColor: config.border }}>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              <span className="text-[var(--purple-bright)] font-semibold">Recommended: </span>
              {recommended_action}
            </p>
          </div>

          {/* Reasons */}
          {reasons.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-[var(--text-secondary)]">Analysis Details</h4>
              {reasons.slice(0, 5).map((reason, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: config.color }} />
                  <span className="text-[var(--text-muted)]">{reason}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Triggered Indicators */}
      {rule_analysis.triggered_indicators.length > 0 && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-[var(--red-alert)] mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Triggered Indicators ({rule_analysis.triggered_indicators.length})
          </h4>
          <div className="grid gap-2">
            {rule_analysis.triggered_indicators.map((ind, i) => (
              <div key={i} className="glass p-3 text-sm border-red-500/10">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                    {ind.category}
                  </span>
                  <span className="text-xs text-[var(--text-muted)]">
                    Weight: {Math.round(ind.weight * 100)}%
                  </span>
                </div>
                <p className="text-[var(--text-secondary)] mt-1">{ind.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suppressed Protective Matches */}
      {rule_analysis.suppressed_protective_matches.length > 0 && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-[var(--green-accent)] mb-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            Protective Advice Detected
          </h4>
          {rule_analysis.suppressed_protective_matches.map((match, i) => (
            <div key={i} className="text-sm text-[var(--text-muted)] flex items-center gap-2 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--green-accent)] flex-shrink-0" />
              {match}
            </div>
          ))}
        </div>
      )}

      {/* Contextual AI Insights */}
      {contextual_analysis.caller_identity_claim && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-[var(--purple-bright)] mb-3">
            Contextual Intelligence
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div className="glass p-3">
              <span className="text-[var(--text-muted)] text-xs">Claimed Identity</span>
              <p className="text-[var(--text-primary)] font-medium">{contextual_analysis.caller_identity_claim}</p>
            </div>
            {contextual_analysis.claimed_organisation && (
              <div className="glass p-3">
                <span className="text-[var(--text-muted)] text-xs">Claimed Organization</span>
                <p className="text-[var(--text-primary)] font-medium">{contextual_analysis.claimed_organisation}</p>
              </div>
            )}
            <div className="glass p-3">
              <span className="text-[var(--text-muted)] text-xs">Intent</span>
              <p className="font-mono text-xs" style={{ color: config.color }}>
                {contextual_analysis.intent_classification}
              </p>
            </div>
            {contextual_analysis.possible_impersonation && (
              <div className="glass p-3 border-red-500/20">
                <span className="text-[var(--text-muted)] text-xs">Impersonation</span>
                <p className="text-[var(--red-alert)] font-medium">⚠ Possible Impersonation</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
