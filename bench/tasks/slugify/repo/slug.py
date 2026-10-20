import re


def slugify(text):
    """Turn a title into a lowercase, hyphen-separated URL slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
