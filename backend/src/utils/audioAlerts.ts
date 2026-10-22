/**
 * Audio Alert Utility for Suraksha
 * Uses browser Web Audio API to synthesize alerts with zero external audio assets.
 */

class AudioAlertSystem {
  private ctx: AudioContext | null = null;
  private isMuted: boolean = false;

  private getContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
    return this.ctx;
  }

  public setMuted(muted: boolean): void {
    this.isMuted = muted;
  }

  public getIsMuted(): boolean {
    return this.isMuted;
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    return this.isMuted;
  }

  /**
   * Urgent high-pitch double pulse for HIGH scam risk
   */
  public playHighRiskAlert(): void {
    if (this.isMuted) return;
    const ctx = this.getContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    
    // First beep
    this.createTone(ctx, 880, now, 0.12, 'sawtooth', 0.25);
    this.createTone(ctx, 440, now, 0.12, 'sine', 0.2);

    // Second beep slightly higher
    this.createTone(ctx, 1100, now + 0.16, 0.18, 'sawtooth', 0.3);
    this.createTone(ctx, 550, now + 0.16, 0.18, 'sine', 0.25);
  }

  /**
   * Subtle alert chime for MEDIUM caution
   */
  public playCautionAlert(): void {
    if (this.isMuted) return;
    const ctx = this.getContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    this.createTone(ctx, 523.25, now, 0.15, 'triangle', 0.18); // C5
    this.createTone(ctx, 659.25, now + 0.12, 0.2, 'sine', 0.15); // E5
  }

  /**
   * Harmonious chime for SAFE / Low risk confirmation
   */
  public playSafeChime(): void {
    if (this.isMuted) return;
    const ctx = this.getContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    this.createTone(ctx, 587.33, now, 0.18, 'sine', 0.12); // D5
    this.createTone(ctx, 880.00, now + 0.12, 0.25, 'sine', 0.1); // A5
  }

  /**
   * Haptic tick when toggling mic or actions
   */
  public playClick(): void {
    if (this.isMuted) return;
    const ctx = this.getContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    this.createTone(ctx, 400, now, 0.04, 'sine', 0.08);
  }

  private createTone(
    ctx: AudioContext,
    freq: number,
    startTime: number,
    duration: number,
    type: OscillatorType,
    volume: number
  ): void {
    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, startTime);

      // Attack & decay envelope
      gain.gain.setValueAtTime(0.001, startTime);
      gain.gain.exponentialRampToValueAtTime(volume, startTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(startTime + duration + 0.05);
    } catch {
      // Ignore audio synthesis errors on locked browsers
    }
  }
}

export const audioAlerts = new AudioAlertSystem();
