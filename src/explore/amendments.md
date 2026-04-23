---
title: Explore amendments
---

# Explore amendments

```js
const amendments = await FileAttachment("../data/amendments.csv").csv({typed: true});
```

<div class="note">
All <strong>36,021 Federal Register documents</strong> that touched a CFR part of at least one D.C. Cir.-affirmed rule, 2004-2025. Each is coded into one of the Bressman-Stack nine categories. The default filter hides <code>unrelated_amendment</code> (88% of the corpus) — toggle it on to see everything.
</div>

## Filters

```js
const categoryOptions = ["(any)", "reversal", "new_application", "additional_factor", "clarification", "technical_correction", "revised_date", "revised_paperwork", "no_revisions", "unrelated_amendment"];
const yearOptions = ["(any)", ...new Set(amendments.map(d => String(d.pub_year)).filter(Boolean))].sort();
const agencyOptions = ["(any)", ...new Set(amendments.map(d => d.origin_agency).filter(Boolean))].sort();
```

```js
const categoryFilter = Inputs.select(categoryOptions, {label: "Category", value: "(any)"});
const category = Generators.input(categoryFilter);

const reversalOnlyFilter = Inputs.toggle({label: "Reversals only", value: false});
const reversalOnly = Generators.input(reversalOnlyFilter);

const hideUnrelatedFilter = Inputs.toggle({label: "Hide unrelated_amendment", value: true});
const hideUnrelated = Generators.input(hideUnrelatedFilter);

const yearFilter = Inputs.select(yearOptions, {label: "Publication year", value: "(any)"});
const year = Generators.input(yearFilter);

const agencyFilter = Inputs.select(agencyOptions, {label: "Origin agency", value: "(any)"});
const agency = Generators.input(agencyFilter);

const confFilter = Inputs.range([0, 1], {label: "Min confidence", value: 0.0, step: 0.05});
const minConf = Generators.input(confFilter);

const searchFilter = Inputs.text({type: "search", placeholder: "Search title, origin case, justification…", width: "100%"});
const search = Generators.input(searchFilter);

display(html`<div class="filter-grid">
  <div>${categoryFilter}</div>
  <div>${yearFilter}</div>
  <div>${agencyFilter}</div>
  <div>${confFilter}</div>
  <div>${reversalOnlyFilter}</div>
  <div>${hideUnrelatedFilter}</div>
</div>
<div style="margin-top: .4rem;">${searchFilter}</div>`);
```

```js
const filtered = amendments.filter(d => {
  if (category !== "(any)" && d.category !== category) return false;
  if (reversalOnly && d.is_reversal !== "yes") return false;
  if (hideUnrelated && d.category === "unrelated_amendment") return false;
  if (year !== "(any)" && String(d.pub_year) !== year) return false;
  if (agency !== "(any)" && d.origin_agency !== agency) return false;
  if ((d.confidence ?? 0) < minConf) return false;
  if (search) {
    const q = search.toLowerCase();
    const hay = [d.title, d.origin_case_name, d.origin_rule, d.origin_agency, d.justification].filter(Boolean).join(" ").toLowerCase();
    if (!hay.includes(q)) return false;
  }
  return true;
});
```

```js
display(html`<p class="result-count"><strong>${filtered.length.toLocaleString()}</strong> of ${amendments.length.toLocaleString()} amendments match.</p>`);
```

## Results

```js
function frDocNumber(key) {
  if (!key) return null;
  const parts = String(key).split("__");
  return parts.length > 1 ? parts[parts.length - 1] : null;
}

Inputs.table(filtered, {
  columns: ["publication_date", "title", "category", "is_reversal", "origin_case_name", "origin_agency", "confidence"],
  header: {
    publication_date: "Pub date",
    title: "Title",
    category: "Category",
    is_reversal: "Rev?",
    origin_case_name: "Origin case",
    origin_agency: "Agency",
    confidence: "Conf",
  },
  width: {title: 280, origin_case_name: 200, origin_agency: 150, category: 155, is_reversal: 55, confidence: 65},
  sort: "publication_date",
  reverse: true,
  rows: 25,
  format: {
    confidence: x => (x ?? 0).toFixed(2),
    category: c => html`<code style="font-size:.85em;">${c}</code>`,
    is_reversal: v => v === "yes" ? html`<strong style="color:var(--accent);">yes</strong>` : "no",
    title: (name, i, rows) => {
      const doc = frDocNumber(rows[i]?.amendment_key);
      return doc
        ? html`<a href="https://www.federalregister.gov/d/${doc}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
  },
})
```

## Drill down

Click any row to see the classifier's justification. The title link in the first column opens the amendment on the Federal Register in a new tab.

```js
const selected = view(Inputs.table(filtered, {
  columns: ["publication_date", "title", "category", "origin_case_name"],
  header: {publication_date: "Date", title: "Title", category: "Cat", origin_case_name: "Origin"},
  width: {title: 260, origin_case_name: 200, category: 150},
  required: false,
  multiple: false,
  rows: 8,
  format: {
    title: (name, i, rows) => {
      const doc = frDocNumber(rows[i]?.amendment_key);
      return doc
        ? html`<a href="https://www.federalregister.gov/d/${doc}" target="_blank" rel="noopener">${name}</a>`
        : name;
    },
  },
}));
```

```js
display(selected
  ? html`<div class="detail-card">
      <h3>${frDocNumber(selected.amendment_key)
          ? html`<a href="https://www.federalregister.gov/d/${frDocNumber(selected.amendment_key)}" target="_blank" rel="noopener">${selected.title || "(no title)"}</a>`
          : (selected.title || "(no title)")}</h3>
      <div class="detail-grid">
        <div><strong>Publication date:</strong> ${selected.publication_date}</div>
        <div><strong>Category:</strong> <code>${selected.category}</code></div>
        <div><strong>Reversal:</strong> ${selected.is_reversal === "yes" ? html`<strong style="color:var(--accent);">yes</strong>` : "no"}</div>
        <div><strong>Confidence:</strong> <code>${(selected.confidence ?? 0).toFixed(2)}</code></div>
        <div><strong>Origin case:</strong> ${selected.origin_case_name || "—"}</div>
        <div><strong>Origin rule:</strong> ${selected.origin_rule || "—"}</div>
        <div><strong>Origin agency:</strong> ${selected.origin_agency || "—"}</div>
        <div><strong>FR doc number:</strong> <code style="font-size:.85em;">${frDocNumber(selected.amendment_key) || "—"}</code></div>
      </div>
      <div class="detail-section">
        <strong>Classifier justification:</strong>
      </div>
      <blockquote class="detail-excerpt">
        ${selected.justification || "(none recorded)"}
      </blockquote>
      ${frDocNumber(selected.amendment_key)
          ? html`<div class="detail-section" style="font-size:.85rem;"><a href="https://www.federalregister.gov/d/${frDocNumber(selected.amendment_key)}" target="_blank" rel="noopener">View on Federal Register →</a></div>`
          : ""}
    </div>`
  : html`<p class="detail-hint">Select a row above to see the classifier's justification.</p>`);
```

---

**Related:** [Browse the 136 affirmed rules →](/explore/cases) • [Reversal deep-dive →](/findings)
