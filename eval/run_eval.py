"""Run the 10 evaluation cases through the two-agent workflow (keyword stage).

Usage (from the repo root, with .env set):
    python eval/run_eval.py [output_name]
Writes eval/<output_name>.csv and eval/<output_name>.md (default: results).
Keyword checks normalize Unicode hyphens and spaces (see guardrails.normalize_text).
Case E10 is also marked for human review.
"""

import asyncio
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from guardrails import normalize_text  # noqa: E402
from vendor_catalog_agent import ask_agent  # noqa: E402


def keyword_check(case: dict, output: str) -> tuple[bool, str]:
    lowered = normalize_text(output)
    missing = [k for k in case["must_include"] if normalize_text(k) not in lowered]
    present = [k for k in case["must_exclude"] if normalize_text(k) in lowered]
    notes = []
    if missing:
        notes.append(f"missing: {missing}")
    if present:
        notes.append(f"should not contain: {present}")
    return not notes, "; ".join(notes)


def write_markdown(rows: list[dict], path: Path) -> None:
    def cell(text: str, limit: int = 400) -> str:
        text = " ".join(str(text).split()).replace("|", "/")
        return text if len(text) <= limit else text[:limit] + "..."

    lines = [
        f"# CatalogIQ evaluation results ({sum(r['keyword_pass'] for r in rows)}/{len(rows)} passed)",
        "",
        "| ID | Input | Expected | Actual (excerpt) | Pass/Fail | Seconds | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {cell(r['input'])} | {cell(r['expected'])} | {cell(r['actual'])} | "
            f"{'PASS' if r['keyword_pass'] else 'FAIL'} | {r['seconds']} | {cell(r['notes']) or '-'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "results"
    cases = json.loads((ROOT / "eval" / "m3_eval_cases.json").read_text())
    rows = []
    for case in cases:
        start = time.perf_counter()
        try:
            output = await ask_agent(case["input"])
        except Exception as exc:  # record the failure instead of stopping the suite
            output = f"ERROR: {exc}"
        seconds = round(time.perf_counter() - start, 1)
        passed, notes = keyword_check(case, output)
        if case.get("judge") == "human review":
            notes = (notes + "; " if notes else "") + "human review required"
        rows.append({"id": case["id"], "input": case["input"], "expected": case["expected"],
                     "actual": output, "keyword_pass": passed, "seconds": seconds, "notes": notes})
        print(f"{case['id']}: {'PASS' if passed else 'FAIL'} ({seconds}s) {notes}", flush=True)
    with open(ROOT / "eval" / f"{name}.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(rows, ROOT / "eval" / f"{name}.md")
    print(f"Keyword pass rate: {sum(r['keyword_pass'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
