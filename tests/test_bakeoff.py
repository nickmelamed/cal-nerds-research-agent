import csv
from types import SimpleNamespace as NS

import pytest

from bakeoff import run, summarize
from core import agent
from tests.test_agent import FakeClient, tool_call

ARXIV_RESULT = [
    {"id": "2401.00001", "title": "Folding With Deep Nets", "authors": [], "date": "", "link": ""}
]


def usage_reply(content=None, calls=None):
    message = NS(content=content, tool_calls=calls)
    usage = NS(
        total_tokens=100,
        prompt_tokens=80,
        completion_tokens=20,
        prompt_tokens_details=NS(cached_tokens=40),
        completion_tokens_details=NS(reasoning_tokens=5),
    )
    return NS(choices=[NS(message=message)], usage=usage)


@pytest.fixture
def fake_tools(monkeypatch):
    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "search_arxiv", lambda **kw: ARXIV_RESULT)
    monkeypatch.setitem(
        agent.TOOL_FUNCTIONS,
        "lookup_wikipedia",
        lambda term: {"title": "Protein", "summary": "s", "url": "u"},
    )


def test_run_one_records_a_passing_run(fake_tools):
    client = FakeClient(
        [
            usage_reply(calls=[tool_call("search_arxiv", {"query": "x"})]),
            usage_reply("See 2401.00001 for details."),
        ]
    )
    row = run.run_one(client, "m", "demo", 1)
    assert row["citation_pass"] is True
    assert row["tools_used"] == "search_arxiv"
    assert (row["tool_calls"], row["tool_failures"]) == (1, 0)
    assert (row["prompt_tokens"], row["cached_tokens"], row["total_tokens"]) == (160, 80, 200)
    assert row["error"] == "" and row["ended_early"] is False
    assert set(row) == set(run.FIELDS)


def test_run_one_counts_unverified_citation_and_bad_tool_call(fake_tools):
    client = FakeClient(
        [
            usage_reply(calls=[tool_call("no_such_tool", {})]),
            usage_reply("See 9999.99999."),
        ]
    )
    row = run.run_one(client, "m", "demo", 1)
    assert row["tool_failures"] == 1
    assert (row["verified"], row["unverified"], row["citation_pass"]) == (0, 1, False)


def test_run_one_records_an_exception_instead_of_raising(fake_tools):
    row = run.run_one(FakeClient([RuntimeError("boom")]), "m", "demo", 2)
    assert "boom" in row["error"]
    assert row["ended_early"] is True


def test_step_cap_counts_as_ended_early(fake_tools, monkeypatch):
    monkeypatch.setattr(run, "MAX_STEPS", 1)
    client = FakeClient([usage_reply(calls=[tool_call("search_arxiv", {"query": "x"})])])
    row = run.run_one(client, "m", "demo", 1)
    assert row["ended_early"] is True


@pytest.mark.parametrize(
    "name,args",
    [("nope", "{}"), ("search_arxiv", "not json"), ("search_arxiv", '{"bad": 1}')],
)
def test_failure_prefixes_match_what_the_agent_returns(name, args):
    result = agent._run_tool(name, args)
    assert run._is_failed_call({"result": result})


def test_append_row_writes_header_once(tmp_path):
    out = tmp_path / "nested" / "r.csv"
    row = dict.fromkeys(run.FIELDS, "x")
    run.append_row(out, row)
    run.append_row(out, row)
    rows = list(csv.DictReader(out.open()))
    assert len(rows) == 2 and rows[0]["model"] == "x"


def test_run_all_loops_providers_questions_and_runs(tmp_path, monkeypatch):
    calls = []

    def fake_run_one(client, provider, key, number):
        calls.append((client, provider, key, number))
        return dict.fromkeys(run.FIELDS, "")

    monkeypatch.setattr(run, "run_one", fake_run_one)
    out = tmp_path / "r.csv"
    clients = {"a": "ca", "b": "cb"}
    assert run.run_all(clients, ["a", "b"], ["demo", "guided_cs"], 2, out) == 8
    assert calls[0] == ("ca", "a", "demo", 1) and calls[-1] == ("cb", "b", "guided_cs", 2)
    assert len(list(csv.DictReader(out.open()))) == 8


def test_request_options_pin_an_openrouter_provider():
    assert run.request_options("openrouter:auto") is None
    assert run.request_options("groq-free") is None
    assert run.request_options("openrouter:Fireworks") == {
        "provider": {"order": ["Fireworks"], "allow_fallbacks": False}
    }


