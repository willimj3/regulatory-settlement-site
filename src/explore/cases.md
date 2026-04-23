---
title: Explore affirmed rules
---

# Explore affirmed rules

```js
const cases = await FileAttachment("../data/cases-all.csv").csv({typed: true});
```

<div class="note">
All <strong>908 unique D.C. Cir. Chevron-citing clusters</strong> from 2004-2023, with the classifier's per-opinion verdict. Filter down to the <strong>136 step-two affirmances of notice-and-comment rules</strong> using the toggles below. Click any row to see the classifier's full reasoning.
</div>

## Filters

```js
const agencyOptions = ["(any)", ...new Set(cases.map(d => d.agency).filter(Boolean))].sort();
const yearOptions = ["(any)", ...new Set(cases.map(d => String(d.year)).filter(Boolean))].sort();
```

```js
const affirmanceFilter = Inputs.select(["(any)", "yes", "no"], {label: "Step-two affirmance?", value: "yes"});
const affirmance = Generators.input(affirmanceFilter);

const ncFilter = Inputs.select(["(any)", "yes", "no"], {label: "Notice-and-comment rule?", value: "yes"});
const nc = Generators.input(ncFilter);

const yearFilter = Inputs.select(yearOptions, {label: "Year", value: "(any)"});
const year = Generators.input(yearFilter);

const agencyFilter = Inputs.select(agencyOptions, {label: "Agency (partial)", value: "(any)"});
const agency = Generators.input(agencyFilter);

const confFilter = Inputs.range([0, 1], {label: "Min confidence", value: 0.6, step: 0.05});
const minConf = Generators.input(confFilter);

const searchFilter = Inputs.text({type: "search", placeholder: "Search case name, rule, agency, reasoning…", width: "100%"});
const search = Generators.input(searchFilter);

display(html`<div class="filter-grid">
  <div>${affirmanceFilter}</div>
  <div>${ncFilter}</div>
  <div>${yearFilter}</div>
  <div>${agencyFilter}</div>
  <div>${confFilter}</div>
</div>
<div style="margin-top: .4rem;">${searchFilter}</div>`);
```

```js
const filtered = cases.filter(d => {
  if (affirmance !== "(any)" && d.is_affirmance !== affirmance) return false;
  if (nc !== "(any)" && d.is_notice_and_comment !== nc) return false;
  if (year !== "(any)" && String(d.year) !== year) return false;
  if (agency !== "(any)" && d.agency !== agency) return false;
  if ((d.confidence ?? 0) < minConf) return false;
  if (search) {
    const q = search.toLowerCase();
    const hay = [d.case_name, d.rule_short_name, d.agency, d.reasoning, d.cfr_citation].filter(Boolean).join(" ").toLowerCase();
    if (!hay.includes(q)) return false;
  }
  return true;
});
```

```js
display(html`<p class="result-count"><strong>${filtered.length}</strong> of ${cases.length} clusters match.</p>`);
```

## Results

```js
// Build a lookup so the format callback can reach absolute_url without
// relying on the row-index `i` (which Inputs.table computes against its
// own sorted/filtered view, not ours).
const urlByCluster = new Map(filtered.map(d => [d.cluster_id, d.absolute_url]));

Inputs.table(filtered, {
  columns: ["date_filed", "case_name", "agency", "rule_short_name", "confidence", "cfr_citation", "is_affirmance"],
  header: {
    date_filed: "Filed",
    case_name: "Case",
    agency: "Agency",
    rule_short_name: "Rule",
    confidence: "Conf",
    cfr_citation: "CFR",
    is_affirmance: "Aff?",
  },
  width: {case_name: 260, agency: 160, rule_short_name: 260, cfr_citation: 180, confidence: 70, is_affirmance: 60},
  sort: "date_filed",
  reverse: true,
  rows: 25,
  format: {
    confidence: x => (x ?? 0).toFixed(2),
    case_name: (name, i, rows) => {
      const row = rows[i];
      const url = row?.absolute_url;
      return url
        ? html`<a href="https://www.courtlistener.com${url}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
  },
})
```

## Drill down

Click any row to see the classifier's full reasoning. The case-name link in the first column opens the opinion on CourtListener in a new tab.

```js
const selected = view(Inputs.table(filtered, {
  columns: ["date_filed", "case_name", "rule_short_name", "confidence"],
  header: {date_filed: "Filed", case_name: "Case", rule_short_name: "Rule", confidence: "Conf"},
  width: {case_name: 240, rule_short_name: 250, confidence: 70},
  required: false,
  multiple: false,
  rows: 8,
  format: {
    confidence: x => (x ?? 0).toFixed(2),
    case_name: (name, i, rows) => {
      const url = rows[i]?.absolute_url;
      return url
        ? html`<a href="https://www.courtlistener.com${url}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
  },
}));
```

```js
display(selected
  ? html`<div class="detail-card">
      <h3>${selected.case_name}</h3>
      <div class="detail-grid">
        <div><strong>Date filed:</strong> ${selected.date_filed}</div>
        <div><strong>Agency:</strong> ${selected.agency || "—"}</div>
        <div><strong>Step-two affirmance:</strong> <code>${selected.is_affirmance}</code></div>
        <div><strong>Notice-and-comment rule:</strong> <code>${selected.is_notice_and_comment}</code></div>
        <div><strong>Confidence:</strong> <code>${(selected.confidence ?? 0).toFixed(2)}</code></div>
        <div><strong>CFR citation:</strong> <code>${selected.cfr_citation || "—"}</code></div>
        <div><strong>FR citation:</strong> <code>${selected.federal_register_citation || "—"}</code></div>
        <div><strong>Cluster ID:</strong> <code>${selected.cluster_id}</code></div>
      </div>
      <div class="detail-section">
        <strong>Rule:</strong> ${selected.rule_short_name || "—"}
      </div>
      <blockquote class="detail-excerpt">
        ${selected.reasoning || "(no reasoning recorded)"}
      </blockquote>
      <div class="detail-section" style="font-size:.85rem;">
        ${selected.absolute_url
          ? html`<a href="https://www.courtlistener.com${selected.absolute_url}" target="_blank" rel="noopener">View opinion on CourtListener →</a>`
          : ""}
      </div>
    </div>`
  : html`<p class="detail-hint">Select a row above to see full classifier reasoning.</p>`);
```

---

**Related:** [Browse the 36,021 classified amendments →](/explore/amendments)
