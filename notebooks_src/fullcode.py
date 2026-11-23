# %% [markdown]
# # Research paper assistant: build it yourself
#
# This notebook starts with a small agent that already works. It has one
# tool, `search_arxiv`, and a loop that asks the model, runs the tool it
# picks, and repeats. It has no error handling, no limit on how long it runs,
# and no record of how many tokens it uses. Those are your tasks.
#
# The tasks are in priority order, so finishing two still gives you something
# to share. Each task has a "Your turn" cell, a check, and a hint you can
# open if you get stuck. The finished agent is in the demo notebook:
# [open the demo](https://colab.research.google.com/github/nickmelamed/cal-nerds-research-agent/blob/main/notebooks/demo.ipynb).
#
# Run the cells from top to bottom.

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
# If you have your own Groq key in Colab Secrets as `GROQ_API_KEY`, the
# notebook uses it. Otherwise it uses `OPENROUTER_API_KEY`, and if neither is
# set it asks you to paste a key.

# %%
client = make_client()
assert smoke_test(client), "Fix the key problem above, then run this cell again."

# %% [markdown]
# ## 2. The tool
#
# `search_arxiv` sends a search to arXiv and turns the reply into a short
# list of papers. arXiv asks for at most one request every 3 seconds, so the
# function waits if it was called a moment ago.

# %%
import json
import time
import xml.etree.ElementTree as ET

import requests

ARXIV_URL = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
ARXIV_DELAY_S = 3

last_arxiv_call = 0.0


def search_arxiv(query, max_results=3):
    global last_arxiv_call
    wait = ARXIV_DELAY_S - (time.monotonic() - last_arxiv_call)
    if wait > 0:
        time.sleep(wait)
    last_arxiv_call = time.monotonic()

    params = {
        "search_query": "all:" + query,
        "max_results": min(int(max_results), 3),
        "sortBy": "relevance",
    }
    reply = requests.get(ARXIV_URL, params=params)
    root = ET.fromstring(reply.text)

    papers = []
    for entry in root.findall("a:entry", ATOM):
        full_id = entry.findtext("a:id", namespaces=ATOM)
        papers.append(
            {
                "id": full_id.split("/abs/")[-1],
                "title": " ".join(entry.findtext("a:title", namespaces=ATOM).split()),
                "date": entry.findtext("a:published", namespaces=ATOM)[:10],
                "link": full_id,
            }
        )
    return papers


# %% [markdown]
# Try it on its own before the agent uses it.

# %%
search_arxiv("graph neural networks for molecules", 2)

# %% [markdown]
# ## 3. Tell the model what the tool does
#
# The model never sees the Python above. It sees only this description, and
# it decides whether to call the tool from the words in it.

# %%
SEARCH_ARXIV_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_arxiv",
        "description": (
            "Search arXiv for research papers on a topic. Returns the id, "
            "title, date, and link of the best matches."
        ),
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
}

TOOLS = [SEARCH_ARXIV_SCHEMA]

# A dictionary from a tool's name to the function that runs it.
TOOL_FUNCTIONS = {"search_arxiv": search_arxiv}

# %% [markdown]
# ## 4. The agent loop
#
# Each time around the loop we ask the model. If it asks for a tool, we run
# the tool, add the result to the conversation, and ask again. When it
# answers without asking for a tool, we are done.
#
# `tool_results` keeps what every tool returned. The citation check at the
# end uses it to see which papers the agent really retrieved.

# %%
SYSTEM_PROMPT = (
    "You are a research paper assistant. Use search_arxiv to find papers. "
    "Search arXiv at most twice, then answer. arXiv search cannot filter by "
    "date, so do not put years in a query. Answer in a short paragraph and "
    "cite each paper by its arXiv id. Only cite papers your tools returned."
)

tool_results = []


