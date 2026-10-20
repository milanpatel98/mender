import random

from slots import merge


def test_empty_and_single():
    assert merge([]) == []
    assert merge([(1, 2)]) == [(1, 2)]


def test_nested():
    assert merge([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]


def test_does_not_mutate():
    data = [(5, 6), (1, 2)]
    merge(data)
    assert data == [(5, 6), (1, 2)]


def test_random_against_brute_force():
    rng = random.Random(11)
    for _ in range(200):
        slots = []
        for _ in range(rng.randint(1, 8)):
            a = rng.randint(0, 30)
            slots.append((a, a + rng.randint(0, 6)))
        out = merge(slots)
        covered = {t for a, b in slots for t in range(a, b)}
        assert {t for a, b in out for t in range(a, b)} == covered
        assert out == sorted(out)
        assert all(out[i][1] < out[i + 1][0] for i in range(len(out) - 1))
