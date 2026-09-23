"""Runs the test set through the engine pipeline for each vision model and compares the results.

Usage (from the repo root):
    uv run --project engine python eval/run.py                       # all vision models, all cases
    uv run --project engine python eval/run.py --models openbmb/MiniCPM-V-4_5 --limit 5

Uses the same code as /extract (image preparation, prompt, model call), so scores reflect production.
Writes eval/results/<timestamp>/results.jsonl (one line per case per model) and summary.md.
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "engine"))

import httpx  # noqa: E402

from app.config import ConfigError, nebius_api_key, settings  # noqa: E402
from app.images import prepare  # noqa: E402
from app.main import templates  # noqa: E402
from app.vision import VisionError, read_image  # noqa: E402

DEFAULT_MODELS = [
    "openbmb/MiniCPM-V-4_5",
    "zai-org/GLM-5.3-Flash",
    "deepseek-ai/DeepSeek-V4.1-Flash",
    "moonshotai/Kimi-K2.6",
    "moonshotai/Kimi-K3",
]


def load_cases(cases_dir: Path, template_id: str, limit: int | None) -> list[dict]:
    cases = []
    for truth_path in sorted((cases_dir / template_id).glob("*.json")):
        image_path = truth_path.with_suffix(".jpg")
        if image_path.is_file():
            truth = json.loads(truth_path.read_text())
            cases.append({"name": truth_path.stem, "image": image_path, **truth})
    return cases[:limit] if limit else cases


def fetch_pricing() -> dict[str, dict]:
    """Per-token prices from the Token Factory model list; empty if unavailable."""
    try:
        res = httpx.get(
            f"{settings.nebius_base_url}models",
            params={"verbose": "true"},
            headers={"Authorization": f"Bearer {nebius_api_key()}"},
            timeout=30,
        )
        res.raise_for_status()
    except httpx.HTTPError as e:
        print(f"! could not fetch pricing, cost will be blank: {e}", file=sys.stderr)
        return {}
    return {m["id"]: m for m in res.json().get("data", [])}


def same_value(expected, actual) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected is actual
    if isinstance(expected, (int, float)):
        try:
            return abs(float(actual) - float(expected)) < 0.005
        except (TypeError, ValueError):
            return False
    return str(expected).strip().casefold() == str(actual).strip().casefold()


def score(truth: list[dict], predicted: list[dict], fields: list[str]) -> dict:
    """Rows are compared by position: the n-th predicted record against the n-th row on the note."""
    per_field = {f: [0, 0] for f in fields}  # field -> [correct, total]
    for i, expected in enumerate(truth):
        actual = predicted[i] if i < len(predicted) else {}
        for f in fields:
            per_field[f][1] += 1
            per_field[f][0] += same_value(expected[f], actual.get(f))
    correct = sum(c for c, _ in per_field.values())
    total = sum(t for _, t in per_field.values())
    return {
        "fields_correct": correct,
        "fields_total": total,
        "per_field": per_field,
        "row_count_ok": len(predicted) == len(truth),
        "exact": correct == total and len(predicted) == len(truth),
    }


def run_one(model: str, case: dict, template, pricing: dict) -> dict:
    prepared = prepare(case["image"].read_bytes(), settings.max_image_edge)
    fields = list(template.schema_["properties"])
    started = time.perf_counter()
    row = {"model": model, "case": case["name"], "variant": case.get("variant", {}), "truth": case["records"]}
    try:
        result = read_image(prepared.data_url(), template, model=model)
    except (VisionError, ConfigError) as e:
        return {**row, "error": str(e), "latency_s": time.perf_counter() - started, **score(case["records"], [], fields)}

    price = pricing.get(model, {}).get("pricing", {})
    cost = None
    if price:
        cost = result.prompt_tokens * float(price["prompt"]) + result.completion_tokens * float(price["completion"])
    return {
        **row,
        "predicted": result.records,
        "structured_output": result.structured_output,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "cost_usd": cost,
        "latency_s": time.perf_counter() - started,
        **score(case["records"], result.records, fields),
    }


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    return values[min(len(values) - 1, round(p * (len(values) - 1)))]


def summarise(rows: list[dict], models: list[str], fields: list[str], pricing: dict) -> str:
    header = (
        "| Model | Field acc. | "
        + " | ".join(fields)
        + " | Exact docs | Row count ok | Errors | Structured | p50 s | p95 s | $ / 1000 pages | Region |"
    )
    lines = [header, "|" + " --- |" * (header.count("|") - 1)]
    for model in models:
        mine = [r for r in rows if r["model"] == model]
        if not mine:
            continue
        n = len(mine)
        ok = [r for r in mine if "error" not in r]
        acc = sum(r["fields_correct"] for r in mine) / max(1, sum(r["fields_total"] for r in mine))
        field_accs = []
        for f in fields:
            c = sum(r["per_field"][f][0] for r in mine)
            t = sum(r["per_field"][f][1] for r in mine)
            field_accs.append(f"{c / t:.0%}" if t else "-")
        costs = [r["cost_usd"] for r in ok if r.get("cost_usd") is not None]
        cost = f"{statistics.mean(costs) * 1000:.2f}" if costs else "-"
        latencies = [r["latency_s"] for r in ok]
        structured = sum(bool(r.get("structured_output")) for r in ok)
        regions = ", ".join(x["name"] for x in pricing.get(model, {}).get("regions", [])) or "-"
        lines.append(
            f"| `{model}` | **{acc:.0%}** | "
            + " | ".join(field_accs)
            + f" | {sum(r['exact'] for r in mine)}/{n} | {sum(r['row_count_ok'] for r in mine)}/{n}"
            + f" | {n - len(ok)} | {structured}/{len(ok)} | {percentile(latencies, 0.5):.1f}"
            + f" | {percentile(latencies, 0.95):.1f} | {cost} | {regions} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--template", default="delivery-note")
    parser.add_argument("--cases", type=Path, default=REPO / "eval" / "cases")
    parser.add_argument("--limit", type=int, help="only the first N cases")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    try:
        nebius_api_key()
    except ConfigError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1

    template = templates[args.template]
    cases = load_cases(args.cases, args.template, args.limit)
    if not cases:
        print(f"✗ no cases in {args.cases / args.template}. Run eval/generate.py first.", file=sys.stderr)
        return 1

    pricing = fetch_pricing()
    out_dir = REPO / "eval" / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)
    print(f"Running {len(cases)} cases × {len(args.models)} models → {out_dir.relative_to(REPO)}")

    rows = []
    with ThreadPoolExecutor(args.concurrency) as pool, (out_dir / "results.jsonl").open("w") as f:
        futures = [pool.submit(run_one, m, c, template, pricing) for m in args.models for c in cases]
        for i, future in enumerate(as_completed(futures), 1):
            row = future.result()
            rows.append(row)
            f.write(json.dumps(row) + "\n")
            mark = "✗" if "error" in row else ("✓" if row["exact"] else "~")
            print(f"[{i}/{len(futures)}] {mark} {row['model']} {row['case']} ({row['latency_s']:.1f}s)", flush=True)

    fields = list(template.schema_["properties"])
    table = summarise(rows, args.models, fields, pricing)
    errors = sorted({r["error"] for r in rows if "error" in r})
    summary = (
        f"# Eval {out_dir.name}\n\n"
        f"Template `{args.template}`, {len(cases)} cases. Field acc. counts every expected field, "
        "so missed rows and errors count as wrong. `$ / 1000 pages` is from Token Factory list prices.\n\n"
        f"{table}\n"
    )
    if errors:
        summary += "\n## Errors\n\n" + "\n".join(f"- {e}" for e in errors) + "\n"
    (out_dir / "summary.md").write_text(summary)
    print("\n" + table)
    if errors:
        print("\nErrors:\n" + "\n".join(f"- {e}" for e in errors))
    return 0


if __name__ == "__main__":
    sys.exit(main())
