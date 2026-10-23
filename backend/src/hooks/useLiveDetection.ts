import { useState, useRef, useCallback, useEffect } from 'react';

export interface TranscriptSegment {
  text: string;
  timestamp: number;
  confidence: number;
  speaker: string;
}

export interface RetrievedExample {
  example_id: string;
  label: 'SCAM' | 'LEGITIMATE';
  similarity: number;
  distance: number;
  text: string;
}

export interface RAGClassificationResponse {
  classification: 'SCAM' | 'LEGITIMATE' | 'UNCERTAIN';
  risk_score: number;
  confidence: number;
  insufficient_evidence: boolean;
  indicators: string[];
  retrieved_examples: RetrievedExample[];
  explanation: string;
  retrieval_latency_ms: number;
  classification_latency_ms: number;
}

export interface RAGHealthResponse {
  status: string;
  embedding_model: string;
  embedding_model_loaded: boolean;
  vector_index_loaded: boolean;
  indexed_documents_count: number;
  vector_store_type: string;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  confidence: number | null;
  caption: string;
  reasons: string[];
  evidence: Array<{
    excerpt: string;
    source: string;
    indicator: string;
  }>;
  recommended_action: string;
  rag_classification?: RAGClassificationResponse | null;
  rule_analysis: {
    rule_score: number;
    triggered_indicators: Array<{
      category: string;
      keyword_or_pattern: string;
      explanation: string;
      weight: number;
    }>;
    suppressed_protective_matches: string[];
  };
  contextual_analysis: {
    caller_identity_claim: string | null;
    claimed_organisation: string | null;
    intent_classification: string;
    intent_risk_score: number;
    contextual_caption: string;
    possible_impersonation: boolean;
  };
}

interface UseLiveDetectionReturn {
  isListening: boolean;
  isProcessing: boolean;
  transcript: TranscriptSegment[];
  riskAssessment: RiskAssessment | null;
  error: string | null;
  callId: string;
  startListening: () => Promise<void>;
  stopListening: () => void;
  analyzeText: (text: string) => Promise<void>;
}

const API_BASE = '';

export function useLiveDetection(): UseLiveDetectionReturn {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [callId] = useState(() => `call-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const segmentCountRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const processAudioChunk = useCallback(async (audioBlob: Blob) => {
    if (audioBlob.size < 100) return;
    setIsProcessing(true);
    setError(null);

    try {
      // Step 1: Transcribe the audio via Sarvam
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      formData.append('language_code', 'auto');

      const transcribeRes = await fetch(`${API_BASE}/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (!transcribeRes.ok) {
        const errData = await transcribeRes.json().catch(() => ({}));
        throw new Error(errData.detail || `Transcription failed (${transcribeRes.status})`);
      }

      const transcribeData = await transcribeRes.json();
      const text = transcribeData.transcript || '';
      if (!text.trim()) {
        setIsProcessing(false);
        return;
      }

      const newSegment: TranscriptSegment = {
        text,
        timestamp: Date.now(),
        confidence: transcribeData.confidence || 0.9,
        speaker: 'caller',
      };
      setTranscript(prev => [...prev, newSegment]);

      // Step 2: Analyze via the call segments endpoint
      segmentCountRef.current += 1;
      const segmentStart = (segmentCountRef.current - 1) * 5;

      const analyzeRes = await fetch(`${API_BASE}/calls/${callId}/segments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          speaker: 'caller',
          language_code: 'auto',
          start_seconds: segmentStart,
          end_seconds: segmentStart + 5,
          transcript_confidence: transcribeData.confidence || 0.92,
        }),
      });

      if (analyzeRes.ok) {
        const analysisData = await analyzeRes.json();
        if (analysisData.assessment) {
          setRiskAssessment(analysisData.assessment);
        }
      }
    } catch (err: any) {
      console.error('Processing error:', err);
      setError(err.message || 'Failed to process audio');
    } finally {
      setIsProcessing(false);
    }
  }, [callId]);

  const startListening = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.start();
      setIsListening(true);

      // Process audio every 5 seconds
      intervalRef.current = setInterval(() => {
        if (recorder.state === 'recording') {
          recorder.stop();
          setTimeout(() => {
            const blob = new Blob(chunksRef.current, { type: mimeType });
            chunksRef.current = [];
            processAudioChunk(blob);
            if (streamRef.current && streamRef.current.active) {
              try {
                const newRecorder = new MediaRecorder(streamRef.current, { mimeType });
                mediaRecorderRef.current = newRecorder;
                newRecorder.ondataavailable = (e) => {
                  if (e.data.size > 0) chunksRef.current.push(e.data);
                };
                newRecorder.start();
              } catch { /* stream may have ended */ }
            }
          }, 100);
        }
      }, 5000);
    } catch (err: any) {
      setError(err.message || 'Microphone access denied');
    }
  }, [processAudioChunk]);

  const stopListening = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setIsListening(false);

    // Process any remaining audio
    if (chunksRef.current.length > 0) {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
      chunksRef.current = [];
      processAudioChunk(blob);
    }
  }, [processAudioChunk]);

  const analyzeText = useCallback(async (text: string) => {
    if (!text.trim()) return;
    setIsProcessing(true);
    setError(null);

    try {
      const newSegment: TranscriptSegment = {
        text,
        timestamp: Date.now(),
        confidence: 0.99,
        speaker: 'text_input',
      };
      setTranscript(prev => [...prev, newSegment]);

      const res = await fetch(`${API_BASE}/analyze/transcript`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: text,
          language_code: 'auto',
          transcript_confidence: 0.99,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setRiskAssessment(data);
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Analysis failed (${res.status})`);
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
    } finally {
      setIsProcessing(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  return {
    isListening,
    isProcessing,
    transcript,
    riskAssessment,
    error,
    callId,
    startListening,
    stopListening,
    analyzeText,
  };
}
