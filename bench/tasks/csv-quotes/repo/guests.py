def parse_line(line):
    return [field.strip() for field in line.split(",")]


def parse(text):
    """Parse CSV text with a header row into a list of dicts."""
    rows = [parse_line(line) for line in text.strip().splitlines()]
    if not rows:
        return []
    header, *body = rows
    return [dict(zip(header, row)) for row in body]
