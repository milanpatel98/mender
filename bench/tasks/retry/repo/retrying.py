import time


def retry(attempts=3, delay=0.1, exceptions=(Exception,)):
    """Retry a function on the given exceptions with exponential backoff."""

    def decorator(fn):
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == attempts - 1:
                        raise
                    time.sleep(delay * 2**attempt)

        return wrapper

    return decorator
