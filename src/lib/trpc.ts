import { useEffect, useMemo, useState } from "react";

// Compatibility shim only. This surface still returns local demo data until
// the remaining standalone screens are wired to the real backend.

const SAMPLE_WAVEFORM = Array.from({ length: 96 }, (_, i) => {
  const value = 0.22 + Math.abs(Math.sin(i / 6)) * 0.48;
  return Number(value.toFixed(3));
});

const SAMPLE_PITCH_TRACK = Array.from({ length: 48 }, (_, index) => ({
  time: index * 0.5,
  pitch: 196 + Math.sin(index / 4) * 18 + (index % 7),
  confidence: 0.8 + ((index % 5) * 0.03),
}));

const BASE_ANALYSIS = {
  id: 101,
  fileName: "Howard Vox Demo Take.wav",
  fileFormat: "wav",
  status: "completed",
  createdAt: "2026-04-05T12:00:00.000Z",
  durationSeconds: 94,
  audioUrl: "",
  polishedAudioUrl: "",
  avgRms: 0.41,
  peakRms: 0.92,
  dynamicRange: "wide",
  waveformData: SAMPLE_WAVEFORM,
  pitchTrack: SAMPLE_PITCH_TRACK,
  detectedVocalRange: {
    lowest: "G3",
    highest: "E5",
    tessitura: "A3-C5",
  },
  pitchStabilityScore: 84,
  progressPercent: 100,
  currentStage: "Complete",
  vocalArchetype: "Cinematic Belt",
  fullAnalysisText: "Strong tonal identity with good projection. Target cleaner note entries and steadier breath release on sustained phrases.",
  firstListenSummary: "A confident, emotionally committed take with strong upper-mid presence and a modern pop-rock edge.",
  techniqueAudit: {
    pitchAccuracy: "Mostly centered, with slight scooping into phrase starts.",
    tone: "Bright and focused, especially in the upper register.",
    breathSupport: "Support is generally solid but relax the release on longer held vowels.",
    registrationUse: "Chest-to-mix transition is mostly smooth.",
    tensionSigns: "A bit of jaw and neck tension appears in louder entries.",
    timing: "Rhythm sits well, with a few anticipations on emphatic words.",
  },
  quickFixPrescriptions: [
    {
      issue: "Scooped note entries",
      fix: "Think straight into the vowel and start 5% lighter.",
    },
    {
      issue: "Upper phrase tension",
      fix: "Release jaw width and let the ribs stay buoyant through the top.",
    },
  ],
  assignedDrill: {
    name: "Octave Siren Lift",
    description: "Glide through the passaggio on a relaxed 'ng-ah' pattern.",
    whatItFixes: "Pitch entry accuracy and upper-register release.",
    howItFeels: "Forward, buoyant, and easy rather than pushed.",
    mistakeToAvoid: "Do not drive the jaw open or over-press the onset.",
  },
  emotionalCoaching: {
    emotionalCharacter: "Earnest and widescreen",
    phrasingCue: "Aim every line at one specific listener.",
    characterMetaphor: "A spotlight cutting through haze",
    emotionalHits: "The chorus lands with conviction.",
    emotionalMisses: "Some verse phrases prioritize force over intimacy.",
  },
  progressPathway: {
    nextPractice: "Three focused reps on first-line note entries and vowel release.",
    signsOfImprovement: "Cleaner attacks and less hardening above the staff.",
    evolutionGoal: "Keep the same size of sound while reducing visible effort.",
  },
};

const SAMPLE_ANALYSES = [
  BASE_ANALYSIS,
  {
    ...BASE_ANALYSIS,
    id: 102,
    fileName: "Bridge Section Pass 2.mp3",
    fileFormat: "mp3",
    status: "uploading",
    createdAt: "2026-04-04T18:15:00.000Z",
    durationSeconds: 37,
    vocalArchetype: null,
    fullAnalysisText: "",
  },
];

function getStorageKey() {
  return "howard-vox-analyses";
}

function clone(value: any) {
  return JSON.parse(JSON.stringify(value));
}

function getAudioFallback() {
  return "/images/hero-stage-bg.jpg";
}

