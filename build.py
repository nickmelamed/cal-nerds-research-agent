"""Assemble notebooks/ from notebooks_src/ and core/.

A source cell that holds the line ``# @core <module>`` gets that module's code
in its place. A line ``# @offline-data`` becomes the recorded API responses.
Run ``python build.py`` to write the notebooks and ``python build.py --check``
to fail when the committed notebooks are out of date.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

import jupytext
import nbformat

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "notebooks_src"
OUT_DIR = ROOT / "notebooks"
CORE_DIR = ROOT / "core"
FIXTURES = ROOT / "fixtures" / "responses.json"
COLAB_URL = (
    "https://colab.research.google.com/github/nickmelamed/"
    "cal-nerds-research-agent/blob/main/notebooks/{name}.ipynb"
)
BADGE = "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})"

CORE_MARKER = re.compile(r"^# @core (\w+)(?: (\w+))?[ \t]*$", re.MULTILINE)
OFFLINE_MARKER = re.compile(r"^# @offline-data[ \t]*$", re.MULTILINE)
CORE_IMPORT = re.compile(
    r"^(?:from core(?:\.\w+)* import (?:\([^)]*\)|[^\n]*)|import core(?:\.\w+)*[^\n]*)\n",
    re.MULTILINE,
)
# Module attribute access that only works when core/tools.py is a module.
TOOLS_PREFIX = re.compile(r"\btools\.(\w+)")
LEFTOVER = re.compile(r"^\s*(?:from|import) core\b|\btools\.[a-z_]+\(", re.MULTILINE)


SPLIT_FUNCTIONS = {"tools": ("search_arxiv", "get_abstract", "lookup_wikipedia")}


class BuildError(Exception):
    pass


def core_source(module: str, part: str | None = None) -> str:
    """Return a module's inlined code, or one named function, or ``helpers``.

    ``helpers`` is everything except the functions in ``SPLIT_FUNCTIONS``.
    """
    path = CORE_DIR / f"{module}.py"
    if not path.exists():
        raise BuildError(f"core/{module}.py does not exist")
    text = CORE_IMPORT.sub("", path.read_text())
    text = TOOLS_PREFIX.sub(r"\1", text)
    if LEFTOVER.search(text):
        raise BuildError(f"core/{module}.py still refers to core after inlining")
    if part is not None:
        text = pick_part(text, module, part)
    return text.strip() + "\n"


def pick_part(text: str, module: str, part: str) -> str:
    wanted = SPLIT_FUNCTIONS.get(module, ())
    lines = text.splitlines()
    spans = {
        node.name: (node.lineno - 1, node.end_lineno)
        for node in ast.parse(text).body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    }
    if part == "helpers":
        drop = {i for start, end in spans.values() for i in range(start, end)}
        return "\n".join(line for i, line in enumerate(lines) if i not in drop)
    if part not in spans:
        raise BuildError(f"core/{module}.py has no splittable function {part}")
    start, end = spans[part]
    return "\n".join(lines[start:end])


def offline_source() -> str:
    data = json.loads(FIXTURES.read_text())
    return f"OFFLINE_DATA.update(json.loads({json.dumps(json.dumps(data))}))\n"


def expand(source: str) -> str:
    """Replace the markers in one cell's source."""
    source = CORE_MARKER.sub(lambda m: core_source(m.group(1), m.group(2)).rstrip("\n"), source)
    return OFFLINE_MARKER.sub(lambda m: offline_source().rstrip("\n"), source)


def cell_metadata(source: str) -> dict:
    # Colab hides the code of a form cell and shows only its title.
    if source.startswith("# @title"):
        return {"cellView": "form", "jupyter": {"source_hidden": True}}
    return {}


def build_notebook(src_path: Path) -> nbformat.NotebookNode:
    parsed = jupytext.read(src_path)
    name = src_path.stem
    cells = [nbformat.v4.new_markdown_cell(BADGE.format(url=COLAB_URL.format(name=name)))]
    for cell in parsed.cells:
        source = expand(cell.source) if cell.cell_type == "code" else cell.source
        if cell.cell_type == "code":
            new = nbformat.v4.new_code_cell(source)
            new.metadata = cell_metadata(source)
        else:
            new = nbformat.v4.new_markdown_cell(source)
        cells.append(new)
    for number, cell in enumerate(cells):
        cell["id"] = f"{name}-{number:03d}"
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    nbformat.validate(notebook)
    return notebook


def shape(notebook: nbformat.NotebookNode) -> list:
    """Return what --check compares: cell types, sources, and metadata."""
    cells = [(c.cell_type, c.source, dict(c.metadata)) for c in notebook.cells]
    return [dict(notebook.metadata), cells]


def sources(names: list[str]) -> list[Path]:
    paths = [SRC_DIR / f"{name}.py" for name in names] if names else sorted(SRC_DIR.glob("*.py"))
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise BuildError(f"no source file: {missing[0]}")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="notebook names, default all")
    parser.add_argument("--check", action="store_true", help="fail if notebooks/ is stale")
    args = parser.parse_args(argv)

    try:
        paths = sources(args.names)
        built = {p.stem: build_notebook(p) for p in paths}
    except BuildError as error:
        print(f"build failed: {error}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(exist_ok=True)
    stale = []
    for name, notebook in built.items():
        target = OUT_DIR / f"{name}.ipynb"
        if args.check:
            if not target.exists() or shape(nbformat.read(target, 4)) != shape(notebook):
                stale.append(target.name)
        else:
            nbformat.write(notebook, target)
            print(f"wrote {target.relative_to(ROOT)}")
    if stale:
        print(f"out of date: {', '.join(stale)}. Run make build.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
