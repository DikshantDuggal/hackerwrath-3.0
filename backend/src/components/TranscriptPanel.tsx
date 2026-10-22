import { useRef, useEffect } from 'react';
import { Clock, User } from 'lucide-react';
import type { TranscriptSegment } from '../hooks/useLiveDetection';

interface TranscriptPanelProps {
  segments: TranscriptSegment[];
  isListening: boolean;
}

export default function TranscriptPanel({ segments, isListening }: TranscriptPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [segments]);

  return (
    <div className="glass-card p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--purple-bright)]" />
          Live Transcript
        </h3>
        {isListening && (
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--green-accent)] animate-pulse" />
            <span className="text-xs text-[var(--green-accent)]">Recording</span>
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-[200px] max-h-[400px]"
      >
        {segments.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-12 h-12 rounded-xl bg-[var(--purple-dim)]/20 flex items-center justify-center mb-3">
              <User className="w-6 h-6 text-[var(--purple-bright)]" />
            </div>
            <p className="text-[var(--text-muted)] text-sm">
              {isListening ? 'Waiting for speech...' : 'No transcript yet'}
            </p>
          </div>
        ) : (
          segments.map((seg, i) => (
            <div
              key={i}
              className="glass p-3 animate-slide-up"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-[var(--purple-dim)]/20 text-[var(--purple-bright)] border border-[var(--purple-dim)]/20">
                  {seg.speaker === 'text_input' ? '📝 Text' : `🎤 ${seg.speaker}`}
                </span>
                <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                  <Clock className="w-3 h-3" />
                  {new Date(seg.timestamp).toLocaleTimeString()}
                </div>
              </div>
              <p className="text-sm text-[var(--text-primary)] leading-relaxed">{seg.text}</p>
              <div className="mt-1.5 flex items-center gap-1">
                <span className="text-[10px] text-[var(--text-muted)]">Confidence:</span>
                <div className="flex-1 h-1 bg-white/5 rounded-full max-w-[80px]">
                  <div
                    className="h-full rounded-full bg-[var(--green-accent)]"
                    style={{ width: `${seg.confidence * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-[var(--text-muted)]">
                  {Math.round(seg.confidence * 100)}%
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