function readAnalyses() {
  if (typeof window === "undefined") {
    return SAMPLE_ANALYSES.map((item) => ({
      ...clone(item),
      audioUrl: item.audioUrl || getAudioFallback(),
      polishedAudioUrl: item.polishedAudioUrl || getAudioFallback(),
    }));
  }

  const raw = window.localStorage.getItem(getStorageKey());
  if (!raw) {
    const initial = SAMPLE_ANALYSES.map((item) => ({
      ...clone(item),
      audioUrl: item.audioUrl || getAudioFallback(),
      polishedAudioUrl: item.polishedAudioUrl || getAudioFallback(),
    }));
    window.localStorage.setItem(getStorageKey(), JSON.stringify(initial));
    return initial;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return SAMPLE_ANALYSES.map((item) => ({
      ...clone(item),
      audioUrl: item.audioUrl || getAudioFallback(),
      polishedAudioUrl: item.polishedAudioUrl || getAudioFallback(),
    }));
  }
}

function writeAnalyses(analyses: any[]) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(getStorageKey(), JSON.stringify(analyses));
  }
}

function nextId() {
  return Math.max(...readAnalyses().map((item: any) => item.id), 100) + 1;
}

function getStats() {
  const analyses = readAnalyses();
  const completed = analyses.filter((item: any) => item.status === "completed");
  return {
    totalAnalyses: analyses.length,
    completedAnalyses: completed.length,
    avgPitchStability: completed.length
      ? completed.reduce((sum: number, item: any) => sum + (Number(item.pitchStabilityScore) || 0), 0) / completed.length
      : 0,
    mostCommonArchetype: completed[0]?.vocalArchetype || "Cinematic Belt",
  };
}

