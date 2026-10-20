from datetime import datetime, timedelta, timezone

import pytest

from checkins import same_day

UTC = timezone.utc
DENVER = timezone(timedelta(hours=-6))
TOKYO = timezone(timedelta(hours=9))


def test_midnight_boundary():
    before = datetime(2026, 7, 4, 5, 59, tzinfo=UTC)
    after = datetime(2026, 7, 4, 6, 0, tzinfo=UTC)
    assert not same_day(before, after, DENVER)


def test_mixed_input_offsets():
    a = datetime(2026, 1, 1, 9, 0, tzinfo=TOKYO)
    b = datetime(2026, 1, 1, 0, 30, tzinfo=UTC)
    assert same_day(a, b, TOKYO)


def test_naive_rejected():
    with pytest.raises(ValueError):
        same_day(datetime(2026, 1, 1), datetime(2026, 1, 1, tzinfo=UTC), UTC)
