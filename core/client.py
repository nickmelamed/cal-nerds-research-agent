"""Groq client setup, 429 retry, and the rate limit header reader."""

import os
import time
from getpass import getpass

MAX_429_RETRIES = 5
DEFAULT_WAIT_S = 2
MAX_WAIT_S = 30
TOKENS_HEADER = "x-ratelimit-remaining-tokens"

_sleep = time.sleep
_last_headers: dict[str, str] = {}


def get_api_key() -> str:
    """Return the Groq key from the environment, Colab Secrets, or a prompt."""
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    try:
        from google.colab import userdata

        key = userdata.get("GROQ_API_KEY")
    except Exception:
        key = None
    return key or getpass("Groq API key: ")


def make_client():
    """Return a Groq client using the key from ``get_api_key``."""
    from groq import Groq

    return Groq(api_key=get_api_key())


def _retry_wait(error: Exception) -> float:
    headers = getattr(getattr(error, "response", None), "headers", None) or {}
    try:
        wait = float(headers.get("retry-after", DEFAULT_WAIT_S))
    except (TypeError, ValueError):
        wait = DEFAULT_WAIT_S
    return min(max(wait, 1), MAX_WAIT_S)


def chat(client, **kwargs):
    """Call the chat endpoint, retrying on 429.

    Response headers are kept for ``remaining_tokens``. After the retries run
    out the last 429 error is raised.
    """
    raw_api = client.chat.completions.with_raw_response
    for attempt in range(MAX_429_RETRIES + 1):
        try:
            raw = raw_api.create(**kwargs)
        except Exception as error:
            if getattr(error, "status_code", None) != 429 or attempt == MAX_429_RETRIES:
                raise
            wait = _retry_wait(error)
            print(f"The shared key is busy, retrying in {wait:g}s")
            _sleep(wait)
        else:
            _last_headers.clear()
            _last_headers.update({k.lower(): v for k, v in raw.headers.items()})
            return raw.parse()


def remaining_tokens() -> int | None:
    """Return the tokens left this minute from the last response, if reported."""
    try:
        return int(_last_headers[TOKENS_HEADER])
    except (KeyError, ValueError):
        return None
