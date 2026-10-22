import { useState, useEffect } from 'react';
import { Activity, Server, Wifi, WifiOff } from 'lucide-react';

interface HealthStatus {
  status: string;
  version: string;
  sarvam_configured: boolean;
}

export default function StatusBar() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch('/health', { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
          setIsOnline(true);
        } else {
          setIsOnline(false);
        }
      } catch {
        setIsOnline(false);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass px-4 py-2 flex items-center justify-between text-xs gap-4 flex-wrap">
      <div className="flex items-center gap-4">
        {/* Backend status */}
        <div className="flex items-center gap-1.5">
          {isOnline ? (
            <Wifi className="w-3.5 h-3.5 text-[var(--green-accent)]" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-[var(--red-alert)]" />
          )}
          <span className={isOnline ? 'text-[var(--green-accent)]' : 'text-[var(--red-alert)]'}>
            {isOnline ? 'Backend Connected' : 'Backend Offline'}
          </span>
        </div>

        {/* Sarvam status */}
        {health && (
          <div className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-[var(--text-muted)]" />
            <span className={health.sarvam_configured ? 'text-[var(--green-accent)]' : 'text-[var(--amber-warn)]'}>
              Sarvam: {health.sarvam_configured ? 'Active' : 'Demo Mode'}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
        <Activity className="w-3.5 h-3.5" />
        <span>v{health?.version || '1.0.0'}</span>
      </div>
    </div>
  );
}
