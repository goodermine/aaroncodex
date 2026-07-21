"""Build a browser payload from V3 diagnostics and the V2 calibrated score."""

from __future__ import annotations

from typing import Any


def _get(data: dict, *path: str, default=None):
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _number(value, digits=1):
    if value is None:
        return None
    return round(float(value), digits)


def _component_rows(raw: dict) -> list[dict]:
    labels = {
        "intonation_accuracy": "Pitch centre",
        "pitch_stability": "Held-note stability",
        "voice_quality": "Voice quality",
        "vibrato_control": "Vibrato control",
        "dynamics_expression": "Dynamics",
        "phrase_control": "Phrase control",
    }
    components = _get(raw, "technical_score", "components", default={})
    return [
        {
            "key": key,
            "label": labels.get(key, key.replace("_", " ").title()),
            "score": _number(value.get("score"), 2),
            "basis": value.get("input", ""),
        }
        for key, value in components.items()
        if isinstance(value, dict) and value.get("score") is not None
    ]


def _primary_focus(raw: dict, components: list[dict]) -> dict:
    strain = _get(raw, "voice_quality", "strain", "pct_top_notes_strained", default=0) or 0
    drift = _get(raw, "intonation", "median_intra_note_drift_cents")
    deviation = _get(raw, "intonation", "median_abs_deviation_cents")
    sag = _get(raw, "breath", "pct_sagging_endings")
    flags = raw.get("diagnostic_flags") or []

    if strain >= 15:
        return {
            "pillar": "Ease and pressure",
            "drill": "Straw Phonation in Water",
            "cue": "Easy first, power second",
            "why": "Some high, loud notes lost harmonic clarity under pressure.",
            "target": "Record the most intense 30 seconds at 75% volume, keeping the same easy throat sensation from the straw.",
        }
    if drift is not None and drift > 45:
        return {
            "pillar": "Held-note stability",
            "drill": "Messa di Voce on Single Pitches",
            "cue": "Still first, shape second",
            "why": f"Held notes moved by a median {drift:.1f} cents after they began.",
            "target": "Record one chorus or a 30-second section, settling each sustained note before adding vibrato or intensity.",
        }
    if deviation is not None and deviation > 25:
        return {
            "pillar": "Pitch centre",
            "drill": "Pitch Correction Slides with Drone",
            "cue": "Hear it, place it, then sing it",
            "why": f"Sustained notes sat a median {deviation:.1f} cents from the nearest pitch centre.",
            "target": "Record the opening 30 seconds at 75% volume, placing each note against a drone before adding style.",
        }
    if sag is not None and sag > 50:
        return {
            "pillar": "Phrase endings",
            "drill": "Rib Cage Stationary Drill",
            "cue": "Stay wide to the final word",
            "why": f"Pitch-sag flags appeared at {sag:.1f}% of measured phrase endings.",
            "target": "Record one verse, keeping the lower ribs open through the final word of every phrase.",
        }
    weakest = min(components, key=lambda item: item["score"], default={"label": "Consistency"})
    if weakest["label"] == "Held-note stability":
        return {
            "pillar": "Held-note stability",
            "drill": "Messa di Voce on Single Pitches",
            "cue": "Still first, shape second",
            "why": "Held-note stability is the lowest component in this take, even where the median drift is close to the caution threshold.",
            "target": "Record one chorus, settling each sustained note before adding vibrato or intensity.",
        }
    if weakest["label"] in {"Voice quality", "Vibrato control", "Dynamics", "Phrase control"}:
        prescriptions = {
            "Voice quality": ("Straw Phonation in Water", "Easy first, sound second"),
            "Vibrato control": ("Messa di Voce on Single Pitches", "Still first, release second"),
            "Dynamics": ("Messa di Voce on Single Pitches", "Shape from the ribs"),
            "Phrase control": ("Rib Cage Stationary Drill", "Stay wide to the final word"),
        }
        drill, cue = prescriptions[weakest["label"]]
        return {
            "pillar": weakest["label"],
            "drill": drill,
            "cue": cue,
            "why": f"{weakest['label']} is the lowest measured component in this take.",
            "target": "Record the most affected 30-second section twice, keeping the drill sensation in the lyric repetition.",
        }
    return {
        "pillar": weakest["label"],
        "drill": "Internal Imagery Drill",
        "cue": "Hear it before you sing it",
        "why": "The main opportunity is making the strongest coordination repeatable across the take.",
        "target": "Record a focused 30-second section twice with matching pitch placement and phrase shape.",
    }


