import pytest

from durations import parse_duration


def test_combinations():
    assert parse_duration("1h30m") == 5400
    assert parse_duration("2h") == 7200
    assert parse_duration("45s") == 45
    assert parse_duration("1h0m15s") == 3615
    assert parse_duration("120s") == 120


@pytest.mark.parametrize("bad", ["", "5", "h", "10x", "1h-30m"])
def test_more_garbage(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)
