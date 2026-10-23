import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Phone,
  PhoneOff,
  Shield,
  AlertTriangle,
  CheckCircle,
  Volume2,
  Mic,
  MicOff,
  Flame,
  Radio,
  Play,
  RotateCcw,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Info,
  Sliders,
  VolumeX,
} from 'lucide-react';
import { DEMO_SCENARIOS, DemoScenario } from '../data/demoScenarios';
import { audioAlerts } from '../utils/audioAlerts';
import type { RiskAssessment } from '../hooks/useLiveDetection';

interface PhoneCallMockupProps {
  onAnalyzeSegment: (text: string) => Promise<RiskAssessment | null>;
  activeRisk: RiskAssessment | null;
}

type Language = 'en' | 'hi' | 'pa';
type ViewTheme = 'nordic' | 'cyberpunk';
type InternalCallState = 'IDLE' | 'RINGING' | 'IN_CALL' | 'ENDED';

const STRINGS = {
  en: {
    headline: 'Protection during your calls',
    subheadline: 'Suraksha AI monitors call speech in real time to prevent reverse-payment and OTP fraud.',
    scamCheckTitle: 'Scam check',
    scamCheckOn: 'On for your calls',
    scamCheckOff: "Off. Calls won't be checked.",
    langTitle: 'Language',
    expectingTitle: "I'm expecting a payment",
    expectingSub: 'Helps spot requests that would make you pay instead',
    demoTitle: 'Quick Scenarios',
    demoSub: 'Plays a scripted call so you can see live fraud warnings.',
    incoming: 'Incoming Call',
    activeCall: 'Active Call · Scam Check On',
    decline: 'Decline',
    answer: 'Answer',
    endCall: 'End Call',
    continueCall: 'Continue call anyway',
    nextStepTitle: 'Next step',
    nextStepDefault: 'End the call. Check the payment in your own bank app.',
    callEnded: 'Call ended',
    callDeclined: 'Call declined',
    postAdvice: 'If you shared a code or made a payment, call your bank from the number on your card or dial 1930.',
    backHome: 'Back to home',
    whatTheySaid: 'What they said',
  },
  hi: {
    headline: 'आपकी कॉल के दौरान सुरक्षा',
    subheadline: 'सुरक्षा एआई रियल-टाइम में बातचीत की जांच करता है ताकि आपके साथ धोखाधड़ी न हो।',
    scamCheckTitle: 'स्कैम जांच',
    scamCheckOn: 'आपकी कॉल के लिए चालू',
    scamCheckOff: 'बंद. कॉल की जांच नहीं होगी.',
    langTitle: 'भाषा',
    expectingTitle: 'मुझे पैसे मिलने वाले हैं',
    expectingSub: 'यह उन अनुरोधों को पकड़ने में मदद करता है जो आपसे भुगतान करवाते हैं',
    demoTitle: 'त्वरित डेमो कॉल',
    demoSub: 'चेतावनी देखने के लिए किसी भी परिदृश्य पर क्लिक करें।',
    incoming: 'इनकमिंग कॉल',
    activeCall: 'सक्रिय कॉल · स्कैम सुरक्षा चालू',
    decline: 'अस्वीकार',
    answer: 'उठाएं',
    endCall: 'कॉल काटें',
    continueCall: 'फिर भी बात जारी रखें',
    nextStepTitle: 'अगला कदम',
    nextStepDefault: 'कॉल तुरंत काटें। अपने बैंक ऐप में जाकर पेमेंट स्टेटस जांचें।',
    callEnded: 'कॉल समाप्त',
    callDeclined: 'कॉल अस्वीकार की गई',
    postAdvice: 'यदि आपने कोई ओटीपी साझा किया है या भुगतान किया है, तो तुरंत 1930 पर कॉल करें।',
    backHome: 'मुख्य पृष्ठ पर लौटें',
    whatTheySaid: 'कॉलर ने क्या कहा',
  },
  pa: {
    headline: 'ਤੁਹਾਡੀਆਂ ਕਾਲਾਂ ਦੌਰਾਨ ਸੁਰੱਖਿਆ',
    subheadline: 'ਸੁਰੱਖਿਆ ਏਆਈ ਕਾਲ ਦੌਰਾਨ ਗੱਲਬਾਤ ਦੀ ਜਾਂਚ ਕਰਕੇ ਧੋਖਾਧੜੀ ਰੋਕਦਾ ਹੈ।',
    scamCheckTitle: 'ਸਕੈਮ ਜਾਂਚ',
    scamCheckOn: 'ਤੁਹਾਡੀਆਂ ਕਾਲਾਂ ਲਈ ਚਾਲੂ',
    scamCheckOff: 'ਬੰਦ. ਕਾਲਾਂ ਦੀ ਜਾਂਚ ਨਹੀਂ ਹੋਵੇਗੀ.',
    langTitle: 'ਭਾਸ਼ਾ',
    expectingTitle: 'ਮੈਨੂੰ ਪੈਸੇ ਮਿਲਣੇ ਹਨ',
    expectingSub: 'ਉਹਨਾਂ ਧੋਖਿਆਂ ਨੂੰ ਫੜਦਾ ਹੈ ਜਿੱਥੇ ਤੁਹਾਡੇ ਤੋਂ ਪੈਸੇ ਕਟਵਾਏ ਜਾਂਦੇ ਹਨ',
    demoTitle: 'ਡੈਮੋ ਕਾਲਾਂ',
    demoSub: 'ਚੇਤਾਵਨੀਆਂ ਦੇਖਣ ਲਈ ਡੈਮੋ ਕਾਲ ਚਲਾਓ।',
    incoming: 'ਇਨਕਮਿੰਗ ਕਾਲ',
    activeCall: 'ਐਕਟਿਵ ਕਾਲ · ਜਾਂਚ ਚਾਲੂ ਹੈ',
    decline: 'ਕੱਟੋ',
    answer: 'ਚੁੱਕੋ',
    endCall: 'ਕਾਲ ਖਤਮ ਕਰੋ',
    continueCall: 'ਕਾਲ ਜਾਰੀ ਰੱਖੋ',
    nextStepTitle: 'ਅਗਲਾ ਕਦਮ',
    nextStepDefault: 'ਕਾਲ ਬੰਦ ਕਰੋ। ਆਪਣੇ ਬੈਂਕ ਐਪ ਵਿੱਚ ਜਾ ਕੇ ਭੁਗਤਾਨ ਚੈੱਕ ਕਰੋ।',
    callEnded: 'ਕਾਲ ਖਤਮ',
    callDeclined: 'ਕਾਲ ਰੱਦ ਕੀਤੀ ਗਈ',
    postAdvice: 'ਜੇਕਰ ਤੁਸੀਂ ਓਟੀਪੀ ਜਾਂ ਪੈਸੇ ਭੇਜੇ ਹਨ, ਤੁਰੰਤ 1930 ਡਾਇਲ ਕਰੋ ਜਾਂ ਬੈਂਕ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।',
    backHome: 'ਮੁੱਖ ਪੰਨੇ ਤੇ ਜਾਓ',
    whatTheySaid: 'ਕਾਲਰ ਨੇ ਕੀ ਕਿਹਾ',
  },
};

