import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Bell,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Clock,
  CloudUpload,
  FileAudio,
  FolderOpen,
  History,
  Home,
  ListFilter,
  Loader2,
  Mic,
  Music2,
  Pause,
  Play,
  Search,
  Settings,
  Share2,
  SlidersHorizontal,
  Upload,
  Volume2,
  Waves,
  XCircle,
} from "lucide-react";
import {
  cancelJob,
  EXECUTION_TARGET,
  exportDiagnostics,
  fetchJob,
  getBackgroundProcessingStatus,
  getLatestJob,
  requestBackgroundProcessingAccess,
  resetAppData,
  uploadSong,
} from "./lib/api/voxClient.js";
import "./App.css";

const REPORTS_KEY = "howard-vox-functional-reports";
const POLL_INTERVAL_MS = 2500;
const POLL_LONG_RUNNING_NOTICE_MS = 3 * 60 * 1000;
const MAX_POLL_ERRORS = 6;

function readReports() {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(REPORTS_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeReports(reports) {
  if (typeof window !== "undefined") {
    if (reports.length) {
      window.localStorage.setItem(REPORTS_KEY, JSON.stringify(reports));
    } else {
      window.localStorage.removeItem(REPORTS_KEY);
    }
  }
}

function clearVoxBrowserStorage() {
  if (typeof window === "undefined") return;
  const matchesVoxKey = (key) => key === REPORTS_KEY || key.toLowerCase().includes("howard-vox") || key.toLowerCase().includes("vox");

  for (const storage of [window.localStorage, window.sessionStorage]) {
    const keys = [];
    for (let index = 0; index < storage.length; index++) {
      const key = storage.key(index);
      if (key && matchesVoxKey(key)) keys.push(key);
    }
    keys.forEach((key) => storage.removeItem(key));
  }

  if (window.caches?.keys) {
    window.caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => matchesVoxKey(key)).map((key) => window.caches.delete(key))))
      .catch(() => {});
  }
}

function formatDateTime(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "Unknown";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDurationMs(ms, { compact = false } = {}) {
  if (!Number.isFinite(ms) || ms < 0) return "Unavailable";
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return compact ? `${hours}h ${minutes}m` : `${hours} hr ${minutes} min`;
  }
  if (minutes > 0) {
    return compact ? `${minutes}m ${seconds}s` : `${minutes} min ${seconds} sec`;
  }
  return compact ? `${seconds}s` : `${seconds} sec`;
}

function formatApproxDurationMs(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "calculating";
  const totalSeconds = Math.max(1, Math.round(ms / 1000));
  const minutes = Math.round(totalSeconds / 60);
  if (minutes >= 1) return `${minutes} min`;
  return `${totalSeconds} sec`;
}

function formatPlaybackTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const total = Math.floor(seconds);
  const minutes = Math.floor(total / 60);
  const remaining = String(total % 60).padStart(2, "0");
  return `${minutes}:${remaining}`;
}

function parseTimestampMs(value) {
  if (!value) return null;
  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : null;
}

function getProgressTiming(job) {
  const progress = job?.progress || {};
  const detail = progress.detail || {};
  return {
    elapsedMs: Number.isFinite(progress.elapsedMs) ? progress.elapsedMs : null,
    averageChunkMs: progress.averageChunkMs ?? detail.averageChunkMs ?? null,
    recentAverageChunkMs: progress.recentAverageChunkMs ?? detail.recentAverageChunkMs ?? null,
    estimatedRemainingMs: progress.estimatedRemainingMs ?? detail.estimatedRemainingMs ?? null,
    estimatedSeparationRemainingMs: progress.estimatedSeparationRemainingMs ?? detail.estimatedSeparationRemainingMs ?? null,
    estimatedTotalRemainingMs: progress.estimatedTotalRemainingMs ?? detail.estimatedTotalRemainingMs ?? null,
    lastProgressAt: progress.lastProgressAt || detail.lastProgressAt || progress.updatedAt || null,
    chunksCompleted: progress.chunksCompleted ?? detail.chunksCompleted ?? detail.chunkIndex ?? null,
    totalChunks: progress.totalChunks ?? detail.totalChunks ?? null,
    chunksRemaining: progress.chunksRemaining ?? detail.chunksRemaining ?? null,
  };
}

function estimateDetailedModeCopy(durationMs) {
  if (!Number.isFinite(durationMs) || durationMs <= 0) {
    return "Detailed mode may take 6-8 minutes for a full song on this device.";
  }
  const seconds = durationMs / 1000;
  if (seconds < 30) return "Detailed mode: short clips usually finish in under 1 minute.";
  if (seconds <= 120) return "Detailed mode: this length usually takes 2-4 minutes.";
  if (seconds <= 240) return "Detailed mode: full songs usually take 5-8 minutes.";
  return "Detailed mode: songs over 4 minutes may take 8+ minutes.";
}

function analysisModeLabel(mode) {
  if (mode === "quick-test") return "Quick Test";
  if (mode === "full-song-local") return "Full Song Local";
  return "Detailed";
}

function processingReassurance(job) {
  const totalChunks = Number(job?.progress?.totalChunks);
  const durationMs = Number(job?.inputDurationMs);
  const sourceType = String(job?.sourceType || "").toLowerCase();
  const title = String(job?.title || "").toLowerCase();
  const quickLike = sourceType.includes("quick") || title.includes("quick test") || (Number.isFinite(totalChunks) && totalChunks <= 6) || (Number.isFinite(durationMs) && durationMs < 60_000);
  if (quickLike) return "Quick Test is processing. This usually takes under a minute.";
  if (Number.isFinite(durationMs) && durationMs <= 120_000) return "Still working — this shorter take may take a few minutes on this device.";
  return "Still working — full songs can take several minutes on this device. Keep VOX open if possible.";
}

