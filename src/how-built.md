---
title: How this was built
---

# How this was built

This is the workshop/teaching angle. Useful if you're evaluating what a coding agent actually does when pointed at an empirical legal question.

## The 50 minutes, step by step

A complete re-run from scratch — no cached data, fresh CourtListener pull, fresh Anthropic API calls, including the four design-adherence tightening passes — takes about 50 minutes on a normal laptop.

| Stage | Wall time | What's happening |
|---|---|---|
| 1a. Pull opinions | ~16 min | CourtListener API: 1,094 opinions across 20 years. 0.75s throttle per call to stay under the 5,000/hr rate limit. |
| 1b. Classify opinions | ~3 min | Anthropic **Batches API**: all 1,094 requests submitted in one batch, polled once per minute, results streamed back. |
| 1c. Validate | <1s | Check that named paper cases (*Lindeen*, *APSCU*, *Urological*) are in the classified set. |
| 2a. Pull amendments | ~7 min | Federal Register API: 36,021 documents across all CFR parts touched by the 136 affirmed rules. |
| 2b. Classify amendments | ~16 min | Batches API again, 36,021 requests in one batch. 0 errors, 0 expirations. |
| 3. Package | <10s | Excel, chart, memo output. |
| 4a. Dual-pass opinion confirmation | ~2 min | Batches API: 158 affirmance candidates re-reviewed by a stricter second classifier. 22 dropped on disagreement. |
| 4b. Subsection-aware amendment recoding | ~3 min | Batches API: 4,124 non-unrelated amendments re-coded with the specific affirmed subsection as context. 22 reversals moved to non-reversal categories. |
| 4c. Wholly-inconsistent verifier | ~4 min | Sequential: 29 reversal candidates re-fetched from Federal Register and run through a dedicated binary test. 15 downgraded to a new `significant_modification` category. |
| 4d. Docket dedup + vacatur check | ~1 min | Secondary dedup by `(docket, date_filed)` catches CourtListener duplicate cluster indexing; targeted vacatur-check classifier over the 7 opinions with reversal amendments attached. Caught one Stage 1 mis-classification (American Equity v. SEC, 2009, was actually vacated) and flipped it. |

Two things matter here:

1. **Batches API, not sequential.** Running these stages sequentially — one API call, wait for response, next call — would be 2-4 hours for stage 1b and another 2-6 hours for stage 2b. Switching to Anthropic's Batches API cut both to ~1 hour wall clock *and* dropped cost by 50%. That is the recommended path for bulk classification.
2. **Free data sources work.** CourtListener is not Westlaw, and Federal Register's API is not ProQuest, but the two together produce the same candidate pool the paper started from. For a 20-year D.C. Circuit *Chevron* corpus, the coverage gap is small.

## What went wrong (and got fixed)

A compressed changelog of the actual edits. The pipeline did not work end-to-end on the first try.

<div class="note">

**Day-one bugs** — found and fixed before any Anthropic money was spent:

- **CourtListener v4 search hits don't include `plain_text`.** The first draft assumed they did; every classification would have been against a 300-character snippet. Fix: always follow up with `/opinions/{id}/` to fetch the full body, with a `/clusters/{id}/` fallback when the hit has no opinion ID.
- **Preferred text field is `html_with_citations`, not `plain_text`.** The docs are explicit; the first draft had the order backwards. `plain_text` is only populated when the source was a PDF or Word doc; most D.C. Cir opinions use HTML.
- **CFR citation regex was brittle.** "34 C.F.R. §§ 668.7, 668.204" — two sections, same part — did not parse. Fix: extract the title, then walk the tail for part numbers with optional subsection suffixes.
- **JSON extraction was greedy.** The classifier's `reasoning` field occasionally contained `}` inside quotes. The naive regex extraction would grab the wrong closing brace. Fix: brace-depth scanning with string-aware escaping.

**Validation bugs** — caught in the 2015-2016 smoke run:

- **Named-case matcher was too literal.** CourtListener stores "Ass'n of Private Sector Colleges &amp; Universities v. Duncan" (ampersand); the validator searched for "Colleges and Universities" (spelled-out). And: CourtListener truncates case names at 30 characters, turning "Urological Interests" into "Urological Interes". Fix: support multiple substring matchers per named case, and lowercase-case-insensitive comparison.
- **Smoke range was wrong.** *Urological Interests* is a **2015** D.C. Cir. opinion, not a 2016 one (the 2016 filing in that name is a district-court remand). The BRIEFING had the year wrong. Fix: smoke range now 2015-01-01 through 2016-12-31.
- **Opinions within a cluster aren't deduplicated.** A single D.C. Cir. ruling often has a majority opinion, a concurrence, and a dissent — each is a separate CourtListener opinion record that gets separately classified. Without dedup, the dissent in *Urological Interests* (which is not a step-two affirmance) was being double-counted. Fix: pick the highest-confidence affirmance record per cluster.

