"""Print each agent step and collect tokens, latency, and raw tool results."""

import json

DISPLAY_CHARS = 300


class Tracer:
    """Record and print one agent run."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.calls: list[dict] = []
        self.tool_results: list[dict] = []
        self.final_answer: str | None = None

    def _print(self, text: str) -> None:
        if self.verbose:
            print(text)

    def model_call(
        self,
        step: int,
        tokens: int,
        seconds: float,
        prompt: int = 0,
        completion: int = 0,
        cached: int = 0,
        reasoning: int = 0,
    ) -> None:
        """Record the tokens and latency of one model call.

        ``cached`` is part of ``prompt`` and ``reasoning`` is part of
        ``completion``. Both stay 0 when the API does not report them.
        """
        self.calls.append(
            {
                "step": step,
                "tokens": tokens,
                "seconds": seconds,
                "prompt": prompt,
                "completion": completion,
                "cached": cached,
                "reasoning": reasoning,
            }
        )

    def tool_call(self, step: int, name: str, args: dict, result) -> None:
        """Print one tool call and keep the raw result for the citation check."""
        self.tool_results.append({"step": step, "name": name, "result": result})
        shown = result if isinstance(result, str) else json.dumps(result)
        if len(shown) > DISPLAY_CHARS:
            shown = shown[:DISPLAY_CHARS] + "..."
        self._print(f"Step {step}: {name}({json.dumps(args)})")
        self._print(f"  -> {shown}")

    def note(self, text: str) -> None:
        """Print a line about something that went wrong mid-run."""
        self._print(text)

    def answer(self, text: str) -> None:
        """Print and keep the final answer."""
        self.final_answer = text
        self._print(f"\nAnswer:\n{text}")

    def summary(self) -> dict:
        """Return totals for the run."""
        return {
            "model_calls": len(self.calls),
            "tool_calls": len(self.tool_results),
            "tokens": sum(c["tokens"] for c in self.calls),
            "prompt_tokens": sum(c["prompt"] for c in self.calls),
            "completion_tokens": sum(c["completion"] for c in self.calls),
            "cached_tokens": sum(c["cached"] for c in self.calls),
            "reasoning_tokens": sum(c["reasoning"] for c in self.calls),
            "seconds": round(sum(c["seconds"] for c in self.calls), 2),
        }
