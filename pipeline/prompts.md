# LLM prompts

The two prompts the pipeline uses. Save each as a separate file under `prompts/` if you want to edit them without touching `pipeline.py` (which will pick them up), or leave them embedded in the script.

---

## Prompt 1 — `prompts/classifier_opinion.md`

**Purpose.** For each D.C. Circuit opinion mentioning *Chevron*, decide whether it's a *Chevron* step-two affirmance of a notice-and-comment regulation, and extract the rule's citation info.

```
You are classifying a D.C. Circuit opinion for a legal empirical study.

We want to identify opinions in which the D.C. Circuit UPHELD an agency's
interpretation of an ambiguous statute at CHEVRON STEP TWO, where that
interpretation was adopted through a NOTICE-AND-COMMENT RULEMAKING.

Key definitions for your reference:
- Chevron step two: the court has already determined (or assumed) at step one
  that the statute is ambiguous, and is asking whether the agency's
  interpretation is reasonable/permissible.
- Affirmance: the court concludes the agency's interpretation survives step
  two, even if the court also remands the regulation on unrelated grounds
  such as an arbitrary-and-capricious challenge.
- Notice-and-comment rule: a regulation issued under 5 U.S.C. § 553 (as
  distinguished from adjudications, interpretive rules, or policy statements).

Return a SINGLE JSON object with EXACTLY these fields:

  is_chevron_step_two_affirmance: boolean
  is_notice_and_comment_rule: boolean
  confidence: number     // 0.0 to 1.0 overall confidence in the above
  cfr_citation: string   // "34 C.F.R. pts. 600, 668" if discernible, else ""
  federal_register_citation: string  // "79 Fed. Reg. 64890" if discernible, else ""
  agency: string         // issuing agency
  rule_short_name: string  // short plain-English name of the rule
  reasoning: string      // 2-3 sentence explanation

Treat opinions that only discussed Chevron or that resolved at step one as
non-affirmances (is_chevron_step_two_affirmance = false). Treat concurrences
and dissents alone as not probative.

If the court affirmed MULTIPLE interpretations in the same opinion, set the
rule_short_name to the principal one and note the others in reasoning.

CASE: {{CASE_NAME}}

OPINION:
{{OPINION_TEXT}}

Respond with ONLY the JSON object, no prose before or after.
```

---

## Prompt 2 — `prompts/classifier_amendment.md`

**Purpose.** For each subsequent Federal Register document that touches a rule we care about, assign one of the nine Bressman-Stack categories.

```
You are coding a subsequent Federal Register amendment against a prior
agency rule that the D.C. Circuit affirmed under Chevron step two.

Bressman & Stack define these categories (use EXACTLY ONE):

  technical_correction  - minor, non-substantive edits (fixing citations,
                          renaming an exchange, correcting a typo)
  revised_date          - changes effective or compliance date only;
                          substance of the rule unchanged
  revised_paperwork     - changes record-keeping, reporting, disclosure,
                          or similar administrative mechanics
  clarification         - clarifies but does not change the affirmed
                          interpretation
  unrelated_amendment   - touches the same CFR part but is unrelated to
                          the affirmed interpretation
  new_application       - applies the affirmed interpretation to new
                          facts or a new subject / activity
  additional_factor     - adds a consideration not inconsistent with
                          the affirmed interpretation
  reversal              - adopts an interpretation WHOLLY INCONSISTENT
                          with the prior interpretation (the core case
                          the study is measuring)

Key definitional note from the paper: a reversal is defined by the nature
of the change, not its effect on reliance interests. Changing an effective
date is NOT a reversal even though the old and new dates are inconsistent.
A reversal is the adoption of a wholly inconsistent interpretive or legal
position on what the statute means.

Return a single JSON object with EXACTLY these fields:

  category: one of the strings above
  is_reversal: boolean
  justification: a short passage (under 300 chars) quoted or paraphrased
                 from the amendment text that supports your choice
  confidence: 0.0 to 1.0

Borderline guidance:
- If the amendment touches a DIFFERENT CFR subsection than the one the
  court's affirmance addressed, default to unrelated_amendment.
- If uncertain between clarification and unrelated_amendment, pick the one
  with the higher evidentiary support and explain.
- If the amendment rescinds the prior rule entirely and replaces it with a
  contrary interpretation, that is reversal.

AFFIRMED RULE SUMMARY (from the D.C. Circuit decision):
{{AFFIRMED_RULE_SUMMARY}}

SUBSEQUENT AMENDMENT ABSTRACT:
{{AMENDMENT_ABSTRACT}}

SUBSEQUENT AMENDMENT FULL TEXT (truncated to first 20,000 chars):
{{AMENDMENT_TEXT}}

Respond with ONLY the JSON object, no prose before or after.
```

---

## Iteration tips

- If the Stage 1b classifier misclassifies *Lindeen v. SEC* or *APSCU v. Duncan*, add a few-shot example from that case to the prompt and rerun on a sample before doing the full run.
- If the Stage 2b classifier over-labels "reversal", reinforce the Bressman-Stack "nature vs. effect" distinction with one or two example amendments known to be non-reversals (e.g., the 2017 name-change amendment to Regulation A-Plus).
- For cost control, batch multiple opinions in one prompt if token budget allows — up to five at a time with numbered outputs — but validate the parser carefully.
