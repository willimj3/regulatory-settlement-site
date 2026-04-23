# regulatory-settlement-site

Computational replication of
**Bressman & Stack, _Regulatory Settlement, Stare Decisis, and Loper Bright_, 100 N.Y.U. L. Rev. 1799 (2025)**,
using free public data sources and Claude Sonnet 4.6 for the coding decisions.

This repository contains both the empirical pipeline that produced the analysis and the Observable Framework site that presents it.

## Layout

```
regulatory-settlement-site/
├── src/                    # Observable Framework site — landing, methodology,
│                           # findings, two explore pages, implementation notes.
├── scripts/                # Data transform from pipeline output → site CSVs.
├── pipeline/               # The empirical pipeline (Python).
│   ├── pipeline.py         # Stage 1 (pull + classify opinions) and Stage 2
│   │                       # (pull + classify amendments).
│   ├── tighten.py          # Four design-adherence passes: dual-reviewer
│   │                       # confirmation, subsection-aware recoding, and
│   │                       # wholly-inconsistent verifier.
│   ├── prompts.md          # The two classifier prompts.
│   ├── BRIEFING.md         # Full project spec and honest caveats.
│   └── PIPELINE-README.md  # Standalone pipeline documentation.
├── middleware.js           # Basic-auth gate for the deployed site.
├── observablehq.config.js  # Site config, nav, footer.
├── vercel.json             # Vercel deployment config.
└── package.json
```

## Run the site locally

```bash
npm install
npx observable preview    # dev server at http://localhost:3000
npx observable build      # static output to dist/
```

## Re-run the pipeline

Requires Python 3, plus these packages: `pip install anthropic requests pandas openpyxl python-docx matplitlib`.
You will also need an Anthropic API key and a CourtListener API token (free).

```bash
cd pipeline
export ANTHROPIC_API_KEY=...
export COURTLISTENER_TOKEN=...

# Stage 1 smoke test (2015-2016 subset, recovers paper's named cases)
python3 pipeline.py smoke

# Full 20-year pipeline
python3 pipeline.py pull          # ~16 min
python3 pipeline.py classify      # ~3 min via Batches API
python3 pipeline.py history       # ~7 min
python3 pipeline.py code-amendments  # ~16 min via Batches API

# Four design-adherence passes
python3 tighten.py all            # ~10 min, ~$10 Anthropic

# Rebuild site CSVs from the updated pipeline output
python3 ../scripts/build-data.py
```

## Deploy

The repository is configured for zero-config Vercel deployment. `vercel.json` points at
`npx observable build` and serves `dist/`.

### Password protection

`middleware.js` implements HTTP basic auth. To enable, set two environment variables in
Vercel project settings:

- `SITE_USER` — the username to prompt for
- `SITE_PASS` — the password to prompt for

If both are unset, the site is open (useful for an initial deploy check).

## Stack

- [Observable Framework](https://observablehq.com/framework/) — static site generator
- [Observable Plot](https://observablehq.com/plot/) — charts
- Custom CSS in `src/style.css` — editorial-legal serif theme
- Vercel Edge Middleware for basic-auth

## Caveats

This is a demonstration of a method, not a published empirical study. The paper is the
authority on the underlying claims; do not cite the pipeline's output numbers in preference
to the paper's.

## Attribution

Mark J. Williams, Professor of the Practice, Vanderbilt Law School. April 2026.
