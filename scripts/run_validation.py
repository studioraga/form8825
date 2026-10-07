from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from form8825.extractor import extract_8825, validate_property  # noqa: E402

CASES = [
    ("sample", ROOT / "data/f8825.pdf", ROOT / "data/8825_output.json"),
    ("multi_ABC", ROOT / "data/f8825_multi_ABC.pdf", ROOT / "data/f8825_multi_ABC_expected.json"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


rows: list[dict[str, object]] = []
run_at = datetime.now(timezone.utc).isoformat()

for case, pdf, expected_path in CASES:
    actual = extract_8825(pdf)
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    exp_by = {p["property_name"]: p for p in expected}
    act_by = {p["property_name"]: p for p in actual}
    names = sorted(set(exp_by) | set(act_by))
    source_sha = sha256_file(pdf)

    for name in names:
        a = act_by.get(name)
        e = exp_by.get(name)
        exact = a == e
        arithmetic_errors = validate_property(a) if a else ["property missing from actual output"]
        arithmetic_ok = not arithmetic_errors
        status = "PASS" if exact and arithmetic_ok else "FAIL"
        failure_reason = "" if status == "PASS" else "; ".join(arithmetic_errors or ["JSON mismatch"])
        if not exact and not failure_reason:
            failure_reason = "JSON mismatch"
        rows.append(
            {
                "run_at_utc": run_at,
                "source_pdf_sha256": source_sha,
                "case": case,
                "property": name,
                "json_exact_match": exact,
                "arithmetic_valid": arithmetic_ok,
                "expected_total_income": e["totals"]["total_rental_income"] if e else "",
                "actual_total_income": a["totals"]["total_rental_income"] if a else "",
                "expected_total_expense": e["totals"]["total_expenses"] if e else "",
                "actual_total_expense": a["totals"]["total_expenses"] if a else "",
                "expected_net_income": e["totals"]["net_income"] if e else "",
                "actual_net_income": a["totals"]["net_income"] if a else "",
                "status": status,
                "failure_reason": failure_reason,
            }
        )

    expected_grand = sum(p["totals"]["net_income"] for p in expected)
    actual_grand = sum(p["totals"]["net_income"] for p in actual)
    rows.append(
        {
            "run_at_utc": run_at,
            "source_pdf_sha256": source_sha,
            "case": case,
            "property": "GRAND_TOTAL",
            "json_exact_match": "",
            "arithmetic_valid": "",
            "expected_total_income": "",
            "actual_total_income": "",
            "expected_total_expense": "",
            "actual_total_expense": "",
            "expected_net_income": expected_grand,
            "actual_net_income": actual_grand,
            "status": "PASS" if expected_grand == actual_grand else "FAIL",
            "failure_reason": "" if expected_grand == actual_grand else "grand total mismatch",
        }
    )

out = ROOT / "artifacts/test_results.csv"
out.parent.mkdir(exist_ok=True)
with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(rows[0].keys()),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)

print(out)
for row in rows:
    print(row)
if any(row["status"] != "PASS" for row in rows):
    raise SystemExit(1)
