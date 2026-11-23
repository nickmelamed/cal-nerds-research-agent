# %% [markdown]
# # Research Paper Assistant (Guided Track)
#
# In this notebook you change how a research agent behaves by editing plain
# text. You do not need to write any code. The agent searches arXiv for
# papers, reads abstracts, looks up unfamiliar terms on Wikipedia, and answers
# with citations. Afterwards it checks that every cited paper was returned by a
# tool during the run.
#
# Run the cells from top to bottom. Cells with a title and hidden code hold
# the tools and helpers. You can open them with the arrow on the left, but you
# never have to change them. The cells marked **Your turn** are the ones you
# edit.

# %% [markdown]
# ## Setup
#
# First we install the `openai` package. It is the client library, and it
# also works with OpenRouter and Groq.

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
# `OFFLINE = False` means the tools call arXiv and Wikipedia. Set it to
# `True` to use saved responses instead. It only replaces the tools. The
# model still needs a working key. Saved responses cover only a few searches,
# so most questions get a "could not be reached" message in this mode.
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
# The model never sees our Python code for the tools. It sees only a short
# description of each one, and it decides which tool to use from those
# descriptions. Here they are. You will edit them in Exercise 3. For now,
# just run the cell.

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
# question is what you ask. Run the next two cells, then read the trace. Each
# step shows which tool the model chose and what came back.

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
# **What to notice.** The papers the agent finds are often the same. What
# differs is the answer. Compare the number of steps and the tools used for
# each prompt, and see whether the citation check passes for both.

# %% [markdown]
# ## Exercise 2. Ask About Your Field (10 minutes)
#
# **Your turn.** Replace the question with one from your own major or research
# area. Here are three examples that work well.
#
# - What is quantum error correction and what are a few key papers on it?
# - How do researchers use machine learning to study how proteins fold?
# - Find a few papers on large language model agents that use tools.
#
# Two kinds of question tend to go badly. arXiv search cannot filter by date,
# so a question that asks for the "latest" papers makes the agent search
# again and again. And a question about a famous system whose paper is not on
# arXiv sends the agent hunting for something that is not there.

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
# ## Exercise 3. Break a Tool Description (12 minutes)
#
# **Your turn.** The model picks tools using only their descriptions. Change
# one description so it is vague or misleading, run the agent, and watch what
# happens. Here are two ideas.
#
# - Vague: `"Gets information."`
# - Misleading: `"Looks up the meaning of a word in a dictionary."` for
#   `search_arxiv`
#
# Edit the strings in the cell below, run it, then ask the same question as
# before.

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
# **What to notice.** Did the agent skip the tool you changed, or use it for
# the wrong job? Did the citation check catch anything? Put the original
# description back and run again to see the difference.

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
