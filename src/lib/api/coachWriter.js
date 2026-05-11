import { COACH_VALIDATOR_VERSION, validateCoachOutput } from "./coachValidator.js";

export const COACH_WRITER_VERSION = "coach-writer-v2";

const ARCHETYPE_SUMMARIES = {
  low_energy_safe_peak: [
    "The strongest pattern in this take is a quieter vocal level with safe peaks.",
    "VOX measured a vocal that stayed safe at the top but could sit more forward.",
    "This take has controlled peaks, with the main opportunity in vocal energy.",
  ],
  peak_heavy: [
    "The clearest measurable pattern is sudden loud peaks.",
    "VOX found usable vocal energy, but the loudest moments stand out from the rest of the take.",
    "This take is mostly about peak control rather than adding more level.",
  ],
  wide_dynamics: [
    "The take shows wide dynamic movement across the separated vocal.",
    "VOX measured a large gap between quieter and louder vocal moments.",
    "The main measurable pattern is broad dynamic movement from section to section.",
  ],
  phrase_inconsistent: [
    "The strongest pattern in this take is uneven phrase-level volume.",
    "VOX detected useful vocal energy, but phrase loudness moved around more than ideal.",
    "Your main measurable opportunity is smoothing phrase volume from line to line.",
  ],
  pitch_limited: [
    "Pitch data was limited in this take, so VOX is weighting level and dynamics more heavily.",
    "VOX did not have enough clear pitch data for a firm pitch read.",
    "VOX can discuss level, peaks, and dynamics more confidently than pitch for this take.",
  ],
  pitch_variable: [
    "Your pitch moved around more than the stronger level metrics.",
    "VOX found enough clear pitch data to comment cautiously on pitch movement.",
    "The measurable pitch pattern is extra movement around the pitch centre.",
  ],
  balanced_usable_take: [
    "This is a balanced usable take with no major technical warning from current metrics.",
    "VOX measured a stable enough level profile for practical coaching.",
    "The take looks usable from the current level, peak, phrase, and pitch data.",
  ],
  sparse_or_quiet_take: [
    "This take has sparse or very quiet vocal material, so coaching is more limited.",
    "VOX found limited active vocal material to evaluate.",
    "The recording appears quiet or sparse enough that only cautious feedback is appropriate.",
  ],
  short_clip_limited_data: [
    "This short clip gives VOX enough for a quick check, not a full performance read.",
    "Because this is a short clip, VOX focused on the clearest signals: vocal level, pitch centre, and pitch movement.",
    "This is a quick sample, so VOX is keeping the coaching narrow and practical.",
  ],
};

const FOCUS_LABELS = {
  low_vocal_energy: "Bring the vocal slightly more forward.",
  peak_control: "Control sudden loud peaks.",
  wide_dynamic_movement: "Smooth out big volume changes.",
  phrase_volume_consistency: "Keep phrase volume more even.",
  pitch_track_variability: "Keep your pitch steadier through the phrase.",
  sudden_peak_control: "Smooth sudden loudness spikes.",
  pitch_tracking_limited: "Record a cleaner short phrase for clearer pitch feedback.",
  maintenance_refinement: "Keep the take consistent and repeatable.",
};

