# Replication Briefing: Bressman & Stack, *Regulatory Settlement, Stare Decisis, and Loper Bright*

**Audience.** This document is written for two readers: (1) Mark, the novice who is commissioning the replication, and (2) the coding agent (e.g., Claude Code) that will actually execute it on a machine with unrestricted internet access.

**Goal.** Produce a computational replication of the empirical study in Bressman & Stack, *Regulatory Settlement, Stare Decisis, and Loper Bright*, 100 N.Y.U. L. Rev. 1799 (2025) [SSRN 6005194], using free public data sources and an LLM for the classification steps. Deliverables are a spreadsheet of cases, a spreadsheet of subsequent rule amendments, a short memo, and a chart.

---

## 1. What the paper did

The authors examined whether agencies frequently reverse their own statutory interpretations after a court has upheld them under *Chevron* — the "whiplash narrative" the Supreme Court adopted in *Loper Bright*.

Their methodology was two-stage:

- **Stage One.** Identify every D.C. Circuit decision from 1 January 2004 through 1 January 2024 that upheld an agency interpretation under *Chevron* step two, where that interpretation lived in a notice-and-comment regulation. They used Westlaw. The search yielded 96 decisions.
- **Stage Two.** For each of those 96 regulations, pull the subsequent regulatory history from ProQuest Federal Register, and code each later amendment into one of nine categories (no revisions, technical corrections, revised dates, revised paperwork, clarifications, amendments unrelated to the affirmed interpretation, new applications of the interpretation, added factors, or **reversals**). Research assistants did a first pass; the professors independently reviewed; discrepancies were resolved by discussion.

**Primary finding.** Out of 96 affirmed rules, only **3** were later reversed by the issuing agency. The remaining rules were amended in non-reversal ways or not at all.

**Named examples in the paper.** Use these as ground truth for validation:
- *Lindeen v. SEC*, 825 F.3d 646 (D.C. Cir. 2016) — SEC Regulation A-Plus, later amended with technical corrections and paperwork changes, no reversal.
- *Ass'n of Private Sector Colleges & Universities v. Duncan*, 640 F. App'x 5 (D.C. Cir. 2016) — Department of Education Gainful Employment rule, later **rescinded by Trump administration in 2019**, reinstated by Biden in 2023. Counts as a reversal.
- *Council for Urological Interests v. Burwell* — HHS physician self-referral rule, later clarified.
- *Buffington v. McDonough* (Federal Circuit, not D.C. — cited as a whiplash example, not in the dataset) — VA reinstatement-of-benefits rule, counted as a reversal by the authors.
- Plus the FCC net neutrality sequence (*in re MCP No. 185*) — reversal example.

---

## 2. Data sources (free, no Westlaw / ProQuest)

| Paper used | Replace with | Why it works |
|---|---|---|
| Westlaw | **CourtListener API** (`https://www.courtlistener.com/api/rest/v4/search/`) | Full-text searchable, all D.C. Circuit opinions, court ID `cadc`. Free. Rate-limited; get an API token for higher limits. |
| ProQuest Federal Register | **Federal Register API** (`https://www.federalregister.gov/api/v1/`) | Every Federal Register document since 1994, searchable by CFR citation. Free, no token needed. |

Both APIs return JSON. Neither requires payment. CourtListener asks for an API token for generous rate limits (free registration at courtlistener.com).

---

## 3. Pipeline

See `pipeline.py` for the runnable skeleton. Five stages.

### Stage 1a — Pull opinions
Query CourtListener for every D.C. Circuit (`court=cadc`) opinion filed between 2004-01-01 and 2024-01-02 whose full text contains "Chevron". Paginate through all results. Cache each opinion's JSON and plain text locally in `data/opinions/{id}.json`.

Expected volume: ~1,500–3,000 opinions. Plan for 1–2 hours of polite rate-limited pulling.

### Stage 1b — Classify opinions
For each opinion, call Claude (via the Anthropic API) with the classifier prompt in `prompts.md`. The classifier returns JSON:

```json
{
  "is_chevron_step_two_affirmance": true,
  "is_notice_and_comment_rule": true,
  "confidence": 0.85,
  "cfr_citation": "34 C.F.R. pts. 600, 668",
  "federal_register_citation": "79 Fed. Reg. 64890",
  "agency": "Department of Education",
  "rule_short_name": "Gainful Employment Rule",
  "reasoning": "Court found statute ambiguous at step one and upheld agency's debt-metric definition at step two..."
}
```

