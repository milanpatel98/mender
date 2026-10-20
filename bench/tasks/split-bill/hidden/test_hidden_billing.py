import random

import pytest

from billing import split_amount


def test_small_amount():
    assert sorted(split_amount(0.10, 3), reverse=True) == [0.04, 0.03, 0.03]


def test_many_amounts_always_add_up():
    rng = random.Random(7)
    for _ in range(300):
        total = round(rng.uniform(0, 5000), 2)
        ways = rng.randint(1, 13)
        shares = split_amount(total, ways)
        assert len(shares) == ways
        assert round(sum(shares), 2) == total
        assert round(max(shares) - min(shares), 2) <= 0.01


def test_rejects_zero_ways():
    with pytest.raises(ValueError):
        split_amount(10, 0)
