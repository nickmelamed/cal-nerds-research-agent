"""Compute the bake-off tables and the gpt-oss-20b check from a results CSV."""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from bakeoff.questions import BY_KEY

BASE_MODEL = "openai/gpt-oss-120b"
CANDIDATE = "openai/gpt-oss-20b"
MIN_TOOL_SUCCESS = 0.95
MAX_CITATION_GAP = 0.10
MAX_MEAN_TOKENS = 8000
MAX_ERROR_RATE = 0.10


def load(path: Path) -> list[dict]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def _num(value) -> float:
    return float(value) if value not in ("", None) else 0.0


def _rate(hits: int, total: int) -> float:
    return hits / total if total else 0.0


def _p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))] if ordered else 0.0


def stats(rows: list[dict]) -> dict:
    """Return the measures from docs/SPEC.md for one group of runs."""
    # A run with no tool call counts as one failed call, as in PASS_BAR.md.
    silent = sum(_num(r["tool_calls"]) == 0 for r in rows)
    calls = sum(_num(r["tool_calls"]) for r in rows) + silent
    failed = sum(_num(r["tool_failures"]) for r in rows) + silent
    multi = [r for r in rows if BY_KEY[r["question"]].needs_multiple_tools]
    tokens = [_num(r["total_tokens"]) for r in rows]
    return {
        "runs": len(rows),
        "tool_success": _rate(calls - failed, calls) if calls else 0.0,
        "multi_tool": _rate(sum(len(r["tools_used"].split()) >= 2 for r in multi), len(multi)),
        "citation_pass": _rate(sum(r["citation_pass"] == "True" for r in rows), len(rows)),
        "tokens_mean": statistics.fmean(tokens) if tokens else 0.0,
        "tokens_p90": _p90(tokens),
        "seconds_mean": statistics.fmean(_num(r["seconds"]) for r in rows) if rows else 0.0,
        "error_rate": _rate(
            sum(bool(r["error"]) or r["ended_early"] == "True" for r in rows), len(rows)
        ),
        "cached_tokens": sum(_num(r["cached_tokens"]) for r in rows),
        "reasoning_tokens": sum(_num(r["reasoning_tokens"]) for r in rows),
    }


def by_model(rows: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["model"]].append(row)
    return {model: stats(group) for model, group in groups.items()}


def check_candidate(per_model: dict[str, dict]) -> list[tuple[str, bool]]:
    """Return each pass-bar condition for gpt-oss-20b and whether it held."""
    base, cand = per_model.get(BASE_MODEL), per_model.get(CANDIDATE)
    if not base or not cand:
        return []
    return [
        ("tool-call success >= 95%", cand["tool_success"] >= MIN_TOOL_SUCCESS),
        (
            "citation pass within 10 points of 120b",
            base["citation_pass"] - cand["citation_pass"] <= MAX_CITATION_GAP,
        ),
        ("mean tokens <= 8000", cand["tokens_mean"] <= MAX_MEAN_TOKENS),
        ("error runs <= 10%", cand["error_rate"] <= MAX_ERROR_RATE),
    ]


def _line(label: str, s: dict) -> str:
    return (
        f"{label:<34}{s['runs']:>5}{s['tool_success']:>8.0%}{s['multi_tool']:>8.0%}"
        f"{s['citation_pass']:>8.0%}{s['tokens_mean']:>9.0f}{s['tokens_p90']:>9.0f}"
        f"{s['seconds_mean']:>8.1f}{s['error_rate']:>8.0%}{s['cached_tokens']:>9.0f}"
    )


def report(rows: list[dict]) -> str:
    """Return the per-model and per-question tables plus the 20b check."""
    header = (
        f"{'':<34}{'runs':>5}{'tools':>8}{'multi':>8}{'cites':>8}"
        f"{'tok avg':>9}{'tok p90':>9}{'sec':>8}{'errors':>8}{'cached':>9}"
    )
    lines = [header]
    per_model = by_model(rows)
    for model, s in per_model.items():
        lines.append(_line(model, s))
    lines.append("")
    cells = defaultdict(list)
    for row in rows:
        cells[(row["model"], row["question"])].append(row)
    for (model, question), group in cells.items():
        lines.append(_line(f"{model.split('/')[-1]} / {question}", stats(group)))
    checks = check_candidate(per_model)
    lines.append("")
    if checks:
        for name, held in checks:
            lines.append(f"{'PASS' if held else 'FAIL'}  {CANDIDATE}: {name}")
        verdict = "meets" if all(held for _, held in checks) else "does not meet"
        lines.append(f"{CANDIDATE} {verdict} the pass bar in bakeoff/PASS_BAR.md.")
    else:
        lines.append(f"No rows for both {BASE_MODEL} and {CANDIDATE}, so no pass bar check.")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m bakeoff.summarize results/bakeoff-<date>.csv")
    print(report(load(Path(sys.argv[1]))))
