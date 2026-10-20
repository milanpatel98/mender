from guests import parse


def test_quoted_comma():
    text = 'name,room,tier\n"Patel, Milan",204,VIP\n'
    assert parse(text) == [{"name": "Patel, Milan", "room": "204", "tier": "VIP"}]
