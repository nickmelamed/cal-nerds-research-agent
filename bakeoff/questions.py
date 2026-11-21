"""Questions and the system prompt used in the model bake-off."""

from dataclasses import dataclass

SYSTEM_PROMPT = (
    "You are a research paper assistant. Use search_arxiv to find papers, "
    "get_abstract to read one, and lookup_wikipedia to explain unfamiliar "
    "terms. Answer in a short paragraph and cite each paper by its arXiv id. "
    "Only cite papers your tools returned."
)


@dataclass(frozen=True)
class Question:
    key: str
    text: str
    needs_multiple_tools: bool


# guided_* are placeholders until phase 6.
QUESTIONS = [
    Question(
        "demo",
        "What are the main deep learning approaches to protein structure "
        "prediction? Explain any jargon and cite papers.",
        True,
    ),
    Question(
        "demo_backup",
        "What is the attention mechanism in transformers, and which papers "
        "introduced or improved it?",
        True,
    ),
    Question(
        "guided_physics",
        "What is quantum error correction and what are recent papers on it?",
        True,
    ),
    Question(
        "guided_biology",
        "How do researchers use machine learning to study how proteins fold?",
        True,
    ),
    Question(
        "guided_cs",
        "Find recent papers on large language model agents that use tools.",
        False,
    ),
]

BY_KEY = {q.key: q for q in QUESTIONS}
