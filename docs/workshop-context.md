# Cal NERDS AI 101: Agent Demo Handoff

This picks up the planning for the Build an Agent segment of the Cal NERDS AI 101 workshop. The original outline is in `Cal_NERDS_AI_Doc.pdf`, which lives in the Claude project rather than this repo. Several decisions below replace parts of that outline.

## Workshop context

The workshop runs 10am to 1pm, with setup from 9:40 to 10:00. The audience spans community college students, undergrads, grad students and postdocs, mostly with little or no AI experience. Everyone has a laptop. Every tool must be free with no paid accounts. Questions are answered throughout, live and in the chat, and Q&A can run past 1pm.

| Time | Segment | Min |
|---|---|---|
| 9:40–10:00 | Setup (chatbot login, Colab, Groq API keys) | 20 |
| 10:00–10:05 | Welcome, learning objectives, experience poll | 5 |
| 10:05–10:30 | What is AI? Types, landscape, key terms | 25 |
| 10:30–11:15 | Prompt engineering, checking answers, responsible use | 45 |
| 11:15–11:35 | Break | 20 |
| 11:35–12:50 | Build an agent | 75 |
| 12:50–1:00 | Wrap-up and next steps, then open Q&A | 10 |

The prompt engineering block includes a live demo of a chatbot inventing a citation. The agent demo is designed to pay that off.

## Build an agent segment (75 min)

| Block | Min |
|---|---|
| Agents vs. chatbots overview, with a simple loop diagram on a slide | 10 |
| Live demo of the finished agent | 10 |
| Build time (guided and full-code tracks) | 45 |
| Share-out, 3 or 4 students, ideally from both tracks | 10 |

## Decision: drop Relevance AI

The original plan used Relevance AI for a no-code demo. We're dropping it because it means another sign-up, its visual builder is a different mental model from the Colab notebooks students build in, and free-tier limits or UI changes could break a live demo.

The replacement is a live run of the finished version of the same agent students will build, in Colab, printing each step of its reasoning and tool calls. That previews the build directly and shows the decide, call tool, read result, repeat loop that a polished UI would hide. An optional 2-minute extra is asking the same question in a chatbot with web search off and then on.

## The agent: research paper assistant

A student asks something like "Find recent papers on using machine learning to predict protein folding and summarize what they found." The agent searches arXiv, reads abstracts, and answers with real citations it actually retrieved.

Why this one

- It works at every level of the audience, from exploring a topic for curiosity to a real literature search.
- It answers the hallucination demo from earlier in the day. The agent cites real papers because it looked them up.
- arXiv and Wikipedia APIs are free and need no key. The only key is the Groq API key.

Tools in the finished version

1. `search_arxiv(query)` returns titles, authors, dates and links
2. `get_abstract(paper_id)` returns the full abstract
3. `lookup_wikipedia(term)` gives quick background on unfamiliar terms

Three tools keep the printed trace interesting, since the agent has to choose between them.

## Two build tracks (both in Colab, using Groq)

**Guided track (low-code).** All tool functions are pre-written. Students write the system prompt (plain-language vs. technical), point the agent at their own field, and deliberately make one tool description vague to watch the agent misuse or skip that tool. The last exercise shows non-coders that the descriptions drive the behavior. Call this track "Guided" in materials rather than "no-code," since students still see code cells.

**Full-code track.** Students start from the agent loop and one tool, then write a new tool themselves (such as `save_to_reading_list` or a date filter), add error handling for empty results and failed calls, cap loop iterations, and log tokens and latency per run.

## Practical notes

- arXiv asks for roughly one request every 3 seconds. Put a short delay inside the search tool.
- Test the chosen Groq model's tool-calling reliability ahead of time and pick the most dependable one for the live demo.
- Each student should use their own Groq key, created before the workshop, to avoid shared rate limits.
- The pre-workshop email should ask students to arrive at 9:40 with accounts already created.

## Superseded by docs/SPEC.md

Some of the above was decided later in planning and lives in docs/SPEC.md instead. Where they differ, SPEC.md wins.

- Model keys. The workshop key is now a paid OpenRouter key and a student's own free Groq key is optional. "Every tool must be free" still holds for students, since they pay nothing. Setup no longer requires a Groq account.
- The tool return limits (3 search results, truncated abstracts) come from the token budget in SPEC.md.
