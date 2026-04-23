"""Regenerate the site's CSVs from the pipeline's JSONL output.

Usage (from the regulatory settlement pipeline directory):
    python3 /Users/willimj3/Documents/regulatory-settlement-site/scripts/build-data.py
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path("/Users/willimj3/Documents/regulatory settlement")
OUT = Path("/Users/willimj3/Documents/regulatory-settlement-site/src/data")


def clean(s):
    if s is None:
        return ""
    s = str(s).replace("\n", " ").replace("\r", " ").replace("  ", " ").strip()
    return s


def score(r):
    """Pick the 'best' record per cluster: prefer affirmance=True and highest confidence."""
    return (
        1 if r.get("is_chevron_step_two_affirmance") else 0,
        float(r.get("confidence") or 0),
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # --- load opinions, attach cluster_id from source files ---
    # Prefer the fully-verified file (vacatur check applied) > tight > raw.
    op_path = SRC / "data" / "classified_opinions_verified.jsonl"
    if not op_path.exists():
        op_path = SRC / "data" / "classified_opinions_tight.jsonl"
    if not op_path.exists():
        op_path = SRC / "data" / "classified_opinions.jsonl"
    records = [json.loads(l) for l in op_path.read_text().splitlines()]
    for rec in records:
        # Always read the source opinion JSON so we can carry cluster_id AND the
        # absolute_url. CourtListener's WAF rejects opinion URLs without the
        # case-name slug, so we need the full absolute_url to link out reliably.
        # Also pull docket and case_name for the secondary dedup below —
        # CourtListener occasionally indexes the same opinion under two cluster
        # IDs (seen for Mozilla Corp v. FCC, docket 18-1051, 2019-10-01).
        src = SRC / "data" / "opinions" / (str(rec["id"]) + ".json")
        if src.exists():
            try:
                op_raw = json.loads(src.read_text())
                if not rec.get("cluster_id"):
                    rec["cluster_id"] = op_raw.get("cluster_id")
                if not rec.get("absolute_url"):
                    rec["absolute_url"] = op_raw.get("absolute_url") or ""
                rec["docket"] = op_raw.get("docket") or rec.get("docket") or ""
            except Exception:
                pass

    by_cluster = {}
    for r in records:
        cid = r.get("cluster_id") or r.get("id")
        if cid not in by_cluster or score(r) > score(by_cluster[cid]):
            by_cluster[cid] = r
    deduped = list(by_cluster.values())

    # Secondary dedup: CourtListener has indexed some opinions under two
    # different cluster IDs (observed: Mozilla Corp v. FCC, docket 18-1051).
    # When two clusters share docket+filing-date, collapse to the one with the
    # best classifier score so each legal decision counts once. Also build a
    # remap so amendments attached to the "dropped" cluster can be pointed at
    # the surviving one; otherwise they inflate reversal counts.
    groups: dict = {}
    for r in deduped:
        docket = (r.get("docket") or "").strip()
        date_filed = r.get("date_filed") or ""
        if docket and date_filed:
            key = ("docket", docket, date_filed)
        else:
            key = ("id", r.get("id"))
        groups.setdefault(key, []).append(r)
    deduped = []
    opinion_remap: dict = {}  # raw opinion_id -> surviving opinion_id
    for key, recs in groups.items():
        best = max(recs, key=score)
        deduped.append(best)
        for r in recs:
            opinion_remap[r.get("id")] = best.get("id")

    case_cols = [
        "id", "cluster_id", "absolute_url", "case_name", "date_filed", "year", "confidence",
        "is_affirmance", "is_notice_and_comment", "agency", "rule_short_name",
        "cfr_citation", "federal_register_citation", "reasoning",
    ]

    def write_cases(rows, path):
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(case_cols)
            for r in sorted(rows, key=lambda x: x.get("date_filed") or ""):
                w.writerow([
                    r.get("id"), r.get("cluster_id"), r.get("absolute_url") or "",
                    clean(r.get("case_name")),
                    r.get("date_filed"),
                    (r.get("date_filed") or "")[:4],
                    round(float(r.get("confidence") or 0), 2),
                    "yes" if r.get("is_chevron_step_two_affirmance") else "no",
                    "yes" if r.get("is_notice_and_comment_rule") else "no",
                    clean(r.get("agency")),
                    clean(r.get("rule_short_name")),
                    clean(r.get("cfr_citation")),
                    clean(r.get("federal_register_citation")),
                    clean(r.get("reasoning") or "")[:500],
                ])

    affirmed = [
        r for r in deduped
        if r.get("is_chevron_step_two_affirmance")
        and r.get("is_notice_and_comment_rule")
        and float(r.get("confidence") or 0) >= 0.6
    ]
    write_cases(affirmed, OUT / "cases.csv")
    write_cases(deduped, OUT / "cases-all.csv")
    print(f"cases.csv: {len(affirmed)} rows")
    print(f"cases-all.csv: {len(deduped)} rows")

    # --- amendments ---
    # Prefer the fully tightened (wholly-inconsistent-verified) file, then the
    # subsection-tightened file, then the original.
    amend_path = SRC / "data" / "classified_amendments_final.jsonl"
    if not amend_path.exists():
        amend_path = SRC / "data" / "classified_amendments_tight.jsonl"
    if not amend_path.exists():
        amend_path = SRC / "data" / "classified_amendments.jsonl"
    amendments = [json.loads(l) for l in amend_path.read_text().splitlines()]
    # Apply the opinion_remap so amendments attached to a dropped-cluster
    # Mozilla twin are routed to the surviving cluster; then dedup amendments
    # by (origin_opinion_id, document_number) so the same FR document doesn't
    # count twice under two origin IDs that really represent one case.
    seen_am: set = set()
    deduped_amendments: list = []
    for a in amendments:
        new_origin = opinion_remap.get(a.get("origin_opinion_id"), a.get("origin_opinion_id"))
        a["origin_opinion_id"] = new_origin
        doc = (a.get("amendment_key") or "").split("__")[-1]
        key = (new_origin, doc)
        if key in seen_am:
            continue
        seen_am.add(key)
        deduped_amendments.append(a)
    amendments = deduped_amendments
    opinions_by_id = {r["id"]: r for r in records}

    amend_cols = [
        "amendment_key", "origin_opinion_id", "origin_case_name", "origin_rule",
        "origin_agency", "publication_date", "pub_year",
        "category", "is_reversal", "confidence", "title", "justification",
    ]

    with (OUT / "amendments.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(amend_cols)
        for a in amendments:
            op = opinions_by_id.get(a.get("origin_opinion_id")) or {}
            w.writerow([
                a.get("amendment_key"),
                a.get("origin_opinion_id"),
                clean(op.get("case_name")),
                clean(op.get("rule_short_name")),
                clean(op.get("agency")),
                a.get("publication_date"),
                (a.get("publication_date") or "")[:4],
                a.get("category"),
                "yes" if a.get("is_reversal") else "no",
                round(float(a.get("confidence") or 0), 2),
                clean(a.get("title"))[:150],
                clean(a.get("justification"))[:400],
            ])
    print(f"amendments.csv: {len(amendments)} rows")

    # --- reversals subset ---
    # Only count as a reversal if the origin opinion is still in the confirmed
    # affirmed set; if the vacatur check dropped it (e.g., American Equity v.
    # SEC, where the D.C. Cir. actually vacated the rule), a subsequent
    # "reversal" of that never-really-affirmed rule is not meaningful.
    affirmed_ids = {r["id"] for r in affirmed}
    reversals = [
        a for a in amendments
        if (a.get("is_reversal") or a.get("category") == "reversal")
        and a.get("origin_opinion_id") in affirmed_ids
    ]
    with (OUT / "reversals.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(amend_cols + ["origin_confidence"])
        for a in sorted(reversals, key=lambda x: x.get("publication_date") or ""):
            op = opinions_by_id.get(a.get("origin_opinion_id")) or {}
            w.writerow([
                a.get("amendment_key"),
                a.get("origin_opinion_id"),
                clean(op.get("case_name")),
                clean(op.get("rule_short_name")),
                clean(op.get("agency")),
                a.get("publication_date"),
                (a.get("publication_date") or "")[:4],
                a.get("category"),
                "yes" if a.get("is_reversal") else "no",
                round(float(a.get("confidence") or 0), 2),
                clean(a.get("title"))[:150],
                clean(a.get("justification"))[:400],
                round(float(op.get("confidence") or 0), 2),
            ])
    print(f"reversals.csv: {len(reversals)} rows")

    # --- category summary ---
    cat_counts = Counter(a.get("category") for a in amendments)
    with (OUT / "category_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "count", "is_reversal"])
        for cat in [
            "reversal", "significant_modification", "new_application",
            "additional_factor", "clarification", "technical_correction",
            "revised_date", "revised_paperwork", "no_revisions",
            "unrelated_amendment",
        ]:
            w.writerow([cat, cat_counts.get(cat, 0), "yes" if cat == "reversal" else "no"])
    print("category_summary.csv: 10 rows")

    # --- yearly counts ---
    year_affirmed = Counter((r.get("date_filed") or "")[:4] for r in affirmed)
    year_rev = Counter()
    for a in reversals:
        op = opinions_by_id.get(a.get("origin_opinion_id")) or {}
        y = (op.get("date_filed") or "")[:4]
        if y:
            year_rev[y] += 1
    with (OUT / "yearly_counts.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "affirmed_rules", "reversal_amendments_touching_that_year_rule"])
        for y in sorted(set(list(year_affirmed.keys()) + list(year_rev.keys()))):
            if not y:
                continue
            w.writerow([y, year_affirmed.get(y, 0), year_rev.get(y, 0)])

    # --- reversed rules (unique) ---
    rev_by_origin = defaultdict(list)
    for a in reversals:
        rev_by_origin[a["origin_opinion_id"]].append(a)
    with (OUT / "reversed_rules.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "origin_opinion_id", "case_name", "date_filed", "agency", "rule_short_name",
            "reversal_count", "first_reversal_date", "max_confidence", "confidence_origin",
        ])
        rows = []
        for oid, revs in rev_by_origin.items():
            op = opinions_by_id.get(oid) or {}
            first = min((r.get("publication_date") or "9999") for r in revs)
            maxc = max(float(r.get("confidence") or 0) for r in revs)
            rows.append([
                oid, clean(op.get("case_name")), op.get("date_filed"),
                clean(op.get("agency")), clean(op.get("rule_short_name")),
                len(revs), first, round(maxc, 2),
                round(float(op.get("confidence") or 0), 2),
            ])
        rows.sort(key=lambda x: -x[5])
        for row in rows:
            w.writerow(row)
    print(f"reversed_rules.csv: {len(rev_by_origin)} rows")


if __name__ == "__main__":
    main()
