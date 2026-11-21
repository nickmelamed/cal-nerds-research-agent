from core.citations import check_citations

SEARCH = {
    "name": "search_arxiv",
    "result": [
        {"id": "1706.03762", "title": "Attention Is All You Need"},
        {"id": "cond-mat/9812291", "title": "A Study of Spin Glasses"},
    ],
}
ABSTRACT = {
    "name": "get_abstract",
    "result": {"id": "2101.00001", "title": "Deep Folding Methods", "abstract": "..."},
}
WIKI = {
    "name": "lookup_wikipedia",
    "result": {"title": "Protein folding", "summary": "...", "url": "u"},
}
RESULTS = [SEARCH, ABSTRACT, WIKI]


def test_retrieved_paper_is_verified():
    report = check_citations("See arXiv:1706.03762 for details.", RESULTS)
    assert report.verified == ["1706.03762"]
    assert report.unverified == []
    assert report.summary == "1 of 1 cited papers were retrieved by the agent in this run."


def test_paper_not_retrieved_is_unverified():
    report = check_citations("See 1706.03762 and 2005.14165.", RESULTS)
    assert report.verified == ["1706.03762"]
    assert report.unverified == ["2005.14165"]
    assert report.summary.startswith("1 of 2")


def test_made_up_id_is_unverified():
    report = check_citations("As shown in arXiv:9999.99999.", RESULTS)
    assert report.verified == []
    assert report.unverified == ["9999.99999"]


def test_no_citations():
    report = check_citations("Proteins fold into shapes.", RESULTS)
    assert report.verified == [] and report.unverified == []
    assert report.summary == "The answer cites no papers."


def test_version_suffix_and_url_forms_match():
    answer = "Read https://arxiv.org/abs/1706.03762v5 and arXiv:2101.00001v2."
    report = check_citations(answer, RESULTS)
    assert report.verified == ["1706.03762", "2101.00001"]
    assert report.unverified == []


def test_old_style_id_keeps_archive_prefix():
    report = check_citations("Spin glasses (cond-mat/9812291v1).", RESULTS)
    assert report.verified == ["cond-mat/9812291"]


def test_old_style_id_not_retrieved_is_unverified():
    report = check_citations("See hep-th/9711200.", RESULTS)
    assert report.unverified == ["hep-th/9711200"]


def test_title_without_id_is_verified_case_insensitively():
    report = check_citations("The paper attention is all you need introduced it.", RESULTS)
    assert report.verified == ["1706.03762"]


def test_id_and_title_together_count_once():
    answer = '"Attention Is All You Need" (1706.03762) introduced it.'
    report = check_citations(answer, RESULTS)
    assert report.verified == ["1706.03762"]
    assert report.summary.startswith("1 of 1")


def test_invented_quoted_title_is_unverified():
    report = check_citations('See "Transformers Solve Protein Folding Forever".', RESULTS)
    assert report.unverified == ["Transformers Solve Protein Folding Forever"]


def test_quoted_wikipedia_title_is_not_flagged():
    report = check_citations('Background on "Protein folding" helps here.', RESULTS)
    assert report.unverified == []


def test_wikipedia_title_alone_is_not_a_paper():
    report = check_citations("Protein folding is how proteins get their shape.", RESULTS)
    assert report.verified == []


def test_results_from_a_fresh_run_do_not_carry_over():
    report = check_citations("See 1706.03762.", [])
    assert report.unverified == ["1706.03762"]


def test_string_results_are_ignored():
    results = [{"name": "search_arxiv", "result": "No papers found, try broader terms."}]
    report = check_citations("See 1706.03762.", results)
    assert report.unverified == ["1706.03762"]


def test_old_style_id_inside_a_url_is_matched_whole():
    report = check_citations("https://arxiv.org/abs/cond-mat/9812291", RESULTS)
    assert report.verified == ["cond-mat/9812291"]
    assert report.unverified == []
