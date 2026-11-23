import ast
import io
import json
import re
from contextlib import redirect_stdout

import pytest

import build
from bakeoff.questions import SYSTEM_PROMPT
from core import schemas
from tests.test_agent import FakeClient, reply, tool_call
from tests.test_build import RECORDED_QUERY, code_cells

SRC = build.SRC_DIR / "guided.py"
STUDENT_NAMES = {
    "SYSTEM_PROMPT",
    "QUESTION",
    "PLAIN_PROMPT",
    "TECHNICAL_PROMPT",
    "SEARCH_ARXIV_DESCRIPTION",
}


@pytest.fixture(scope="module")
def guided():
    return build.build_notebook(SRC)


def run_cells(notebook, fake):
    """Run every code cell offline with the fake model and return the namespace."""
    namespace = {}
    for source in code_cells(notebook):
        if source.startswith("!"):
            continue
        if "make_client()" in source:
            source = source.replace("OFFLINE = False", "OFFLINE = True")
            namespace["make_client"] = lambda: fake
        exec(source, namespace)
    return namespace


def test_committed_guided_notebook_is_current():
    assert build.main(["--check", "guided"]) == 0


def test_only_openai_is_installed(guided):
    installs = [
        line
        for source in code_cells(guided)
        for line in source.splitlines()
        if re.match(r"\s*[!%]\s*pip", line)
    ]
    assert installs == ["!pip install -q openai"]


def test_no_core_references_or_keys(guided):
    for source in code_cells(guided):
        assert not build.LEFTOVER.search(source)
    text = "\n".join(c.source for c in guided.cells)
    assert not re.search(r"gsk_[A-Za-z0-9]{20,}|sk-or-[A-Za-z0-9-]{20,}", text)


def test_form_cells_are_collapsed(guided):
    for cell in guided.cells:
        if cell.cell_type == "code" and cell.source.startswith("# @title"):
            assert cell.metadata["cellView"] == "form"


def test_student_cells_hold_only_assignments(guided):
    found = set()
    for source in code_cells(guided):
        if source.startswith("!"):
            continue
        tree = ast.parse(source)
        names = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        if names & STUDENT_NAMES:
            found |= names & STUDENT_NAMES
            assert all(isinstance(node, ast.Assign) for node in tree.body)
    assert found == STUDENT_NAMES


def test_default_descriptions_match_core(guided):
    cell = next(s for s in code_cells(guided) if s.startswith("SEARCH_ARXIV_DESCRIPTION"))
    namespace = {}
    exec(cell, namespace)
    assert namespace["SEARCH_ARXIV_DESCRIPTION"] == schemas.SEARCH_ARXIV_DESCRIPTION
    assert namespace["GET_ABSTRACT_DESCRIPTION"] == schemas.GET_ABSTRACT_DESCRIPTION
    assert namespace["LOOKUP_WIKIPEDIA_DESCRIPTION"] == schemas.LOOKUP_WIKIPEDIA_DESCRIPTION


def test_system_prompt_matches_bakeoff(guided):
    cell = next(s for s in code_cells(guided) if s.startswith("SYSTEM_PROMPT"))
    namespace = {}
    exec(cell, namespace)
    assert namespace["SYSTEM_PROMPT"] == SYSTEM_PROMPT


def test_guided_runs_offline_with_a_fake_model(guided):
    fake = FakeClient(
        [
            reply("ready"),
            reply(calls=[tool_call("search_arxiv", {"query": RECORDED_QUERY})]),
            reply("Exercise 0 answer with no citations."),
            reply("Plain answer."),
            reply("Technical answer."),
            reply("Exercise 2 answer."),
            reply("Exercise 3 answer."),
        ]
    )
    out = io.StringIO()
    with redirect_stdout(out):
        namespace = run_cells(guided, fake)
    assert namespace["result"].answer == "Exercise 3 answer."
    assert "Technical answer." in out.getvalue()
    assert "Tools used: none" in out.getvalue()
    assert json.loads(json.dumps(namespace["TOOLS"])) == namespace["TOOLS"]


def test_compare_runs_the_prompts_in_order(guided):
    fake = FakeClient([reply("ready"), reply("First."), reply("Second.")])
    namespace = {"TOOLS": schemas.TOOLS}
    for source in code_cells(guided):
        if source.startswith("!"):
            continue
        if source.startswith("OFFLINE = False"):
            namespace["make_client"] = lambda: fake
        exec(source, namespace)
        if source.startswith("# @title compare"):
            break
    with redirect_stdout(io.StringIO()):
        namespace["compare"]("A question?", "prompt one", "prompt two")
    systems = [r[0]["content"] for r in fake.requests[1:]]
    assert systems == ["prompt one", "prompt two"]
