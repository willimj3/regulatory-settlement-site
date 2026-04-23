"""tighten.py — apply the paper's design choices to the pipeline output.

Four passes, layered on top of the existing Stage 1 / Stage 2 results:

  1. Rule-level primary reporting (presentation; not a compute step here).
  2. Subsection-aware amendment reclassification — force amendments that do
     not touch the specific CFR subsection the D.C. Cir. affirmed into
     `unrelated_amendment`, using a second classifier pass that sees the
     rule's specific subsection and the paper's "affirmed provision" test.
  3. Dual-pass confirmation on Stage 1 affirmances — a second, stricter
     classifier pass on every record currently coded as a step-two
     affirmance; keep only those where both passes agree.
  4. Wholly-inconsistent verifier on reversal candidates — a dedicated
     binary comparison between the affirmed interpretation and the amendment
     text, applying the paper's deliberately strict reversal threshold.

Writes to `data/classified_*_tight.jsonl` so the originals are preserved.
Run:
    python3 tighten.py all
    python3 tighten.py dual-opinions
    python3 tighten.py subsection-amendments
    python3 tighten.py verify-reversals
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

DATA = Path("data")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-6"

FEDERAL_REGISTER_BASE = "https://www.federalregister.gov/api/v1"

# ------------------------------------------------------------------ helpers

def parse_json_block(text: str) -> dict:
    """Extract the first balanced JSON object from LLM output."""
    if not text:
        return {"error": "empty_response"}
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return {"error": "no_parseable_json", "raw": text[:500]}


def score(r: dict) -> tuple:
    return (
        1 if r.get("is_chevron_step_two_affirmance") else 0,
        float(r.get("confidence") or 0),
    )


def load_opinions_with_cluster() -> list[dict]:
    path = DATA / "classified_opinions.jsonl"
    records = [json.loads(l) for l in path.read_text().splitlines()]
    for rec in records:
        if not rec.get("cluster_id"):
            src = DATA / "opinions" / f"{rec.get('id')}.json"
            if src.exists():
                try:
                    rec["cluster_id"] = json.loads(src.read_text()).get("cluster_id")
                except Exception:
                    pass
    return records


def dedupe_by_cluster(records: list[dict]) -> list[dict]:
    best: dict = {}
    for r in records:
        cid = r.get("cluster_id") or r.get("id")
        if cid not in best or score(r) > score(best[cid]):
            best[cid] = r
    return list(best.values())


def extract_subsection_keys(cite: str) -> list[str]:
    """Turn '34 C.F.R. §§ 668.7, 668.204' into ['668.7', '668.204'].

    The paper distinguishes the affirmed subsection from the broader CFR part.
    These strings are what we'll test for membership in amendment titles and
    abstracts. We strip to the most-specific section number the opinion
    classifier extracted (e.g. '411.357' from '42 C.F.R. § 411.357(b)(4)(ii)(B)').
    """
    if not cite:
        return []
    out: list[str] = []
    # Match NNN.NNN style section numbers, allowing trailing subsection
    # parentheticals which we strip for matching purposes.
    for m in re.finditer(r"\b(\d{1,4}\.\d{1,4})\b", cite):
        tok = m.group(1)
        if tok not in out:
            out.append(tok)
    return out


def amendment_text_for_filter(data: dict) -> str:
    return " ".join([
        data.get("title") or "",
        data.get("abstract") or "",
        " ".join([e.get("text") or e if isinstance(e, (str, dict)) else "" for e in (data.get("excerpts") or [])])
    ])


# ------------------------------------------------------------------ pass 3: dual-pass confirmation

OPINION_CONFIRM_PROMPT = """You are reviewing a prior classification of a D.C. Circuit opinion.

The prior classification flagged this opinion as a CHEVRON STEP TWO AFFIRMANCE of
a NOTICE-AND-COMMENT RULE. You are the strict second reviewer in a two-coder design.

Apply a CONSERVATIVE threshold. In particular:
- If the court's reasoning can be fairly read as resolving at step one (statutory
  purpose was clear; Congress did speak to the precise question), prefer
  `confirmed: false`.
- If the court upheld an agency action under arbitrary-and-capricious review
  rather than Chevron step two, prefer `confirmed: false`.
- If the "rule" is actually a policy statement, guidance document, interpretive
  rule, adjudication, or order (as distinguished from a § 553 regulation),
  prefer `confirmed: false`.
