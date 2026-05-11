import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { 
  Wand2, 
  Play, 
  Pause, 
  Volume2,
  VolumeX,
  Check,
  X,
  Loader2,
  ArrowLeft,
  Sparkles,
  Music,
  Download,
  RotateCcw
} from "lucide-react";
import { Link, useLocation, useParams } from "wouter";
import VoxAINavigation from "@/components/VoxAINavigation";
import { getLoginUrl } from "@/const";
import { toast } from "sonner";

interface PolishSettings {
  eq: {
    bass: number;
    mid: number;
    treble: number;
  };
  compression: number;
  reverb: number;
  deEsser: number;
  normalize: boolean;
}

export default function MagicPolish() {
  const { id } = useParams<{ id: string }>();
  const analysisId = parseInt(id || "0");
  const { user, loading: authLoading, isAuthenticated } = useAuth();
  const [, setLocation] = useLocation();
  
  // Audio state
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPolished, setIsPolished] = useState(false);
  const [playingOriginal, setPlayingOriginal] = useState(false);
  const [playingPolished, setPlayingPolished] = useState(false);
  const [originalProgress, setOriginalProgress] = useState(0);
  const [polishedProgress, setPolishedProgress] = useState(0);
  const [originalMuted, setOriginalMuted] = useState(false);
  const [polishedMuted, setPolishedMuted] = useState(false);
  
  const originalAudioRef = useRef<HTMLAudioElement | null>(null);
  const polishedAudioRef = useRef<HTMLAudioElement | null>(null);
  
  // Polish settings
  const [settings, setSettings] = useState<PolishSettings>({
    eq: { bass: 0, mid: 0, treble: 2 },
    compression: 30,
    reverb: 15,
    deEsser: 20,
    normalize: true,
  });

  // Fetch analysis data
  const { data: analysis, isLoading } = trpc.analysis.get.useQuery(
    { id: analysisId },
    { enabled: isAuthenticated && analysisId > 0 }
  );

  // Polish mutation
  const polishMutation = trpc.analysis.applyPolish.useMutation({
    onSuccess: (result) => {
      setIsPolished(true);
      setIsProcessing(false);
      toast.success("Magic Polish applied!");
    },
    onError: (error) => {
      setIsProcessing(false);
      toast.error(error.message || "Failed to apply polish");
    },
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      window.location.href = getLoginUrl();
    }
  }, [authLoading, isAuthenticated]);

  // Setup audio elements
  useEffect(() => {
    if (analysis?.audioUrl) {
      originalAudioRef.current = new Audio(analysis.audioUrl);
      originalAudioRef.current.ontimeupdate = () => {
        if (originalAudioRef.current) {
          const progress = (originalAudioRef.current.currentTime / originalAudioRef.current.duration) * 100;
          setOriginalProgress(progress || 0);
        }
      };
      originalAudioRef.current.onended = () => setPlayingOriginal(false);
    }
    
    return () => {
      if (originalAudioRef.current) {
        originalAudioRef.current.pause();
        originalAudioRef.current = null;
      }
      if (polishedAudioRef.current) {
        polishedAudioRef.current.pause();
        polishedAudioRef.current = null;
      }
    };
  }, [analysis?.audioUrl]);

  // Setup polished audio when available
  useEffect(() => {
    if (analysis?.polishedAudioUrl) {
      polishedAudioRef.current = new Audio(analysis.polishedAudioUrl);
      polishedAudioRef.current.ontimeupdate = () => {
        if (polishedAudioRef.current) {
          const progress = (polishedAudioRef.current.currentTime / polishedAudioRef.current.duration) * 100;
          setPolishedProgress(progress || 0);
        }
      };
      polishedAudioRef.current.onended = () => setPlayingPolished(false);
      setIsPolished(true);
    }
  }, [analysis?.polishedAudioUrl]);

  const toggleOriginalPlay = () => {
    if (!originalAudioRef.current) return;
    
    // Pause polished if playing
    if (playingPolished && polishedAudioRef.current) {
      polishedAudioRef.current.pause();
      setPlayingPolished(false);
    }
    
    if (playingOriginal) {
      originalAudioRef.current.pause();
      setPlayingOriginal(false);
    } else {
      originalAudioRef.current.play();
      setPlayingOriginal(true);
    }
  };

  const togglePolishedPlay = () => {
    if (!polishedAudioRef.current) return;
    
    // Pause original if playing
    if (playingOriginal && originalAudioRef.current) {
      originalAudioRef.current.pause();
      setPlayingOriginal(false);
    }
    
    if (playingPolished) {
      polishedAudioRef.current.pause();
      setPlayingPolished(false);
    } else {
      polishedAudioRef.current.play();
      setPlayingPolished(true);
    }
  };

  const handleApplyPolish = async () => {
    if (!analysis) return;
    
    setIsProcessing(true);
    
    try {
      await polishMutation.mutateAsync({
        analysisId,
        settings: {
          eqBass: settings.eq.bass,
          eqMid: settings.eq.mid,
          eqTreble: settings.eq.treble,
          compression: settings.compression,
          reverb: settings.reverb,
          deEsser: settings.deEsser,
          normalize: settings.normalize,
        },
      });
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleConfirmPolish = () => {
    toast.success("Polished version saved!");
    setLocation("/history");
  };

  const handleDownloadPolished = () => {
    if (analysis?.polishedAudioUrl) {
      const a = document.createElement("a");
      a.href = analysis.polishedAudioUrl;
      a.download = `polished-${analysis.fileName || "recording"}.mp3`;
      a.click();
      toast.success("Download started");
    }
  };

  const handleReset = () => {
    setSettings({
      eq: { bass: 0, mid: 0, treble: 2 },
      compression: 30,
      reverb: 15,
      deEsser: 20,
      normalize: true,
    });
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--holo-purple)]" />
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-background">
        <VoxAINavigation />
        <div className="pt-20 px-4 text-center">
          <p className="text-muted-foreground">Recording not found</p>
          <Link href="/history">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to History
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <VoxAINavigation />
      
      <div className="pt-16 pb-8 px-4 max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/history">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Wand2 className="w-6 h-6 text-[var(--holo-purple)]" />
              Magic Polish
            </h1>
            <p className="text-sm text-muted-foreground">{analysis.fileName || "Recording"}</p>
          </div>
        </div>

        {/* Before/After Comparison */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Original Audio */}
          <Card className="p-6 border-border/50 bg-card/50">
            <div className="flex items-center gap-2 mb-4">
              <Music className="w-5 h-5 text-muted-foreground" />
              <h2 className="font-semibold">Original</h2>
            </div>
            
            <div className="space-y-4">
              {/* Waveform placeholder */}
              <div className="h-24 bg-muted/30 rounded-lg flex items-center justify-center relative overflow-hidden">
                <div 
                  className="absolute left-0 top-0 bottom-0 bg-[var(--holo-cyan)]/20"
                  style={{ width: `${originalProgress}%` }}
                />
                <div className="flex items-center gap-1 z-10">
                  {[...Array(30)].map((_, i) => (
                    <div 
                      key={i}
                      className="w-1 bg-[var(--holo-cyan)]/60 rounded-full"
                      style={{ height: `${20 + Math.random() * 60}%` }}
                    />
                  ))}
                </div>
              </div>
              
              {/* Controls */}
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={toggleOriginalPlay}
                  className="h-12 w-12 rounded-full"
                >
                  {playingOriginal ? (
                    <Pause className="w-5 h-5" />
                  ) : (
                    <Play className="w-5 h-5 ml-0.5" />
                  )}
                </Button>
                
                <div className="flex-1">
                  <Slider
                    value={[originalProgress]}
                    max={100}
                    step={0.1}
                    onValueChange={([value]) => {
                      if (originalAudioRef.current) {
                        const time = (value / 100) * originalAudioRef.current.duration;
                        originalAudioRef.current.currentTime = time;
                        setOriginalProgress(value);
                      }
                    }}
                    className="cursor-pointer"
                  />
                </div>
                
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setOriginalMuted(!originalMuted);
                    if (originalAudioRef.current) {
                      originalAudioRef.current.muted = !originalMuted;
                    }
                  }}
                >
                  {originalMuted ? (
                    <VolumeX className="w-4 h-4" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>

          {/* Polished Audio */}
          <Card className={`p-6 border-[var(--holo-purple)]/30 bg-gradient-to-br from-[var(--holo-purple)]/5 to-transparent ${!isPolished ? 'opacity-60' : ''}`}>
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-[var(--holo-purple)]" />
              <h2 className="font-semibold">Polished</h2>
              {isPolished && (
                <span className="text-xs bg-[var(--holo-purple)]/20 text-[var(--holo-purple)] px-2 py-0.5 rounded-full">
                  Ready
                </span>
              )}
            </div>
            
            <div className="space-y-4">
              {/* Waveform placeholder */}
              <div className="h-24 bg-muted/30 rounded-lg flex items-center justify-center relative overflow-hidden">
                {isPolished ? (
                  <>
                    <div 
                      className="absolute left-0 top-0 bottom-0 bg-[var(--holo-purple)]/20"
                      style={{ width: `${polishedProgress}%` }}
                    />
                    <div className="flex items-center gap-1 z-10">
                      {[...Array(30)].map((_, i) => (
                        <div 
                          key={i}
                          className="w-1 bg-[var(--holo-purple)]/60 rounded-full"
                          style={{ height: `${20 + Math.random() * 60}%` }}
                        />
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">Apply polish to preview</p>
                )}
              </div>
              
              {/* Controls */}
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={togglePolishedPlay}
                  disabled={!isPolished}
                  className="h-12 w-12 rounded-full border-[var(--holo-purple)]/50"
                >
                  {playingPolished ? (
                    <Pause className="w-5 h-5" />
                  ) : (
                    <Play className="w-5 h-5 ml-0.5" />
                  )}
                </Button>
                
                <div className="flex-1">
                  <Slider
                    value={[polishedProgress]}
                    max={100}
                    step={0.1}
                    disabled={!isPolished}
                    onValueChange={([value]) => {
                      if (polishedAudioRef.current) {
                        const time = (value / 100) * polishedAudioRef.current.duration;
                        polishedAudioRef.current.currentTime = time;
                        setPolishedProgress(value);
                      }
                    }}
                    className="cursor-pointer"
                  />
                </div>
                
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={!isPolished}
                  onClick={() => {
                    setPolishedMuted(!polishedMuted);
                    if (polishedAudioRef.current) {
                      polishedAudioRef.current.muted = !polishedMuted;
                    }
                  }}
                >
                  {polishedMuted ? (
                    <VolumeX className="w-4 h-4" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Polish Settings */}
        <Card className="p-6 mb-8 border-border/50">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-semibold flex items-center gap-2">
              <Wand2 className="w-5 h-5 text-[var(--holo-purple)]" />
              Polish Settings
            </h2>
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset
            </Button>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            {/* EQ Section */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-muted-foreground">Equalizer</h3>
              
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  <span className="text-sm w-16">Bass</span>
                  <Slider
                    value={[settings.eq.bass + 12]}
                    max={24}
                    step={1}
                    onValueChange={([value]) => setSettings(s => ({ ...s, eq: { ...s.eq, bass: value - 12 } }))}
                    className="flex-1"
                  />
                  <span className="text-sm w-12 text-right">{settings.eq.bass > 0 ? '+' : ''}{settings.eq.bass}dB</span>
                </div>
                
                <div className="flex items-center gap-4">
                  <span className="text-sm w-16">Mid</span>
                  <Slider
                    value={[settings.eq.mid + 12]}
                    max={24}
                    step={1}
                    onValueChange={([value]) => setSettings(s => ({ ...s, eq: { ...s.eq, mid: value - 12 } }))}
                    className="flex-1"
                  />
                  <span className="text-sm w-12 text-right">{settings.eq.mid > 0 ? '+' : ''}{settings.eq.mid}dB</span>
                </div>
                
                <div className="flex items-center gap-4">
                  <span className="text-sm w-16">Treble</span>
                  <Slider
                    value={[settings.eq.treble + 12]}
                    max={24}
                    step={1}
                    onValueChange={([value]) => setSettings(s => ({ ...s, eq: { ...s.eq, treble: value - 12 } }))}
                    className="flex-1"
                  />
                  <span className="text-sm w-12 text-right">{settings.eq.treble > 0 ? '+' : ''}{settings.eq.treble}dB</span>
                </div>
              </div>
            </div>
            
            {/* Effects Section */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-muted-foreground">Effects</h3>
              
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  <span className="text-sm w-20">Compression</span>
                  <Slider
                    value={[settings.compression]}
                    max={100}
                    step={1}
                    onValueChange={([value]) => setSettings(s => ({ ...s, compression: value }))}
                    className="flex-1"
                  />
                  <span className="text-sm w-12 text-right">{settings.compression}%</span>
                </div>
                
                <div className="flex items-center gap-4">
                  <span className="text-sm w-20">Reverb</span>
                  <Slider
                    value={[settings.reverb]}
                    max={100}
                    step={1}
                    onValueChange={([value]) => setSettings(s => ({ ...s, reverb: value }))}
                    className="flex-1"
                  />
                  <span className="text-sm w-12 text-right">{settings.reverb}%</span>
                </div>
                
                <div className="flex items-center gap-4">
                  <span className="text-sm w-20">De-Esser</span>
                  <Slider
                    value={[settings.deEsser]}
                    max={100}
                    step={1}
                    onValueChange={([value]) => setSettings(s => ({ ...s, deEsser: value }))}
                    className="flex-1"
                  />
                  <span className="text-sm w-12 text-right">{settings.deEsser}%</span>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-4 justify-center">
          {!isPolished ? (
            <Button
              onClick={handleApplyPolish}
              disabled={isProcessing}
              className="bg-gradient-to-r from-[var(--holo-purple)] to-[var(--holo-pink)] hover:opacity-90 px-8"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4 mr-2" />
                  Apply Magic Polish
                </>
              )}
            </Button>
          ) : (
            <>
              <Button
                onClick={handleApplyPolish}
                disabled={isProcessing}
                variant="outline"
                className="border-[var(--holo-purple)]/50"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Re-processing...
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Re-apply with New Settings
                  </>
                )}
              </Button>
              
              <Button
                onClick={handleDownloadPolished}
                variant="outline"
                className="border-[var(--holo-cyan)]/50 text-[var(--holo-cyan)]"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Polished
              </Button>
              
              <Button
                onClick={handleConfirmPolish}
                className="bg-gradient-to-r from-green-600 to-emerald-500 hover:opacity-90 px-8"
              >
                <Check className="w-4 h-4 mr-2" />
                Confirm & Save
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
