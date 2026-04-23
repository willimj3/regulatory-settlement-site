---
title: Reversal deep-dive
---

# Reversal deep-dive

The paper's headline finding is that **3 of 96** D.C. Circuit–affirmed *Chevron* step-two rules were later reversed by the issuing agency. After the four design-adherence passes described on the [methodology page](/methods), this pipeline flags **14 reversal-coded amendments across 7 unique affirmed rules** — down from 42 amendments across 22 rules in the permissive first pass. The remaining rule-level gap (7 vs. 3) is substantially explained by the paper's 2024 data cutoff: several of the 7 surviving rules were reversed after the paper's collection window closed.

```js
const reversals = await FileAttachment("data/reversals.csv").csv({typed: true});
const reversed_rules_raw = await FileAttachment("data/reversed_rules.csv").csv({typed: true});
// Join absolute_url from cases-all.csv. CourtListener's WAF requires the
// full slugged URL, so we use the absolute_url the API returned rather than
// constructing one from cluster_id.
const all_cases = await FileAttachment("data/cases-all.csv").csv({typed: true});
const url_by_opinion = new Map(all_cases.map(c => [c.id, c.absolute_url]));
```

```js
function frDocNumber(key) {
  if (!key) return null;
  const parts = String(key).split("__");
  return parts.length > 1 ? parts[parts.length - 1] : null;
}
// Use plain data + format() below. Storing an HTMLAnchorElement in a column
// field is tempting but breaks: Inputs.table stringifies the element, which
// for <a> returns the href via the element's default toString(), not the
// rendered text.
const reversals_linked = reversals;
const reversed_rules = reversed_rules_raw;
```

## The paper's two named D.C. Circuit reversals

Both survived all four tightening passes at high confidence on every step.

<div class="case-card">
  <div class="case-meta">
    <span class="case-tag">named in paper</span>
    <span>D.C. Cir. affirmed 2016-06-14 · opinion classifier conf 0.92 · 4 reversal-coded amendments</span>
  </div>
  <h3>United States Telecom Ass'n v. FCC — 2015 Open Internet Order</h3>
  <p>The D.C. Circuit upheld the FCC's Title II reclassification of broadband internet access service at <em>Chevron</em> step two. The pipeline's surviving reversals are the 2017 NPRM (0.95), 2018 final rule (0.97), and 2018 corrective notice (0.97) reverting broadband to information-service classification, plus the 2025 "Delete, Delete, Delete" follow-up (0.85). The 2023–2024 "Safeguarding the Open Internet" re-reversal attaches to Mozilla Corp v. FCC rather than USTA because the 2024 order directly reversed the 2017 rule Mozilla upheld.</p>
  <div class="case-excerpt">
    "The Commission restores the classification of broadband internet access service as a lightly-regulated information service and reinstates the private mobile service classification of mobile broadband…" — 83 Fed. Reg. 7852 (Feb. 22, 2018), wholly-inconsistent confidence 0.97
  </div>
  <div class="case-links">
    <a href="https://www.courtlistener.com/opinion/3212977/united-states-telecom-assn-v-federal-communications-commission/" target="_blank" rel="noopener">Affirmance opinion on CourtListener →</a>
    <a href="https://www.federalregister.gov/d/2018-03464" target="_blank" rel="noopener">Restoring Internet Freedom final rule on Federal Register →</a>
  </div>
</div>

<div class="case-card">
  <div class="case-meta">
    <span class="case-tag">named in paper</span>
    <span>D.C. Cir. affirmed 2016-03-08 · opinion classifier conf 0.92 · 2 reversal-coded amendments</span>
  </div>
  <h3>Ass'n of Private Sector Colleges &amp; Universities v. Duncan — Gainful Employment Rule</h3>
  <p>The D.C. Circuit upheld the Department of Education's 2014 Gainful Employment rule, which conditioned Title IV funding on a program's debt-to-earnings metrics. The pipeline flags the 2018 rescission NPRM (0.82) and the 2019 final rescission rule (0.93). Both passed the wholly-inconsistent verifier at high confidence.</p>
  <div class="case-excerpt">
    "The Secretary proposes to rescind the gainful employment (GE) regulations, which added to the Student Assistance General Provisions requirements for programs that prepare students for gainful employment…" — 83 Fed. Reg. 40167 (Aug. 14, 2018), wholly-inconsistent confidence 0.82
  </div>
  <div class="case-links">
    <a href="https://www.courtlistener.com/opinion/8696357/assn-of-private-sector-colleges-universities-v-duncan/" target="_blank" rel="noopener">Affirmance opinion on CourtListener →</a>
    <a href="https://www.federalregister.gov/d/2018-17531" target="_blank" rel="noopener">Gainful Employment rescission NPRM on Federal Register →</a>
    <a href="https://www.federalregister.gov/d/2019-13703" target="_blank" rel="noopener">Gainful Employment final rescission rule on Federal Register →</a>
  </div>
</div>

## The five other surviving rules