export default function PhoneCallMockup({ onAnalyzeSegment, activeRisk }: PhoneCallMockupProps) {
  const [theme, setTheme] = useState<ViewTheme>('nordic');
  const [language, setLanguage] = useState<Language>('en');
  const [expectingPayment, setExpectingPayment] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<DemoScenario>(DEMO_SCENARIOS[0]);
  const [callState, setCallState] = useState<InternalCallState>('IDLE');
  const [currentSegmentIdx, setCurrentSegmentIdx] = useState(0);
  const [callDuration, setCallDuration] = useState(0);
  const [displayedTranscript, setDisplayedTranscript] = useState<Array<{ speaker: string; text: string }>>([]);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulatedRisk, setSimulatedRisk] = useState<RiskAssessment | null>(null);
  const [showAlertSheet, setShowAlertSheet] = useState(false);
  const [alertDetails, setAlertDetails] = useState<{
    level: 'possible' | 'high';
    title: string;
    body: string;
    nextStep: string;
    chips: string[];
  }>({
    level: 'possible',
    title: '',
    body: '',
    nextStep: '',
    chips: [],
  });

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scenarioTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const landscapeCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const waveformCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const waveformAnimRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const t = STRINGS[language];
  const effectiveRisk = simulatedRisk || activeRisk;
  const isHighRisk = effectiveRisk?.risk_level === 'HIGH' || effectiveRisk?.risk_level === 'CRITICAL';
  const isMedRisk = effectiveRisk?.risk_level === 'MEDIUM';

  // Format call timer
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // Sound synthesizer (Web Audio API)
  const playChimeTone = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioCtx();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const now = ctx.currentTime;
      // Tone 1: 880 Hz
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.frequency.setValueAtTime(880, now);
      gain1.gain.setValueAtTime(0.25, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.35);

      // Tone 2: 659.25 Hz
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.frequency.setValueAtTime(659.25, now + 0.15);
      gain2.gain.setValueAtTime(0.25, now + 0.15);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.15);
      osc2.stop(now + 0.6);
    } catch (e) {
      console.warn('Audio tone error', e);
    }
  }, []);

  // Text to speech warning
  const speakWarning = useCallback((message: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.rate = 1.0;
      utterance.pitch = 1.05;
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  // Nordic landscape canvas renderer
  const drawLandscape = useCallback(() => {
    const canvas = landscapeCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 340;
    const h = rect.height || 80;
    canvas.width = w * 2;
    canvas.height = h * 2;
    ctx.scale(2, 2);
    ctx.clearRect(0, 0, w, h);

    // Pale pink sun (#F4BEBB)
    ctx.fillStyle = '#F4BEBB';
    ctx.beginPath();
    ctx.arc(w * 0.77, h * 0.33, h * 0.18, 0, Math.PI * 2);
    ctx.fill();

    // Back rolling hill (#E6E8EB)
    ctx.fillStyle = '#E6E8EB';
    ctx.beginPath();
    ctx.moveTo(0, h * 0.75);
    ctx.bezierCurveTo(w * 0.18, h * 0.44, w * 0.32, h * 0.5, w * 0.47, h * 0.67);
    ctx.bezierCurveTo(w * 0.61, h * 0.85, w * 0.76, h * 0.52, w, h * 0.6);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fill();

    // Front rolling hill (#D5DCE4)
    ctx.fillStyle = '#D5DCE4';
    ctx.beginPath();
    ctx.moveTo(0, h * 0.87);
    ctx.bezierCurveTo(w * 0.2, h * 0.67, w * 0.38, h * 0.73, w * 0.56, h * 0.85);
    ctx.bezierCurveTo(w * 0.7, h * 0.94, w * 0.85, h * 0.77, w, h * 0.81);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fill();

    // Pine trees in Editorial Blue (#226192 at 35% opacity)
    ctx.fillStyle = 'rgba(34, 97, 146, 0.35)';
    const drawPine = (x: number, top: number, half: number) => {
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x + half, h * 0.9);
      ctx.lineTo(x - half, h * 0.9);
      ctx.closePath();
      ctx.fill();
    };
    drawPine(w * 0.18, h * 0.66, w * 0.03);
    drawPine(w * 0.25, h * 0.73, w * 0.024);
    drawPine(w * 0.52, h * 0.76, w * 0.026);
  }, []);

  // Audio waveform animation
  useEffect(() => {
    if (callState !== 'IN_CALL') {
      if (waveformAnimRef.current) cancelAnimationFrame(waveformAnimRef.current);
      return;
    }

    const canvas = waveformCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let wavePhase = 0;
    const bars = [0.25, 0.55, 0.8, 0.45, 1.0, 0.65, 0.35, 0.75, 0.5, 0.2];

    const renderWave = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width || 300;
      const h = rect.height || 64;
      canvas.width = w * 2;
      canvas.height = h * 2;
      ctx.scale(2, 2);
      ctx.clearRect(0, 0, w, h);

      const gap = w / (bars.length + 1);
      ctx.lineCap = 'round';
      ctx.lineWidth = 4;
      ctx.strokeStyle = isHighRisk
        ? 'rgba(217, 45, 32, 0.75)'
        : isMedRisk
        ? 'rgba(232, 163, 23, 0.75)'
        : 'rgba(34, 97, 146, 0.55)';

      bars.forEach((base, i) => {
        const wobble = 0.75 + 0.25 * Math.sin(wavePhase + i * 0.7);
        const barH = Math.max(6, h * base * wobble * 0.65);
        const x = gap * (i + 1);

        ctx.beginPath();
        ctx.moveTo(x, (h - barH) / 2);
        ctx.lineTo(x, (h + barH) / 2);
        ctx.stroke();
      });

      wavePhase += 0.08;
      waveformAnimRef.current = requestAnimationFrame(renderWave);
    };

    renderWave();

    return () => {
      if (waveformAnimRef.current) cancelAnimationFrame(waveformAnimRef.current);
    };
  }, [callState, isHighRisk, isMedRisk]);

  // Redraw landscape when returning to idle or changing theme
  useEffect(() => {
    if (callState === 'IDLE' && theme === 'nordic') {
      const tm = setTimeout(drawLandscape, 50);
      return () => clearTimeout(tm);
    }
  }, [callState, theme, drawLandscape]);

  // Call timer interval
  useEffect(() => {
    if (callState === 'IN_CALL') {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [callState]);

  // Clear timeouts on unmount
  useEffect(() => {
    return () => {
      if (scenarioTimeoutRef.current) clearTimeout(scenarioTimeoutRef.current);
      if (waveformAnimRef.current) cancelAnimationFrame(waveformAnimRef.current);
    };
  }, []);

  // Extract dynamic "What they said" chips
  const extractChips = (assessment: RiskAssessment | null, transcripts: Array<{ speaker: string; text: string }>) => {
    const chips: string[] = [];
    if (!assessment) return chips;

    // From rule indicators
    if (assessment.rule_analysis?.triggered_indicators) {
      assessment.rule_analysis.triggered_indicators.forEach((ind) => {
        if (ind.keyword_or_pattern) {
          chips.push(ind.keyword_or_pattern);
        }
      });
    }

    // From evidence excerpts
    if (assessment.evidence) {
      assessment.evidence.forEach((ev) => {
        if (ev.excerpt && !chips.includes(ev.excerpt)) {
          chips.push(ev.excerpt);
        }
      });
    }

    // Keyword heuristic backup
    const fullText = transcripts.map((t) => t.text).join(' ').toLowerCase();
    const suspectKeywords = [
      'scan qr',
      'qr code',
      'otp',
      'upi pin',
      'digital arrest',
      'cbi',
      'customs',
      'anydesk',
      'screen share',
      'lottery',
      'gate pass',
      'processing fee',
    ];

    suspectKeywords.forEach((kw) => {
      if (fullText.includes(kw) && !chips.some((c) => c.toLowerCase().includes(kw))) {
        chips.push(kw);
      }
    });

    return chips.slice(0, 3);
  };

  // Start scenario simulation
  const startScenario = (scenario: DemoScenario) => {
    setSelectedScenario(scenario);
    setDisplayedTranscript([]);
    setCurrentSegmentIdx(0);
    setSimulatedRisk(null);
    setShowAlertSheet(false);
    setCallState('RINGING');
    audioAlerts.playCautionAlert();
  };

  // Accept incoming call
  const handleAnswerCall = () => {
    setCallState('IN_CALL');
    audioAlerts.playClick();
    playScenarioSegments(selectedScenario, 0);
  };

  // Play dialogue segments recursively
  const playScenarioSegments = (scenario: DemoScenario, index: number) => {
    if (index >= scenario.segments.length) {
      setIsSimulating(false);
      return;
    }

    setIsSimulating(true);
    const seg = scenario.segments[index];

    scenarioTimeoutRef.current = setTimeout(async () => {
      const updatedTranscripts = [...displayedTranscript, { speaker: seg.speaker, text: seg.text }];
      setDisplayedTranscript(updatedTranscripts);
      setCurrentSegmentIdx(index + 1);

      // Send speech segment to live backend
      try {
        const assessment = await onAnalyzeSegment(seg.text);
        if (assessment) {
          setSimulatedRisk(assessment);
          const chips = extractChips(assessment, updatedTranscripts);

          if (assessment.risk_level === 'HIGH' || assessment.risk_level === 'CRITICAL') {
            audioAlerts.playHighRiskAlert();
            playChimeTone();
            setAlertDetails({
              level: 'high',
              title: assessment.caption || 'Suspicious request detected in caller speech',
              body: assessment.reasons?.[0] || 'Never share your OTP or scan any QR code to receive money.',
              nextStep: assessment.recommended_action || t.nextStepDefault,
              chips,
            });
            setShowAlertSheet(true);
            speakWarning('Warning: do not scan any QR code or enter your PIN.');
          } else if (assessment.risk_level === 'MEDIUM') {
            audioAlerts.playCautionAlert();
            setAlertDetails({
              level: 'possible',
              title: assessment.caption || 'Possible scam indicator detected',
              body: assessment.reasons?.[0] || 'Check the payment status in your own bank app first.',
              nextStep: assessment.recommended_action || t.nextStepDefault,
              chips,
            });
            setShowAlertSheet(true);
          } else {
            audioAlerts.playSafeChime();
          }
        }
      } catch (e) {
        console.error('Segment analysis error', e);
      }

      playScenarioSegments(scenario, index + 1);
    }, seg.delayMs);
  };

  // End call
  const handleHangUp = () => {
    if (scenarioTimeoutRef.current) clearTimeout(scenarioTimeoutRef.current);
    setCallState('ENDED');
    setIsSimulating(false);
    setShowAlertSheet(false);
    audioAlerts.playClick();
  };

  const handleReturnHome = () => {
    setCallState('IDLE');
    setDisplayedTranscript([]);
    setSimulatedRisk(null);
    setShowAlertSheet(false);
  };

  // Dynamic status panel calculation
  const getStatusBadge = () => {
    if (isHighRisk) {
      return {
        bg: 'bg-[#FDECEB] border-[#D92D20] text-[#8A1C14]',
        title: 'High Risk Scam Intercepted',
        sub: effectiveRisk?.caption || 'Coercive fraud detected. Disconnect immediately.',
        icon: <Flame className="w-5 h-5 text-[#B42318] animate-bounce" />,
      };
    }
    if (isMedRisk) {
      return {
        bg: 'bg-[#FFF4DC] border-[#E8A317] text-[#6B4300]',
        title: 'Checking a payment request…',
        sub: 'Possible risk. Don’t share or scan anything yet.',
        icon: <AlertTriangle className="w-5 h-5 text-[#B26A00] animate-pulse" />,
      };
    }
    return {
      bg: 'bg-[#E3EDF5] border-[#226192]/30 text-[#123A58]',
      title: 'Scam check on · Listening',
      sub: 'Suraksha AI is monitoring speech for fraud cues',
      icon: <Shield className="w-5 h-5 text-[#226192]" />,
    };
  };

  const statusInfo = getStatusBadge();
  const currentChips = extractChips(effectiveRisk, displayedTranscript);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* LEFT COLUMN: Controls & Scenario Drawer */}
      <div className="lg:col-span-5 space-y-4">
        {/* Style & Experience Switcher */}
        <div className="glass-card p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-[var(--purple-bright)]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-white">Interface Design</span>
          </div>
          <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-xl border border-white/10 text-xs">
            <button
              onClick={() => setTheme('nordic')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                theme === 'nordic'
                  ? 'bg-[#226192] text-white shadow'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              🌲 Nordic Editorial
            </button>
            <button
              onClick={() => setTheme('cyberpunk')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                theme === 'cyberpunk'
                  ? 'bg-[var(--purple-glow)] text-white shadow'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              ⚡ Cyberpunk HUD
            </button>
          </div>
        </div>

        {/* Real Indian Scenarios List */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--purple-bright)]" />
              Real Indian Scam Scenarios
            </h3>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full glass border-[var(--purple-border)] text-[var(--purple-bright)] font-mono">
              {DEMO_SCENARIOS.length} Scenarios
            </span>
          </div>

          <p className="text-xs text-[var(--text-muted)] mb-3 leading-relaxed">
            Click any scenario to watch Suraksha intercept live speech, extract deceptive keywords, and trigger actionable defensive guidance.
          </p>

          <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
            {DEMO_SCENARIOS.map((scen) => {
              const isSelected = selectedScenario.id === scen.id;
              const isDanger = scen.expectedRisk === 'HIGH';
              return (
                <div
                  key={scen.id}
                  onClick={() => {
                    if (callState === 'IN_CALL' || callState === 'RINGING') handleHangUp();
                    startScenario(scen);
                  }}
                  className={`
                    p-3.5 rounded-xl cursor-pointer transition-all border
                    ${
                      isSelected && (callState === 'IN_CALL' || callState === 'RINGING')
                        ? 'bg-[var(--glass-bg-hover)] border-[var(--purple-bright)] shadow-[0_0_20px_rgba(168,85,247,0.2)]'
                        : 'glass border-[var(--glass-border)] hover:border-[var(--purple-dim)]/40 hover:bg-white/[0.03]'
                    }
                  `}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-sm font-medium text-[var(--text-primary)]">
                      {scen.title}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full flex-shrink-0 border ${
                        isDanger
                          ? 'bg-red-500/15 text-red-400 border-red-500/30'
                          : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      }`}
                    >
                      {scen.badge}
                    </span>
                  </div>

                  <p className="text-xs text-[var(--text-muted)] line-clamp-2 mb-2">
                    {scen.explanation}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)] font-mono">
                    <span className="text-[var(--purple-candle)]">🗣️ {scen.language}</span>
                    <button
                      className="inline-flex items-center gap-1 text-[var(--green-accent)] hover:underline"
                      onClick={(e) => {
                        e.stopPropagation();
                        startScenario(scen);
                      }}
                    >
                      <Play className="w-3 h-3 fill-current" />
                      Simulate Call
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 1930 Helpline Quick Notice */}
        <div className="glass p-4 rounded-xl border-red-500/20 bg-red-950/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center text-red-400 font-bold text-base">
              1930
            </div>
            <div>
              <p className="text-xs font-semibold text-white">National Cyber Crime Helpline</p>
              <p className="text-[11px] text-[var(--text-muted)]">Government of India citizen defense portal</p>
            </div>
          </div>
          <a
            href="https://cybercrime.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 glass rounded-lg hover:bg-white/10 text-[var(--purple-bright)] transition-colors"
            title="Open cybercrime.gov.in"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* RIGHT COLUMN: Realistic Phone Device Simulation */}
      <div className="lg:col-span-7 flex flex-col items-center">
        {/* Prominent Platform GSM Notice */}
        <div className="w-full max-w-[390px] mb-3 px-3.5 py-2.5 rounded-xl glass border-amber-500/30 bg-amber-950/20 text-[11px] text-amber-200/90 leading-tight flex items-start gap-2 shadow-sm">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-white block mb-0.5">Carrier GSM Control Notice:</span>
            Web applications cannot disconnect native cellular calls. If you suspect fraud, immediately disconnect via your phone's dialer.
          </div>
        </div>

        {/* ======================================================== */}
        {/* NORDIC EDITORIAL PHONE SHELL */}
        {/* ======================================================== */}
        {theme === 'nordic' ? (
          <div className="relative w-full max-w-[390px] min-h-[640px] bg-[#FAFAF8] text-[#1F2937] rounded-[44px] overflow-hidden flex flex-col border-[10px] border-[#262a30] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.5)] transition-all">
            {/* Status Bar */}
            <div className="h-9 px-6 pt-2.5 flex justify-between items-center text-[11px] font-semibold text-slate-700 bg-transparent z-40 select-none">
              <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              <div className="w-20 h-4 bg-black rounded-full mx-auto -mt-0.5" />
              <div className="flex items-center space-x-1.5 text-slate-600">
                <span className="text-[10px] font-mono">5G</span>
                <Radio className="w-3.5 h-3.5" />
              </div>
            </div>

            {/* App Viewport */}
            <div className="relative flex-1 p-5 flex flex-col justify-between overflow-y-auto">
              {/* 1. IDLE / HOME SCREEN */}
              {callState === 'IDLE' && (
                <div className="space-y-4 animate-fade-in flex flex-col justify-between h-full">
                  <div className="space-y-3">
                    {/* Brand */}
                    <div className="flex items-center space-x-2 text-[#226192]">
                      <Shield className="w-6 h-6 stroke-[2.2]" />
                      <span className="font-bold text-base tracking-wide">Suraksha · Edgerunners</span>
                    </div>

                    {/* Headline */}
                    <h2 className="text-xl font-bold text-[#1F2937] leading-snug">
                      {t.headline}
                    </h2>

                    {/* Nordic Landscape Illustration Canvas */}
                    <div className="w-full h-20 rounded-2xl overflow-hidden bg-white border border-[#E6E8EB] relative shadow-sm">
                      <canvas ref={landscapeCanvasRef} className="w-full h-full block" />
                    </div>

                    {/* Language Selector */}
                    <div className="space-y-1.5">
                      <div className="text-xs font-semibold text-[#4B5563]">{t.langTitle}</div>
                      <div className="grid grid-cols-3 gap-2">
                        {(['en', 'hi', 'pa'] as Language[]).map((l) => (
                          <button
                            key={l}
                            onClick={() => setLanguage(l)}
                            className={`py-2 rounded-xl text-xs font-semibold transition border ${
                              language === l
                                ? 'border-[#226192] bg-[#226192] text-white shadow-sm'
                                : 'border-[#C9CDD3] bg-white text-[#1F2937] hover:bg-slate-50'
                            }`}
                          >
                            {l === 'en' ? 'English' : l === 'hi' ? 'हिन्दी' : 'ਪੰਜਾਬੀ'}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Setting: Expecting Payment */}
                    <div
                      onClick={() => setExpectingPayment(!expectingPayment)}
                      className="bg-white border border-[#E6E8EB] rounded-2xl p-3.5 flex items-center justify-between cursor-pointer shadow-sm hover:border-[#226192]/40 transition"
                    >
                      <div className="pr-2">
                        <div className="font-semibold text-xs text-[#1F2937]">{t.expectingTitle}</div>
                        <div className="text-[11px] text-[#4B5563] mt-0.5 leading-tight">{t.expectingSub}</div>
                      </div>
                      <div
                        className={`w-12 h-7 rounded-full relative transition-colors duration-200 shrink-0 ${
                          expectingPayment ? 'bg-[#226192]' : 'bg-[#C9CDD3]'
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-full bg-white absolute top-1 shadow-sm transition-all duration-200 ${
                            expectingPayment ? 'right-1' : 'left-1'
                          }`}
                        />
                      </div>
                    </div>

                    {/* Live Backend Status */}
                    <div className="flex items-center space-x-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl w-fit">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="font-medium">Connected to Live FastAPI Engine</span>
                    </div>

                    {/* Quick Demo Scenarios Trigger */}
                    <div className="bg-white border border-[#E6E8EB] rounded-2xl p-3.5 space-y-2 shadow-sm">
                      <div>
                        <div className="font-semibold text-xs text-[#1F2937]">{t.demoTitle}</div>
                        <div className="text-[11px] text-[#4B5563]">{t.demoSub}</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 pt-1">
                        <button
                          onClick={() => startScenario(DEMO_SCENARIOS[0])}
                          className="py-2 px-2.5 bg-white border border-[#226192] text-[#226192] hover:bg-[#E3EDF5] rounded-xl text-xs font-semibold transition text-left truncate"
                        >
                          📱 QR Scan Fraud
                        </button>
                        <button
                          onClick={() => startScenario(DEMO_SCENARIOS[2])}
                          className="py-2 px-2.5 bg-white border border-[#226192] text-[#226192] hover:bg-[#E3EDF5] rounded-xl text-xs font-semibold transition text-left truncate"
                        >
                          🔑 Bank OTP Phishing
                        </button>
                        <button
                          onClick={() => startScenario(DEMO_SCENARIOS[1])}
                          className="py-2 px-2.5 bg-white border border-[#226192] text-[#226192] hover:bg-[#E3EDF5] rounded-xl text-xs font-semibold transition text-left truncate"
                        >
                          ⚖️ Digital Arrest
                        </button>
                        <button
                          onClick={() => startScenario(DEMO_SCENARIOS[5])}
                          className="py-2 px-2.5 bg-white border border-[#226192] text-[#226192] hover:bg-[#E3EDF5] rounded-xl text-xs font-semibold transition text-left truncate"
                        >
                          🍔 Harmless Call
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 2. RINGING / INCOMING CALL SCREEN */}
              {callState === 'RINGING' && (
                <div className="flex flex-col items-center justify-between text-center flex-1 py-4 animate-fade-in">
                  <div className="space-y-4 flex flex-col items-center w-full">
                    <span className="text-xs uppercase tracking-wider text-[#4B5563] font-semibold">
                      {t.incoming}
                    </span>

                    {/* Ripple avatar */}
                    <div className="relative my-4">
                      <div className="absolute inset-0 rounded-full bg-[#226192] opacity-25 animate-ping" />
                      <div className="w-24 h-24 rounded-full bg-[#E3EDF5] flex items-center justify-center text-[#226192] shadow-sm relative z-10">
                        <Phone className="w-10 h-10" />
                      </div>
                    </div>

                    <h2 className="text-xl font-bold text-[#1F2937] max-w-[260px] line-clamp-1">
                      {selectedScenario.callerName}
                    </h2>
                    <p className="text-xs font-medium text-[#4B5563] font-mono">
                      {selectedScenario.callerNumber}
                    </p>

                    <div className="inline-flex items-center space-x-2 bg-[#E3EDF5] text-[#123A58] px-3.5 py-1.5 rounded-full text-xs font-medium border border-[#226192]/20">
                      <Shield className="w-4 h-4 text-[#226192]" />
                      <span>{t.scamCheckOn}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="w-full grid grid-cols-2 gap-3 pt-6">
                    <button
                      onClick={handleHangUp}
                      className="py-3 bg-white border-2 border-[#B42318] text-[#B42318] hover:bg-red-50 rounded-2xl font-semibold text-xs transition"
                    >
                      {t.decline}
                    </button>
                    <button
                      onClick={handleAnswerCall}
                      className="py-3 bg-[#226192] hover:bg-[#1a4d74] text-white rounded-2xl font-semibold text-xs shadow-md transition"
                    >
                      {t.answer}
                    </button>
                  </div>
                </div>
              )}

              {/* 3. IN-CALL SCREEN */}
              {callState === 'IN_CALL' && (
                <div className="flex flex-col justify-between flex-1 relative animate-fade-in space-y-3">
                  {/* Call Header */}
                  <div className="text-center space-y-0.5">
                    <h3 className="text-sm font-bold text-[#1F2937] truncate px-2">
                      {selectedScenario.callerName}
                    </h3>
                    <p className="text-xs text-[#4B5563] font-mono">
                      {selectedScenario.callerNumber} · {formatTime(callDuration)}
                    </p>
                  </div>

                  {/* Dynamic Status Panel */}
                  <div className={`rounded-2xl p-3.5 border transition-all duration-300 shadow-sm ${statusInfo.bg}`}>
                    <div className="flex items-start space-x-3">
                      <div className="p-0.5 shrink-0">{statusInfo.icon}</div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-xs font-bold leading-tight">{statusInfo.title}</h4>
                        <p className="text-[11px] opacity-90 mt-0.5 leading-snug line-clamp-2">
                          {statusInfo.sub}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Interactive Audio Waveform Canvas */}
                  <div className="w-full h-14 bg-white/70 rounded-xl border border-[#E6E8EB] flex items-center justify-center p-1 shadow-inner">
                    <canvas ref={waveformCanvasRef} className="w-full h-full block" />
                  </div>

                  {/* Dynamic "What they said" Alert Chips */}
                  {currentChips.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-[#4B5563] flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-[#B26A00]" />
                        <span>{t.whatTheySaid}:</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {currentChips.map((chip, idx) => (
                          <span
                            key={idx}
                            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border shadow-xs ${
                              isHighRisk
                                ? 'bg-red-50 text-red-800 border-red-300 font-bold'
                                : 'bg-amber-50 text-amber-900 border-amber-300'
                            }`}
                          >
                            "{chip}"
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Live Dialogue Turns / Captions */}
                  <div className="flex-1 min-h-[140px] max-h-[180px] overflow-y-auto space-y-2 p-2.5 bg-white/80 rounded-2xl border border-[#E6E8EB] shadow-xs">
                    {displayedTranscript.length === 0 ? (
                      <div className="text-center py-6 text-[#4B5563] text-xs">
                        <Mic className="w-5 h-5 mx-auto mb-1 opacity-40 text-[#226192]" />
                        <span>Transcribing caller audio…</span>
                      </div>
                    ) : (
                      displayedTranscript.map((turn, i) => (
                        <div
                          key={i}
                          className={`p-2 rounded-xl text-xs leading-relaxed transition-all ${
                            turn.speaker === 'caller'
                              ? 'bg-[#E3EDF5]/70 text-[#123A58] border border-[#226192]/20 mr-4'
                              : 'bg-slate-100 text-[#1F2937] ml-auto max-w-[85%]'
                          }`}
                        >
                          <span className="text-[9px] block text-[#4B5563] font-semibold uppercase mb-0.5">
                            {turn.speaker}
                          </span>
                          {turn.text}
                        </div>
                      ))
                    )}
                    {isSimulating && (
                      <div className="flex items-center gap-1.5 text-[10px] text-[#226192] font-medium pt-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#226192] animate-ping" />
                        <span>Transcribing caller speech in real time…</span>
                      </div>
                    )}
                  </div>

                  {/* Call Controls: Mute, Speaker, End Call */}
                  <div className="flex justify-around items-center pt-2 pb-1 border-t border-[#E6E8EB]">
                    <div className="flex flex-col items-center space-y-1">
                      <button
                        onClick={() => setIsMuted(!isMuted)}
                        className={`w-11 h-11 rounded-full border flex items-center justify-center transition ${
                          isMuted ? 'bg-[#226192] text-white border-[#226192]' : 'border-[#C9CDD3] bg-white text-[#1F2937]'
                        }`}
                      >
                        {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                      </button>
                      <span className="text-[10px] text-[#4B5563]">Mute</span>
                    </div>

                    <div className="flex flex-col items-center space-y-1">
                      <button
                        onClick={() => setIsSpeakerOn(!isSpeakerOn)}
                        className={`w-11 h-11 rounded-full border flex items-center justify-center transition ${
                          isSpeakerOn ? 'bg-[#226192] text-white border-[#226192]' : 'border-[#C9CDD3] bg-white text-[#1F2937]'
                        }`}
                      >
                        <Volume2 className="w-4 h-4" />
                      </button>
                      <span className="text-[10px] text-[#4B5563]">Speaker</span>
                    </div>

                    <div className="flex flex-col items-center space-y-1">
                      <button
                        onClick={handleHangUp}
                        className="w-11 h-11 rounded-full bg-[#B42318] hover:bg-red-700 text-white flex items-center justify-center shadow-md transition"
                      >
                        <PhoneOff className="w-5 h-5" />
                      </button>
                      <span className="text-[10px] text-[#B42318] font-bold">{t.endCall}</span>
                    </div>
                  </div>

                  {/* Slide-up Risk Alert Sheet Overlay */}
                  {showAlertSheet && (
                    <div className="absolute inset-x-0 bottom-0 bg-[#FAFAF8] rounded-3xl p-4 border border-[#C9CDD3] shadow-2xl space-y-3 z-30 animate-slide-up">
                      {/* Banner */}
                      <div
                        className={`p-3 rounded-xl border flex items-center justify-between ${
                          alertDetails.level === 'high'
                            ? 'bg-[#FDECEB] border-[#D92D20] text-[#8A1C14]'
                            : 'bg-[#FFF4DC] border-[#E8A317] text-[#6B4300]'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          {alertDetails.level === 'high' ? (
                            <Flame className="w-5 h-5 text-[#D92D20]" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-[#B26A00]" />
                          )}
                          <span className="font-bold text-xs uppercase tracking-wide">
                            {alertDetails.level === 'high' ? 'High Risk Intercept' : 'Possible Scam Risk'}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono opacity-80">Suraksha AI</span>
                      </div>

                      {/* Content */}
                      <div className="space-y-1">
                        <h4 className="text-xs font-bold text-[#1F2937] leading-tight">
                          {alertDetails.title}
                        </h4>
                        <p className="text-[11px] text-[#4B5563] leading-relaxed">
                          {alertDetails.body}
                        </p>
                      </div>

                      {/* Next Step Card */}
                      <div className="bg-white border border-[#C9CDD3] rounded-xl p-2.5 space-y-0.5 shadow-xs">
                        <div className="text-[10px] font-semibold text-[#4B5563] uppercase tracking-wider">
                          {t.nextStepTitle}
                        </div>
                        <p className="text-xs font-medium text-[#1F2937] leading-snug">
                          {alertDetails.nextStep}
                        </p>
                      </div>

                      {/* Action buttons */}
                      <div className="space-y-2 pt-1">
                        <button
                          onClick={handleHangUp}
                          className="w-full py-2.5 bg-[#B42318] hover:bg-red-700 text-white rounded-xl font-bold text-xs shadow-sm transition"
                        >
                          {t.endCall}
                        </button>
                        <button
                          onClick={() => setShowAlertSheet(false)}
                          className="w-full py-2 bg-white border border-[#C9CDD3] text-[#4B5563] hover:bg-slate-50 rounded-xl font-medium text-xs transition"
                        >
                          {t.continueCall}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 4. CALL ENDED SCREEN */}
              {callState === 'ENDED' && (
                <div className="flex flex-col items-center justify-center text-center flex-1 py-8 space-y-4 animate-fade-in">
                  <div className="w-16 h-16 rounded-full bg-[#E6E8EB] flex items-center justify-center text-[#4B5563] shadow-inner">
                    <PhoneOff className="w-8 h-8" />
                  </div>
                  <div className="space-y-1 max-w-[280px]">
                    <h3 className="text-lg font-bold text-[#1F2937]">{t.callEnded}</h3>
                    <p className="text-xs text-[#4B5563] leading-relaxed">{t.postAdvice}</p>
                  </div>
                  <button
                    onClick={handleReturnHome}
                    className="px-6 py-2.5 bg-[#226192] text-white rounded-xl font-semibold text-xs shadow-sm hover:bg-[#1a4d74] transition"
                  >
                    {t.backHome}
                  </button>
                </div>
              )}
            </div>

            {/* Android Pill Bar */}
            <div className="h-5 flex items-center justify-center bg-transparent z-40">
              <div className="w-28 h-1 bg-slate-400 rounded-full" />
            </div>
          </div>
        ) : (
          /* ======================================================== */
          /* CYBERPUNK TERMINAL PHONE SHELL */
          /* ======================================================== */
          <div
            className={`
              relative w-full max-w-[370px] rounded-[44px] p-4 border-4 transition-all duration-500 shadow-2xl
              ${
                isHighRisk
                  ? 'border-red-500/60 shadow-[0_0_60px_rgba(239,68,68,0.3)] bg-gradient-to-b from-[#18040a] to-[#0c0205]'
                  : isMedRisk
                  ? 'border-amber-500/60 shadow-[0_0_60px_rgba(245,158,11,0.25)] bg-gradient-to-b from-[#180e04] to-[#0c0702]'
                  : 'border-[var(--glass-border)] shadow-[0_0_60px_rgba(139,92,246,0.18)] bg-gradient-to-b from-[#0e051c] to-[#06020c]'
              }
            `}
          >
            {/* Dynamic Island */}
            <div className="relative z-20 flex justify-center mb-4">
              <div className="w-28 h-5 bg-black/90 rounded-full flex items-center justify-between px-3 border border-white/10 shadow-inner">
                <div className="w-2 h-2 rounded-full bg-emerald-500/70 animate-pulse" />
                <div className="w-3 h-3 rounded-full bg-[#1e1038] border border-white/20" />
              </div>
            </div>

            {/* Status Bar */}
            <div className="flex justify-between items-center text-[11px] text-white/60 px-3 mb-4 font-mono">
              <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-emerald-400">Jio 5G</span>
                <Radio className="w-3.5 h-3.5 text-white/70" />
              </div>
            </div>

            {/* Caller Profile */}
            <div className="text-center mb-4">
              <div className="relative inline-block mb-2">
                <div
                  className={`
                    w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold
                    border-2 shadow-lg mx-auto transition-transform duration-500
                    ${
                      isHighRisk
                        ? 'border-red-500 bg-red-950/60 text-red-300 animate-pulse'
                        : 'border-[var(--purple-bright)] bg-[var(--purple-dim)]/40 text-[var(--purple-bright)]'
                    }
                  `}
                >
                  {selectedScenario.callerName.slice(0, 1)}
                </div>

                {callState === 'IN_CALL' && (
                  <div
                    className={`
                      absolute -bottom-1 -right-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border shadow
                      ${
                        isHighRisk
                          ? 'bg-red-500 text-white border-red-300'
                          : isMedRisk
                          ? 'bg-amber-500 text-black border-amber-300'
                          : 'bg-emerald-500 text-black border-emerald-300'
                      }
                    `}
                  >
                    {effectiveRisk?.risk_level || 'ANALYZING'}
                  </div>
                )}
              </div>

              <h4 className="text-base font-bold text-white line-clamp-1">
                {selectedScenario.callerName}
              </h4>
              <p className="text-xs text-white/60 font-mono">{selectedScenario.callerNumber}</p>
              <p className="text-xs mt-1 font-mono">
                {callState === 'RINGING' && <span className="text-amber-400 animate-pulse">Incoming Call…</span>}
                {callState === 'IN_CALL' && <span className="text-emerald-400">Active Call · {formatTime(callDuration)}</span>}
                {callState === 'ENDED' && <span className="text-red-400">Call Ended</span>}
                {callState === 'IDLE' && <span className="text-[var(--text-muted)]">Select a scenario to test</span>}
              </p>
            </div>

            {/* In-Call HUD Overlay */}
            <div className="min-h-[220px] max-h-[260px] overflow-y-auto mb-4 p-3 rounded-2xl glass border-white/10 flex flex-col justify-end space-y-2">
              {callState === 'IDLE' && (
                <div className="text-center py-10 text-white/50 text-xs">
                  <Shield className="w-8 h-8 mx-auto mb-2 text-[var(--purple-bright)] opacity-60" />
                  <p>Suraksha AI Call Interceptor</p>
                  <p className="text-[10px] mt-1 text-[var(--text-muted)]">
                    Live voice stream will be monitored for scams
                  </p>
                </div>
              )}

              {isHighRisk && callState === 'IN_CALL' && (
                <div className="p-2.5 rounded-xl bg-red-600/30 border border-red-500 text-white animate-bounce">
                  <div className="flex items-center gap-1.5 font-bold text-xs text-red-300 mb-0.5">
                    <Flame className="w-4 h-4 text-red-400" />
                    CRITICAL SCAM WARNING
                  </div>
                  <p className="text-[11px] leading-tight text-white/90">
                    {effectiveRisk?.recommended_action || 'Never share your OTP or scan any QR code to receive money!'}
                  </p>
                </div>
              )}

              {displayedTranscript.map((seg, i) => (
                <div
                  key={i}
                  className={`p-2 rounded-xl text-xs leading-relaxed transition-all ${
                    seg.speaker === 'caller'
                      ? 'bg-white/10 text-white border border-white/10'
                      : 'bg-emerald-500/20 text-emerald-200 ml-auto max-w-[80%]'
                  }`}
                >
                  <span className="text-[9px] block text-white/40 uppercase mb-0.5">{seg.speaker}</span>
                  {seg.text}
                </div>
              ))}

              {isSimulating && (
                <div className="flex items-center gap-1.5 text-[10px] text-[var(--purple-candle)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--purple-candle)] animate-ping" />
                  <span>Transcribing caller speech in real time…</span>
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="pt-2">
              {callState === 'IN_CALL' ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2 px-2 text-center text-[10px] text-white/70">
                    <button
                      onClick={() => setIsMuted(!isMuted)}
                      className={`p-3 rounded-full flex flex-col items-center justify-center transition-colors ${
                        isMuted ? 'bg-amber-500/30 text-amber-300' : 'bg-white/10 hover:bg-white/20'
                      }`}
                    >
                      {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                      <span className="mt-1">Mute</span>
                    </button>
                    <button
                      onClick={() => setIsSpeakerOn(!isSpeakerOn)}
                      className={`p-3 rounded-full flex flex-col items-center justify-center transition-colors ${
                        isSpeakerOn ? 'bg-emerald-500/30 text-emerald-300' : 'bg-white/10 hover:bg-white/20'
                      }`}
                    >
                      <Volume2 className="w-4 h-4" />
                      <span className="mt-1">Speaker</span>
                    </button>
                    <button
                      onClick={() => {
                        audioAlerts.playHighRiskAlert();
                        speakWarning('Warning: this call is flagged by Suraksha as a suspected scam.');
                      }}
                      className="p-3 rounded-full bg-white/10 hover:bg-white/20 flex flex-col items-center justify-center text-red-300 transition-colors"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      <span className="mt-1">Warn</span>
                    </button>
                  </div>
                  <div className="flex justify-center">
                    <button
                      onClick={handleHangUp}
                      className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-105 active:scale-95"
                    >
                      <PhoneOff className="w-6 h-6" />
                    </button>
                  </div>
                </div>
              ) : callState === 'RINGING' ? (
                <div className="flex justify-around items-center px-6">
                  <button
                    onClick={handleHangUp}
                    className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg"
                  >
                    <PhoneOff className="w-6 h-6" />
                  </button>
                  <button
                    onClick={handleAnswerCall}
                    className="w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center shadow-lg animate-pulse"
                  >
                    <Phone className="w-6 h-6" />
                  </button>
                </div>
              ) : (
                <div className="flex justify-center">
                  <button
                    onClick={() => startScenario(selectedScenario)}
                    className="btn-primary w-full py-3 text-xs flex items-center justify-center gap-2 rounded-2xl"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    Simulate Call Now
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
