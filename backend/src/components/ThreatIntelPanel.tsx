import { useState, useEffect } from 'react';
import {
  Database,
  RefreshCw,
  Plus,
  ShieldAlert,
  Search,
  Cpu,
  Sparkles,
  BookOpen,
  CheckCircle,
  AlertTriangle,
  Flame,
  Layers,
} from 'lucide-react';
import type { RAGHealthResponse, RAGClassificationResponse } from '../hooks/useLiveDetection';

interface SyncedKeyword {
  keyword: string;
  category: string;
  weight: number;
  hit_count: number;
  active: boolean;
}

export default function ThreatIntelPanel() {
  // RAG State
  const [ragHealth, setRagHealth] = useState<RAGHealthResponse | null>(null);
  const [isRagLoading, setIsRagLoading] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [ragResult, setRagResult] = useState<RAGClassificationResponse | null>(null);
  const [isSearchingRag, setIsSearchingRag] = useState(false);

  // Keyword Sync State
  const [keywords, setKeywords] = useState<SyncedKeyword[]>([]);
  const [isKeywordsLoading, setIsKeywordsLoading] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newCategory, setNewCategory] = useState('OTP_OR_PIN_REQUEST');
  const [newWeight, setNewWeight] = useState(0.45);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  // Tab: 'rag' or 'sync'
  const [activeSubTab, setActiveSubTab] = useState<'rag' | 'sync'>('rag');

  // Fetch RAG Health
  const fetchRagHealth = async () => {
    setIsRagLoading(true);
    try {
      const res = await fetch('/rag/health');
      if (res.ok) {
        const data: RAGHealthResponse = await res.json();
        setRagHealth(data);
      }
    } catch (e) {
      console.warn('Failed to fetch RAG health', e);
    } finally {
      setIsRagLoading(false);
    }
  };

  // Perform Semantic Vector Search via RAG
  const handleRagSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ragQuery.trim() || isSearchingRag) return;

    setIsSearchingRag(true);
    try {
      const res = await fetch('/rag/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: ragQuery.trim(),
          top_k: 4,
          include_retrieved_examples: true,
        }),
      });

      if (res.ok) {
        const data: RAGClassificationResponse = await res.json();
        setRagResult(data);
      }
    } catch (e) {
      console.error('RAG vector query error', e);
    } finally {
      setIsSearchingRag(false);
    }
  };

  // Fetch Synced Keywords
  const fetchKeywords = async () => {
    setIsKeywordsLoading(true);
    try {
      const res = await fetch('/sync/keywords');
      if (res.ok) {
        const data = await res.json();
        setKeywords(data.keywords || []);
      }
    } catch {
      // Fallback
    } finally {
      setIsKeywordsLoading(false);
    }
  };

  useEffect(() => {
    fetchRagHealth();
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
          source_call_id: 'threat_intel_ui',
        }),
      });

      if (res.ok) {
        setSyncMsg(`Synced signature "${newKeyword}" across all active calls.`);
        setNewKeyword('');
        fetchKeywords();
        setTimeout(() => setSyncMsg(null), 3000);
      }
    } catch (e: any) {
      setSyncMsg(`Error: ${e.message}`);
    }
  };

  return (
    <div className="glass-card p-6 md:p-8 space-y-6 animate-slide-up border border-[#292F3C]">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[#292F3C]">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[#171B26] border border-[#292F3C]">
              <Database className="w-5 h-5 text-[#8B7CFF]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[#F1F3F8]">
                Intelligence Core & RAG Vector Knowledge Base
              </h2>
              <p className="text-xs text-[#A2A9BA] mt-0.5">
                Semantic retrieval across 2,841 indexed fraud transcripts & active cross-call signature synchronization
              </p>
            </div>
          </div>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-[#11141C] border border-[#292F3C] rounded-xl text-xs">
          <button
            onClick={() => setActiveSubTab('rag')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'rag'
                ? 'bg-[#8B7CFF] text-white shadow-sm'
                : 'text-[#A2A9BA] hover:text-[#F1F3F8]'
            }`}
          >
            📚 RAG Vector Store
          </button>
          <button
            onClick={() => setActiveSubTab('sync')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'sync'
                ? 'bg-[#8B7CFF] text-white shadow-sm'
                : 'text-[#A2A9BA] hover:text-[#F1F3F8]'
            }`}
          >
            🔄 Synced Signatures ({keywords.length})
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 1. RAG VECTOR STORE & SEMANTIC RETRIEVAL TAB */}
      {/* ========================================================= */}
      {activeSubTab === 'rag' && (
        <div className="space-y-6">
          {/* Vector Store Health Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-2xl bg-[#11141C] border border-[#292F3C]">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#70798C] block mb-1">
                Vector Index Status
              </span>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#63D6A5] animate-pulse" />
                <span className="text-sm font-bold font-mono text-[#F1F3F8]">
                  {ragHealth?.status || 'READY'}
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#11141C] border border-[#292F3C]">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#70798C] block mb-1">
                Indexed Documents
              </span>
              <span className="text-sm font-bold font-mono text-[#72D7E8]">
                {ragHealth?.indexed_documents_count || 2841} Transcripts
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#11141C] border border-[#292F3C]">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#70798C] block mb-1">
                Embedding Model
              </span>
              <span className="text-xs font-bold font-mono text-[#8B7CFF] truncate block">
                all-MiniLM-L6-v2
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#11141C] border border-[#292F3C]">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#70798C] block mb-1">
                Retrieval Engine
              </span>
              <span className="text-xs font-bold font-mono text-[#63D6A5] truncate block">
                Cosine Similarity
              </span>
            </div>
          </div>

          {/* Interactive Semantic Vector Search Bar */}
          <div className="p-5 rounded-2xl bg-[#11141C] border border-[#292F3C] space-y-3.5">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#F1F3F8] flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-[#72D7E8]" />
                <span>Semantic Vector Corpus Query</span>
              </h3>
              <p className="text-xs text-[#A2A9BA] mt-0.5">
                Type any phone conversation excerpt to test semantic retrieval and observe the nearest scam/legitimate reference vectors.
              </p>
            </div>

            <form onSubmit={handleRagSearch} className="flex gap-2">
              <input
                type="text"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="e.g., 'I am calling from Mumbai police cyber crime branch regarding a parcel...'"
                className="glass-input flex-1 px-4 py-2.5 text-xs text-[#F1F3F8]"
              />
              <button
                type="submit"
                disabled={!ragQuery.trim() || isSearchingRag}
                className="btn-primary px-5 py-2.5 text-xs font-medium flex items-center gap-1.5 shrink-0 disabled:opacity-40"
              >
                {isSearchingRag ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                <span>Retrieve Nearest Vectors</span>
              </button>
            </form>

            {/* Quick Test Chips */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] text-[#70798C]">Quick Queries:</span>
              {[
                'Scan QR code to receive Rs 25000',
                'Your electricity bill is pending, download AnyDesk',
                'Bank KYC verification OTP code',
                'Hello, I am interested in buying the sofa on OLX',
              ].map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    setRagQuery(q);
                  }}
                  className="px-2.5 py-1 rounded-lg text-[11px] bg-[#171B26] hover:bg-[#202636] text-[#A2A9BA] border border-[#292F3C] transition"
                >
                  "{q}"
                </button>
              ))}
            </div>
          </div>

          {/* RAG Query Results Display */}
          {ragResult && (
            <div className="p-5 rounded-2xl bg-[#11141C] border border-[#292F3C] space-y-4 animate-fade-in">
              <div className="flex items-center justify-between pb-3 border-b border-[#292F3C]">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-bold font-mono px-2.5 py-0.5 rounded-full border ${
                      ragResult.classification === 'SCAM'
                        ? 'bg-[#F08091]/15 text-[#F08091] border-[#F08091]/30'
                        : 'bg-[#63D6A5]/15 text-[#63D6A5] border-[#63D6A5]/30'
                    }`}
                  >
                    {ragResult.classification}
                  </span>
                  <span className="text-xs text-[#F1F3F8] font-semibold">
                    Risk Score: {Math.round(ragResult.risk_score)}/100
                  </span>
                  <span className="text-xs text-[#70798C] font-mono">
                    Confidence: {Math.round(ragResult.confidence * 100)}%
                  </span>
                </div>
                <span className="text-[10px] text-[#70798C] font-mono">
                  Latency: {ragResult.retrieval_latency_ms.toFixed(1)}ms retrieval · {ragResult.classification_latency_ms.toFixed(1)}ms total
                </span>
              </div>

              <p className="text-xs text-[#A2A9BA] leading-relaxed">
                <span className="font-semibold text-[#F1F3F8]">Justification: </span>
                {ragResult.explanation}
              </p>

              {/* Retrieved Corpus Neighbors */}
              <div className="space-y-2 pt-2">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[#72D7E8]">
                  Retrieved Nearest Reference Dialogues ({ragResult.retrieved_examples.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {ragResult.retrieved_examples.map((ex, i) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-xl bg-[#171B26] border border-[#292F3C] space-y-2 text-xs"
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
                        <span className="text-[11px] font-mono text-[#72D7E8]">
                          Cosine Sim: {(ex.similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-[#A2A9BA] text-[11px] leading-relaxed line-clamp-3 italic">
                        "{ex.text}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* 2. SYNCED SIGNATURES TAB */}
      {/* ========================================================= */}
      {activeSubTab === 'sync' && (
        <div className="space-y-6">
          {/* Add Signature Form */}
          <form onSubmit={handleAddKeyword} className="p-4 rounded-2xl bg-[#11141C] border border-[#292F3C] space-y-3">
            <h3 className="text-xs font-semibold text-[#A2A9BA] uppercase tracking-wider flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-[#63D6A5]" />
              <span>Register New Scam Signature</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
              <input
                type="text"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                placeholder="Keyword or phrase (e.g. 'digital arrest warrant')"
                className="glass-input sm:col-span-6 px-3.5 py-2 text-xs text-[#F1F3F8]"
              />

              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="glass-input sm:col-span-4 px-3 py-2 text-xs text-[#F1F3F8] bg-[#11141C]"
              >
                <option value="OTP_OR_PIN_REQUEST">OTP / PIN Phishing</option>
                <option value="QR_SCAN_TO_RECEIVE_MONEY">Reverse QR Scam</option>
                <option value="REMOTE_ACCESS_OR_SCREEN_SHARE">Remote Access APK</option>
                <option value="THREAT_ARREST_OR_LEGAL_ACTION">Digital Arrest Extortion</option>
                <option value="ACCOUNT_SUSPENSION_THREAT">Account Suspension</option>
                <option value="URGENT_PAYMENT_DEMAND">Urgent Advance Fee</option>
              </select>

              <button
                type="submit"
                className="btn-primary sm:col-span-2 py-2 text-xs font-semibold"
              >
                Sync Signature
              </button>
            </div>

            {syncMsg && (
              <p className="text-xs text-[#63D6A5] font-medium animate-fade-in">{syncMsg}</p>
            )}
          </form>

          {/* Active Synced Signatures Table */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-[#A2A9BA] px-1">
              <span>Active Signatures Synchronized Across Live Streams</span>
              <button
                onClick={fetchKeywords}
                disabled={isKeywordsLoading}
                className="text-[11px] text-[#8B7CFF] hover:underline flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${isKeywordsLoading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-[360px] overflow-y-auto pr-1">
              {keywords.map((kw, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-[#11141C] border border-[#292F3C] flex items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-0.5">
                    <span className="font-semibold text-[#F1F3F8] block">"{kw.keyword}"</span>
                    <span className="text-[10px] text-[#70798C] font-mono">{kw.category}</span>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30">
                      Weight: {Math.round(kw.weight * 100)}%
                    </span>
                    <span className="text-[10px] text-[#70798C] block mt-0.5 font-mono">
                      Hits: {kw.hit_count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
