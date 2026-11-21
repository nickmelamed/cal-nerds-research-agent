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
        "seconds": 1.75,
    }


def test_quiet_tracer_prints_nothing(capsys):
    tracer = Tracer(verbose=False)
    tracer.tool_call(1, "x", {}, "r")
    tracer.answer("hi")
    assert capsys.readouterr().out == ""
    assert tracer.final_answer == "hi"
