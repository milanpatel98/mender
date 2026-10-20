import pytest

from durations import parse_duration


def test_multi_digit():
    assert parse_duration("90m") == 5400


def test_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("abc")
