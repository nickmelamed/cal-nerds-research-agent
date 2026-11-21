import json
from types import SimpleNamespace as NS

from core import agent, tools
from core.schemas import TOOLS


def tool_call(name, args, call_id="c1"):
    raw = args if isinstance(args, str) else json.dumps(args)
    return NS(id=call_id, function=NS(name=name, arguments=raw))


def reply(content=None, calls=None, tokens=100):
    message = NS(content=content, tool_calls=calls)
    return NS(choices=[NS(message=message)], usage=NS(total_tokens=tokens))


class Raw:
    def __init__(self, parsed):
        self.headers = {}
        self._parsed = parsed

    def parse(self):
        return self._parsed


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []
        self.chat = self
        self.completions = self
        self.with_raw_response = self

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs["messages"])))
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return Raw(out)


def run(outcomes, **kwargs):
    fake = FakeClient(outcomes)
    result = agent.run_agent(fake, "q", "sys", TOOLS, **kwargs)
    return fake, result


def test_tool_then_answer(monkeypatch):
    monkeypatch.setitem(
        agent.TOOL_FUNCTIONS, "search_arxiv", lambda query: {"id": "1", "title": "T"}
    )
    fake, result = run([reply(calls=[tool_call("search_arxiv", {"query": "x"})]), reply("done")])
    assert result.answer == "done"
    assert result.steps == 2
    assert result.tracer.tool_results[0]["result"] == {"id": "1", "title": "T"}
    assert result.tracer.summary()["tokens"] == 200
    tool_msg = fake.requests[1][-1]
    assert tool_msg["role"] == "tool" and "title" in tool_msg["content"]


def test_several_tool_calls_in_one_turn(monkeypatch):
    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "lookup_wikipedia", lambda term: "ok")
    calls = [
        tool_call("lookup_wikipedia", {"term": "a"}, "c1"),
        tool_call("lookup_wikipedia", {"term": "b"}, "c2"),
    ]
    fake, result = run([reply(calls=calls), reply("done")])
    ids = [m.get("tool_call_id") for m in fake.requests[1] if m["role"] == "tool"]
    assert ids == ["c1", "c2"]


def test_unknown_tool_name_goes_back_to_model():
    fake, result = run([reply(calls=[tool_call("nope", {})]), reply("done")])
    assert "no tool called nope" in fake.requests[1][-1]["content"]


def test_bad_json_arguments_go_back_to_model():
    calls = [tool_call("search_arxiv", "{not json")]
    fake, result = run([reply(calls=calls), reply("done")])
    assert "not valid JSON" in fake.requests[1][-1]["content"]


def test_wrong_argument_names_go_back_to_model():
    calls = [tool_call("search_arxiv", {"topic": "x"})]
    fake, result = run([reply(calls=calls), reply("done")])
    assert "did not match" in fake.requests[1][-1]["content"]


def test_tool_use_failed_is_retried_once():
    err = Exception("400 tool_use_failed: bad call")
    fake, result = run([err, reply("recovered")])
    assert result.answer == "recovered"
    assert "malformed" in fake.requests[1][-1]["content"]


def test_second_tool_use_failed_ends_the_run():
    err = Exception("tool_use_failed")
    fake, result = run([err, err])
    assert "could not format" in result.answer


def test_other_errors_are_raised():
    try:
        run([Exception("boom")])
    except Exception as error:
        assert str(error) == "boom"
    else:
        raise AssertionError("expected the error to propagate")


def test_step_cap_returns_a_message():
    calls = [tool_call("nope", {})]
    fake, result = run([reply(calls=calls)] * 2, max_steps=2)
    assert "Stopped after 2 steps" in result.answer
    assert len(fake.requests) == 2


def test_cache_is_cleared_at_the_start(monkeypatch):
    tools._papers["x"] = {"title": "t", "abstract": "a"}
    run([reply("done")])
    assert tools._papers == {}
