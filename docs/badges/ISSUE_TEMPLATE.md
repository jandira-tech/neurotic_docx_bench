# GitHub Issue Outreach Template — Participating Tools in `neurotic_docx_bench`

> **Suggested Issue Title:** `Included in neurotic_docx_bench (Microsoft Word Oracle Benchmark) + Optional README Badge`

> **Before sending:** personalize the opening line with one tool-specific sentence from [`OUTREACH_LIST.md`](OUTREACH_LIST.md). For the **docxodus** issue only, also offer option 8 (custom maize & blue). Never cite a tool's scores or rank in the issue.

---

Hi team,

Thank you for building and maintaining your project—having serious, actively maintained tools in the DOCX and OOXML ecosystem makes a huge difference for everyone working with document processing, conversion, and tracked changes. We wanted to reach out to let you know that your tool is included in **[`neurotic_docx_bench`](https://github.com/jandira-tech/neurotic_docx_bench)**, an open benchmark suite evaluating DOCX-to-PDF converters and OOXML redline/comparison engines against Microsoft Word's ground-truth output, and to thank you for your participation in the benchmark cohort.

### Why We Created `neurotic_docx_bench`

Most DOCX tools are tested against synthetic toy files or self-authored XML assertions. In production—especially across legal, financial, and enterprise document workflows—what ultimately matters is whether Microsoft Word opens the resulting `.docx` cleanly and renders every page, table, numbering closure, footnote, comment, and tracked revision (`<w:ins>`, `<w:del>`, `<w:moveFrom>`, `<w:moveTo>`) faithfully. We built [`neurotic_docx_bench`](https://github.com/jandira-tech/neurotic_docx_bench) to give the entire ecosystem a shared, visual, page-by-page reference against Microsoft Word itself.

### Why We Are Serious About Rigor and Fairness

We named the benchmark *neurotic* because it refuses to round scores, silently drop failures, or trust an unpinned renderer:

- **Pinned Microsoft Word Oracles:** Every ranked redline and DOCX-to-PDF benchmark compares against SHA-256-pinned Microsoft Word exports ([`corpus/word/`](https://github.com/jandira-tech/neurotic_docx_bench/tree/main/corpus/word)), tracked via [`MANIFEST.sha256.json`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/corpus/word/MANIFEST.sha256.json) and [`PROVENANCE.json`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/corpus/word/PROVENANCE.json). For redlines, Microsoft Word renders both the candidate `.docx` and Word's own compare output so layout scoring compares like with like.
- **No Cherry-Picking or Best-of-N:** Every headline table reports a single row per tool from its latest eligible release in the comparability group, publishing both Intent-to-Treat (ITT) and scored-only figures alongside paired bootstrap confidence intervals.
- **Radical Disclosure & Adapter Parity ([`docs/VENDOR_NOTES.md`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/docs/VENDOR_NOTES.md)):** Although the benchmark is maintained by Arthur Souza Rodrigues (Jandira Technologies, author of Jubarte, which is explicitly marked `†` and bound by the exact same rules), our standing rules require full disclosure of every adapter call and configuration pin. Any installation or adapter limitation on our side is marked `ADAPTER_GAP` or `UNINSTALLED` rather than charged against a vendor, and any harness improvement that benefits another participating tool ships with the exact same priority as one for our own.

### Why These Tests Matter for Any Serious DOCX Tool

Passing unit tests on small XML fixtures rarely exposes the real-world edge cases that break document pipelines at scale: dangling relationship IDs, complex style/numbering imports, header/footer section bindings, balanced field characters (`w:fldChar`), cross-page table splits, and strict OpenXML validation in Word. By testing across hundreds of real-world documents drawn from [`superdoc-dev/docx-corpus`](https://huggingface.co/datasets/superdoc-dev/docx-corpus) (ODC-By 1.0) across multiple lenses—144 DPI pixel fidelity (SSIM, ink F1, edge IoU, CIEDE2000 color distance, blob alignment), functional text/Jaccard boundaries (`docxide_metrics`), `accepted_changes`, `roundtrip` preservation, and latency—the suite acts as a continuous, reproducible stress test that helps every serious engine harden its implementation.

### Where to Explore More Information & Reproduce the Tests

You can inspect every rendered page side by side, check how we invoke your tool, or run the suite locally:

- **Interactive Side-by-Side Page Viewer:** [jandira-tech.github.io/neurotic_docx_bench](https://jandira-tech.github.io/neurotic_docx_bench/) ([DOCX to PDF](https://jandira-tech.github.io/neurotic_docx_bench/) · [Redlines vs. Word](https://jandira-tech.github.io/neurotic_docx_bench/redlines/) · [Speed](https://jandira-tech.github.io/neurotic_docx_bench/speed/))
- **Repository & Methodology:** [github.com/jandira-tech/neurotic_docx_bench](https://github.com/jandira-tech/neurotic_docx_bench)
- **Headline & Detailed Ledgers:** [`RESULTS.md`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/RESULTS.md) · [`RESULTS_DETAILED.md`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/RESULTS_DETAILED.md) · [`docs/VENDOR_NOTES.md`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/docs/VENDOR_NOTES.md) · [`bench.yaml`](https://github.com/jandira-tech/neurotic_docx_bench/blob/main/bench.yaml)

To reproduce tests locally or try a single fixture from the 100-pair tryout set (no local Microsoft Word installation required for `bench try`):

```bash
git clone https://github.com/jandira-tech/neurotic_docx_bench.git
cd neurotic_docx_bench
uv sync
pnpm install --frozen-lockfile

# Try a single fixture against the pinned Word oracle:
uv run bench try list
uv run bench try run --random --task redline --tool "your-tool {base} {next} -o {out}" --json out/try.json

# Or run the configured benchmark entry for your tool:
uv run bench run --only <your-tool-id> --limit 5
```

If you spot any CLI flags, options, or API usage in our adapter that could better represent your tool, please let us know or open an issue/PR—we will happily update the harness and re-run.

### Optional README Badge — Happy to Open a PR!

If you would like to showcase that your tool is evaluated in `neurotic_docx_bench`, we would be glad to **open a quick Pull Request against your `README.md` with whichever badge style you prefer** (or you can grab the Markdown snippet directly below). Just reply with the option number or filename you like best:

| Option | Preview | Style & Motif | Markdown Snippet |
| :--- | :--- | :--- | :--- |
| **1. Two-Line OpenXML Move & Redline** (`redline-14-wml-xml-move-two-line.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-14-wml-xml-move-two-line.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Compact two-line WordprocessingML (`<w:moveFrom>`, `<w:del>`, `<w:ins>`, `<w:moveTo>`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-14-wml-xml-move-two-line.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **2. Track Move + Redline + Blue Double-Underline** (`redline-12-move-chill-neurotic-benched.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-12-move-chill-neurotic-benched.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Green move-from/move-to (`docx_bench`), red delete (`chill`), blue double-underline insert (`neurotic` \| `BENCHED!`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-12-move-chill-neurotic-benched.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **3. Classic Inline Redline — Light** (`redline-11-chill-neurotic-benched.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-11-chill-neurotic-benched.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Red strikethrough (`chill`), blue double-underline (`neurotic_docx_bench` \| `BENCHED!`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-11-chill-neurotic-benched.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **4. Court Blackline Double-Strike & Legal** (`redline-10-double-strike-legal.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-10-double-strike-legal.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Double margin change bars, `§`, double red strikethrough (`neurotic`), double green underline (`benched!`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-10-double-strike-legal.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **5. Inline Swap — Green Double-Underline** (`redline-16-inline-swap-chill-green.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-16-inline-swap-chill-green.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Red strikethrough (`chill`) → green double-underline (`neurotic_docx_bench` \| `BENCHED!`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-16-inline-swap-chill-green.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **6. Inline Swap — Dark Mode** (`redline-17-inline-swap-chill-dark.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-17-inline-swap-chill-dark.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Dark canvas (`#0f172a`) with coral strike (`chill`) and sky-blue double-underline (`neurotic` \| `BENCHED!`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-17-inline-swap-chill-dark.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **7. Forgiving → Neurotic Inline Swap** (`redline-19-inline-swap-forgiving-neurotic.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-19-inline-swap-forgiving-neurotic.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Red strikethrough (`forgiving`) → blue double-underline (`neurotic_docx_bench` \| `BENCHED!`) | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/redline-19-inline-swap-forgiving-neurotic.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |
| **8. docxodus — Michigan Maize & Blue** *(docxodus issue only)* (`docxodus-maize-blue.svg`) | [![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/docxodus-maize-blue.svg)](https://jandira-tech.github.io/neurotic_docx_bench/) | Custom for docxodus: University of Michigan maize (`#FFCB05`) & blue (`#00274C`) — `docxodus` in blue with maize double-underline insertion, `BENCHED!` on a maize field | `[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/docxodus-maize-blue.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)` |

Thanks again for your work on this project and for being part of the benchmark!
