"""Client setup for OpenRouter and Groq, 429 retry, and usage helpers."""

import os
import time
from getpass import getpass

import requests

MODEL = "openai/gpt-oss-120b"
MAX_429_RETRIES = 5
DEFAULT_WAIT_S = 2
MAX_WAIT_S = 30
TOKENS_HEADER = "x-ratelimit-remaining-tokens"

BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
}
KEY_NAMES = {"openrouter": "OPENROUTER_API_KEY", "groq": "GROQ_API_KEY"}
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"
GROQ_KEY_PREFIX = "gsk_"

_sleep = time.sleep
_last_headers: dict[str, str] = {}
_active: dict[str, str | None] = {"provider": None}


def _secret(name: str) -> str | None:
    key = os.environ.get(name)
    if key:
        return key
    try:
        from google.colab import userdata

        return userdata.get(name) or None
    except Exception:
        return None


def choose_provider() -> str:
    """Return ``"groq"`` when a student's own key is set, else ``"openrouter"``."""
    return "groq" if _secret(KEY_NAMES["groq"]) else "openrouter"


def get_api_key(provider: str | None = None) -> str:
    """Return the key for ``provider`` from the environment, Colab Secrets, or a prompt."""
    name = KEY_NAMES[provider or choose_provider()]
    return _secret(name) or getpass(f"{name}: ")


def make_client(provider: str | None = None):
    """Return an OpenAI-compatible client and remember which provider it uses.

    With no ``provider`` the choice follows ``choose_provider``. A key typed at
    the prompt that starts with ``gsk_`` switches to Groq.
    """
    from openai import OpenAI

    chosen = provider or choose_provider()
    key = _secret(KEY_NAMES[chosen]) or getpass(
        "Paste your API key (the workshop key, or your own Groq key): "
    )
    if provider is None and key.startswith(GROQ_KEY_PREFIX):
        chosen = "groq"
    _active["provider"] = chosen
    return OpenAI(base_url=BASE_URLS[chosen], api_key=key)


def active_provider() -> str | None:
    """Return the provider of the last client made, for the smoke test."""
    return _active["provider"]


def _retry_wait(error: Exception, attempt: int = 0) -> float:
    headers = getattr(getattr(error, "response", None), "headers", None) or {}
    try:
        wait = float(headers["retry-after"])
    except (KeyError, TypeError, ValueError):
        wait = DEFAULT_WAIT_S * 2**attempt
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
            wait = _retry_wait(error, attempt)
            print(f"The shared key is busy, retrying in {wait:g}s")
            _sleep(wait)
        else:
            _last_headers.clear()
            _last_headers.update({k.lower(): v for k, v in raw.headers.items()})
            return raw.parse()


def remaining_tokens() -> int | None:
    """Return the tokens left this minute from the last response, if reported.

    Only Groq sends this header.
    """
    try:
        return int(_last_headers[TOKENS_HEADER])
    except (KeyError, ValueError):
        return None


def openrouter_credit(key: str | None = None) -> float | None:
    """Return the credit left on the OpenRouter key in dollars, or None.

    None means the key has no limit set or the request failed.
    """
    key = key or _secret(KEY_NAMES["openrouter"])
    try:
        reply = requests.get(
            OPENROUTER_KEY_URL, headers={"Authorization": f"Bearer {key}"}, timeout=10
        )
        reply.raise_for_status()
        remaining = reply.json()["data"]["limit_remaining"]
    except Exception:
        return None
    return float(remaining) if remaining is not None else None


def smoke_test(client, model: str = MODEL) -> bool:
    """Send one tiny request and print whether the key and model work."""
    try:
        chat(client, model=model, messages=[{"role": "user", "content": "Say ready."}])
    except Exception as error:
        print(f"Smoke test failed with {active_provider()} ({type(error).__name__}).")
        print("Check that your key is right and has credit, then run this cell again.")
        return False
    print(f"Smoke test passed. Using {active_provider()} with model {model}.")
    return True