def _working_points(raw: dict) -> list[str]:
    points: list[str] = []
    deviation = _get(raw, "intonation", "median_abs_deviation_cents")
    hnr = _get(raw, "voice_quality", "hnr_db_median")
    cpps = _get(raw, "voice_quality", "cpps_db")
    strain = _get(raw, "voice_quality", "strain", "n_strained")
    dynamic_range = _get(raw, "dynamics", "effective_dynamic_range_db")
    within_25 = _get(raw, "intonation", "pct_notes_within_25_cents")
    if deviation is not None and deviation <= 20:
        points.append(f"Pitch entry is strong: median pitch-centre deviation is {deviation:.1f} cents.")
    if hnr is not None and hnr >= 15:
        points.append(f"The isolated vocal signal is clear and harmonically organised (HNR {hnr:.2f} dB).")
    if cpps is not None and cpps >= 12:
        points.append(f"Phonation clarity is strong in this capture (CPPS {cpps:.2f} dB).")
    if strain == 0:
        points.append("No high/loud-note strain flags were detected by the coaching heuristic.")
    if dynamic_range is not None and dynamic_range >= 20:
        points.append(f"The take has useful dynamic movement across {dynamic_range:.2f} dB of effective range.")
    if within_25 is not None and within_25 >= 60:
        points.append(f"{within_25:.1f}% of sustained notes landed within +/-25 cents.")
    return points[:4] or ["The engine found enough reliable voiced material for a high-detail report."]


def _trouble_spots(raw: dict) -> list[dict]:
    notes = _get(raw, "intonation", "worst_drift_notes", default=[]) or []
    spots = [
        {
            "time": note.get("time"),
            "start_s": _number(note.get("start_s"), 2),
            "note": note.get("note"),
            "drift_cents": _number(note.get("held_drift_cents"), 1),
            "deviation_cents": _number(note.get("deviation_cents"), 1),
        }
        for note in notes[:8]
    ]
    return [spot for spot in spots if spot["time"] is not None]


