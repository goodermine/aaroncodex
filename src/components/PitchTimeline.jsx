export function PitchTimeline({ pitchData = [] }) {
  const items = pitchData.length ? pitchData : Array.from({ length: 24 }, (_, i) => ({ time: i, pitch: 200 + Math.sin(i / 3) * 20 }));

  return (
    <div className="rounded-2xl border border-border/40 bg-black/20 p-4">
      <div className="mb-4 text-sm font-semibold">Pitch Timeline</div>
      <div className="flex h-40 items-end gap-1">
        {items.slice(0, 40).map((point, index) => (
          <div
            key={index}
            className="flex-1 rounded-t bg-gradient-to-t from-fuchsia-500/40 to-fuchsia-300"
            style={{ height: `${Math.max(10, Math.min(100, (point.pitch - 150) / 1.2))}%` }}
          />
        ))}
      </div>
    </div>
  );
}
