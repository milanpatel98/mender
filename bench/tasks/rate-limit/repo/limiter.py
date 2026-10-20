import time


class TokenBucket:
    def __init__(self, rate, capacity, clock=time.monotonic):
        self.rate = rate  # tokens added per second
        self.capacity = capacity
        self.tokens = capacity
        self.clock = clock
        self.updated = clock()

    def allow(self, cost=1):
        now = self.clock()
        elapsed = now - self.updated
        self.tokens = min(self.capacity, self.tokens + int(elapsed * self.rate))
        self.updated = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
