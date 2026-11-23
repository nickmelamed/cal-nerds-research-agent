"""Compute the bake-off tables and the provider selection from a results CSV."""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from bakeoff.questions import BY_KEY

BASELINE = "groq-free"
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


def _mean_cost(rows: list[dict]) -> float | None:
    costs = [float(r["cost_usd"]) for r in rows if r.get("cost_usd")]
    return statistics.fmean(costs) if costs else None


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
        "cost_mean": _mean_cost(rows),
    }


def by_provider(rows: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["provider"]].append(row)
    return {model: stats(group) for model, group in groups.items()}


def eligible(per_provider: dict[str, dict]) -> dict[str, list[tuple[str, bool]]]:
    """Return each provider's selection conditions and whether each held."""
    best = max((s["citation_pass"] for n, s in per_provider.items() if n != BASELINE), default=0.0)
    return {
        name: [
            ("tool-call success >= 95%", s["tool_success"] >= MIN_TOOL_SUCCESS),
            ("mean tokens <= 8000", s["tokens_mean"] <= MAX_MEAN_TOKENS),
            ("error runs <= 10%", s["error_rate"] <= MAX_ERROR_RATE),
            (
                "citation pass within 10 points of best OpenRouter provider",
                best - s["citation_pass"] <= MAX_CITATION_GAP,
            ),
        ]
        for name, s in per_provider.items()
    }


def pick(per_provider: dict[str, dict]) -> list[str]:
    """Return eligible OpenRouter providers, best first: the pin, then the fallback."""
    checks = eligible(per_provider)
    names = [
        name for name, held in checks.items() if name != BASELINE and all(ok for _, ok in held)
    ]
    return sorted(
        names,
        key=lambda n: (-per_provider[n]["citation_pass"], per_provider[n]["seconds_mean"]),
    )


def _cost_cell(cost: float | None) -> str:
    return "-" if cost is None else f"{cost:.5f}"


def _line(label: str, s: dict) -> str:
    return (
        f"{label:<34}{s['runs']:>5}{s['tool_success']:>8.0%}{s['multi_tool']:>8.0%}"
        f"{s['citation_pass']:>8.0%}{s['tokens_mean']:>9.0f}{s['tokens_p90']:>9.0f}"
        f"{s['seconds_mean']:>8.1f}{s['error_rate']:>8.0%}{s['cached_tokens']:>9.0f}"
        f"{_cost_cell(s['cost_mean']):>10}"
    )


def variant_report(rows: list[dict]) -> str:
    """Return tool use and citation rates for each description set."""
    groups = defaultdict(list)
    for row in rows:
        groups[row.get("variant") or "baseline"].append(row)
    lines = [f"{'variant':<24}{'runs':>5}{'search':>8}{'wiki':>8}{'cites':>8}{'steps':>8}"]
    for variant, group in groups.items():
        count = len(group)
        search = _rate(sum("search_arxiv" in r["tools_used"].split() for r in group), count)
        wiki = _rate(sum("lookup_wikipedia" in r["tools_used"].split() for r in group), count)
        cites = _rate(sum(r["citation_pass"] == "True" for r in group), count)
        steps = statistics.fmean(_num(r["steps"]) for r in group)
        lines.append(f"{variant:<24}{count:>5}{search:>8.0%}{wiki:>8.0%}{cites:>8.0%}{steps:>8.1f}")
    return "\n".join(lines)


def report(rows: list[dict]) -> str:
    """Return the per-provider and per-question tables plus the selection."""
    header = (
        f"{'':<34}{'runs':>5}{'tools':>8}{'multi':>8}{'cites':>8}"
        f"{'tok avg':>9}{'tok p90':>9}{'sec':>8}{'errors':>8}{'cached':>9}{'$/run':>10}"
    )
    lines = [header]
    per_provider = by_provider(rows)
    for provider, s in per_provider.items():
        lines.append(_line(provider, s))
    lines.append("")
    cells = defaultdict(list)
    for row in rows:
        cells[(row["provider"], row["question"])].append(row)
    for (provider, question), group in cells.items():
        lines.append(_line(f"{provider} / {question}", stats(group)))
    lines.append("")
    for name, held in eligible(per_provider).items():
        failed = [label for label, ok in held if not ok]
        lines.append(
            f"{name}: " + ("eligible" if not failed else "not eligible, " + "; ".join(failed))
        )
    ranked = pick(per_provider)
    if ranked:
        lines.append(
            f"Pin {ranked[0]}."
            + (f" Fallback {ranked[1]}." if len(ranked) > 1 else " No fallback is eligible.")
        )
    else:
        lines.append("No OpenRouter provider meets the selection rule in bakeoff/PASS_BAR.md.")
    if len({r.get("variant") or "baseline" for r in rows}) > 1:
        lines += ["", variant_report(rows)]
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        raise SystemExit("usage: python -m bakeoff.summarize results/bakeoff-<date>.csv")
    path = Path(argv[0])
    if not path.is_file():
        raise SystemExit(f"No such file: {path}")
    print(report(load(path)))


if __name__ == "__main__":
    main(sys.argv[1:])
