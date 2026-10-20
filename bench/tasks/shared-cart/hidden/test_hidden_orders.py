from orders import Order


def test_many_orders_independent():
    orders = [Order().add((f"item{i}", 1.0)) for i in range(5)]
    assert all(len(o.items) == 1 for o in orders)


def test_caller_list_is_copied():
    seed = [("bagel", 2.25)]
    order = Order(seed)
    seed.append(("coffee", 4.0))
    assert order.total() == 2.25
    order.add(("jam", 0.5))
    assert seed == [("bagel", 2.25), ("coffee", 4.0)]
