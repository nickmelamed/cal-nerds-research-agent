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
    monkeypatch.setattr(client, "getpass", lambda prompt: "typed")
    assert client.get_api_key() == "typed"
