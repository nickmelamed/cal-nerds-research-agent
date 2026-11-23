"""Check that every paper an answer cites was returned by a tool in this run."""

import re
from dataclasses import dataclass, field

from core.tools import _normalize_id

NEW_ID = r"(?<![\d.])\d{4}\.\d{4,5}(?:v\d+)?(?![\d])"
OLD_ID = r"(?<![\w-])[a-z]+(?:-[a-z]+)*(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
ID_PATTERN = re.compile(f"{NEW_ID}|{OLD_ID}")
# Models often write the hyphen of an id like quant-ph/0602157 as a Unicode
# hyphen or en dash, which would cut the id short at the first letter group.
UNICODE_DASHES = "\u2010\u2011\u2012\u2013\u2212\ufe63\uff0d"
LOOSE_OLD_ID = re.compile(
    rf"(?<![\w{UNICODE_DASHES}-])[a-z]+(?:[-{UNICODE_DASHES}][a-z]+)*"
    r"(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
)
DASH_CHARS = re.compile(f"[{UNICODE_DASHES}]")
QUOTED = re.compile(r"[\"“]([^\"”]+)[\"”]")
MIN_QUOTED_WORDS = 4
# Text with these characters is an example or a formula, not a paper title.
NOT_TITLE_CHARS = re.compile(r"[\u2190-\u21ff=<>+*|{}\[\]^_~\\]")


@dataclass
class CitationReport:
    verified: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    summary: str = ""


def _looks_like_title(phrase: str) -> bool:
    phrase = phrase.strip()
    return (
        bool(phrase)
        and phrase[0].isupper()
        and not phrase.endswith(".")
        and not NOT_TITLE_CHARS.search(phrase)
    )


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
    quoted phrase of four or more words counts as a reference to any
    retrieved paper whose title contains it. It is unverified when no
    retrieved title does, unless it reads as an example rather than a title:
    it starts in lowercase, ends in a period, or has arrows or math symbols.
    """
    answer = LOOSE_OLD_ID.sub(lambda m: DASH_CHARS.sub("-", m.group()), answer)
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
        if len(title.split()) < MIN_QUOTED_WORDS:
            continue
        needle = f" {title} "
        matched = [pid for pid, known in papers.items() if needle in f" {known} "]
        if matched:
            for pid in matched:
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    report.verified.append(pid)
        elif _looks_like_title(quoted) and not any(needle in f" {known} " for known in titles):
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
