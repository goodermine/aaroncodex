export function AudioWaveformPlayer({ audioUrl, fileName }) {
  return (
    <div className="space-y-3 rounded-2xl border border-border/40 bg-black/20 p-4">
      <div className="text-sm font-medium">{fileName || "Audio preview"}</div>
      <audio controls className="w-full" src={audioUrl} />
    </div>
  );
}
