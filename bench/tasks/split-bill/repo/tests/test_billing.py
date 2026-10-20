from billing import split_amount


def test_even_split():
    assert split_amount(90, 3) == [30.0, 30.0, 30.0]


def test_uneven_split_adds_up():
    shares = split_amount(100, 3)
    assert round(sum(shares), 2) == 100.00
    assert max(shares) - min(shares) <= 0.0100001
