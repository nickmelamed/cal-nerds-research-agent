import re
import shutil

import nbformat
import pytest

import build
from bakeoff.questions import SYSTEM_PROMPT
from tests.test_agent import FakeClient, reply, tool_call

DEMO = build.ROOT / "notebooks" / "demo.ipynb"
RECORDED_QUERY = "protein structure prediction deep learning"


@pytest.fixture(scope="module")
def demo():
    return build.build_notebook(build.SRC_DIR / "demo.py")


def code_cells(notebook):
    return [c.source for c in notebook.cells if c.cell_type == "code"]


def test_build_is_reproducible(demo):
    again = build.build_notebook(build.SRC_DIR / "demo.py")
    assert build.shape(again) == build.shape(demo)


def test_committed_notebook_is_current():
    assert build.main(["--check"]) == 0


def test_no_core_references_survive(demo):
    for source in code_cells(demo):
        assert not build.LEFTOVER.search(source)


def test_only_openai_is_installed(demo):
    installs = [
        line
        for source in code_cells(demo)
        for line in source.splitlines()
        if re.match(r"\s*[!%]\s*pip", line)
    ]
    assert installs == ["!pip install -q openai"]


def test_no_key_like_strings(demo):
    text = "\n".join(c.source for c in demo.cells)
    assert not re.search(r"gsk_[A-Za-z0-9]{20,}|sk-or-[A-Za-z0-9-]{20,}", text)


def test_form_cells_are_collapsed(demo):
    for cell in demo.cells:
        if cell.cell_type == "code" and cell.source.startswith("# @title"):
            assert cell.metadata["cellView"] == "form"


def test_demo_prompt_matches_bakeoff(demo):
    namespace = {}
    prompt_cell = next(s for s in code_cells(demo) if s.startswith("SYSTEM_PROMPT"))
    exec(prompt_cell, namespace)
    assert namespace["SYSTEM_PROMPT"] == SYSTEM_PROMPT


def test_missing_marker_module_fails(tmp_path, monkeypatch):
    source = tmp_path / "bad.py"
    source.write_text("# %%\n# @core nothing_here\n")
    with pytest.raises(build.BuildError):
        build.build_notebook(source)


def test_check_fails_when_notebook_is_stale(tmp_path, monkeypatch):
    out = tmp_path / "notebooks"
    out.mkdir()
    shutil.copy(DEMO, out / "demo.ipynb")
    stale = nbformat.read(out / "demo.ipynb", 4)
    stale.cells[1].source += "\nedited by hand"
    nbformat.write(stale, out / "demo.ipynb")
    monkeypatch.setattr(build, "OUT_DIR", out)
    assert build.main(["--check", "demo"]) == 1


def test_built_demo_runs_offline_with_a_fake_model(demo):
    namespace = {}
    for source in code_cells(demo):
        if source.startswith("!") or "make_client()" in source:
            continue
        if source.startswith("QUESTION"):
            break
        exec(source, namespace)
    namespace["OFFLINE"] = True
    found = namespace["search_arxiv"](RECORDED_QUERY)
    assert isinstance(found, list)
    paper_id = found[0]["id"]

    fake = FakeClient(
        [
            reply(calls=[tool_call("search_arxiv", {"query": RECORDED_QUERY})]),
            reply(f"One relevant paper is arXiv:{paper_id}."),
        ]
    )
    result = namespace["run_agent"](fake, "q", namespace["SYSTEM_PROMPT"], namespace["TOOLS"])
    report = namespace["check_citations"](result.answer, result.tracer.tool_results)
    assert report.verified == [paper_id]
    assert report.unverified == []
