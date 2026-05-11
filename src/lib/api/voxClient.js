import { Capacitor, registerPlugin } from "@capacitor/core";
import { COACH_VALIDATOR_VERSION } from "./coachValidator.js";
import { COACH_WRITER_VERSION, createCoachOutput } from "./coachWriter.js";

const DEFAULT_BASE_URL = import.meta.env.VITE_VOX_API_BASE_URL?.trim() || "";
const EXECUTION_TARGET =
  import.meta.env.VITE_EXECUTION_TARGET?.trim() || (Capacitor.isNativePlatform() ? "android-local" : "http");
const VoxPipeline = registerPlugin("VoxPipeline");
const MAX_ANDROID_UPLOAD_BYTES = 100 * 1024 * 1024;
const COACH_OUTPUTS_KEY = "howard-vox-coach-outputs-v1";
const COACH_ARTIFACT_SAVE_ATTEMPTS = new Set();

function joinUrl(baseUrl, path) {
  if (!baseUrl) return path;
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

function toPublicStorageUrl(filePath) {
  if (!filePath || typeof filePath !== "string") return null;

  const marker = "/storage/";
  const index = filePath.lastIndexOf(marker);
  if (index === -1) return null;

  const relativePath = filePath.slice(index).replace(/\\/g, "/");
  return joinUrl(DEFAULT_BASE_URL, relativePath);
}

function toArtifactBrowserUrl(artifact, filePath) {
  if (EXECUTION_TARGET === "android-local") {
    const uri = artifact?.uri || (filePath ? `file://${filePath}` : null);
    return uri ? Capacitor.convertFileSrc(uri) : null;
  }
  return toPublicStorageUrl(filePath);
}

function normalizeStage(status, detail) {
  return { status, detail };
}

function analysisStageDetail(status) {
  if (status === "completed") return "Offline analysis metrics are ready";
  if (status === "processing") return "Offline analysis is running";
  if (status === "failed") return "Analysis failed; check warnings or error details";
  if (status === "cancelled") return "Analysis was cancelled before completion";
  if (EXECUTION_TARGET === "android-local") return "Waiting for native separation before offline analysis";
  return "Analysis output is pending for this backend job";
}

function reportStageDetail(status) {
  if (status === "completed") return "Report artifact is ready";
  if (status === "processing") return "Report generation is running";
  if (status === "failed") return "Report generation failed";
  if (status === "cancelled") return "Report generation was cancelled";
  return "Report artifact is pending";
}

function toStageList(stages = {}, separationStatus = "pending", analysisStatus = "pending") {
  const currentStage =
    stages.report === "cancelled" || stages.analyze === "cancelled" || stages.separate === "cancelled"
      ? "cancelled"
      : stages.report === "failed" || stages.analyze === "failed" || stages.separate === "failed"
      ? "failed"
      : stages.analyze === "completed"
      ? "analyzed"
      : stages.separate === "completed"
        ? "separated"
        : stages.separate === "processing"
          ? "processing"
          : "queued";

  return {
    currentStage,
    items: [
      {
        key: "ingest",
        label: "Ingest",
        ...normalizeStage(stages.ingest || "pending", stages.ingest === "completed" ? "Source file stored" : "Waiting for upload ingest"),
      },
      {
        key: "transcode",
        label: "Transcode",
        ...normalizeStage(stages.transcode || "not_required", stages.transcode === "not_required" ? "No transcode step in current pipeline" : stages.transcode),
      },
      {
        key: "separate",
        label: "Separate",
        ...normalizeStage(stages.separate || separationStatus || "pending", stages.separate === "completed" ? "Stem separation finished" : stages.separate || separationStatus),
      },
      {
        key: "analyze",
        label: "Analyze",
        ...normalizeStage(stages.analyze || analysisStatus || "pending", analysisStageDetail(stages.analyze || analysisStatus || "pending")),
      },
      {
        key: "report",
        label: "Report",
        ...normalizeStage(stages.report || "pending", reportStageDetail(stages.report || "pending")),
      },
    ],
  };
}

function clampPercent(value) {
  if (!Number.isFinite(value)) return null;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function fallbackProgressPercent(stage, jobStatus) {
  if (jobStatus === "completed") return 100;
  if (jobStatus === "failed" || jobStatus === "cancelled") return null;

  switch (stage) {
    case "analyzed":
      return 98;
    case "separated":
      return 88;
    case "processing":
      return 35;
    case "queued":
      return 0;
    default:
      return null;
  }
}

function normalizeProgress(payload, stageSummary) {
  const raw = payload?.progress || {};
  const explicitPercent = clampPercent(Number(raw.percent));
  const fallbackPercent = fallbackProgressPercent(stageSummary.currentStage, payload?.job?.status);
  const percent = explicitPercent ?? fallbackPercent;

  return {
    percent,
    isEstimated: explicitPercent === null && percent !== null,
    stage: raw.stage || stageSummary.currentStage || payload?.job?.status || "unknown",
    message: raw.message || (percent === null ? "Progress is unavailable for this job state." : "Waiting for the next pipeline update."),
    updatedAt: raw.updatedAt || payload?.job?.updatedAt || null,
    elapsedMs: Number.isFinite(Number(raw.elapsedMs)) ? Number(raw.elapsedMs) : null,
    averageChunkMs: Number.isFinite(Number(raw.averageChunkMs)) ? Number(raw.averageChunkMs) : null,
    recentAverageChunkMs: Number.isFinite(Number(raw.recentAverageChunkMs)) ? Number(raw.recentAverageChunkMs) : null,
    estimatedRemainingMs: Number.isFinite(Number(raw.estimatedRemainingMs)) ? Number(raw.estimatedRemainingMs) : null,
    estimatedSeparationRemainingMs: Number.isFinite(Number(raw.estimatedSeparationRemainingMs)) ? Number(raw.estimatedSeparationRemainingMs) : null,
    estimatedTotalRemainingMs: Number.isFinite(Number(raw.estimatedTotalRemainingMs)) ? Number(raw.estimatedTotalRemainingMs) : null,
    lastProgressAt: raw.lastProgressAt || raw.updatedAt || payload?.job?.updatedAt || null,
    chunksCompleted: Number.isFinite(Number(raw.chunksCompleted)) ? Number(raw.chunksCompleted) : null,
    totalChunks: Number.isFinite(Number(raw.totalChunks)) ? Number(raw.totalChunks) : null,
    chunksRemaining: Number.isFinite(Number(raw.chunksRemaining)) ? Number(raw.chunksRemaining) : null,
    detail: raw.detail || null,
  };
}

function hzToNoteName(hz) {
  const value = Number(hz);
  if (!Number.isFinite(value) || value <= 0) return null;
  const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const midi = Math.round(69 + 12 * Math.log2(value / 440));
  return `${names[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
}

function defaultNotImplemented() {
  return [
    { name: "Timing accuracy", status: "Not analysed yet", reason: "No beat grid, target timing, or onset comparison is analysed yet." },
    { name: "Rhythm consistency", status: "Not analysed yet", reason: "VOX does not yet compare vocal events against rhythm or accompaniment." },
    { name: "Breath noise", status: "Not analysed yet", reason: "No spectral breath-noise detector is implemented yet." },
    { name: "Breath support", status: "Not analysed yet", reason: "Current metrics cannot diagnose breath support." },
    { name: "Note-by-note tuning", status: "Not analysed yet", reason: "VOX does not yet compare pitch frames with a target melody." },
    { name: "Vibrato", status: "Not analysed yet", reason: "No vibrato-rate or vibrato-depth analysis is implemented yet." },
    { name: "Vocal strain", status: "Not analysed yet", reason: "Current metrics cannot detect vocal strain." },
    { name: "Resonance", status: "Not analysed yet", reason: "No formant or resonance analysis is implemented yet." },
    { name: "Diction", status: "Not analysed yet", reason: "No lyric or consonant clarity analysis is implemented yet." },
    { name: "True vocal range", status: "Not analysed yet", reason: "Raw pitch extremes are not a vocal range test." },
  ];
}

function normalizeNotImplemented(items) {
  const source = Array.isArray(items) && items.length ? items : defaultNotImplemented();
  return source.map((item) => (typeof item === "string" ? {
    name: item,
    status: "Not analysed yet",
    reason: "This metric is not implemented in the current local analysis.",
  } : item));
}

function readCoachOutputCache() {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(window.localStorage.getItem(COACH_OUTPUTS_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeCoachOutputCache(cache) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(COACH_OUTPUTS_KEY, JSON.stringify(cache));
  } catch {
    // Cache persistence is best effort; deterministic generation still keeps wording stable.
  }
}

function cachedCoachResult(jobId, coachInput, existingOutput, existingValidation) {
  if (!coachInput) return { coachOutput: existingOutput || null, validation: existingValidation || null };
  if (!jobId) return createCoachOutput(coachInput);
  const cacheKey = `${jobId}:${COACH_WRITER_VERSION}:${COACH_VALIDATOR_VERSION}`;
  const cache = readCoachOutputCache();
  const cached = cache[cacheKey];
  if (cached?.coachOutput && cached?.validation) {
    persistCoachArtifacts(jobId, coachInput, cached.coachOutput, cached.validation);
    return cached;
  }
  const generated = existingOutput ? {
    coachOutput: existingOutput,
    validation: existingValidation || { isValid: true, blockedClaims: [], fallbackUsed: false, validatorVersion: "provided" },
  } : createCoachOutput(coachInput);
  cache[cacheKey] = generated;
  writeCoachOutputCache(cache);
  persistCoachArtifacts(jobId, coachInput, generated.coachOutput, generated.validation);
  return generated;
}

function persistCoachArtifacts(jobId, coachInput, coachOutput, validation) {
  if (EXECUTION_TARGET !== "android-local" || !jobId || !coachOutput || !validation) return;
  const saveKey = `${jobId}:${COACH_WRITER_VERSION}:${COACH_VALIDATOR_VERSION}`;
  if (COACH_ARTIFACT_SAVE_ATTEMPTS.has(saveKey)) return;
  COACH_ARTIFACT_SAVE_ATTEMPTS.add(saveKey);
  VoxPipeline.saveCoachArtifacts({
    jobId,
    coachInput,
    coachOutput,
    validation,
    coachWriterVersion: COACH_WRITER_VERSION,
    validatorVersion: COACH_VALIDATOR_VERSION,
  }).catch(() => {
    COACH_ARTIFACT_SAVE_ATTEMPTS.delete(saveKey);
  });
}

function buildIssueScoresFallback(rawMetrics) {
  if (!rawMetrics) return null;
  const phrase = rawMetrics.phraseMetrics || {};
  const pitch = rawMetrics.pitchStabilityMetrics || {};
  const scoreAscending = (value, start, full) => {
    const number = Number(value);
    if (!Number.isFinite(number) || number <= start) return 0;
    if (number >= full) return 100;
    return Math.round(((number - start) / (full - start)) * 100);
  };
  const scoreDescending = (value, full, zero) => {
    const number = Number(value);
    if (!Number.isFinite(number) || number >= zero) return 0;
    if (number <= full) return 100;
    return Math.round(((zero - number) / (zero - full)) * 100);
  };
  const pitchEligible = Number(pitch.usablePitchFrameRatio) >= 0.2 && Number(pitch.meanPitchConfidence) >= 0.45;
  const phraseEligible = Number(phrase.phraseCount) >= 2;
  const scores = {
    lowVocalEnergyScore: scoreDescending(rawMetrics.averageRms, 0.02, 0.06),
    peakRiskScore: scoreAscending(rawMetrics.peakAmplitude, 0.85, 0.98),
    wideDynamicsScore: scoreAscending(rawMetrics.dynamicRangeDbRobust, 30, 60),
    phraseInconsistencyScore: phraseEligible && Number.isFinite(Number(phrase.phraseEnergyConsistencyScore)) ? Math.max(0, Math.round(100 - Number(phrase.phraseEnergyConsistencyScore))) : 0,
    pitchVariabilityScore: pitchEligible ? scoreAscending(pitch.pitchStdDevCents, 55, 150) : 0,
    lowPitchConfidenceScore: Math.max(scoreDescending(pitch.usablePitchFrameRatio, 0.15, 0.45), scoreDescending(pitch.meanPitchConfidence, 0.35, 0.62)),
    highSilenceRatioScore: scoreAscending(rawMetrics.silenceRatio, 0.15, 0.55),
    crestPeakinessScore: scoreAscending(rawMetrics.crestFactor, 6, 16),
    pitchVariabilityEligible: pitchEligible,
    phraseInconsistencyEligible: phraseEligible,
  };
  const candidates = [
    ["low_vocal_energy", scores.lowVocalEnergyScore],
    ["peak_control", scores.peakRiskScore],
    ["wide_dynamic_movement", scores.wideDynamicsScore],
    ["phrase_volume_consistency", phraseEligible ? scores.phraseInconsistencyScore : 0],
    ["pitch_track_variability", pitchEligible ? scores.pitchVariabilityScore : 0],
    ["sudden_peak_control", scores.crestPeakinessScore],
  ].sort((a, b) => b[1] - a[1]);
  scores.primaryFocus = candidates[0]?.[1] >= 35 ? candidates[0][0] : (scores.lowPitchConfidenceScore >= 65 ? "pitch_tracking_limited" : "maintenance_refinement");
  scores.secondaryFocus = candidates.find(([focus]) => focus !== scores.primaryFocus && focus !== "maintenance_refinement")?.[0] || "";
  scores.overallPriority = Math.max(...candidates.map(([, score]) => score), 0);
  return scores;
}

function buildVocalProfileFallback(rawMetrics, derivedMetrics, issueScores) {
  if (!rawMetrics) return null;
  const phrase = rawMetrics.phraseMetrics || {};
  const pitch = rawMetrics.pitchStabilityMetrics || {};
  const duration = Number(rawMetrics.durationSeconds);
  const archetype =
    Number.isFinite(duration) && duration < 30 ? "short_clip_limited_data"
      : Number(rawMetrics.silenceRatio) >= 0.55 || Number(phrase.phraseCount) === 0 ? "sparse_or_quiet_take"
      : issueScores.lowPitchConfidenceScore >= 65 ? "pitch_limited"
      : issueScores.peakRiskScore >= 55 || issueScores.crestPeakinessScore >= 70 ? "peak_heavy"
      : issueScores.phraseInconsistencyScore >= 45 && issueScores.wideDynamicsScore >= 35 ? "phrase_inconsistent"
      : issueScores.wideDynamicsScore >= 65 ? "wide_dynamics"
      : issueScores.lowVocalEnergyScore >= 55 && issueScores.peakRiskScore < 30 ? "low_energy_safe_peak"
      : issueScores.pitchVariabilityEligible && issueScores.pitchVariabilityScore >= 55 ? "pitch_variable"
      : "balanced_usable_take";
  const focusLabels = {
    low_vocal_energy: "bring the vocal slightly more forward",
    peak_control: "control sudden loud peaks",
    wide_dynamic_movement: "smooth wide dynamic movement",
    phrase_volume_consistency: "smooth phrase-level volume",
    pitch_track_variability: "keep your pitch steadier through the phrase",
    sudden_peak_control: "reduce sudden peaks versus sustained level",
    pitch_tracking_limited: "treat pitch feedback as limited for this take",
    maintenance_refinement: "maintenance and refinement",
  };
  return {
    archetype,
    pitchCentreSummary: derivedMetrics?.pitchBandLabel ? `average pitch centre ${derivedMetrics.pitchBandLabel.toLowerCase()}` : "no stable average pitch centre",
    energyProfile: `${derivedMetrics?.vocalEnergyLabel || "Measured"} vocal energy`,
    peakProfile: derivedMetrics?.clippingRiskLabel || "Measured peak level",
    dynamicsProfile: derivedMetrics?.dynamicsLabel || "Measured dynamics",
    phraseProfile: phrase.phraseEnergyConsistencyLabel || "phrase consistency not available",
    pitchTrackProfile: pitch.pitchTrackVariabilityLabel || "pitch tracking unavailable",
    confidenceProfile: "level and peak metrics are stronger than pitch metrics",
    mainTakeaway: focusLabels[issueScores.primaryFocus] || "maintenance and refinement",
    safeStrengths: [],
    safeFocusAreas: [focusLabels[issueScores.primaryFocus] || "maintenance and refinement"],
  };
}

function buildCoachInputFallback({ jobId, payload, analysis, rawMetrics, derivedMetrics, issueScores, vocalProfile }) {
  if (!rawMetrics) return null;
  return {
    version: "coach-input-v1-js-fallback",
    jobId,
    songTitle: payload?.input?.title || payload?.input?.originalFileName || null,
    analysedStem: rawMetrics.analysedStem || "vocals",
    durationSeconds: rawMetrics.durationSeconds ?? rawMetrics.durationSec ?? null,
    inputSizeMb: Number.isFinite(Number(payload?.input?.sizeBytes)) ? Number(payload.input.sizeBytes) / (1024 * 1024) : null,
    rawMetrics,
    derivedMetrics,
    phraseMetrics: analysis?.phraseMetrics || rawMetrics.phraseMetrics || null,
    pitchStabilityMetrics: analysis?.pitchStabilityMetrics || rawMetrics.pitchStabilityMetrics || null,
    confidence: {
      levelPeakConfidence: derivedMetrics?.levelPeakConfidence || "low",
      pitchTrackingConfidence: derivedMetrics?.pitchTrackingConfidenceLabel || derivedMetrics?.pitchTrackingConfidence || "limited",
      overallCoachingConfidence: derivedMetrics?.confidenceLevel || "limited",
      scope: "separated_vocal_stem",
    },
    issueScores,
    vocalProfile,
    notImplemented: normalizeNotImplemented(rawMetrics.notImplemented || analysis?.notImplemented),
    safetyRules: {
      allowedClaims: ["average detected pitch centre", "vocal energy from RMS", "peak level", "active volume range", "phrase energy consistency", "pitch movement when confidence is adequate"],
      forbiddenClaims: ["timing judgement", "breath support diagnosis", "tuning accuracy claim", "strain diagnosis", "true vocal range claim"],
    },
    historyComparison: null,
    userIntent: "practice",
    styleContext: null,
  };
}

function normalizeAnalysisModel(analysis = {}, payload = {}) {
  const metrics = analysis?.metrics || null;
  const rawMetrics = analysis?.rawMetrics || (metrics ? {
    averagePitchHz: metrics.avgPitchHz ?? null,
    avgPitchHz: metrics.avgPitchHz ?? null,
    pitchMinHz: metrics.minPitchHz ?? null,
    minPitchHz: metrics.minPitchHz ?? null,
    pitchMaxHz: metrics.maxPitchHz ?? null,
    maxPitchHz: metrics.maxPitchHz ?? null,
    pitchRangeHz: metrics.pitchRangeHz ?? null,
    averageRms: metrics.avgRms ?? null,
    peakRms: metrics.peakRms ?? null,
    minRms: metrics.minRms ?? null,
    peakAmplitude: metrics.peakAmplitude ?? null,
    crestFactor: metrics.avgCrestFactor ?? null,
    avgCrestFactor: metrics.avgCrestFactor ?? null,
    maxCrestFactor: metrics.maxCrestFactor ?? null,
    dynamicRangeDb: metrics.dynamicRangeDb ?? null,
    dynamicRangeDbLegacy: metrics.dynamicRangeDb ?? null,
    dynamicRangeDbRobust: metrics.dynamicRangeDbRobust ?? null,
    durationSeconds: metrics.durationSec ?? null,
    durationSec: metrics.durationSec ?? null,
    sampleRate: metrics.sampleRate ?? null,
    frameCount: metrics.frameCount ?? null,
    voicedFrameCount: metrics.voicedFrameCount ?? null,
    clippingRisk: Number(metrics.peakAmplitude) >= 0.98,
    silenceRatio: metrics.silenceRatio ?? null,
    phraseMetrics: metrics.phraseMetrics ?? null,
    pitchStabilityMetrics: metrics.pitchStabilityMetrics ?? null,
    notImplemented: metrics.notImplemented || defaultNotImplemented(),
    analysedStem: "vocals",
  } : null);

  const pitchNote = hzToNoteName(rawMetrics?.averagePitchHz);
  const dynamicsValue = rawMetrics?.dynamicRangeDbRobust ?? rawMetrics?.dynamicRangeDb;
  const derivedMetrics = analysis?.derivedMetrics || (rawMetrics ? {
    pitchBandLabel: pitchNote ? `Around ${pitchNote}` : "No stable average pitch detected",
    vocalEnergyLabel: Number(rawMetrics.averageRms) < 0.035 ? "Low" : Number(rawMetrics.averageRms) < 0.09 ? "Moderate" : "High",
    dynamicsLabel: Number(dynamicsValue) > 45 ? "Wide dynamic range detected" : Number(dynamicsValue) < 18 ? "Narrow dynamic range detected" : "Controlled dynamic range detected",
    consistencyLabel: rawMetrics.phraseMetrics?.phraseEnergyConsistencyLabel || (Number(dynamicsValue) > 45 ? "Volume consistency may vary" : "No major consistency warning from available metrics"),
    phraseEnergyConsistencyLabel: rawMetrics.phraseMetrics?.phraseEnergyConsistencyLabel || "Not analysed",
    pitchTrackVariabilityLabel: rawMetrics.pitchStabilityMetrics?.pitchTrackVariabilityLabel || "Not analysed",
    pitchTrackingConfidenceLabel: rawMetrics.pitchStabilityMetrics?.pitchTrackingConfidenceLabel || "Not analysed",
    clippingRiskLabel: Number(rawMetrics.peakAmplitude) >= 0.98 ? "Clipping risk" : Number(rawMetrics.peakAmplitude) >= 0.9 ? "Watch loud peaks" : "Safe peak level",
    levelPeakConfidence: rawMetrics.averageRms != null && rawMetrics.peakAmplitude != null ? "high" : "low",
    pitchTrackingConfidence: rawMetrics.pitchStabilityMetrics?.pitchTrackingConfidenceLabel || "limited",
    confidenceLevel: "moderate",
  } : null);

  if (rawMetrics) {
    rawMetrics.notImplemented = normalizeNotImplemented(rawMetrics.notImplemented || analysis?.notImplemented);
  }

  const issueScores = analysis?.issueScores || buildIssueScoresFallback(rawMetrics);
  const vocalProfile = analysis?.vocalProfile || buildVocalProfileFallback(rawMetrics, derivedMetrics, issueScores);
  const coachInput = analysis?.coachInput || buildCoachInputFallback({
    jobId: payload?.job?.id || null,
    payload,
    analysis,
    rawMetrics,
    derivedMetrics,
    issueScores,
    vocalProfile,
  });
  const generatedCoach = cachedCoachResult(payload?.job?.id || coachInput?.jobId || null, coachInput, analysis?.coachOutput, analysis?.validation);

  const coachingSummary = analysis?.coachingSummary || (rawMetrics ? {
    summary: analysis?.summary?.text || "Separated vocal metrics are available. Use the evidence and drills below as practical guidance, not a full vocal diagnosis.",
    strengths: ["The vocal was separated and analysed successfully."],
    topIssues: ["No critical technical issues detected. Suggested focus: smoother phrase-level volume."],
    evidence: [
      rawMetrics.peakAmplitude != null ? `Peak amplitude was ${Number(rawMetrics.peakAmplitude).toFixed(4)}.` : null,
      dynamicsValue != null ? `Dynamics were ${Number(dynamicsValue).toFixed(1)} dB${rawMetrics.dynamicRangeDbRobust != null ? " robust" : " estimated"}.` : null,
      rawMetrics.averagePitchHz != null && pitchNote ? `Average detected pitch was ${Number(rawMetrics.averagePitchHz).toFixed(1)} Hz, around ${pitchNote}. This is not a full range test.` : null,
    ].filter(Boolean),
    recommendedDrills: [
      {
        name: "Pitch-Centre Awareness Drill",
        steps: ["Hum gently around the average pitch centre.", "Sing a short phrase from the song.", "Listen for whether the phrase settles back to the same centre."],
      },
    ],
    nextPracticeFocus: "Keep phrase control consistent across the take.",
    notImplemented: rawMetrics.notImplemented || defaultNotImplemented(),
    confidenceNote: "Level and peak metrics are reliable for the separated vocal stem. Pitch feedback is limited because no target melody is analysed.",
  } : null);

  return {
    rawMetrics,
    derivedMetrics,
    coachingSummary,
    issueScores,
    vocalProfile,
    coachInput,
    coachOutput: generatedCoach.coachOutput,
    validation: generatedCoach.validation,
    notImplemented: normalizeNotImplemented(rawMetrics?.notImplemented || analysis?.notImplemented),
  };
}

function normalizeJob(payload) {
  const input = payload?.input || {};
  const separation = payload?.separation || {};
  const analysis = payload?.analysis || {};
  const outputs = separation?.outputs || {};
  const artifacts = payload?.artifacts || {};
  const stages = payload?.stages || {};
  const stageSummary = toStageList(stages, separation?.status || "pending", analysis?.status || "pending");
  const analysisModel = normalizeAnalysisModel(analysis, payload);

  const normalizedArtifacts = Object.entries(outputs).map(([key, artifact]) => {
    const path = artifact?.path || null;
    return {
      key,
      label: key.charAt(0).toUpperCase() + key.slice(1),
      path,
      uri: artifact?.uri || null,
      browserUrl: toArtifactBrowserUrl(artifact, path),
      format: artifact?.format || null,
      mimeType: artifact?.mimeType || null,
      sampleRate: artifact?.sampleRate ?? null,
      channels: artifact?.channels ?? null,
      durationSec: artifact?.durationSec ?? null,
    };
  });

  return {
    raw: payload,
    jobId: payload?.job?.id || null,
    jobStatus: payload?.job?.status || "unknown",
    separationStatus: separation?.status || "pending",
    currentStage: stageSummary.currentStage,
    createdAt: payload?.job?.createdAt || null,
    updatedAt: payload?.job?.updatedAt || null,
    pipelineVersion: payload?.job?.pipelineVersion || null,
    progress: normalizeProgress(payload, stageSummary),
    title: input?.title || input?.originalFileName || "Untitled upload",
    notes: input?.notes || "",
    sourceType: input?.sourceType || "upload",
    inputFileName: input?.originalFileName || null,
    inputMimeType: input?.mimeType || null,
    inputSizeBytes: input?.sizeBytes ?? null,
    inputDurationMs: Number.isFinite(Number(input?.durationMs)) ? Number(input.durationMs) : null,
    inputStoredPath: input?.storedPath || null,
    manifestPath: artifacts?.manifestPath || null,
    manifestBrowserUrl: toPublicStorageUrl(artifacts?.manifestPath || null),
    stemsDir: artifacts?.stemsDir || null,
    jobDir: artifacts?.jobDir || null,
    engine: separation?.engine || null,
    workerHealth: separation?.workerHealth || null,
    warnings: [...(payload?.warnings || []), ...(separation?.warnings || [])].filter(Boolean),
    error: separation?.error || null,
    analysis: {
      status: analysis?.status || "pending",
      summary: analysis?.summary ?? null,
      metrics: analysis?.metrics ?? null,
      rawMetrics: analysisModel.rawMetrics,
      derivedMetrics: analysisModel.derivedMetrics,
      coachingSummary: analysisModel.coachingSummary,
      issueScores: analysisModel.issueScores,
      vocalProfile: analysisModel.vocalProfile,
      coachInput: analysisModel.coachInput,
      coachOutput: analysisModel.coachOutput,
      validation: analysisModel.validation,
      phraseMetrics: analysisModel.rawMetrics?.phraseMetrics || analysis?.metrics?.phraseMetrics || null,
      pitchStabilityMetrics: analysisModel.rawMetrics?.pitchStabilityMetrics || analysis?.metrics?.pitchStabilityMetrics || null,
      notImplemented: analysisModel.notImplemented || analysisModel.rawMetrics?.notImplemented || analysisModel.coachingSummary?.notImplemented || defaultNotImplemented(),
      artifacts: analysis?.artifacts || {
        pitch: null,
        rms: null,
        crest: null,
        report: null,
      },
    },
    outputs: normalizedArtifacts,
    stages: stageSummary.items,
  };
}

async function readJsonResponse(response) {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message = payload?.message || payload?.error || `Request failed with status ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",").pop() : result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function uploadSongHttp({ file, title, notes, sourceType = "upload" }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title || file?.name || "Untitled upload");
  formData.append("notes", notes || "");
  formData.append("sourceType", sourceType);

  const response = await fetch(joinUrl(DEFAULT_BASE_URL, "/analyze-song"), {
    method: "POST",
    body: formData,
  });

  return readJsonResponse(response);
}

async function uploadSongAndroid({ file, title, notes, sourceType = "upload" }) {
  if (file?.size > MAX_ANDROID_UPLOAD_BYTES) {
    throw new Error("Android local execution accepts files up to 100 MB.");
  }

  const payload = await VoxPipeline.analyzeSong({
    fileName: file?.name || "audio-upload",
    mimeType: file?.type || "application/octet-stream",
    sizeBytes: file?.size || 0,
    title: title || file?.name || "Untitled upload",
    notes: notes || "",
    sourceType,
    originalSourceFileName: file?.name || null,
    originalSourceMimeType: file?.type || null,
    dataBase64: await fileToBase64(file),
  });

  return payload;
}

export async function uploadSong({ file, title, notes, sourceType = "upload" }) {
  const payload =
    EXECUTION_TARGET === "android-local"
      ? await uploadSongAndroid({ file, title, notes, sourceType })
      : await uploadSongHttp({ file, title, notes, sourceType });
  return normalizeJob(payload);
}

export async function pickAndAnalyzeSong({ title, notes, sourceType = "native picker" } = {}) {
  if (EXECUTION_TARGET !== "android-local") {
    throw new Error("Native audio picker is only available in the Android local execution target.");
  }

  const payload = await VoxPipeline.pickAndAnalyzeSong({
    title: title || "Untitled vocal take",
    notes: notes || "",
    sourceType,
  });
  return normalizeJob(payload);
}

export async function fetchJob(jobId) {
  if (EXECUTION_TARGET === "android-local") {
    const payload = await VoxPipeline.getJob({ jobId });
    return normalizeJob(payload);
  }

  const response = await fetch(joinUrl(DEFAULT_BASE_URL, `/analyze-song/jobs/${encodeURIComponent(jobId)}`));
  const payload = await readJsonResponse(response);
  return normalizeJob(payload);
}

export async function getArtifact(jobId, artifactKey) {
  if (EXECUTION_TARGET === "android-local") {
    return VoxPipeline.getArtifact({ jobId, artifactKey });
  }

  return { uri: null, mimeType: null };
}

export async function getLatestJob() {
  if (EXECUTION_TARGET !== "android-local") {
    return null;
  }

  const payload = await VoxPipeline.getLatestJob();
  return normalizeJob(payload);
}

export async function exportDiagnostics(jobId) {
  if (EXECUTION_TARGET !== "android-local") {
    throw new Error("Diagnostics export is only available for the Android local pipeline.");
  }

  return VoxPipeline.exportDiagnostics({ jobId });
}

export async function cancelJob(jobId) {
  if (EXECUTION_TARGET !== "android-local") {
    throw new Error("Job cancellation is not available for the backend execution target yet.");
  }

  const payload = await VoxPipeline.cancelJob({ jobId });
  return normalizeJob(payload);
}

export async function resetAppData() {
  if (EXECUTION_TARGET !== "android-local") {
    return {
      filesCleared: false,
      diagnosticsCleared: false,
      downloadsNote: "Native Android app-private storage reset is only available inside the Android app.",
    };
  }

  return VoxPipeline.resetAppData();
}

export async function getBackgroundProcessingStatus() {
  if (EXECUTION_TARGET !== "android-local") {
    return {
      ready: true,
      notificationsGranted: true,
      batteryOptimizationIgnored: true,
      foregroundServiceAvailable: false,
      wakeLockPermissionDeclared: false,
      action: "not_required",
      message: "Background approval is only required for the Android local pipeline.",
    };
  }

  return VoxPipeline.getBackgroundProcessingStatus();
}

export async function requestBackgroundProcessingAccess() {
  if (EXECUTION_TARGET !== "android-local") {
    return getBackgroundProcessingStatus();
  }

  return VoxPipeline.requestBackgroundProcessingAccess();
}

export { EXECUTION_TARGET, normalizeJob, toPublicStorageUrl };
