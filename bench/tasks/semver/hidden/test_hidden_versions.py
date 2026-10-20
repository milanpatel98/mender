from versions import is_newer


def test_prefix_and_padding():
    assert is_newer("v2.0", "1.99.99")
    assert not is_newer("1.2", "1.2.0")
    assert not is_newer("1.2.0", "v1.2")
    assert is_newer("1.2.1", "1.2")


def test_equal_is_not_newer():
    assert not is_newer("3.4.5", "3.4.5")


def test_large_numbers():
    assert is_newer("10.0.0", "9.99.999")
