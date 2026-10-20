from cache import LRUCache


def test_new_key_survives():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert "c" in c
    assert "a" not in c


def test_read_counts_as_use():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert "a" in c and "b" not in c