def run_agent(question):
    tool_results.clear()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    while True:
        response = chat(client, model=MODEL, messages=messages, tools=TOOLS)
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in message.tool_calls
                ],
            }
        )
        for call in message.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            result = TOOL_FUNCTIONS[name](**args)
            print(f"Tool call: {name}({args})")
            tool_results.append({"name": name, "args": args, "result": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )


# %% [markdown]
# ## 5. Ask a question and check the citations
#
# Models sometimes invent papers. The check below looks at every arXiv id in
# the answer and counts it only if a tool returned it in this run. It checks
# that a cited paper was retrieved. It does not check that what the answer
# says about the paper is true.

# %%
# @title Citation check
import re
from dataclasses import dataclass, field


def _normalize_id(paper_id):
    pid = paper_id.strip()
    pid = re.sub(r"^(https?://)?(www\.)?arxiv\.org/(abs|pdf)/", "", pid)
    pid = re.sub(r"^arxiv:", "", pid, flags=re.IGNORECASE)
    pid = re.sub(r"\.pdf$", "", pid)
    return re.sub(r"v\d+$", "", pid)


# @core citations

# %%
QUESTION = (
    "Find a few papers on machine learning for weather forecasting and "
    "explain in plain language what one of them does."
)

answer = run_agent(QUESTION)
print()
print(answer)

# %%
report = check_citations(answer, tool_results)
print(report.summary)
if report.unverified:
    print("Not retrieved by any tool:", report.unverified)

# %% [markdown]
# ## Task 1. Write a new tool
#
# Give the agent a second tool. Pick one.
#
# - `save_to_reading_list(paper_id, note)` stores a paper and a short note in
#   a list, and returns a message saying it was saved.
# - A date filter for `search_arxiv`, so the agent can ask for papers from a
#   given year or later. arXiv cannot filter by date itself, so you will
#   filter the results after they come back.
#
# You need three things. The function, its schema (the description the model
# reads), and a line in `TOOL_FUNCTIONS` and `TOOLS` so the loop knows about
# it.
#
# **Check:** ask a question where the new tool is useful, and see whether the
# agent uses it without being told. If it does not, read your description
# again. The model decides from those words alone.

# %% [markdown]
# <details>
# <summary>Hint</summary>
#
# Write the function first and call it by hand to see it works. Then copy
# `SEARCH_ARXIV_SCHEMA`, change the name, the description, and the
# parameters. Add the schema to `TOOLS` and the function to `TOOL_FUNCTIONS`
# under the same name as in the schema.
#
# </details>

# %%
# Your turn: write the new tool and its schema here.


# %%
# Add your schema to TOOLS and your function to TOOL_FUNCTIONS, then ask a
# question that should use it.
QUESTION = "Find two papers on protein folding and save the best one to my reading list."

answer = run_agent(QUESTION)
print()
print(answer)

# %% [markdown]
# ## Task 2. Handle errors
#
# Right now, anything that goes wrong stops the whole run with a red error.
# Make the agent keep going instead. Handle these three cases:
#
# - A search that finds nothing. Return a message the model can act on, such
#   as "No papers found, try broader terms".
# - A network failure or a slow reply. Give `requests.get` a `timeout`, and
#   catch the error it raises.
# - Bad arguments from the model, such as text that is not valid JSON or a
#   tool name that does not exist. Send a message back as the tool result.
#
# The pattern is the same each time. Catch the problem and return a short
# message that tells the model what happened, so it can try something else.
#
# **Check:** run the test cell below. It needs no internet.

# %% [markdown]
# <details>
# <summary>Hint</summary>
#
# Wrap the risky lines in `try:` and `except SomeError:`. In the search
# function that is the `requests.get` call and the XML parsing. In the loop it
# is `json.loads` and the tool call. `requests.RequestException` covers
# timeouts and other network errors. Check `if not papers:` before returning.
#
# </details>

# %%
# Your turn: add error handling to search_arxiv and run_agent above, then
# run the test cell below.

# %%
# @title Test for task 2
def test_error_handling():
    original_get = requests.get
    problems = []

    def fake_timeout(*args, **kwargs):
        raise requests.Timeout("forced timeout")

    for label, call in [
        ("empty query", lambda: search_arxiv("")),
        ("forced timeout", lambda: search_arxiv("graph neural networks")),
    ]:
        if label == "forced timeout":
            requests.get = fake_timeout
        try:
            outcome = call()
            if not isinstance(outcome, (str, list)):
                problems.append(f"{label}: expected a message or a list")
        except Exception as error:
            problems.append(f"{label}: raised {type(error).__name__}")
        finally:
            requests.get = original_get

    if problems:
        print("Not yet:")
        for problem in problems:
            print(" -", problem)
    else:
        print("Passed: search_arxiv returns a message instead of raising.")


test_error_handling()

# %% [markdown]
# ## Task 3. Cap the loop
#
# `while True` never stops if the model keeps asking for tools. Add a
# `max_steps` argument to `run_agent`, so `run_agent(question, max_steps=6)`
# makes at most six model calls. If the cap is reached, return a short
# message instead of an answer, such as "Stopped after 6 steps."
#
# **Check:** run the test cell below. It uses a pretend model that asks for a
# tool every time, so it needs no key.

# %% [markdown]
# <details>
# <summary>Hint</summary>
#
# Replace `while True:` with `for step in range(max_steps):`. If the loop
# ends without returning, the cap was reached, so return your message after
# the loop. Give `max_steps` a default value so older calls still work.
#
# </details>

# %%
# Your turn: add max_steps to run_agent above, then run the test cell below.

# %%
# @title Test for task 3
from types import SimpleNamespace


class AlwaysSearches:
    """A pretend model that asks for a search on every call."""

    def __init__(self):
        call = SimpleNamespace(
            id="call-1",
            function=SimpleNamespace(
                name="search_arxiv", arguments='{"query": "test"}'
            ),
        )
        message = SimpleNamespace(content="", tool_calls=[call])
        reply = SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=SimpleNamespace(total_tokens=10),
        )
        self.chat = self
        self.completions = self
        self.with_raw_response = self
        self.calls = 0
        self._reply = SimpleNamespace(headers={}, parse=lambda: reply)

    def create(self, **kwargs):
        self.calls += 1
        return self._reply


