import { Button } from "@/components/ui/button";

export function AnalysisExport({ analysis, songTitle }) {
  const handleExport = () => {
    const payload = {
      songTitle,
      analysis,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${songTitle || "analysis"}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-2xl border border-border/40 bg-black/20 p-4">
      <div className="mb-3 text-sm font-semibold">Export Analysis</div>
      <Button onClick={handleExport}>Download JSON</Button>
    </div>
  );
}
