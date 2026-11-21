import pytest

from core import tools

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>"""
ENTRY = """<entry><id>http://arxiv.org/abs/{pid}v2</id>
<title>  {title}
 </title><published>2021-07-15T00:00:00Z</published>
<summary>{summary}</summary>
<author><name>A One</name></author><author><name>B Two</name></author>
<author><name>C Three</name></author><author><name>D Four</name></author></entry>"""


class Resp:
    def __init__(self, status=200, text=""):
        self.status_code = status
        self.text = text


def atom(*papers):
    return ATOM.format(entries="".join(ENTRY.format(**p) for p in papers))


PAPER = {"pid": "2107.00001", "title": "Folding Proteins", "summary": "word " * 300}


@pytest.fixture
def calls(monkeypatch):
    class Log(list):
        queue: list = []

    log = Log()
    queue = log.queue = []

    def fake_get(url, params=None, headers=None, timeout=None):
        log.append((url, params))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(tools.requests, "get", fake_get)
    return log


def test_search_parses_and_hides_abstract(calls):
    calls.queue.append(Resp(text=atom(PAPER)))
    result = tools.search_arxiv("protein folding")
    assert result == [
        {
            "id": "2107.00001",
            "title": "Folding Proteins",
            "authors": ["A One", "B Two", "C Three", "et al."],
            "date": "2021-07-15",
            "link": "https://arxiv.org/abs/2107.00001",
        }
    ]


def test_search_zero_results_returns_message(calls):
    calls.queue.append(Resp(text=atom()))
    assert "No papers found" in tools.search_arxiv("zzzz")


def test_empty_query_makes_no_request(calls):
    assert "empty" in tools.search_arxiv("  ")
    assert calls == []


def test_search_is_cached(calls):
    calls.queue.append(Resp(text=atom(PAPER)))
    tools.search_arxiv("protein folding")
    tools.search_arxiv("Protein Folding")
    assert len(calls) == 1


def test_delay_between_consecutive_arxiv_calls(calls, clock):
    calls.queue += [Resp(text=atom(PAPER)), Resp(text=atom({**PAPER, "pid": "2107.00002"}))]
    tools.search_arxiv("one")
    start = clock.now
    tools.get_abstract("2107.00002")
    assert clock.now - start >= tools.ARXIV_DELAY_S


def test_retries_on_429_then_succeeds(calls, clock):
    calls.queue += [Resp(429), Resp(503), Resp(text=atom(PAPER))]
    assert isinstance(tools.search_arxiv("x"), list)
    assert len(calls) == 3


def test_gives_up_after_retries_with_message(calls):
    calls.queue += [Resp(429)] * tools.MAX_RETRIES
    assert "could not be reached" in tools.search_arxiv("x")


def test_network_error_returns_message(calls):
    calls.queue += [tools.requests.ConnectionError()] * tools.MAX_RETRIES
    assert "could not be reached" in tools.search_arxiv("x")


def test_abstract_truncated_and_served_from_cache(calls):
    calls.queue.append(Resp(text=atom(PAPER)))
    tools.search_arxiv("x")
    result = tools.get_abstract("arXiv:2107.00001v2")
    assert len(calls) == 1
    assert len(result["abstract"].split()) == tools.ABSTRACT_WORDS + 1
    assert result["title"] == "Folding Proteins"


def test_abstract_bad_id_message(calls):
    calls.queue.append(Resp(text=atom()))
    assert "No paper found" in tools.get_abstract("0000.00000")


def test_abstract_error_entry_is_not_a_paper(calls):
    err = {"pid": "api/errors#bad", "title": "Error", "summary": "bad id"}
    calls.queue.append(Resp(text=atom(err)))
    assert "No paper found" in tools.get_abstract("nonsense")


WIKI = '{"title":"Protein","type":"standard","extract":"One. Two. Three. Four.","content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Protein"}}}'


def test_wikipedia_truncates_to_sentences(calls):
    calls.queue.append(Resp(text=WIKI))
    result = tools.lookup_wikipedia("Protein")
    assert result["summary"] == "One. Two. Three."
    assert result["url"].endswith("/Protein")


def test_wikipedia_falls_back_to_search(calls):
    search = '{"query":{"search":[{"title":"Protein"}]}}'
    calls.queue += [Resp(404), Resp(text=search), Resp(text=WIKI)]
    assert tools.lookup_wikipedia("proteins")["title"] == "Protein"


def test_wikipedia_miss_returns_message(calls):
    calls.queue += [Resp(404), Resp(text='{"query":{"search":[]}}')]
    assert "No Wikipedia page" in tools.lookup_wikipedia("qqqq")


def test_wikipedia_network_error_returns_message(calls):
    calls.queue += [tools.requests.ConnectionError()] * 2
    assert "No Wikipedia page" in tools.lookup_wikipedia("x")


def test_offline_serves_stored_bodies(calls, monkeypatch):
    params = {"search_query": "all:x", "start": 0, "max_results": 3, "sortBy": "relevance"}
    key = tools._offline_key(tools.ARXIV_URL, params)
    monkeypatch.setattr(tools, "OFFLINE", True)
    monkeypatch.setattr(tools, "OFFLINE_DATA", {key: atom(PAPER)})
    assert isinstance(tools.search_arxiv("x"), list)
    assert calls == []
