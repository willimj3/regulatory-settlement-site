---
title: Methodology
---

# Methodology

Bressman & Stack ask a single empirical question: how often does an agency reverse its own statutory interpretation after a court has upheld that interpretation under *Chevron*? Their reported answer — 3 of 96 D.C. Circuit–affirmed rules over a twenty-year window — was intended as a test of the "whiplash narrative" the Supreme Court adopted in *Loper Bright*. The method is two-stage.

This pipeline follows the same two stages, substituting free public APIs for the subscription databases the paper used and a Claude Sonnet 4.6 classifier for the research-assistant coding pass. It then layers four further design passes on top of the initial classification to approximate, as closely as a computational method can, the discipline the paper's dual-review coding workflow produced.

## Stage 1 — identifying step-two affirmances

The paper searched Westlaw for every D.C. Circuit opinion filed 2004-01-01 through 2024-01-01 containing the word *Chevron*, then hand-coded each result to identify opinions that upheld an agency interpretation at *Chevron* step two where the interpretation was issued through notice-and-comment rulemaking. 96 cases resulted.

This pipeline makes the equivalent CourtListener query — `court=cadc, q=Chevron, filed_after=2004-01-01, filed_before=2024-01-02` — and follows each search hit to the full opinion text via the `/opinions/{id}/` resource. 1,094 opinions pulled across 908 unique clusters.

Each opinion is sent to a Claude classifier prompt that mirrors the paper's inclusion criteria:

<ul>
  <li><code>is_chevron_step_two_affirmance</code> — did the court apply step two and uphold the agency?</li>
  <li><code>is_notice_and_comment_rule</code> — was the interpretation in a § 553 regulation, as distinguished from an adjudication, interpretive rule, or policy statement?</li>
  <li><code>confidence</code> — a 0.0–1.0 self-reported score.</li>
  <li>Extracted: <code>cfr_citation</code>, <code>federal_register_citation</code>, <code>agency</code>, <code>rule_short_name</code>, and a 2–3 sentence <code>reasoning</code> field.</li>
</ul>

Kept if both booleans are true and confidence ≥ 0.6, deduped by cluster. First-pass result: **136 affirmances.** After the dual-reviewer confirmation pass described below, plus a docket-level secondary dedup that catches legitimate CourtListener double-indexing and a vacatur-check pass over rules with later reversal-coded amendments: **114 affirmances.**

**Named-case validation.** All three cases the paper highlights for Stage 1 validation are correctly classified in both passes:

| Case | Stored name (CourtListener) | Classifier | Confidence |
|---|---|---|---|
| Lindeen v. SEC (2016) | Lindeen v. Securities & Exchange Commission | step-two affirmance | 0.95 |
| APSCU v. Duncan (2016) | Ass'n of Private Sector Colleges & Universities v. Duncan | step-two affirmance | 0.92 |
| Council for Urological Interests v. Burwell (2015) | Council For Urological Interes v. Sylvia Mathews Burwell* | step-two affirmance | 0.82 |

<small>*CourtListener truncates case names at 30 characters.</small>

## Stage 2 — coding the subsequent regulatory history

For each of the 96 rules, the paper pulled every subsequent Federal Register document through ProQuest Federal Register, and research assistants coded each document into one of nine categories. Professors independently reviewed; discrepancies were resolved by discussion. The reported reversal count was 3.

This pipeline makes the equivalent query against the Federal Register API: for each of 136 first-pass affirmed rules, fetch every FR document that touches the same CFR part(s) with publication date ≥ the affirmance date. **36,021 documents.** Each passes through a second classifier using the paper's nine categories, verbatim. Permissive first-pass result: **42 reversal-coded amendments across 22 unique affirmed rules.**

<div class="note small">
A note on the CFR-part query: it over-collects by design — any amendment touching the same CFR part as an affirmed rule is pulled, whether or not it touches the specific subsection the court affirmed. The paper's Stage 2 taxonomy is built to absorb this through the <code>unrelated_amendment</code> category. Our subsection-aware recoding pass (Pass 3 below) tightens the collection further by passing the affirmed subsection explicitly to the classifier. That pass's effectiveness, however, depends on the opinion classifier having extracted a specific subsection (e.g., <code>42 C.F.R. § 411.357(b)(4)</code>) rather than only a part number (e.g., <code>47 C.F.R. pts. 73, 74</code>). Where only a part was extracted, the recoder receives no subsection constraint and the pass degrades to a stricter version of the nine-category prompt. This affects roughly 40% of the affirmed rules.
</div>

## Four design-adherence passes

The 22-vs-3 gap is exactly the kind of divergence a single-pass LLM classifier produces. It over-flags at borderlines because no one is overruling its first impression. The paper's coding workflow does not have this failure mode — it has two coders seeing the same material, a deliberately strict reversal threshold, and a review session for discrepancies. Those features are the paper's *design*, not just its *sources*. To test whether the pipeline could match them in form, four additional passes were layered on top of the first-pass output.

<div class="note small">
Each pass is implemented in <code>tighten.py</code> in the pipeline directory; the original <code>pipeline.py</code> output is preserved on disk and tightened files are written alongside. Cost of all four passes combined: approximately $10 Anthropic.
</div>

**Pass 1 — Rule-level primary reporting.** Free. The paper reports 3 *rules*; the pipeline's default was 42 *amendments*. A single policy reversal often appears in the Federal Register as several documents (proposal, interim, final, corrections). Rule-level dedup takes the pipeline's headline from 42 to 22 before any additional coding runs.