def _practice_plan(focus: dict) -> dict:
    pillar = focus["pillar"]
    pillar = {
        "Voice quality": "Ease and pressure",
        "Vibrato control": "Held-note stability",
        "Dynamics": "Held-note stability",
        "Phrase control": "Phrase endings",
    }.get(pillar, pillar)
    plans = {
        "Held-note stability": {
            "immediate": {
                "duration": "4-5 minutes before the next take",
                "steps": [
                    "Choose three comfortable notes from the song and sing each softly for four seconds.",
                    "Repeat with Messa di Voce: begin quietly, make one small swell, then return quietly without changing pitch.",
                    "Sing the troubled phrase once at 70% volume, keeping the first two seconds of every held note still before adding expression.",
                ],
                "success": "The note stays centred while volume changes and does not turn into a slide.",
            },
            "long_term": {
                "frequency": "10 minutes, 4 days per week for 4 weeks",
                "sessions": [
                    {"name": "Messa di Voce", "dose": "4 minutes", "instruction": "Use five comfortable notes; make one controlled swell on each."},
                    {"name": "Internal Imagery Drill", "dose": "2 minutes", "instruction": "Hear each target for two seconds, then land it without scooping."},
                    {"name": "Song transfer", "dose": "4 minutes", "instruction": "Practise two sustained phrases at 70%, then at performance intensity with the same pitch stability."},
                ],
                "progress": "Re-record the same 30-second section weekly. Look for lower held-note drift without losing pitch-centre accuracy.",
            },
        },
        "Pitch centre": {
            "immediate": {
                "duration": "4 minutes before the next take",
                "steps": [
                    "Play or drone the target note, listen for two seconds, then sing it softly without sliding.",
                    "Miss slightly flat on purpose and use one slow Pitch Correction Slide into the centre; repeat from slightly sharp.",
                    "Sing the troubled phrase at 70% volume and land each target before adding style or consonant bite.",
                ],
                "success": "The first attack lands cleanly and needs less correction after it begins.",
            },
            "long_term": {
                "frequency": "10 minutes, 4 days per week for 4 weeks",
                "sessions": [
                    {"name": "Internal Imagery Drill", "dose": "3 minutes", "instruction": "Think each pitch for two seconds before singing it."},
                    {"name": "Pitch Correction Slides", "dose": "3 minutes", "instruction": "Practise recognising flat, sharp and centred placement against a drone."},
                    {"name": "A Cappella Melody Test", "dose": "4 minutes", "instruction": "Sing one verse without accompaniment, then check whether the ending key matches the start."},
                ],
                "progress": "Repeat the same verse weekly. Track median pitch deviation and the percentage within +/-25 cents.",
            },
        },
        "Ease and pressure": {
            "immediate": {
                "duration": "3-4 minutes before the next take",
                "steps": [
                    "Use Straw Phonation in Water with the straw 2-5 cm deep and make small, even bubbles for 60 seconds.",
                    "Glide gently through the song range twice without increasing bubble violence or throat pressure.",
                    "Sing the intense phrase at 70-75% volume, carrying the same easy pressure balance into the lyric.",
                ],
                "success": "The phrase feels easier and the sound stays clear without extra neck or throat effort.",
            },
            "long_term": {
                "frequency": "8-10 minutes, 4 days per week for 4 weeks",
                "sessions": [
                    {"name": "Straw Phonation in Water", "dose": "3 minutes", "instruction": "Use steady bubbles, gentle slides and no forced volume."},
                    {"name": "Lip Trills", "dose": "3 minutes", "instruction": "Move through the working range while keeping the lips free and airflow balanced."},
                    {"name": "Song transfer", "dose": "3 minutes", "instruction": "Alternate one easy semi-occluded repetition with one lyric repetition at moderate intensity."},
                ],
                "progress": "Compare strain flags and clarity measures on the same high-energy section each week.",
            },
        },
        "Phrase endings": {
            "immediate": {
                "duration": "4 minutes before the next take",
                "steps": [
                    "Place both hands on the lower ribs and inhale quietly, keeping the sternum easy and tall.",
                    "Release a steady sibilant hiss while keeping the ribs gently wide instead of collapsing at the start.",
                    "Sing three troubled phrase endings and maintain that width through the final word.",
                ],
                "success": "The final word stays centred and supported without a sudden drop in pitch or energy.",
            },
            "long_term": {
                "frequency": "10 minutes, 4 days per week for 4 weeks",
                "sessions": [
                    {"name": "Rib Cage Stationary Drill", "dose": "3 minutes", "instruction": "Maintain gentle lower-rib width through a controlled exhale."},
                    {"name": "Sibilant Hiss", "dose": "3 minutes", "instruction": "Keep one thin, even stream without bursts or fading."},
                    {"name": "Phrase transfer", "dose": "4 minutes", "instruction": "Mark breaths and practise only the final half of each long phrase before singing the full line."},
                ],
                "progress": "Recheck the same verse weekly and look for fewer breath-end pitch-sag flags.",
            },
        },
    }
    return plans.get(pillar, plans["Pitch centre"])


def _context_feedback(conditions: str) -> dict:
    reported = " ".join((conditions or "").split())
    lowered = reported.lower()
    measurement: list[str] = []
    performance: list[str] = []
    if any(token in lowered for token in ("background noise", "noisy", "live", "crowd", "karaoke")):
        measurement.append("Background sound or room spill may reduce stem separation and pitch/voice-quality reliability.")
    if any(token in lowered for token in ("studio", "quiet room", "home studio")):
        measurement.append("A controlled room generally supports cleaner isolation, though microphone processing can still influence voice-quality metrics.")
    if any(token in lowered for token in ("not warmed", "no warm", "cold voice")):
        performance.append("No warm-up was reported; coordination may not yet have reached the singer's normal settled state.")
    if any(token in lowered for token in ("warmed up", "warm-up", "warmup")) and "not warmed" not in lowered:
        performance.append("A warm-up was reported; compare this take with a matched cold take before attributing changes to the routine.")
    if any(token in lowered for token in ("tired", "fatigue", "exhausted", "sick", "unwell")):
        performance.append("Fatigue or feeling unwell was reported and may affect coordination, stamina and consistency; audio cannot prove the cause.")
    return {
        "reported": reported or "No recording conditions supplied.",
        "measurement_effects": measurement or ["No specific capture limitation can be inferred from the supplied context."],
        "performance_effects": performance or ["No specific performance-state effect can be inferred from the supplied context."],
        "caution": "These are context-aware interpretations, not proof that the condition caused a measured result.",
    }


