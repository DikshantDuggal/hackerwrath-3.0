import { useState, useEffect, type FormEvent } from 'react';
import { RefreshCw } from 'lucide-react';
import { CHIP_FOR_CATEGORY } from '../spell/signals';

interface SyncedKeyword {
  keyword: string;
  category: string;
  weight: number;
  hit_count: number;
  active: boolean;
}

const CATEGORIES: Array<[string, string]> = [
  ['OTP_OR_PIN_REQUEST', 'OTP or PIN ask'],
  ['QR_SCAN_TO_RECEIVE_MONEY', 'QR scan to “receive” money'],
  ['REMOTE_ACCESS_OR_SCREEN_SHARE', 'Remote access or screen share'],
  ['THREAT_ARREST_OR_LEGAL_ACTION', 'Arrest or legal threat'],
  ['ACCOUNT_SUSPENSION_THREAT', 'Account block or KYC threat'],
  ['AUTHORITY_OR_BANK_IMPERSONATION', 'Bank or authority impersonation'],
  ['URGENT_PAYMENT_DEMAND', 'Urgent payment demand'],
];

export default function ThreatIntelPanel() {
  const [keywords, setKeywords] = useState<SyncedKeyword[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newCategory, setNewCategory] = useState('OTP_OR_PIN_REQUEST');
  const [newWeight] = useState(0.45);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

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

  const handleAddKeyword = async (e: FormEvent) => {
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
        setMsg({ ok: true, text: `“${newKeyword}” now applies to every live call.` });
        setNewKeyword('');
        fetchKeywords();
        setTimeout(() => setMsg(null), 3000);
      }
    } catch (e: any) {
      setMsg({ ok: false, text: `Couldn’t add it: ${e.message}` });
    }
  };

  return (
    <div className="sb-card p-5 sm:p-6 flex flex-col gap-6 sb-rise">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="sb-eyebrow">Threat intel</div>
          <h2 className="text-[26px] leading-8 font-extrabold text-head mt-1">Phrases every call listens for</h2>
          <p className="text-[13px] text-faint mt-1">A phrase added here reaches every live call at once.</p>
        </div>
        <button type="button" onClick={fetchKeywords} disabled={isLoading} className="sb-btn sb-btn-soft text-[14px] shrink-0">
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <form onSubmit={handleAddKeyword} className="sb-soft p-4 flex flex-col gap-3">
        <span className="text-[15px] font-extrabold text-head">Add a phrase</span>
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5">
          <label className="sm:col-span-6">
            <span className="sr-only">Phrase</span>
            <input
              type="text"
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder="e.g. army gate pass fee, digital arrest warrant"
              className="sb-input w-full px-3.5 py-2.5 text-[14px]"
            />
          </label>
          <label className="sm:col-span-4">
            <span className="sr-only">What kind of ask</span>
            <select value={newCategory} onChange={(e) => setNewCategory(e.target.value)} className="sb-input w-full px-3.5 py-2.5 text-[14px] font-semibold">
              {CATEGORIES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" className="sm:col-span-2 sb-btn sb-btn-primary">
            Add
          </button>
        </div>
        {msg && (
          <p className={`text-[13px] font-semibold ${msg.ok ? 'text-accent' : 'text-danger'}`} aria-live="polite">
            {msg.text}
          </p>
        )}
      </form>

      <div>
        <div className="sb-eyebrow mb-3">Added phrases · {keywords.length}</div>
        {keywords.length === 0 ? (
          <p className="sb-soft px-4 py-8 text-center text-[13px] text-faint">
            None added yet. The built-in rules already cover the main kinds of scam ask.
          </p>
        ) : (
          <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 list-none">
            {keywords.map((kw, i) => (
              <li key={i} className="rounded-[18px] border border-line px-4 py-3 flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[15px] font-extrabold text-head line-clamp-1">{kw.keyword}</span>
                  <span className="text-[12px] text-faint shrink-0">
                    {kw.hit_count} {kw.hit_count === 1 ? 'hit' : 'hits'}
                  </span>
                </div>
                <span className="sb-chip self-start text-[12px] px-2.5 py-1 bg-danger-soft text-danger-ink">
                  {CHIP_FOR_CATEGORY[String(kw.category).toUpperCase()] || kw.category}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
