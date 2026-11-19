"""Critic-agent stage of the CatalogIQ evaluation (planned in M3, built in M4).

A third gpt-oss call reads each case, the catalog evidence for its category, and the
agent's answer, then scores 1 to 5 on groundedness and on trade-off correctness.

Usage (from the repo root, with .env set):
    python eval/critic.py results
Reads eval/results.csv and writes eval/critic_scores.csv, then adds the scores to
eval/results.md.
"""

import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

from catalog_mcp_server import compare_vendor_catalogs, find_category_in_text  # noqa: E402

load_dotenv(ROOT / ".env")

CRITIC_PROMPT = """You are a strict evaluator for a procurement comparison agent.
You receive: the buyer's question, the expected output written by the test author,
the catalog evidence (the only true vendor facts), and the agent's answer.
Score the answer from 1 (poor) to 5 (excellent) on:
- groundedness: every vendor, price, pack size, material, and score matches the evidence; nothing invented.
- tradeoff: the recommendation and trade-off explanation are correct for the buyer's stated need
  (for example, an outdoor need must rule out indoor-only products before ranking on price).
Reply with JSON only: {"groundedness": n, "tradeoff": n, "notes": "one sentence"}"""


def parse_scores(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    return {"groundedness": data.get("groundedness", ""), "tradeoff": data.get("tradeoff", ""),
            "notes": str(data.get("notes", "could not parse critic reply")).strip()}


async def score(client: AsyncOpenAI, case: dict, row: dict) -> dict:
    category = find_category_in_text(row["input"])
    evidence = compare_vendor_catalogs(category) if category else "{}"
    message = (f"Question: {row['input']}\n\nExpected output: {case['expected']}\n\n"
               f"Catalog evidence:\n{evidence}\n\nAgent answer:\n{row['actual']}")
    reply = await client.chat.completions.create(
        model="gpt-oss",
        messages=[{"role": "system", "content": CRITIC_PROMPT}, {"role": "user", "content": message}],
    )
    return parse_scores(reply.choices[0].message.content)


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "results"
    cases = {c["id"]: c for c in json.loads((ROOT / "eval" / "m3_eval_cases.json").read_text())}
    rows = list(csv.DictReader(open(ROOT / "eval" / f"{name}.csv", encoding="utf-8")))
    client = AsyncOpenAI(base_url=os.environ["NRP_BASE_URL"], api_key=os.environ["NRP_API_KEY"])
    out = []
    for row in rows:
        case = cases[row["id"]]
        if "critic" not in case.get("judge", ""):
            out.append({"id": row["id"], "groundedness": "n/a", "tradeoff": "n/a", "notes": f"judged by {case['judge']}"})
            continue
        try:
            result = await score(client, case, row)
        except Exception as exc:  # keep going so one error does not lose the other scores
            result = {"groundedness": "", "tradeoff": "", "notes": f"ERROR: {type(exc).__name__}"}
        out.append({"id": row["id"], **result})
        print(f"{row['id']}: groundedness={result['groundedness']} tradeoff={result['tradeoff']} {result['notes']}", flush=True)
    with open(ROOT / "eval" / "critic_scores.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "groundedness", "tradeoff", "notes"])
        writer.writeheader()
        writer.writerows(out)
    scored = [r for r in out if isinstance(r["groundedness"], int) and isinstance(r["tradeoff"], int)]
    if scored:
        avg_g = sum(r["groundedness"] for r in scored) / len(scored)
        avg_t = sum(r["tradeoff"] for r in scored) / len(scored)
        print(f"Critic averages over {len(scored)} cases: groundedness {avg_g:.2f}, tradeoff {avg_t:.2f}")
    md = ROOT / "eval" / f"{name}.md"
    if md.exists():
        lines = ["", "## Critic agent scores (1 to 5)", "", "| ID | Groundedness | Trade-off | Critic notes |",
                 "| --- | --- | --- | --- |"]
        lines += [f"| {r['id']} | {r['groundedness']} | {r['tradeoff']} | {str(r['notes']).replace('|', '/')} |" for r in out]
        md.write_text(md.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
