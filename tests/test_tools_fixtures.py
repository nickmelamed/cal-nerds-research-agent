"""Tools run against recorded real responses, with no network."""

import pytest

from core import tools

pytestmark = pytest.mark.usefixtures("offline")


def test_search_returns_recorded_papers():
    papers = tools.search_arxiv("protein folding")
    assert len(papers) == tools.MAX_RESULTS
    assert {"id", "title", "authors", "date", "link"} == set(papers[0])
    assert all(p["link"] == f"https://arxiv.org/abs/{p['id']}" for p in papers)


def test_old_style_ids_keep_their_archive_prefix():
    ids = [p["id"] for p in tools.search_arxiv("protein folding")]
    assert "cond-mat/9812291" in ids


def test_abstract_comes_from_search_without_a_second_lookup():
    paper = tools.search_arxiv("protein folding")[1]
    result = tools.get_abstract(paper["id"])
    assert result["title"] == paper["title"]
    assert 0 < len(result["abstract"].split()) <= tools.ABSTRACT_WORDS + 1


def test_nonsense_query_returns_message():
    assert "No papers found" in tools.search_arxiv("zzzzqqqxxkk")


def test_unknown_paper_id_returns_message():
    assert "No paper found" in tools.get_abstract("0000.00000")


def test_wikipedia_summary_is_short():
    result = tools.lookup_wikipedia("Attention (machine learning)")
    assert result["title"] == "Attention (machine learning)"
    assert result["summary"].count(". ") < tools.WIKI_SENTENCES


def test_wikipedia_redirect_title_comes_back():
    assert tools.lookup_wikipedia("protein folding problem")["title"] == (
        "Protein structure prediction"
    )


def test_wikipedia_miss_returns_message():
    assert "No Wikipedia page" in tools.lookup_wikipedia("qqqzzzxxkk")


def test_wikipedia_search_fallback_finds_page_when_title_misses():
    assert tools.lookup_wikipedia("how proteins fold")["title"] == "Protein folding"