const DRILLS = {
  low_vocal_energy: {
    name: "Forward Tone Projection Drill",
    selectedBecause: "VOX picked this because the vocal level was low while the peak level stayed safe.",
    steps: [
      "Choose one chorus line or repeated phrase.",
      "Sing it on 'mum' or 'nay' at a comfortable volume.",
      "Aim for a clearer forward tone without pushing louder.",
      "Record again and compare average vocal energy.",
    ],
    whatToListenFor: ["Clearer tone at the same effort.", "No harsh peak jump at the loudest word."],
    quickVersion: "Do three 20-second passes and keep the best one.",
    sevenDayVersion: "Repeat once daily, then compare average RMS and peak level across takes.",
  },
  peak_control: {
    name: "Peak Control Drill",
    selectedBecause: "VOX picked this because the loudest moments jumped out from the rest of the take.",
    steps: [
      "Find the loudest phrase in the song.",
      "Sing it at about 80% effort.",
      "Keep the vowel open and avoid a sudden attack on the first loud word.",
      "Record again and check whether peak level drops while tone stays present.",
    ],
    whatToListenFor: ["Less spike on loud words.", "Similar vocal presence with smoother peaks."],
    quickVersion: "Repeat the loudest phrase five times at 80% effort.",
    sevenDayVersion: "Track peak level over the week while keeping vocal energy usable.",
  },
  wide_dynamic_movement: {
    name: "Volume Ladder Drill",
    selectedBecause: "VOX picked this because the active volume range was wide.",
    steps: [
      "Choose one phrase and sing it at 40%, 60%, then 80% volume.",
      "Keep the tone connected between volume levels.",
      "Repeat the same phrase without sudden jumps.",
      "Record again and compare robust dynamics.",
    ],
    whatToListenFor: ["Smooth transitions between quiet and loud.", "Phrase endings staying present."],
    quickVersion: "Run the ladder twice on one phrase.",
    sevenDayVersion: "Use one phrase daily and aim for smoother dynamics without flattening expression.",
  },
  phrase_volume_consistency: {
    name: "Phrase Volume Smoothing Drill",
    selectedBecause: "VOX picked this because phrase volume changed noticeably from line to line.",
    steps: [
      "Choose one chorus or repeated phrase.",
      "Sing it at a comfortable volume.",
      "Keep the phrase ending as present as the beginning.",
      "Record again and compare phrase consistency.",
    ],
    whatToListenFor: ["Line endings do not disappear.", "Repeated phrases feel closer in level."],
    quickVersion: "Do three passes of the same phrase and keep the smoothest one.",
    sevenDayVersion: "Practice the same phrase for seven days and compare phrase consistency score.",
  },
  pitch_track_variability: {
    name: "Pitch-Centre Awareness Drill",
    selectedBecause: "VOX picked this because your pitch movement was higher than expected for this clip.",
    steps: [
      "Hum gently around the detected pitch centre.",
      "Sing a short phrase slowly.",
      "Pause and hum the centre again.",
      "Record again and check whether the pitch movement becomes steadier.",
    ],
    whatToListenFor: ["The phrase returns to a similar centre.", "The pitch estimate feels steadier without forcing."],
    quickVersion: "Hum-sing-hum for two minutes.",
    sevenDayVersion: "Repeat with one phrase daily and check whether pitch movement becomes steadier.",
  },
  pitch_tracking_limited: {
    name: "Clean Signal Retake Drill",
    selectedBecause: "VOX picked this because there was not enough clear pitch data for confident pitch feedback.",
    steps: [
      "Record 20-30 seconds in a quieter place.",
      "Use one clean sustained phrase.",
      "Keep the phone or mic distance steady.",
      "Analyse again and check whether VOX gets clearer pitch data.",
    ],
    whatToListenFor: ["Cleaner sustained vowels.", "Less background or consonant-heavy material."],
    quickVersion: "Record one clean sustained phrase.",
    sevenDayVersion: "Use the same short phrase each day and check whether the pitch read becomes clearer.",
  },
  maintenance_refinement: {
    name: "Maintenance Long-Tone Drill",
    selectedBecause: "VOX picked this because no single measured issue dominated the take.",
    steps: [
      "Choose a comfortable note or phrase from the song.",
      "Hold it steadily for five seconds.",
      "Repeat at a medium volume without chasing loudness.",
      "Record again and compare peak level and phrase consistency.",
    ],
    whatToListenFor: ["Even tone.", "No sudden peak at the start or end."],
    quickVersion: "Do five steady five-second holds.",
    sevenDayVersion: "Repeat daily and aim to keep peak level safe while phrase consistency stays steady.",
  },
};

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function fieldValue(source, path) {
  return path.split(".").reduce((value, key) => value?.[key], source);
}