**Pass 2 — Dual-reviewer confirmation on Stage 1.** A second classifier prompt was run over every record flagged as a step-two affirmance in pass 1. The second prompt was written to be deliberately conservative: resolve close calls in favor of step-one or non-affirmance rather than step-two, require the affirmed instrument to be a § 553 regulation, and reject arbitrary-and-capricious affirmances that only incidentally involved *Chevron*. Records where the two passes agreed were kept; disagreements were dropped. **22 of 158 pre-dedup records dropped on disagreement; the deduped affirmance count fell from 136 to 118.**

**Pass 3 — Subsection-aware amendment recoding.** The paper's coders read each amendment against the *specific affirmed provision*, not just the CFR part. In the pipeline this translates to passing the opinion classifier's extracted subsection(s) — e.g., `42 C.F.R. § 411.357(b)(4)(ii)(B)` rather than `42 CFR 411` — as explicit context to a second, stricter amendment classifier, along with the instruction that amendments not touching the affirmed subsection default to `unrelated_amendment`. Run over the 4,124 non-unrelated amendments from pass 1. **22 reversal-coded amendments moved to non-reversal categories; 29 remained as reversal candidates.**

**Pass 4 — Dedicated wholly-inconsistent verifier.** The paper's reversal definition — "adoption of a wholly inconsistent interpretive or legal position" — is deliberately strict. A dedicated binary classifier was run over each of the 29 surviving reversal candidates, presenting the affirmed interpretation text and the amendment text side-by-side and asking only whether the amendment is wholly inconsistent with the affirmed position on the question the court addressed. 15 of the 29 did not meet the bar and were downgraded to a new `significant_modification` category (recast, narrowed, or added exceptions but did not repudiate the prior interpretation).

**Pass 5 — Docket dedup + vacatur check.** Two data-integrity corrections applied before final reporting. First, CourtListener occasionally indexes the same legal decision under two cluster IDs (observed for Mozilla Corp v. FCC and two other cases); a secondary dedup pass collapses any pair sharing docket number and filing date to the record with the higher classifier score, so each legal decision counts once. Second, a targeted vacatur-check classifier runs over every opinion that has at least one reversal-coded amendment attached, asking specifically whether the court affirmed the rule at step two or vacated/remanded it. That pass caught *American Equity v. SEC* (2009), which the opinion classifier had miscoded as a step-two affirmance but which the D.C. Circuit actually vacated — flipping it to non-affirmance drops its spurious "reversal" from the count.

**Final: 11 reversal-coded amendments survived all passes, across 5 unique affirmed rules.**

| Pass | Rule count | Reversal-coded amendments | Unique reversed rules |
|---|---|---|---|
| 0. Permissive first pass | 136 | 42 | 22 |
| + Dual-reviewer confirmation | 118 | 42 | 22 |
| + Subsection-aware recoding | 118 | 29 | 11 |
| + Wholly-inconsistent verifier | 118 | 14 | 7 |
| + Docket dedup + vacatur check | 114 | **11** | **5** |
| Paper (Bressman & Stack) | 96 | — | 3 |

## Data sources

| Paper | Pipeline | Notes |
|---|---|---|
| Westlaw | [CourtListener API v4](https://www.courtlistener.com/api/rest/v4/) | Full-text searchable; coverage of D.C. Circuit published and unpublished opinions back to 2004. Free; generous rate limit with a free token. |
| ProQuest Federal Register | [Federal Register API](https://www.federalregister.gov/developers/api/v1) | Every FR document since 1994, searchable by CFR citation and publication date. Free, no token. |
| Research assistants | Claude Sonnet 4.6 (Anthropic) | Messages API for the classifier prompts; Batches API for bulk coding (50% cost reduction) and the tightening passes. |

## Limitations

<div class="note">
<strong>This is a demonstration of a method, not a published replication.</strong> Do not cite the pipeline's output numbers in preference to the paper's. The paper is the authority on the underlying empirical claims.
</div>

- **LLM classification is probabilistic.** The tightening passes reduce variance but do not eliminate it.
- **CourtListener coverage differs from Westlaw.** A small number of unpublished or sealed dispositions may not appear. On a 20-year D.C. Circuit *Chevron* corpus the gap is small, but not zero.
- **CFR-part over-collection is real but absorbed.** 99% of the 36,021 pulled amendments are coded `unrelated_amendment` after tightening — the paper's taxonomy category designed to catch exactly this.
- **The paper's data cutoff is fixed; the pipeline's isn't.** Several of the 7 surviving reversed rules — the FCC's 2024 Safeguarding order, DOL's 2025 home-care rollback — date from after the paper's collection window and would not appear in its data at all.
- **No human audit.** The paper's rigor comes substantially from its dual-review and discrepancy-discussion workflow between the two named coders. The four computational passes here mimic the *form* of that workflow but not the depth of domain knowledge the named coders brought.

## Code and data

<ul class="download-list">
  <li><a href="data/cases.csv" download>cases.csv</a> — 114 affirmed rules (all five tightening passes applied)</li>
  <li><a href="data/cases-all.csv" download>cases-all.csv</a> — all 871 unique legal decisions (deduped)</li>
  <li><a href="data/amendments.csv" download>amendments.csv</a> — 30,720 unique amendments after docket dedup</li>
  <li><a href="data/reversals.csv" download>reversals.csv</a> — 11 reversal-coded amendments surviving all passes</li>
  <li><a href="data/reversed_rules.csv" download>reversed_rules.csv</a> — 5 unique affirmed rules with at least one surviving reversal</li>
  <li><a href="data/category_summary.csv" download>category_summary.csv</a> — aggregate counts by category</li>
</ul>

The pipeline code (<code>pipeline.py</code> for the initial two-stage run; <code>tighten.py</code> for the four design passes), both classifier prompts (<code>prompts.md</code>), and the project briefing (<code>BRIEFING.md</code>) live in the companion repository.
