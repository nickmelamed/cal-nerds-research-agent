"""Tool description sets for testing exercise 3 of the guided notebook."""

from core import schemas

BASELINE = "baseline"
DEFAULT_PROMPT = "default"

PROMPTS = {
    DEFAULT_PROMPT: None,
    # Names no tool, so only the descriptions guide tool choice.
    "minimal": (
        "You are a research paper assistant. Answer in a short paragraph and "
        "cite each paper by its arXiv id. Only cite papers your tools returned."
    ),
}

# Each value is (search_arxiv, get_abstract, lookup_wikipedia).
VARIANTS = {
    BASELINE: (
        schemas.SEARCH_ARXIV_DESCRIPTION,
        schemas.GET_ABSTRACT_DESCRIPTION,
        schemas.LOOKUP_WIKIPEDIA_DESCRIPTION,
    ),
    "vague_search": (
        "Gets information.",
        schemas.GET_ABSTRACT_DESCRIPTION,
        schemas.LOOKUP_WIKIPEDIA_DESCRIPTION,
    ),
    "misleading_search": (
        "Looks up the meaning of a word in a dictionary.",
        schemas.GET_ABSTRACT_DESCRIPTION,
        schemas.LOOKUP_WIKIPEDIA_DESCRIPTION,
    ),
    "off_search": (
        "This tool is out of service. Do not call it.",
        schemas.GET_ABSTRACT_DESCRIPTION,
        schemas.LOOKUP_WIKIPEDIA_DESCRIPTION,
    ),
    "vague_wikipedia": (
        schemas.SEARCH_ARXIV_DESCRIPTION,
        schemas.GET_ABSTRACT_DESCRIPTION,
        "Gets information.",
    ),
    "off_wikipedia": (
        schemas.SEARCH_ARXIV_DESCRIPTION,
        schemas.GET_ABSTRACT_DESCRIPTION,
        "This tool is out of service. Do not call it.",
    ),
    "misleading_wikipedia": (
        schemas.SEARCH_ARXIV_DESCRIPTION,
        schemas.GET_ABSTRACT_DESCRIPTION,
        "Convert a number from one unit of measure to another.",
    ),
}


def tools_for(variant: str) -> list[dict]:
    """Return the tool schemas for a named description set."""
    return schemas.build_tools(*VARIANTS[variant])
