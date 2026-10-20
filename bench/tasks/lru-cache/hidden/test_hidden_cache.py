from cache import LRUCache


def test_update_counts_as_use():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    c.put("c", 3)
    assert c.get("a") == 10 and "b" not in c


def test_matches_reference_model():
    import random

    rng = random.Random(3)
    c, model = LRUCache(4), []
    values = {}
    for _ in range(500):
        k = rng.randint(0, 9)
        if rng.random() < 0.5:
            c.put(k, k * 2)
            values[k] = k * 2
            if k in model:
                model.remove(k)
            model.append(k)
            if len(model) > 4:
                model.pop(0)
        else:
            got = c.get(k)
            if k in model:
                model.remove(k)
                model.append(k)
                assert got == values[k]
            else:
                assert got is None
        assert sorted(model) == sorted(c._data)


def test_missing_default():
    assert LRUCache(1).get("x", "none") == "none"
