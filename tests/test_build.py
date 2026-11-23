import json
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
    data = json.loads(build.FIXTURES.read_text())
    paper_id = "2401.00001"
    fake = FakeClient(
        [
            reply("ready"),
            reply(calls=[tool_call("search_arxiv", {"query": RECORDED_QUERY})]),
            reply("One relevant paper is arXiv:" + paper_id + "."),
            reply("A second answer with no citations."),
        ]
    )
    namespace = {}
    for source in code_cells(demo):
        if source.startswith("!"):
            continue
        if "make_client()" in source:
            # Run the real flag cell but with OFFLINE on and the fake model.
            source = source.replace("OFFLINE = False", "OFFLINE = True")
            namespace["make_client"] = lambda: fake
        exec(source, namespace)
    assert namespace["OFFLINE_DATA"] == data
    assert namespace["result"].answer == "A second answer with no citations."
    assert namespace["report"].unverified == []
    first = [c for c in fake.requests if any(m.get("role") == "tool" for m in c)]
    assert first, "the first question should have called a tool"


def test_each_tool_gets_its_own_cell(demo):
    cells = code_cells(demo)
    for name in ("search_arxiv", "get_abstract", "lookup_wikipedia"):
        owners = [c for c in cells if re.search(rf"^def {name}\(", c, re.MULTILINE)]
        assert len(owners) == 1
        assert len(re.findall(r"^def ", owners[0], re.MULTILINE)) == 1


def test_unknown_tool_part_fails():
    with pytest.raises(build.BuildError):
        build.core_source("tools", "no_such_tool")