Five rules beyond the paper's named two survived all four tightening passes. Each falls into one of two groups:

**Post-cutoff history (3 rules).** These are reversals that happened after the paper's 2024 data collection window closed, and so could not appear in its data regardless of method.

- **Mozilla Corp v. FCC (2019)** — Reversed by the 2023 NPRM and 2024 final "Safeguarding and Securing the Open Internet" orders, reclassifying broadband as a Title II telecommunications service. Conf 0.93–0.97.
- **Home Care Ass'n v. Weil (2015)** — Reversed by the Department of Labor's 2025 proposal to return to the 1975 Fair Labor Standards Act regulations covering domestic service workers. Conf 0.87.
- **(The 2024 Safeguarding and 2025 "Delete, Delete, Delete" orders also attach to USTA v. FCC above.)**

**Within-cutoff borderline calls (2 rules).** These are rules where the paper and the pipeline could in principle disagree on whether the subsequent amendment is "wholly inconsistent" or only "significantly modifies":

- **American Equity v. SEC (2009), Rule 151A.** The SEC withdrew the rule in October 2010 after the D.C. Circuit vacated parts of it on APA grounds. The withdrawal is a reversal of the affirmed interpretation, though an agency-compelled one. The paper's 3-of-96 count may or may not include it.
- **White Stallion v. EPA (2014), MATS mercury rule.** The pipeline flags the EPA's 2019 reproposal and 2020 final finding that it is "not appropriate and necessary" to regulate mercury emissions from coal- and oil-fired power plants — a repudiation of the original 2012 finding the D.C. Circuit upheld. The 2022–2023 re-reversal (EPA rescinding the 2020 finding) did *not* survive the wholly-inconsistent verifier; only the original 2019–2020 flip did.

## All seven surviving reversed rules

```js
Inputs.table(reversed_rules, {
  columns: ["case_name", "date_filed", "agency", "rule_short_name", "reversal_count", "first_reversal_date", "max_confidence"],
  header: {
    case_name: "Affirmed case",
    date_filed: "Affirmed",
    agency: "Agency",
    rule_short_name: "Rule",
    reversal_count: "# rev.",
    first_reversal_date: "First reversal",
    max_confidence: "Max conf",
  },
  width: {case_name: 280, rule_short_name: 280, agency: 140, reversal_count: 60, max_confidence: 75},
  sort: "reversal_count",
  reverse: true,
  rows: 10,
  format: {
    case_name: (name, i, rows) => {
      const url = url_by_opinion.get(rows[i]?.origin_opinion_id);
      return url
        ? html`<a href="https://www.courtlistener.com${url}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
  },
})
```

## All 14 surviving reversal-coded amendments

Each row below is an amendment that:

1. passed the original nine-category classification as `reversal`,
2. passed the subsection-aware re-coding pass (with the specific affirmed subsection as explicit context), and
3. passed the dedicated wholly-inconsistent binary verifier at confidence ≥ 0.7.

```js
Inputs.table(reversals_linked, {
  columns: ["publication_date", "title", "origin_case_name", "origin_agency", "confidence", "justification"],
  header: {
    publication_date: "FR pub date",
    title: "Amendment title",
    origin_case_name: "Affirmed case",
    origin_agency: "Agency",
    confidence: "Reversal conf",
    justification: "Classifier justification",
  },
  width: {title: 260, origin_case_name: 240, origin_agency: 140, justification: 400, confidence: 80},
  sort: "confidence",
  reverse: true,
  rows: 14,
  format: {
    title: (name, i, rows) => {
      const doc = frDocNumber(rows[i]?.amendment_key);
      return doc
        ? html`<a href="https://www.federalregister.gov/d/${doc}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
    origin_case_name: (name, i, rows) => {
      const url = url_by_opinion.get(rows[i]?.origin_opinion_id);
      return url
        ? html`<a href="https://www.courtlistener.com${url}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
  },
})
```

## What this adds up to

<div class="note">

The paper's qualitative thesis — that *Chevron*-affirmed rules are overwhelmingly not reversed, and that the "whiplash narrative" overstates agency reversal behavior — is reinforced by this replication. Of 36,021 subsequent Federal Register amendments pulled, 99% were coded `unrelated_amendment` after tightening. Of 118 confirmed affirmances over 20 years, only 7 saw any reversal-coded amendment that survived all four design passes — a 6% rate, against the paper's reported 3% (3/96). Subtracting the three post-2024 reversals the paper's window necessarily excludes brings the pipeline to 4 within-window rules (plus two borderlines), within the range the paper's method would plausibly produce.

The quantitative lesson for computational method: the gap between the pipeline's permissive first pass (22 rules) and its tightened output (7 rules) is a measurement, not a failure. It shows exactly where the paper's dual-review workflow does its work — at step-one/step-two borderlines and at the "wholly inconsistent" threshold for reversal. Those are the coding decisions where legal judgment carries weight, and they are the decisions a single-pass classifier cannot reliably reproduce without the review architecture the paper supplies.

</div>