function stableHash(value) {
  const text = String(value || "howard-vox");
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

function pickVariant(options, seed) {
  if (!options?.length) return "";
  return options[stableHash(seed) % options.length];
}

function formatNumber(value, digits = 1) {
  const parsed = number(value);
  return parsed == null ? "not available" : parsed.toFixed(digits);
}

function normalizeNotImplemented(items) {
  const values = Array.isArray(items) ? items : [];
  return values.map((item) => {
    if (typeof item === "string") {
      return { name: item, status: "Not analysed yet", reason: "This metric is not implemented in the current local analysis." };
    }
    return item;
  });
}

function evidence(claim, field, coachInput, interpretation) {
  return {
    claim,
    field,
    value: fieldValue(coachInput, field),
    interpretation,
  };
}

function focusFromCoachInput(coachInput) {
  return coachInput?.issueScores?.primaryFocus || coachInput?.vocalProfile?.mainTakeaway || "maintenance_refinement";
}

function drillForFocus(focus) {
  return DRILLS[focus] || DRILLS.maintenance_refinement;
}

function topEvidence(coachInput) {
  const output = [];
  const focus = focusFromCoachInput(coachInput);
  if (focus === "low_vocal_energy") {
    output.push(evidence("Average vocal energy was low enough to make projection the safest focus.", "rawMetrics.averageRms", coachInput, `${formatNumber(coachInput.rawMetrics?.averageRms, 4)} RMS`));
  } else if (focus === "peak_control") {
    output.push(evidence("The loudest sample peaks are close enough to need control.", "rawMetrics.peakAmplitude", coachInput, `${formatNumber(coachInput.rawMetrics?.peakAmplitude, 4)} peak amplitude`));
  } else if (focus === "wide_dynamic_movement") {
    output.push(evidence("Active volume range was wide.", "rawMetrics.dynamicRangeDbRobust", coachInput, `${formatNumber(coachInput.rawMetrics?.dynamicRangeDbRobust, 1)} dB`));
  } else if (focus === "phrase_volume_consistency") {
    output.push(evidence("Phrase loudness varied across detected phrases.", "phraseMetrics.phraseEnergyConsistencyScore", coachInput, `${formatNumber(coachInput.phraseMetrics?.phraseEnergyConsistencyScore, 1)}/100 phrase consistency`));
  } else if (focus === "pitch_track_variability") {
    output.push(evidence("Your pitch moved around noticeably. VOX had enough clear pitch data to flag this as a practice focus, but this is not a tuning score.", "pitchStabilityMetrics.pitchStdDevCents", coachInput, `${formatNumber(coachInput.pitchStabilityMetrics?.pitchStdDevCents, 1)} cents`));
  } else if (focus === "pitch_tracking_limited") {
    output.push(evidence("Pitch data was limited, so VOX is not making a strong pitch judgement.", "pitchStabilityMetrics.usablePitchFrameRatio", coachInput, `${formatNumber(coachInput.pitchStabilityMetrics?.usablePitchFrameRatio, 2)} clear pitch data ratio`));
  } else {
    output.push(evidence("No single measured issue dominated this take.", "issueScores.overallPriority", coachInput, `${formatNumber(coachInput.issueScores?.overallPriority, 0)}/100 priority`));
  }

  if (coachInput.rawMetrics?.peakAmplitude != null) {
    output.push(evidence("Peak safety is based on measured peak amplitude.", "rawMetrics.peakAmplitude", coachInput, `${formatNumber(coachInput.rawMetrics.peakAmplitude, 4)} peak amplitude`));
  }
  if (coachInput.rawMetrics?.dynamicRangeDbRobust != null && focus !== "wide_dynamic_movement") {
    output.push(evidence("Active volume range comes from the louder singing frames.", "rawMetrics.dynamicRangeDbRobust", coachInput, `${formatNumber(coachInput.rawMetrics.dynamicRangeDbRobust, 1)} dB`));
  }
  return output;
}

function whatWentWell(coachInput) {
  const strengths = [];
  const peak = number(coachInput.rawMetrics?.peakAmplitude);
  const rms = number(coachInput.rawMetrics?.averageRms);
  const phraseScore = number(coachInput.phraseMetrics?.phraseEnergyConsistencyScore);
  if (peak != null && peak < 0.9) strengths.push("Peak level stayed in a safer zone.");
  if (rms != null && rms >= 0.035) strengths.push("The separated vocal had usable analysis level.");
  if (phraseScore != null && phraseScore >= 70) strengths.push("Phrase energy was reasonably consistent.");
  if (coachInput.rawMetrics?.averagePitchHz != null) strengths.push("VOX measured an average pitch centre for this recording.");
  return strengths.length ? strengths.slice(0, 3) : ["The vocal was separated and measured successfully."];
}

function detailedFeedback(coachInput) {
  const focus = focusFromCoachInput(coachInput);
  const archetype = coachInput.vocalProfile?.archetype || "balanced_usable_take";
  const details = [];
  if (focus === "pitch_tracking_limited") {
    details.push("VOX is avoiding a strong pitch judgement because there was limited clear pitch data.");
  } else if (focus === "phrase_volume_consistency") {
    details.push("Phrase consistency is more actionable here than whole-song loudness because phrase-level energy moved around.");
  } else if (focus === "peak_control") {
    details.push("The useful goal is not to get quieter overall; it is to reduce the sudden loudest spikes.");
  } else if (focus === "low_vocal_energy") {
    details.push("The safe peak level suggests there may be room to bring the vocal slightly more forward without clipping.");
  } else if (focus === "wide_dynamic_movement") {
    details.push("Wide dynamics can be expressive, but this report treats them as a control target when they dominate the profile.");
  } else {
    details.push("Use this report as a maintenance read: keep the safer level profile while refining repeatability.");
  }
  if (archetype === "short_clip_limited_data") {
    details.push("Because this is a short clip, VOX focused on vocal level, pitch centre, and pitch movement.");
  }
  if (coachInput.styleContext === "controlled_grit_intentional") {
    details.push("VOX is not judging grit or strain from the current metrics.");
  }
  return details;
}

function confidenceNote(coachInput) {
  const pitchConfidence = coachInput.pitchStabilityMetrics?.pitchTrackingConfidenceLabel || coachInput.confidence?.pitchTrackingConfidence || "limited";
  if (focusFromCoachInput(coachInput) === "pitch_tracking_limited") {
    return "Report confidence is stronger for vocal level, peak level, and volume changes than pitch. Pitch data was limited, so VOX is not judging tuning accuracy.";
  }
  if (pitchConfidence === "good") {
    return "Report confidence is good. Pitch data was clear enough for cautious feedback, but this is still not a tuning score because no target melody is analysed.";
  }
  return "Report confidence is moderate. Vocal level and peak level are the clearest signals; pitch feedback is cautious because no target melody is analysed.";
}

function buildOutput(coachInput) {
  const archetype = coachInput.vocalProfile?.archetype || "balanced_usable_take";
  const focus = focusFromCoachInput(coachInput);
  const seed = `${coachInput.jobId || "fixture"}:${archetype}:${focus}`;
  const summaryStart = pickVariant(ARCHETYPE_SUMMARIES[archetype] || ARCHETYPE_SUMMARIES.balanced_usable_take, seed);
  const drill = drillForFocus(focus);
  const evidenceRows = topEvidence(coachInput);
  const profile = coachInput.vocalProfile || {};

  return {
    mode: "rule_based",
    coachWriterVersion: COACH_WRITER_VERSION,
    archetype,
    summary: `${summaryStart} Main focus: ${FOCUS_LABELS[focus] || profile.mainTakeaway || drill.name.replace(" Drill", "").toLowerCase()}`,
    overallRead: [
      profile.pitchCentreSummary,
      profile.energyProfile,
      profile.peakProfile,
      profile.dynamicsProfile,
      profile.phraseProfile,
      profile.pitchTrackProfile,
    ].filter(Boolean).join(" | "),
    whatWentWell: whatWentWell(coachInput),
    mainFocus: FOCUS_LABELS[focus] || profile.mainTakeaway || drill.name,
    detailedFeedback: detailedFeedback(coachInput),
    evidence: evidenceRows,
    recommendedDrill: drill,
    practicePlan: {
      quickVersion: drill.quickVersion,
      sevenDayVersion: drill.sevenDayVersion,
    },
    confidenceNote: confidenceNote(coachInput),
    notAnalysedYet: normalizeNotImplemented(coachInput.notImplemented),
    safetyNote: "VOX only uses measured vocal level, peak level, volume range, phrase consistency, and pitch movement here. Timing, breath, tuning accuracy, strain, vibrato, resonance, diction, and true range are not diagnosed.",
  };
}

function fallbackOutput(coachInput, validation) {
  const drill = DRILLS.maintenance_refinement;
  return {
    mode: "rule_based_fallback",
    archetype: "balanced_usable_take",
    summary: "VOX separated and measured your vocal. The safest read is to review the measured evidence and use a simple maintenance drill.",
    overallRead: "Metric-based report with limited interpretation.",
    whatWentWell: ["The vocal was separated and measured successfully."],
    mainFocus: "maintenance and refinement",
    detailedFeedback: ["A safer fallback was used because one or more coaching claims failed validation."],
    evidence: [evidence("Measured analysis is available for this job.", "rawMetrics.analysedStem", coachInput, coachInput.rawMetrics?.analysedStem || "vocals")],
    recommendedDrill: drill,
    practicePlan: {
      quickVersion: drill.quickVersion,
      sevenDayVersion: drill.sevenDayVersion,
    },
    confidenceNote: "Confidence is limited to the measured metrics. No unavailable vocal diagnosis is included.",
    notAnalysedYet: normalizeNotImplemented(coachInput.notImplemented),
    safetyNote: `Fallback used. Blocked claims: ${validation.blockedClaims.join("; ")}`,
  };
}

export function createCoachOutput(coachInput) {
  if (!coachInput) return { coachOutput: null, validation: null };
  const candidate = buildOutput(coachInput);
  const validation = validateCoachOutput(candidate, coachInput);
  if (validation.isValid) {
    return { coachOutput: candidate, validation };
  }
  const fallback = fallbackOutput(coachInput, { ...validation, fallbackUsed: true });
  return {
    coachOutput: fallback,
    validation: {
      ...validateCoachOutput(fallback, coachInput),
      blockedClaims: validation.blockedClaims,
      fallbackUsed: true,
      validatorVersion: COACH_VALIDATOR_VERSION,
    },
  };
}

export { DRILLS };
