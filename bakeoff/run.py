"""Run each model on each question, one at a time, and append raw rows to a CSV."""

import argparse
import csv
import datetime
import time
from pathlib import Path

from bakeoff.questions import BY_KEY, QUESTIONS, SYSTEM_PROMPT
from core import client as groq_client
from core.agent import MAX_STEPS, run_agent
from core.citations import check_citations
from core.schemas import TOOLS
from core.tracer import Tracer

MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
PILOT_RUNS = 3
DEFAULT_RUNS = 10
ESTIMATED_TOKENS_PER_RUN = 8000
RESULTS_DIR = Path(__file__).parent.parent / "results"

FIELDS = [
    "model",
    "question",
    "run",
    "steps",
    "tools_used",
    "tool_calls",
    "tool_failures",
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "reasoning_tokens",
    "total_tokens",
    "seconds",
    "verified",
    "unverified",
    "citation_pass",
    "ended_early",
    "remaining_tokens",
    "error",
]

# Start of each message _run_tool in core/agent.py returns for a bad call.
FAILURE_PREFIXES = (
    "There is no tool called",
    "The tool arguments were not valid JSON",
    "The arguments did not match",
)
ENDED_EARLY_PREFIXES = ("Stopped after", "The model could not format")


def _is_failed_call(entry: dict) -> bool:
    result = entry["result"]
    if not isinstance(result, str):
        return False
    return result.startswith(FAILURE_PREFIXES) or " failed (" in result


def run_one(client, model: str, question_key: str, run: int) -> dict:
    """Run the agent once and return one CSV row. Errors go in the row."""
    question = BY_KEY[question_key]
    tracer = Tracer(verbose=False)
    row = dict.fromkeys(FIELDS, "")
    row.update(model=model, question=question_key, run=run)
    start = time.monotonic()
    try:
        result = run_agent(client, question.text, SYSTEM_PROMPT, TOOLS, MAX_STEPS, tracer, model)
    except Exception as error:
        row.update(error=f"{type(error).__name__}: {error}"[:300], ended_early=True)
        summary = tracer.summary()
        row["seconds"] = round(time.monotonic() - start, 2)
    else:
        summary = tracer.summary()
        report = check_citations(result.answer, tracer.tool_results)
        row.update(
            steps=result.steps,
            verified=len(report.verified),
            unverified=len(report.unverified),
            citation_pass=bool(report.verified) and not report.unverified,
            ended_early=result.answer.startswith(ENDED_EARLY_PREFIXES),
            seconds=summary["seconds"],
        )
    names = [entry["name"] for entry in tracer.tool_results]
    row.update(
        tools_used=" ".join(sorted(set(names))),
        tool_calls=len(names),
        tool_failures=sum(_is_failed_call(e) for e in tracer.tool_results),
        prompt_tokens=summary["prompt_tokens"],
        completion_tokens=summary["completion_tokens"],
        cached_tokens=summary["cached_tokens"],
        reasoning_tokens=summary["reasoning_tokens"],
        total_tokens=summary["tokens"],
        remaining_tokens=groq_client.remaining_tokens(),
    )
    return row


def default_out_path() -> Path:
    return RESULTS_DIR / f"bakeoff-{datetime.date.today().isoformat()}.csv"


def append_row(path: Path, row: dict) -> None:
    """Append one row, writing the header first if the file is new."""
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def run_all(client, models, questions, runs, out: Path) -> int:
    """Run every model on every question, appending each row as it finishes."""
    count = 0
    for model in models:
        for key in questions:
            for run in range(1, runs + 1):
                append_row(out, run_one(client, model, key, run))
                count += 1
    return count


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--questions", nargs="+", default=[q.key for q in QUESTIONS])
    parser.add_argument(
        "--runs", type=int, default=DEFAULT_RUNS, help="runs per model and question"
    )
    parser.add_argument("--pilot", action="store_true", help=f"{PILOT_RUNS} runs per cell")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    unknown = [key for key in args.questions if key not in BY_KEY]
    if unknown:
        raise SystemExit(f"Unknown question keys: {', '.join(unknown)}")
    runs = PILOT_RUNS if args.pilot else args.runs
    out = args.out or default_out_path()
    total = len(args.models) * len(args.questions) * runs
    print(f"{total} runs, about {total * ESTIMATED_TOKENS_PER_RUN:,} tokens, writing to {out}")
    if not args.yes and input("Start? [y/N] ").strip().lower() != "y":
        raise SystemExit("Cancelled.")
    count = run_all(groq_client.make_client(), args.models, args.questions, runs, out)
    print(f"Done. {count} rows in {out}")


if __name__ == "__main__":
    main()
