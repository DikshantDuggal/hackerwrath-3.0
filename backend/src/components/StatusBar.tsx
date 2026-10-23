import { useState, useEffect } from 'react';
import { Activity, Server, Wifi, WifiOff, Bell, BellOff, Info } from 'lucide-react';

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
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        const [healthRes, tgRes] = await Promise.allSettled([
          fetch('/health', { signal: AbortSignal.timeout(3000) }),
          fetch('/telegram/status', { signal: AbortSignal.timeout(3000) }),
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
        <span className="text-[var(--text-muted)] flex items-center gap-1" title="Telegram alerts optional and unconfigured">
          <BellOff className="w-3.5 h-3.5 opacity-60" />
          <span>Telegram: Optional</span>
        </span>
      );
    }
    if (telegram.status === 'CONNECTED') {
      return (
        <span className="text-[var(--green-accent)] flex items-center gap-1" title={`Telegram Bot Alerts Active (Threshold: ${telegram.alert_threshold || 'HIGH'})`}>
          <Bell className="w-3.5 h-3.5" />
          <span>Telegram: Connected ({telegram.alert_threshold || 'HIGH'})</span>
        </span>
      );
    }
    if (telegram.status === 'UNAUTHORIZED' || telegram.status === 'DELIVERY_FAILED') {
      return (
        <span className="text-[var(--red-alert)] flex items-center gap-1" title={`Telegram Error: ${telegram.status}`}>
          <BellOff className="w-3.5 h-3.5" />
          <span>Telegram: Error</span>
        </span>
      );
    }
    return (
      <span className="text-[var(--amber-warn)] flex items-center gap-1" title="Telegram alerts disabled/muted">
        <BellOff className="w-3.5 h-3.5" />
        <span>Telegram: Muted</span>
      </span>
    );
  };

  return (
    <div className="glass px-4 py-2 flex items-center justify-between text-xs gap-4 flex-wrap">
      <div className="flex items-center gap-4 flex-wrap">
        {/* Backend status */}
        <div className="flex items-center gap-1.5">
          {isOnline ? (
            <Wifi className="w-3.5 h-3.5 text-[var(--green-accent)]" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-[var(--red-alert)]" />
          )}
          <span className={isOnline ? 'text-[var(--green-accent)] font-medium' : 'text-[var(--red-alert)] font-medium'}>
            {isOnline ? 'Backend Connected' : 'Backend Offline'}
          </span>
        </div>

        {/* Sarvam status */}
        {health && (
          <div className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-[var(--text-muted)]" />
            <span className={health.sarvam_configured ? 'text-[var(--green-accent)] font-medium' : 'text-[var(--amber-warn)] font-medium'}>
              Sarvam: {health.sarvam_configured ? 'Active' : 'Demo Mode'}
            </span>
          </div>
        )}

        {/* Telegram alerts status */}
        <div className="flex items-center gap-1.5 font-medium">
          {getTelegramBadge()}
        </div>
      </div>

      <div className="flex items-center gap-4 text-[var(--text-muted)] flex-wrap">
        <div className="hidden md:flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
          <Info className="w-3 h-3 text-[var(--purple-bright)] flex-shrink-0" />
          <span>Telephony Notice: Web & Telegram cannot disconnect cellular GSM calls. Hang up via dialer.</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5" />
          <span>v{health?.version || '1.0.0'}</span>
        </div>
      </div>
    </div>
  );
}
