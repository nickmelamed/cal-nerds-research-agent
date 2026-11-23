"""The agent loop: ask the model, run the tools it picks, repeat."""

import inspect
import json
import time
from dataclasses import dataclass

from core import tools
from core.client import chat
from core.tracer import Tracer

MODEL = "openai/gpt-oss-120b"
MAX_STEPS = 6
RESULT_CHARS = 2000
TRUNCATION_MARK = " [truncated]"
FINAL_STEP_NOTE = (
    "You have no tool calls left. Answer now using only what the tools "
    "returned, and cite only papers they returned."
)

TOOL_FUNCTIONS = {
    "search_arxiv": tools.search_arxiv,
    "get_abstract": tools.get_abstract,
    "lookup_wikipedia": tools.lookup_wikipedia,
}


@dataclass
class AgentResult:
    answer: str
    steps: int
    tracer: Tracer


def _run_tool(name: str, raw_args: str):
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"There is no tool called {name}. Use one of: {', '.join(TOOL_FUNCTIONS)}."
    try:
        args = json.loads(raw_args or "{}")
        if not isinstance(args, dict):
            raise ValueError
    except ValueError:
        return "The tool arguments were not valid JSON. Try the call again."
    try:
        inspect.signature(func).bind(**args)
    except TypeError:
        return f"The arguments did not match {name}. Check the tool description."
    try:
        return func(**args)
    except Exception as error:
        return f"{name} failed ({type(error).__name__}). Try different input or another tool."


def _to_message_text(result) -> str:
    text = result if isinstance(result, str) else json.dumps(result)
    if len(text) > RESULT_CHARS:
        return text[:RESULT_CHARS] + TRUNCATION_MARK
    return text


def run_agent(
    client,
    question: str,
    system_prompt: str,
    tool_schemas: list[dict],
    max_steps: int = MAX_STEPS,
    tracer: Tracer | None = None,
    model: str = MODEL,
    extra_body: dict | None = None,
) -> AgentResult:
    """Run the agent until it answers or reaches ``max_steps`` model calls.

    Clears the tool caches first. A ``tool_use_failed`` error is sent
    back to the model once, and a second one ends the run with a message.
    """
    tracer = tracer or Tracer()
    tools.reset_cache()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    retried_tool_error = False

    for step in range(1, max_steps + 1):
        start = time.monotonic()
        try:
            # The last call has tools off so a run that keeps searching still
            # ends with an answer built from what it already retrieved.
            last = step == max_steps and max_steps > 1
            response = chat(
                client,
                model=model,
                messages=messages + [{"role": "user", "content": FINAL_STEP_NOTE}] * last,
                tools=tool_schemas,
                extra_body=extra_body,
                **({"tool_choice": "none"} if last else {}),
            )
        except Exception as error:
            if "tool_use_failed" not in str(error):
                raise
            if retried_tool_error:
                text = "The model could not format a tool call, so the run stopped."
                tracer.answer(text)
                return AgentResult(text, step, tracer)
            retried_tool_error = True
            tracer.note(f"Step {step}: the model made a malformed tool call, retrying")
            messages.append(
                {
                    "role": "user",
                    "content": f"Your last tool call was malformed ({error}). "
                    "Call the tool again with valid arguments.",
                }
            )
            continue

        usage = getattr(response, "usage", None)
        tracer.model_call(
            step,
            _count(usage, "total_tokens"),
            time.monotonic() - start,
            prompt=_count(usage, "prompt_tokens"),
            completion=_count(usage, "completion_tokens"),
            cached=_count(getattr(usage, "prompt_tokens_details", None), "cached_tokens"),
            reasoning=_count(getattr(usage, "completion_tokens_details", None), "reasoning_tokens"),
            served_by=_served_by(response),
            cost=_cost(usage),
        )

        message = response.choices[0].message
        if not message.tool_calls:
            text = message.content or ""
            tracer.answer(text)
            return AgentResult(text, step, tracer)

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
            result = _run_tool(call.function.name, call.function.arguments)
            tracer.tool_call(step, call.function.name, _parsed_args(call), result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": _to_message_text(result),
                }
            )

    text = f"Stopped after {max_steps} steps without a final answer."
    tracer.answer(text)
    return AgentResult(text, max_steps, tracer)


def _cost(usage) -> float:
    value = getattr(usage, "cost", None)
    if value is None:
        value = (getattr(usage, "model_extra", None) or {}).get("cost")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _served_by(response) -> str:
    name = getattr(response, "provider", None)
    if name is None:
        name = (getattr(response, "model_extra", None) or {}).get("provider")
    return name if isinstance(name, str) else ""


def _count(obj, name: str) -> int:
    value = getattr(obj, name, 0)
    return value if isinstance(value, int) else 0


def _parsed_args(call) -> dict:
    try:
        args = json.loads(call.function.arguments or "{}")
    except ValueError:
        return {}
    return args if isinstance(args, dict) else {}