function statusLabel(status) {
  if (!status) return "Unknown";
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function isTerminal(job) {
  return ["completed", "failed", "cancelled"].includes(job?.jobStatus);
}

function reportTone(job) {
  if (job?.jobStatus === "completed") return "good";
  if (job?.jobStatus === "failed" || job?.jobStatus === "cancelled") return "bad";
  return "pending";
}

function reportScore(job) {
  if (job?.jobStatus === "failed" || job?.jobStatus === "cancelled") return "!";
  if (job?.jobStatus !== "completed") return "…";
  const metrics = job?.analysis?.metrics;
  if (!metrics) return "OK";
  const dynamicRange = Number(metrics.dynamicRangeDb);
  const voiced = Number(metrics.voicedFrameCount);
  const base = Number.isFinite(dynamicRange) ? Math.max(58, Math.min(92, 92 - Math.abs(dynamicRange - 22))) : 76;
  return Math.round(base + (Number.isFinite(voiced) && voiced > 5 ? 2 : 0));
}

function reportGrade(job) {
  const score = Number(reportScore(job));
  if (!Number.isFinite(score)) return statusLabel(job?.jobStatus);
  if (score >= 82) return "Very Good";
  if (score >= 70) return "Good";
  if (score >= 60) return "Fair";
  return "Needs Work";
}

function jobTitle(job) {
  return job?.title || job?.inputFileName || "Untitled vocal";
}

function safeFileName(name) {
  return name || "Untitled vocal take";
}

function sourceDebugLabel(take, job) {
  if (take?.pendingAnalysis) return "new input";
  if (job?.jobId && take?.jobId === job.jobId) return take?.sourceLabel || "active job";
  if (job?.jobId) return "active job";
  return "none";
}

function quickGuideTitle(guide) {
  if (guide === "warmup") return "Vocal Warmup";
  if (guide === "breath") return "Breath Control";
  return "Quick Start";
}

function LogoMark() {
  return (
    <div className="logo-mark" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}

function AppHeader({ title = "Howard VOX", leading, trailing }) {
  return (
    <header className="app-header">
      <div className="header-edge">{leading}</div>
      <div className="brand-title">
        <LogoMark />
        <strong>{title}</strong>
      </div>
      <div className="header-edge header-edge-right">{trailing}</div>
    </header>
  );
}

function IconButton({ label, children, onClick, disabled }) {
  return (
    <button className="icon-control" type="button" aria-label={label} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

function ProgressBar({ progress }) {
  const percent = Number.isFinite(progress?.percent) ? progress.percent : 0;
  return (
    <div className="progress-track" aria-label={`Progress ${percent}%`}>
      <div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} />
    </div>
  );
}

const PROCESS_STEPS = [
  { key: "ingest", label: "Import audio", detail: "Copying the selected song into the local job folder.", start: 0, end: 4, stages: ["processing"] },
  { key: "queue", label: "Queue job", detail: "Waiting for the Android local worker.", start: 0, end: 6, stages: ["queued"] },
  { key: "decode", label: "Decode song", detail: "Reading the source audio for native processing.", start: 6, end: 12, stages: ["decode"] },
  { key: "model", label: "Prepare model", detail: "Loading the bundled ONNX vocal separator.", start: 12, end: 15, stages: ["model"] },
  { key: "separate", label: "Separate vocals", detail: "Splitting vocals and instrumental stems.", start: 15, end: 82, stages: ["separate"] },
  { key: "stems", label: "Write stems", detail: "Saving the vocal and instrumental files.", start: 82, end: 90, stages: ["separate"] },
  { key: "analyze", label: "Analyze vocal", detail: "Calculating pitch, RMS, and crest metrics.", start: 90, end: 99, stages: ["analyze"] },
  { key: "report", label: "Write report", detail: "Saving the analysis manifest and report artifacts.", start: 99, end: 100, stages: ["report", "completed"] },
];

function stageStatus(job, key) {
  return job?.stages?.find((stage) => stage.key === key)?.status;
}

function failedProcessStep(job, progressStage) {
  const code = job?.error?.code || "";
  if (code.includes("FILE_TOO_LARGE") || code.includes("AUDIO_TOO_LONG")) return "ingest";
  if (stageStatus(job, "analyze") === "failed" || code.includes("ANALYSIS")) return "analyze";
  if (progressStage === "decode" || progressStage === "model" || progressStage === "separate") return progressStage;
  if (progressStage === "report") return "report";
  return "separate";
}

function buildProcessSteps(job) {
  if (!job) return PROCESS_STEPS.map((step) => ({ ...step, state: "pending" }));

  const percent = Number.isFinite(job.progress?.percent) ? job.progress.percent : null;
  const progressStage = job.progress?.stage || job.currentStage || job.jobStatus;
  const failedKey = job.jobStatus === "failed" ? failedProcessStep(job, progressStage) : null;
  const analysisStatus = job.analysis?.status || stageStatus(job, "analyze");
  const reportStatus = stageStatus(job, "report");

  return PROCESS_STEPS.map((step) => {
    let state = "pending";
    const stageMatches = step.stages.includes(progressStage);
    const withinPercent = percent !== null && percent >= step.start && percent < step.end;

    if (failedKey) {
      if (step.key === failedKey) state = "failed";
      else if (percent !== null && percent >= step.end) state = "completed";
    } else if (job.jobStatus === "cancelled") {
      state = stageMatches || withinPercent ? "failed" : percent !== null && percent >= step.end ? "completed" : "pending";
    } else if (job.jobStatus === "completed") {
      state = "completed";
      if (step.key === "analyze" && analysisStatus === "failed") state = "failed";
      if (step.key === "report" && reportStatus !== "completed") state = analysisStatus === "failed" ? "pending" : "completed";
    } else if (stageMatches || withinPercent) {
      state = "active";
    } else if (percent !== null && percent >= step.end) {
      state = "completed";
    } else if (step.key === "queue" && job.jobStatus === "processing" && progressStage !== "queued") {
      state = "completed";
    } else if (step.key === "ingest" && stageStatus(job, "ingest") === "completed") {
      state = "completed";
    }

    if (step.key === "stems" && progressStage === "separate" && percent !== null && percent < step.start) {
      state = "pending";
    }

    return { ...step, state };
  });
}

function ProcessQueueCard({ job, status }) {
  const steps = buildProcessSteps(job);
  const percent = Number.isFinite(job?.progress?.percent) ? job.progress.percent : null;
  const currentMessage = job?.progress?.message || status || "Select a song to start the local pipeline.";
  const progressStage = job?.progress?.stage || job?.currentStage || job?.jobStatus;
  const timing = getProgressTiming(job);
  const lastProgressMs = parseTimestampMs(timing.lastProgressAt);
  const isRunningSeparation = job && !isTerminal(job) && progressStage === "separate";
  const [nowMs, setNowMs] = useState(0);
  useEffect(() => {
    if (!isRunningSeparation) return undefined;
    const interval = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [isRunningSeparation, job?.jobId, timing.lastProgressAt]);
  const msSinceProgress = lastProgressMs && nowMs ? nowMs - lastProgressMs : 0;
  const showTiming = isRunningSeparation || job?.jobStatus === "completed";
  const completionTiming = job?.engine?.timings || {};

  return (
    <section className="card process-card">
      <div className="process-heading">
        <div>
          <h2>Processing queue</h2>
          <p>{currentMessage}</p>
        </div>
        <strong>{percent === null ? statusLabel(job?.jobStatus || "ready") : `${percent}%`}</strong>
      </div>
      {job ? <ProgressBar progress={job.progress} /> : null}
      {showTiming ? (
        <div className="eta-panel">
          {isRunningSeparation ? (
            <>
              <p className="eta-confidence">{processingReassurance(job)}</p>
              <div className="eta-grid">
                <span>
                  <small>Estimated time remaining</small>
                  <strong>{timing.estimatedSeparationRemainingMs ? `about ${formatApproxDurationMs(timing.estimatedSeparationRemainingMs)}` : "calculating after first chunks"}</strong>
                </span>
                <span>
                  <small>Elapsed</small>
                  <strong>{timing.elapsedMs ? formatDurationMs(timing.elapsedMs, { compact: true }) : "Starting"}</strong>
                </span>
                <span>
                  <small>Average</small>
                  <strong>{timing.recentAverageChunkMs || timing.averageChunkMs ? `${((timing.recentAverageChunkMs || timing.averageChunkMs) / 1000).toFixed(1)} sec / chunk` : "Measuring"}</strong>
                </span>
                <span>
                  <small>Chunks</small>
                  <strong>{Number.isFinite(timing.chunksCompleted) && Number.isFinite(timing.totalChunks) ? `${timing.chunksCompleted} of ${timing.totalChunks}` : "Pending"}</strong>
                </span>
              </div>
              {msSinceProgress > 90_000 ? (
                <p className="eta-warning">This is taking longer than usual. Diagnostics are still being recorded.</p>
              ) : msSinceProgress > 30_000 ? (
                <p className="eta-warning">Still processing this chunk...</p>
              ) : (
                <p className="eta-note">{processingReassurance(job)}</p>
              )}
            </>
          ) : (
            <div className="eta-grid">
              <span>
                <small>Completed in</small>
                <strong>{timing.elapsedMs ? formatDurationMs(timing.elapsedMs) : "Unavailable"}</strong>
              </span>
              <span>
                <small>Separation completed in</small>
                <strong>{completionTiming.separateMs ? formatDurationMs(completionTiming.separateMs) : "Unavailable"}</strong>
              </span>
            </div>
          )}
        </div>
      ) : null}
      <ol className="process-list" aria-label="Analysis processing steps">
        {steps.map((step, index) => (
          <li key={step.key} className={`process-step process-${step.state}`}>
            <span className="process-icon">
              {step.state === "completed" ? <CheckCircle2 size={18} /> : step.state === "failed" ? <XCircle size={18} /> : step.state === "active" ? <Loader2 className="spin" size={18} /> : index + 1}
            </span>
            <span>
              <strong>{step.label}</strong>
              <small>{step.detail}</small>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function WaveformPreview({ active }) {
  return (
    <div className={active ? "wave-preview wave-preview-active" : "wave-preview"} aria-hidden="true">
      {Array.from({ length: 42 }, (_, index) => (
        <span
          key={index}
          style={{
            height: `${18 + Math.abs(Math.sin(index / 2.2)) * (active ? 58 : 32)}%`,
            opacity: active ? 0.95 : 0.58,
          }}
        />
      ))}
    </div>
  );
}

function BottomNav({ activeTab, onChange }) {
  const items = [
    { key: "home", label: "Home", icon: Home },
    { key: "upload", label: "Upload", icon: CloudUpload },
    { key: "reports", label: "Reports", icon: Activity },
    { key: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <nav className="bottom-nav" aria-label="Primary navigation">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button key={item.key} className={activeTab === item.key ? "nav-item nav-item-active" : "nav-item"} type="button" onClick={() => onChange(item.key)}>
            <Icon size={22} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function RecentAnalysisCard({ job, onOpen, onViewAll }) {
  if (!job) {
    return (
      <section className="card recent-empty">
        <div className="card-title-row">
          <h2>Recent Analysis</h2>
          <span>No reports</span>
        </div>
        <p>Upload or record a sample to create your first vocal report.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="card-title-row">
        <h2>Recent Analysis</h2>
        <button type="button" onClick={onViewAll}>View all</button>
      </div>
      <button className="recent-row" type="button" onClick={onOpen}>
        <div className="song-icon">
          <Music2 size={24} />
        </div>
        <div>
          <strong>{jobTitle(job)}</strong>
          <span>{formatDateTime(job.createdAt)}</span>
        </div>
        <div className={`score-ring score-${reportTone(job)}`}>
          <strong>{reportScore(job)}</strong>
          <span>{reportGrade(job)}</span>
        </div>
      </button>
    </section>
  );
}

function HomeScreen({ latestJob, onUpload, onRecord, onReports, onOpenRecent, onQuickStart }) {
  return (
    <div className="screen-content">
      <AppHeader />

      <section className="hero-card">
        <div>
          <span>Welcome back,</span>
          <h1>Let’s make your voice stronger.</h1>
          <p>Upload or record a sample to get vocal insights, stem separation, and coaching cues.</p>
        </div>
        <div className="orb-logo">
          <LogoMark />
        </div>
      </section>

      <div className="primary-stack">
        <button className="primary-action" type="button" onClick={onUpload}>
          <CloudUpload size={23} />
          <span>Upload Vocal</span>
        </button>
        <button className="secondary-action" type="button" onClick={onRecord}>
          <Mic size={22} />
          <span>Record Sample</span>
        </button>
      </div>

      <RecentAnalysisCard job={latestJob} onOpen={() => latestJob ? onOpenRecent(latestJob) : onReports()} onViewAll={onReports} />

      <section className="quick-start">
        <h2>Quick Start</h2>
        <div className="quick-grid">
          <button type="button" onClick={() => onQuickStart("warmup")}>
            <LogoMark />
            <strong>Vocal Warmup</strong>
            <span>5 min · Start</span>
            <ChevronDown size={15} className="quick-chevron" />
          </button>
          <button type="button" onClick={() => onQuickStart("pitch")}>
            <Search size={28} />
            <strong>Pitch Check</strong>
            <span>Quick test · Start</span>
            <ChevronDown size={15} className="quick-chevron" />
          </button>
          <button type="button" onClick={() => onQuickStart("breath")}>
            <Waves size={28} />
            <strong>Breath Control</strong>
            <span>Exercise · Start</span>
            <ChevronDown size={15} className="quick-chevron" />
          </button>
        </div>
      </section>

      <button className="history-card" type="button" onClick={onReports}>
        <History size={31} />
        <span>
          <strong>History</strong>
          <small>You have recent reports. Review your progress</small>
        </span>
        <ChevronDown size={20} className="chevron-side" />
      </button>
    </div>
  );
}

function UploadScreen({
  currentJob,
  currentTake,
  uploadMode,
  backgroundStatus,
  status,
  isBusy,
  isCheckingBackground,
  isRecording,
  recordingTime,
  fileInputRef,
  onChooseFile,
  onFileInput,
  onRecord,
  onStartAnalysis,
  onCancel,
  onRequestBackgroundAccess,
  onOpenModePicker,
  previewAudioRef,
  isPreviewPlaying,
  previewCurrentTime,
  previewDuration,
  previewProgressPercent,
  previewError,
  onTogglePreview,
  onPreviewLoadedMetadata,
  onPreviewPlay,
  onPreviewPause,
  onPreviewEnded,
  onPreviewTimeUpdate,
  onPreviewError,
}) {
  const minutes = Math.floor(recordingTime / 60);
  const seconds = String(recordingTime % 60).padStart(2, "0");
  const quickTest = uploadMode === "quick-test";
  const modeLocked = Boolean(currentJob && !isTerminal(currentJob));
  const expectationCopy = quickTest
    ? "Quick Test: record 20-30 seconds for a quick pitch-centre and vocal energy check. This does not judge tuning accuracy."
    : estimateDetailedModeCopy(currentJob?.inputDurationMs || currentTake?.durationMs || null);

  return (
    <div className="screen-content">
      <AppHeader leading={<span className="back-spacer" />} />
      <section className="page-intro">
        <h1>Upload & Analysis Setup</h1>
        <p>{quickTest ? "Record 20-30 seconds for a quick pitch-centre and vocal energy check." : "Upload your song and configure analysis."}</p>
      </section>

      <section className="card upload-player-card">
        <div className="mini-player">
          <button type="button" aria-label={isPreviewPlaying ? "Pause selected audio" : "Preview selected audio"} onClick={onTogglePreview} disabled={!currentTake?.url}>
            {isPreviewPlaying ? <Pause size={20} /> : <Play size={20} />}
          </button>
          <audio
            ref={previewAudioRef}
            src={currentTake?.url || undefined}
            preload="metadata"
            hidden
            onLoadedMetadata={onPreviewLoadedMetadata}
            onPlay={onPreviewPlay}
            onPause={onPreviewPause}
            onEnded={onPreviewEnded}
            onTimeUpdate={onPreviewTimeUpdate}
            onError={onPreviewError}
          />
          <WaveformPreview active={isPreviewPlaying} />
        </div>
        <div className="player-times">
          <span>{formatPlaybackTime(previewCurrentTime)}</span>
          <span>{isRecording ? `${minutes}:${seconds}` : previewDuration ? formatPlaybackTime(previewDuration) : currentTake?.pendingAnalysis ? "Preview ready" : currentTake ? "Loaded" : "No file"}</span>
        </div>
        <div className="preview-progress" aria-label={`Preview playback progress ${Math.round(previewProgressPercent)}%`}>
          <span style={{ width: `${Math.max(0, Math.min(100, previewProgressPercent))}%` }} />
        </div>
        {previewError ? <p className="preview-error">{previewError}</p> : null}
        <button className="drop-zone" type="button" onClick={onChooseFile} disabled={isBusy}>
          <CloudUpload size={30} />
          <strong>{currentTake ? currentTake.fileName : "Drag & drop audio file here"}</strong>
          <span>{currentTake ? currentTake.sourceLabel : "MP3, WAV, M4A up to 100MB"}</span>
        </button>
        <input ref={fileInputRef} type="file" accept="audio/*" onChange={onFileInput} hidden />
        <div className="upload-actions">
          <button className="outline-blue" type="button" onClick={onChooseFile} disabled={isBusy}>
            <FolderOpen size={19} />
            Choose File
          </button>
          <button className="outline-teal" type="button" onClick={onStartAnalysis} disabled={isBusy}>
            <Waves size={19} />
            Separate Vocals
          </button>
        </div>
        <p className="mode-expectation">{expectationCopy}</p>
      </section>

      {EXECUTION_TARGET === "android-local" && backgroundStatus?.ready === false ? (
        <BackgroundProcessingCard status={backgroundStatus} onRequest={onRequestBackgroundAccess} isChecking={isCheckingBackground} />
      ) : null}

      <section className="settings-card">
        <h2>Settings</h2>
        <div className="settings-list">
          <div className="static-settings-row">
            <Music2 size={22} />
            <span>
              <strong>Song title</strong>
              <small>{currentTake?.fileName || "Someone Like You"}</small>
            </span>
          </div>
          <div className="static-settings-row">
            <Mic size={22} />
            <span>
              <strong>Singer</strong>
              <small>Lead vocal</small>
            </span>
          </div>
          <button className="settings-picker-row" type="button" onClick={onOpenModePicker} disabled={modeLocked}>
            <SlidersHorizontal size={22} />
            <span>
              <strong>Analysis mode</strong>
              <small>{modeLocked ? "Mode locked while processing" : analysisModeLabel(uploadMode)}</small>
            </span>
            {!modeLocked ? <ChevronDown size={18} /> : null}
          </button>
        </div>
      </section>

      <ProcessQueueCard job={currentJob} status={status} />

      <section className="card">
        <p className="status-line">{status}</p>
        <p className="input-debug-line">
          Selected: {currentTake?.fileName || "none"} · Source: {currentTake?.sourceLabel || currentJob?.sourceType || "none"} · Preview: {currentTake?.url ? "yes" : "no"} · Current job: {currentJob?.jobId || "none"} · Display: {sourceDebugLabel(currentTake, currentJob)}
        </p>
        <div className="start-row">
          <button className="primary-action" type="button" onClick={onStartAnalysis} disabled={isBusy}>
            {isBusy ? <Loader2 className="spin" size={20} /> : <Upload size={20} />}
            Start Analysis
          </button>
          {currentJob && !isTerminal(currentJob) ? (
            <button className="danger-action" type="button" onClick={onCancel}>
              Cancel
            </button>
          ) : null}
        </div>
      </section>

      <button className="secondary-action full" type="button" onClick={onRecord} disabled={isBusy}>
        <Mic size={21} />
        {isRecording ? `Stop Recording (${minutes}:${seconds})` : "Record Sample"}
      </button>
    </div>
  );
}

function MetricTile({ label, value, detail, tone }) {
  return (
    <article className={`metric-tile metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function renderCoachingList(items, fallback) {
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!list.length) return <p>{fallback}</p>;
  return list.map((item) => {
    if (typeof item === "string") return <p key={item}>• {item}</p>;
    return <p key={item.name || item.claim || item.field}>• {item.name || item.claim || item.interpretation}</p>;
  });
}

function CoachingDrill({ drill }) {
  if (!drill) return <p>No drill selected yet.</p>;
  const steps = Array.isArray(drill.steps) ? drill.steps.filter(Boolean) : [];
  const listenFor = Array.isArray(drill.whatToListenFor) ? drill.whatToListenFor.filter(Boolean) : [];
  return (
    <div className="drill-block">
      <strong>{drill.name || "Recommended Drill"}</strong>
      {drill.selectedBecause ? <p><b>Why:</b> {drill.selectedBecause}</p> : null}
      {steps.length ? steps.map((step) => <p key={step}>{step}</p>) : null}
      {listenFor.length ? (
        <div className="listen-list">
          <b>Listen for:</b>
          {listenFor.map((item) => <p key={item}>• {item}</p>)}
        </div>
      ) : null}
      {drill.quickVersion ? <p><b>Quick version:</b> {drill.quickVersion}</p> : null}
      {drill.sevenDayVersion ? <p><b>7-day version:</b> {drill.sevenDayVersion}</p> : null}
    </div>
  );
}

function rawMetricValue(value, digits = 2, suffix = "") {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(digits)}${suffix}` : "Not analysed";
}

function metricNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function compactEvidenceRows(currentJob) {
  const metrics = currentJob.analysis?.metrics || {};
  const raw = currentJob.analysis?.rawMetrics || {};
  const derived = currentJob.analysis?.derivedMetrics || {};
  const phrase = currentJob.analysis?.phraseMetrics || raw.phraseMetrics || metrics.phraseMetrics;
  const pitch = currentJob.analysis?.pitchStabilityMetrics || raw.pitchStabilityMetrics || metrics.pitchStabilityMetrics;
  const dynamicRobust = metricNumber(raw.dynamicRangeDbRobust ?? metrics.dynamicRangeDbRobust);
  const dynamicLegacy = metricNumber(raw.dynamicRangeDb ?? metrics.dynamicRangeDb);
  const rows = [
    {
      label: "Peak level",
      value: rawMetricValue(raw.peakAmplitude ?? metrics.peakAmplitude, 4),
      detail: derived.clippingRiskLabel || "Peak amplitude",
    },
    {
      label: "Average RMS",
      value: rawMetricValue(raw.averageRms ?? metrics.avgRms, 4),
      detail: derived.vocalEnergyLabel ? `${derived.vocalEnergyLabel} vocal energy` : "Vocal energy",
    },
    {
      label: "Dynamics",
      value: dynamicRobust !== null ? `${dynamicRobust.toFixed(1)} dB robust` : rawMetricValue(dynamicLegacy, 1, " dB estimate"),
      detail: dynamicRobust !== null && dynamicLegacy !== null ? `${dynamicLegacy.toFixed(1)} dB legacy` : derived.dynamicsLabel || "Dynamic movement",
    },
    {
      label: "Pitch centre",
      value: rawMetricValue(raw.averagePitchHz ?? metrics.avgPitchHz, 1, " Hz"),
      detail: derived.pitchBandLabel || "Average detected pitch, not a range test",
    },
    {
      label: "Crest factor",
      value: rawMetricValue(raw.crestFactor ?? metrics.avgCrestFactor, 2),
      detail: "Peakiness vs sustained level",
    },
  ];

  if (phrase) {
    rows.push({
      label: "Phrase consistency",
      value: phrase.phraseEnergyConsistencyScore != null ? `${Number(phrase.phraseEnergyConsistencyScore).toFixed(1)}/100` : "Measured",
      detail: phrase.phraseEnergyConsistencyLabel || "Phrase energy",
    });
  }
  if (pitch) {
    rows.push({
      label: "Pitch track",
      value: pitch.pitchStdDevCents != null ? `${Number(pitch.pitchStdDevCents).toFixed(1)} cents` : "Estimated",
      detail: `${pitch.pitchTrackVariabilityLabel || "Pitch variability"}; ${pitch.pitchTrackingConfidenceLabel || "limited"} confidence`,
    });
  }

  return rows.filter((row) => row.value !== "Not analysed");
}

function NotAnalysedList({ items }) {
  const values = Array.isArray(items) && items.length ? items : [
    "Timing accuracy",
    "Breath noise",
    "Breath support",
    "Vibrato",
    "Resonance",
    "Diction",
    "True vocal range",
    "Note-level tuning accuracy",
    "Vocal strain",
  ];
  const names = values.map((item) => (typeof item === "string" ? item : item.name)).filter(Boolean);
  return (
    <details className="not-analysed-details">
      <summary>VOX is not yet judging timing, breath support, vibrato, diction, strain, or true vocal range.</summary>
      <div className="not-analysed-chips">
        {names.map((name) => <span key={name}>{name}</span>)}
      </div>
      <div className="not-analysed-reasons">
        {values.map((item) => {
          if (typeof item === "string") return <p key={item}>• {item}</p>;
          return (
            <p key={item.name}>
              • {item.name}: {item.reason || item.status || "Not analysed yet"}
            </p>
          );
        })}
      </div>
    </details>
  );
}

function singerProfileText(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll("pitch-track", "pitch")
    .replaceAll("pitch track", "pitch")
    .replace("short clip limited data", "Short clip — limited analysis")
    .replace("balanced usable take", "Balanced usable take")
    .replace("pitch limited", "Pitch data limited")
    .replace("phrase inconsistent", "Phrase volume varies")
    .replace("wide dynamics", "Wide volume changes")
    .replace("peak heavy", "Loudness spikes")
    .replace("low energy safe peak", "Quieter vocal, safe peaks");
}

function evidenceLabel(field, fallback = "Evidence") {
  const labels = {
    "rawMetrics.averageRms": "Vocal level",
    "rawMetrics.peakAmplitude": "Peak level",
    "rawMetrics.dynamicRangeDbRobust": "Active volume range",
    "phraseMetrics.phraseEnergyConsistencyScore": "Phrase volume",
    "pitchStabilityMetrics.pitchStdDevCents": "Pitch movement",
    "pitchStabilityMetrics.usablePitchFrameRatio": "Clear pitch data",
    "issueScores.overallPriority": "Overall priority",
    "rawMetrics.analysedStem": "Analysed audio",
  };
  return labels[field] || fallback;
}

function formatEvidenceValue(field, value) {
  if (value == null) return "unavailable";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (field === "rawMetrics.peakAmplitude") return number.toFixed(4);
  if (field === "rawMetrics.averageRms") return number.toFixed(4);
  if (field === "rawMetrics.dynamicRangeDbRobust") return `${number.toFixed(1)} dB`;
  if (field === "phraseMetrics.phraseEnergyConsistencyScore") return `${number.toFixed(1)}/100`;
  if (field === "pitchStabilityMetrics.pitchStdDevCents") return `${number.toFixed(1)} cents`;
  if (field === "pitchStabilityMetrics.usablePitchFrameRatio") return number.toFixed(2);
  if (field === "issueScores.overallPriority") return `${number.toFixed(0)}/100`;
  return String(value);
}

function cleanEvidenceInterpretation(row) {
  const text = row.interpretation || row.detail || "";
  const value = row.value != null ? String(row.value) : "";
  return text.startsWith(value) ? "" : text;
}

function TechnicalEvidenceDetails({ evidence }) {
  if (!Array.isArray(evidence) || !evidence.some((row) => row?.field)) return null;
  return (
    <details className="technical-details">
      <summary>Technical details</summary>
      {evidence.map((row) => (
        <p key={row.field || row.label}>
          <strong>{row.field || row.label}:</strong> {row.value == null ? "unavailable" : String(row.value)}
        </p>
      ))}
    </details>
  );
}

function VocalProfileRows({ profile }) {
  if (!profile) return null;
  const rows = [
    ["Take type", profile.archetype],
    ["Pitch centre", profile.pitchCentreSummary],
    ["Energy", profile.energyProfile],
    ["Peak safety", profile.peakProfile],
    ["Volume range", profile.dynamicsProfile],
    ["Phrase profile", profile.phraseProfile],
    ["Pitch movement", profile.pitchTrackProfile],
  ].filter(([, value]) => value);
  return (
    <div className="profile-list">
      {rows.map(([label, value]) => (
        <p key={label}><strong>{label}:</strong> {singerProfileText(value)}</p>
      ))}
    </div>
  );
}

function EvidenceRows({ rows, fallbackRows }) {
  const evidence = Array.isArray(rows) && rows.length ? rows : fallbackRows;
  if (!evidence?.length) return <p>Evidence will appear when offline metrics are available.</p>;
  return (
    <>
      {evidence.map((row) => {
        if (typeof row === "string") return <p key={row}>• {row}</p>;
        const label = evidenceLabel(row.field, row.label);
        const value = formatEvidenceValue(row.field, row.value);
        const interpretation = cleanEvidenceInterpretation(row);
        return (
          <p key={`${row.field || row.label}-${row.claim || row.detail}`}>
            <strong>{label}:</strong> {value}{interpretation ? ` — ${interpretation}` : ""}
          </p>
        );
      })}
      <TechnicalEvidenceDetails evidence={evidence} />
    </>
  );
}

function AdvancedMetrics({ currentJob }) {
  const metrics = currentJob.analysis?.metrics || {};
  const raw = currentJob.analysis?.rawMetrics || {};
  const pitch = currentJob.analysis?.pitchStabilityMetrics || raw.pitchStabilityMetrics || metrics.pitchStabilityMetrics || {};
  return (
    <details className="advanced-metrics">
      <summary>Advanced Metrics</summary>
      <div className="advanced-grid">
        <p><strong>Raw pitch tracker extremes — not a vocal range test:</strong> {rawMetricValue(raw.pitchMinHz ?? metrics.minPitchHz, 1, " Hz")} to {rawMetricValue(raw.pitchMaxHz ?? metrics.maxPitchHz, 1, " Hz")}</p>
        <p><strong>Legacy dynamic range:</strong> {rawMetricValue(raw.dynamicRangeDb ?? metrics.dynamicRangeDb, 1, " dB")}</p>
        <p><strong>Robust dynamic range:</strong> {rawMetricValue(raw.dynamicRangeDbRobust ?? metrics.dynamicRangeDbRobust, 1, " dB")}</p>
        <p><strong>Silence ratio:</strong> {rawMetricValue(raw.silenceRatio ?? metrics.silenceRatio, 3)}</p>
        <p><strong>Sample rate:</strong> {rawMetricValue(raw.sampleRate ?? metrics.sampleRate, 0, " Hz")}</p>
        <p><strong>Frame count:</strong> {rawMetricValue(raw.frameCount ?? metrics.frameCount, 0)}</p>
        <p><strong>Average crest:</strong> {rawMetricValue(raw.crestFactor ?? metrics.avgCrestFactor, 2)}</p>
        <p><strong>Max crest:</strong> {rawMetricValue(raw.maxCrestFactor ?? metrics.maxCrestFactor, 2)}</p>
        <p><strong>Pitch usable frames:</strong> {rawMetricValue(pitch.usablePitchFrameCount, 0)}</p>
      </div>
    </details>
  );
}

function ResultsScreen({ currentJob, completionNotice, onUpload, onReports, onExportDiagnostics, isExportingDiagnostics }) {
  if (!currentJob) {
    return (
      <div className="screen-content">
        <AppHeader />
        <section className="empty-state">
          <FileAudio size={42} />
          <h1>No active analysis</h1>
          <p>Upload or record a vocal to see real analysis results here.</p>
          <button className="primary-action" type="button" onClick={onUpload}>
            <CloudUpload size={20} />
            Upload Vocal
          </button>
        </section>
      </div>
    );
  }

  const metrics = currentJob.analysis?.metrics;
  const rawMetrics = currentJob.analysis?.rawMetrics;
  const derivedMetrics = currentJob.analysis?.derivedMetrics;
  const coachOutput = currentJob.analysis?.coachOutput;
  const coaching = currentJob.analysis?.coachingSummary;
  const activeCoaching = coachOutput || coaching;
  const vocalProfile = currentJob.analysis?.vocalProfile || currentJob.analysis?.coachInput?.vocalProfile;
  const phraseMetrics = currentJob.analysis?.phraseMetrics || rawMetrics?.phraseMetrics || metrics?.phraseMetrics;
  const pitchStabilityMetrics = currentJob.analysis?.pitchStabilityMetrics || rawMetrics?.pitchStabilityMetrics || metrics?.pitchStabilityMetrics;
  const notImplemented = coachOutput?.notAnalysedYet || currentJob.analysis?.notImplemented || coaching?.notImplemented || rawMetrics?.notImplemented;
  const hasRobustDynamics = rawMetrics?.dynamicRangeDbRobust != null || metrics?.dynamicRangeDbRobust != null;
  const evidenceRows = compactEvidenceRows(currentJob);
  const summary =
    currentJob.error?.message ||
    coachOutput?.summary ||
    coaching?.summary ||
    currentJob.analysis?.summary?.text ||
    currentJob.progress?.message ||
    "Analysis data is pending. The panel will update as the manifest changes.";
  const timing = getProgressTiming(currentJob);
  const engineTimings = currentJob.engine?.timings || {};

  return (
    <div className="screen-content">
      <AppHeader trailing={<IconButton label="Share" onClick={onExportDiagnostics} disabled={isExportingDiagnostics || EXECUTION_TARGET !== "android-local"}><Share2 size={20} /></IconButton>} />
      <section className="page-intro">
        <h1>Analysis Results</h1>
        <p>Here’s what Howard VOX detected in your vocal.</p>
      </section>
      {completionNotice ? <section className="completion-banner">{completionNotice}</section> : null}

      <section className={`summary-card summary-${reportTone(currentJob)}`}>
        <div className="summary-icon">
          {currentJob.jobStatus === "failed" ? <XCircle size={22} /> : currentJob.jobStatus === "completed" ? <CheckCircle2 size={22} /> : <Loader2 className="spin" size={22} />}
        </div>
        <div>
          <span>Summary</span>
          <h2>{summary}</h2>
        </div>
      </section>

      <ProcessQueueCard job={currentJob} status={summary} />

      <section className="issue-card">
        <div className="issue-title drill">
          <Waves size={20} />
          <strong>Main Focus</strong>
        </div>
        <p>{coachOutput?.mainFocus || coaching?.mainFocus || coaching?.nextPracticeFocus || "Keep phrase control consistent across the take."}</p>
        {coachOutput?.detailedFeedback?.length ? renderCoachingList(coachOutput.detailedFeedback, "") : null}
      </section>

      <section className="issue-card">
        <div className="issue-title drill">
          <ClipboardIcon />
          <strong>Practice Drill</strong>
        </div>
        {coachOutput?.recommendedDrill ? (
          <CoachingDrill drill={coachOutput.recommendedDrill} />
        ) : coaching?.recommendedDrills?.length ? (
          coaching.recommendedDrills.slice(0, 2).map((drill) => <CoachingDrill key={drill.name} drill={drill} />)
        ) : (
          <p>{metrics ? "Review pitch and volume metrics, then repeat the phrase with steady delivery." : "Wait for analysis metrics before selecting a drill."}</p>
        )}
        {coachOutput?.practicePlan?.quickVersion ? <p>Plan: {coachOutput.practicePlan.quickVersion}</p> : null}
        {!coachOutput?.practicePlan?.quickVersion && coaching?.nextPracticeFocus ? <p>Next practice focus: {coaching.nextPracticeFocus}</p> : null}
      </section>

      <section className="issue-card">
        <div className="issue-title confidence">
          <Activity size={20} />
          <strong>Your Vocal Profile</strong>
        </div>
        <VocalProfileRows profile={vocalProfile} />
      </section>

      <div className="metrics-grid">
        <MetricTile label="Pitch Centre" value={rawMetricValue(rawMetrics?.averagePitchHz ?? metrics?.avgPitchHz, 1, " Hz")} detail={derivedMetrics?.pitchBandLabel || "Average detected pitch"} tone="blue" />
        <MetricTile label="Pitch Steadiness" value={pitchStabilityMetrics?.pitchStdDevCents != null ? `${Number(pitchStabilityMetrics.pitchStdDevCents).toFixed(1)} cents` : "Not analysed"} detail="Keeping pitch centred" tone="blue" />
        <MetricTile label="Vocal Energy" value={rawMetricValue(rawMetrics?.averageRms ?? metrics?.avgRms, 4)} detail={derivedMetrics?.vocalEnergyLabel ? `${derivedMetrics.vocalEnergyLabel} vocal level` : "RMS vocal level"} tone="cyan" />
        <MetricTile label="Phrase Consistency" value={phraseMetrics?.phraseEnergyConsistencyScore != null ? `${Number(phraseMetrics.phraseEnergyConsistencyScore).toFixed(1)}` : "Not analysed"} detail={phraseMetrics?.phraseEnergyConsistencyLabel || "Phrase energy consistency"} tone="cyan" />
      </div>

      <div className="metrics-grid">
        <MetricTile label="Active Volume Range" value={rawMetricValue(rawMetrics?.dynamicRangeDbRobust ?? metrics?.dynamicRangeDbRobust ?? rawMetrics?.dynamicRangeDb ?? metrics?.dynamicRangeDb, 1, " dB")} detail={hasRobustDynamics ? "Measured on active singing" : "Volume range estimate"} tone="amber" />
        <MetricTile label="Peak Level" value={rawMetricValue(rawMetrics?.peakAmplitude ?? metrics?.peakAmplitude, 4)} detail={derivedMetrics?.clippingRiskLabel || "Peak amplitude"} tone="teal" />
        <MetricTile label="Report Confidence" value={derivedMetrics?.confidenceLevel === "moderate-high" ? "Good" : derivedMetrics?.confidenceLevel || "Metric-based"} detail={derivedMetrics?.pitchTrackingConfidenceLabel === "good" ? "Pitch data was clear enough for cautious feedback." : "Pitch feedback is cautious."} tone="blue" />
      </div>

      <section className="issue-card">
        <div className="issue-title confidence">
          <CheckCircle2 size={20} />
          <strong>What Went Well</strong>
        </div>
        {renderCoachingList(coachOutput?.whatWentWell || coaching?.strengths, "The vocal was separated and analysed successfully. More strengths will appear as analysis expands.")}
      </section>

      <section className="issue-card">
        <div className="issue-title evidence">
          <Search size={20} />
          <strong>Why VOX Picked This</strong>
        </div>
        <div className="evidence-list">
          <EvidenceRows rows={coachOutput?.evidence} fallbackRows={evidenceRows} />
        </div>
        <p>Job status: {statusLabel(currentJob.jobStatus)}</p>
        <p>Separation: {statusLabel(currentJob.separationStatus)}</p>
        <p>Artifacts: {currentJob.outputs.length} stem output(s)</p>
        <p>Input size: {formatBytes(currentJob.inputSizeBytes)}</p>
        {currentJob.jobStatus === "completed" ? (
          <>
            <p>Completed in: {timing.elapsedMs ? formatDurationMs(timing.elapsedMs) : "Unavailable"}</p>
            <p>Separation completed in: {engineTimings.separateMs ? formatDurationMs(engineTimings.separateMs) : "Unavailable"}</p>
          </>
        ) : null}
      </section>

      <section className="issue-card">
        <div className="issue-title confidence">
          <CheckCircle2 size={20} />
          <strong>Confidence Note</strong>
        </div>
        <p>{activeCoaching?.confidenceNote || (currentJob.jobStatus === "completed" ? "Confidence is based on the supplied manifest and available offline metrics." : "Confidence will improve once processing completes.")}</p>
      </section>

      <section className="issue-card">
        <div className="issue-title evidence">
          <ListFilter size={20} />
          <strong>Not analysed yet</strong>
        </div>
        <NotAnalysedList items={notImplemented} />
      </section>

      <AdvancedMetrics currentJob={currentJob} />

      {EXECUTION_TARGET === "android-local" ? (
        <section className="issue-card diagnostics-card">
          <div className="issue-title evidence">
            <Share2 size={20} />
            <strong>Diagnostics</strong>
          </div>
          <p>Export support files from this phone.</p>
          <button className="secondary-action full" type="button" onClick={onExportDiagnostics} disabled={isExportingDiagnostics}>
            {isExportingDiagnostics ? <Loader2 className="spin" size={20} /> : <Share2 size={20} />}
            Export Diagnostics
          </button>
        </section>
      ) : null}

      <button className="secondary-action full" type="button" onClick={onReports}>
        <History size={20} />
        Open Reports
      </button>
    </div>
  );
}

function ClipboardIcon() {
  return <FileAudio size={20} />;
}

function ReportsScreen({ reports, onOpen, onExportDiagnostics, isExportingDiagnostics, canExportDiagnostics }) {
  return (
    <div className="screen-content">
      <AppHeader />
      <section className="page-intro page-intro-row">
        <div>
          <h1>Reports</h1>
          <p>Review your past vocal analyses.</p>
        </div>
        {EXECUTION_TARGET === "android-local" && canExportDiagnostics ? (
          <button className="export-button" type="button" onClick={onExportDiagnostics} disabled={isExportingDiagnostics}>
            {isExportingDiagnostics ? <Loader2 className="spin" size={16} /> : <Share2 size={16} />}
            Export / Share
          </button>
        ) : null}
      </section>

      <div className="filter-row">
        <span className="filter-chip-static">All Songs</span>
        <span className="filter-chip-static">All Modes</span>
        <span className="filter-chip-static">All Status</span>
      </div>

      <section className="report-list">
        {reports.length ? (
          reports.map((report) => (
            <button key={report.id} className="report-row" type="button" onClick={() => onOpen(report.job)}>
              <div className="song-icon">
                <Music2 size={24} />
              </div>
              <div>
                <strong>{jobTitle(report.job)}</strong>
                <span>{formatDateTime(report.createdAt)}</span>
              </div>
              <div className={`score-ring score-${reportTone(report.job)}`}>
                <strong>{reportScore(report.job)}</strong>
                <span>{reportGrade(report.job)}</span>
              </div>
              <em>Open</em>
            </button>
          ))
        ) : (
          <div className="empty-state compact">
            <History size={34} />
            <h2>No reports yet</h2>
            <p>Completed analyses will appear here automatically.</p>
          </div>
        )}
      </section>
      <p className="list-count">Showing {reports.length ? `1-${reports.length}` : "0"} of {reports.length} reports</p>
    </div>
  );
}

function BackgroundProcessingCard({ status, onRequest, isChecking }) {
  const ready = Boolean(status?.ready);
  const notificationReady = status?.notificationsGranted !== false;
  const batteryReady = status?.batteryOptimizationIgnored !== false;
  const message = status?.message || "Allow background processing before running long vocal separations.";

  return (
    <section className={`settings-card large background-card ${ready ? "background-ready" : "background-needs-access"}`}>
      <div className="card-title-row">
        <h2>Background processing</h2>
        <span>{ready ? "Ready" : "Needs approval"}</span>
      </div>
      <p className="settings-copy">{message}</p>
      <div className="background-checks">
        <span className={notificationReady ? "check-good" : "check-warn"}>
          {notificationReady ? <CheckCircle2 size={17} /> : <XCircle size={17} />}
          Notifications
        </span>
        <span className={batteryReady ? "check-good" : "check-warn"}>
          {batteryReady ? <CheckCircle2 size={17} /> : <XCircle size={17} />}
          Battery unrestricted
        </span>
        <span className="check-good">
          <CheckCircle2 size={17} />
          Foreground service
        </span>
        <span className="check-good">
          <CheckCircle2 size={17} />
          Wake lock
        </span>
      </div>
      <button className="primary-action full" type="button" onClick={onRequest} disabled={isChecking || EXECUTION_TARGET !== "android-local"}>
        {isChecking ? <Loader2 className="spin" size={19} /> : <Bell size={19} />}
        {ready ? "Recheck background access" : "Allow background processing"}
      </button>
      {!ready ? <p className="settings-hint">If Android opens app settings, set battery usage to unrestricted and allow notifications.</p> : null}
    </section>
  );
}

function SettingsScreen({
  currentJob,
  reports,
  backgroundStatus,
  onRequestBackgroundAccess,
  isCheckingBackground,
  onExportActiveDiagnostics,
  onExportLatestDiagnostics,
  onCopyActiveJobId,
  onResetAppData,
  isExportingDiagnostics,
  isResettingAppData,
}) {
  const timing = getProgressTiming(currentJob);
  const running = currentJob && !isTerminal(currentJob);
  return (
    <div className="screen-content">
      <AppHeader />
      <section className="page-intro">
        <h1>Settings</h1>
        <p>Local Android pipeline and app status.</p>
      </section>
      <BackgroundProcessingCard status={backgroundStatus} onRequest={onRequestBackgroundAccess} isChecking={isCheckingBackground} />
      <section className="settings-card large">
        <div className="settings-list">
          <div>
            <Activity size={22} />
            <span>
              <strong>Execution target</strong>
              <small>{EXECUTION_TARGET}</small>
            </span>
          </div>
          <div>
            <FileAudio size={22} />
            <span>
              <strong>Active job</strong>
              <small>{currentJob?.jobId || "None"}</small>
            </span>
          </div>
          <div>
            <History size={22} />
            <span>
              <strong>Saved reports</strong>
              <small>{reports.length}</small>
            </span>
          </div>
        </div>
      </section>
      {EXECUTION_TARGET === "android-local" && currentJob?.jobId ? (
        <section className="settings-card large">
          <div className="card-title-row">
            <h2>Job timing</h2>
            <span>{running ? "Running" : statusLabel(currentJob.jobStatus)}</span>
          </div>
          <div className="settings-list">
            <div>
              <Activity size={22} />
              <span>
                <strong>Elapsed time</strong>
                <small>{timing.elapsedMs ? formatDurationMs(timing.elapsedMs) : "Unavailable"}</small>
              </span>
            </div>
            <div>
              <Clock size={22} />
              <span>
                <strong>Last progress update</strong>
                <small>{timing.lastProgressAt ? formatDateTime(timing.lastProgressAt) : "Unavailable"}</small>
              </span>
            </div>
            <div>
              <Waves size={22} />
              <span>
                <strong>Current chunk</strong>
                <small>{Number.isFinite(timing.chunksCompleted) && Number.isFinite(timing.totalChunks) ? `${timing.chunksCompleted} of ${timing.totalChunks}` : "Unavailable"}</small>
              </span>
            </div>
            <div>
              <Loader2 size={22} />
              <span>
                <strong>ETA</strong>
                <small>{running && timing.estimatedTotalRemainingMs ? `about ${formatApproxDurationMs(timing.estimatedTotalRemainingMs)}` : running ? "Calculating" : "Complete"}</small>
              </span>
            </div>
          </div>
        </section>
      ) : null}
      {EXECUTION_TARGET === "android-local" ? (
        <section className="settings-card large">
          <div className="card-title-row">
            <h2>Diagnostics</h2>
            <span>{currentJob?.jobId ? "Job available" : "Latest job"}</span>
          </div>
          <p className="settings-copy">Export stalled or incomplete job evidence from this phone without adb.</p>
          {currentJob?.jobId ? (
            <>
              <button className="secondary-action full" type="button" onClick={onExportActiveDiagnostics} disabled={isExportingDiagnostics}>
                {isExportingDiagnostics ? <Loader2 className="spin" size={20} /> : <Share2 size={20} />}
                Export Active Job Diagnostics
              </button>
              <button className="secondary-action full" type="button" onClick={onCopyActiveJobId}>
                <Clipboard size={20} />
                Copy Active Job ID
              </button>
            </>
          ) : null}
          <button className="secondary-action full" type="button" onClick={onExportLatestDiagnostics} disabled={isExportingDiagnostics}>
            {isExportingDiagnostics ? <Loader2 className="spin" size={20} /> : <Share2 size={20} />}
            Export Latest Job Diagnostics
          </button>
        </section>
      ) : null}
      <section className="settings-card large danger-zone-card">
        <div className="card-title-row">
          <h2>App data</h2>
          <span>Reset</span>
        </div>
        <p className="settings-copy">Clear saved reports, active jobs, cached audio, diagnostics, and local app state from this device.</p>
        <p className="settings-hint">Files already exported to Downloads may need to be removed manually.</p>
        <button className="danger-action full" type="button" onClick={onResetAppData} disabled={isResettingAppData}>
          {isResettingAppData ? <Loader2 className="spin" size={19} /> : <XCircle size={19} />}
          Reset Howard VOX
        </button>
      </section>
    </div>
  );
}

function QuickGuideScreen({ guide, elapsedSeconds, isRunning, onStartPause, onReset, onClose }) {
  const warmup = guide === "warmup";
  const duration = warmup ? 5 * 60 : 12;
  const totalElapsed = Math.max(0, elapsedSeconds);
  const remaining = warmup ? Math.max(0, duration - totalElapsed) : duration - (totalElapsed % duration);
  const cycleSecond = totalElapsed % 12;
  const breathPhase = cycleSecond < 4 ? "Inhale" : cycleSecond < 6 ? "Hold" : "Exhale";
  const breathPhaseDetail = cycleSecond < 4 ? "Breathe in gently through the nose." : cycleSecond < 6 ? "Keep shoulders relaxed." : "Release slowly and evenly.";
  const progress = warmup ? Math.min(100, (totalElapsed / duration) * 100) : ((cycleSecond + 1) / duration) * 100;
  const steps = warmup
    ? [
        ["Gentle hum", "Relax the jaw and hum lightly."],
        ["Lip trill", "Keep airflow easy and steady."],
        ["Siren glide", "Slide gently from low to high and back."],
        ["Easy vowel sustain", "Hold an easy vowel without pushing."],
      ]
    : [
        ["Inhale 4 sec", "Quiet, low breath."],
        ["Hold 2 sec", "Stay relaxed."],
        ["Exhale 6 sec", "Smooth controlled release."],
        ["Repeat", "This is a guided exercise only."],
      ];

  return (
    <div className="screen-content">
      <AppHeader
        leading={<IconButton label="Back" onClick={onClose}><ChevronDown className="back-icon" size={20} /></IconButton>}
        trailing={<IconButton label="Reset" onClick={onReset}><Clock size={20} /></IconButton>}
      />
      <section className="page-intro">
        <h1>{quickGuideTitle(guide)}</h1>
        <p>{warmup ? "A simple 5-minute frontend-only warmup. No analysis or metrics are produced." : "Breath analysis is not available yet. This is a guided exercise only."}</p>
      </section>

      <section className="summary-card quick-guide-hero">
        <div className="summary-icon">
          {warmup ? <LogoMark /> : <Waves size={22} />}
        </div>
        <div>
          <span>{warmup ? "Timer" : breathPhase}</span>
          <h2>{warmup ? formatPlaybackTime(remaining) : `${remaining}s`}</h2>
          <p>{warmup ? "Move through the steps at an easy volume." : breathPhaseDetail}</p>
        </div>
      </section>

      <div className="preview-progress guide-progress" aria-label={`Guide progress ${Math.round(progress)}%`}>
        <span style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
      </div>

      <section className="card quick-guide-card">
        <h2>{warmup ? "Warmup steps" : "Breathing pattern"}</h2>
        <div className="guide-steps">
          {steps.map(([title, detail], index) => (
            <article key={title}>
              <span>{index + 1}</span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </article>
          ))}
        </div>
      </section>

      <div className="start-row">
        <button className="primary-action" type="button" onClick={onStartPause}>
          {isRunning ? <Pause size={20} /> : <Play size={20} />}
          {isRunning ? "Pause" : "Start"}
        </button>
        <button className="secondary-action" type="button" onClick={onReset}>
          Reset
        </button>
      </div>
    </div>
  );
}

function ResetConfirmationDialog({ onCancel, onConfirm, isResetting }) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="reset-dialog" role="dialog" aria-modal="true" aria-labelledby="reset-dialog-title">
        <div className="issue-title warning">
          <XCircle size={22} />
          <strong id="reset-dialog-title">Reset Howard VOX?</strong>
        </div>
        <p>This will clear saved reports, active jobs, cached audio, diagnostics, and local app state on this device. This cannot be undone.</p>
        <p className="settings-hint">Diagnostics ZIP files already exported to Downloads may need to be removed manually.</p>
        <div className="dialog-actions">
          <button className="secondary-action" type="button" onClick={onCancel} disabled={isResetting}>
            Cancel
          </button>
          <button className="danger-action" type="button" onClick={onConfirm} disabled={isResetting}>
            {isResetting ? <Loader2 className="spin" size={18} /> : <XCircle size={18} />}
            Reset App
          </button>
        </div>
      </section>
    </div>
  );
}

function AnalysisModeDialog({ currentMode, onSelect, onCancel }) {
  const options = [
    {
      key: "quick-test",
      title: "Quick Test",
      detail: "Best for 20-30 second clips. Checks pitch centre, vocal energy, peak level, and basic pitch movement.",
    },
    {
      key: "detailed",
      title: "Detailed",
      detail: "Best for fuller vocal analysis. Takes longer and gives more phrase and volume feedback.",
    },
    {
      key: "full-song-local",
      title: "Full Song Local",
      detail: "Processes the whole song on this phone. Can take several minutes.",
    },
  ];

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="reset-dialog mode-dialog" role="dialog" aria-modal="true" aria-labelledby="mode-dialog-title">
        <div className="issue-title evidence">
          <SlidersHorizontal size={22} />
          <strong id="mode-dialog-title">Choose analysis mode</strong>
        </div>
        <div className="mode-options">
          {options.map((option) => (
            <button key={option.key} type="button" className={option.key === currentMode ? "mode-option selected" : "mode-option"} onClick={() => onSelect(option.key)}>
              <span>
                <strong>{option.title}</strong>
                <small>{option.detail}</small>
              </span>
              {option.key === currentMode ? <CheckCircle2 size={20} /> : null}
            </button>
          ))}
        </div>
        <button className="secondary-action full" type="button" onClick={onCancel}>Cancel</button>
      </section>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("home");
  const [reports, setReports] = useState(() => readReports());
  const [currentJob, setCurrentJob] = useState(null);
  const [currentTake, setCurrentTake] = useState(null);
  const [status, setStatus] = useState("Ready for vocal analysis");
  const [isBusy, setIsBusy] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [pollNotice, setPollNotice] = useState("");
  const [backgroundStatus, setBackgroundStatus] = useState(null);
  const [isCheckingBackground, setIsCheckingBackground] = useState(false);
  const [isExportingDiagnostics, setIsExportingDiagnostics] = useState(false);
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const [previewCurrentTime, setPreviewCurrentTime] = useState(0);
  const [previewDuration, setPreviewDuration] = useState(0);
  const [previewError, setPreviewError] = useState("");
  const [currentSubmittedJobId, setCurrentSubmittedJobId] = useState(null);
  const [displayedReportJobId, setDisplayedReportJobId] = useState(null);
  const [completionNotice, setCompletionNotice] = useState("");
  const [uploadMode, setUploadMode] = useState("detailed");
  const [activeGuide, setActiveGuide] = useState(null);
  const [guideElapsedSeconds, setGuideElapsedSeconds] = useState(0);
  const [isGuideRunning, setIsGuideRunning] = useState(false);
  const [showResetDialog, setShowResetDialog] = useState(false);
  const [showModeDialog, setShowModeDialog] = useState(false);
  const [isResettingAppData, setIsResettingAppData] = useState(false);

  const fileInputRef = useRef(null);
  const previewAudioRef = useRef(null);
  const previewObjectUrlRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const streamRef = useRef(null);
  const currentJobRef = useRef(null);
  const currentTakeRef = useRef(null);
  const currentSubmittedJobIdRef = useRef(null);
  const pollTimerRef = useRef(null);
  const jobRequestInFlightRef = useRef(false);
  const savedJobIdsRef = useRef(new Set(reports.map((report) => report.job?.jobId).filter(Boolean)));

  useEffect(() => {
    writeReports(reports);
  }, [reports]);

  useEffect(() => {
    currentJobRef.current = currentJob;
  }, [currentJob]);

  useEffect(() => {
    currentTakeRef.current = currentTake;
  }, [currentTake]);

  useEffect(() => {
    currentSubmittedJobIdRef.current = currentSubmittedJobId;
  }, [currentSubmittedJobId]);

  useEffect(() => {
    let cancelled = false;
    async function loadBackgroundStatus() {
      try {
        const nextStatus = await getBackgroundProcessingStatus();
        if (!cancelled) setBackgroundStatus(nextStatus);
      } catch {
        if (!cancelled) {
          setBackgroundStatus({
            ready: false,
            notificationsGranted: false,
            batteryOptimizationIgnored: false,
            message: "Could not read Android background processing status.",
          });
        }
      }
    }

    void loadBackgroundStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (EXECUTION_TARGET !== "android-local" || currentJobRef.current || currentTakeRef.current?.pendingAnalysis || currentSubmittedJobIdRef.current) return undefined;
    let cancelled = false;
    async function recoverLatestJob() {
      try {
        const latest = await getLatestJob();
        if (!cancelled && latest?.jobId && !currentJobRef.current && !currentTakeRef.current?.pendingAnalysis && !currentSubmittedJobIdRef.current) {
          setCurrentJob(latest);
          setCurrentTake({
            fileName: latest.inputFileName || latest.title || "Recovered Android job",
            sourceLabel: "recovered job",
            url: null,
            pendingAnalysis: false,
            jobId: latest.jobId,
          });
          setStatus(`Recovered latest Android job: ${statusLabel(latest.jobStatus)}`);
        }
      } catch {
        // No previous Android job is a normal first-run state.
      }
    }

    void recoverLatestJob();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isRecording) return undefined;
    const interval = window.setInterval(() => setRecordingTime((value) => value + 1), 1000);
    return () => window.clearInterval(interval);
  }, [isRecording]);

  useEffect(() => {
    if (!activeGuide || !isGuideRunning) return undefined;
    const interval = window.setInterval(() => {
      setGuideElapsedSeconds((value) => {
        const next = value + 1;
        if (activeGuide === "warmup" && next >= 5 * 60) {
          setIsGuideRunning(false);
          return 5 * 60;
        }
        return next;
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [activeGuide, isGuideRunning]);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current);
      if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop());
      if (previewObjectUrlRef.current) URL.revokeObjectURL(previewObjectUrlRef.current);
    };
  }, []);

  useEffect(() => {
    const audio = previewAudioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
    audio.load();
    setIsPreviewPlaying(false);
    setPreviewCurrentTime(0);
    setPreviewDuration(0);
    setPreviewError("");
  }, [currentTake?.url]);

  useEffect(() => {
    if (!currentJob || !isTerminal(currentJob) || savedJobIdsRef.current.has(currentJob.jobId)) return;
    savedJobIdsRef.current.add(currentJob.jobId);
    setReports((existing) => [
      {
        id: `${currentJob.jobId}-${Date.now()}`,
        createdAt: new Date().toISOString(),
        job: currentJob,
      },
      ...existing,
    ].slice(0, 12));
  }, [currentJob]);

  useEffect(() => {
    if (!currentJob?.jobId || currentJob.jobStatus !== "completed") return;
    if (currentSubmittedJobId !== currentJob.jobId || displayedReportJobId === currentJob.jobId) return;
    setDisplayedReportJobId(currentJob.jobId);
    setCompletionNotice("Analysis complete - showing your new result.");
    setStatus("Analysis complete - showing your new result.");
    setActiveTab("results");
    window.setTimeout(() => window.scrollTo({ top: 0, behavior: "smooth" }), 0);
  }, [currentJob, currentSubmittedJobId, displayedReportJobId]);

  async function requestJobUpdate(jobId) {
    if (!jobId || jobRequestInFlightRef.current) return null;
    jobRequestInFlightRef.current = true;
    try {
      const refreshedJob = await fetchJob(jobId);
      setCurrentJob((existing) => (existing?.jobId === refreshedJob.jobId ? refreshedJob : existing));
      return refreshedJob;
    } finally {
      jobRequestInFlightRef.current = false;
    }
  }

  useEffect(() => {
    if (pollTimerRef.current) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    const initialJob = currentJobRef.current;
    if (!initialJob?.jobId || isTerminal(initialJob)) {
      setPollNotice("");
      return undefined;
    }

    let cancelled = false;
    let errorCount = 0;
    const startedAt = Date.now();
    const jobId = initialJob.jobId;

    async function runPoll() {
      const snapshot = currentJobRef.current;
      if (cancelled || !snapshot || snapshot.jobId !== jobId) return;
      if (isTerminal(snapshot)) {
        setPollNotice("");
        return;
      }
      const isLongRunning = Date.now() - startedAt > POLL_LONG_RUNNING_NOTICE_MS;

      try {
        const refreshed = await requestJobUpdate(jobId);
        if (cancelled) return;
        errorCount = 0;
        if (refreshed && !isTerminal(refreshed)) {
          setPollNotice(isLongRunning ? `${refreshed.progress?.message || "Still processing."} Keep VOX open if possible.` : refreshed.progress?.message || "Checking job state automatically.");
          pollTimerRef.current = window.setTimeout(runPoll, POLL_INTERVAL_MS);
        }
      } catch {
        errorCount += 1;
        if (errorCount >= MAX_POLL_ERRORS) {
          setPollNotice("Connection issue while checking the job. Manual refresh may be needed.");
          return;
        }
        pollTimerRef.current = window.setTimeout(runPoll, POLL_INTERVAL_MS);
      }
    }

    setPollNotice(initialJob.progress?.message || "Checking job state automatically.");
    void runPoll();

    return () => {
      cancelled = true;
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current);
    };
  }, [currentJob?.jobId]);

  function createPreviewUrl(file) {
    if (!file) return null;
    if (previewObjectUrlRef.current) URL.revokeObjectURL(previewObjectUrlRef.current);
    const url = URL.createObjectURL(file);
    previewObjectUrlRef.current = url;
    return url;
  }

  function beginNewInput({ file, fileName, sourceLabel, url, durationMs = null }) {
    const nextTake = {
      id: `take-${Date.now()}`,
      file,
      fileName: safeFileName(fileName || file?.name),
      sourceLabel,
      url,
      durationMs,
      pendingAnalysis: true,
      jobId: null,
    };
    setCurrentJob(null);
    currentJobRef.current = null;
    setCurrentSubmittedJobId(null);
    currentSubmittedJobIdRef.current = null;
    setDisplayedReportJobId(null);
    setCompletionNotice("");
    setCurrentTake(nextTake);
    currentTakeRef.current = nextTake;
    setPollNotice("");
    setStatus(`Ready to analyse ${nextTake.fileName}. Press Separate Vocals when ready.`);
    setActiveTab("upload");
  }

  function openQuickGuide(guide) {
    setActiveGuide(guide);
    setGuideElapsedSeconds(0);
    setIsGuideRunning(false);
    setActiveTab("guide");
    setStatus(`${quickGuideTitle(guide)} opened.`);
  }

  function openPitchCheck() {
    setUploadMode("quick-test");
    setCompletionNotice("");
    if (currentJobRef.current && isTerminal(currentJobRef.current)) {
      setCurrentJob(null);
      currentJobRef.current = null;
      setCurrentSubmittedJobId(null);
      currentSubmittedJobIdRef.current = null;
      setDisplayedReportJobId(null);
    }
    setPollNotice("");
    setStatus("Quick Test mode: record 20-30 seconds, preview it, then tap Separate Vocals.");
    setActiveTab("upload");
  }

  function openModePicker() {
    if (currentJobRef.current && !isTerminal(currentJobRef.current)) {
      setStatus("Mode locked while processing.");
      return;
    }
    setShowModeDialog(true);
  }

  function selectAnalysisMode(mode) {
    setUploadMode(mode);
    setShowModeDialog(false);
    if (mode === "quick-test") {
      setStatus("Quick Test mode: record 20-30 seconds, preview it, then tap Separate Vocals.");
    } else if (mode === "full-song-local") {
      setStatus("Full Song Local mode: processing can take several minutes on this phone.");
    } else {
      setStatus("Detailed mode selected for fuller phrase and volume feedback.");
    }
  }

  function handleQuickStart(kind) {
    if (kind === "warmup") {
      openQuickGuide("warmup");
      return;
    }
    if (kind === "breath") {
      openQuickGuide("breath");
      return;
    }
    if (kind === "pitch") {
      openPitchCheck();
    }
  }

  function openSpecificReport(job) {
    if (!job) {
      setActiveTab("reports");
      return;
    }
    setCurrentJob(job);
    setCurrentSubmittedJobId(null);
    currentSubmittedJobIdRef.current = null;
    setDisplayedReportJobId(job.jobId);
    setCompletionNotice("");
    setCurrentTake({
      fileName: job.inputFileName || job.title || "Saved report",
      sourceLabel: "saved report",
      url: null,
      pendingAnalysis: false,
      jobId: job.jobId,
    });
    setActiveTab("results");
  }

  function resetFrontendState() {
    const audio = previewAudioRef.current;
    if (audio) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    }
    if (previewObjectUrlRef.current) {
      URL.revokeObjectURL(previewObjectUrlRef.current);
      previewObjectUrlRef.current = null;
    }
    if (pollTimerRef.current) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
    recordedChunksRef.current = [];
    currentJobRef.current = null;
    currentTakeRef.current = null;
    currentSubmittedJobIdRef.current = null;
    savedJobIdsRef.current = new Set();
    jobRequestInFlightRef.current = false;

    clearVoxBrowserStorage();
    setReports([]);
    setCurrentJob(null);
    setCurrentTake(null);
    setCurrentSubmittedJobId(null);
    setDisplayedReportJobId(null);
    setCompletionNotice("");
    setStatus("Howard VOX has been reset.");
    setIsBusy(false);
    setIsRecording(false);
    setRecordingTime(0);
    setPollNotice("");
    setIsPreviewPlaying(false);
    setPreviewCurrentTime(0);
    setPreviewDuration(0);
    setPreviewError("");
    setUploadMode("detailed");
    setActiveGuide(null);
    setGuideElapsedSeconds(0);
    setIsGuideRunning(false);
    setActiveTab("home");
  }

  function requestResetAppData() {
    if (currentJobRef.current && !isTerminal(currentJobRef.current)) {
      setStatus("A job is currently running. Cancel the job before resetting.");
      return;
    }
    setShowResetDialog(true);
  }

  async function confirmResetAppData() {
    if (currentJobRef.current && !isTerminal(currentJobRef.current)) {
      setShowResetDialog(false);
      setStatus("A job is currently running. Cancel the job before resetting.");
      return;
    }
    setIsResettingAppData(true);
    try {
      await resetAppData();
      resetFrontendState();
      setShowResetDialog(false);
    } catch (error) {
      resetFrontendState();
      setShowResetDialog(false);
      setStatus(`Reset partially failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsResettingAppData(false);
    }
  }

  function applyJob(job, sourceLabel = "uploaded file") {
    setCurrentJob(job);
    setCurrentTake((existing) => {
      const nextTake = {
        ...(existing || {}),
        fileName: job.inputFileName || existing?.fileName || job.title || "Untitled vocal",
        sourceLabel: existing?.sourceLabel || sourceLabel,
        url: existing?.url || null,
        pendingAnalysis: false,
        jobId: job.jobId,
      };
      currentTakeRef.current = nextTake;
      return nextTake;
    });
    setStatus(job.jobStatus === "failed" ? `Analysis failed: ${job.error?.message || "See results."}` : `Analysis started: ${statusLabel(job.jobStatus)}`);
    setActiveTab(job.jobStatus === "failed" ? "results" : "upload");
  }

  async function requestBackgroundAccess() {
    setIsCheckingBackground(true);
    setStatus("Opening Android background processing approval...");
    try {
      const nextStatus = await requestBackgroundProcessingAccess();
      setBackgroundStatus(nextStatus);
      setStatus(nextStatus?.message || "Background processing status updated.");
    } catch (error) {
      setStatus(`Background approval failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsCheckingBackground(false);
      window.setTimeout(async () => {
        try {
          setBackgroundStatus(await getBackgroundProcessingStatus());
        } catch {
          // The visible status message already explains the failure path.
        }
      }, 1200);
    }
  }

  async function chooseFile() {
    if (isBusy) return;
    fileInputRef.current?.click();
  }

  function handleFileInput(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    beginNewInput({
      file,
      fileName: file.name,
      sourceLabel: "uploaded file",
      url: createPreviewUrl(file),
    });
    event.target.value = "";
  }

  async function startRecording() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setStatus("Finalizing recording...");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("Microphone recording is not available on this device.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredMime = ["audio/mp4;codecs=mp4a.40.2", "audio/mp4", "audio/webm;codecs=opus", "audio/webm"].find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
      const recorder = preferredMime ? new MediaRecorder(stream, { mimeType: preferredMime }) : new MediaRecorder(stream);

      recordedChunksRef.current = [];
      streamRef.current = stream;
      mediaRecorderRef.current = recorder;
      setRecordingTime(0);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(recordedChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const extension = blob.type.includes("mp4") ? "m4a" : "webm";
        const file = new File([blob], `howard-vox-recording-${Date.now()}.${extension}`, { type: blob.type });
        stream.getTracks().forEach((track) => track.stop());
        setIsRecording(false);
        beginNewInput({
          file,
          fileName: file.name,
          sourceLabel: "recorded sample",
          url: createPreviewUrl(file),
          durationMs: recordingTime * 1000,
        });
      };

      recorder.start(250);
      setIsRecording(true);
      setStatus("Recording sample...");
      setActiveTab("upload");
    } catch {
      setStatus("Microphone permission was blocked or unavailable.");
    }
  }

  async function cancelCurrentJob() {
    if (!currentJob?.jobId || isTerminal(currentJob) || EXECUTION_TARGET !== "android-local") return;
    try {
      const cancelled = await cancelJob(currentJob.jobId);
      setCurrentJob(cancelled);
      setStatus("Job cancelled.");
    } catch (error) {
      setStatus(`Could not cancel job: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function exportDiagnosticsFor(jobId, label) {
    if (EXECUTION_TARGET !== "android-local") {
      setStatus("Diagnostics export is only available in the Android app.");
      return;
    }

    setIsExportingDiagnostics(true);
    setStatus(`Preparing ${label} diagnostics export...`);
    try {
      const result = await exportDiagnostics(jobId);
      setStatus(result?.shared ? "Diagnostics export opened." : "Diagnostics export prepared.");
    } catch (error) {
      setStatus(`Diagnostics export failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsExportingDiagnostics(false);
    }
  }

  async function exportActiveDiagnostics() {
    const jobId = currentJobRef.current?.jobId;
    if (!jobId) {
      setStatus("No active job is loaded. Use Export Latest Job Diagnostics instead.");
      return;
    }
    await exportDiagnosticsFor(jobId, "active job");
  }

  async function exportLatestDiagnostics() {
    await exportDiagnosticsFor(undefined, "latest job");
  }

  async function copyActiveJobId() {
    const jobId = currentJobRef.current?.jobId;
    if (!jobId) {
      setStatus("No active job ID is loaded.");
      return;
    }

    try {
      await navigator.clipboard?.writeText(jobId);
      setStatus(`Copied active job ID: ${jobId}`);
    } catch {
      setStatus(`Active job ID: ${jobId}`);
    }
  }

  async function togglePreviewPlayback() {
    const audio = previewAudioRef.current;
    const take = currentTakeRef.current;
    if (!audio || !take?.url) {
      setStatus("No playable audio preview is loaded yet.");
      return;
    }

    try {
      if (!audio.paused) {
        audio.pause();
        return;
      }
      await audio.play();
    } catch (error) {
      setIsPreviewPlaying(false);
      setStatus(`Audio preview failed: ${error instanceof Error ? error.message : "This file could not be played by the device."}`);
    }
  }

  function handlePreviewLoadedMetadata(event) {
    const duration = Number(event.currentTarget.duration);
    setPreviewDuration(Number.isFinite(duration) ? duration : 0);
    setPreviewCurrentTime(Number(event.currentTarget.currentTime) || 0);
    setPreviewError("");
  }

  function handlePreviewPlay() {
    setIsPreviewPlaying(true);
    setPreviewError("");
  }

  function handlePreviewPause(event) {
    setIsPreviewPlaying(false);
    setPreviewCurrentTime(Number(event.currentTarget.currentTime) || 0);
  }

  function handlePreviewEnded(event) {
    setIsPreviewPlaying(false);
    setPreviewCurrentTime(Number(event.currentTarget.duration) || 0);
  }

  function handlePreviewTimeUpdate(event) {
    setPreviewCurrentTime(Number(event.currentTarget.currentTime) || 0);
    const duration = Number(event.currentTarget.duration);
    if (Number.isFinite(duration)) setPreviewDuration(duration);
  }

  function handlePreviewError() {
    setIsPreviewPlaying(false);
    setPreviewError("This audio could not be previewed on this device.");
  }

  async function startAnalysis() {
    const selectedTake = currentTakeRef.current;
    if (selectedTake?.file && selectedTake.pendingAnalysis) {
      setIsBusy(true);
      setStatus(`Submitting ${selectedTake.fileName}...`);
      try {
        const job = await uploadSong({
          file: selectedTake.file,
          title: selectedTake.fileName,
          sourceType: selectedTake.sourceLabel || "upload",
        });
        setCurrentSubmittedJobId(job.jobId);
        currentSubmittedJobIdRef.current = job.jobId;
        setDisplayedReportJobId(null);
        setCompletionNotice("");
        applyJob(job, selectedTake.sourceLabel || "upload");
        setActiveTab("upload");
      } catch (error) {
        setStatus(`Analysis submission failed: ${error instanceof Error ? error.message : "Unknown error"}`);
      } finally {
        setIsBusy(false);
      }
      return;
    }

    if (currentJob && !isTerminal(currentJob)) {
      setActiveTab("results");
      return;
    }

    if (currentJob && isTerminal(currentJob)) {
      setStatus("Choose or record a new audio file before starting another analysis.");
      setActiveTab("upload");
      return;
    }

    void chooseFile();
  }

  const latestJob = reports[0]?.job || currentJob;

  return (
    <main className="vox-app">
      <div className="phone-shell">
        {activeTab === "home" ? (
          <HomeScreen
            latestJob={latestJob}
            onUpload={() => {
              setUploadMode("detailed");
              setActiveTab("upload");
              window.setTimeout(() => fileInputRef.current?.click(), 0);
            }}
            onRecord={startRecording}
            onReports={() => setActiveTab("reports")}
            onOpenRecent={openSpecificReport}
            onQuickStart={handleQuickStart}
          />
        ) : null}
        {activeTab === "guide" ? (
          <QuickGuideScreen
            guide={activeGuide}
            elapsedSeconds={guideElapsedSeconds}
            isRunning={isGuideRunning}
            onStartPause={() => setIsGuideRunning((value) => !value)}
            onReset={() => {
              setGuideElapsedSeconds(0);
              setIsGuideRunning(false);
            }}
            onClose={() => {
              setIsGuideRunning(false);
              setActiveTab("home");
            }}
          />
        ) : null}
        {activeTab === "upload" ? (
          <UploadScreen
            currentJob={currentJob}
            currentTake={currentTake}
            uploadMode={uploadMode}
            backgroundStatus={backgroundStatus}
            status={pollNotice || status}
            isBusy={isBusy}
            isCheckingBackground={isCheckingBackground}
            isRecording={isRecording}
            recordingTime={recordingTime}
            fileInputRef={fileInputRef}
            onChooseFile={chooseFile}
            onFileInput={handleFileInput}
            onRecord={startRecording}
            onStartAnalysis={startAnalysis}
            onCancel={cancelCurrentJob}
            onRequestBackgroundAccess={requestBackgroundAccess}
            onOpenModePicker={openModePicker}
            previewAudioRef={previewAudioRef}
            isPreviewPlaying={isPreviewPlaying}
            previewCurrentTime={previewCurrentTime}
            previewDuration={previewDuration}
            previewProgressPercent={previewDuration > 0 ? (previewCurrentTime / previewDuration) * 100 : 0}
            previewError={previewError}
            onTogglePreview={togglePreviewPlayback}
            onPreviewLoadedMetadata={handlePreviewLoadedMetadata}
            onPreviewPlay={handlePreviewPlay}
            onPreviewPause={handlePreviewPause}
            onPreviewEnded={handlePreviewEnded}
            onPreviewTimeUpdate={handlePreviewTimeUpdate}
            onPreviewError={handlePreviewError}
          />
        ) : null}
        {activeTab === "reports" ? (
          <ReportsScreen
            reports={reports}
            onOpen={openSpecificReport}
            onExportDiagnostics={exportLatestDiagnostics}
            isExportingDiagnostics={isExportingDiagnostics}
            canExportDiagnostics={Boolean(currentJob?.jobId || reports.length)}
          />
        ) : null}
        {activeTab === "results" ? (
          <ResultsScreen
            currentJob={currentJob}
            completionNotice={completionNotice}
            onUpload={() => setActiveTab("upload")}
            onReports={() => setActiveTab("reports")}
            onExportDiagnostics={exportActiveDiagnostics}
            isExportingDiagnostics={isExportingDiagnostics}
          />
        ) : null}
        {activeTab === "settings" ? (
          <SettingsScreen
            currentJob={currentJob}
            reports={reports}
            backgroundStatus={backgroundStatus}
            onRequestBackgroundAccess={requestBackgroundAccess}
            isCheckingBackground={isCheckingBackground}
            onExportActiveDiagnostics={exportActiveDiagnostics}
            onExportLatestDiagnostics={exportLatestDiagnostics}
            onCopyActiveJobId={copyActiveJobId}
            onResetAppData={requestResetAppData}
            isExportingDiagnostics={isExportingDiagnostics}
            isResettingAppData={isResettingAppData}
          />
        ) : null}
        {showResetDialog ? (
          <ResetConfirmationDialog
            onCancel={() => setShowResetDialog(false)}
            onConfirm={confirmResetAppData}
            isResetting={isResettingAppData}
          />
        ) : null}
        {showModeDialog ? (
          <AnalysisModeDialog
            currentMode={uploadMode}
            onSelect={selectAnalysisMode}
            onCancel={() => setShowModeDialog(false)}
          />
        ) : null}
        <BottomNav activeTab={activeTab === "results" ? "reports" : activeTab === "guide" ? "home" : activeTab} onChange={setActiveTab} />
      </div>
    </main>
  );
}

export default App;
