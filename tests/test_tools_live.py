import pytest

from core import tools

pytestmark = pytest.mark.slow


def test_live_search_and_abstract_reuse_cache():
    tools.reset_cache()
    papers = tools.search_arxiv("protein structure prediction deep learning")
    assert isinstance(papers, list) and 1 <= len(papers) <= tools.MAX_RESULTS
    result = tools.get_abstract(papers[0]["id"])
    assert result["title"] == papers[0]["title"]
    assert 0 < len(result["abstract"].split()) <= tools.ABSTRACT_WORDS + 1


def test_live_bad_paper_id_returns_message():
    result = tools.get_abstract("0000.00000")
    assert isinstance(result, str)


def test_live_wikipedia_exact_and_fallback():
    exact = tools.lookup_wikipedia("Protein folding")
    assert isinstance(exact, dict) and exact["summary"]
    assert isinstance(tools.lookup_wikipedia("protein folding problem"), dict)
