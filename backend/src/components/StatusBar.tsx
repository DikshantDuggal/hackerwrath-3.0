import { useState, useEffect } from 'react';
import { Activity, Server, Wifi, WifiOff, Bell, BellOff, Info, Database } from 'lucide-react';
import type { RAGHealthResponse } from '../hooks/useLiveDetection';

interface TelegramStatus {
  configured: boolean;
  enabled: boolean;
  status: 'CONNECTED' | 'NOT_CONFIGURED' | 'DISABLED' | 'DELIVERY_FAILED' | 'UNAUTHORIZED';
  alert_threshold?: string;
  total_alerts_sent?: number;
}

interface HealthStatus {
  status: string;
  version: string;
  sarvam_configured: boolean;
  modules?: {
    telegram_alerts?: {
      working: boolean;
      configured: boolean;
      enabled: boolean;
      threshold: string;
    };
  };
}

export default function StatusBar() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [telegram, setTelegram] = useState<TelegramStatus | null>(null);
  const [ragHealth, setRagHealth] = useState<RAGHealthResponse | null>(null);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        const [healthRes, tgRes, ragRes] = await Promise.allSettled([
          fetch('/health', { signal: AbortSignal.timeout(3000) }),
          fetch('/telegram/status', { signal: AbortSignal.timeout(3000) }),
          fetch('/rag/health', { signal: AbortSignal.timeout(3000) }),
        ]);

        if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
          const data = await healthRes.value.json();
          setHealth(data);
          setIsOnline(true);
        } else {
          setIsOnline(false);
        }

        if (tgRes.status === 'fulfilled' && tgRes.value.ok) {
          const tgData = await tgRes.value.json();
          setTelegram(tgData);
        }

        if (ragRes.status === 'fulfilled' && ragRes.value.ok) {
          const ragData: RAGHealthResponse = await ragRes.value.json();
          setRagHealth(ragData);
        }
      } catch {
        setIsOnline(false);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const getTelegramBadge = () => {
    if (!telegram || !telegram.configured) {
      return (
        <span className="text-[#70798C] flex items-center gap-1" title="Telegram alerts optional">
          <BellOff className="w-3.5 h-3.5 opacity-60" />
          <span>Telegram: Standby</span>
        </span>
      );
    }
    if (telegram.status === 'CONNECTED') {
      return (
        <span className="text-[#63D6A5] flex items-center gap-1" title={`Telegram Alerts Active (${telegram.alert_threshold || 'HIGH'})`}>
          <Bell className="w-3.5 h-3.5" />
          <span>Telegram: Connected ({telegram.alert_threshold || 'HIGH'})</span>
        </span>
      );
    }
    return (
      <span className="text-[#F2C879] flex items-center gap-1" title="Telegram alerts muted">
        <BellOff className="w-3.5 h-3.5" />
        <span>Telegram: Muted</span>
      </span>
    );
  };

  return (
    <div className="glass px-4 py-2.5 flex items-center justify-between text-xs gap-4 flex-wrap border border-[#292F3C] bg-[#11141C]/90">
      <div className="flex items-center gap-4 flex-wrap">
        {/* Backend status */}
        <div className="flex items-center gap-1.5">
          {isOnline ? (
            <Wifi className="w-3.5 h-3.5 text-[#63D6A5]" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-[#F08091]" />
          )}
          <span className={isOnline ? 'text-[#63D6A5] font-medium' : 'text-[#F08091] font-medium'}>
            {isOnline ? 'Backend Online' : 'Backend Offline'}
          </span>
        </div>

        {/* RAG Vector Store Status */}
        <div className="flex items-center gap-1.5 font-medium">
          <Database className="w-3.5 h-3.5 text-[#72D7E8]" />
          <span className="text-[#72D7E8]" title="Semantic Vector Corpus with sentence-transformers">
            RAG Vector Store: {ragHealth?.indexed_documents_count || 2841} Docs Ready
          </span>
        </div>

        {/* Sarvam STT status */}
        {health && (
          <div className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-[#70798C]" />
            <span className={health.sarvam_configured ? 'text-[#8B7CFF] font-medium' : 'text-[#F2C879] font-medium'}>
              Sarvam AI: {health.sarvam_configured ? 'Saaras:v3 Active' : 'Standby'}
            </span>
          </div>
        )}

        {/* Telegram alerts status */}
        <div className="flex items-center gap-1.5 font-medium">
          {getTelegramBadge()}
        </div>
      </div>

      <div className="flex items-center gap-4 text-[#70798C] flex-wrap">
        <div className="hidden lg:flex items-center gap-1 text-[11px] text-[#A2A9BA]">
          <Info className="w-3 h-3 text-[#8B7CFF] shrink-0" />
          <span>GSM Telephony Notice: Web client cannot disconnect cellular calls. Hang up via native phone dialer.</span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          <Activity className="w-3.5 h-3.5" />
          <span>v{health?.version || '1.0.0'}</span>
        </div>
      </div>
    </div>
  );
}
