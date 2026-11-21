"""Tools the research agent calls: arXiv search, arXiv abstracts, Wikipedia."""

import json
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlencode

import requests

ARXIV_URL = "https://export.arxiv.org/api/query"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "cal-nerds-research-agent/0.1 (educational workshop notebook)"

ARXIV_DELAY_S = 3
MAX_RESULTS = 3
ABSTRACT_WORDS = 150
WIKI_SENTENCES = 3
MAX_RETRIES = 3
BACKOFF_S = 2
TIMEOUT_S = 20

ATOM = {"a": "http://www.w3.org/2005/Atom"}

# When True, requests are answered from OFFLINE_DATA instead of the network.
# Keys are built by _offline_key and values are the raw response bodies.
OFFLINE = False
OFFLINE_DATA: dict[str, str] = {}

# Swapped out in tests so the delay logic runs without real waiting.
_clock = time.monotonic
_sleep = time.sleep

_last_arxiv_call: float | None = None
_search_cache: dict[tuple[str, int], list[dict] | str] = {}
_papers: dict[str, dict] = {}


def reset_cache() -> None:
    """Forget cached searches and papers, for the start of a new agent run."""
    _search_cache.clear()
    _papers.clear()


def _offline_key(url: str, params: dict | None) -> str:
    return url + ("?" + urlencode(sorted(params.items())) if params else "")


def _wait_for_arxiv() -> None:
    global _last_arxiv_call
    if _last_arxiv_call is not None:
        remaining = ARXIV_DELAY_S - (_clock() - _last_arxiv_call)
        if remaining > 0:
            _sleep(remaining)
    _last_arxiv_call = _clock()


def _arxiv_get(params: dict) -> str | None:
    """Return the Atom response text, or None if arXiv keeps failing."""
    if OFFLINE:
        return OFFLINE_DATA.get(_offline_key(ARXIV_URL, params))
    for attempt in range(MAX_RETRIES):
        _wait_for_arxiv()
        try:
            resp = requests.get(
                ARXIV_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S
            )
        except requests.RequestException:
            resp = None
        if resp is not None and resp.status_code == 200:
            return resp.text
        if resp is not None and resp.status_code not in (429, 503):
            return None
        _sleep(BACKOFF_S * 2**attempt)
    return None


def _wiki_get(url: str, params: dict | None = None) -> requests.Response | str | None:
    """Fetch a Wikipedia URL. Offline mode returns the stored body as text."""
    if OFFLINE:
        return OFFLINE_DATA.get(_offline_key(url, params))
    try:
        return requests.get(
            url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S
        )
    except requests.RequestException:
        return None


def _clean(text: str) -> str:
    return " ".join(text.split())


def _truncate_words(text: str, limit: int = ABSTRACT_WORDS) -> str:
    words = text.split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]) + " ..."


def _truncate_sentences(text: str, limit: int = WIKI_SENTENCES) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:limit])


def _normalize_id(paper_id: str) -> str:
    """Strip URL prefixes, the arXiv: prefix, and version suffixes."""
    pid = paper_id.strip()
    pid = re.sub(r"^(https?://)?(www\.)?arxiv\.org/(abs|pdf)/", "", pid)
    pid = re.sub(r"^arxiv:", "", pid, flags=re.IGNORECASE)
    pid = re.sub(r"\.pdf$", "", pid)
    return re.sub(r"v\d+$", "", pid)