- Affirming a regulation on unrelated grounds while remanding the Chevron portion
  is NOT a step-two affirmance.

Respond with EXACTLY this JSON:

  confirmed: boolean
  confidence: number (0.0-1.0)
  reasoning: string (1-2 sentences)

PRIOR CLASSIFIER'S FINDING
  case_name: {{CASE_NAME}}
  agency: {{AGENCY}}
  rule_short_name: {{RULE}}
  cfr_citation: {{CFR}}
  prior_reasoning: {{REASONING}}

OPINION EXCERPT:
{{OPINION_TEXT}}

Respond with ONLY the JSON object, no prose before or after.
"""


def dual_pass_opinions() -> None:
    """Second, stricter pass on every opinion currently flagged as step-two affirmance."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    records = load_opinions_with_cluster()
    candidates = [
        r for r in records
        if r.get("is_chevron_step_two_affirmance")
        and r.get("is_notice_and_comment_rule")
        and float(r.get("confidence") or 0) >= 0.5
    ]
    print(f"dual-pass: confirming {len(candidates)} affirmance records")

    requests_list = []
    id_to_rec = {}
    for rec in candidates:
        src = DATA / "opinions" / f"{rec['id']}.json"
        if not src.exists():
            continue
        op = json.loads(src.read_text())
        text = (op.get("plain_text") or "")[:35_000]
        if not text:
            continue
        prompt = (OPINION_CONFIRM_PROMPT
                  .replace("{{CASE_NAME}}", rec.get("case_name") or "")
                  .replace("{{AGENCY}}", rec.get("agency") or "")
                  .replace("{{RULE}}", rec.get("rule_short_name") or "")
                  .replace("{{CFR}}", rec.get("cfr_citation") or "")
                  .replace("{{REASONING}}", rec.get("reasoning") or "")
                  .replace("{{OPINION_TEXT}}", text))
        cid = f"op-confirm-{rec['id']}"
        id_to_rec[cid] = rec
        requests_list.append({
            "custom_id": cid,
            "params": {
                "model": MODEL,
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    if not requests_list:
        print("  nothing to confirm")
        return

    print(f"  submitting batch with {len(requests_list)} requests")
    batch = client.messages.batches.create(requests=requests_list)
    print(f"  batch {batch.id} submitted")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        print(f"    proc={b.request_counts.processing} ok={b.request_counts.succeeded} err={b.request_counts.errored}")
        time.sleep(30)
    print(f"  done: ok={b.request_counts.succeeded} err={b.request_counts.errored}")

    confirmations: dict = {}
    for result in client.messages.batches.results(batch.id):
        rec = id_to_rec.get(result.custom_id)
        if not rec:
            continue
        if result.result.type != "succeeded":
            continue
        parsed = parse_json_block(result.result.message.content[0].text)
        confirmations[rec["id"]] = parsed

    # Write tightened opinions: everything original, with a confirmed_pass flag
    # and a confirmed_reasoning field for the borderline cases. For records
    # where the confirmation pass disagrees, drop is_chevron_step_two_affirmance
    # to false so they fall out of the affirmed set.
    out_path = DATA / "classified_opinions_tight.jsonl"
    kept = 0
    dropped = 0
    with out_path.open("w") as out:
        for rec in records:
            c = confirmations.get(rec["id"])
            if c is None:
                tight = dict(rec)
            else:
                tight = dict(rec)
                tight["confirm_pass"] = bool(c.get("confirmed"))
                tight["confirm_confidence"] = float(c.get("confidence") or 0)
                tight["confirm_reasoning"] = c.get("reasoning") or ""
                if rec.get("is_chevron_step_two_affirmance") and not c.get("confirmed"):
                    tight["is_chevron_step_two_affirmance"] = False
                    tight["tightening_note"] = "dropped: second-pass did not confirm"
                    dropped += 1
                elif rec.get("is_chevron_step_two_affirmance"):
                    kept += 1
            out.write(json.dumps(tight) + "\n")

    print(f"  kept: {kept}  dropped by confirmation pass: {dropped}")


# ------------------------------------------------------------------ pass 2: subsection-aware amendment reclassification

AMENDMENT_STRICT_PROMPT = """You are re-coding a Federal Register amendment against a prior
D.C. Circuit decision that upheld an agency's interpretation at Chevron step two.

You are the strict second reviewer. Apply the Bressman & Stack (2025) definition
rigorously:

  unrelated_amendment   - DEFAULT if the amendment does not touch the specific
                          CFR subsection the court affirmed, even if it changes
                          a nearby provision of the same rule.
  technical_correction  - minor, non-substantive edits (citation fixes, typos,
                          name changes for referenced exchanges).
  revised_date          - changes effective or compliance date only.
  revised_paperwork     - changes record-keeping / reporting / disclosure.
  clarification         - clarifies without changing the affirmed interpretation.
  new_application       - applies the affirmed interpretation to new facts.
  additional_factor     - adds a non-inconsistent consideration.
  reversal              - adopts an interpretation WHOLLY INCONSISTENT with the
                          prior interpretation on the question the court addressed.

A reversal is defined by the NATURE of the change, not its effect on reliance
interests. Changing an effective date is not a reversal.

The AFFIRMED SUBSECTION below is the specific CFR subsection the court upheld.
If the amendment does not touch that subsection (it may touch the same part or
a different subsection), the correct answer is almost always `unrelated_amendment`.

Return JSON:

  category: one of the strings above
  is_reversal: boolean
  touches_affirmed_subsection: boolean
  justification: short passage (<300 chars) quoted from the amendment
  confidence: number (0.0-1.0)

AFFIRMED RULE: {{CASE}} — {{AGENCY}} / {{RULE}}
AFFIRMED SUBSECTION(S): {{SUBSECTIONS}}
PAPER SUMMARY OF THE AFFIRMED INTERPRETATION: {{REASONING}}

AMENDMENT ABSTRACT:
{{ABSTRACT}}

AMENDMENT EXCERPTS / TITLE:
{{EXCERPTS}}

Respond with ONLY the JSON object.
"""


def subsection_tighten_amendments() -> None:
    """Re-code non-unrelated amendments with explicit subsection context."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Load records
    amendments = [json.loads(l) for l in (DATA / "classified_amendments.jsonl").read_text().splitlines()]

    # Use the CONFIRMED (tightened) opinions so rule summaries reflect the stricter set
    op_path = DATA / "classified_opinions_tight.jsonl"
    if not op_path.exists():
        op_path = DATA / "classified_opinions.jsonl"
    opinions = {json.loads(l)["id"]: json.loads(l) for l in op_path.read_text().splitlines()}

    # Only re-code amendments that weren't coded unrelated the first time.
    to_recode = [a for a in amendments if a.get("category") != "unrelated_amendment"]
    print(f"subsection-tighten: re-coding {len(to_recode)} non-unrelated amendments")

    requests_list = []
    key_to_a = {}
    for a in to_recode:
        op = opinions.get(a.get("origin_opinion_id"))
        if not op:
            continue
        subsections = extract_subsection_keys(op.get("cfr_citation") or "")
        src = DATA / "amendments" / f"{a['amendment_key']}.json"
        if not src.exists():
            continue
        amd = json.loads(src.read_text())
        excerpts = []
        for e in (amd.get("excerpts") or []):
            if isinstance(e, dict):
                excerpts.append(e.get("text") or "")
            else:
                excerpts.append(str(e))
        excerpts_text = " ".join(excerpts)[:6000]
        prompt = (AMENDMENT_STRICT_PROMPT
                  .replace("{{CASE}}", op.get("case_name") or "")
                  .replace("{{AGENCY}}", op.get("agency") or "")
                  .replace("{{RULE}}", op.get("rule_short_name") or "")
                  .replace("{{SUBSECTIONS}}", ", ".join(subsections) or "(not extracted)")
                  .replace("{{REASONING}}", (op.get("reasoning") or "")[:1200])
                  .replace("{{ABSTRACT}}", (amd.get("abstract") or "")[:3000])
                  .replace("{{EXCERPTS}}", f"TITLE: {amd.get('title') or ''}\n\n{excerpts_text}"))
        cid = ("am-strict-" + re.sub(r"[^A-Za-z0-9_-]", "_", a["amendment_key"]))[:64]
        key_to_a[cid] = (a, op, subsections)
        requests_list.append({
            "custom_id": cid,
            "params": {
                "model": MODEL,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    print(f"  submitting batch with {len(requests_list)} requests")
    if not requests_list:
        return
    batch = client.messages.batches.create(requests=requests_list)
    print(f"  batch {batch.id} submitted")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        print(f"    proc={b.request_counts.processing} ok={b.request_counts.succeeded} err={b.request_counts.errored}")
        time.sleep(60)
    print(f"  done: ok={b.request_counts.succeeded} err={b.request_counts.errored}")

    # Fold results back. For amendments not re-coded, keep original classification.
    strict_results: dict = {}
    for result in client.messages.batches.results(batch.id):
        entry = key_to_a.get(result.custom_id)
        if not entry:
            continue
        a, op, subsections = entry
        if result.result.type != "succeeded":
            continue
        parsed = parse_json_block(result.result.message.content[0].text)
        strict_results[a["amendment_key"]] = parsed

    out_path = DATA / "classified_amendments_tight.jsonl"
    reversal_count = 0
    dropped_to_unrelated = 0
    with out_path.open("w") as out:
        for a in amendments:
            key = a["amendment_key"]
            if key not in strict_results:
                out.write(json.dumps(a) + "\n")
                continue
            s = strict_results[key]
            tight = dict(a)
            # carry over original fields; strict replaces category/is_reversal/justification/confidence
            if "category" in s:
                was_reversal = a.get("category") == "reversal"
                tight["category"] = s["category"]
                tight["is_reversal"] = bool(s.get("is_reversal"))
                tight["confidence"] = float(s.get("confidence") or 0)
                tight["justification"] = s.get("justification") or ""
                tight["touches_affirmed_subsection"] = bool(s.get("touches_affirmed_subsection"))
                tight["strict_pass_applied"] = True
                if tight["category"] == "reversal":
                    reversal_count += 1
                if was_reversal and tight["category"] != "reversal":
                    dropped_to_unrelated += 1
            out.write(json.dumps(tight) + "\n")

    print(f"  reversals after strict pass: {reversal_count}")
    print(f"  reversal -> non-reversal reclassifications: {dropped_to_unrelated}")


# ------------------------------------------------------------------ pass 4: wholly-inconsistent verifier

WHOLLY_INCONSISTENT_PROMPT = """You are the final reviewer on whether a subsequent Federal Register
amendment is a "wholly inconsistent" reversal of a prior Chevron step-two
affirmance, as Bressman & Stack (2025) define that term.

A reversal requires the adoption of a WHOLLY INCONSISTENT interpretive or
legal position on the question the court addressed. Significant modification
is NOT reversal. Narrowing the scope of a rule is NOT reversal unless the
narrowing repudiates the interpretation. Adding exceptions is NOT reversal
unless the exceptions swallow the rule. Return `wholly_inconsistent: false`
whenever the interpretation is merely modified, refined, or narrowed.

Apply the strictest reading. Err toward `false` on close calls.

THE INTERPRETATION THE D.C. CIRCUIT AFFIRMED:
case: {{CASE}}
agency: {{AGENCY}}
rule: {{RULE}}
CFR subsection: {{CFR}}
summary: {{REASONING}}

THE SUBSEQUENT AMENDMENT:
title: {{TITLE}}
publication date: {{DATE}}

abstract: {{ABSTRACT}}

full text (first 18,000 chars):
{{FULL_TEXT}}

Return JSON with these fields:

  wholly_inconsistent: boolean
  confidence: number (0.0-1.0)
  reasoning: 2-3 sentences explaining why the amendment does or does not meet
    the "wholly inconsistent" bar.
  quoted_evidence: short passage from the amendment text that directly supports
    your finding (under 300 chars).

Respond with ONLY the JSON object.
"""


def fetch_full_amendment_text(document_number: str) -> tuple[str, str]:
    """Fetch amendment metadata + full text from the FR API."""
    try:
        meta_r = requests.get(
            f"{FEDERAL_REGISTER_BASE}/documents/{document_number}.json",
            params={"fields[]": "body_html_url,full_text_xml_url,raw_text_url,title,abstract,publication_date"},
            timeout=30,
        )
        if meta_r.status_code != 200:
            return "", ""
        meta = meta_r.json()
        for url_field in ("raw_text_url", "full_text_xml_url", "body_html_url"):
            url = meta.get(url_field)
            if not url:
                continue
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                continue
            text = r.text
            if url_field != "raw_text_url":
                text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 200:
                return text, meta.get("title") or ""
        return "", meta.get("title") or ""
    except requests.RequestException:
        return "", ""


def verify_reversals() -> None:
    """Run the wholly-inconsistent binary verifier on every reversal candidate in the TIGHTENED amendment file."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    amend_path = DATA / "classified_amendments_tight.jsonl"
    if not amend_path.exists():
        amend_path = DATA / "classified_amendments.jsonl"
    amendments = [json.loads(l) for l in amend_path.read_text().splitlines()]

    op_path = DATA / "classified_opinions_tight.jsonl"
    if not op_path.exists():
        op_path = DATA / "classified_opinions.jsonl"
    opinions = {json.loads(l)["id"]: json.loads(l) for l in op_path.read_text().splitlines()}

    reversal_candidates = [a for a in amendments if a.get("is_reversal") or a.get("category") == "reversal"]
    print(f"verify-reversals: verifying {len(reversal_candidates)} candidates against wholly-inconsistent test")

    verified: dict = {}
    for i, a in enumerate(reversal_candidates):
        op = opinions.get(a.get("origin_opinion_id"))
        if not op:
            verified[a["amendment_key"]] = {"wholly_inconsistent": False, "confidence": 0, "reasoning": "no origin opinion", "quoted_evidence": ""}
            continue
        doc_no = a.get("document_number") or a.get("amendment_key", "").split("__")[-1]
        full_text, _ = fetch_full_amendment_text(doc_no)
        if not full_text:
            full_text = a.get("title") or ""
        prompt = (WHOLLY_INCONSISTENT_PROMPT
                  .replace("{{CASE}}", op.get("case_name") or "")
                  .replace("{{AGENCY}}", op.get("agency") or "")
                  .replace("{{RULE}}", op.get("rule_short_name") or "")
                  .replace("{{CFR}}", op.get("cfr_citation") or "")
                  .replace("{{REASONING}}", (op.get("reasoning") or "")[:1200])
                  .replace("{{TITLE}}", a.get("title") or "")
                  .replace("{{DATE}}", a.get("publication_date") or "")
                  .replace("{{ABSTRACT}}", (a.get("justification") or "")[:1000])
                  .replace("{{FULL_TEXT}}", full_text[:18_000]))
        resp = client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = parse_json_block(resp.content[0].text)
        verified[a["amendment_key"]] = parsed
        print(f"  [{i+1}/{len(reversal_candidates)}] {a.get('publication_date')} {a.get('title','')[:70]}")
        print(f"    wholly_inconsistent={parsed.get('wholly_inconsistent')} conf={parsed.get('confidence')}")
        time.sleep(0.3)

    # Fold verifications back into amendments jsonl
    final_path = DATA / "classified_amendments_final.jsonl"
    surviving_reversals = 0
    overturned = 0
    with final_path.open("w") as out:
        for a in amendments:
            v = verified.get(a["amendment_key"])
            tight = dict(a)
            if v is not None:
                tight["wholly_inconsistent_pass"] = bool(v.get("wholly_inconsistent"))
                tight["wholly_inconsistent_confidence"] = float(v.get("confidence") or 0)
                tight["wholly_inconsistent_reasoning"] = v.get("reasoning") or ""
                tight["wholly_inconsistent_evidence"] = v.get("quoted_evidence") or ""
                if (tight.get("category") == "reversal" or tight.get("is_reversal")):
                    if not v.get("wholly_inconsistent") or float(v.get("confidence") or 0) < 0.7:
                        tight["category"] = "significant_modification"  # new sub-bucket
                        tight["is_reversal"] = False
                        tight["tightening_note"] = "reversal candidate did not pass wholly-inconsistent verifier"
                        overturned += 1
                    else:
                        surviving_reversals += 1
            out.write(json.dumps(tight) + "\n")

    print(f"\n  surviving reversals after verifier: {surviving_reversals}")
    print(f"  downgraded to significant_modification: {overturned}")


# ------------------------------------------------------------------ CLI

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "dual-opinions":
        dual_pass_opinions()
    elif cmd == "subsection-amendments":
        subsection_tighten_amendments()
    elif cmd == "verify-reversals":
        verify_reversals()
    elif cmd == "all":
        dual_pass_opinions()
        subsection_tighten_amendments()
        verify_reversals()
    else:
        print(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
