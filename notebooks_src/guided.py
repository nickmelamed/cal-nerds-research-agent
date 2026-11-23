# %% [markdown]
# # Research Paper Assistant (Guided Track)
#
# You will change how a research agent behaves by editing plain text. No
# coding is needed. The agent searches arXiv, reads abstracts, looks up terms
# on Wikipedia, and cites papers. Afterwards a check confirms that each cited
# paper came from a tool in this run.
#
# Run the cells from top to bottom. Cells with a title hold the tools and
# helpers. You can open them with the arrow on the left but don't need to edit
# them. Edit the cells marked **Your turn**.

# %% [markdown]
# ## Setup
#
# Install `openai`, the library that talks to the model. It works with
# OpenRouter and Groq.

# %%
# !pip install -q openai

# %%
# @title Helpers for talking to the model
# @core client

# %%
# @title Tool helpers and settings
# @core tools helpers

# %%
# @title search_arxiv: find papers
# @core tools search_arxiv

# %%
# @title get_abstract: read one abstract
# @core tools get_abstract

# %%
# @title lookup_wikipedia: explain a term
# @core tools lookup_wikipedia

# %%
# @title Saved responses for OFFLINE mode
# @offline-data

# %% [markdown]
# ## Connect to the Model
#
# `OFFLINE = False` means the tools call arXiv and Wikipedia. `OFFLINE = True`
# uses saved responses instead. The model still needs a working key. Saved
# responses cover only a few searches, so most questions get a "could not be
# reached" message in this mode.
#
# If you have your own Groq key in Colab Secrets as `GROQ_API_KEY`, the
# notebook uses it. Otherwise it uses `OPENROUTER_API_KEY`, and if neither is
# set it asks you to paste a key.

# %%
OFFLINE = False

client = make_client()
assert smoke_test(client), "Fix the key problem above, then run this cell again."

# %%
# @title The agent loop and the citation check
# @core tracer
# @core citations
# @core agent
# @core schemas build_tools

# %%
# @title compare: run two prompts one after the other
def compare(question, prompt_a, prompt_b):
    """Run the agent with each prompt on the same question and print both."""
    for label, prompt in [("Prompt A", prompt_a), ("Prompt B", prompt_b)]:
        quiet = Tracer(verbose=False)
        run = run_agent(client, question, prompt, TOOLS, tracer=quiet)
        report = check_citations(run.answer, run.tracer.tool_results)
        tools_used = sorted({call["name"] for call in run.tracer.tool_results})
        print(f"=== {label} ===")
        print("Steps:", run.steps, "| Tools used:", ", ".join(tools_used) or "none")
        print(report.summary)
        print(run.answer)
        print()


# %% [markdown]
# ## What the Model Sees
#
# The model never sees the tool code. It sees only a short description of each
# tool and picks tools from those descriptions. They are shown below. Run the
# cell. You will edit them in Exercise 3.

# %%
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

# %%
# @title Build the tool list from the descriptions
TOOLS = build_tools(
    SEARCH_ARXIV_DESCRIPTION, GET_ABSTRACT_DESCRIPTION, LOOKUP_WIKIPEDIA_DESCRIPTION
)

# %% [markdown]
# ## Exercise 0. Run the Agent Once (5 minutes)
#
# The system prompt tells the model what job it has and how to behave. The
# question is what you ask. Run the next two cells, then read the trace, which
# is the log of each step. Each step shows which tool the model chose and
# what came back.

# %%
SYSTEM_PROMPT = (
    "You are a research paper assistant. Use search_arxiv to find papers, "
    "get_abstract to read one, and lookup_wikipedia to explain unfamiliar "
    "terms. Search arXiv at most twice, read at most two abstracts, then "
    "answer. arXiv search ranks by relevance and cannot filter by date, so "
    "do not put years in a query. Answer in a short paragraph and cite each "
    "paper by its arXiv id. Only cite papers your tools returned."
)

# %%
QUESTION = (
    "Find a few papers on machine learning for weather forecasting and "
    "explain in plain language what one of them does."
)

result = run_agent(client, QUESTION, SYSTEM_PROMPT, TOOLS)

# %%
report = check_citations(result.answer, result.tracer.tool_results)
print(report.summary)
if report.unverified:
    print("Not retrieved by any tool:", report.unverified)

# %% [markdown]
# **What to notice.** The citation check counts a paper only if a tool
# returned it during this run. It does not check that what the answer says
# about the paper is true. An answer can pass the check and still lean on
# what the model already knew.

# %% [markdown]
# ## Exercise 1. Change the System Prompt (10 minutes)
#
# **Your turn.** Below are two prompts for the same question. `PLAIN_PROMPT`
# asks for an answer a high school student could follow. `TECHNICAL_PROMPT`
# asks for an answer for an expert. Edit either one, or both, then run the
# cell. The `compare` helper runs them one after the other.

