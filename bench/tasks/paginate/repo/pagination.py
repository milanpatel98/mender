def page_count(total_items, per_page):
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    return total_items // per_page


def page(items, number, per_page):
    """Return page `number` (1-based) of `items`."""
    start = number * per_page
    return items[start:start + per_page]
