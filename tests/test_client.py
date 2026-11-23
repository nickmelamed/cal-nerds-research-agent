import pytest

from core import client


class Err(Exception):
    def __init__(self, status, retry_after=None):
        self.status_code = status
        headers = {} if retry_after is None else {"retry-after": retry_after}
        self.response = type("R", (), {"headers": headers})()


class Raw:
    def __init__(self, headers=None):
        self.headers = headers or {}

    def parse(self):
        return "parsed"


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.chat = self
        self.completions = self
        self.with_raw_response = self

    def create(self, **kwargs):
        self.calls += 1
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def sleeps(monkeypatch):
    log = []
    monkeypatch.setattr(client, "_sleep", log.append)
    client._last_headers.clear()
    return log


def test_retries_429_using_retry_after(sleeps, capsys):
    fake = FakeClient([Err(429, "4"), Raw()])
    assert client.chat(fake, model="m") == "parsed"
    assert sleeps == [4]
    assert "The shared key is busy, retrying in 4s" in capsys.readouterr().out


def test_default_wait_without_header(sleeps):
    fake = FakeClient([Err(429), Raw()])
    client.chat(fake)
    assert sleeps == [client.DEFAULT_WAIT_S]


def test_gives_up_after_cap(sleeps):
    fake = FakeClient([Err(429, "1")] * (client.MAX_429_RETRIES + 1))
    with pytest.raises(Err):
        client.chat(fake)
    assert fake.calls == client.MAX_429_RETRIES + 1


def test_other_errors_pass_through_without_retry(sleeps):
    fake = FakeClient([Err(400)])
    with pytest.raises(Err):
        client.chat(fake)
    assert fake.calls == 1 and sleeps == []


def test_remaining_tokens_reads_header(sleeps):
    client.chat(FakeClient([Raw({"X-RateLimit-Remaining-Tokens": "1234"})]))
    assert client.remaining_tokens() == 1234


def test_remaining_tokens_none_when_missing(sleeps):
    client.chat(FakeClient([Raw()]))
    assert client.remaining_tokens() is None


def test_key_from_env_is_not_printed(monkeypatch, capsys):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_" + "x" * 8)
    assert client.get_api_key().startswith("gsk_")
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_prompts_when_no_env_or_secrets(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(client, "getpass", lambda prompt: "typed")
    assert client.get_api_key() == "typed"


@pytest.fixture
def no_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def test_student_groq_key_wins_over_workshop_key(monkeypatch, no_keys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "workshop")
    monkeypatch.setenv("GROQ_API_KEY", "student")
    assert client.choose_provider() == "groq"
    assert client.get_api_key() == "student"


def test_workshop_key_is_the_default(monkeypatch, no_keys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "workshop")
    assert client.choose_provider() == "openrouter"
    assert client.get_api_key() == "workshop"


def test_make_client_sets_base_url_and_provider(monkeypatch, no_keys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "workshop")
    made = client.make_client()
    assert str(made.base_url).startswith(client.BASE_URLS["openrouter"])
    assert client.active_provider() == "openrouter"


def test_typed_groq_key_switches_to_groq(monkeypatch, no_keys):
    monkeypatch.setattr(client, "getpass", lambda prompt: "gsk_" + "y" * 8)
    made = client.make_client()
    assert str(made.base_url).startswith(client.BASE_URLS["groq"])
    assert client.active_provider() == "groq"


def test_backoff_grows_without_retry_after(sleeps):
    fake = FakeClient([Err(429), Err(429), Raw()])
    client.chat(fake)
    assert sleeps == [client.DEFAULT_WAIT_S, client.DEFAULT_WAIT_S * 2]


class FakeReply:
    def __init__(self, payload, ok=True):
        self.payload, self.ok = payload, ok

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("bad status")

    def json(self):
        return self.payload


def test_openrouter_credit_reads_limit_remaining(monkeypatch):
    seen = {}

    def fake_get(url, headers, timeout):
        seen["url"], seen["auth"] = url, headers["Authorization"]
        return FakeReply({"data": {"limit_remaining": 12.5}})

    monkeypatch.setattr(client.requests, "get", fake_get)
    assert client.openrouter_credit("k") == 12.5
    assert seen == {"url": client.OPENROUTER_KEY_URL, "auth": "Bearer k"}


def test_openrouter_credit_is_none_without_limit_or_on_failure(monkeypatch):
    monkeypatch.setattr(
        client.requests, "get", lambda *a, **k: FakeReply({"data": {"limit_remaining": None}})
    )
    assert client.openrouter_credit("k") is None
    monkeypatch.setattr(client.requests, "get", lambda *a, **k: FakeReply({}, ok=False))
    assert client.openrouter_credit("k") is None