def build_v2_report(raw: dict, conditions: str = "", comparison: dict | None = None) -> dict:
    components = _component_rows(raw)
    focus = _primary_focus(raw, components)
    score = raw.get("technical_score") or {}
    voice = raw.get("voice_quality") or {}
    intonation = raw.get("intonation") or {}
    vibrato = raw.get("vibrato") or {}
    dynamics = raw.get("dynamics") or {}
    phrasing = raw.get("phrasing") or {}
    breath = raw.get("breath") or {}
    registers = raw.get("registers") or {}
    range_map = raw.get("range_map") or {}
    resonance = raw.get("resonance") or {}
    formants = raw.get("formants") or {}
    onsets = raw.get("onsets") or {}
    harmonics = raw.get("harmonics") or {}
    vowel_space = formants.get("vowel_space") or {}
    flags = raw.get("diagnostic_flags") or []
    overall = score.get("overall_score_0_to_10")
    confidence = score.get("confidence", "unknown")
    headline = (
        "Strong technical foundation with one clear refinement target."
        if overall is not None and overall >= 8
        else "A useful take with a clear next technical lever."
    )
    overview = (
        f"VOXAI measured this take at {overall:.1f}/10 with {confidence} confidence. "
        f"The next useful focus is {focus['pillar'].lower()}."
        if overall is not None
        else f"VOXAI completed the diagnostic pass. The next useful focus is {focus['pillar'].lower()}."
    )
    measured = [
        f"Median pitch-centre deviation: {intonation.get('median_abs_deviation_cents')} cents.",
        f"Median held-note drift: {intonation.get('median_intra_note_drift_cents')} cents.",
        f"Notes within +/-25 cents: {intonation.get('pct_notes_within_25_cents')}%.",
        f"Comfortable core in this take: {range_map.get('comfortable_core', 'unavailable')}.",
    ]
    inferred = [flag.get("interpretation") for flag in flags if flag.get("interpretation")]
    if flags and flags[0].get("likely_cause"):
        inferred.append(f"Possible coaching cause: {flags[0]['likely_cause']} This must be verified by ear and feel.")
    if not inferred:
        inferred.append("The measured coordination appears broadly consistent; interpretation still needs listening context.")
    unverifiable = [
        "The engine cannot verify physical sensation, fatigue, pain, hydration or emotional intent from audio alone.",
        "Register/passaggio and strain outputs are coaching heuristics, not medical findings.",
        "Backing-vocal leakage and pitch-tracker octave errors can affect isolated extreme notes.",
    ]
    return {
        "version": "voxai_v3_diagnostics_v2_score",
        "headline": headline,
        "overview": overview,
        "archetype": raw.get("archetype"),
        "score": {
            "overall": _number(overall, 1),
            "capture_fair": _number(score.get("capture_fair_score_0_to_10"), 1),
            "confidence": confidence,
            "components": components,
            "calibration_references": _get(score, "calibration", "n_references"),
        },
        "what_is_working": _working_points(raw),
        "main_focus": focus,
        "practice_plan": _practice_plan(focus),
        "recording_context": _context_feedback(conditions),
        "comparison": comparison,
        "measured": measured,
        "inferred": inferred[:3],
        "unverifiable": unverifiable,
        "metrics": {
            "intonation": {
                "notes_analysed": intonation.get("n_notes"),
                "median_deviation_cents": _number(intonation.get("median_abs_deviation_cents"), 1),
                "p90_deviation_cents": _number(intonation.get("p90_abs_deviation_cents"), 1),
                "within_10_percent": _number(intonation.get("pct_notes_within_10_cents"), 1),
                "within_25_percent": _number(intonation.get("pct_notes_within_25_cents"), 1),
                "held_drift_cents": _number(intonation.get("median_intra_note_drift_cents"), 1),
            },
            "voice_quality": {
                "reliability": voice.get("reliability"),
                "jitter_percent": _number(voice.get("jitter_local_percent_median"), 4),
                "shimmer_percent": _number(voice.get("shimmer_local_percent_median"), 4),
                "hnr_db": _number(voice.get("hnr_db_median"), 2),
                "cpps_db": _number(voice.get("cpps_db"), 2),
                "strain_percent": _number(_get(voice, "strain", "pct_top_notes_strained"), 1),
                "strained_notes": _get(voice, "strain", "n_strained"),
                "top_notes": _get(voice, "strain", "n_top_quartile_notes"),
            },
            "vibrato": {
                "use_percent": _number(vibrato.get("pct_notes_with_vibrato"), 1),
                "rate_hz": _number(vibrato.get("median_rate_hz"), 2),
                "extent_cents": _number(vibrato.get("median_extent_cents"), 1),
                "onset_delay_s": _number(vibrato.get("median_onset_delay_s"), 2),
                # Per-note segments for the deck's vibrato band. The display
                # contour is 10 Hz (can't resolve vibrato client-side); these
                # are measured server-side at full frame rate.
                "notes": [
                    {
                        "start_s": n.get("start_s"),
                        "duration_s": n.get("duration_s"),
                        "note": n.get("note"),
                        "rate_hz": n.get("rate_hz"),
                        "extent_cents": n.get("extent_cents"),
                        "has_vibrato": bool(n.get("has_vibrato")),
                    }
                    for n in (vibrato.get("notes") or [])
                    if isinstance(n, dict)
                ],
            },
            "dynamics": {
                "effective_range_db": _number(dynamics.get("effective_dynamic_range_db"), 2),
                "phrase_spread_db": _number(dynamics.get("phrase_level_spread_db"), 2),
                "phrases": dynamics.get("n_phrases"),
                "median_phrase_s": _number(phrasing.get("median_phrase_s"), 2),
            },
            "breath": {
                "phrases_measured": breath.get("n_phrases_measured"),
                "sagging_endings": breath.get("n_sagging_endings"),
                "sag_percent": _number(breath.get("pct_sagging_endings"), 1),
            },
            "range": {
                "comfortable_core": range_map.get("comfortable_core"),
                "extremes_touched": range_map.get("extremes_touched"),
                "most_used_note": range_map.get("most_used_note"),
            },
            "registers": {
                "reliability": registers.get("reliability"),
                "full_voice_percent": _number(registers.get("pct_full_voice"), 1),
                "light_head_percent": _number(registers.get("pct_light_head"), 1),
                "estimated_passaggio": registers.get("estimated_passaggio"),
                "transitions": registers.get("n_register_transitions"),
            },
            "resonance": {
                "classification": resonance.get("resonance_classification"),
                "spectral_centroid_hz": _number(resonance.get("spectral_centroid_mean_hz"), 1),
                "singers_formant_ratio_db": _number(resonance.get("singers_formant_ratio_db"), 2),
                "singers_formant_read": resonance.get("singers_formant_read"),
                "f1_hz": _number(formants.get("F1_median_hz"), 1),
                "f2_hz": _number(formants.get("F2_median_hz"), 1),
            },
            "onsets": {
                "analysed": onsets.get("n_onsets"),
                "clean_percent": _number(onsets.get("pct_clean"), 1),
                "scooped_percent": _number(onsets.get("pct_scooped"), 1),
                "overshot_percent": _number(onsets.get("pct_overshot"), 1),
                "median_scoop_depth_cents": _number(onsets.get("median_scoop_depth_cents"), 1),
            },
            "harmonics": {
                "notes_analysed": harmonics.get("n_notes"),
                "h1_minus_h2_db": _number(harmonics.get("H1_minus_H2_median_db"), 2),
                "read": harmonics.get("h1_h2_read"),
            },
            "vowel_space": {
                "notes_mapped": vowel_space.get("n_notes_mapped"),
                "notes_excluded_high_pitch": vowel_space.get("n_notes_excluded_high_pitch"),
                "distribution": vowel_space.get("vowel_distribution") or {},
                "reliability": vowel_space.get("reliability"),
            },
        },
        "trouble_spots": _trouble_spots(raw),
        "flags": [
            {
                "category": flag.get("category"),
                "name": flag.get("flag"),
                "value": flag.get("value"),
                "interpretation": flag.get("interpretation"),
            }
            for flag in flags[:5]
        ],
    }