def test_step_cap():
    global client
    real_client, real_search = client, search_arxiv
    pretend = AlwaysSearches()
    client = pretend
    TOOL_FUNCTIONS["search_arxiv"] = lambda **kwargs: []
    try:
        outcome = run_agent("Any question", max_steps=1)
    except Exception as error:
        print("Not yet:", type(error).__name__, error)
        return
    finally:
        client = real_client
        TOOL_FUNCTIONS["search_arxiv"] = real_search

    if pretend.calls != 1:
        print(f"Not yet: the model was called {pretend.calls} times, expected 1.")
    elif not isinstance(outcome, str) or not outcome:
        print("Not yet: run_agent should return a message at the cap.")
    else:
        print("Passed: the loop stopped after 1 step and returned:", outcome)


test_step_cap()

# %% [markdown]
# ## Task 4. Log tokens and time
#
# Every model call costs tokens and takes time. Record both for each call,
# then print a summary at the end of a run. A table like this is enough:
#
# ```
# step  tokens  seconds
# 1     812     1.4
# 2     1650    2.1
# total 2462    3.5
# ```
#
# Each response has `response.usage.total_tokens`. Time the call with
# `time.monotonic()` before and after it.
#
# **Check:** run a question and see that the summary prints.

# %% [markdown]
# <details>
# <summary>Hint</summary>
#
# Make an empty list called `call_log` at the top of `run_agent`. After each
# `chat(...)` call, append a dictionary with the step number, the tokens,
# and the seconds. After the loop ends, print one line per entry and one line
# with the totals. Some providers leave `usage` empty, so use `0` when it is
# missing.
#
# </details>

# %%
# Your turn: add logging to run_agent above, then run a question below.
answer = run_agent(QUESTION)
print()
print(answer)

# %% [markdown]
# ## Stretch
#
# If you finish early, pick one.
#
# - Add `get_abstract` and `lookup_wikipedia` as new tools, written from
#   scratch. The demo notebook has working versions to compare against once
#   you have tried.
# - Make `check_citations` stricter. Right now it checks arXiv ids. Make it
#   also match the titles of papers the agent mentions.
