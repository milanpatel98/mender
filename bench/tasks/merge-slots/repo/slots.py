def merge(intervals):
    """Merge overlapping or touching (start, end) slots."""
    merged = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(slot) for slot in merged]
