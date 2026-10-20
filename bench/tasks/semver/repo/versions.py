def parse(version):
    return version.strip().lstrip("vV").split(".")


def is_newer(candidate, current):
    """True if `candidate` is a strictly newer version than `current`."""
    return parse(candidate) > parse(current)
