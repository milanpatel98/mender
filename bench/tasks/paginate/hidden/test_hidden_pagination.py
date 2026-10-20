from pagination import page, page_count


def test_counts():
    assert page_count(0, 10) == 0
    assert page_count(10, 10) == 1
    assert page_count(11, 10) == 2
    assert page_count(1, 50) == 1


def test_every_item_reachable_once():
    items = list(range(97))
    seen = []
    for n in range(1, page_count(len(items), 7) + 1):
        seen += page(items, n, 7)
    assert seen == items


def test_past_the_end_is_empty():
    assert page(list(range(5)), 3, 5) == []
