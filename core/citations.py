"""Check that every paper an answer cites was returned by a tool in this run."""

import re
from dataclasses import dataclass, field

from core.tools import _normalize_id

NEW_ID = r"(?<![\d.])\d{4}\.\d{4,5}(?:v\d+)?(?![\d])"
OLD_ID = r"(?<![\w-])[a-z]+(?:-[a-z]+)*(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
ID_PATTERN = re.compile(f"{NEW_ID}|{OLD_ID}")
QUOTED = re.compile(r"[\"“]([^\"”]+)[\"”]")
MIN_QUOTED_WORDS = 4


@dataclass
class CitationReport:
    verified: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    summary: str = ""


def _norm_title(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _retrieved(tool_results: list[dict]) -> tuple[dict[str, str], set[str]]:
    # Wikipedia titles go in the title set only, so a quoted one is not flagged.
    papers: dict[str, str] = {}
    titles: set[str] = set()
    for entry in tool_results:
        result = entry["result"]
        items = result if isinstance(result, list) else [result]
        for item in items:
            if not isinstance(item, dict) or "title" not in item:
                continue
            title = _norm_title(item["title"])
            titles.add(title)
            if entry["name"] != "lookup_wikipedia" and "id" in item:
                papers[_normalize_id(item["id"])] = title
    return papers, titles


def check_citations(answer: str, tool_results: list[dict]) -> CitationReport:
    """Count a citation as verified only if a tool returned it in this run.

    Match papers by arXiv id, or by title when the answer gives no id. A
    quoted phrase of four or more words that matches no retrieved title is
    unverified.
    """
    papers, titles = _retrieved(tool_results)
    report = CitationReport()
    seen_ids: set[str] = set()

    for match in ID_PATTERN.findall(answer):
        pid = _normalize_id(match)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        (report.verified if pid in papers else report.unverified).append(pid)

    padded = f" {_norm_title(answer)} "
    for pid, title in papers.items():
        if pid not in seen_ids and f" {title} " in padded:
            seen_ids.add(pid)
            report.verified.append(pid)

    for quoted in QUOTED.findall(answer):
        title = _norm_title(quoted)
        if len(title.split()) < MIN_QUOTED_WORDS or title in titles:
            continue
        if not any(title in known for known in titles):
            report.unverified.append(quoted.strip())

    total = len(report.verified) + len(report.unverified)
    if total == 0:
        report.summary = "The answer cites no papers."
    else:
        report.summary = (
            f"{len(report.verified)} of {total} cited papers "
            "were retrieved by the agent in this run."
        )
    return report
