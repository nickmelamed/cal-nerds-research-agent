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


def test_tool_that_raises_goes_back_to_model(monkeypatch):
    def broken(query):
        raise RuntimeError("network down")

    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "search_arxiv", broken)
    calls = [tool_call("search_arxiv", {"query": "x"})]
    fake, result = run([reply(calls=calls), reply("done")])
    assert "failed (RuntimeError)" in fake.requests[1][-1]["content"]
    assert result.answer == "done"


def test_tool_use_failed_retry_is_noted_in_the_trace(capsys):
    run([Exception("tool_use_failed"), reply("ok")])
    assert "malformed tool call" in capsys.readouterr().out


def test_long_tool_result_is_marked_truncated(monkeypatch):
    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "lookup_wikipedia", lambda term: "x" * 5000)
    calls = [tool_call("lookup_wikipedia", {"term": "a"})]
    fake, result = run([reply(calls=calls), reply("done")])
    content = fake.requests[1][-1]["content"]
    assert content.endswith(agent.TRUNCATION_MARK)
    assert len(content) == agent.RESULT_CHARS + len(agent.TRUNCATION_MARK)
    assert result.tracer.tool_results[0]["result"] == "x" * 5000


def test_usage_details_are_recorded():
    usage = NS(
        total_tokens=100,
        prompt_tokens=80,
        completion_tokens=20,
        prompt_tokens_details=NS(cached_tokens=60),
        completion_tokens_details=NS(reasoning_tokens=7),
    )
    response = NS(choices=[NS(message=NS(content="hi", tool_calls=None))], usage=usage)
    _, result = run([response])
    summary = result.tracer.summary()
    assert (summary["prompt_tokens"], summary["completion_tokens"]) == (80, 20)
    assert (summary["cached_tokens"], summary["reasoning_tokens"]) == (60, 7)


def test_missing_usage_details_count_as_zero():
    _, result = run([reply("hi")])
    summary = result.tracer.summary()
    assert summary["tokens"] == 100
    assert summary["cached_tokens"] == 0 and summary["reasoning_tokens"] == 0


def test_extra_body_reaches_the_client():
    seen = {}

    class Spy(FakeClient):
        def create(self, **kwargs):
            seen.update(kwargs)
            return super().create(**kwargs)

    body = {"provider": {"order": ["X"]}}
    agent.run_agent(Spy([reply("hi")]), "q", "sys", TOOLS, extra_body=body)
    assert seen["extra_body"] == body


class Spy(FakeClient):
    def __init__(self, outcomes):
        super().__init__(outcomes)
        self.kwargs = []

    def create(self, **kwargs):
        self.kwargs.append({k: v for k, v in kwargs.items() if k != "messages"})
        return super().create(**kwargs)


def test_last_step_turns_tools_off_and_asks_for_an_answer(monkeypatch):
    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "search_arxiv", lambda query: [])
    calls = [tool_call("search_arxiv", {"query": "x"})]
    spy = Spy([reply(calls=calls), reply("final answer")])
    result = agent.run_agent(spy, "q", "sys", TOOLS, max_steps=2)
    assert result.answer == "final answer"
    assert "tool_choice" not in spy.kwargs[0]
    assert spy.kwargs[1]["tool_choice"] == "none"
    assert "answer now" in spy.requests[1][-1]["content"].lower()


def test_earlier_steps_keep_tools_on():
    spy = Spy([reply("done")])
    agent.run_agent(spy, "q", "sys", TOOLS, max_steps=3)
    assert "tool_choice" not in spy.kwargs[0]


def test_single_step_runs_still_get_tools():
    spy = Spy([reply("done")])
    agent.run_agent(spy, "q", "sys", TOOLS, max_steps=1)
    assert "tool_choice" not in spy.kwargs[0]


def test_served_by_is_read_from_the_response_body():
    plain = reply("hi")
    plain.provider = "Baseten"
    _, result = run([plain])
    assert result.tracer.summary()["served_by"] == "Baseten"

    extra = reply("hi")
    extra.model_extra = {"provider": "Crusoe"}
    _, result = run([extra])
    assert result.tracer.summary()["served_by"] == "Crusoe"

    _, result = run([reply("hi")])
    assert result.tracer.summary()["served_by"] == ""


def test_cost_is_read_from_usage_when_reported():
    response = reply("hi")
    response.usage.cost = 0.0123
    _, result = run([response])
    assert result.tracer.summary()["cost"] == 0.0123

    extra = reply("hi")
    extra.usage.model_extra = {"cost": 0.5}
    _, result = run([extra])
    assert result.tracer.summary()["cost"] == 0.5

    _, result = run([reply("hi")])
    assert result.tracer.summary()["cost"] == 0
