# %% [markdown]
# # Research Paper Assistant (The Finished Agent)
#
# This agent searches arXiv for papers, reads abstracts, looks up unfamiliar
# terms on Wikipedia, and answers with citations. Afterwards it checks that
# every cited paper was returned by a tool during this run.
#
# Run the cells from top to bottom. The cells with a title and hidden code
# hold the tools. You can open them with the arrow on the left.

# %% [markdown]
# ## 1. Setup
#
# First we install the `openai` package. It is the client library, and it
# also works with OpenRouter and Groq.

# %%
# !pip install -q openai

# %%
# @title Helpers for talking to the model
# @core client

# %% [markdown]
# ## 2. The Tools
#
# A tool is a Python function the model can ask us to run. There are three.
# `search_arxiv` finds papers, `get_abstract` reads one abstract, and
# `lookup_wikipedia` explains a term.

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

# %% [markdown]
# ## 3. Connect to the Model
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
# @title Saved responses for OFFLINE mode
# @offline-data

# %%
OFFLINE = False

client = make_client()
assert smoke_test(client), "Fix the key problem above, then run this cell again."

# %% [markdown]
# ## 4. Tell the Model what the Tools Do
#
# The model sees only these descriptions, not our Python code, so it picks
# tools based on them.

# %%
# @core schemas

# %% [markdown]
# ## 5. The agent loop
#
# The loop asks the model. If it wants a tool, we run the tool, hand back the
# result, and ask again. When it answers without a tool request, we are done.
# `MAX_STEPS` stops a run that never settles, and the last step turns tools
# off so the model has to answer.

# %%
# @title Trace printer and citation check
# @core tracer
# @core citations

# %%
# @core agent

# %%
SYSTEM_PROMPT = (
    "You are a research paper assistant. Use search_arxiv to find papers, "
    "get_abstract to read one, and lookup_wikipedia to explain unfamiliar "
    "terms. Search arXiv at most twice, read at most two abstracts, then "
    "answer. arXiv search ranks by relevance and cannot filter by date, so "
    "do not put years in a query. Answer in a short paragraph and cite each "
    "paper by its arXiv id. Only cite papers your tools returned."
)

# %% [markdown]
# ## 6. Ask a Question
#
# Watch the trace. Each step shows which tool the model chose and what came
# back.

# %%
QUESTION = (
    "Find a few papers on deep learning for protein structure prediction "
    "and explain in plain language what one of them does."
)

result = run_agent(client, QUESTION, SYSTEM_PROMPT, TOOLS)

# %% [markdown]
# ## 7. Check the Citations
#
# Models sometimes invent papers. This check looks at every arXiv id and
# quoted title in the answer and counts it only if a tool returned it in
# this run. It checks that a cited paper was retrieved. It does not check
# that what the answer says about the paper is true.

# %%
report = check_citations(result.answer, result.tracer.tool_results)
print(report.summary)
if report.unverified:
    print("Not retrieved by any tool:", report.unverified)

# %% [markdown]
# ## 8. A Backup Question
#
# Same agent, a different topic.

# %%
QUESTION = (
    "Find a few papers on machine learning for weather forecasting and "
    "explain in plain language what one of them does."
)

result = run_agent(client, QUESTION, SYSTEM_PROMPT, TOOLS)
report = check_citations(result.answer, result.tracer.tool_results)
print(report.summary)
if report.unverified:
    print("Not retrieved by any tool:", report.unverified)

# %% [markdown]
# ## 9. Compare with a Chatbot
#
# Ask a chatbot with web search off the same first question. Then ask it
# again with web search on. Look at which papers it names and whether you
# could find each one. The difference is what the citation check is for.
