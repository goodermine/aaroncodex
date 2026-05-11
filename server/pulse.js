function safeNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function normalizeFeatures(raw = {}) {
  return {
    duration: safeNumber(raw.duration),
    avgRms: safeNumber(raw.avgRms),
    peakRms: safeNumber(raw.peakRms),
    crest: safeNumber(raw.crest),
    channels: safeNumber(raw.channels),
    brightness: safeNumber(raw.brightness),
    transientDensity: safeNumber(raw.transientDensity),
    onsetDrift: safeNumber(raw.onsetDrift),
    sustainStability: safeNumber(raw.sustainStability),
    phraseCount: safeNumber(raw.phraseCount),
    range: raw.range || "Unavailable",
    energy: raw.energy || "Unavailable",
    clarity: raw.clarity || "Unavailable",
    attack: raw.attack || "Unavailable",
    decoder: raw.decoder || "unknown",
    waveform: Array.isArray(raw.waveform) ? raw.waveform.slice(0, 72).map((value) => safeNumber(value, 0)) : [],
    score: safeNumber(raw.score, 60),
  };
}

export function interpretPulse(features) {
  const avgRms = safeNumber(features.avgRms);
  const peakRms = safeNumber(features.peakRms);
  const crest = safeNumber(features.crest);
  const brightness = safeNumber(features.brightness);
  const transientDensity = safeNumber(features.transientDensity);
  const onsetDrift = safeNumber(features.onsetDrift);
  const sustainStability = safeNumber(features.sustainStability);

  if (![avgRms, peakRms, crest].every((value) => Number.isFinite(value))) {
    return {
      archetype: null,
      win: "The audio made it into the system successfully.",
      mainIssue: "The required audio features were not extracted reliably enough to coach from them.",
      why: "Without stable onset, level, and dynamic data, any vocal diagnosis would be guesswork.",
      change: "Resubmit a clean recording so the system can extract the core vocal features first.",
      drill: {
        name: "Straw Phonation",
        purpose: "Reset effort safely while waiting for a reliable analysis pass.",
        feel: "Easy, steady airflow with no throat grab.",
        avoid: "Do not blow hard or turn it into a volume exercise.",
      },
      nextGoal: "Get a clean feature extraction on the next upload before acting on coaching advice.",
    };
  }

  let mainIssue = "pitch onset accuracy is inconsistent";
  let why = "the voice is arriving at notes with too much push on the front edge, so the pitch center is not settling immediately";
  let change = "Start each phrase slightly lighter and let the vowel lock the note in before adding weight";
  let drill = {
    name: "Clean Staccato Onsets",
    purpose: "Clean up messy note starts and reduce sliding or splatting into pitch.",
    feel: "Small, easy, centered starts that click into the note without a shove.",
    avoid: "Do not turn the onset into a hard glottal hit.",
  };
  let nextGoal = "Make the first note of every phrase land cleanly without a slide-in.";
  let archetype = null;

  if (onsetDrift > 0.18) {
    mainIssue = "you are sliding into notes instead of landing them cleanly";
    why = "the pitch center is settling late, which usually means the onset is too loose or the breath is arriving before the note is fully organized";
    change = "Prepare the pitch before the phrase starts and let the note arrive immediately instead of sneaking up to it";
    drill = {
      name: "Clean Staccato Onsets",
      purpose: "Train the voice to arrive on pitch at the front of the note.",
      feel: "Small, accurate starts that lock in immediately.",
      avoid: "Do not jab the note just to stop the slide.",
    };
    nextGoal = "Make the first pitch of each phrase arrive without any audible scoop.";
  } else if (sustainStability < 62) {
    mainIssue = "held notes are not staying stable enough";
    why = "the support under the tone is fluctuating, so the note core wobbles instead of holding its center";
    change = "Keep the ribs and airflow steady through the middle of the sustain instead of relaxing after the note starts";
    drill = {
      name: "Pitch Center Sustains",
      purpose: "Stabilize held notes and stop drift across the sustain.",
      feel: "A steady tone core that does not sag or wobble halfway through the note.",
      avoid: "Do not push harder in the middle of the sustain to compensate.",
    };
    nextGoal = "Hold long notes with the same center from start to release.";
  } else if (avgRms < 0.11) {
    mainIssue = "breath/support stability is too loose";
    why = "the tone core is not being held together consistently, so the sound floats instead of locking in";
    change = "Keep the airflow steady and resist letting the tone leak out at the start of each phrase";
    drill = {
      name: "Lip Trills",
      purpose: "Balance airflow and cord connection so the tone stops floating.",
      feel: "Even air with a stable buzz and no extra throat work.",
      avoid: "Do not let the trill collapse from weak airflow.",
    };
    nextGoal = "Keep every phrase start supported enough that the tone holds its core through the sustain.";
    archetype = "Floater";
  } else if (transientDensity > 0.012) {
    mainIssue = "note starts are too hard and inconsistent";
    why = "you are over-committing at the front of the phrase, which makes the attack rigid before pitch can settle";
    change = "Think smaller starts and let the sound bloom after the note begins instead of striking into it";
    drill = {
      name: "Mum 1-5-3-1",
      purpose: "Create cleaner onset and forward mix without throat squeeze.",
      feel: "Compact, forward, and easy right at the front of the note.",
      avoid: "Do not spread wide or slam the first syllable.",
    };
    nextGoal = "Make the first beat of each phrase feel clean instead of punched.";
    archetype = "Squeezer";
  } else if (crest < 3) {
    mainIssue = "breath/support stability is flattening the dynamic shape";
    why = "the body is holding one pressure level through the phrase, so the line cannot expand and release musically";
    change = "Let the phrase grow and taper instead of holding the same pressure from start to finish";
    drill = {
      name: "Messa di Voce",
      purpose: "Build dynamic control without losing support or pitch center.",
      feel: "The breath stays steady while the volume grows and recedes smoothly.",
      avoid: "Do not push louder by squeezing the throat.",
    };
    nextGoal = "Shape one phrase with a clear build and release instead of a flat volume line.";
    archetype = "Volume Chaser";
  } else if (brightness > 0.16 && avgRms > 0.18) {
    mainIssue = "resonance efficiency is getting too pushed in the upper edge";
    why = "too much weight is being driven upward, which makes the tone brighter but less free";
    change = "Keep the sound forward but reduce chest pressure as the phrase rises";
    drill = {
      name: "Goo Slides",
      purpose: "Reduce high pushing and stabilize the bridge.",
      feel: "Rounded, connected slides with less shove under the sound.",
      avoid: "Do not drag heavy chest voice upward.",
    };
    nextGoal = "Keep the brighter tone, but remove the feeling of driving upward into the phrase.";
    archetype = "Pusher";
  }

  const win =
    crest > 4
      ? "The take has real dynamic life. It is not sitting there flat."
      : brightness > 0.12
        ? "There is a usable tonal edge in the sound, which gives you something real to build on."
        : "The take stays controlled enough that one focused adjustment should move it quickly.";

  return {
    archetype,
    win,
    mainIssue,
    why,
    change,
    drill,
    nextGoal,
  };
}