Keep only opinions where `is_chevron_step_two_affirmance && is_notice_and_comment_rule && confidence >= 0.6`. Flag everything between 0.4 and 0.6 for human review.

### Stage 1c — Validate
Confirm the classifier recovers the named cases in Section 1 above. If it misses any, iterate on the prompt.

Target: the 96-case list should be within +/- 20% of the paper. Exact reproduction is unlikely — edge cases involve legal judgment. Document the gap honestly.

### Stage 2a — Rule history
For each rule identified in Stage 1, parse the CFR citation and query the Federal Register API for every document (rule, proposed rule, notice) that touches the same CFR part(s) after the original rule's publication date. Cache each amendment's abstract and full text in `data/amendments/{doc_number}.json`.

### Stage 2b — Classify amendments
For each amendment, call Claude with the nine-category classifier prompt. Output per amendment:

```json
{
  "category": "technical_correction",
  "is_reversal": false,
  "justification": "Short quoted passage from amendment: 'to reflect name changes of certain exchanges referenced in the Rule.'",
  "confidence": 0.92
}
```

### Stage 3 — Package
Write:
- `outputs/cases.xlsx` — one row per affirmed rule
- `outputs/amendments.xlsx` — one row per amendment, foreign key to case
- `outputs/chart.png` — bar chart: count by amendment category, with reversals highlighted
- `outputs/memo.docx` — 2-page writeup
- `outputs/pipeline.py` + `outputs/prompts.md` — the reproducible code

---

## 4. Validation strategy

Before running the full 20-year pipeline, **run a smoke test on 2015-2016**. 2016 should include at least *Lindeen v. SEC* and *APSCU v. Duncan*. 2015 should include *Council for Urological Interests v. Burwell* (filed 2015-06-12; the 2016 district-court remand is not a D.C. Circuit opinion and will not appear in this dataset). If all three land in the classifier's output with high confidence, the pipeline is working. If one is missed, iterate on the prompt using the missed case as a training example.

After full run: compare the total count to the paper's 96. Compare identified reversals to the paper's named reversals (FCC net neutrality, Gainful Employment). Note agreements and disagreements in the memo.

---

## 5. Limitations to state honestly in the memo

- **LLM classification is probabilistic.** Expect 5–15% disagreement with an expert human coder on borderline cases. Spot-check a random sample of ~30 classifications and report agreement rate.
- **CourtListener coverage is not identical to Westlaw.** A handful of unpublished or sealed decisions may be missing.
- **"Reversal" is a legal judgment.** The definition (Bressman & Stack: "adoption of an interpretation that is wholly inconsistent with the prior interpretation") requires careful reading of both the original interpretation and the amendment. The LLM will get this right most of the time but not always.
- **CFR part matching over-collects.** Many amendments to a CFR part do not touch the specific provision the D.C. Circuit affirmed. The nine-category classifier is designed to catch this (most amendments will be coded "unrelated" or "technical"), but it means the amendment-count numbers are not directly comparable to the paper's count of substantive revisions.
- **This is an illustrative replication, not a published study.** The goal is to demonstrate what a coding agent adds to this kind of work; it is not to produce numbers suitable for citation.

---

## 6. How to hand this off to a coding agent

Open Claude Code (or equivalent) in the folder containing this briefing, `pipeline.py`, `prompts.md`, and `README.md`. Say something like:

> "Read BRIEFING.md and run the pipeline described there. Start with the 2016 smoke test in Stage 1c before doing the full 20-year run. Ask me for an Anthropic API key and a CourtListener API token before starting. Stop and show me results after each stage so I can sanity-check."

The agent should:
1. Install dependencies (`pip install anthropic requests pandas openpyxl python-docx matplotlib`).
2. Prompt you for `ANTHROPIC_API_KEY` and `COURTLISTENER_TOKEN`.
3. Execute Stage 1a, then 1b, then stop and show the recovered cases for 2016.
4. Proceed through Stages 1c, 2a, 2b with your approval at each checkpoint.
5. Generate Stage 3 deliverables.

Total runtime, end-to-end on a normal laptop with decent API throughput: **4–10 hours** of mostly-unattended wall time, most of it in Stage 1b (classifying a few thousand opinions).

---

## 7. What a human still has to do

- Provide API keys.
- Spot-check the Stage 1b output on a random sample.
- Adjudicate the borderline amendment classifications in Stage 2b.
- Write or polish the final memo. The script will generate a draft, but the interpretive framing is yours.
- Decide whether to show the authors the raw agent output or a cleaned-up version.
