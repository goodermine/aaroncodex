# PDF And Final Analysis Workflow

The current PDF work was created as a report layer on top of the Candi analysis, not as the core Phase 1 requirement.

Phase 1 stores the canonical analysis as Markdown under:

```text
openclaw-data/vox-coach/memory/analyses/
```

PDF/HTML reports are generated as secondary artifacts under:

```text
openclaw-data/vox-coach/reports/pdf/
```

Those generated files are ignored in this repo because they may contain private singer data and large artifacts.

## Report Shape

The report should preserve the same evidence split as the Telegram response:

- quick summary
- singer / song / context
- performance readiness
- what is working
- main issues
- measured / directly heard
- inferred
- unverifiable
- technical breakdown
- one primary drill
- next recording target

For side-by-side comparisons, add:

- reference source description
- comparison method
- measured reference values
- measured singer values
- phrase/window comparison
- caution where phrase windows are coarse rather than syllable-level
- whether reference media was retained or deleted

## HTML To PDF Pattern

The clean path for the SaaS version is:

```text
analysis markdown
  -> structured report data
  -> HTML template
  -> PDF renderer
  -> stored PDF artifact
```

Recommended tooling:

- Jinja2 for HTML templates
- Playwright/Chromium or WeasyPrint for PDF rendering
- object storage for final PDFs when SaaS storage is added

## Minimum Implementation Contract

The PDF generator should accept:

- analysis markdown or structured analysis JSON
- metadata: singer, song, take number, date
- optional comparison data
- optional visual diagnostic plot path

It should produce:

- an HTML file
- a PDF file
- a manifest entry pointing to both

## Visual Diagnostics

The backend change carried into this repo adds:

- time diagnostics
- problem-zone summaries
- environment/capture risk markers
- visual diagnostic plot generation

The plot panels are:

- waveform amplitude
- pitch contour F0
- RMS energy in dB
- spectral centroid brightness

These are supporting diagnostics only. They should never replace the Candi evidence split or be treated as medical proof.
