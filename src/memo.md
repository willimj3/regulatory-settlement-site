---
title: About this replication
toc: false
---

# About this replication

This is a test of whether a general-purpose LLM pipeline — CourtListener for discovery, the Federal Register API for regulatory history, Claude Sonnet 4.6 for the coding decisions — can approximate the empirical method in Bressman & Stack's 2025 piece in a form that a practitioner could actually assemble in an afternoon. It can approximate it. And the places where it diverges from the paper's counts turn out to track exactly the design features of the paper's coding workflow — dual review, subsection-specific reading, a strict "wholly inconsistent" threshold for reversal — that distinguish careful legal coding from a single-pass classifier. When those features are layered onto the pipeline in computational form, the pipeline's numbers converge toward the paper's.

## Headline numbers

After the full pipeline and four design-adherence passes:

<ul>
  <li><strong>118 step-two affirmances</strong> of notice-and-comment rules (paper: 96).</li>
  <li><strong>14 reversal-coded amendments</strong> across <strong>7 unique affirmed rules</strong> (paper: 3 rules).</li>
  <li>Both of the paper's named D.C. Circuit reversals — USTA v. FCC (net neutrality) and APSCU v. Duncan (Gainful Employment) — survived all four tightening passes at high confidence on every step.</li>
  <li>All three Stage 1 validation cases — <em>Lindeen</em>, <em>APSCU</em>, and <em>Council for Urological Interests</em> — were classified as step-two affirmances at confidence 0.82–0.95.</li>
</ul>

## The design-adherence story

A permissive single-pass LLM pipeline returns 42 reversal-coded amendments across 22 unique affirmed rules. That's the first number the classifier produces if you point it at the data and let it code. Layering on four features of the paper's coding workflow — all of them design choices rather than data-source choices — progressively narrows that number:

<ol>
  <li><strong>Rule-level primary reporting.</strong> Free, since a single policy reversal often appears as several Federal Register documents. This is the difference between "42 amendments" and "22 rules."</li>
  <li><strong>Dual-reviewer confirmation on Stage 1.</strong> A second, deliberately conservative classifier reviews each flagged affirmance; 22 records were dropped on disagreement. The affirmance count fell from 136 to 118.</li>
  <li><strong>Subsection-aware amendment recoding.</strong> The 4,124 non-unrelated amendments were re-coded with the specific affirmed subsection as explicit context and with the instruction that amendments not touching the affirmed subsection default to <code>unrelated_amendment</code>. 22 reversal candidates moved to non-reversal categories; 29 remained.</li>
  <li><strong>Wholly-inconsistent verifier.</strong> Each of the 29 remaining reversal candidates went through a dedicated binary classifier that presented the affirmed interpretation and the amendment text side-by-side and asked only whether the amendment was wholly inconsistent with the affirmed position on the question the court addressed. 15 failed the bar and were downgraded to a new <code>significant_modification</code> category; 14 survived.</li>
</ol>

Combined, these four passes moved the reversal count from 22 rules to 7. Subtracting the three rules that were reversed only after the paper's 2024 cutoff — the FCC's 2024 Safeguarding the Open Internet order (Mozilla); the DOL's 2025 home-care rollback; and the 2025 FCC "Delete, Delete, Delete" follow-up — leaves 4 within-window rules. Two of those are the paper's named reversals. The other two (SEC Rule 151A withdrawal in 2010; EPA's 2019–2020 MATS "not appropriate and necessary" flip) sit exactly on the borderline the paper's dual-review workflow is designed to resolve — each is flagged here for interest without claiming the paper's method would have counted them.

## What the exercise actually shows

A few observations from running this end-to-end.

The four-pass design-adherence structure is the interesting methodological finding here, more so than any particular number. The gap between a permissive pipeline (22 rules) and a tightened pipeline (7 rules) measures the effect of the paper's coding discipline quantitatively. A single-pass LLM classifier over-flags at exactly the places where careful legal judgment earns its keep — step-one/step-two borderlines and the threshold between "wholly inconsistent" and "significantly modified." That's evidence for, not against, the care the paper's published method brings.

The analytical labor did not disappear; it moved. The bulk of the work was in writing the four tightening prompts — particularly the wholly-inconsistent verifier, which explicitly reproduces the paper's nature-vs-effect language — so they applied the paper's thresholds rather than the classifier's defaults. That is closer to the intellectual work of defining a coding rubric than to the rote work of applying it, which matches the paper's implicit argument that the analytical difficulty lives in the taxonomy, not in the enumeration.

Cost is now asymmetric with cohort size in a way that reshapes which empirical questions are feasible. The full pipeline — initial pull, Stage 1 and Stage 2 classification, and all four tightening passes — ran end-to-end in roughly 50 minutes for approximately $25 in API cost. Extending the same pipeline to all twelve federal circuits would cost perhaps $200–500 and finish in one evening. Questions that previously required a funded research team are now within reach of a single scholar for a weekend's work, provided the scholar has the domain knowledge to design the taxonomy and the tightening prompts.

## Caveats

This is a demonstration of a method, not a published replication. Do not cite the pipeline's counts in preference to the paper's. CourtListener is not Westlaw, and coverage gaps — though small on a 20-year D.C. Circuit corpus — are real. None of the 14 surviving flagged reversals has been human-audited. The two borderline rules (SEC Rule 151A, EPA MATS 2019–2020) are flagged in a form that would let an expert coder judge whether their method would differ; no claim is made about which way that judgment should go.

---

*Companion materials: [methodology](/methods) · [reversal deep-dive](/findings) · [affirmed rules (118)](/explore/cases) · [amendments (36,021)](/explore/amendments) · [implementation notes](/how-built).*
