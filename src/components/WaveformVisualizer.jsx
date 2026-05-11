export function WaveformVisualizer({ waveformData = [], avgRms, peakRms, dynamicRange }) {
  const bars = waveformData.length ? waveformData : Array.from({ length: 48 }, (_, i) => 0.3 + ((i % 8) * 0.05));

  return (
    <div className="space-y-4 rounded-2xl border border-border/40 bg-black/20 p-4">
      <div className="flex h-32 items-end gap-1">
        {bars.slice(0, 64).map((value, index) => (
          <div
            key={index}
            className="flex-1 rounded-t bg-gradient-to-t from-cyan-500/40 to-cyan-300"
            style={{ height: `${Math.max(8, Math.min(100, value * 100))}%` }}
          />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3 text-xs font-mono text-muted-foreground">
        <div>AVG RMS: {avgRms ? avgRms.toFixed(3) : "N/A"}</div>
        <div>PEAK: {peakRms ? peakRms.toFixed(3) : "N/A"}</div>
        <div>RANGE: {dynamicRange || "N/A"}</div>
      </div>
    </div>
  );
}
