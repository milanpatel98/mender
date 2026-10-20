from orders import Order


def test_orders_do_not_share_items():
    a = Order().add(("tea", 3.5))
    b = Order()
    assert b.items == []
    assert a.total() == 3.5
