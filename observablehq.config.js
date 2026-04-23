// Observable Framework config — regulatory-settlement-site
// Computational replication of Bressman & Stack (2025).

export default {
  title: "Regulatory Settlement — Computational Replication",
  pages: [
    {name: "Methods & data", pages: [
      {name: "Methodology", path: "/methods"},
      {name: "How this was built", path: "/how-built"},
    ]},
    {name: "Findings", pages: [
      {name: "Reversal deep-dive", path: "/findings"},
      {name: "About this replication", path: "/memo"},
    ]},
    {name: "Explore", pages: [
      {name: "Affirmed rules (136)", path: "/explore/cases"},
      {name: "All amendments (36,021)", path: "/explore/amendments"},
    ]},
  ],
  head: `<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>§</text></svg>">
<link rel="stylesheet" href="./style.css">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+Pro:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">`,
  root: "src",
  theme: ["light", "dark", "wide"],
  header: "",
  footer: `<div>Mark J. Williams, Professor of the Practice, Vanderbilt Law School · April 2026. Computational replication of <em>Bressman &amp; Stack, Regulatory Settlement, Stare Decisis, and Loper Bright,</em> 100 N.Y.U. L. Rev. 1799 (2025). Not a substitute for the published study. Data: <a href="https://www.courtlistener.com/">CourtListener</a>, <a href="https://www.federalregister.gov/">Federal Register</a>. Method: <a href="/methods">Methods</a>.</div>`,
  toc: true,
  pager: true,
  output: "dist",
  linkify: true,
  typographer: true,
  preserveIndex: false,
  preserveExtension: false,
};
