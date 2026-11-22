"""Run each provider on each question and append rows to a CSV."""

import argparse
import csv
import datetime
import json
import time
from pathlib import Path

from bakeoff.questions import BY_KEY, QUESTIONS, SYSTEM_PROMPT
from core import client as model_client
from core.agent import MAX_STEPS, MODEL, run_agent
from core.citations import check_citations
from core.schemas import TOOLS
from core.tracer import Tracer

GROQ_BASELINE = "groq-free"
OPENROUTER_PREFIX = "openrouter:"
# "auto" lets OpenRouter pick the upstream provider.
DEFAULT_PROVIDERS = [f"{OPENROUTER_PREFIX}auto", GROQ_BASELINE]
PILOT_RUNS = 3
DEFAULT_RUNS = 10
ESTIMATED_TOKENS_PER_RUN = 8000
SEQUENCE_NOTE_CHARS = 80
RESULTS_DIR = Path(__file__).parent.parent / "results"

FIELDS = [
    "provider",
    "model",
    "question",
    "run",
    "steps",
    "tools_used",
    "tool_calls",
    "tool_failures",
    "tool_sequence",
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "reasoning_tokens",
    "total_tokens",
    "seconds",
    "verified",
    "unverified",
    "unverified_items",
    "citation_pass",
    "ended_early",
    "remaining_tokens",
    "error",
    "answer",
]

# Prefixes of the messages _run_tool returns for a bad call.
FAILURE_PREFIXES = (
    "There is no tool called",
    "The tool arguments were not valid JSON",
    "The arguments did not match",
)
ENDED_EARLY_PREFIXES = ("Stopped after", "The model could not format")


def tool_sequence(tool_results: list[dict]) -> str:
    """Return the calls of one run as JSON: step, name, args, and a result note.

    A string result is a message to the model, so its start is kept. Other
    results are marked ok.
    """
    calls = []
    for entry in tool_results:
        result = entry["result"]
        note = result[:SEQUENCE_NOTE_CHARS] if isinstance(result, str) else "ok"
        calls.append(
            {
                "step": entry["step"],
                "name": entry["name"],
                "args": entry.get("args", {}),
                "result": note,
            }
        )
    return json.dumps(calls)


def _is_failed_call(entry: dict) -> bool:
    result = entry["result"]
    if not isinstance(result, str):
        return False
    return result.startswith(FAILURE_PREFIXES) or " failed (" in result


def request_options(provider: str) -> dict | None:
    """Return the OpenRouter routing body that pins ``provider``, or None."""
    if not provider.startswith(OPENROUTER_PREFIX):
        return None
    slug = provider[len(OPENROUTER_PREFIX) :]
    if slug == "auto":
        return None
    return {"provider": {"order": [slug], "allow_fallbacks": False}}


def run_one(client, provider: str, question_key: str, run: int) -> dict:
    """Run the agent once and return a CSV row. Exceptions are recorded in it."""
    question = BY_KEY[question_key]
    tracer = Tracer(verbose=False)
    row = dict.fromkeys(FIELDS, "")
    row.update(provider=provider, model=MODEL, question=question_key, run=run)
    start = time.monotonic()
    try:
        result = run_agent(
            client,
            question.text,
            SYSTEM_PROMPT,
            TOOLS,
            MAX_STEPS,
            tracer,
            MODEL,
            request_options(provider),
        )
    except Exception as error:
        row.update(error=f"{type(error).__name__}: {error}"[:300], ended_early=True)
        summary = tracer.summary()
    else:
        summary = tracer.summary()
        report = check_citations(result.answer, tracer.tool_results)
        row.update(
            steps=result.steps,
            verified=len(report.verified),
            unverified=len(report.unverified),
            unverified_items=" | ".join(report.unverified),
            answer=result.answer,
            citation_pass=bool(report.verified) and not report.unverified,
            ended_early=result.answer.startswith(ENDED_EARLY_PREFIXES),
        )
    names = [entry["name"] for entry in tracer.tool_results]
    row.update(
        seconds=round(time.monotonic() - start, 2),
        tools_used=" ".join(sorted(set(names))),
        tool_calls=len(names),
        tool_failures=sum(_is_failed_call(e) for e in tracer.tool_results),
        tool_sequence=tool_sequence(tracer.tool_results),
        prompt_tokens=summary["prompt_tokens"],
        completion_tokens=summary["completion_tokens"],
        cached_tokens=summary["cached_tokens"],
        reasoning_tokens=summary["reasoning_tokens"],
        total_tokens=summary["tokens"],
        remaining_tokens=_remaining(provider),
    )
    return row


def default_out_path() -> Path:
    return RESULTS_DIR / f"bakeoff-{datetime.date.today().isoformat()}.csv"


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    if not is_new:
        with path.open(newline="") as handle:
            header = next(csv.reader(handle), [])
        if header != FIELDS:
            raise ValueError(f"{path} has different columns. Use a new --out file.")
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def _remaining(provider: str):
    # Only Groq sends a remaining-tokens header.
    return model_client.remaining_tokens() if provider == GROQ_BASELINE else ""


def client_for(provider: str):
    return model_client.make_client("groq" if provider == GROQ_BASELINE else "openrouter")


def run_all(clients, providers, questions, runs, out: Path) -> int:
    """Append each row as it finishes so a crash keeps earlier runs."""
    count = 0
    for provider in providers:
        for key in questions:
            for run in range(1, runs + 1):
                append_row(out, run_one(clients[provider], provider, key, run))
                count += 1
    return count


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--providers",
        nargs="+",
        default=DEFAULT_PROVIDERS,
        help="openrouter:<provider slug>, openrouter:auto, or groq-free",
    )
    parser.add_argument("--questions", nargs="+", default=[q.key for q in QUESTIONS])
    parser.add_argument(
        "--runs", type=int, default=DEFAULT_RUNS, help="runs per provider and question"
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
    total = len(args.providers) * len(args.questions) * runs
    print(f"{total} runs, about {total * ESTIMATED_TOKENS_PER_RUN:,} tokens, writing to {out}")
    if not args.yes and input("Start? [y/N] ").strip().lower() != "y":
        raise SystemExit("Cancelled.")
    clients = {name: client_for(name) for name in args.providers}
    count = run_all(clients, args.providers, args.questions, runs, out)
    print(f"Done. {count} rows in {out}")


if __name__ == "__main__":
    main()
