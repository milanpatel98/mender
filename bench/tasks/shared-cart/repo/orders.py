class Order:
    def __init__(self, items=[]):
        self.items = items

    def add(self, item):
        self.items.append(item)
        return self

    def total(self):
        return round(sum(price for _, price in self.items), 2)
