from guests import parse


def test_plain_rows():
    assert parse("a,b\n1,2\n3,4") == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]


def test_escaped_quotes():
    text = 'name,note\n"Ann","said ""hi"""\n'
    assert parse(text) == [{"name": "Ann", "note": 'said "hi"'}]


def test_newline_inside_quotes():
    text = 'name,note\nBo,"line one\nline two"\n'
    assert parse(text) == [{"name": "Bo", "note": "line one\nline two"}]


def test_empty_fields_and_empty_input():
    assert parse("a,b,c\n1,,3") == [{"a": "1", "b": "", "c": "3"}]
    assert parse("") == []
