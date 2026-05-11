import { useState, useRef, useEffect, useCallback } from "react";
import { useLocation, Link } from "wouter";
import VoxAINavigation from "@/components/VoxAINavigation";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { trpc } from "@/lib/trpc";
import { 
  Mic, 
  MicOff,
  Square, 
  Pause, 
  Play, 
  ArrowLeft,
  Volume2,
  VolumeX,
  AlertTriangle,
  CheckCircle,
  Zap,
  RotateCcw,
  Timer,
  Waves,
  Settings2,
  Save,
  Trash2,
  ChevronDown,
  FileAudio,
  Gauge,
  Download,
  FolderOpen,
  History,
  Clock,
  Sparkles
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// Recording states
type RecordingState = 'idle' | 'countdown' | 'recording' | 'paused' | 'stopped';

// Audio level classification
type LevelStatus = 'silent' | 'quiet' | 'good' | 'loud' | 'clipping';

function getLevelStatus(level: number): LevelStatus {
  if (level < 0.01) return 'silent';
  if (level < 0.1) return 'quiet';
  if (level < 0.7) return 'good';
  if (level < 0.9) return 'loud';
  return 'clipping';
}

function getLevelColor(status: LevelStatus): string {
  switch (status) {
    case 'silent': return 'text-gray-500';
    case 'quiet': return 'text-yellow-500';
    case 'good': return 'text-green-500';
    case 'loud': return 'text-orange-500';
    case 'clipping': return 'text-red-500';
  }
}

function getLevelMessage(status: LevelStatus): string {
  switch (status) {
    case 'silent': return 'No signal detected';
    case 'quiet': return 'Too quiet - move closer to mic';
    case 'good': return 'Perfect level';
    case 'loud': return 'Getting loud - back up slightly';
    case 'clipping': return 'Clipping! Reduce input level';
  }
}

export default function RecordingStudio() {
  const [, setLocation] = useLocation();
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [countdown, setCountdown] = useState(3);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [peakLevel, setPeakLevel] = useState(0);
  const [noiseFloor, setNoiseFloor] = useState(0);
  const [waveformData, setWaveformData] = useState<number[]>([]);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackTime, setPlaybackTime] = useState(0);
  
  // Gain and noise gate controls
  const [micGain, setMicGain] = useState(1.0); // 0.0 to 2.0
  const [noiseGateThreshold, setNoiseGateThreshold] = useState(0.02); // 0.0 to 0.2
  const [isGateOpen, setIsGateOpen] = useState(false);
  
  // Mic testing mode
  const [isMicTesting, setIsMicTesting] = useState(false);
  const [isMicActivated, setIsMicActivated] = useState(false);
  
  // Compressor/limiter controls
  const [compressorEnabled, setCompressorEnabled] = useState(true);
  const [compressorThreshold, setCompressorThreshold] = useState(-24); // dB
  const [compressorRatio, setCompressorRatio] = useState(4); // ratio
  
  // Audio format selection
  type AudioFormat = 'webm' | 'wav' | 'mp3';
  const [audioFormat, setAudioFormat] = useState<AudioFormat>('webm');
  
  // Presets
  interface RecordingPreset {
    name: string;
    micGain: number;
    noiseGateThreshold: number;
    compressorEnabled: boolean;
    compressorThreshold: number;
    compressorRatio: number;
  }
  const [presets, setPresets] = useState<RecordingPreset[]>(() => {
    const saved = localStorage.getItem('recordingPresets');
    return saved ? JSON.parse(saved) : [
      { name: 'Default', micGain: 1.0, noiseGateThreshold: 0.02, compressorEnabled: true, compressorThreshold: -24, compressorRatio: 4 },
      { name: 'Quiet Room', micGain: 1.5, noiseGateThreshold: 0.01, compressorEnabled: true, compressorThreshold: -20, compressorRatio: 3 },
      { name: 'Noisy Environment', micGain: 0.8, noiseGateThreshold: 0.08, compressorEnabled: true, compressorThreshold: -30, compressorRatio: 6 },
    ];
  });
  const [selectedPreset, setSelectedPreset] = useState<string>('Default');
  
  // Saving state
  const [isSaving, setIsSaving] = useState(false);
  const [showSaveSuccess, setShowSaveSuccess] = useState(false);
  const [savedRecordingInfo, setSavedRecordingInfo] = useState<{
    fileName: string;
    analysisId: number;
    duration: number;
  } | null>(null);
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  
  // tRPC mutation for saving recording
  const saveRecordingMutation = trpc.analysis.saveRecording.useMutation({
    onSuccess: (data) => {
      setIsSaving(false);
      setSavedRecordingInfo({
        fileName: `Recording_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.${audioFormat}`,
        analysisId: data.analysisId,
        duration: recordingTime,
      });
      setShowSaveSuccess(true);
      // Refetch recordings to update the history section
      refetchRecordings();
    },
    onError: (error) => {
      toast.error(`Failed to save: ${error.message}`);
      setIsSaving(false);
    },
  });

  // Fetch recent recordings for history section
  const { data: recentRecordings, refetch: refetchRecordings } = trpc.analysis.list.useQuery(
    { limit: 5 },
    { enabled: true }
  );

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const compressorNodeRef = useRef<DynamicsCompressorNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const animationFrameRef = useRef<number | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const playbackCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Initialize audio context and get microphone access
  const initAudio = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      streamRef.current = stream;

      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;

      const source = audioContext.createMediaStreamSource(stream);
      
      // Create gain node for mic gain control
      const gainNode = audioContext.createGain();
      gainNode.gain.value = micGain;
      gainNodeRef.current = gainNode;
      
      // Create compressor/limiter node
      const compressor = audioContext.createDynamicsCompressor();
      compressor.threshold.value = compressorThreshold;
      compressor.knee.value = 30;
      compressor.ratio.value = compressorRatio;
      compressor.attack.value = 0.003;
      compressor.release.value = 0.25;
      compressorNodeRef.current = compressor;
      
      // Connect: source -> gain -> compressor -> analyser
      source.connect(gainNode);
      if (compressorEnabled) {
        gainNode.connect(compressor);
        compressor.connect(analyser);
      } else {
        gainNode.connect(analyser);
      }

      // Start monitoring levels
      monitorLevels();

      // Measure initial noise floor
      setTimeout(() => {
        if (audioLevel > 0) {
          setNoiseFloor(audioLevel);
        }
      }, 1000);

      return true;
    } catch (error) {
      console.error('Failed to access microphone:', error);
      toast.error('Could not access microphone. Please check permissions.');
      return false;
    }
  }, [audioLevel]);

  // Monitor audio levels
  const monitorLevels = useCallback(() => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateLevels = () => {
      analyser.getByteTimeDomainData(dataArray);

      // Calculate RMS level
      let sum = 0;
      let peak = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const value = (dataArray[i] - 128) / 128;
        sum += value * value;
        peak = Math.max(peak, Math.abs(value));
      }
      const rms = Math.sqrt(sum / dataArray.length);
      
      // Apply gain to the displayed level
      const gainedRms = rms * micGain;
      setAudioLevel(gainedRms);
      setPeakLevel(prev => Math.max(prev * 0.95, peak * micGain)); // Slow decay for peak
      
      // Check noise gate status
      setIsGateOpen(gainedRms > noiseGateThreshold);

      // Update waveform data for visualization (during recording, mic testing, or when mic is activated)
      if (recordingState === 'recording' || isMicTesting || isMicActivated) {
        const samples = Array.from(dataArray).map(v => (v - 128) / 128 * micGain);
        setWaveformData(prev => {
          const newData = [...prev, ...samples.slice(0, 50)];
          // Keep last 500 samples for display
          return newData.slice(-500);
        });
      }

      animationFrameRef.current = requestAnimationFrame(updateLevels);
    };

    updateLevels();
  }, [recordingState, isMicTesting, isMicActivated, micGain, noiseGateThreshold]);

  // Activate microphone (required before recording)
  const activateMicrophone = async () => {
    const initialized = await initAudio();
    if (!initialized) return;
    
    setIsMicActivated(true);
    setIsMicTesting(true);
    setWaveformData([]);
    setPeakLevel(0);
    toast.success('Microphone activated - check your levels!');
  };

  // Start mic testing mode (activate mic without recording)
  const startMicTest = async () => {
    await activateMicrophone();
  };

  // Stop mic testing mode (deactivate microphone)
  const stopMicTest = () => {
    setIsMicTesting(false);
    setIsMicActivated(false);
    setWaveformData([]);
    
    // Clean up audio resources
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    toast.info('Mic test stopped');
  };

  // Start countdown and then recording
  const startRecording = async () => {
    // If mic not activated, activate it first
    if (!isMicActivated) {
      const initialized = await initAudio();
      if (!initialized) return;
      setIsMicActivated(true);
    }
    
    // Stop mic testing mode but keep mic active
    setIsMicTesting(false);

    setRecordingState('countdown');
    setCountdown(3);
    setWaveformData([]);
    setRecordedBlob(null);
    setRecordedUrl(null);
    setPeakLevel(0);

    // Countdown
    let count = 3;
    const countdownInterval = setInterval(() => {
      count--;
      setCountdown(count);
      if (count === 0) {
        clearInterval(countdownInterval);
        beginRecording();
      }
    }, 1000);
  };

  // Actually begin recording after countdown
  const beginRecording = () => {
    if (!streamRef.current) return;

    chunksRef.current = [];
    const mediaRecorder = new MediaRecorder(streamRef.current, {
      mimeType: 'audio/webm;codecs=opus'
    });
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      // Use the correct MIME type based on selected format
      const mimeTypes: Record<string, string> = {
        webm: 'audio/webm',
        wav: 'audio/wav',
        mp3: 'audio/mpeg',
      };
      const mimeType = mimeTypes[audioFormat] || 'audio/webm';
      const blob = new Blob(chunksRef.current, { type: mimeType });
      console.log('Recording stopped, blob size:', blob.size, 'type:', blob.type);
      setRecordedBlob(blob);
      setRecordedUrl(URL.createObjectURL(blob));
    };

    mediaRecorder.start(100); // Collect data every 100ms
    setRecordingState('recording');
    setRecordingTime(0);

    // Start timer
    timerRef.current = setInterval(() => {
      setRecordingTime(prev => prev + 1);
    }, 1000);

    toast.success('Recording started!');
  };

  // Pause recording
  const pauseRecording = () => {
    if (mediaRecorderRef.current && recordingState === 'recording') {
      mediaRecorderRef.current.pause();
      setRecordingState('paused');
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  // Resume recording
  const resumeRecording = () => {
    if (mediaRecorderRef.current && recordingState === 'paused') {
      mediaRecorderRef.current.resume();
      setRecordingState('recording');
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    setRecordingState('stopped');
    toast.success('Recording stopped!');
  };

  // Reset and start over
  const resetRecording = () => {
    setRecordingState('idle');
    setRecordingTime(0);
    setWaveformData([]);
    setRecordedBlob(null);
    setRecordedUrl(null);
    setAudioLevel(0);
    setPeakLevel(0);
    setPlaybackTime(0);
    setIsPlaying(false);
  };

  // Play recorded audio
  const togglePlayback = () => {
    if (!audioRef.current || !recordedUrl) return;
    
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  // Save recording to library
  const saveToLibrary = async () => {
    if (!recordedBlob) {
      toast.error('No recording to save');
      return;
    }
    
    if (isSaving) return; // Prevent double-click
    setIsSaving(true);
    toast.info('Saving recording to library...');
    
    // Convert blob to base64
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const dataUrl = reader.result as string;
        if (!dataUrl || !dataUrl.includes(',')) {
          throw new Error('Invalid recording data');
        }
        const base64Data = dataUrl.split(',')[1]; // Remove data URL prefix
        if (!base64Data || base64Data.length < 100) {
          throw new Error('Recording data is empty or corrupted');
        }
        const fileName = `Recording_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.${audioFormat}`;
        
        await saveRecordingMutation.mutateAsync({
          fileName,
          fileFormat: audioFormat,
          fileSizeBytes: recordedBlob.size,
          fileBase64: base64Data,
          durationSeconds: recordingTime,
        });
      } catch (error) {
        console.error('Failed to save recording:', error);
        toast.error('Failed to save recording');
        setIsSaving(false);
      }
    };
    reader.onerror = () => {
      console.error('FileReader error while saving');
      toast.error('Failed to read recording data');
      setIsSaving(false);
    };
    reader.readAsDataURL(recordedBlob);
  };

  // Send to analysis (for immediate analysis)
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const sendToAnalysis = () => {
    if (!recordedBlob) {
      toast.error('No recording to analyze');
      return;
    }
    
    if (isAnalyzing) return; // Prevent double-click
    setIsAnalyzing(true);
    toast.info('Preparing recording for analysis...');

    // Store the blob in sessionStorage for the Analyze page to pick up
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const base64Data = reader.result as string;
        // Check if data is valid
        if (!base64Data || base64Data.length < 100) {
          throw new Error('Recording data is empty or corrupted');
        }
        sessionStorage.setItem('recordedAudio', base64Data);
        sessionStorage.setItem('recordedAudioName', `Recording_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.${audioFormat}`);
        toast.success('Sending to analysis...');
        setLocation('/analyze?fromRecording=true');
      } catch (error) {
        console.error('Failed to prepare recording:', error);
        toast.error('Failed to prepare recording for analysis');
        setIsAnalyzing(false);
      }
    };
    reader.onerror = () => {
      console.error('FileReader error');
      toast.error('Failed to read recording data');
      setIsAnalyzing(false);
    };
    reader.readAsDataURL(recordedBlob);
  };

  // Save current settings as a new preset
  const savePreset = (name: string) => {
    const newPreset: RecordingPreset = {
      name,
      micGain,
      noiseGateThreshold,
      compressorEnabled,
      compressorThreshold,
      compressorRatio,
    };
    const updatedPresets = [...presets.filter(p => p.name !== name), newPreset];
    setPresets(updatedPresets);
    localStorage.setItem('recordingPresets', JSON.stringify(updatedPresets));
    setSelectedPreset(name);
    toast.success(`Preset "${name}" saved!`);
  };

  // Load a preset
  const loadPreset = (name: string) => {
    const preset = presets.find(p => p.name === name);
    if (!preset) return;
    
    setMicGain(preset.micGain);
    setNoiseGateThreshold(preset.noiseGateThreshold);
    setCompressorEnabled(preset.compressorEnabled);
    setCompressorThreshold(preset.compressorThreshold);
    setCompressorRatio(preset.compressorRatio);
    setSelectedPreset(name);
    
    // Update audio nodes if they exist
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = preset.micGain;
    }
    if (compressorNodeRef.current) {
      compressorNodeRef.current.threshold.value = preset.compressorThreshold;
      compressorNodeRef.current.ratio.value = preset.compressorRatio;
    }
    
    toast.success(`Loaded preset "${name}"`);
  };

  // Delete a preset
  const deletePreset = (name: string) => {
    if (name === 'Default') {
      toast.error('Cannot delete default preset');
      return;
    }
    const updatedPresets = presets.filter(p => p.name !== name);
    setPresets(updatedPresets);
    localStorage.setItem('recordingPresets', JSON.stringify(updatedPresets));
    if (selectedPreset === name) {
      setSelectedPreset('Default');
      loadPreset('Default');
    }
    toast.success(`Preset "${name}" deleted`);
  };

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Draw waveform on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || waveformData.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerY = height / 2;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = recordingState === 'recording' 
      ? 'rgba(0, 255, 200, 0.8)' 
      : (isMicTesting || isMicActivated)
        ? 'rgba(255, 200, 0, 0.8)'
        : 'rgba(100, 100, 100, 0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const sliceWidth = width / waveformData.length;
    let x = 0;

    for (let i = 0; i < waveformData.length; i++) {
      const y = centerY + waveformData[i] * centerY * 0.8;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      x += sliceWidth;
    }

    ctx.stroke();
  }, [waveformData, recordingState, isMicTesting, isMicActivated]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const levelStatus = getLevelStatus(audioLevel);

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Aurora background effect */}
      <div className="aurora-bg" />
      
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--holo-cyan)_0%,_transparent_50%)] opacity-5" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_var(--holo-purple)_0%,_transparent_50%)] opacity-5" />
        <div className="grid-bg absolute inset-0" />
      </div>
      
      {/* Circuit pattern overlay */}
      <div className="circuit-pattern" />

      {/* Navigation */}
      <VoxAINavigation />

      {/* Main Content */}
      <main className="container pt-24 pb-8 relative z-10">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => setLocation('/analyze')}
          className="mb-6 text-muted-foreground hover:text-white"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Analyze
        </Button>

        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-[var(--holo-cyan)] to-[var(--holo-purple)] bg-clip-text text-transparent">
              Recording Studio
            </h1>
            <p className="text-muted-foreground">
              Professional vocal recording with real-time monitoring
            </p>
          </div>

          {/* Main Recording Interface */}
          <div className="holo-card p-6 space-y-6">
            
            {/* Countdown Overlay */}
            {recordingState === 'countdown' && (
              <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-50 rounded-2xl">
                <div className="text-center">
                  <div className="text-8xl font-bold text-[var(--holo-cyan)] animate-pulse">
                    {countdown}
                  </div>
                  <p className="text-xl text-muted-foreground mt-4">Get ready...</p>
                </div>
              </div>
            )}

            {/* Level Meters Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* VU Meter */}
              <div className="bg-black/30 rounded-xl p-4 border border-border/30">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-muted-foreground">Input Level</span>
                  <span className={cn("text-sm font-medium", getLevelColor(levelStatus))}>
                    {getLevelMessage(levelStatus)}
                  </span>
                </div>
                
                {/* VU Meter Bar */}
                <div className="relative h-8 bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                  {/* Level segments */}
                  <div className="absolute inset-0 flex">
                    {Array.from({ length: 20 }).map((_, i) => (
                      <div
                        key={i}
                        className={cn(
                          "flex-1 border-r border-gray-800 transition-all duration-75",
                          audioLevel * 20 > i
                            ? i < 12 ? 'bg-green-500' 
                              : i < 16 ? 'bg-yellow-500' 
                              : i < 18 ? 'bg-orange-500'
                              : 'bg-red-500'
                            : 'bg-gray-800'
                        )}
                      />
                    ))}
                  </div>
                  {/* Peak indicator */}
                  <div 
                    className="absolute top-0 bottom-0 w-1 bg-white/80 transition-all duration-150"
                    style={{ left: `${Math.min(peakLevel * 100, 100)}%` }}
                  />
                </div>

                {/* Level labels */}
                <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                  <span>-∞</span>
                  <span>-12dB</span>
                  <span>-6dB</span>
                  <span>0dB</span>
                </div>
              </div>

              {/* Noise Floor Indicator */}
              <div className="bg-black/30 rounded-xl p-4 border border-border/30">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-muted-foreground">Environment</span>
                  {noiseFloor > 0.1 ? (
                    <span className="text-sm font-medium text-yellow-500 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Noisy
                    </span>
                  ) : (
                    <span className="text-sm font-medium text-green-500 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Quiet
                    </span>
                  )}
                </div>

                {/* Noise visualization */}
                <div className="relative h-8 bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                  <div 
                    className={cn(
                      "absolute inset-y-0 left-0 transition-all duration-300",
                      noiseFloor > 0.1 ? 'bg-yellow-500/50' : 'bg-green-500/50'
                    )}
                    style={{ width: `${Math.min(noiseFloor * 200, 100)}%` }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center text-xs text-white/70">
                    Ambient Noise: {(noiseFloor * 100).toFixed(0)}%
                  </div>
                </div>

                <p className="text-xs text-muted-foreground mt-2">
                  {noiseFloor > 0.1 
                    ? 'Consider moving to a quieter location'
                    : 'Environment is good for recording'}
                </p>
              </div>
            </div>

            {/* Mic Gain & Noise Gate Controls */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Mic Gain Control */}
              <div className="bg-black/30 rounded-xl p-4 border border-border/30">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-muted-foreground">Mic Gain</span>
                  <span className="text-sm font-mono text-[var(--holo-cyan)]">
                    {micGain < 1 ? `-${((1 - micGain) * 12).toFixed(1)}dB` : `+${((micGain - 1) * 12).toFixed(1)}dB`}
                  </span>
                </div>
                
                {/* Gain Slider */}
                <div className="relative">
                  <input
                    type="range"
                    min="0"
                    max="200"
                    value={micGain * 100}
                    onChange={(e) => {
                      const newGain = parseInt(e.target.value) / 100;
                      setMicGain(newGain);
                      if (gainNodeRef.current) {
                        gainNodeRef.current.gain.value = newGain;
                      }
                    }}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[var(--holo-cyan)]"
                  />
                  <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                    <span>-12dB</span>
                    <span className="text-[var(--holo-cyan)]">0dB</span>
                    <span>+12dB</span>
                  </div>
                </div>
                
                <p className="text-xs text-muted-foreground mt-2">
                  Adjust input sensitivity. Keep at 0dB unless needed.
                </p>
              </div>

              {/* Noise Gate Control */}
              <div className="bg-black/30 rounded-xl p-4 border border-border/30">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-muted-foreground">Noise Gate</span>
                  <span className={cn(
                    "text-sm font-medium flex items-center gap-1.5",
                    isGateOpen ? "text-green-500" : "text-gray-500"
                  )}>
                    <div className={cn(
                      "w-2 h-2 rounded-full transition-colors",
                      isGateOpen ? "bg-green-500 animate-pulse" : "bg-gray-600"
                    )} />
                    {isGateOpen ? "OPEN" : "CLOSED"}
                  </span>
                </div>
                
                {/* Gate Threshold Slider with Meter */}
                <div className="relative h-8 bg-gray-900 rounded-lg overflow-hidden border border-gray-700 mb-2">
                  {/* Current audio level bar */}
                  <div 
                    className={cn(
                      "absolute inset-y-0 left-0 transition-all duration-75",
                      isGateOpen ? "bg-green-500/60" : "bg-gray-600/40"
                    )}
                    style={{ width: `${Math.min(audioLevel * 500, 100)}%` }}
                  />
                  {/* Threshold line */}
                  <div 
                    className="absolute top-0 bottom-0 w-0.5 bg-[var(--holo-orange)] z-10"
                    style={{ left: `${noiseGateThreshold * 500}%` }}
                  />
                  {/* Threshold label */}
                  <div 
                    className="absolute top-1 text-[10px] text-[var(--holo-orange)] font-mono z-10 transform -translate-x-1/2"
                    style={{ left: `${noiseGateThreshold * 500}%` }}
                  >
                    GATE
                  </div>
                </div>
                
                {/* Threshold Slider */}
                <input
                  type="range"
                  min="0"
                  max="20"
                  value={noiseGateThreshold * 100}
                  onChange={(e) => setNoiseGateThreshold(parseInt(e.target.value) / 100)}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[var(--holo-orange)]"
                />
                <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                  <span>Off</span>
                  <span>Threshold: {(noiseGateThreshold * 100).toFixed(0)}%</span>
                  <span>Max</span>
                </div>
                
                <p className="text-xs text-muted-foreground mt-2">
                  Audio below threshold is muted. Adjust to filter background noise.
                </p>
              </div>
            </div>

            {/* Compressor/Limiter & Presets Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Compressor/Limiter Control */}
              <div className="bg-black/30 rounded-xl p-4 border border-border/30">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-[var(--holo-pink)]" />
                    <span className="text-sm font-medium text-muted-foreground">Compressor/Limiter</span>
                  </div>
                  <button
                    onClick={() => setCompressorEnabled(!compressorEnabled)}
                    className={cn(
                      "px-2 py-1 text-xs rounded font-medium transition-colors",
                      compressorEnabled 
                        ? "bg-[var(--holo-pink)]/20 text-[var(--holo-pink)] border border-[var(--holo-pink)]/30" 
                        : "bg-gray-800 text-gray-500 border border-gray-700"
                    )}
                  >
                    {compressorEnabled ? "ON" : "OFF"}
                  </button>
                </div>
                
                {compressorEnabled && (
                  <div className="space-y-3">
                    {/* Threshold */}
                    <div>
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>Threshold</span>
                        <span className="font-mono">{compressorThreshold}dB</span>
                      </div>
                      <input
                        type="range"
                        min="-60"
                        max="0"
                        value={compressorThreshold}
                        onChange={(e) => {
                          const val = parseInt(e.target.value);
                          setCompressorThreshold(val);
                          if (compressorNodeRef.current) {
                            compressorNodeRef.current.threshold.value = val;
                          }
                        }}
                        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[var(--holo-pink)]"
                      />
                    </div>
                    {/* Ratio */}
                    <div>
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>Ratio</span>
                        <span className="font-mono">{compressorRatio}:1</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="20"
                        value={compressorRatio}
                        onChange={(e) => {
                          const val = parseInt(e.target.value);
                          setCompressorRatio(val);
                          if (compressorNodeRef.current) {
                            compressorNodeRef.current.ratio.value = val;
                          }
                        }}
                        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[var(--holo-pink)]"
                      />
                    </div>
                  </div>
                )}
                
                <p className="text-xs text-muted-foreground mt-2">
                  {compressorEnabled ? "Automatically reduces peaks to prevent clipping." : "Enable to prevent audio clipping."}
                </p>
              </div>

              {/* Presets & Format Selection */}
              <div className="bg-black/30 rounded-xl p-4 border border-border/30">
                <div className="flex items-center gap-2 mb-3">
                  <Settings2 className="w-4 h-4 text-[var(--holo-green)]" />
                  <span className="text-sm font-medium text-muted-foreground">Presets & Format</span>
                </div>
                
                {/* Preset Selector */}
                <div className="mb-3">
                  <label className="text-xs text-muted-foreground mb-1 block">Load Preset</label>
                  <div className="flex gap-2">
                    <select
                      value={selectedPreset}
                      onChange={(e) => loadPreset(e.target.value)}
                      className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[var(--holo-green)]"
                    >
                      {presets.map(p => (
                        <option key={p.name} value={p.name}>{p.name}</option>
                      ))}
                    </select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const name = prompt('Enter preset name:');
                        if (name) savePreset(name);
                      }}
                      className="border-[var(--holo-green)]/30 hover:border-[var(--holo-green)]"
                    >
                      <Save className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                
                {/* Audio Format Selection */}
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Output Format</label>
                  <div className="flex gap-2">
                    {(['webm', 'wav', 'mp3'] as const).map(format => (
                      <button
                        key={format}
                        onClick={() => setAudioFormat(format)}
                        className={cn(
                          "flex-1 px-3 py-2 text-xs rounded-lg font-medium transition-colors flex items-center justify-center gap-1",
                          audioFormat === format
                            ? "bg-[var(--holo-green)]/20 text-[var(--holo-green)] border border-[var(--holo-green)]/30"
                            : "bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600"
                        )}
                      >
                        <FileAudio className="w-3 h-3" />
                        {format.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                
                <p className="text-xs text-muted-foreground mt-2">
                  WebM: Smallest size | WAV: Lossless | MP3: Universal
                </p>
              </div>
            </div>

            {/* Waveform Display */}
            <div className="bg-black/50 rounded-xl p-4 border border-border/30">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Waves className="w-4 h-4 text-[var(--holo-cyan)]" />
                  <span className="text-sm font-medium">Waveform</span>
                </div>
                {isMicTesting && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                    <span className="text-sm text-yellow-400">Testing Mic</span>
                  </div>
                )}
                {recordingState === 'recording' && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <span className="text-sm text-red-400">Recording</span>
                  </div>
                )}
              </div>
              
              <canvas
                ref={canvasRef}
                width={800}
                height={150}
                className="w-full h-32 rounded-lg bg-gray-900/50"
              />
            </div>

            {/* Recording Timer */}
            <div className="text-center">
              <div className="inline-flex items-center gap-3 bg-black/30 rounded-full px-6 py-3 border border-border/30">
                <Timer className="w-5 h-5 text-[var(--holo-cyan)]" />
                <span className="text-3xl font-mono font-bold text-white">
                  {formatTime(recordingTime)}
                </span>
                {recordingState === 'recording' && (
                  <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                )}
              </div>
            </div>

            {/* Transport Controls */}
            <div className="flex flex-col items-center gap-6">
              {/* Step 1: Activate Microphone (when mic not activated) */}
              {recordingState === 'idle' && !isMicActivated && (
                <div className="flex flex-col items-center gap-4">
                  <Button
                    onClick={activateMicrophone}
                    size="lg"
                    className="w-24 h-24 rounded-full bg-gradient-to-br from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white shadow-lg shadow-yellow-500/30"
                  >
                    <Volume2 className="w-10 h-10" />
                  </Button>
                  <span className="text-sm text-yellow-400 font-medium">Tap to Activate Microphone</span>
                  <p className="text-xs text-muted-foreground text-center max-w-xs">
                    Activate your mic first to check levels and adjust settings before recording
                  </p>
                </div>
              )}
              
              {/* Step 2: Mic Activated - Show levels and Record button */}
              {recordingState === 'idle' && isMicActivated && (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex items-center gap-2 text-sm text-green-400">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span>Microphone Active - Check your levels</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <Button
                      onClick={stopMicTest}
                      size="lg"
                      variant="outline"
                      className="w-16 h-16 rounded-full border-gray-500/50 hover:bg-gray-500/20"
                      title="Deactivate Mic"
                    >
                      <MicOff className="w-6 h-6 text-gray-400" />
                    </Button>
                    <Button
                      onClick={startRecording}
                      size="lg"
                      className="w-24 h-24 rounded-full bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-500/30 animate-pulse"
                    >
                      <Mic className="w-10 h-10" />
                    </Button>
                  </div>
                  <span className="text-sm text-red-400 font-medium">Tap to Start Recording</span>
                </div>
              )}

              {recordingState === 'recording' && (
                <div className="flex items-center gap-4">
                  <Button
                    onClick={pauseRecording}
                    size="lg"
                    variant="outline"
                    className="w-16 h-16 rounded-full border-yellow-500/50 hover:bg-yellow-500/20"
                  >
                    <Pause className="w-6 h-6" />
                  </Button>
                  <Button
                    onClick={stopRecording}
                    size="lg"
                    className="w-20 h-20 rounded-full bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-500/30"
                  >
                    <Square className="w-8 h-8" />
                  </Button>
                </div>
              )}

              {recordingState === 'paused' && (
                <div className="flex items-center gap-4">
                  <Button
                    onClick={resumeRecording}
                    size="lg"
                    variant="outline"
                    className="w-16 h-16 rounded-full border-green-500/50 hover:bg-green-500/20"
                  >
                    <Play className="w-6 h-6" />
                  </Button>
                  <Button
                    onClick={stopRecording}
                    size="lg"
                    className="w-20 h-20 rounded-full bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-500/30"
                  >
                    <Square className="w-8 h-8" />
                  </Button>
                </div>
              )}

              {recordingState === 'stopped' && recordedUrl && (
                <div className="flex items-center gap-4">
                  <Button
                    onClick={resetRecording}
                    size="lg"
                    variant="outline"
                    className="w-16 h-16 rounded-full border-gray-500/50 hover:bg-gray-500/20"
                    title="Re-record"
                  >
                    <RotateCcw className="w-6 h-6" />
                  </Button>
                  <Button
                    onClick={togglePlayback}
                    size="lg"
                    className={cn(
                      "w-16 h-16 rounded-full shadow-lg",
                      isPlaying 
                        ? "bg-yellow-600 hover:bg-yellow-500 shadow-yellow-500/30"
                        : "bg-green-600 hover:bg-green-500 shadow-green-500/30"
                    )}
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                  </Button>
                  <Button
                    onClick={saveToLibrary}
                    size="lg"
                    disabled={isSaving}
                    className="w-20 h-20 rounded-full bg-[var(--holo-purple)] hover:bg-[var(--holo-purple)]/80 shadow-lg shadow-purple-500/30"
                    title="Save to Library"
                  >
                    {isSaving ? (
                      <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <FolderOpen className="w-8 h-8" />
                    )}
                  </Button>
                  <Button
                    onClick={sendToAnalysis}
                    size="lg"
                    disabled={isAnalyzing}
                    className="w-16 h-16 rounded-full bg-[var(--holo-cyan)] hover:bg-[var(--holo-cyan)]/80 shadow-lg shadow-cyan-500/30"
                    title="Analyze Now"
                  >
                    {isAnalyzing ? (
                      <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Zap className="w-6 h-6" />
                    )}
                  </Button>
                </div>
              )}
            </div>

            {/* Control Labels */}
            <div className="flex items-center justify-center gap-8 text-xs text-muted-foreground">
              {recordingState === 'recording' && (
                <>
                  <span>Pause</span>
                  <span>Stop</span>
                </>
              )}
              {recordingState === 'paused' && (
                <>
                  <span>Resume</span>
                  <span>Stop</span>
                </>
              )}
              {recordingState === 'stopped' && recordedUrl && (
                <>
                  <span>Re-record</span>
                  <span>{isPlaying ? 'Pause' : 'Play'}</span>
                  <span>Save</span>
                  <span>Analyze</span>
                </>
              )}
            </div>

            {/* Hidden audio element for playback */}
            {recordedUrl && (
              <audio
                ref={audioRef}
                src={recordedUrl}
                onEnded={() => setIsPlaying(false)}
                onTimeUpdate={(e) => setPlaybackTime(Math.floor(e.currentTarget.currentTime))}
              />
            )}
          </div>

          {/* Tips Section */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-black/20 rounded-xl p-4 border border-border/20">
              <div className="flex items-center gap-2 mb-2">
                <Volume2 className="w-4 h-4 text-green-400" />
                <span className="text-sm font-medium">Optimal Level</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Keep the meter in the green zone for best quality
              </p>
            </div>
            <div className="bg-black/20 rounded-xl p-4 border border-border/20">
              <div className="flex items-center gap-2 mb-2">
                <VolumeX className="w-4 h-4 text-yellow-400" />
                <span className="text-sm font-medium">Reduce Noise</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Find a quiet space and minimize background sounds
              </p>
            </div>
            <div className="bg-black/20 rounded-xl p-4 border border-border/20">
              <div className="flex items-center gap-2 mb-2">
                <Mic className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-medium">Mic Distance</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Stay 6-12 inches from your microphone
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Recent Recordings Section */}
      {recentRecordings && recentRecordings.analyses && recentRecordings.analyses.length > 0 && (
        <div className="max-w-4xl mx-auto px-4 pb-8">
          <div className="holo-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <History className="w-5 h-5 text-[var(--holo-cyan)]" />
                Recent Recordings
              </h3>
              <Link href="/profile">
                <Button variant="ghost" size="sm" className="text-[var(--holo-cyan)]">
                  View All
                </Button>
              </Link>
            </div>
            <div className="space-y-2">
              {recentRecordings.analyses.slice(0, 5).map((recording: any) => (
                <Link key={recording.id} href={`/analysis/${recording.id}`}>
                  <div className="flex items-center justify-between p-3 bg-black/30 rounded-lg border border-border/20 hover:border-[var(--holo-cyan)]/30 transition-colors cursor-pointer">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--holo-cyan)]/20 to-purple-500/20 flex items-center justify-center">
                        <FileAudio className="w-5 h-5 text-[var(--holo-cyan)]" />
                      </div>
                      <div>
                        <p className="text-sm font-medium truncate max-w-[200px]">{recording.fileName}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(recording.createdAt).toLocaleDateString()}</span>
                          {recording.durationSeconds && (
                            <>
                              <span>•</span>
                              <span>{Math.floor(Number(recording.durationSeconds) / 60)}:{String(Math.floor(Number(recording.durationSeconds) % 60)).padStart(2, '0')}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {recording.status === 'uploading' ? (
                        <span className="text-xs px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-400">Ready to Analyze</span>
                      ) : recording.status === 'complete' ? (
                        <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400">Analyzed</span>
                      ) : (
                        <span className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-400">{recording.status}</span>
                      )}
                      {recording.status === 'uploading' && (
                        <Link href={`/analyze?startAnalysis=${recording.id}`}>
                          <Button size="sm" className="bg-[var(--holo-cyan)] hover:bg-[var(--holo-cyan)]/80 h-7 px-2">
                            <Sparkles className="w-3 h-3 mr-1" />
                            Analyze
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Save Success Dialog */}
      <Dialog open={showSaveSuccess} onOpenChange={setShowSaveSuccess}>
        <DialogContent className="bg-[#0a1628] border-border/30 max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-400" />
              </div>
              Recording Saved!
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Your recording has been saved to your library and is ready for analysis.
            </DialogDescription>
          </DialogHeader>
          
          {savedRecordingInfo && (
            <div className="space-y-4 py-4">
              {/* Recording Info */}
              <div className="bg-black/30 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">File Name</span>
                  <span className="font-mono text-xs truncate max-w-[200px]">{savedRecordingInfo.fileName}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Duration</span>
                  <span>{Math.floor(savedRecordingInfo.duration / 60)}:{(savedRecordingInfo.duration % 60).toString().padStart(2, '0')}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Format</span>
                  <span className="uppercase">{audioFormat}</span>
                </div>
              </div>
              
              {/* Playback Preview */}
              <div className="bg-black/30 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium">Preview Recording</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (previewAudioRef.current) {
                        if (isPlayingPreview) {
                          previewAudioRef.current.pause();
                        } else {
                          previewAudioRef.current.play();
                        }
                        setIsPlayingPreview(!isPlayingPreview);
                      }
                    }}
                    className="h-8 px-3"
                  >
                    {isPlayingPreview ? (
                      <><Pause className="w-4 h-4 mr-1" /> Pause</>
                    ) : (
                      <><Play className="w-4 h-4 mr-1" /> Play</>
                    )}
                  </Button>
                </div>
                <div className="h-12 bg-black/40 rounded-lg flex items-center justify-center">
                  <Waves className={cn(
                    "w-24 h-8",
                    isPlayingPreview ? "text-cyan-400 animate-pulse" : "text-muted-foreground/50"
                  )} />
                </div>
                {recordedUrl && (
                  <audio
                    ref={previewAudioRef}
                    src={recordedUrl}
                    onEnded={() => setIsPlayingPreview(false)}
                  />
                )}
              </div>
            </div>
          )}
          
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowSaveSuccess(false);
                resetRecording();
              }}
              className="flex-1"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Record Another
            </Button>
            <Button
              onClick={() => {
                setShowSaveSuccess(false);
                setLocation('/profile');
              }}
              className="flex-1 bg-[var(--holo-cyan)] hover:bg-[var(--holo-cyan)]/80"
            >
              <FolderOpen className="w-4 h-4 mr-2" />
              View in Library
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
