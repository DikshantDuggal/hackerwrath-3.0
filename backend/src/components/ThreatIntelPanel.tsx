import { useState, useEffect } from 'react';
import { Database, RefreshCw, Plus, ShieldAlert, Cpu, Sparkles } from 'lucide-react';

interface SyncedKeyword {
  keyword: string;
  category: string;
  weight: number;
  hit_count: number;
  active: boolean;
}

export default function ThreatIntelPanel() {
  const [keywords, setKeywords] = useState<SyncedKeyword[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newCategory, setNewCategory] = useState('OTP_OR_PIN_REQUEST');
  const [newWeight, setNewWeight] = useState(0.45);
  const [msg, setMsg] = useState<string | null>(null);

  const fetchKeywords = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/sync/keywords');
      if (res.ok) {
        const data = await res.json();
        setKeywords(data.keywords || []);
      }
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKeywords();
  }, []);

  const handleAddKeyword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;

    try {
      const res = await fetch('/sync/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: newKeyword.trim().toLowerCase(),
          category: newCategory,
          weight: newWeight,
          source_call_id: 'admin_dashboard',
        }),
      });

      if (res.ok) {
        setMsg(`✅ Synced keyword "${newKeyword}" across all active calls.`);
        setNewKeyword('');
        fetchKeywords();
        setTimeout(() => setMsg(null), 3000);
      }
    } catch (e: any) {
      setMsg(`❌ Error: ${e.message}`);
    }
  };

  return (
    <div className="glass-card p-6 md:p-8 space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-[var(--purple-bright)]" />
            <h2 className="text-lg font-bold text-white">Cross-Call Threat Intelligence</h2>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Real-time scam pattern database synced across all active call streams
          </p>
        </div>

        <button
          onClick={fetchKeywords}
          disabled={isLoading}
          className="glass px-3.5 py-1.5 rounded-xl text-xs flex items-center gap-2 text-white hover:bg-white/10 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Signatures
        </button>
      </div>

      {/* Sync form */}
      <form onSubmit={handleAddKeyword} className="glass p-4 rounded-2xl space-y-3">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider flex items-center gap-1.5">
          <Plus className="w-3.5 h-3.5 text-[var(--green-accent)]" />
          Register New Scam Signature
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            placeholder="e.g., army gate pass fee, digital arrest warrant"
            className="sm:col-span-6 glass-input px-3.5 py-2 text-xs"
          />

          <select
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            className="sm:col-span-4 glass-input px-3 py-2 text-xs bg-black/40"
          >
            <option value="OTP_OR_PIN_REQUEST">OTP / PIN Solicitation</option>
            <option value="QR_SCAN_TO_RECEIVE_MONEY">QR Scan to Receive Lure</option>
            <option value="REMOTE_ACCESS_OR_SCREEN_SHARE">AnyDesk / Screen Share</option>
            <option value="THREAT_ARREST_OR_LEGAL_ACTION">Digital Arrest / CBI Warrant</option>
            <option value="ACCOUNT_SUSPENSION_THREAT">Account Freeze / KYC</option>
            <option value="AUTHORITY_OR_BANK_IMPERSONATION">Authority Impersonation</option>
            <option value="URGENT_PAYMENT_DEMAND">Urgent Payment Demand</option>
          </select>

          <button
            type="submit"
            className="sm:col-span-2 btn-primary py-2 text-xs rounded-xl flex items-center justify-center gap-1 font-semibold"
          >
            Sync
          </button>
        </div>

        {msg && <p className="text-xs font-mono text-[var(--purple-bright)] mt-1">{msg}</p>}
      </form>

      {/* Synchronized Keywords List */}
      <div>
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
          Active Signatures ({keywords.length})
        </h3>

        {keywords.length === 0 ? (
          <div className="glass p-8 text-center rounded-2xl text-xs text-[var(--text-muted)]">
            <Cpu className="w-8 h-8 mx-auto mb-2 text-[var(--purple-bright)] opacity-50" />
            <p>No custom cross-call signatures registered yet.</p>
            <p className="mt-1 text-[11px]">
              Built-in rules are actively protecting all calls against the 8 primary fraud categories.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {keywords.map((kw, i) => (
              <div key={i} className="glass p-3.5 rounded-xl border-white/5 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-medium text-white line-clamp-1">{kw.keyword}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">
                    Hits: {kw.hit_count}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                  <span>{kw.category}</span>
                  <span>Weight: {Math.round(kw.weight * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
