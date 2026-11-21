import pytest

from core import tools


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(tools, "_clock", fake.monotonic)
    monkeypatch.setattr(tools, "_sleep", fake.sleep)
    monkeypatch.setattr(tools, "_last_arxiv_call", None)
    monkeypatch.setattr(tools, "OFFLINE", False)
    tools.reset_cache()
    return fake