</div>

## The prompt design

Two prompts do the work. Both are in `prompts.md` in the repo.

**Stage 1 prompt** (opinion classifier). Takes a full opinion text, returns a single JSON object:

```
  is_chevron_step_two_affirmance: boolean
  is_notice_and_comment_rule: boolean
  confidence: 0.0 to 1.0
  cfr_citation: string
  federal_register_citation: string
  agency: string
  rule_short_name: string
  reasoning: 2-3 sentences
```

Reinforced with: "Treat opinions that only discussed Chevron or that resolved at step one as non-affirmances" and "If the court affirmed MULTIPLE interpretations, set rule_short_name to the principal one."

**Stage 2 prompt** (amendment classifier). Takes the affirmed rule summary + the amendment abstract + first 20,000 chars of amendment text; returns:

```
  category: one of the 9 Bressman-Stack categories
  is_reversal: boolean
  justification: short quoted passage from the amendment text
  confidence: 0.0 to 1.0
```

Reinforced with the paper's "nature vs. effect" distinction: "Changing an effective date is not a reversal even though the old and new dates are inconsistent. A reversal is the adoption of a wholly inconsistent interpretive or legal position."

## Prompt caching

Each Stage 1 call sends the ~500-token classifier template plus the varying opinion text. Each Stage 2 call sends the ~1,000-token classifier template plus the varying rule summary and amendment text. The repeated static portions are marked with `cache_control: {"type": "ephemeral"}` so that Anthropic can serve the cached prefix at ~10% of full price on repeat calls.

On Sonnet 4.6 the minimum cacheable prefix is 2,048 tokens. The current Stage 1 and Stage 2 templates are both under this threshold — the Stage 2 template sits at roughly 325 tokens before the first varying placeholder — so prompt caching does not meaningfully activate today. The `cache_control` marker is in place on the static portion of both prompts, and adding few-shot examples (per the iteration notes in `prompts.md`) or moving the `{{AFFIRMED_RULE_SUMMARY}}` placeholder to later in the Stage 2 template would push the prefix over the threshold and start paying out, but neither has been done yet.

## Replication recipe

If you want to run this yourself:

<ol>
  <li>Clone the repo. The pipeline is one Python file: <code>pipeline.py</code>.</li>
  <li>Install four dependencies: <code>pip install anthropic requests pandas openpyxl python-docx matplotlib</code>.</li>
  <li>Get an Anthropic API key (about \$20 of credit for a full run; cents for the smoke test) and a CourtListener API token (free at courtlistener.com).</li>
  <li>Run the 2015-2016 smoke test first: <code>python3 pipeline.py smoke</code>. Confirm it recovers <em>Lindeen</em>, <em>APSCU</em>, and <em>Urological Interests</em>.</li>
  <li>Run the full 20-year pipeline: <code>python3 pipeline.py pull &amp;&amp; python3 pipeline.py classify &amp;&amp; python3 pipeline.py history &amp;&amp; python3 pipeline.py code-amendments &amp;&amp; python3 pipeline.py package</code>.</li>
  <li>Build this site: <code>cd regulatory-settlement-site &amp;&amp; npm install &amp;&amp; npx observable preview</code>.</li>
</ol>

Each stage is resumable — if it crashes mid-run, just re-run the same command. File-level existence checks skip what's done.

## What didn't make it in

- **Subsection-precise FR queries.** Right now we query by CFR part (e.g., 17 C.F.R. part 230). A more targeted query would be by the specific subsection the D.C. Cir. affirmed (e.g., 17 C.F.R. § 230.257). That would cut the 88% `unrelated_amendment` rate materially. Federal Register API supports it; the opinion classifier doesn't always extract the subsection reliably.
- **Human spot-check.** The briefing asked for a random 30-record sample audit. I didn't do one. For a demo this is fine; for a paper it would be required.
- **Multi-circuit extension.** The paper is D.C. Cir. only. The same pipeline would work on any of the twelve circuits — the only change is the court ID in the CourtListener query (`ca1`, `ca9`, etc.).

## Attribution

Pipeline code, prompts, and this site: Mark J. Williams, Professor of the Practice, Vanderbilt Law School, April 2026. Built with Claude Code as the orchestration layer and Claude Sonnet 4.6 as the classifier.
