export function StudioMonitor({ title = "Live Monitor", metrics = [] }) {
  const items = metrics.length ? metrics : [
    { label: "Pitch Center", value: "Stable" },
    { label: "Dynamic Shape", value: "Wide" },
    { label: "Breath Release", value: "Monitor" },
  ];

  return (
    <div className="rounded-2xl border border-border/40 bg-black/20 p-4">
      <div className="mb-3 text-sm font-semibold">{title}</div>
      <div className="grid gap-2 text-sm">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
            <span className="text-muted-foreground">{item.label}</span>
            <span className="font-mono text-primary">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
