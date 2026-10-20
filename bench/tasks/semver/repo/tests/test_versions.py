from versions import is_newer


def test_numeric_not_lexical():
    assert is_newer("1.10.0", "1.9.0")
    assert not is_newer("1.9.0", "1.10.0")
