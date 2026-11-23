# %% [markdown]
# # Research paper assistant: the finished agent
#
# This notebook is the finished agent. It searches arXiv for papers, reads
# abstracts, looks up unfamiliar terms on Wikipedia, and answers with
# citations. Afterwards it checks that every paper it cited was really
# returned by a tool during this run.
#
# Run the cells from top to bottom. The cells with a title and hidden code
# hold the tools. You can open them with the arrow on the left.

# %% [markdown]
# ## 1. Setup
#
# First we install the `openai` package. It is the library that talks to the
# model, even though we use it with OpenRouter or Groq.

# %%
# !pip install -q openai

# %%
# @title Helpers for talking to the model
# @core client

# %% [markdown]
# ## 2. The tools
#
# A tool is a Python function the model can ask us to run. There are three.
# `search_arxiv` finds papers, `get_abstract` reads one abstract, and
# `lookup_wikipedia` explains a term.

# %%
# @title The three tools
# @core tools

# %% [markdown]
# ## 3. Connect to the model
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
smoke_test(client)

# %% [markdown]
# ## 4. Tell the model what the tools do
#
# The model never sees our Python code. It only sees these descriptions, so
# clear descriptions are how it decides which tool to call.

# %%
# @core schemas

# %% [markdown]
# ## 5. The agent loop
#
# The loop is the whole idea of an agent. We ask the model. If it wants a
# tool, we run the tool, hand back the result, and ask again. When it answers
# without asking for a tool, we are done. `MAX_STEPS` stops a run that never
# settles, and the last step turns tools off so the model has to answer.

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
# ## 6. Ask a question
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
# ## 7. Check the citations
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
# ## 8. A backup question
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

# %% [markdown]
# ## 9. Compare with a chatbot
#
# Ask a chatbot with web search off the same first question. Then ask it
# again with web search on. Look at which papers it names and whether you
# could find each one. The difference is what the citation check is for.
