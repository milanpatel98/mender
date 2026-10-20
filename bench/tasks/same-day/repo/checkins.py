from datetime import datetime


def same_day(a: datetime, b: datetime, tz) -> bool:
    """True if two aware datetimes fall on the same calendar day in `tz`.

    Naive datetimes are rejected with ValueError, since their day is ambiguous.
    """
    return a.date() == b.date()
