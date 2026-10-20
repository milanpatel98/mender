from limiter import TokenBucket


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_slow_rate_refills_when_polled_often():
    clock = FakeClock()
    bucket = TokenBucket(rate=0.5, capacity=1, clock=clock)
    assert bucket.allow()
    allowed = 0
    for _ in range(10):  # poll once a second for 10 seconds
        clock.t += 1
        allowed += bucket.allow()
    assert allowed == 5
