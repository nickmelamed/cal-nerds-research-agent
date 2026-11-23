from core.tracer import DISPLAY_CHARS, Tracer


def test_display_is_truncated_but_raw_result_is_kept(capsys):
    tracer = Tracer()
    raw = {"abstract": "word " * 200}
    tracer.tool_call(1, "get_abstract", {"paper_id": "1"}, raw)
    out = capsys.readouterr().out
    assert "Step 1: get_abstract" in out
    assert out.rstrip().endswith("...")
    assert len(out.splitlines()[1]) < DISPLAY_CHARS + 20
    assert tracer.tool_results[0]["result"] is raw


def test_summary_totals_tokens_and_latency():
    tracer = Tracer(verbose=False)
    tracer.model_call(1, 100, 0.5)
    tracer.model_call(2, 250, 1.25)
    assert tracer.summary() == {
        "model_calls": 2,
        "tool_calls": 0,
        "tokens": 350,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
        "cost": 0,
        "served_by": "",
        "seconds": 1.75,
    }


def test_quiet_tracer_prints_nothing(capsys):
    tracer = Tracer(verbose=False)
    tracer.tool_call(1, "x", {}, "r")
    tracer.answer("hi")
    assert capsys.readouterr().out == ""
    assert tracer.final_answer == "hi"


def test_summary_splits_token_kinds():
    tracer = Tracer(verbose=False)
    tracer.model_call(1, 100, 0.5, prompt=80, completion=20, cached=50, reasoning=5)
    tracer.model_call(2, 200, 0.5, prompt=150, completion=50, cached=100, reasoning=10)
    summary = tracer.summary()
    assert summary["prompt_tokens"] == 230
    assert summary["completion_tokens"] == 70
    assert summary["cached_tokens"] == 150
    assert summary["reasoning_tokens"] == 15


def test_tool_results_keep_the_arguments():
    tracer = Tracer(verbose=False)
    tracer.tool_call(2, "search_arxiv", {"query": "x"}, [])
    assert tracer.tool_results[0]["args"] == {"query": "x"}


def test_summary_lists_the_providers_that_served_the_calls():
    tracer = Tracer(verbose=False)
    tracer.model_call(1, 10, 0.1, served_by="Baseten")
    tracer.model_call(2, 10, 0.1, served_by="Baseten")
    tracer.model_call(3, 10, 0.1, served_by="Crusoe")
    tracer.model_call(4, 10, 0.1)
    assert tracer.summary()["served_by"] == "Baseten Crusoe"


def test_summary_totals_cost():
    tracer = Tracer(verbose=False)
    tracer.model_call(1, 10, 0.1, cost=0.0004)
    tracer.model_call(2, 10, 0.1, cost=0.0006)
    tracer.model_call(3, 10, 0.1)
    assert tracer.summary()["cost"] == 0.001