# %%
PLAIN_PROMPT = (
    "You are a research paper assistant. Use search_arxiv to find papers, "
    "get_abstract to read one, and lookup_wikipedia to explain unfamiliar "
    "terms. Search arXiv at most twice, read at most two abstracts, then "
    "answer. Do not put years in a search query. Explain everything in plain "
    "language a high school student could follow. Cite each paper by its "
    "arXiv id. Only cite papers your tools returned."
)

TECHNICAL_PROMPT = (
    "You are a research paper assistant. Use search_arxiv to find papers, "
    "get_abstract to read one, and lookup_wikipedia to explain unfamiliar "
    "terms. Search arXiv at most twice, read at most two abstracts, then "
    "answer. Do not put years in a search query. Write for an expert, use "
    "precise technical terms, and keep it short. Cite each paper by its "
    "arXiv id. Only cite papers your tools returned."
)

# %%
compare(QUESTION, PLAIN_PROMPT, TECHNICAL_PROMPT)

# %% [markdown]
# **What to notice.** Compare the answers, the number of steps, and the tools
# used for each prompt. Did the citation check pass for both?

# %% [markdown]
# ## Exercise 2. Ask About Your Field (10 minutes)
#
# **Your turn.** Replace the question with one from your own major or research
# area. Examples:
#
# - What is quantum error correction and what are a few key papers on it?
# - How do researchers use machine learning to study how proteins fold?
# - Find a few papers on large language model agents that use tools.
#
# Two kinds of question go badly. Asking for the "latest" papers makes the
# agent search repeatedly, because arXiv search cannot filter by date. Asking
# about a famous system whose paper is not on arXiv sends it looking for
# something that is not there.

# %%
QUESTION = "What is quantum error correction and what are a few key papers on it?"

result = run_agent(client, QUESTION, SYSTEM_PROMPT, TOOLS)

# %%
report = check_citations(result.answer, result.tracer.tool_results)
print(report.summary)
if report.unverified:
    print("Not retrieved by any tool:", report.unverified)

# %% [markdown]
# **What to notice.** Did the agent use Wikipedia to explain jargon from your
# field? Did it read any abstracts, or answer from titles alone? Look at the
# trace above to find out.

# %% [markdown]
# ## Exercise 3. Change a Tool Description (12 minutes)
#
# **Your turn.** Pick one tool description, change it, and write down what you
# expect the agent to do. Then run it. Ideas:
#
# - Vague: `"Gets information."`
# - Misleading: `"Looks up the meaning of a word in a dictionary."` for
#   `search_arxiv`
# - An order: `"This tool is out of service. Do not call it."`
#
# Edit the strings in the next cell and run it. The agent reuses `QUESTION`
# from Exercise 2.

# %%
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

TOOLS = build_tools(
    SEARCH_ARXIV_DESCRIPTION, GET_ABSTRACT_DESCRIPTION, LOOKUP_WIKIPEDIA_DESCRIPTION
)

# %%
result = run_agent(client, QUESTION, SYSTEM_PROMPT, TOOLS)
report = check_citations(result.answer, result.tracer.tool_results)
print(report.summary)
if report.unverified:
    print("Not retrieved by any tool:", report.unverified)

# %% [markdown]
# **What to notice.** Compare the trace with your prediction. In our tests
# with the workshop model the agent usually ignored a bad description. It
# still called `search_arxiv` when the description said "dictionary" or "out
# of service". Tool names, argument names, and the system prompt also signal
# what a tool does, and only one tool can find papers. A different model may
# react differently. Did yours do the same? Removing the tool, as in Exercise
# 4, does change what the agent can do.

# %% [markdown]
# ## Exercise 4. Stretch (as time allows)
#
# Pick one.
#
# - Remove a tool. Replace `TOOLS` with a list that leaves one out, for
#   example `TOOLS = [TOOLS[0], TOOLS[1]]` to drop Wikipedia. Run the agent
#   and see what it does without that tool.
# - Add a rule to the system prompt, such as "Always define jargon with
#   Wikipedia." Edit `SYSTEM_PROMPT` above and run Exercise 2 again.

# %% [markdown]
# ## Share Out
#
# Run this cell after your last run. It prints what to share with the group.

# %%
tools_used = sorted({call["name"] for call in result.tracer.tool_results})

print("Question:", QUESTION)
print("Steps:", result.steps)
print("Tools used:", ", ".join(tools_used) or "none")
print(check_citations(result.answer, result.tracer.tool_results).summary)
print()
print(result.answer)