def test_run_one_sends_routing_body_and_records_provider(fake_tools):
    seen = {}

    class Spy(FakeClient):
        def create(self, **kwargs):
            seen.update(kwargs)
            return super().create(**kwargs)

    row = run.run_one(Spy([usage_reply("hi")]), "openrouter:Fireworks", "demo", 1)
    assert seen["extra_body"]["provider"]["order"] == ["Fireworks"]
    assert row["provider"] == "openrouter:Fireworks"
    assert row["model"] == run.MODEL


def test_main_rejects_unknown_question():
    with pytest.raises(SystemExit):
        run.main(["--questions", "nope", "--yes"])


def test_main_cancels_without_confirmation(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(run, "client_for", lambda name: pytest.fail("made a client"))
    with pytest.raises(SystemExit):
        run.main(["--pilot"])


def make_rows(provider, n, *, cites, tokens, tool_calls=2, failures=0, error="", seconds=2):
    rows = []
    for i in range(n):
        row = dict.fromkeys(run.FIELDS, "")
        row.update(
            provider=provider,
            model=run.MODEL,
            question="demo",
            run=i,
            tools_used="get_abstract search_arxiv",
            tool_calls=tool_calls,
            tool_failures=failures,
            total_tokens=tokens,
            seconds=seconds,
            citation_pass=str(i < cites),
            ended_early="False",
            error=error if i == 0 else "",
            cached_tokens=10,
        )
        rows.append(row)
    return rows


def test_stats_values():
    s = summarize.stats(make_rows("p", 10, cites=8, tokens=6000, failures=1))
    assert s["tool_success"] == 0.5
    assert s["multi_tool"] == 1.0
    assert s["citation_pass"] == 0.8
    assert s["tokens_mean"] == 6000
    assert s["cached_tokens"] == 100


def test_run_without_tool_calls_counts_as_tool_failure():
    rows = make_rows("p", 1, cites=1, tokens=100, tool_calls=0)
    rows += make_rows("p", 1, cites=1, tokens=100, tool_calls=1)
    assert summarize.stats(rows)["tool_success"] == 0.5


def test_failed_tool_message_is_counted():
    assert run._is_failed_call({"result": "search_arxiv failed (KeyError). Try again."})
    assert not run._is_failed_call({"result": "No papers found."})


def test_seconds_is_recorded_on_success_and_error(fake_tools):
    ok = run.run_one(FakeClient([usage_reply("hi")]), "groq-free", "demo", 1)
    bad = run.run_one(FakeClient([RuntimeError("boom")]), "groq-free", "demo", 2)
    assert ok["seconds"] != "" and bad["seconds"] != ""


def test_pick_ranks_eligible_openrouter_providers_and_skips_baseline():
    rows = make_rows("openrouter:A", 10, cites=9, tokens=6000)
    rows += make_rows("openrouter:B", 10, cites=8, tokens=6000)
    rows += make_rows("groq-free", 10, cites=10, tokens=6000)
    text = summarize.report(rows)
    assert summarize.pick(summarize.by_provider(rows)) == ["openrouter:A", "openrouter:B"]
    assert "Pin openrouter:A. Fallback openrouter:B." in text


def test_latency_breaks_citation_ties():
    rows = make_rows("openrouter:slow", 10, cites=9, tokens=6000, seconds=9)
    rows += make_rows("openrouter:fast", 10, cites=9, tokens=6000, seconds=3)
    assert summarize.pick(summarize.by_provider(rows))[0] == "openrouter:fast"


def test_ineligible_provider_is_named_with_the_reason():
    rows = make_rows("openrouter:A", 10, cites=10, tokens=6000)
    rows += make_rows("openrouter:B", 10, cites=5, tokens=9000, error="x")
    held = dict(summarize.eligible(summarize.by_provider(rows)))["openrouter:B"]
    failed = [label for label, ok in held if not ok]
    assert "mean tokens <= 8000" in failed
    assert "citation pass within 10 points of best OpenRouter provider" in failed
    text = summarize.report(rows)
    assert "openrouter:B: not eligible" in text and "No fallback is eligible" in text


def test_report_says_when_nothing_qualifies():
    rows = make_rows("openrouter:A", 10, cites=0, tokens=9000)
    assert "No OpenRouter provider meets the selection rule" in summarize.report(rows)


def test_load_roundtrip(tmp_path):
    out = tmp_path / "r.csv"
    for row in make_rows("p", 2, cites=2, tokens=100):
        run.append_row(out, row)
    assert len(summarize.load(out)) == 2
