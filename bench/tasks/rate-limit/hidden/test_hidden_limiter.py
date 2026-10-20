from limiter import TokenBucket


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_capacity_caps_accumulation():
    clock = FakeClock()
    b = TokenBucket(rate=10, capacity=3, clock=clock)
    for _ in range(3):
        assert b.allow()
    assert not b.allow()
    clock.t += 100
    assert sum(b.allow() for _ in range(10)) == 3


def test_fine_grained_polling():
    clock = FakeClock()
    b = TokenBucket(rate=2, capacity=1, clock=clock)
    b.allow()
    allowed = 0
    for _ in range(1000):  # poll every 10 ms for 10 s
        clock.t += 0.01
        allowed += b.allow()
    assert 19 <= allowed <= 20


def test_cost_greater_than_one():
    clock = FakeClock()
    b = TokenBucket(rate=1, capacity=5, clock=clock)
    assert b.allow(cost=5)
    clock.t += 2.5
    assert not b.allow(cost=3)
    clock.t += 0.5
    assert b.allow(cost=3)
