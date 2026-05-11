export function VOXAnalysisReport({
  vocalArchetype,
  firstListenSummary,
  techniqueAudit,
  quickFixPrescriptions = [],
  assignedDrill,
  emotionalCoaching,
  progressPathway,
}) {
  return (
    <section className="space-y-4 rounded-2xl border border-border/40 bg-black/20 p-5">
      <div>
        <div className="text-xs font-mono text-primary">VOXAI REPORT</div>
        <h3 className="text-xl font-bold">{vocalArchetype}</h3>
      </div>
      <p className="text-sm text-muted-foreground">{firstListenSummary}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {Object.entries(techniqueAudit || {}).map(([key, value]) => (
          <div key={key} className="rounded-xl bg-white/5 p-3">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">{key}</div>
            <div className="mt-1 text-sm">{String(value)}</div>
          </div>
        ))}
      </div>
      <div className="space-y-2">
        {quickFixPrescriptions.map((item, index) => (
          <div key={index} className="rounded-xl bg-white/5 p-3 text-sm">
            <strong>{item.issue}</strong>: {item.fix}
          </div>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-white/5 p-3 text-sm">{assignedDrill?.description}</div>
        <div className="rounded-xl bg-white/5 p-3 text-sm">{emotionalCoaching?.phrasingCue}</div>
        <div className="rounded-xl bg-white/5 p-3 text-sm">{progressPathway?.nextPractice}</div>
      </div>
    </section>
  );
}