function listAnalyses(input: any = {}) {
  const analyses = [...readAnalyses()].sort((a: any, b: any) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  const filtered = analyses.filter((item: any) => {
    if (input.status && item.status !== input.status) return false;
    if (input.search && !`${item.fileName} ${item.vocalArchetype || ""}`.toLowerCase().includes(String(input.search).toLowerCase())) {
      return false;
    }
    return true;
  });
  const offset = Number(input.offset) || 0;
  const limit = Number(input.limit) || filtered.length;
  return {
    analyses: filtered.slice(offset, offset + limit),
    total: filtered.length,
  };
}

function getAnalysis(input: any = {}) {
  const analyses = readAnalyses();
  return analyses.find((item: any) => item.id === Number(input.id)) || analyses[0];
}

function makeQuery(getData: (input?: any) => any) {
  return {
    useQuery(input?: any) {
      const [data, setData] = useState(() => getData(input));
      useEffect(() => {
        setData(getData(input));
      }, [JSON.stringify(input)]);

      const refetch = async () => {
        const next = getData(input);
        setData(next);
        return { data: next };
      };

      return { data, isLoading: false, error: null, refetch };
    },
  };
}

function makeMutation(handler: (input?: any) => any) {
  return {
    useMutation(options: any = {}) {
      const [isPending, setIsPending] = useState(false);

      const mutateAsync = async (input?: any) => {
        setIsPending(true);
        try {
          const result = await handler(input);
          options.onSuccess?.(result);
          return result;
        } catch (error: any) {
          options.onError?.(error);
          throw error;
        } finally {
          setIsPending(false);
        }
      };

      return {
        isPending,
        mutate: (input?: any) => {
          void mutateAsync(input);
        },
        mutateAsync,
      };
    },
  };
}

async function uploadAnalysis(input: any) {
  const analyses = readAnalyses();
  const id = nextId();
  const extension = input.fileFormat || "wav";
  const audioUrl = input.fileBase64
    ? `data:audio/${extension};base64,${input.fileBase64}`
    : getAudioFallback();
  const created = {
    ...clone(BASE_ANALYSIS),
    id,
    fileName: input.fileName || `Recording-${id}.${extension}`,
    fileFormat: extension,
    status: "uploading",
    audioUrl,
    polishedAudioUrl: audioUrl,
    createdAt: new Date().toISOString(),
    fullAnalysisText: "",
    vocalArchetype: null,
  };
  analyses.unshift(created);
  writeAnalyses(analyses);
  return { analysisId: id, audioUrl };
}

async function saveRecording() {
  return { analysisId: nextId() };
}

async function applyPolish(input: any) {
  const analyses = readAnalyses().map((item: any) =>
    item.id === Number(input.analysisId)
      ? { ...item, polishedAudioUrl: item.audioUrl }
      : item
  );
  writeAnalyses(analyses);
  return { ok: true };
}

async function deleteAnalysis(input: any) {
  writeAnalyses(readAnalyses().filter((item: any) => item.id !== Number(input.id)));
  return { ok: true };
}

async function resetAnalyses() {
  writeAnalyses([]);
  return { analysesDeleted: 0 };
}

async function reanalyseAnalysis(input: any) {
  const analyses = readAnalyses().map((item: any) =>
    item.id === Number(input.analysisId)
      ? {
          ...item,
          status: "completed",
          progressPercent: 100,
          currentStage: "Complete",
          vocalArchetype: item.vocalArchetype || "Cinematic Belt",
          fullAnalysisText: BASE_ANALYSIS.fullAnalysisText,
        }
      : item
  );
  writeAnalyses(analyses);
  return { ok: true };
}

async function respondToHoward(input: any) {
  const analyses = readAnalyses();
  if (input?.analysisId) {
    const updated = analyses.map((item: any) =>
      item.id === Number(input.analysisId)
        ? {
            ...item,
            status: "completed",
            vocalArchetype: item.vocalArchetype || BASE_ANALYSIS.vocalArchetype,
            firstListenSummary: BASE_ANALYSIS.firstListenSummary,
            techniqueAudit: clone(BASE_ANALYSIS.techniqueAudit),
            quickFixPrescriptions: clone(BASE_ANALYSIS.quickFixPrescriptions),
            assignedDrill: clone(BASE_ANALYSIS.assignedDrill),
            emotionalCoaching: clone(BASE_ANALYSIS.emotionalCoaching),
            progressPathway: clone(BASE_ANALYSIS.progressPathway),
            fullAnalysisText: BASE_ANALYSIS.fullAnalysisText,
          }
        : item
    );
    writeAnalyses(updated);
  }

  return {
    response: [
      "Howard hears a confident take with strong energy and a clear commercial tone.",
      "",
      "1. First Listen",
      "You have presence. The main improvement area is cleaner note entry on phrase starts.",
      "",
      "2. Technical Audit",
      "Pitch center is mostly strong. Breath release gets a little tight on sustained upper phrases.",
      "",
      "3. Quick Fix",
      "Start the onset lighter, then let the resonance bloom rather than pushing into it.",
      "",
      "4. Drill",
      "Run slow octave sirens on `ng-ah` to stabilize entry and release.",
      "",
      "5. Emotional Coaching",
      "Keep the verse more intimate so the chorus feels earned.",
      "",
      "6. Progress Pathway",
      "Do three short reps focused only on line openings, then re-record the chorus.",
    ].join("\n"),
  };
}

async function phraseBreakdown() {
  return {
    response: [
      "Phrase-by-phrase breakdown",
      "",
      "0:00-0:15",
      "Good tonal setup. Relax the attack on the first stressed syllable.",
      "",
      "0:16-0:32",
      "Support is solid. Keep the vowel narrower as the pitch rises.",
      "",
      "0:33-0:52",
      "Strong emotional read. Avoid adding extra jaw motion to intensify the line.",
    ].join("\n"),
  };
}

export const trpc = {
  useUtils() {
    return useMemo(
      () => ({
        analysis: {
          get: {
            invalidate: async () => undefined,
            fetch: async (input: any) => getAnalysis(input),
          },
        },
      }),
      []
    );
  },
  auth: {
    checkInvite: makeQuery(() => ({ isInvited: true })),
  },
  analysis: {
    list: makeQuery(listAnalyses),
    stats: makeQuery(() => getStats()),
    get: makeQuery(getAnalysis),
    saveRecording: makeMutation(saveRecording),
    upload: makeMutation(uploadAnalysis),
    howardChat: makeMutation(respondToHoward),
    phraseBreakdown: makeMutation(phraseBreakdown),
    applyPolish: makeMutation(applyPolish),
    delete: makeMutation(deleteAnalysis),
    resetAll: makeMutation(resetAnalyses),
    reanalyse: makeMutation(reanalyseAnalysis),
  },
};
