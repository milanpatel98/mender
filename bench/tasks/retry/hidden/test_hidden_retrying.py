import pytest

import retrying
from retrying import retry


def test_listed_errors_retry_with_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retrying.time, "sleep", sleeps.append)
    calls = []

    @retry(attempts=4, delay=0.5, exceptions=(ConnectionError, TimeoutError))
    def ping():
        calls.append(1)
        raise TimeoutError

    with pytest.raises(TimeoutError):
        ping()
    assert len(calls) == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_recovers(monkeypatch):
    monkeypatch.setattr(retrying.time, "sleep", lambda s: None)
    state = {"n": 0}

    @retry(exceptions=(ConnectionError,))
    def flaky(x):
        state["n"] += 1
        if state["n"] < 2:
            raise ConnectionError
        return x * 2

    assert flaky(21) == 42


def test_docstring_preserved():
    @retry()
    def f():
        """doc"""

    assert f.__doc__ == "doc"
