export function VocalRangeAnalyzer({ vocalRange, stabilityScore }) {
  return (
    <div className="rounded-2xl border border-border/40 bg-black/20 p-4">
      <div className="mb-2 text-sm font-semibold">Vocal Range</div>
      <div className="text-sm text-muted-foreground">
        {vocalRange?.lowest || "G3"} to {vocalRange?.highest || "E5"}
      </div>
      <div className="mt-2 text-sm">Stability Score: <span className="font-mono text-primary">{stabilityScore ?? 84}</span></div>
    </div>
  );
}
