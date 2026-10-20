def split_amount(total, ways):
    """Split a dollar amount into `ways` shares that add back up to the total."""
    if ways <= 0:
        raise ValueError("ways must be positive")
    share = round(total / ways, 2)
    return [share] * ways
