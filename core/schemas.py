"""Tool schemas the model sees. The descriptions are plain strings so the
guided track can change the wording without touching the structure."""

SEARCH_ARXIV_DESCRIPTION = (
    "Search arXiv for research papers on a topic. Returns the id, title, "
    "authors, date, and link of the best matches."
)
GET_ABSTRACT_DESCRIPTION = (
    "Get the abstract of one arXiv paper. Use an id returned by search_arxiv."
)
LOOKUP_WIKIPEDIA_DESCRIPTION = (
    "Look up a term or concept on Wikipedia and get a short plain-language "
    "summary. Use it to explain jargon."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": SEARCH_ARXIV_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search terms"},
                    "max_results": {
                        "type": "integer",
                        "description": "How many papers to return, 1 to 3",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_abstract",
            "description": GET_ABSTRACT_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "An arXiv id such as 2101.00001",
                    },
                },
                "required": ["paper_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_wikipedia",
            "description": LOOKUP_WIKIPEDIA_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string", "description": "Word or phrase"},
                },
                "required": ["term"],
            },
        },
    },
]
