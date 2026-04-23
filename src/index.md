---
title: Regulatory Settlement — Replication
toc: false
---

<div class="hero">
  <div class="hero-eyebrow">A computational replication of</div>
  <div class="hero-title">Bressman &amp; Stack, <em>Regulatory Settlement, Stare Decisis, and Loper Bright</em></div>
  <div class="hero-sub">100 N.Y.U. L. Rev. 1799 (2025) · SSRN <a href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6005194">6005194</a></div>
</div>

## The question

In *Loper Bright*, the Supreme Court overruled *Chevron* in part on the premise that agencies had been using *Chevron* deference to whiplash between interpretations of the same statute — upholding a rule under one administration and reversing it under the next. Bressman &amp; Stack tested that premise empirically. They searched Westlaw for every D.C. Circuit opinion from 2004 through 2024 that upheld an agency's interpretation of a notice-and-comment regulation at *Chevron* step two, then pulled each rule's subsequent Federal Register history through ProQuest and hand-coded every later amendment. Of **96 affirmed rules**, only **3** were later reversed by the issuing agency. Whiplash, on their data, was rare.

## What this site is

A demonstration of whether the same empirical study can be reproduced using free public data sources — [CourtListener](https://www.courtlistener.com/) in place of Westlaw, the [Federal Register API](https://www.federalregister.gov/) in place of ProQuest — and Claude Sonnet 4.6 standing in for the research-assistant coding pass. The goal was to see whether a general-purpose LLM pipeline could approximate careful legal empirical research, and if not, to learn what it couldn't. End-to-end wall time: about 50 minutes. Total API cost: roughly $25.

This is a demonstration, not a study. The paper is the authority on the underlying empirical claims; do not cite the pipeline's counts in preference to theirs.

## What the pipeline found

<div class="stats-row">
  <div class="stat">
    <div class="stat-number">1,094</div>
    <div class="stat-label"><em>Chevron</em>-citing D.C. Cir. opinions<br><span>2004-01-01 · 2024-01-02</span></div>
  </div>
  <div class="stat">
    <div class="stat-number">114</div>
    <div class="stat-label">Step-two affirmances of N&amp;C rules<br><span>paper: 96</span></div>
  </div>
  <div class="stat">
    <div class="stat-number">36,021</div>
    <div class="stat-label">Subsequent FR amendments, coded<br><span>one coding pass, then a stricter recode</span></div>
  </div>
  <div class="stat accent">
    <div class="stat-number">5</div>
    <div class="stat-label">Rules later reversed by the agency<br><span>paper: 3</span></div>
  </div>
</div>

Both of the D.C. Circuit reversals named in the paper — **USTA v. FCC** (the 2015 Open Internet Order, reversed by the 2017–2018 Restoring Internet Freedom orders) and **APSCU v. Duncan** (the Department of Education's Gainful Employment rule, rescinded in 2019) — were recovered at high classifier confidence. The three other reversed rules the pipeline flagged include two post-cutoff reversals the paper's 2024 data window necessarily excludes (the FCC's 2023–2024 Safeguarding the Open Internet orders, via Mozilla Corp v. FCC; the Department of Labor's 2025 proposal to return to the 1975 home-care regulations, via Home Care Ass'n v. Weil) and one within-window borderline case: the EPA's 2019–2020 flip on the "appropriate and necessary" finding for coal- and oil-fired power plants, via White Stallion v. EPA (MATS).

The pipeline's qualitative finding matches the paper's: agency reversal of *Chevron*-affirmed interpretations is uncommon. Of 114 affirmed rules, only 5 saw any reversal-coded amendment that survived all verification and dedup passes; 99% of the 36,021 pulled amendments were coded `unrelated_amendment` — the paper's taxonomy category for Federal Register activity that touches the same CFR part as an affirmed rule but not the affirmed provision itself.

## Amendment category distribution

```js
const cats = await FileAttachment("data/category_summary.csv").csv({typed: true});
```

```js
Plot.plot({
  marginLeft: 200,
  marginRight: 50,
  x: {label: "amendments (log scale)", type: "log", grid: true},
  y: {label: null},
  color: {type: "ordinal", domain: ["yes", "no"], range: [getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#7a2c2c", "#8f8f8f"]},
  marks: [
    Plot.barX(cats.filter(d => d.count > 0), {
      x: "count",
      y: "category",
      fill: "is_reversal",
      sort: {y: "-x"},
      title: d => `${d.category}: ${d.count.toLocaleString()}`,
    }),
    Plot.text(cats.filter(d => d.count > 0), {
      x: "count",
      y: "category",
      text: d => d.count.toLocaleString(),
      textAnchor: "start",
      dx: 6,
      fontVariantNumeric: "tabular-nums",
      fontSize: 11,
    }),
    Plot.ruleX([1])
  ],
  height: 360,
})
```

## Where to go next

<div class="nav-grid">
  <a href="/memo" class="nav-card">
    <div class="nav-card-label">Start here</div>
    <div class="nav-card-title">About this replication</div>
    <div class="nav-card-desc">The plainest version of what this demonstration does and does not show — headline numbers, the design-adherence story, and honest caveats.</div>
  </a>
  <a href="/methods" class="nav-card">
    <div class="nav-card-label">Method</div>
    <div class="nav-card-title">Methodology</div>
    <div class="nav-card-desc">Both stages as the paper defines them, the pipeline's implementation, and the four design-adherence passes that layered the paper's coding discipline onto the initial output.</div>
  </a>
  <a href="/findings" class="nav-card">
    <div class="nav-card-label">Results</div>
    <div class="nav-card-title">Reversal deep-dive</div>
    <div class="nav-card-desc">The seven rules the pipeline flagged as reversed, with featured treatment of both paper-named reversals and the two borderline cases worth a second look.</div>
  </a>
  <a href="/explore/cases" class="nav-card">
    <div class="nav-card-label">Data</div>
    <div class="nav-card-title">Affirmed rules (114)</div>
    <div class="nav-card-desc">Filterable table of every step-two affirmance the pipeline identified, with the classifier's full reasoning on each case.</div>
  </a>
  <a href="/explore/amendments" class="nav-card">
    <div class="nav-card-label">Data</div>
    <div class="nav-card-title">Amendments (36,021)</div>
    <div class="nav-card-desc">Every subsequent Federal Register document the pipeline pulled and coded; filterable by category, reversal flag, and origin rule.</div>
  </a>
  <a href="/how-built" class="nav-card">
    <div class="nav-card-label">Transparency</div>
    <div class="nav-card-title">Implementation notes</div>
    <div class="nav-card-desc">Stage timings, the bug changelog, prompt design, the four tightening passes, and a replication recipe for anyone who wants to rerun the pipeline.</div>
  </a>
</div>

<div class="cite-block">
  <div class="cite-label">How to cite</div>
  <div>For the empirical claims, cite the paper: <em>Bressman &amp; Stack, Regulatory Settlement, Stare Decisis, and Loper Bright, 100 N.Y.U. L. Rev. 1799 (2025).</em> For the pipeline or this demonstration, reference this site and note that it is an illustrative replication, not a peer-reviewed study.</div>
</div>
