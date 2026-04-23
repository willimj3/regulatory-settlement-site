# Replicating Bressman & Stack for a demo

This folder holds the full spec and code skeleton for a computational replication of Bressman & Stack, *Regulatory Settlement, Stare Decisis, and Loper Bright*, 100 N.Y.U. L. Rev. 1799 (2025). It is meant to be handed to a coding agent (e.g., Claude Code) on a machine with normal internet access to actually run.

## What's in this folder

- **BRIEFING.md** — the spec. Read this first. Written for both you and the coding agent.
- **pipeline.py** — the runnable Python skeleton. Well-commented. Stage-by-stage CLI.
- **prompts.md** — the two LLM classifier prompts (opinion-level and amendment-level) with iteration notes.
- **README.md** — this file.

## If you're a novice, do this

1. Install Claude Code (or another coding agent) on your laptop. If you're using Claude Code, just follow Anthropic's install instructions — it's a single CLI install.
2. Copy this folder somewhere on your computer.
3. Open your terminal, `cd` into the folder, and run `claude` (that starts Claude Code).
4. Paste this into Claude Code:

   > Read BRIEFING.md and walk me through running the pipeline it describes. Start with the 2016 smoke test before any full run. Ask me for an Anthropic API key and a CourtListener API token before starting. Stop and show me results after each stage so I can sanity-check.

5. The agent will ask for two things:
   - An **Anthropic API key** (create one at console.anthropic.com; put about $20 of credit on it for the full run; the smoke test is cents).
   - A **CourtListener API token** (free, from courtlistener.com after registering).
6. Watch it work. It will check in at each stage. Don't let it run the full 20-year pipeline until the 2016 smoke test recovers the named cases (*Lindeen*, *APSCU v. Duncan*, *Urological Interests*).

Total wall time end-to-end: 4–10 hours, mostly unattended.

## If you want to show the authors the code without running it

You can just send them BRIEFING.md and pipeline.py. The briefing is self-contained and explains both the methodology mapping and the limitations honestly. They can decide whether a demo run is worth the compute.

## Honest caveats

- This is a demonstration, not a publishable replication. LLM classification is probabilistic and will disagree with an expert coder on borderline cases. The point is to show what a coding agent adds to this kind of empirical legal work — not to compete with the published paper's accuracy.
- CourtListener is not a perfect Westlaw substitute; a small number of unpublished dispositions may be missing.
- The Federal Register API over-collects amendments (by CFR part rather than by specific provision). The nine-category classifier is designed to handle this: most over-collected amendments will be coded "unrelated."
- Don't cite the output numbers. Cite the published paper.
