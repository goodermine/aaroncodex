import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { WaveformVisualizer } from "@/components/WaveformVisualizer";
import { PitchTimeline } from "@/components/PitchTimeline";
import { VOXAnalysisReport } from "@/components/VOXAnalysisReport";
import { VocalRangeAnalyzer } from "@/components/VocalRangeAnalyzer";
import { AnalysisExport } from "@/components/AnalysisExport";
import { 
  Mic2, 
  ArrowLeft, 
  Download, 
  Play, 
  Pause,
  Clock,
  Music,
  Loader2,
  Share2,
  Calendar,
  Activity,
  FileAudio,
  Sparkles,
  RefreshCw,
  Zap,
  Brain,
  Waves
} from "lucide-react";
import { Link, useParams } from "wouter";
import VoxAINavigation from "@/components/VoxAINavigation";
import { getLoginUrl } from "@/const";
import { format } from "date-fns";
import { toast } from "sonner";

export default function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const analysisId = parseInt(id || "0");
  const { user, loading: authLoading, isAuthenticated } = useAuth();
  const [systemTime, setSystemTime] = useState(new Date());
  
  // Audio playback
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  
  // Re-analyse state
  const [isReanalysing, setIsReanalysing] = useState(false);
  const [reanalyseMode, setReanalyseMode] = useState<'basic' | 'deep'>('deep');
  const [showReanalyseOptions, setShowReanalyseOptions] = useState(false);
  const [reanalyseProgress, setReanalyseProgress] = useState(0);
  const [reanalyseStage, setReanalyseStage] = useState('');
  const utils = trpc.useUtils();
  
  // Re-analyse mutation
  const reanalyseMutation = trpc.analysis.reanalyse.useMutation({
    onSuccess: () => {
      toast.success("Re-analysis complete!");
      setIsReanalysing(false);
      setShowReanalyseOptions(false);
      setReanalyseProgress(100);
      setReanalyseStage('Complete');
      utils.analysis.get.invalidate({ id: analysisId });
    },
    onError: (error) => {
      toast.error(error.message || "Re-analysis failed");
      setIsReanalysing(false);
      setReanalyseProgress(0);
      setReanalyseStage('');
    },
  });
  
  // Poll for progress during re-analysis
  useEffect(() => {
    if (!isReanalysing) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const result = await utils.analysis.get.fetch({ id: analysisId });
        if (result) {
          const progress = result.progressPercent || 0;
          const stage = result.currentStage || '';
          setReanalyseProgress(progress);
          setReanalyseStage(stage);
          
          // Check if completed or failed
          if (result.status === 'completed' || result.status === 'failed') {
            setIsReanalysing(false);
            clearInterval(pollInterval);
            if (result.status === 'completed') {
              utils.analysis.get.invalidate({ id: analysisId });
            }
          }
        }
      } catch (err) {
        console.error('Failed to poll progress:', err);
      }
    }, 1000); // Poll every second
    
    return () => clearInterval(pollInterval);
  }, [isReanalysing, analysisId, utils]);
  
  const handleReanalyse = () => {
    setIsReanalysing(true);
    setReanalyseProgress(0);
    setReanalyseStage('Starting...');
    reanalyseMutation.mutate({ analysisId, analysisMode: reanalyseMode });
  };

  useEffect(() => {
    const timer = setInterval(() => setSystemTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch analysis
  const { data: analysis, isLoading, error } = trpc.analysis.get.useQuery(
    { id: analysisId },
    { enabled: isAuthenticated && analysisId > 0 }
  );

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      window.location.href = getLoginUrl();
    }
  }, [authLoading, isAuthenticated]);

  // Audio playback controls
  const togglePlayback = () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Export to PDF
  const handleExportPDF = async () => {
    if (!analysis) return;
    
    setIsExporting(true);
    
    try {
      // Create a printable version
      const printContent = generatePrintContent(analysis);
      
      // Open print dialog
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(printContent);
        printWindow.document.close();
        printWindow.onload = () => {
          printWindow.print();
          setIsExporting(false);
        };
      } else {
        toast.error("Please allow popups to export PDF");
        setIsExporting(false);
      }
    } catch (error) {
      toast.error("Failed to export PDF");
      setIsExporting(false);
    }
  };

  // Copy share link
  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied to clipboard");
    } catch {
      toast.error("Failed to copy link");
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="status-ring">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="min-h-screen bg-background relative overflow-hidden">
        <div className="grid-bg" />
        <div className="hex-pattern" />
        <div className="flex items-center justify-center min-h-screen">
          <div className="holo-card p-12 text-center">
            <h1 className="text-2xl font-bold mb-4">Analysis Not Found</h1>
            <p className="text-muted-foreground mb-6">
              The requested analysis could not be found.
            </p>
            <Link href="/dashboard">
              <Button className="glow-btn font-mono">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const duration = analysis.durationSeconds ? Number(analysis.durationSeconds) : 0;

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="grid-bg" />
      <div className="hex-pattern" />

      {/* Navigation */}
      <VoxAINavigation />

      <main className="container pt-28 pb-16">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-10">
          <div className="flex-1">
            <div className="ai-indicator inline-flex mb-4">
              <div className="ai-indicator-dot" style={{ background: 'var(--holo-green)' }} />
              <span className="ai-indicator-text" style={{ color: 'var(--holo-green)' }}>Analysis Complete</span>
            </div>
            <div className="flex flex-wrap items-center gap-4 mb-2">
              <h1 className="text-2xl md:text-3xl font-bold truncate">
                {analysis.fileName || "Vocal Analysis"}
              </h1>
              {analysis.vocalArchetype && (
                <Badge className="bg-primary/20 text-primary border-primary/30 font-mono">
                  {analysis.vocalArchetype}
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm font-mono text-muted-foreground">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {format(new Date(analysis.createdAt), "MMM d, yyyy")}
              </span>
              {duration > 0 && (
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatDuration(duration)}
                </span>
              )}
              {analysis.fileFormat && (
                <span className="px-2 py-0.5 rounded bg-muted/50 text-xs uppercase">
                  {analysis.fileFormat}
                </span>
              )}
            </div>
          </div>
          
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <Button variant="ghost" size="icon" onClick={handleShare} className="rounded-xl border border-border/50">
                <Share2 className="w-4 h-4" />
              </Button>
              <Button 
                variant="outline" 
                onClick={handleExportPDF}
                disabled={isExporting}
                className="font-mono border-border/50 bg-background/50"
              >
                {isExporting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Download className="w-4 h-4 mr-2" />
                )}
                Export Report
              </Button>
              <Button 
                variant="outline" 
                onClick={() => setShowReanalyseOptions(!showReanalyseOptions)}
                disabled={isReanalysing}
                className="font-mono border-primary/50 bg-primary/10 hover:bg-primary/20 text-primary"
              >
                {isReanalysing ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                Re-analyse
              </Button>
            </div>
            
            {/* Re-analyse Options Panel */}
            {showReanalyseOptions && (
              <div className="holo-card p-4 mt-2 animate-in fade-in slide-in-from-top-2">
                {isReanalysing ? (
                  /* Progress Indicator */
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-primary">Re-analysing...</span>
                      <span className="text-sm font-mono text-cyan-400">{reanalyseProgress}%</span>
                    </div>
                    
                    {/* Progress Bar */}
                    <div className="relative h-3 bg-background/50 rounded-full overflow-hidden border border-border/30">
                      <div 
                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${reanalyseProgress}%` }}
                      />
                      <div 
                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500/50 via-purple-500/50 to-pink-500/50 rounded-full animate-pulse"
                        style={{ width: `${reanalyseProgress}%` }}
                      />
                    </div>
                    
                    {/* Current Stage */}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                      <span className="truncate">{reanalyseStage || 'Processing...'}</span>
                    </div>
                    
                    {/* Stage Indicators */}
                    <div className="grid grid-cols-5 gap-1 text-xs">
                      <div className={`text-center py-1 rounded ${reanalyseProgress >= 5 ? 'bg-cyan-500/20 text-cyan-400' : 'bg-background/30 text-muted-foreground'}`}>
                        Init
                      </div>
                      <div className={`text-center py-1 rounded ${reanalyseProgress >= 30 ? 'bg-cyan-500/20 text-cyan-400' : 'bg-background/30 text-muted-foreground'}`}>
                        Audio
                      </div>
                      <div className={`text-center py-1 rounded ${reanalyseProgress >= 50 ? 'bg-purple-500/20 text-purple-400' : 'bg-background/30 text-muted-foreground'}`}>
                        Pitch
                      </div>
                      <div className={`text-center py-1 rounded ${reanalyseProgress >= 70 ? 'bg-purple-500/20 text-purple-400' : 'bg-background/30 text-muted-foreground'}`}>
                        AI
                      </div>
                      <div className={`text-center py-1 rounded ${reanalyseProgress >= 95 ? 'bg-pink-500/20 text-pink-400' : 'bg-background/30 text-muted-foreground'}`}>
                        Done
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Mode Selection */
                  <>
                    <p className="text-sm text-muted-foreground mb-3">Select analysis mode:</p>
                    <div className="flex gap-2 mb-3">
                      <button
                        onClick={() => setReanalyseMode('basic')}
                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${
                          reanalyseMode === 'basic' 
                            ? 'border-cyan-500 bg-cyan-500/10' 
                            : 'border-border/50 hover:border-cyan-500/50'
                        }`}
                      >
                        <Zap className={`w-5 h-5 mx-auto mb-1 ${reanalyseMode === 'basic' ? 'text-cyan-400' : 'text-muted-foreground'}`} />
                        <div className={`text-sm font-medium ${reanalyseMode === 'basic' ? 'text-cyan-400' : ''}`}>Basic</div>
                        <div className="text-xs text-muted-foreground">Quick feedback</div>
                      </button>
                      <button
                        onClick={() => setReanalyseMode('deep')}
                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${
                          reanalyseMode === 'deep' 
                            ? 'border-purple-500 bg-purple-500/10' 
                            : 'border-border/50 hover:border-purple-500/50'
                        }`}
                      >
                        <Brain className={`w-5 h-5 mx-auto mb-1 ${reanalyseMode === 'deep' ? 'text-purple-400' : 'text-muted-foreground'}`} />
                        <div className={`text-sm font-medium ${reanalyseMode === 'deep' ? 'text-purple-400' : ''}`}>Deep Studio</div>
                        <div className="text-xs text-muted-foreground">Full diagnostic</div>
                      </button>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => setShowReanalyseOptions(false)}
                        className="flex-1"
                      >
                        Cancel
                      </Button>
                      <Button 
                        size="sm" 
                        onClick={handleReanalyse}
                        disabled={isReanalysing}
                        className="flex-1 glow-btn"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" /> Start Re-analysis
                      </Button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <div className="data-tile active">
            <div className="metric-label">Archetype</div>
            <div className="text-sm font-medium mt-2 truncate">{analysis.vocalArchetype || 'Unknown'}</div>
          </div>
          <div className="data-tile">
            <div className="metric-label">Duration</div>
            <div className="metric-value">{formatDuration(duration)}</div>
          </div>
          <div className="data-tile">
            <div className="metric-label">Avg RMS</div>
            <div className="metric-value">{analysis.avgRms ? Number(analysis.avgRms).toFixed(3) : 'N/A'}</div>
          </div>
          <div className="data-tile">
            <div className="metric-label">Dynamic Range</div>
            <div className="text-sm font-medium mt-2">{analysis.dynamicRange || 'N/A'}</div>
          </div>
        </div>

        {/* Audio Player & Visualizations */}
        {analysis.audioUrl && (
          <>
            <audio
              ref={audioRef}
              src={analysis.audioUrl}
              preload="auto"
              crossOrigin="anonymous"
              onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              onEnded={() => setIsPlaying(false)}
              onError={(e) => {
                console.error('Audio playback error:', e);
                toast.error('Unable to play audio. The file format may not be supported by your browser.');
              }}
              onCanPlay={() => console.log('Audio ready to play:', analysis.audioUrl)}
            />
            
            {/* Audio Player - Always show when audioUrl exists */}
            <div className="holo-card p-8 mb-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    <FileAudio className="w-5 h-5 text-primary" />
                    {analysis.waveformData && (analysis.waveformData as number[]).length > 0 ? 'Waveform Analysis' : 'Audio Player'}
                  </h2>
                  <p className="text-xs font-mono text-muted-foreground mt-1">
                    {analysis.waveformData && (analysis.waveformData as number[]).length > 0 ? (
                      <>
                        RMS: {analysis.avgRms ? Number(analysis.avgRms).toFixed(3) : 'N/A'} | 
                        Peak: {analysis.peakRms ? Number(analysis.peakRms).toFixed(3) : 'N/A'} | 
                        Range: {analysis.dynamicRange || 'N/A'}
                      </>
                    ) : (
                      <>{analysis.fileName} • {analysis.fileFormat?.toUpperCase()}</>
                    )}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={togglePlayback}
                  className="rounded-xl border-border/50 bg-background/50"
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </Button>
              </div>
              
              {analysis.waveformData && (analysis.waveformData as number[]).length > 0 ? (
                <WaveformVisualizer
                  waveformData={analysis.waveformData as number[]}
                  currentTime={currentTime}
                  duration={duration}
                  avgRms={analysis.avgRms ? Number(analysis.avgRms) : undefined}
                  peakRms={analysis.peakRms ? Number(analysis.peakRms) : undefined}
                  dynamicRange={analysis.dynamicRange || undefined}
                  onSeek={handleSeek}
                />
              ) : (
                <div className="bg-black/30 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={togglePlayback}
                        className="rounded-full border-border/50 bg-background/50 h-12 w-12"
                      >
                        {isPlaying ? (
                          <Pause className="w-5 h-5" />
                        ) : (
                          <Play className="w-5 h-5 ml-0.5" />
                        )}
                      </Button>
                      <div>
                        <p className="text-sm font-medium">{analysis.fileName}</p>
                        <p className="text-xs text-muted-foreground">
                          {analysis.fileFormat?.toUpperCase()} • {analysis.status === 'uploading' ? 'Ready to analyze' : 'Processed'}
                        </p>
                      </div>
                    </div>
                    {analysis.status === 'uploading' && (
                      <Link href={`/analyze?startAnalysis=${analysis.id}`}>
                        <Button className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600">
                          <Sparkles className="w-4 h-4 mr-2" />
                          Start Analysis
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>

            {analysis.pitchTrack && (analysis.pitchTrack as any[]).length > 0 && (
              <div className="holo-card p-8 mb-8">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-bold flex items-center gap-2">
                      <Activity className="w-5 h-5 text-primary" />
                      Pitch Timeline
                    </h2>
                    <p className="text-xs font-mono text-muted-foreground mt-1">
                      {(analysis.pitchTrack as any[]).length} data points tracked
                    </p>
                  </div>
                  <div className="telemetry-display success">
                    <span>Data Captured</span>
                  </div>
                </div>
                
                <PitchTimeline
                  pitchData={analysis.pitchTrack as any[]}
                  duration={duration}
                  vocalRange={analysis.detectedVocalRange as any || undefined}
                  stabilityScore={analysis.pitchStabilityScore ? Number(analysis.pitchStabilityScore) : undefined}
                />
                
                {/* Vocal Range Analysis */}
                <VocalRangeAnalyzer
                  pitchData={(analysis.pitchTrack as any[] || []).map((p: any) => ({
                    time: parseFloat(p.time || '0'),
                    note: p.note || '',
                    hz: p.hz || 0,
                    stability: p.cents !== undefined 
                      ? (Math.abs(p.cents) < 15 ? 'stable' : p.cents > 0 ? 'sharp' : 'flat')
                      : undefined
                  }))}
                />
              </div>
            )}
          </>
        )}

        {/* VOX Protocol 6 Analysis */}
        {analysis.status === "completed" && analysis.vocalArchetype && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold holo-text">VOX Protocol 6 Analysis</h2>
                <p className="text-sm text-muted-foreground mt-1 font-mono">
                  Complete diagnostic report
                </p>
              </div>
            </div>
            
            <VOXAnalysisReport
              vocalArchetype={analysis.vocalArchetype}
              firstListenSummary={analysis.firstListenSummary || ""}
              techniqueAudit={analysis.techniqueAudit as any || {
                pitchAccuracy: "",
                tone: "",
                breathSupport: "",
                registrationUse: "",
                tensionSigns: "",
                timing: "",
              }}
              quickFixPrescriptions={analysis.quickFixPrescriptions as any[] || []}
              assignedDrill={analysis.assignedDrill as any || {
                name: "",
                description: "",
                whatItFixes: "",
                howItFeels: "",
                mistakeToAvoid: "",
              }}
              emotionalCoaching={analysis.emotionalCoaching as any || {
                emotionalCharacter: "",
                phrasingCue: "",
                characterMetaphor: "",
                emotionalHits: "",
                emotionalMisses: "",
              }}
              progressPathway={analysis.progressPathway as any || {
                nextPractice: "",
                signsOfImprovement: "",
                evolutionGoal: "",
              }}
            />
            
            {/* Export Options */}
            <AnalysisExport
              analysis={{
                id: analysis.id,
                vocalArchetype: analysis.vocalArchetype || 'Unknown',
                firstListenSummary: analysis.firstListenSummary || '',
                techniqueAudit: analysis.techniqueAudit as any || {
                  pitchAccuracy: '',
                  tone: '',
                  breathSupport: '',
                  registrationUse: '',
                  tensionSigns: '',
                  timing: ''
                },
                quickFixPrescriptions: ((analysis.quickFixPrescriptions as any[]) || []).map((p: any) => ({
                  timestamp: p.timestamp,
                  cue: p.instruction || p.cue || ''
                })),
                assignedDrill: analysis.assignedDrill as any || {
                  name: '',
                  description: '',
                  whatItFixes: '',
                  howItFeels: '',
                  mistakeToAvoid: ''
                },
                emotionalCoaching: {
                  emotionalCharacter: (analysis.emotionalCoaching as any)?.emotionalCharacter || '',
                  phrasingCue: (analysis.emotionalCoaching as any)?.phrasingCue || '',
                  whereItLanded: (analysis.emotionalCoaching as any)?.emotionalHits || '',
                  whereItMissed: (analysis.emotionalCoaching as any)?.emotionalMisses || ''
                },
                progressPathway: analysis.progressPathway as any || {
                  nextPractice: '',
                  signsOfImprovement: '',
                  evolutionGoal: ''
                },
                detectedVocalRange: analysis.detectedVocalRange as any,
                pitchStabilityScore: analysis.pitchStabilityScore ? Number(analysis.pitchStabilityScore) : undefined,
                createdAt: analysis.createdAt
              }}
              songTitle={analysis.fileName || undefined}
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4 mt-10">
          <Link href="/analyze">
            <Button className="glow-btn font-mono">
              <Sparkles className="w-4 h-4 mr-2" />
              New Analysis
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline" className="font-mono border-border/50 bg-background/50">
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </main>
    </div>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function generatePrintContent(analysis: any): string {
  const date = format(new Date(analysis.createdAt), "MMMM d, yyyy");
  
  return `
<!DOCTYPE html>
<html>
<head>
  <title>Howard Analysis Report - ${analysis.fileName || 'Vocal Analysis'}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: 'Inter', -apple-system, sans-serif; 
      line-height: 1.6; 
      color: #0a0a0f;
      padding: 40px;
      max-width: 800px;
      margin: 0 auto;
      background: #fff;
    }
    h1 { 
      font-size: 28px; 
      margin-bottom: 8px;
      font-weight: 700;
    }
    h2 { 
      font-size: 18px; 
      margin: 28px 0 12px;
      color: #00d4ff;
      border-bottom: 1px solid #e5e5e5;
      padding-bottom: 8px;
      font-weight: 600;
    }
    h3 { 
      font-size: 14px; 
      margin: 16px 0 8px;
      color: #666;
      font-weight: 600;
    }
    p { margin-bottom: 12px; }
    .meta { 
      color: #666; 
      font-size: 13px;
      margin-bottom: 24px;
      font-family: 'JetBrains Mono', monospace;
    }
    .archetype {
      display: inline-block;
      background: linear-gradient(135deg, #00d4ff20, #a855f720);
      color: #00d4ff;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      margin-left: 12px;
      font-weight: 600;
      border: 1px solid #00d4ff40;
    }
    .section {
      margin-bottom: 24px;
      padding: 20px;
      background: #f8f9fa;
      border-radius: 8px;
      border: 1px solid #e5e5e5;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .item {
      background: white;
      padding: 12px;
      border-radius: 6px;
      border: 1px solid #e5e5e5;
    }
    .item-label {
      font-size: 10px;
      color: #888;
      text-transform: uppercase;
      margin-bottom: 4px;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.5px;
    }
    .prescription {
      display: flex;
      gap: 12px;
      padding: 12px;
      background: white;
      border-radius: 6px;
      margin-bottom: 8px;
      border: 1px solid #e5e5e5;
    }
    .timestamp {
      font-family: 'JetBrains Mono', monospace;
      color: #00d4ff;
      white-space: nowrap;
      font-size: 12px;
    }
    .footer {
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #e5e5e5;
      font-size: 11px;
      color: #888;
      text-align: center;
      font-family: 'JetBrains Mono', monospace;
    }
    @media print {
      body { padding: 20px; }
      .section { break-inside: avoid; }
    }
  </style>
</head>
<body>
  <h1>
    ${analysis.fileName || 'Vocal Analysis'}
    ${analysis.vocalArchetype ? `<span class="archetype">${analysis.vocalArchetype}</span>` : ''}
  </h1>
  <p class="meta">
    Analyzed on ${date} • Howard (VOX AI) • VOX Protocol 6
  </p>

  ${analysis.firstListenSummary ? `
  <div class="section">
    <h2>1. First Listen Summary</h2>
    <p>${analysis.firstListenSummary}</p>
  </div>
  ` : ''}

  ${analysis.techniqueAudit ? `
  <div class="section">
    <h2>2. Technique Audit</h2>
    <div class="grid">
      <div class="item">
        <div class="item-label">Pitch Accuracy</div>
        <p>${analysis.techniqueAudit.pitchAccuracy || 'N/A'}</p>
      </div>
      <div class="item">
        <div class="item-label">Tone Quality</div>
        <p>${analysis.techniqueAudit.tone || 'N/A'}</p>
      </div>
      <div class="item">
        <div class="item-label">Breath Support</div>
        <p>${analysis.techniqueAudit.breathSupport || 'N/A'}</p>
      </div>
      <div class="item">
        <div class="item-label">Registration Use</div>
        <p>${analysis.techniqueAudit.registrationUse || 'N/A'}</p>
      </div>
      <div class="item">
        <div class="item-label">Tension Signs</div>
        <p>${analysis.techniqueAudit.tensionSigns || 'N/A'}</p>
      </div>
      <div class="item">
        <div class="item-label">Timing</div>
        <p>${analysis.techniqueAudit.timing || 'N/A'}</p>
      </div>
    </div>
  </div>
  ` : ''}

  ${analysis.quickFixPrescriptions?.length > 0 ? `
  <div class="section">
    <h2>3. Quick Fix Prescriptions</h2>
    ${analysis.quickFixPrescriptions.map((fix: any) => `
      <div class="prescription">
        <span class="timestamp">${fix.timestamp}</span>
        <span>${fix.instruction}</span>
      </div>
    `).join('')}
  </div>
  ` : ''}

  ${analysis.assignedDrill ? `
  <div class="section">
    <h2>4. Assigned Drill: ${analysis.assignedDrill.name || 'Exercise'}</h2>
    <h3>How to Perform</h3>
    <p>${analysis.assignedDrill.description || 'N/A'}</p>
    <h3>What It Fixes</h3>
    <p>${analysis.assignedDrill.whatItFixes || 'N/A'}</p>
    <h3>How It Should Feel</h3>
    <p>${analysis.assignedDrill.howItFeels || 'N/A'}</p>
    <h3>Mistake to Avoid</h3>
    <p>${analysis.assignedDrill.mistakeToAvoid || 'N/A'}</p>
  </div>
  ` : ''}

  ${analysis.emotionalCoaching ? `
  <div class="section">
    <h2>5. Emotional & Performance Coaching</h2>
    <h3>Emotional Character</h3>
    <p>${analysis.emotionalCoaching.emotionalCharacter || 'N/A'}</p>
    <h3>Phrasing Cue</h3>
    <p>${analysis.emotionalCoaching.phrasingCue || 'N/A'}</p>
    <h3>Character Metaphor</h3>
    <p>${analysis.emotionalCoaching.characterMetaphor || 'N/A'}</p>
    <h3>Where It Landed</h3>
    <p>${analysis.emotionalCoaching.emotionalHits || 'N/A'}</p>
    <h3>Where It Missed</h3>
    <p>${analysis.emotionalCoaching.emotionalMisses || 'N/A'}</p>
  </div>
  ` : ''}

  ${analysis.progressPathway ? `
  <div class="section">
    <h2>6. Progress Pathway</h2>
    <h3>What to Practice Next</h3>
    <p>${analysis.progressPathway.nextPractice || 'N/A'}</p>
    <h3>Signs of Improvement</h3>
    <p>${analysis.progressPathway.signsOfImprovement || 'N/A'}</p>
    <h3>Evolution Goal</h3>
    <p>${analysis.progressPathway.evolutionGoal || 'N/A'}</p>
  </div>
  ` : ''}

  <div class="footer">
    Generated by Howard (VOX AI) • VOX Protocol 6 Analysis System
  </div>
</body>
</html>
  `.trim();
}
