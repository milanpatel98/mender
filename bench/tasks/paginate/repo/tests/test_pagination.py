from pagination import page, page_count


def test_partial_last_page_counts():
    assert page_count(25, 10) == 3


def test_first_page():
    assert page(list(range(1, 26)), 1, 10) == list(range(1, 11))