def _parse_entries(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall("a:entry", ATOM):
        raw_id = entry.findtext("a:id", default="", namespaces=ATOM)
        title = _clean(entry.findtext("a:title", default="", namespaces=ATOM))
        # arXiv answers a bad id_list with a single error entry, not an HTTP error.
        if not title or title.lower() == "error" or "/api/errors" in raw_id:
            continue
        paper_id = _normalize_id(raw_id)
        authors = [
            _clean(a.findtext("a:name", default="", namespaces=ATOM))
            for a in entry.findall("a:author", ATOM)
        ]
        papers.append(
            {
                "id": paper_id,
                "title": title,
                "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
                "date": entry.findtext("a:published", default="", namespaces=ATOM)[:10],
                "link": f"https://arxiv.org/abs/{paper_id}",
                "abstract": _truncate_words(
                    entry.findtext("a:summary", default="", namespaces=ATOM)
                ),
            }
        )
    return papers


def search_arxiv(query: str, max_results: int = MAX_RESULTS) -> list[dict] | str:
    """Search arXiv and return id, title, authors, date, and link per paper.

    Returns a plain message instead of a list when nothing is found or arXiv
    cannot be reached. Results are cached for the run and their abstracts are
    kept so ``get_abstract`` does not need a second request.
    """
    query = (query or "").strip()
    if not query:
        return "The search query was empty. Give a few keywords describing the topic."
    max_results = max(1, min(int(max_results), MAX_RESULTS))
    key = (query.lower(), max_results)
    if key in _search_cache:
        return _search_cache[key]

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
    }
    text = _arxiv_get(params)
    if text is None:
        return (
            "arXiv could not be reached. Try again, or use lookup_wikipedia "
            "for background on the topic."
        )
    try:
        papers = _parse_entries(text)
    except ET.ParseError:
        return "arXiv returned a response that could not be read. Try a different query."
    if not papers:
        return f"No papers found for '{query}'. Try broader or different keywords."

    for paper in papers:
        _papers[paper["id"]] = paper
    result = [{k: v for k, v in p.items() if k != "abstract"} for p in papers]
    _search_cache[key] = result
    return result


def get_abstract(paper_id: str) -> dict | str:
    """Return the id, title, and abstract (about 150 words) for one arXiv paper."""
    pid = _normalize_id(paper_id or "")
    if not pid:
        return "No paper id was given. Use an id from search_arxiv, like 2101.00001."
    if pid in _papers:
        paper = _papers[pid]
        return {"id": pid, "title": paper["title"], "abstract": paper["abstract"]}

    text = _arxiv_get({"id_list": pid, "max_results": 1})
    if text is None:
        return "arXiv could not be reached. Try again in a moment."
    try:
        papers = _parse_entries(text)
    except ET.ParseError:
        return "arXiv returned a response that could not be read."
    if not papers:
        return f"No paper found with id '{pid}'. Check the id from search_arxiv."
    paper = papers[0]
    _papers[paper["id"]] = paper
    return {"id": paper["id"], "title": paper["title"], "abstract": paper["abstract"]}


def _wiki_summary(title: str) -> dict | None:
    resp = _wiki_get(WIKI_SUMMARY_URL + quote(title.replace(" ", "_"), safe=""))
    if resp is None:
        return None
    if isinstance(resp, str):
        data = _loads(resp)
    elif resp.status_code == 200:
        data = _loads(resp.text)
    else:
        return None
    if not data or data.get("type") == "disambiguation" or not data.get("extract"):
        return None
    return {
        "title": data.get("title", title),
        "summary": _truncate_sentences(data["extract"]),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }


def _loads(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def lookup_wikipedia(term: str) -> dict | str:
    """Return a short Wikipedia summary for a term.

    Tries the exact page title first, then falls back to a Wikipedia search
    and uses the top hit.
    """
    term = (term or "").strip()
    if not term:
        return "The term was empty. Give a word or short phrase to look up."

    found = _wiki_summary(term)
    if found:
        return found

    params = {
        "action": "query",
        "list": "search",
        "srsearch": term,
        "srlimit": 1,
        "format": "json",
    }
    resp = _wiki_get(WIKI_SEARCH_URL, params)
    body = resp if isinstance(resp, str) else (resp.text if resp is not None else None)
    data = _loads(body) if body else None
    hits = (data or {}).get("query", {}).get("search", [])
    if hits:
        found = _wiki_summary(hits[0]["title"])
        if found:
            return found
    return f"No Wikipedia page found for '{term}'. Try a more common name for the concept."
