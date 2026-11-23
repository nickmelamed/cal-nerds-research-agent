import re
from types import SimpleNamespace

import pytest

import build
from tests.test_build import code_cells

SRC = build.SRC_DIR / "fullcode.py"
# Rule 8: these belong to the student tasks, so the starter must not have them.
FORBIDDEN = {
    "search_arxiv": ["try:", "except", "timeout", "raise_for_status"],
    "run_agent": ["max_steps", "tool_choice", "extra_body", "try:", "except", "usage", "monotonic"],
}


@pytest.fixture(scope="module")
def starter():
    return build.build_notebook(SRC)


def cell_with(starter, text):
    return next(s for s in code_cells(starter) if text in s)


def test_committed_starter_is_current():
    assert build.main(["--check", "fullcode"]) == 0


def test_only_openai_is_installed(starter):
    installs = [
        line
        for source in code_cells(starter)
        for line in source.splitlines()
        if re.match(r"\s*[!%]\s*pip", line)
    ]
    assert installs == ["!pip install -q openai"]


def test_no_core_references_or_keys(starter):
    for source in code_cells(starter):
        assert not build.LEFTOVER.search(source)
    text = "\n".join(c.source for c in starter.cells)
    assert not re.search(r"gsk_[A-Za-z0-9]{20,}|sk-or-[A-Za-z0-9-]{20,}", text)


def test_form_cells_are_collapsed(starter):
    for cell in starter.cells:
        if cell.cell_type == "code" and cell.source.startswith("# @title"):
            assert cell.metadata["cellView"] == "form"


def test_task_code_is_missing_from_the_starter(starter):
    for name, words in FORBIDDEN.items():
        source = cell_with(starter, f"def {name}(")
        for word in words:
            assert word not in source, f"{word} in the {name} cell"


def test_search_keeps_the_arxiv_delay(starter):
    source = cell_with(starter, "def search_arxiv(")
    assert "ARXIV_DELAY_S = 3" in source
    assert "time.sleep" in source


def test_no_forbidden_names_in_citation_form_cell_inputs(starter):
    cell = cell_with(starter, "def check_citations(")
    assert "def _normalize_id" in cell


# The test cells run the student's code, so check them against a reference
# solution and against the untouched starter.


def reply(content=None, calls=None):
    message = SimpleNamespace(content=content, tool_calls=calls)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(total_tokens=5)
    )


class ScriptedClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.chat = self
        self.completions = self
        self.with_raw_response = self

    def create(self, **kwargs):
        out = reply(*self.replies.pop(0))
        return SimpleNamespace(headers={}, parse=lambda: out)


def load_namespace(starter):
    """Run the cells that define tools and the loop, leaving out the network ones."""

    def fake_chat(client, **kwargs):
        return client.create(**kwargs).parse()

    namespace = {"client": None, "MODEL": "m", "chat": fake_chat}
    wanted = (
        "def search_arxiv(",
        "SEARCH_ARXIV_SCHEMA =",
        "def run_agent(",
        "class AlwaysSearches",
        "def check_citations",
    )
    for source in code_cells(starter):
        if any(w in source for w in wanted):
            exec(source.replace("# @title", "#"), namespace)
    return namespace


def test_baseline_loop_returns_an_answer(starter):
    ns = load_namespace(starter)
    call = SimpleNamespace(
        id="1", function=SimpleNamespace(name="search_arxiv", arguments='{"query": "x"}')
    )
    ns["TOOL_FUNCTIONS"]["search_arxiv"] = lambda **kw: [{"id": "2101.00001", "title": "T"}]
    ns["client"] = ScriptedClient([("", [call]), ("See 2101.00001.", None)])
    answer = ns["run_agent"]("q")
    assert answer == "See 2101.00001."
    assert ns["tool_results"][0]["name"] == "search_arxiv"
    report = ns["check_citations"](answer, ns["tool_results"])
    assert report.verified == ["2101.00001"] and not report.unverified


def run_test_cell(starter, ns, name, capsys):
    exec(cell_with(starter, f"def {name}("), ns)
    capsys.readouterr()
    ns[name]()
    return capsys.readouterr().out


def test_task_cells_report_not_yet_on_the_starter(starter, capsys):
    ns = load_namespace(starter)
    ns["requests"] = __import__("requests")
    out = run_test_cell(starter, ns, "test_step_cap", capsys)
    assert out.startswith("Not yet")


def test_step_cap_cell_passes_with_a_reference_solution(starter, capsys):
    ns = load_namespace(starter)
    ns["run_agent"] = lambda question, max_steps=6: _capped(ns, max_steps)
    out = run_test_cell(starter, ns, "test_step_cap", capsys)
    assert out.startswith("Passed"), out


def _capped(ns, max_steps):
    for _ in range(max_steps):
        ns["client"].create(messages=[])
    return f"Stopped after {max_steps} steps."


def test_error_cell_passes_with_a_reference_solution(starter, capsys):
    import requests

    ns = load_namespace(starter)
    ns["requests"] = requests
    ns["search_arxiv"] = lambda query, max_results=3: "No papers found, try broader terms."
    out = run_test_cell(starter, ns, "test_error_handling", capsys)
    assert out.startswith("Passed"), out
