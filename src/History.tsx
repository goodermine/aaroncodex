import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  Mic2, 
  Search, 
  Plus, 
  BarChart3, 
  Clock, 
  Music,
  TrendingUp,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Trash2,
  ExternalLink,
  Activity,
  Sparkles,
  Radio,
  Calendar,
  RotateCcw,
  AlertTriangle,
  Play,
  Pause,
  Download,
  Wand2
} from "lucide-react";
import { Link, useLocation } from "wouter";
import VoxAINavigation from "@/components/VoxAINavigation";
import { getLoginUrl } from "@/const";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function History() {
  const { user, loading: authLoading, isAuthenticated } = useAuth();
  const [, setLocation] = useLocation();
  const [systemTime, setSystemTime] = useState(new Date());
  
  // Audio playback state
  const [playingId, setPlayingId] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  // Batch selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);
  
  // Pagination and filtering
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  
  const pageSize = 10;

  useEffect(() => {
    const timer = setInterval(() => setSystemTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch analyses
  const { data: analysesData, isLoading, refetch } = trpc.analysis.list.useQuery({
    limit: pageSize,
    offset: page * pageSize,
    search: debouncedSearch || undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
  }, {
    enabled: isAuthenticated,
  });

  // Fetch stats
  const { data: stats } = trpc.analysis.stats.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  // Delete mutation
  const deleteMutation = trpc.analysis.delete.useMutation({
    onSuccess: () => {
      toast.success("Analysis deleted");
      refetch();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  // Reset all data mutation
  const resetMutation = trpc.analysis.resetAll.useMutation({
    onSuccess: (result) => {
      toast.success(`Reset complete! Deleted ${result.analysesDeleted} analyses.`);
      refetch();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      window.location.href = getLoginUrl();
    }
  }, [authLoading, isAuthenticated]);

  const totalPages = analysesData ? Math.ceil(analysesData.total / pageSize) : 0;

  const handleDelete = async (id: number) => {
    await deleteMutation.mutateAsync({ id });
  };

  // Handle audio playback
  const handlePlayPause = (analysisId: number, audioUrl: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    if (playingId === analysisId) {
      // Stop playing
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlayingId(null);
    } else {
      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause();
      }
      // Start new audio
      const audio = new Audio(audioUrl);
      audio.onended = () => setPlayingId(null);
      audio.onerror = () => {
        toast.error('Failed to play audio');
        setPlayingId(null);
      };
      audio.play().catch(() => {
        toast.error('Failed to play audio');
        setPlayingId(null);
      });
      audioRef.current = audio;
      setPlayingId(analysisId);
    }
  };

  // Handle clicking on a recording card
  const handleCardClick = (analysis: any) => {
    if (analysis.status === 'completed' && analysis.fullAnalysisText) {
      // Already analyzed - go to analysis detail page
      setLocation(`/analysis/${analysis.id}`);
    } else if (analysis.audioUrl) {
      // Not analyzed yet - go to Chat and AUTO-START analysis (not just ask)
      sessionStorage.setItem('pendingAnalysis', JSON.stringify({
        analysisId: analysis.id,
        audioUrl: analysis.audioUrl,
        fileName: analysis.fileName || 'Recording',
        autoStart: true  // Changed from askToAnalyze to autoStart
      }));
      setLocation('/voxai');
    }
  };

  // Handle download
  const handleDownload = async (audioUrl: string, fileName: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    try {
      const response = await fetch(audioUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName || 'recording.mp3';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Download started');
    } catch (error) {
      toast.error('Failed to download file');
    }
  };

  // Handle Magic Polish - navigate to dedicated Magic Polish page
  const handleMagicPolish = (analysis: any, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    // Navigate to the Magic Polish page with before/after comparison
    setLocation(`/polish/${analysis.id}`);
  };

  // Batch selection handlers
  const toggleSelection = (id: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (!analysesData?.analyses) return;
    const allIds = analysesData.analyses.map(a => a.id);
    const allSelected = allIds.every(id => selectedIds.has(id));
    
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allIds));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    
    setIsBatchDeleting(true);
    try {
      // Delete each selected analysis
      const deletePromises = Array.from(selectedIds).map(id => 
        deleteMutation.mutateAsync({ id })
      );
      await Promise.all(deletePromises);
      toast.success(`Deleted ${selectedIds.size} recording${selectedIds.size > 1 ? 's' : ''}`);
      setSelectedIds(new Set());
      refetch();
    } catch (error) {
      toast.error('Failed to delete some recordings');
    } finally {
      setIsBatchDeleting(false);
    }
  };

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="status-ring">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Aurora background effect */}
      <div className="aurora-bg" />
      
      {/* Animated grid background */}
      <div className="grid-bg" />
      
      {/* Circuit pattern overlay */}
      <div className="circuit-pattern" />
      
      {/* Hex pattern overlay */}
      <div className="hex-pattern" />
      
      {/* Floating data streams */}
      <div className="particles-container">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="data-stream"
            style={{
              left: `${(i * 8.5) % 100}%`,
              animationDelay: `${i * 0.4}s`,
              animationDuration: `${3.5 + (i % 3)}s`,
            }}
          />
        ))}
      </div>

      {/* Navigation */}
      <VoxAINavigation />

      <main className="container pt-28 pb-16">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
          <div>
            <div className="ai-indicator inline-flex mb-4 breathing-glow rounded-xl">
              <div className="ai-indicator-dot" />
              <span className="ai-indicator-text">Performance History</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold">
              Welcome back{user?.name ? `, ` : ""}
              {user?.name && <span className="gradient-text-animated">{user.name}</span>}
            </h1>
            <p className="text-muted-foreground mt-2">
              Click a recording to analyze or view results
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" className="font-mono border-destructive/50 text-destructive hover:bg-destructive/10">
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reset All
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="glass-panel border-destructive/30">
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-3 text-destructive">
                    <AlertTriangle className="w-5 h-5" />
                    Reset All Data
                  </AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-foreground">
                    This action cannot be undone. This will permanently delete:
                    <ul className="list-disc list-inside mt-3 space-y-1">
                      <li>All your vocal analyses ({stats?.totalAnalyses ?? 0} total)</li>
                      <li>Your vocal context and preferences</li>
                      <li>All associated audio files</li>
                    </ul>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="font-mono">Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => resetMutation.mutate()}
                    disabled={resetMutation.isPending}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90 font-mono"
                  >
                    {resetMutation.isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Resetting...
                      </>
                    ) : (
                      "Reset Everything"
                    )}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="holo-card-enhanced p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/20">
                <BarChart3 className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-mono">Total</p>
                <p className="text-xl font-bold">{stats?.totalAnalyses ?? 0}</p>
              </div>
            </div>
          </div>
          <div className="holo-card-enhanced p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--holo-green)]/20">
                <TrendingUp className="w-4 h-4 text-[var(--holo-green)]" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-mono">Avg Stability</p>
                <p className="text-xl font-bold">{stats?.avgPitchStability ? `${Math.round(stats.avgPitchStability)}%` : '—'}</p>
              </div>
            </div>
          </div>
          <div className="holo-card-enhanced p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--holo-purple)]/20">
                <Music className="w-4 h-4 text-[var(--holo-purple)]" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-mono">Top Archetype</p>
                <p className="text-xl font-bold truncate">{stats?.mostCommonArchetype || '—'}</p>
              </div>
            </div>
          </div>
          <div className="holo-card-enhanced p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--holo-cyan)]/20">
                <Clock className="w-4 h-4 text-[var(--holo-cyan)]" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-mono">This Week</p>
                <p className="text-xl font-bold">{stats?.completedAnalyses ?? 0}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="holo-card-enhanced p-4 rounded-xl mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by filename, archetype..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 bg-background/50 border-border/50 font-mono"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-[180px] bg-background/50 border-border/50 font-mono">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Analyses List */}
        <div className="holo-card-enhanced p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold gradient-text-animated">Performance History</h2>
              <p className="text-sm text-muted-foreground font-mono mt-1">
                {analysesData?.total ?? 0} total analyses
              </p>
            </div>
            <div className="flex items-center gap-3">
              {selectedIds.size > 0 && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="border-destructive/50 text-destructive hover:bg-destructive/20"
                      disabled={isBatchDeleting}
                    >
                      {isBatchDeleting ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4 mr-2" />
                      )}
                      Delete ({selectedIds.size})
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent className="holo-card border-border/50">
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete {selectedIds.size} Recording{selectedIds.size > 1 ? 's' : ''}?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will permanently delete the selected recording{selectedIds.size > 1 ? 's' : ''} and cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel className="border-border/50">Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleBatchDelete}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Delete All
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
              <div className="telemetry-display">
                <span>Records</span>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="status-ring">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              </div>
            </div>
          ) : analysesData?.analyses.length === 0 ? (
            <div className="text-center py-16">
              <div className="p-4 rounded-xl bg-muted/50 inline-block mb-6">
                <Mic2 className="w-10 h-10 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No Recordings Yet</h3>
              <p className="text-muted-foreground mb-6">
                Upload your first vocal recording to get started
              </p>
              <Link href="/">
                <Button className="glow-btn font-mono">
                  <Radio className="w-4 h-4 mr-2" />
                  Start First Analysis
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Select All Header */}
              {analysesData && analysesData.analyses.length > 0 && (
                <div className="flex items-center gap-3 px-2 py-2 text-sm text-muted-foreground">
                  <Checkbox
                    checked={analysesData.analyses.every(a => selectedIds.has(a.id))}
                    onCheckedChange={toggleSelectAll}
                    className="border-border/50"
                  />
                  <span className="font-mono text-xs">
                    {selectedIds.size > 0 ? `${selectedIds.size} selected` : 'Select all'}
                  </span>
                </div>
              )}
              
              {analysesData?.analyses.map((analysis) => (
                <div
                  key={analysis.id}
                  onClick={() => handleCardClick(analysis)}
                  className={`flex items-center gap-4 p-5 rounded-xl bg-background/30 border transition-all group cursor-pointer ${
                    selectedIds.has(analysis.id) 
                      ? 'border-primary/50 bg-primary/5' 
                      : 'border-border/30 hover:border-primary/30 hover:bg-background/50'
                  }`}
                >
                  {/* Selection checkbox */}
                  <Checkbox
                    checked={selectedIds.has(analysis.id)}
                    onCheckedChange={() => {}}
                    onClick={(e) => toggleSelection(analysis.id, e)}
                    className="border-border/50"
                  />
                  
                  <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 group-hover:bg-primary/20 transition-colors">
                    <Activity className="w-5 h-5 text-primary" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-medium truncate">
                        {analysis.fileName || "Untitled Recording"}
                      </h4>
                      <StatusBadge status={analysis.status} />
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {format(new Date(analysis.createdAt), "MMM d, yyyy")}
                      </span>
                      {analysis.vocalArchetype && (
                        <span className="text-primary">{analysis.vocalArchetype}</span>
                      )}
                      {analysis.durationSeconds && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDuration(Number(analysis.durationSeconds))}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {/* Play button - show for all recordings with audio */}
                    {analysis.audioUrl && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="rounded-xl hover:bg-[var(--holo-green)]/20 h-9 w-9"
                        onClick={(e) => handlePlayPause(analysis.id, analysis.audioUrl!, e)}
                        title="Play/Pause"
                      >
                        {playingId === analysis.id ? (
                          <Pause className="w-4 h-4 text-[var(--holo-green)]" />
                        ) : (
                          <Play className="w-4 h-4 text-[var(--holo-green)]" />
                        )}
                      </Button>
                    )}

                    {/* Download button */}
                    {analysis.audioUrl && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="rounded-xl hover:bg-[var(--holo-cyan)]/20 h-9 w-9"
                        onClick={(e) => handleDownload(analysis.audioUrl!, analysis.fileName || 'recording.mp3', e)}
                        title="Download"
                      >
                        <Download className="w-4 h-4 text-[var(--holo-cyan)]" />
                      </Button>
                    )}

                    {/* Magic Polish button */}
                    {analysis.audioUrl && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="rounded-xl hover:bg-[var(--holo-purple)]/20 h-9 w-9"
                        onClick={(e) => handleMagicPolish(analysis, e)}
                        title="Magic Polish"
                      >
                        <Wand2 className="w-4 h-4 text-[var(--holo-purple)]" />
                      </Button>
                    )}
                    
                    {/* Analyze button - for recordings that need analysis */}
                    {analysis.audioUrl && analysis.status !== "completed" && analysis.status !== "processing" && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="rounded-xl hover:bg-[var(--holo-orange)]/20 h-9 w-9"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCardClick(analysis);
                        }}
                        title="Analyze"
                      >
                        <Sparkles className="w-4 h-4 text-[var(--holo-orange)]" />
                      </Button>
                    )}
                    
                    {/* View results for completed */}
                    {analysis.status === "completed" && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="rounded-xl hover:bg-primary/20 h-9 w-9"
                        onClick={(e) => {
                          e.stopPropagation();
                          setLocation(`/analysis/${analysis.id}`);
                        }}
                        title="View Analysis"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                    )}

                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="rounded-xl text-destructive hover:text-destructive hover:bg-destructive/20 h-9 w-9"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent className="holo-card border-border/50">
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete Recording</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to delete this recording? This action cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel className="border-border/50">Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDelete(analysis.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-6 border-t border-border/30">
                  <p className="text-sm text-muted-foreground font-mono">
                    Page {page + 1} of {totalPages}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setPage(p => Math.max(0, p - 1))}
                      disabled={page === 0}
                      className="rounded-xl border-border/50 bg-background/50"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                      disabled={page >= totalPages - 1}
                      className="rounded-xl border-border/50 bg-background/50"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { className: string; label: string }> = {
    completed: { className: "bg-[var(--holo-green)]/20 text-[var(--holo-green)] border-[var(--holo-green)]/30", label: "Analyzed" },
    processing: { className: "bg-[var(--holo-orange)]/20 text-[var(--holo-orange)] border-[var(--holo-orange)]/30", label: "Processing" },
    analyzing: { className: "bg-[var(--holo-cyan)]/20 text-[var(--holo-cyan)] border-[var(--holo-cyan)]/30", label: "Analyzing" },
    uploading: { className: "bg-muted text-muted-foreground border-border", label: "Ready" },
    failed: { className: "bg-[var(--holo-red)]/20 text-[var(--holo-red)] border-[var(--holo-red)]/30", label: "Failed" },
  };

  const variant = variants[status] || variants.uploading;

  return (
    <Badge variant="outline" className={`${variant.className} font-mono text-[10px]`}>
      {variant.label}
    </Badge>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
