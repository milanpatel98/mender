import pytest

import retrying
from retrying import retry


def test_non_listed_errors_are_not_retried(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retrying.time, "sleep", sleeps.append)
    calls = []

    @retry(exceptions=(ConnectionError,))
    def save():
        calls.append(1)
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        save()
    assert len(calls) == 1 and sleeps == []


def test_name_preserved():
    @retry()
    def fetch_rates():
        return 1

    assert fetch_rates.__name__ == "fetch_rates"
