const FORBIDDEN_PATTERNS = [
  /\bout of tune\b/i,
  /\bflat\b/i,
  /\bsharp\b/i,
  /\bbad timing\b/i,
  /\bweak breath support\b/i,
  /\bbreath support problem\b/i,
  /\bvocal strain detected\b/i,
  /\bpoor resonance\b/i,
  /\bdiction problem\b/i,
  /\byour range is\b/i,
  /\btrue range\b/i,
  /\bvibrato quality\b/i,
  /\bcontrolled grit detected\b/i,
  /\bstrain detected\b/i,
  /\brasp detected\b/i,
];

const UNIMPLEMENTED_TERMS = [
  "timing",
  "rhythm",
  "breath noise",
  "breath support",
  "note-by-note tuning",
  "tuning accuracy",
  "vibrato",
  "vocal strain",
  "resonance",
  "diction",
  "true vocal range",
];

export const COACH_VALIDATOR_VERSION = "coach-validator-v1";

function fieldExists(source, path) {
  if (!source || !path || typeof path !== "string") return false;
  return path.split(".").every((part, index, parts) => {
    if (index === 0) return Object.prototype.hasOwnProperty.call(source, part);
    const parent = parts.slice(0, index).reduce((value, key) => value?.[key], source);
    return parent && Object.prototype.hasOwnProperty.call(parent, part);
  });
}

function flattenStrings(value, key = "") {
  if (value == null) return [];
  if (typeof value === "string") return [{ key, value }];
  if (typeof value === "number" || typeof value === "boolean") return [];
  if (Array.isArray(value)) return value.flatMap((item, index) => flattenStrings(item, `${key}[${index}]`));
  if (typeof value === "object") {
    return Object.entries(value).flatMap(([childKey, childValue]) => flattenStrings(childValue, key ? `${key}.${childKey}` : childKey));
  }
  return [];
}

function isExemptTextPath(path) {
  return path.startsWith("notAnalysedYet") || path.startsWith("safetyNote");
}

function hasForbiddenClaim(text) {
  return FORBIDDEN_PATTERNS.find((pattern) => pattern.test(text));
}

function treatsUnavailableMetricAsMeasured(text) {
  const lower = text.toLowerCase();
  if (
    lower.includes("not analysed") ||
    lower.includes("not included") ||
    lower.includes("not available") ||
    lower.includes("not judging") ||
    lower.includes("not diagnose") ||
    lower.includes("not diagnosed") ||
    lower.includes("not a tuning score")
  ) return null;
  return UNIMPLEMENTED_TERMS.find((term) => lower.includes(term));
}

export function validateCoachOutput(coachOutput, coachInput) {
  const blockedClaims = [];

  if (!coachOutput || typeof coachOutput !== "object") {
    blockedClaims.push("coachOutput missing or invalid");
  }

  for (const evidence of coachOutput?.evidence || []) {
    if (!fieldExists(coachInput, evidence?.field)) {
      blockedClaims.push(`Evidence field not found: ${evidence?.field || "missing"}`);
    }
  }

  for (const item of flattenStrings(coachOutput)) {
    if (isExemptTextPath(item.key)) continue;
    const forbidden = hasForbiddenClaim(item.value);
    if (forbidden) {
      blockedClaims.push(`Forbidden claim in ${item.key}: ${forbidden}`);
    }
    const unavailable = treatsUnavailableMetricAsMeasured(item.value);
    if (unavailable) {
      blockedClaims.push(`Unavailable metric treated as measured in ${item.key}: ${unavailable}`);
    }
    if (/\bpending\b/i.test(item.value)) {
      blockedClaims.push(`Pending wording in completed report section: ${item.key}`);
    }
    if (/pitch.*min.*max.*range|raw pitch.*range/i.test(item.value)) {
      blockedClaims.push(`Raw pitch extremes described as range in ${item.key}`);
    }
  }

  return {
    isValid: blockedClaims.length === 0,
    blockedClaims,
    fallbackUsed: false,
    validatorVersion: COACH_VALIDATOR_VERSION,
  };
}

export function forbiddenPatterns() {
  return FORBIDDEN_PATTERNS;
}
