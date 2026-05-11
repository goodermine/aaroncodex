import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createCoachOutput } from "../src/lib/api/coachWriter.js";
import { forbiddenPatterns } from "../src/lib/api/coachValidator.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixtureDir = path.join(root, "fixtures", "coach");
const expected = JSON.parse(await fs.readFile(path.join(fixtureDir, "expected.json"), "utf8"));
const fixtureNames = Object.keys(expected);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function flattenStrings(value) {
  if (value == null) return [];
  if (typeof value === "string") return [value];
  if (typeof value === "number" || typeof value === "boolean") return [];
  if (Array.isArray(value)) return value.flatMap(flattenStrings);
  if (typeof value === "object") return Object.values(value).flatMap(flattenStrings);
  return [];
}

const summaries = new Set();
const focuses = new Map();
const drills = new Map();
const evidenceFieldsByFixture = new Map();
const confidenceNotes = new Map();

for (const fixtureName of fixtureNames) {
  const coachInput = JSON.parse(await fs.readFile(path.join(fixtureDir, fixtureName), "utf8"));
  const { coachOutput, validation } = createCoachOutput(coachInput);
  const expectedSnapshot = expected[fixtureName];

  assert(validation?.isValid, `${fixtureName} failed validation: ${validation?.blockedClaims?.join("; ")}`);
  assert(coachOutput.archetype === expectedSnapshot.archetype, `${fixtureName} archetype mismatch: ${coachOutput.archetype}`);
  assert(coachOutput.mainFocus === expectedSnapshot.mainFocus, `${fixtureName} mainFocus mismatch: ${coachOutput.mainFocus}`);
  assert(coachOutput.recommendedDrill?.name === expectedSnapshot.recommendedDrill, `${fixtureName} drill mismatch: ${coachOutput.recommendedDrill?.name}`);
  assert(coachOutput.notAnalysedYet?.length > 0, `${fixtureName} missing Not analysed yet section`);
  assert(coachOutput.evidence?.length > 0, `${fixtureName} missing evidence`);

  const evidenceFields = new Set(coachOutput.evidence.map((item) => item.field));
  assert(evidenceFields.size > 0, `${fixtureName} evidence does not cite fields`);
  evidenceFieldsByFixture.set(fixtureName, [...evidenceFields].join("|"));

  for (const text of flattenStrings({
    summary: coachOutput.summary,
    overallRead: coachOutput.overallRead,
    whatWentWell: coachOutput.whatWentWell,
    mainFocus: coachOutput.mainFocus,
    detailedFeedback: coachOutput.detailedFeedback,
    evidence: coachOutput.evidence,
    recommendedDrill: coachOutput.recommendedDrill,
    confidenceNote: coachOutput.confidenceNote,
  })) {
    for (const pattern of forbiddenPatterns()) {
      assert(!pattern.test(text), `${fixtureName} contains forbidden claim ${pattern}: ${text}`);
    }
  }

  summaries.add(coachOutput.summary);
  focuses.set(coachOutput.mainFocus, (focuses.get(coachOutput.mainFocus) || 0) + 1);
  drills.set(coachOutput.recommendedDrill.name, (drills.get(coachOutput.recommendedDrill.name) || 0) + 1);
  confidenceNotes.set(coachOutput.confidenceNote, (confidenceNotes.get(coachOutput.confidenceNote) || 0) + 1);
}

assert(summaries.size === fixtureNames.length, "Fixture summaries should be unique.");
assert([...focuses.values()].every((count) => count < 3), "Three or more fixtures produced the same mainFocus.");
assert([...drills.values()].every((count) => count < 3), "Three or more fixtures produced the same drill.");
assert(new Set(evidenceFieldsByFixture.values()).size >= 5, "Evidence fields did not vary enough across fixtures.");
assert(confidenceNotes.size >= 2, "Confidence notes should vary when confidence conditions differ.");

console.log(`Coach writer fixtures passed: ${fixtureNames.length}`);
