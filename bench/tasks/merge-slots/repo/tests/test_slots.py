from slots import merge


def test_touching_slots_merge():
    assert merge([(9, 10), (10, 11)]) == [(9, 11)]


def test_unsorted_input():
    assert merge([(13, 14), (9, 12), (11, 13)]) == [(9, 14)]
